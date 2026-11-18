"""MAE/MFE study: no stop. For each entry track, over the intraday horizon (<=4h, flat 20:45 UTC):
for targets D: was +D reached, adverse excursion before reaching it; final P&L.
Then: P(reach +D | already adverse x) and EV grid (stop x, target D) net of cost. Breakouts vs random entries."""
import numpy as np, pandas as pd, numba as nb, sys
sys.path.insert(0,'.'); from scalp import setups; from grid import load, prep
pd.set_option("display.width",250); pd.set_option("display.max_rows",300)
D_=np.array([2.,4.,6.,8.,10.]); X_=np.array([1.,2.,3.,4.,5.,6.,8.,10.,15.])
@nb.njit(cache=True)
def track(k0,kend,d,E,H,L,C,D_,X_):
    nD=len(D_); nX=len(X_)
    hitD=np.zeros(nD); maeD=np.zeros(nD)   # MAE before hitting D (or total if never)
    # EV grid outcome: for each (x,D) result in $
    res=np.zeros((nX,nD)); done=np.zeros((nX,nD))
    mae=0.0; e=d*E
    for k in range(k0,kend):
        hi=(H[k] if d==1 else -L[k])-e; lo=(L[k] if d==1 else -H[k])-e
        # adverse first (conservative)
        if -lo>mae: mae=-lo
        for a in range(nX):
            for b in range(nD):
                if done[a,b]==0 and mae>=X_[a]: res[a,b]=-X_[a]; done[a,b]=1
        for b in range(nD):
            if hitD[b]==0 and hi>=D_[b]:
                hitD[b]=1; maeD[b]=mae
                for a in range(nX):
                    if done[a,b]==0: res[a,b]=D_[b]; done[a,b]=1
    fin=(C[kend-1] if d==1 else -C[kend-1])-e
    for b in range(nD):
        if hitD[b]==0: maeD[b]=mae
        for a in range(nX):
            if done[a,b]==0: res[a,b]=fin
    return hitD,maeD,res,mae,fin
m=load("exness"); mod,wd,yr,eod=prep(m); O,H,L,C=(m[x].values.astype(np.float64) for x in ("open","high","low","close"))
def ok(kk): return kk<len(O) and mod[kk]<1200 and wd[kk]<5 and eod[kk]>kk
ent=[]
for tf,N in [(1,30),(1,60),(3,20),(5,12),(5,24)]:
    for K in [2.0,3.0]:
        k,d,SL,hgt,spd,vr=setups(m,tf,N,K,"mid")
        for j in range(len(k)):
            if ok(k[j]): ent.append((k[j],d[j]))
ent=pd.DataFrame(ent,columns=["k","d"]).drop_duplicates("k")
rng=np.random.default_rng(1); cand=np.flatnonzero((mod<1200)&(wd<5)&(eod>np.arange(len(O))))
rnd=pd.DataFrame({"k":rng.choice(cand,len(ent),replace=False),"d":rng.choice([-1,1],len(ent))})
def run(df):
    hits=[];maes=[];R=[];tot=[]
    for kk,dd in zip(df.k.values,df.d.values):
        kend=min(eod[kk],kk+240)
        h,mD,res,mae,fin=track(kk+1,kend,dd,O[kk],H,L,C,D_,X_); hits.append(h); maes.append(mD); R.append(res); tot.append(mae)
    return np.array(hits),np.array(maes),np.array(R),np.array(tot)
out={}
for name,df in [("ROTTURE",ent),("CASUALI",rnd)]:
    hits,maes,R,tot=run(df); IS=yr[df.k.values]<=2022; out[name]=(hits,maes,R,IS)
    print(f"\n===== {name}: {len(df)} ingressi =====")
    print("A) % che raggiunge +D $ entro l'orizzonte (senza stop) e quanto va CONTRO prima di arrivarci (percentili $):")
    t=[]
    for b,D in enumerate(D_):
        w=hits[:,b]==1; mm=maes[w,b]
        t.append(dict(D=f"+{D:.0f}$ ({D*10:.0f}pip)",raggiunge=f"{100*w.mean():.1f}%",MAE_mediana=round(np.median(mm),2),MAE_75=round(np.percentile(mm,75),2),MAE_90=round(np.percentile(mm,90),2),MAE_95=round(np.percentile(mm,95),2)))
    print(pd.DataFrame(t).to_string(index=False))
    print("B) Se sono gia' sotto di x $, probabilita' di arrivare comunque a +D (senza stop):")
    t=[]
    for x in [1,2,3,4,5,6,8,10]:
        r={"gia' sotto di":f"-{x}$ ({x*10}pip)","casi %":round(100*(tot>=x).mean(),1)}
        for b,D in enumerate(D_):
            sel=(tot>=x); # reached -x at some point; did it reach D AFTER being -x? -> hit and maeD>=x
            r[f"+{D:.0f}$"]=f"{100*((hits[:,b]==1)&(maes[:,b]>=x)).sum()/max(1,sel.sum()):.0f}%"
        t.append(r)
    print(pd.DataFrame(t).to_string(index=False))
    net=R-0.354
    print("C) Expectancy netta in $ per oncia: stop x (righe) / target D (colonne). IS 2017-22 | OOS 2023-26")
    for per,msk in [("IS",IS),("OOS",~IS)]:
        g=pd.DataFrame(net[msk].mean(axis=0),index=[f"SL {x:.0f}$" for x in X_],columns=[f"TP {D:.0f}$" for D in D_]).round(3)
        print(f"-- {per} --"); print(g.to_string())
