import pandas as pd, numpy as np
pd.set_option("display.width",250)
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
h=e.resample("1h").agg({"open":"first","close":"last"}).dropna()
h["r"]=np.log(h.close/h.open)*1e4  # bps
h["hr"]=h.index.hour; h["IS"]=h.index.year<=2022
g=h.groupby(["hr","IS"]).r.agg(["mean","std","size"]); g["t"]=g["mean"]/(g["std"]/np.sqrt(g["size"]))
t=g[["mean","t"]].unstack().round(2); t.columns=["bps_OOS","bps_IS","t_OOS","t_IS"]
t["$_su_4000"]=(t.bps_OOS*0.4).round(2)
print("Rendimento medio per ora UTC (bps; 1 bp a 4000$ = 0.40$). Costo ~0.35$ = ~0.9 bp OOS / ~1.8 bp IS"); print(t.to_string())
# Session blocks
blocks={"Asia 22-06":list(range(22,24))+list(range(0,6)),"Londra 06-12":range(6,12),"NY 12-17":range(12,17),"Sera 17-22":range(17,22)}
for k,v in blocks.items():
    x=h[h.hr.isin(v)]; d=x.groupby([x.index.date,x.IS]).r.sum().reset_index()
    for per in [True,False]:
        y=d[d.IS==per].r; print(f"{k:14s} {'IS ' if per else 'OOS'} giorni={len(y):5d} media={y.mean():6.2f}bps t={y.mean()/(y.std()/np.sqrt(len(y))):5.2f} %pos={100*(y>0).mean():.1f}")
