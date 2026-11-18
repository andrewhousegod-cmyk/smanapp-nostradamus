"""Macro surprise -> gold direction. Pre-registered theory map (no fitting):
actual > forecast = stronger/hawkish US -> gold DOWN (-1); Unemployment Rate higher -> gold UP (+1).
Surprise z = (actual-forecast)/std of PAST surprises of that indicator (expanding, >=12 obs).
Composite per release time S = sum(map * z). Trade gold in sign(S) direction, enter delay min after release
at M1 open, exit after H minutes at M1 close. Costs per oz: 0.50$ and 1.00$ (news spread+slippage+comm)."""
import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd
from grid import load
pd.set_option("display.width",250); pd.set_option("display.max_rows",300)
N=pd.read_parquet("news_us.parquet").dropna(subset=["actual","forecast"]).copy()
N["mapv"]=np.where(N.title.str.contains("Unemployment"),1.0,-1.0)
N["sur"]=N.actual-N.forecast
N["sd"]=N.groupby("title").sur.transform(lambda s: s.abs().expanding().mean().shift(1))  # mean abs past surprise (robust scale)
N["cnt"]=N.groupby("title").cumcount()
N=N[(N.cnt>=12)&(N.sd>0)]
N["z"]=N.sur/N.sd
G=N.groupby("t").apply(lambda g: pd.Series({"S":(g.mapv*g.z).sum(),"titles":"+".join(sorted(set(g.title)))[:60],"nfp":g.title.str.contains("Non Farm").any(),"cpi":g.title.str.contains("Inflation").any(),"fed":g.title.str.contains("Interest Rate").any()})).reset_index()
def run(src):
    m=load(src); idx=m.index; O=m.open.values; C=m.close.values
    out=[]
    for r in G.itertuples():
        for delay in [1,2,5]:
            t_in=r.t+pd.Timedelta(minutes=delay); ki=idx.searchsorted(t_in)
            if ki>=len(idx) or abs((idx[ki]-t_in).total_seconds())>60: continue
            for Hm in [15,30,60,120]:
                ke=idx.searchsorted(t_in+pd.Timedelta(minutes=Hm))-1
                if ke<=ki or ke>=len(idx): continue
                d=np.sign(r.S)
                if d==0: continue
                mv=d*(C[ke]-O[ki])
                pre=C[ki-1]-O[idx.searchsorted(r.t)] if ki>0 else 0.0   # move already done before entry (gold, signed by d)
                out.append((src,r.t,r.t.year,abs(r.S),r.nfp,r.cpi,r.fed,delay,Hm,mv,d*pre))
    return pd.DataFrame(out,columns=["src","t","year","absS","nfp","cpi","fed","delay","H","move","pre"])
A=pd.concat([run("exness"),run("duka")]); A.to_parquet("surprise.parquet")
A["per"]=np.where(A.src=="duka","ago-nov26 (tick)",np.where(A.year<=2022,"2017-22","2023-26"))
A=A[~((A.src=="exness")&(A.t>=pd.Timestamp("2026-08-18",tz="UTC")))]
print("Eventi di rilascio (orari unici) con sorpresa calcolabile:",G.shape[0])
print("\n1) LA DIREZIONE: % di volte che l'oro va nel verso previsto dalla sorpresa (ritardo 1 min)")
x=A[A.delay==1]
for thr in [0,0.5,1,2]:
    y=x[x.absS>=thr]
    t=y.groupby(["per","H"]).move.agg(lambda v: 100*(v>0).mean()).unstack("H").round(1)
    n=y[y.H==30].groupby("per").size()
    print(f"\n|sorpresa| >= {thr}  (eventi: {n.to_dict()})"); print(t.to_string())
print("\n2) TRADE NETTO ($/oncia, media per evento) per ritardo, durata e soglia, costo 0,50$ | 1,00$")
rows=[]
for thr in [0,0.5,1,2]:
    for delay in [1,2,5]:
        for Hm in [15,30,60,120]:
            for per in ["2017-22","2023-26","ago-nov26 (tick)"]:
                v=A[(A.absS>=thr)&(A.delay==delay)&(A.H==Hm)&(A.per==per)].move
                if len(v)<5: continue
                rows.append(dict(soglia=thr,ritardo=delay,durata=Hm,per=per,n=len(v),lordo=v.mean(),t=v.mean()/(v.std()/np.sqrt(len(v))),netto050=v.mean()-0.5,netto100=v.mean()-1.0))
R=pd.DataFrame(rows)
pv=R.pivot_table(index=["soglia","ritardo","durata"],columns="per",values=["n","lordo","t","netto050"]).round(2)
pv["ok"]=np.where((pv[("netto050","2017-22")]>0)&(pv[("netto050","2023-26")]>0)&(pv[("t","2017-22")]>2)&(pv[("t","2023-26")]>2),"<<< SUPERA","")
print(pv.to_string())
print("\n3) Quanto si e' gia' mosso l'oro PRIMA del nostro ingresso (nel verso previsto, $ medi):")
print(A[(A.H==30)].groupby(["delay","per"]).pre.mean().round(2).unstack().to_string())
print("\n4) Per tipo di notizia (ritardo 1 min, durata 30, |S|>=1): % nel verso previsto e $ lordi")
y=A[(A.delay==1)&(A.H==30)&(A.absS>=1)]
for lab,msk in [("NFP",y.nfp),("CPI",y.cpi),("FED tassi",y.fed),("altre",~(y.nfp|y.cpi|y.fed))]:
    z=y[msk]; print(f"  {lab:10s}", z.groupby("per").move.agg(lambda v: f"n={len(v)} giusto={100*(v>0).mean():.0f}% lordo={v.mean():+.2f}$").to_dict())
