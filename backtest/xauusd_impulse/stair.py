import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from engine import P, run, make_tf, find_setups
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet"); e["spr"]=np.maximum(e.spread/1000,0.20)
COST=0.20+0.054+0.10
rows=[]; trows=[]
for tf in [1,3,5,15,30]:
    p=P(DON=32,ALIGN=True,USEQUIET=False)
    b=make_tf(e,tf); sig,ar=find_setups(b,p)
    d=np.sign((b.close-b.open).values)[sig]
    # leg index: previous same-direction signals within the last 32 bars
    leg=np.array([((sig[(sig<s)&(sig>=s-32)]>=0) & (d[(sig<s)&(sig>=s-32)]==dd)).sum() for s,dd in zip(sig,d)])
    c=b.close.values; yr=b.index.year[sig]
    for legname,lm in [("1a rottura",leg==0),("gamba 2+",leg>=1),("tutte",leg>=0)]:
        for per,pm in [("IS",yr<=2022),("OOS",yr>=2023)]:
            ix=sig[lm&pm]; dd=d[lm&pm]; r=dict(TF=f"M{tf}",leg=legname,per=per,n=len(ix))
            for h in [1,3,6,12,24]:
                ok=ix+h<len(c); fr=dd[ok]*(c[ix[ok]+h]-c[ix[ok]])
                r[f"h{h}$"]=round(fr.mean(),2); r[f"t{h}"]=round(fr.mean()/(fr.std()/np.sqrt(len(fr))),1) if len(fr)>2 else np.nan
            rows.append(r)
    # pause->breakout trades (net) with leg tag
    n=run(e,tf,p,cost=True); g=run(e,tf,p,cost=False)
    legmap=dict(zip(pd.to_datetime(b.index[sig]).values,leg))
    for df,lab in [(g,"lordo"),(n,"netto")]:
        t=df[df.status=="triggered"].copy(); t["leg"]=[legmap.get(np.datetime64(x),-1) for x in pd.to_datetime(t.t).values]
        t["IS"]=pd.to_datetime(t.t).dt.year<=2022
        for (l1,isv),gg in t.groupby([t.leg>=1,"IS"]):
            trows.append(dict(TF=f"M{tf}",costi=lab,leg="gamba 2+" if l1 else "1a rottura",per="IS" if isv else "OOS",n=len(gg),
               win=round(100*(gg.R>0).mean(),1),ER=round(gg.R.mean(),3),t=round(gg.R.mean()/(gg.R.std()/np.sqrt(len(gg))),1) if len(gg)>2 else np.nan))
print("A) Deriva $ nella direzione dell'impulso, ingresso a chiusura impulso (costo ~",COST,"$)")
print(pd.DataFrame(rows).to_string(index=False))
print("\nB) Trade impulso->pausa->breakout, SL oltre pausa, TP 2R")
print(pd.DataFrame(trows).to_string(index=False))
