import pandas as pd, numpy as np
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
C=e.close
days=pd.date_range("2017-05-01","2026-08-17",freq="D")
ff=[d for d in days if d.weekday()==4 and d.day<=7]       # first Friday (rule; a few months deviate)
rows=[]
for d in ff:
    t0=pd.Timestamp(d.date(),tz="America/New_York")+pd.Timedelta(hours=8,minutes=30); t0=t0.tz_convert("UTC")
    try:
        p0=C.loc[t0-pd.Timedelta(minutes=1)]
    except KeyError: continue
    w=C.loc[t0:t0+pd.Timedelta(hours=4)]
    if len(w)<200: continue
    for m in [5,15,30]:
        pm=C.asof(t0+pd.Timedelta(minutes=m)); dirn=np.sign(pm-p0)
        if dirn==0: continue
        for H in [30,60,120,240]:
            ph=C.asof(t0+pd.Timedelta(minutes=m+H))
            rows.append(dict(day=d,m=m,H=H,first=abs(pm-p0),cont=dirn*(ph-pm)))
r=pd.DataFrame(rows); r["IS"]=r.day.dt.year<=2022
COST=0.80  # news spread+slippage+commission, $ (conservative)
g=r.groupby(["m","H","IS"]).cont.agg(["size","mean","std"]); g["t"]=g["mean"]/(g["std"]/np.sqrt(g["size"])); g["netto"]=g["mean"]-COST
print("NFP: segui la direzione dei primi m minuti, tieni H minuti. $ medi (costo stimato",COST,"$)"); print(g.round(2).unstack().to_string())
