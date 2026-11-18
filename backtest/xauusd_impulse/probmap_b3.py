import numpy as np, pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_rows",400)
SLs=[0.5,1,1.5,2,3.]; TPs=[0.25,0.5,1,1.5,2,3.]; MONTHS=111.7
D=pd.read_parquet("probmap_ev.parquet"); G=np.load("probmap_res.npy"); D["IS"]=D.year<=2022
col=lambda s,t: SLs.index(s)*len(TPs)+TPs.index(t)
rows=[]
for tf in [3,5,15,30]:
  for name,cond in [("B esaurimento (exp>3 o RSI>75 o vol>3)",lambda d:(d.exp>3)|(d.rsi_dir>75)|(d.vr>3)),
                    ("B2 forte (exp>3 e RSI>75)",lambda d:(d.exp>3)&(d.rsi_dir>75))]:
    for atrmin in [0,1.5,2.5,4]:
      for s in [0.5,1.0]:
        for costo in [0.354,0.254]:
          for per,pm in [("IS",D.IS),("OOS",~D.IS)]:
            m=((D.kind=="pattern")&(D.tf==tf)&cond(D)&(D.ATR>=atrmin)&pm).values
            if m.sum()<30: continue
            r=-G[m,col(s,s)]; A=D.ATR.values[m]; net=(r-costo/A)/s
            rows.append(dict(TF=f"M{tf}",setup=name,ATR_min=atrmin,SL_TP=f"{s} ATR",costo=costo,per=per,n=int(m.sum()),
               mese=round(m.sum()/(MONTHS*(0.57 if per=='IS' else 0.43)),1),stop_medio=round(np.median(A)*s,2),
               win=round(100*np.isclose(r,s).mean(),1),lordo=round((r/s).mean(),3),netto=round(net.mean(),3)))
R=pd.DataFrame(rows)
pv=R.pivot_table(index=["TF","setup","ATR_min","SL_TP","costo"],columns="per",values=["n","mese","stop_medio","win","lordo","netto"]).dropna()
pv["ok"]=np.where((pv[("netto","IS")]>0)&(pv[("netto","OOS")]>0),"<<< POSITIVO IN ENTRAMBI","")
print(pv.round(3).to_string())
