import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from engine import P, run
from tickcheck import sim   # same management logic
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet"); e["spr"]=0.0
H,L,C=e.high.values,e.low.values,e.close.values; mt=e.index.values
COSTU=0.354
rows=[]
for setup,p in [("utente",P()),("scala",P(DON=32,ALIGN=True,USEQUIET=False))]:
    for tf in [1,3,5,15,30]:
        g=run(e,tf,p,cost=False); t=g[g.status=="triggered"]
        for r in t.itertuples():
            d=r.dir; E=(r.tp+2*r.sl)/3; R=abs(E-r.sl); k0=np.searchsorted(mt,np.datetime64(r.t_in)); ke=min(len(mt),k0+48*tf)
            for sch,units_max in [("TP2R",1),("TRAIL1R",1),("TRAIL2R",1),("PIRAMIDE+1R",2)]:
                go=sim(H,L,C,k0+1,ke,d,E,R,sch,False); gp=sim(H,L,C,k0+1,ke,d,E,R,sch,True)
                rows.append(dict(setup=setup,tf=tf,sch=sch,yr=pd.Timestamp(r.t_in).year,R=R,lordo=(go+gp)/2,lordo_ott=go,cost=units_max*COSTU/R))
df=pd.DataFrame(rows); df["netto"]=df.lordo-df.cost; df["IS"]=df.yr<=2022
df["stop$"]=pd.cut(df.R,[0,1,2,3,5,8,100],labels=["<1","1-2","2-3","3-5","5-8",">8"])
df.to_pickle("riskbucket.pkl")
o=df.groupby(["sch","stop$","IS"],observed=True).agg(n=("netto","size"),lordo=("lordo","mean"),netto=("netto","mean"),sd=("netto","std"))
o["t_netto"]=o.netto/(o.sd/np.sqrt(o.n))
pd.set_option("display.width",200); pd.set_option("display.max_rows",200)
print("Tutti i setup e TF insieme. lordo = media stima ottimistica/pessimistica; netto = lordo - costi (0.354$/unità)")
print(o.drop(columns="sd").round(3).unstack("IS").to_string())
