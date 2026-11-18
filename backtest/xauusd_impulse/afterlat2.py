import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, numba as nb
from engine import make_tf; from grid import load, prep
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
@nb.njit(cache=True)
def sym(k0,kend,d,E,X,H,L):
    e=d*E
    for k in range(k0,kend):
        hi=(H[k] if d==1 else -L[k])-e; lo=(L[k] if d==1 else -H[k])-e
        up=hi>=X; dn=-lo>=X
        if up and dn: return 0   # ambiguo nella stessa candela M1: non conteggiato
        if up: return 1
        if dn: return -1
    return 2
@nb.njit(cache=True)
def excursion(k0,kend,d,E,H,L,C):
    e=d*E; mfe=0.0; mae=0.0
    for k in range(k0,kend):
        hi=(H[k] if d==1 else -L[k])-e; lo=(L[k] if d==1 else -H[k])-e
        if hi>mfe: mfe=hi
        if -lo>mae: mae=-lo
    return mfe,mae,(C[kend-1] if d==1 else -C[kend-1])-e
m=load("exness"); mod,wd,yr,eod=prep(m); H,L,C=(m[c].values.astype(np.float64) for c in ["high","low","close"])
yrs=(pd.Timestamp("2026-08-18")-pd.Timestamp("2017-04-28")).days/365.25
rng_=np.random.default_rng(5); rows=[]
for tf in [5,15,30,60]:
    b=make_tf(m,tf); rg=(b.high-b.low); body=(b.close-b.open)
    a20=rg.shift(1).rolling(20).mean(); v20=b.vol.shift(1).rolling(20).mean(); mx=rg.shift(1).rolling(20).max()
    ok=(a20.notna()&(rg>0)).values
    ev=ok&(mx<2*a20).values&(rg>=2*a20).values&(b.vol>=2*v20).values&(body.abs()>=0.6*rg).values
    cand=np.flatnonzero(ev); imps=rg.values[cand]
    pool=np.flatnonzero(ok); rnd=rng_.choice(pool,len(cand)*5,replace=False)
    for kind,idxs in [("dopo lateralita",cand),("casuale",rnd)]:
        for j,i in enumerate(idxs):
            k=int(b.i1.values[i])
            if k>=len(H) or eod[k]<=k: continue
            kend=min(eod[k],int(b.i1.values[min(len(b)-1,i+12)]))
            if kind=="dopo lateralita":
                d=int(np.sign(body.values[i])); imp=rg.values[i]
            else:
                d=int(rng_.choice([-1,1])); imp=imps[rng_.integers(len(imps))]
            if d==0: continue
            E=b.close.values[i]
            r05=sym(k,kend,d,E,0.5*imp,H,L); r1=sym(k,kend,d,E,1.0*imp,H,L)
            mfe,mae,fin=excursion(k,kend,d,E,H,L,C)
            rows.append((tf,kind,yr[k],m.index[k].hour,imp,r05,r1,mfe/imp,mae/imp,fin/imp,fin))
D=pd.DataFrame(rows,columns=["tf","kind","year","hour","imp","r05","r1","mfeX","maeX","finX","fin"]); D.to_parquet("afterlat2.parquet")
for tf in [5,15,30,60]:
    x=D[(D.tf==tf)&(D.kind=="dopo lateralita")]
    print(f"\n=== M{tf}: {len(x)} lateralità seguite da candela >=2x range e >=2x volume = {len(x)/yrs/12:.1f} al mese; impulso mediano {x.imp.median():.2f}$ ===")
    for kind in ["dopo lateralita","casuale"]:
        z=D[(D.tf==tf)&(D.kind==kind)]
        def share(col):
            v=z[col]; dec=v.isin([1,-1]); return 100*(v[dec]==1).mean(), 100*(v==2).mean()
        c05,s05=share("r05"); c1,s1=share("r1")
        print(f"  {kind:16s} | +0.5x prima di -0.5x: {c05:5.1f}% (fermo {s05:4.1f}%) | +1x prima di -1x: {c1:5.1f}% (fermo {s1:4.1f}%) | max a favore {z.mfeX.median():.2f}x  max contro {z.maeX.median():.2f}x  | media dopo 12 candele {z.finX.mean():+.3f}x ({z.fin.mean():+.2f}$)")
