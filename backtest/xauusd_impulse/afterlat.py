import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, numba as nb
from engine import make_tf; from grid import load, prep
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
@nb.njit(cache=True)
def first_touch(k0,kend,d,E,ext,back,H,L,C):
    # returns 1 continue (+ext first), -1 back (-back first), 0 neither; plus MFE, MAE, final (in $)
    e=d*E; mfe=0.0; mae=0.0; res=0
    for k in range(k0,kend):
        hi=(H[k] if d==1 else -L[k])-e; lo=(L[k] if d==1 else -H[k])-e
        if -lo>mae: mae=-lo
        if hi>mfe: mfe=hi
        if res==0:
            if -lo>=back: res=-1
            elif hi>=ext: res=1
    fin=(C[kend-1] if d==1 else -C[kend-1])-e
    return res,mfe,mae,fin
m=load("exness"); mod,wd,yr,eod=prep(m); H,L,C=(m[c].values.astype(np.float64) for c in ["high","low","close"])
rows=[]; rng_=np.random.default_rng(3)
for tf in [5,15,30,60]:
    b=make_tf(m,tf); rg=(b.high-b.low); body=(b.close-b.open)
    a20=rg.shift(1).rolling(20).mean(); v20=b.vol.shift(1).rolling(20).mean(); mx=rg.shift(1).rolling(20).max()
    ema=b.close.ewm(span=200,adjust=False).mean()
    ok=a20.notna()&(rg>0)
    ev=ok&(mx<2*a20)&(rg>=2*a20)&(b.vol>=2*v20)&(body.abs()>=0.6*rg)
    cand=np.flatnonzero(ev.values)
    rnd=rng_.choice(np.flatnonzero(ok.values&(rg>0).values), size=min(len(cand)*5, ok.sum()), replace=False)
    for kind,idxs in [("dopo lateralità",cand),("candela casuale",rnd)]:
        for i in idxs:
            k=int(b.i1.values[i]); 
            if k>=len(H) or eod[k]<=k: continue
            kend=min(eod[k],int(b.i1.values[min(len(b)-1,i+12)]))
            d=int(np.sign(body.values[i])) if kind=="dopo lateralità" else int(rng_.choice([-1,1]))
            if d==0: continue
            r_=rg.values[i]; E=b.close.values[i]
            back = abs(b.close.values[i]-b.open.values[i]) if kind=="dopo lateralità" else r_   # ritorno all'apertura dell'impulso
            res,mfe,mae,fin=first_touch(k,kend,d,E,r_,back,H,L,C)
            t=m.index[k]
            rows.append((tf,kind,yr[k],t.hour,d,r_,rg.values[i]/a20.values[i],b.vol.values[i]/v20.values[i],res,mfe,mae,fin,np.sign(b.close.values[i]-ema.values[i])==d))
D=pd.DataFrame(rows,columns=["tf","kind","year","hour","d","imp","ratio","vratio","res","mfe","mae","fin","withtrend"])
D.to_parquet("afterlat.parquet")
yrs=(pd.Timestamp("2026-08-18")-pd.Timestamp("2017-04-28")).days/365.25
print("=== QUANTE VOLTE E COSA SUCCEDE (2017-04 -> 2026-08, oro) ===")
for tf in [5,15,30,60]:
    x=D[(D.tf==tf)&(D.kind=="dopo lateralità")]; y=D[(D.tf==tf)&(D.kind=="candela casuale")]
    print(f"\nM{tf}: {len(x)} eventi = {len(x)/yrs:.0f}/anno = {len(x)/yrs/12:.1f}/mese ; impulso mediano {x.imp.median():.2f}$")
    for lab,z in [("dopo lateralità",x),("candela casuale",y)]:
        c=(z.res==1).mean(); bk=(z.res==-1).mean(); st=(z.res==0).mean()
        print(f"  {lab:16s}: CONTINUA {100*c:5.1f}%  TORNA INDIETRO {100*bk:5.1f}%  RESTA LI {100*st:5.1f}% | estensione mediana a favore {z.mfe.median()/z.imp.median() if lab=='dopo lateralità' else z.mfe.median()/z.imp.median():.2f}x impulso | risultato medio a 12 candele {z.fin.mean():+.2f}$")
