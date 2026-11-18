import numpy as np, pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_rows",400)
SLs=[0.5,1,1.5,2,3.]; TPs=[0.25,0.5,1,1.5,2,3.]; MONTHS=111.7
D=pd.read_parquet("probmap_ev.parquet"); G=np.load("probmap_res.npy"); D["IS"]=D.year<=2022
col=lambda s,t: SLs.index(s)*len(TPs)+TPs.index(t)
def table(mask, rand_mask, fade=False, geoms=None, label=""):
    rows=[]
    for s,t in geoms:
        for per,pm in [("IS",D.IS),("OOS",~D.IS)]:
            m=(mask&pm).values; q=(rand_mask&pm).values
            if fade:  # opposite direction: symmetric geometry only -> outcome = -original (target and stop swap)
                r=-G[m,col(s,t)]; rq=-G[q,col(s,t)]
            else:
                r=G[m,col(s,t)]; rq=G[q,col(s,t)]
            c=D.costATR.values[m]; cq=D.costATR.values[q]
            rows.append(dict(SL=s,TP=t,per=per,n=m.sum(),mese=round(m.sum()/(MONTHS*(0.57 if per=="IS" else 0.43)),1),
                win=round(100*np.isclose(r,t).mean(),1),win_caso=round(100*np.isclose(rq,t).mean(),1),
                E_netto_R=round(((r-c)/s).mean(),3),E_lordo_R=round((r/s).mean(),3),E_caso_R=round(((rq-cq)/s).mean(),3)))
    R=pd.DataFrame(rows).pivot_table(index=["SL","TP"],columns="per",values=["n","mese","win","win_caso","E_lordo_R","E_netto_R","E_caso_R"])
    print(f"\n### {label}"); print(R.round(3).to_string())
geoms_c=[(1,1),(1.5,1.5),(2,2),(3,3),(2,3),(3,1.5),(1.5,3)]
geoms_s=[(0.5,0.5),(1,1),(1.5,1.5),(2,2),(3,3)]
for tf in [15,30]:
    P=(D.kind=="pattern")&(D.tf==tf); Q=(D.kind=="casuale")&(D.tf==tf)
    clean=P&(D.exp<=2)&(D.rsi_dir<=60)&(~D.brk)&(D.vr<=1.5)
    table(clean,Q,False,geoms_c,f"A) CONTINUAZIONE 'PULITA' M{tf}: espansione 1.5-2x, RSI in direzione <=60, nessuna rottura del range 32, volume <=1.5x")
for tf in [5,15,30]:
    P=(D.kind=="pattern")&(D.tf==tf); Q=(D.kind=="casuale")&(D.tf==tf)
    exh=P&((D.exp>3)|(D.rsi_dir>75)|(D.vr>3))
    table(exh,Q,True,geoms_s,f"B) CONTRO L'ESAURIMENTO M{tf}: espansione >3x o RSI in direzione >75 o volume >3x -> si entra CONTRO")
    exh2=P&(D.exp>3)&(D.rsi_dir>75)
    table(exh2,Q,True,geoms_s,f"B2) ESAURIMENTO FORTE M{tf}: espansione >3x E RSI >75 -> CONTRO")
