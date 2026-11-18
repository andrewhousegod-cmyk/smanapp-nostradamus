import pandas as pd, numpy as np, sys
sys.path.insert(0,'.')
from engine import equity
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
A=pd.read_pickle("allres.pkl")
yrs=(pd.Timestamp("2026-08-18")-pd.Timestamp("2017-04-28")).days/365.25
def maxstreak(x):
    m=c=0
    for v in x: c=c+1 if v else 0; m=max(m,c)
    return m
R1=[];allt=[]
for tf,(g,n) in A.items():
    gt=g[g.status=="triggered"].copy(); nt=n[n.status=="triggered"].copy()
    gt["mfeR"]=gt.mfe_vs_imp*gt.leg_range/gt.risk_px
    nt["t"]=pd.to_datetime(nt.t); nt["tf"]=f"M{tf}"; allt.append(nt)
    e=equity(n); e["t"]=pd.to_datetime(e.t)
    eo=equity(n[pd.to_datetime(n.t).dt.year>=2023])
    dd=lambda x: round(100*(1-(x.equity/x.equity.cummax()).min()),1)
    R1.append(dict(TF=f"M{tf}",setup_tot=len(g),setup_mese=round(len(g)/yrs/12,1),setup_sett=round(len(g)/yrs/52,1),setup_giorno=round(len(g)/yrs/260,2),
      trade_tot=len(nt),trade_mese=round(len(nt)/yrs/12,1),trade_giorno=round(len(nt)/yrs/260,2),
      pct_profitto=round(100*(nt.R>0).mean(),1),pct_TP2R=round(100*(nt.res=="TP").mean(),1),
      vinc_medio_R=round(nt.R[nt.R>0].mean(),2),perd_media_R=round(nt.R[nt.R<=0].mean(),2),
      E_R_netto=round(nt.R.mean(),3),PF=round(nt.R[nt.R>0].sum()/-nt.R[nt.R<0].sum(),2),
      max_perdite_consec=maxstreak((nt.sort_values("t").R<=0).values),
      raggiunge_1R=round(100*(gt.mfeR>=1).mean(),1),raggiunge_2R=round(100*(gt.mfeR>=2).mean(),1),raggiunge_3R=round(100*(gt.mfeR>=3).mean(),1),
      cap_finale_eur_17_26=round(e.equity.iloc[-1]/1.16) if len(e) else None,maxDD_17_26=dd(e) if len(e) else None,
      cap_finale_eur_23_26=round(eo.equity.iloc[-1]/1.16) if len(eo) else None,maxDD_23_26=dd(eo) if len(eo) else None,
      costo_medio_R=round((gt.R.mean()-nt.R.mean()),3)))
print("=== SINTESI PER TIMEFRAME (2017-04 -> 2026-08, costi reali) ==="); print(pd.DataFrame(R1).T.to_string())
T=pd.concat(allt); T["year"]=T.t.dt.year
T["dow"]=T.t.dt.dayofweek; T["hour"]=T.t.dt.hour; T["IS"]=T.year<=2022
def tab(key,lab):
    x=T.groupby([key]).agg(n=("R","size"),win=("R",lambda r: round(100*(r>0).mean(),1)),ER=("R",lambda r: round(r.mean(),3)))
    xi=T[T.IS].groupby(key).R.mean().round(3).rename("ER_IS"); xo=T[~T.IS].groupby(key).R.mean().round(3).rename("ER_OOS")
    print(f"=== {lab} (tutti i TF insieme, R netto) ==="); print(pd.concat([x,xi,xo],axis=1).to_string())
tab("dow","GIORNO SETTIMANA (0=lun)"); tab("hour","ORA UTC (Italia = +1 inverno/+2 estate)"); tab("year","ANNO"); tab("tf","TF")
print("=== FILTRO TREND EMA200 (impulso nella direzione del trend) ===")
print(T.groupby(["tf","align"]).agg(n=("R","size"),win=("R",lambda r: round(100*(r>0).mean(),1)),ER=("R",lambda r: round(r.mean(),3))).unstack().to_string())
print(T.groupby(["IS","align"]).R.agg(["size","mean"]).round(3).to_string())
print("=== DURATA PAUSA (candele) ===")
print(T.groupby("pause").agg(n=("R","size"),win=("R",lambda r: round(100*(r>0).mean(),1)),ER=("R",lambda r: round(r.mean(),3))).head(9).to_string())
print("=== DIREZIONE (1=buy,-1=sell) ==="); print(T.groupby(["dir","IS"]).R.agg(["size","mean"]).round(3).to_string())
T.to_pickle("trades_all.pkl")
