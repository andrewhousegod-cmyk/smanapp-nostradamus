import pandas as pd, numpy as np
pd.set_option("display.width",250); pd.set_option("display.max_rows",300); pd.set_option("display.max_columns",40)
A=pd.read_parquet("scalp_exness.parquet"); P=pd.read_parquet("scalp_exness_pess.parquet")
days=A.days.iloc[0]; A["IS"]=A.year<=2022; cfg=["tf","N","K","sl"]
print(f"Giorni di trading nel campione: {days}")
print("\n1) FREQUENZA dei setup lateralita'->rottura con volume (tutte le ore 00-20 UTC, NFP escluso)")
f=A.groupby(cfg).agg(setup=("k","size"),stop_med=("R","median")); f["al_giorno"]=(f.setup/days).round(2); print(f.to_string())
u=A.drop_duplicates("k"); print(f"Unione di tutte le configurazioni: {len(u)} rotture distinte = {len(u)/days:.2f} al giorno")
print("\n2) DOPO LA ROTTURA: % che raggiunge +D $ prima dello stop  vs  % atteso se il prezzo fosse casuale [R/(R+D)]")
rows=[]
for key,g in A.groupby(cfg):
    r=dict(zip(cfg,key)); r["n"]=len(g)
    for D in [2,4,6,8,10]:
        obs=g[f"hit{D}"].mean(); exp_=(g.R/(g.R+D)).mean(); r[f"{D}$ oss"]=round(100*obs,1); r[f"{D}$ caso"]=round(100*exp_,1)
    rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))
print("\n3) SETUP A 6 ORDINI (5 TP + 1 runner trailing 3$), R per trade sul rischio TOTALE, netto costi 0.354$/oz")
cols=[c for c in A.columns if "|BE" in c]
out=[]
for key,g in A.groupby(cfg):
    gp=P.loc[g.index]
    for c in cols:
        for per,msk in [("IS",g.IS),("OOS",~g.IS)]:
            net_o=(g[c]-0.354/g.R)[msk]; net_p=(gp[c]-0.354/gp.R)[msk]
            out.append(dict(**dict(zip(cfg,key)),schema=c,per=per,n=int(msk.sum()),lordo=round(g[c][msk].mean(),3),netto_ott=round(net_o.mean(),3),netto_pess=round(net_p.mean(),3),
                            giorni_pos=round(100*((g[msk].assign(x=net_o).groupby(pd.to_datetime(g[msk].k,unit='s').dt.date if False else g[msk].k//1440).x.sum())>0).mean(),1)))
O=pd.DataFrame(out)
pv=O.pivot_table(index=cfg+["schema"],columns="per",values=["lordo","netto_ott","netto_pess"]).round(3)
pv["best_min"]=pv[[("netto_ott","IS"),("netto_ott","OOS")]].min(axis=1)
print(pv.sort_values("best_min",ascending=False).head(25).to_string())
print(f"\nSchemi con netto (ottimistico) >0 in IS e OOS: {(pv.best_min>0).sum()} su {len(pv)}")
print("\nMediane per schema (tutte le config):"); print(pv.groupby(level="schema").median().round(3).to_string())
