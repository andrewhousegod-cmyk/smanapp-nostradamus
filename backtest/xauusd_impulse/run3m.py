import pandas as pd, numpy as np, sys
sys.path.insert(0,'.')
from engine import P, run, equity
from math import sqrt
def wilson(k,n,z=1.96):
    if n==0: return (np.nan,np.nan)
    ph=k/n; d=1+z*z/n; c=ph+z*z/(2*n); m=z*sqrt(ph*(1-ph)/n+z*z/(4*n*n)); return ((c-m)/d,(c+m)/d)
d=pd.read_parquet("duka_m1.parquet"); d=d[d.index>="2026-08-18"]
scen=sys.argv[1] if len(sys.argv)>1 else "ecn"
d["spr"]= 0.25 if scen=="ecn" else d.spread
rows=[]
for tf in [1,3,5,15,30]:
    for base in [False,True]:
        p=P(BASELINE=base)
        g=run(d,tf,p,cost=False); n=run(d,tf,p,cost=True)
        st=g.status.value_counts()
        trg=g[g.status=="triggered"]; nt=len(trg)
        cont=nt; rev=st.get("reversal",0)
        tp=(trg.res=="TP").sum(); sl=(trg.res=="SL").sum()
        lo,hi=wilson(tp,nt)
        nn=n[n.status=="triggered"]
        e=equity(n) if not base else None
        rows.append(dict(TF=f"M{tf}",test="NULL" if base else "PATTERN",impulsi=len(g),no_pausa=st.get("no_pause",0),
            ritracc_profondo=st.get("deep_retrace",0),pausa_ok=nt+rev+st.get("expired",0),
            continua=nt,inverte=rev,scade=st.get("expired",0),
            cont_pct=round(100*nt/max(1,nt+rev),1),
            win2R_pct=round(100*tp/max(1,nt),1),ci95=f"{100*lo:.0f}-{100*hi:.0f}",
            time_exit=(trg.res=="TIME").sum(),
            piu_forte_pct=round(100*(trg.mfe_vs_imp>=1).mean(),1) if nt else np.nan,
            ER_lordo=round(trg.R.mean(),3) if nt else np.nan, ER_netto=round(nn.R.mean(),3) if len(nn) else np.nan,
            rischio_med_usd=round(nn.risk_px.median(),2) if len(nn) else np.nan,
            trade_eq=len(e) if e is not None else None, eq_fin_usd=round(e.equity.iloc[-1],0) if e is not None and len(e) else None,
            maxDD_pct=round(100*(1-(e.equity/e.equity.cummax()).min()),1) if e is not None and len(e) else None))
r=pd.DataFrame(rows); pd.set_option("display.width",250); pd.set_option("display.max_columns",30); print(scen); print(r.to_string(index=False))
r.to_csv(f"res3m_{scen}.csv",index=False)
