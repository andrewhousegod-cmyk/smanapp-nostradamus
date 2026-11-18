import numpy as np, pandas as pd, numba as nb, sys
sys.path.insert(0,'.'); from scalp import setups; from grid import load, prep
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
@nb.njit(cache=True)
def tpsl(k0,kend,d,E,R,tpR,H,L,C):
    e=d*E; s=e-R; tp=e+tpR*R
    for k in range(k0,kend):
        hi=H[k] if d==1 else -L[k]; lo=L[k] if d==1 else -H[k]
        if lo<=s: return -1.0
        if k>k0 and hi>=tp: return tpR
    return (d*C[kend-1]-e)/R
m=load("exness"); mod,wd,yr,eod=prep(m); O,H,L,C=(m[x].values.astype(np.float64) for x in ("open","high","low","close"))
rows=[]
for tf,N in [(1,30),(1,60),(3,20),(5,12),(5,24)]:
    for K in [2.0,3.0]:
        k,d,SL,hgt,spd,vr=setups(m,tf,N,K,"mid")
        for j in range(len(k)):
            kk=k[j]
            if kk>=len(O) or mod[kk]>=1200 or wd[kk]>=5 or eod[kk]<=kk: continue
            E=O[kk]; R=abs(E-SL[j])          # same distance as the breakout stop (to box midpoint)
            if R<1 or R>12: continue
            kend=min(eod[kk],kk+240)
            for tpR in [0.5,1.0,1.5]:
                g=tpsl(kk+1,kend,-d[j],E,R,tpR,H,L,C)
                rows.append((tf,N,K,tpR,yr[kk]<=2022,g,g-0.354/R,mod[kk]//60))
F=pd.DataFrame(rows,columns=["tf","N","K","tpR","IS","lordo","netto","hour"])
o=F.groupby(["tf","N","K","tpR","IS"]).agg(n=("netto","size"),lordo=("lordo","mean"),netto=("netto","mean"),sd=("netto","std"))
o["t"]=o.netto/(o.sd/np.sqrt(o.n)); print("FADE della rottura: contro-direzione a mercato, SL = stessa distanza dello stop di breakout, TP = x R")
print(o.drop(columns="sd").round(3).unstack("IS").to_string())
print("\nFade per ora UTC (tutte le config, TP 1R):"); x=F[F.tpR==1.0]; print(x.groupby(["hour","IS"]).netto.mean().round(3).unstack().to_string())
