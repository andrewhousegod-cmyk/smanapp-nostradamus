"""Exhaustion fade simulated DIRECTLY in the traded direction (SL checked first in every bar, TP never on the entry bar).
Holdout additionally on 1-second bid bars (no intrabar ambiguity)."""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, numba as nb
from engine import make_tf; from grid import load, prep
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
@nb.njit(cache=True)
def trade(k0,kend,d,E,dist,H,L,C,firstTP):
    e=d*E; s=e-dist; t=e+dist
    for k in range(k0,kend):
        hi=H[k] if d==1 else -L[k]; lo=L[k] if d==1 else -H[k]
        if lo<=s: return -1.0
        if (k>k0 or firstTP) and hi>=t: return 1.0
    return ((C[kend-1] if d==1 else -C[kend-1])-e)/dist
def events(m,tf):
    mod,wd,yr,eod=prep(m); b=make_tf(m,tf); rg=b.high-b.low; body=b.close-b.open; a20=rg.shift(1).rolling(20).mean()
    dl=b.close.diff(); up=dl.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-dl.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); rsi=100-100/(1+up/dn.replace(0,np.nan))
    sig=(rg>=3*a20)&(body.abs()>=0.6*rg)&(((body>0)&(rsi>=75))|((body<0)&(rsi<=25)))&a20.notna()
    out=[]
    for i in np.flatnonzero(sig.values):
        k=int(b.i1.values[i])
        if k>=len(m) or mod[k]>=1200 or wd[k]>=5 or eod[k]<=k: continue
        t=m.index[k]
        if t.dayofweek==4 and t.day<=7 and 12<=t.hour<15: continue
        kend=min(eod[k],int(b.i1.values[min(len(b)-1,i+12)]))
        out.append((k,kend,-int(np.sign(body.values[i])),float(a20.values[i]),yr[k],t))
    return pd.DataFrame(out,columns=["k","kend","d","A","year","t"])
rows=[]
s1=pd.read_parquet("duka_s1.parquet"); st=s1.index.values; SH,SL_,SC=(s1[c].values.astype(np.float64) for c in ["high","low","close"])
for src in ["exness","duka"]:
    m=load(src); O,H,L,C=(m[c].values.astype(np.float64) for c in ["open","high","low","close"])
    for tf in [1,3,5,15]:
        ev=events(m,tf)
        for amin in [1.5,2.5]:
            for s in [0.5,1.0]:
                e=ev[ev.A>=amin]
                if len(e)<10: continue
                res=np.array([trade(r.k,r.kend,r.d,O[r.k],s*r.A,H,L,C,False) for r in e.itertuples()])
                net=res-0.354/(s*e.A.values)
                tick=[]
                if src=="duka":
                    for r in e.itertuples():
                        a=np.searchsorted(st,m.index.values[r.k]); z=np.searchsorted(st,m.index.values[r.kend-1]+np.timedelta64(60,'s'))
                        if z>a: tick.append(trade(a,z,r.d,O[r.k],s*r.A,SH,SL_,SC,True))
                        else: tick.append(np.nan)
                    tick=np.array(tick); tn=tick-0.354/(s*e.A.values)
                pers=[("2017-22",e.year.values<=2022),("2023-26",e.year.values>=2023)] if src=="exness" else [("ago-nov26",np.ones(len(e),bool))]
                for per,pm in pers:
                    if pm.sum()<10: continue
                    r=dict(TF=f"M{tf}",ATRmin=amin,SLTP=s,per=per,n=int(pm.sum()),win=round(100*(res[pm]==1).mean(),1),netto_R=round(net[pm].mean(),3))
                    if src=="duka": r.update(win_tick=round(100*np.nanmean(tick[pm]==1),1),netto_tick=round(np.nanmean(tn[pm]),3))
                    rows.append(r)
R=pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv("fade_true.csv",index=False)
