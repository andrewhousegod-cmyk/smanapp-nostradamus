import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from engine import P, run
m1=pd.read_parquet("duka_m1.parquet"); m1["spr"]=0.0
s1=pd.read_parquet("duka_s1.parquet")
SCH=["TP2R","BE1R_TP3R","PARZ50@1R+trail","TRAIL1R","TRAIL2R","PIRAMIDE+1R"]
def sim(H,L,C,k0,kend,d,E,R,sch,pess):
    best=E; sl=E-d*R; units=[(E,1.0)]; banked=0.0; added=False; armed=False
    tp={"TP2R":2,"BE1R_TP3R":3}.get(sch)
    for k in range(k0,kend):
        hi,lo=(H[k],L[k]) if d==1 else (-L[k],-H[k]); s=d*sl; b=d*best
        if lo<=s: return banked+sum(w*(s-d*u) for u,w in units)/R
        if tp and hi>=d*E+tp*R: return banked+tp
        nb=max(b,hi); best=d*nb; prof=(nb-d*E)/R
        if sch=="BE1R_TP3R" and prof>=1: sl=E
        if sch=="PARZ50@1R+trail":
            if not armed and prof>=1: banked+=0.5; units=[(E,0.5)]; armed=True; sl=E
            if armed: sl=d*max(d*sl,nb-R)
        if sch=="TRAIL1R": sl=d*max(d*sl,nb-R)
        if sch=="TRAIL2R" and prof>=1: sl=d*max(d*sl,nb-2*R)
        if sch=="PIRAMIDE+1R":
            if not added and prof>=1: units=[(E,1.0),(E+d*R,1.0)]; added=True; sl=E
            if added: sl=d*max(d*sl,nb-R)
        if pess and lo<=d*sl and d*sl>s: return banked+sum(w*(d*sl-d*u) for u,w in units)/R
    return banked+sum(w*d*(C[kend-1]-u) for u,w in units)/R
MH,ML,MC=m1.high.values,m1.low.values,m1.close.values; mt=m1.index.values
SH,SL_,SC=s1.high.values.astype(float),s1.low.values.astype(float),s1.close.values.astype(float); st=s1.index.values
rows=[]
for setup,p in [("pattern utente",P()),("scala screenshot",P(DON=32,ALIGN=True,USEQUIET=False))]:
    for tf in [1,3,5,15]:
        g=run(m1,tf,p,cost=False); t=g[g.status=="triggered"]
        for r in t.itertuples():
            d=r.dir; E=(r.tp+2*r.sl)/3; R=abs(E-r.sl); tin=np.datetime64(r.t_in)
            k0=np.searchsorted(mt,tin); ke=min(len(mt),k0+48*tf)
            a=np.searchsorted(st,tin); b_=np.searchsorted(st,tin+np.timedelta64(60,'s'))
            seg=SH[a:b_]>=E if d==1 else SL_[a:b_]<=E
            if not seg.any(): continue
            s0=a+np.argmax(seg); se=np.searchsorted(st,mt[ke-1]+np.timedelta64(60,'s'))
            for sch in SCH:
                rows.append(dict(setup=setup,TF=f"M{tf}",sch=sch,
                  M1_ottim=sim(MH,ML,MC,k0+1,ke,d,E,R,sch,False),M1_pess=sim(MH,ML,MC,k0+1,ke,d,E,R,sch,True),
                  tick_1s=sim(SH,SL_,SC,s0+1,se,d,E,R,sch,True)))
df=pd.DataFrame(rows)
o=df.groupby(["setup","TF","sch"],sort=False).agg(n=("tick_1s","size"),M1_ottim=("M1_ottim","mean"),M1_pess=("M1_pess","mean"),tick_1s=("tick_1s","mean"),sd=("tick_1s","std"))
o["t_tick"]=o.tick_1s/(o.sd/np.sqrt(o.n)); pd.set_option("display.width",200); pd.set_option("display.max_rows",100)
print("R lordo medio, stessi trade (lug-nov 2026), 3 risoluzioni"); print(o.drop(columns="sd").round(3).to_string())
