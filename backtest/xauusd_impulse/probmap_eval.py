import numpy as np, pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_rows",400); pd.set_option("display.max_columns",40)
SLs=[0.5,1,1.5,2,3.]; TPs=[0.25,0.5,1,1.5,2,3.]; MONTHS=111.7
D=pd.read_parquet("probmap_ev.parquet"); G=np.load("probmap_res.npy")
col=lambda s,t: SLs.index(s)*len(TPs)+TPs.index(t)
D["IS"]=D.year<=2022
def stats(mask,s,t):
    r=G[mask.values,col(s,t)]; c=D.costATR.values[mask.values]
    win=(np.isclose(r,t)).mean(); net=(r-c)/s
    return win, net.mean(), mask.sum()
print("=== 1) FRONTIERA PROBABILITA' / RENDIMENTO: pattern vs ingresso casuale (stessa ora), tutti gli anni ===")
print("SL e TP in multipli di ATR (ATR = range medio delle 20 candele). E = risultato atteso NETTO per trade in R (1R = stop)")
for tf in [1,5,15,30]:
    rows=[]
    for s in SLs:
        for t in TPs:
            p=(D.tf==tf)&(D.kind=="pattern"); q=(D.tf==tf)&(D.kind=="casuale")
            wp,ep,n=stats(p,s,t); wq,eq,_=stats(q,s,t)
            rows.append(dict(SL=s,TP=t,RR=f"1:{t/s:.2f}",win_pattern=round(100*wp,1),win_casuale=round(100*wq,1),vantaggio_pp=round(100*(wp-wq),1),E_netto_R=round(ep,3),E_casuale_R=round(eq,3)))
    R=pd.DataFrame(rows).sort_values("win_pattern",ascending=False)
    print(f"\n-- M{tf}: {int(((D.tf==tf)&(D.kind=='pattern')).sum())} segnali = {((D.tf==tf)&(D.kind=='pattern')).sum()/MONTHS:.0f}/mese, ATR mediano {D[(D.tf==tf)].ATR.median():.2f}$, costo mediano {D[(D.tf==tf)].costATR.median():.2f} ATR --")
    print(R.iloc[::2].to_string(index=False))
print("\n=== 2) QUALI CONDIZIONI AUMENTANO LA PROBABILITA'? Geometria di riferimento SL 1 ATR / TP 1 ATR ===")
print("vantaggio = win% pattern - win% casuale dello stesso TF; deve essere >0 sia 2017-22 (IS) che 2023-26 (OOS)")
P=D[D.kind=="pattern"].copy(); Q=D[D.kind=="casuale"]
base={(tf,isv):(np.isclose(G[((D.kind=="casuale")&(D.tf==tf)&(D.IS==isv)).values,col(1,1)],1)).mean() for tf in [1,3,5,15,30] for isv in [True,False]}
P["win"]=np.isclose(G[(D.kind=="pattern").values,col(1,1)],1); P["net"]=G[(D.kind=="pattern").values,col(1,1)]-P.costATR
P["lift"]=P.win-np.array([base[(a,b)] for a,b in zip(P.tf,P.IS)])
bins={"tf":None,"hour":None,"dow":None,
      "exp":[1.5,2,2.5,3,4,99],"comp":[0,0.7,0.85,1,1.2,99],"vr":[0,1,1.5,2,3,99],"quiet":None,"brk":None,"trend":None,
      "rsi_dir":[0,40,50,60,70,80,100],"reg":[0,0.8,1,1.25,1.6,99],"costATR":[0,0.1,0.2,0.4,99]}
for f,bb in bins.items():
    x=P.assign(g=pd.cut(P[f],bb) if bb else P[f])
    t=x.groupby(["g","IS"],observed=True).agg(n=("win","size"),win=("win","mean"),lift=("lift","mean"),net=("net","mean")).unstack("IS")
    t.columns=[f"{a}_{'IS' if b else 'OOS'}" for a,b in t.columns]
    for c in ["win_IS","win_OOS","lift_IS","lift_OOS"]: t[c]=(100*t[c]).round(1)
    t[["net_IS","net_OOS"]]=t[["net_IS","net_OOS"]].round(3)
    t["coerente"]=np.where((t.lift_IS>0)&(t.lift_OOS>0),"SI","")
    print(f"\n-- per {f} --"); print(t[["n_IS","n_OOS","win_IS","win_OOS","lift_IS","lift_OOS","net_IS","net_OOS","coerente"]].to_string())
P.to_parquet("probmap_P.parquet")
