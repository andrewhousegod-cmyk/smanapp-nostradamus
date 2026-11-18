import pandas as pd, numpy as np, sys
sys.path.insert(0,'.')
from engine import P, run, equity, make_tf
from math import sqrt
def wilson(k,n,z=1.96):
    if n==0: return (np.nan,np.nan)
    ph=k/n; d=1+z*z/n; c=ph+z*z/(2*n); m=z*sqrt(ph*(1-ph)/n+z*z/(4*n*n)); return ((c-m)/d,(c+m)/d)
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
e["spr"]=e.spread/1000.0
def summ(g,n,label):
    st=g.status.value_counts(); trg=g[g.status=="triggered"]; nn=n[n.status=="triggered"]
    nt=len(trg); rev=st.get("reversal",0); tp=(trg.res=="TP").sum(); lo,hi=wilson(tp,nt)
    return dict(set=label,impulsi=len(g),pausa_ok=nt+rev+st.get("expired",0),continua=nt,inverte=rev,
        cont_pct=round(100*nt/max(1,nt+rev),1),win2R=round(100*tp/max(1,nt),1),ci95=f"{100*lo:.0f}-{100*hi:.0f}",
        piu_forte=round(100*(trg.mfe_vs_imp>=1).mean(),1) if nt else np.nan,
        ER_lordo=round(trg.R.mean(),3) if nt else np.nan, ER_netto=round(nn.R.mean(),3) if len(nn) else np.nan,
        PF_netto=round(nn.R[nn.R>0].sum()/-nn.R[nn.R<0].sum(),2) if len(nn) else np.nan,
        risk_med=round(nn.risk_px.median(),2) if len(nn) else np.nan)
allres={}
rows=[]
for tf in [1,3,5,15,30]:
    for base in [False,True]:
        p=P(BASELINE=base)
        g=run(e,tf,p,cost=False); n=run(e,tf,p,cost=True)
        for lab,msk in [("2017-26",None),("IS 17-22","IS"),("OOS 23-26","OOS")]:
            if msk is None: gg,nn_=g,n
            else:
                f=lambda x: (pd.to_datetime(x.t).dt.year<=2022) if msk=="IS" else (pd.to_datetime(x.t).dt.year>=2023)
                gg,nn_=g[f(g)],n[f(n)]
            r=summ(gg,nn_,lab); r.update(TF=f"M{tf}",test="NULL" if base else "PATTERN"); rows.append(r)
        if not base: allres[tf]=(g,n)
r=pd.DataFrame(rows); cols=["TF","test","set"]+[c for c in r.columns if c not in("TF","test","set")]
pd.set_option("display.width",250); pd.set_option("display.max_columns",30)
print(r[cols].to_string(index=False)); r[cols].to_csv("res_full.csv",index=False)
pd.to_pickle(allres,"allres.pkl")
