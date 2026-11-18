"""Same entries, different trade management. R = initial risk |E-SL| per unit.
Conservative M1 path: in each M1 bar the stop (set from previous bars) is checked before
favourable extremes are used; new trailing levels apply from the next bar."""
import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from engine import P, run
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
e["spr"]=0.20
H,L,C=e.high.values,e.low.values,e.close.values; idx={t:i for i,t in enumerate(e.index.values)}
PESS=True
COSTU=0.20+0.10+0.054          # per unit round trip: spread + 2x slippage + commission ($/oz)
SCHEMES=["TP2R","BE1R_TP3R","PARZ50@1R+trail","TRAIL1R","TRAIL2R","PIRAMIDE+1R"]
def sim(k0,kend,d,E,R,sch):
    best=E; sl=E-d*R; units=[(E,1.0)]; banked=0.0; added=False; armed=False
    tp={"TP1R":1,"TP1.5R":1.5,"TP2R":2,"TP3R":3,"BE1R_TP3R":3}.get(sch)
    for k in range(k0,kend):
        hi,lo=(H[k],L[k]) if d==1 else (-L[k],-H[k])   # mirror sells
        s=d*sl; b=d*best
        if lo<=s or (k==k0 and False):
            return banked+sum(w*(s-d*u) for u,w in units)/R, sum(w for _,w in units)+(0.5 if sch.startswith("PARZ") and armed else 0)
        if tp and hi>=d*E+tp*R and k>k0:
            return banked+tp, 1.0
        nb=max(b,hi); best=d*nb; prof=(nb-d*E)/R
        if sch=="BE1R_TP3R" and prof>=1: sl=E
        if sch=="PARZ50@1R+trail":
            if not armed and prof>=1 and k>k0: banked+=0.5*1.0; units=[(E,0.5)]; armed=True; sl=E
            if armed: sl=d*max(d*sl, nb-1.0*R)
        if sch=="TRAIL1R": sl=d*max(d*sl, nb-1.0*R)
        if sch=="TRAIL2R" : sl=d*max(d*sl, nb-2.0*R) if prof>=1 else sl
        if sch=="PIRAMIDE+1R":
            if not added and prof>=1 and k>k0: units=[(E,1.0),(E+d*R,1.0)]; added=True; sl=E
            if added: sl=d*max(d*sl, nb-1.0*R)
        if PESS and lo<=d*sl and d*sl>s:
            return banked+sum(w*(d*sl-d*u) for u,w in units)/R, sum(w for _,w in units)+(0.5 if sch.startswith("PARZ") and armed else 0)
    k=kend-1; px=C[k]
    return banked+sum(w*d*(px-u) for u,w in units)/R, sum(w for _,w in units)+(0.5 if sch.startswith("PARZ") and armed else 0)
rows=[]
for setup,p in [("pattern utente",P()),("scala screenshot",P(DON=32,ALIGN=True,USEQUIET=False))]:
    for tf in [1,3,5,15,30]:
        g=run(e,tf,p,cost=False); t=g[g.status=="triggered"]
        recs=[]
        for r in t.itertuples():
            d=r.dir; E=(r.tp+2*r.sl)/3; R=abs(E-r.sl); k0=idx[np.datetime64(r.t_in)]
            kend=min(len(e),k0+48*tf); yr=pd.Timestamp(r.t_in).year
            for sch in SCHEMES:
                Rg,u=sim(k0,kend,d,E,R,sch); recs.append((sch,yr<=2022,Rg,Rg-u*COSTU/R))
        df=pd.DataFrame(recs,columns=["sch","IS","lordo","netto"])
        for (sch,isv),gg in df.groupby(["sch","IS"],sort=False):
            rows.append(dict(setup=setup,TF=f"M{tf}",schema=sch,per="IS" if isv else "OOS",n=len(gg),
              win=round(100*(gg.netto>0).mean()),lordo=round(gg.lordo.mean(),3),netto=round(gg.netto.mean(),3),
              t_lordo=round(gg.lordo.mean()/(gg.lordo.std()/np.sqrt(len(gg))),1)))
R=pd.DataFrame(rows); R.to_csv("manage_pess.csv",index=False)
pv=R.pivot_table(index=["setup","TF","schema"],columns="per",values=["lordo","netto","t_lordo"],sort=False)
pd.set_option("display.width",250); pd.set_option("display.max_rows",200); print(pv.round(3).to_string())
