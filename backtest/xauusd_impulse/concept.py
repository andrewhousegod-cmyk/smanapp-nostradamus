"""Concept map: compression -> expansion with volume -> direction. Continuous features, all known at bar close.
Outcome: signed move in the impulse direction after h bars (entry at close, no stop), net of 0.354$ cost."""
import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from engine import make_tf
pd.set_option("display.width",250); pd.set_option("display.max_rows",300)
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
COST=0.354; H=12
out=[]
for tf in [1,3,5,15,30]:
    b=make_tf(e,tf); rng=(b.high-b.low); body=b.close-b.open
    a20=rng.shift(1).rolling(20).mean(); a10=rng.shift(1).rolling(10).mean(); a100=rng.shift(1).rolling(100).mean()
    v20=b.vol.shift(1).rolling(20).mean()
    comp=a10/a100                       # <1 = market was compressed (lateral) before the bar
    exp_=rng/a20                        # expansion of this bar
    vr=b.vol/v20
    dh=b.high.shift(1).rolling(32).max(); dl=b.low.shift(1).rolling(32).min()
    d=np.sign(body); brk=np.where(d>0,b.close>dh,b.close<dl)
    fwd=d*(b.close.shift(-H)-b.close)
    hr=b.index.hour
    df=pd.DataFrame({"comp":comp,"exp":exp_,"vr":vr,"brk":brk,"fwd":fwd,"dirn":body.abs()/rng.replace(0,np.nan),
                     "IS":b.index.year<=2022,"sessNY":(hr>=12)&(hr<17),"a20":a20}).dropna()
    df=df[(df.dirn>=0.5)&(df.exp>=1.0)]
    df["compq"]=pd.cut(df.comp,[0,0.7,0.85,1.0,1.2,99],labels=["molto compresso","compresso","normale","attivo","molto attivo"])
    df["expq"]=pd.cut(df.exp,[1,1.5,2,3,99],labels=["1-1.5x","1.5-2x","2-3x",">3x"])
    df["vrq"]=pd.cut(df.vr,[0,1.2,2,99],labels=["vol<1.2","vol1.2-2",">2"])
    df["net"]=df.fwd-COST; df["TF"]=f"M{tf}"
    out.append(df)
D=pd.concat(out)
g=D.groupby(["TF","compq","expq","vrq","brk","IS"],observed=True).agg(n=("net","size"),net=("net","mean"),gross=("fwd","mean"),sd=("net","std"))
g["t"]=g.net/(g.sd/np.sqrt(g.n)); g=g.drop(columns="sd").unstack("IS")
g.columns=[f"{a}_{'IS' if b else 'OOS'}" for a,b in g.columns]
g=g[(g.n_IS>=150)&(g.n_OOS>=100)]
print(f"Celle valutabili: {len(g)}  (soglia multipla ~ |t|>{__import__('scipy').stats.norm.isf(0.025/len(g)):.2f})")
print(f"Celle con NETTO>0 in IS e OOS: {((g.net_IS>0)&(g.net_OOS>0)).sum()}   con LORDO>0 in entrambi: {((g.gross_IS>0)&(g.gross_OOS>0)).sum()} su {len(g)}")
g["minnet"]=g[["net_IS","net_OOS"]].min(axis=1)
print("\nMigliori 20 celle (ordinate per il peggiore dei due periodi):")
print(g.sort_values("minnet",ascending=False).head(20).round(3).to_string())
print("\nMedia lorda (in $) per livello di compressione e TF, solo rotture (brk) con espansione>=2x, IS/OOS:")
x=D[(D.brk)&(D.exp>=2)].groupby(["TF","compq","IS"],observed=True).fwd.agg(["size","mean"]).round(3).unstack("IS"); print(x.to_string())
D.to_parquet("concept.parquet")
