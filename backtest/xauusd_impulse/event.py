import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from engine import make_tf
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
COST=0.20+0.054+0.10   # spread + commission per oz-equivalent ($5.40/lot/100oz) + 2x slippage, in $
H=[1,3,6,12,24,48]
rows=[]
for tf in [1,3,5,15,30]:
    b=make_tf(e,tf); rng=(b.high-b.low); ar=rng.shift(1).rolling(20).mean(); av=b.vol.shift(1).rolling(20).mean()
    mx=rng.shift(1).rolling(20).max(); body=(b.close-b.open); dirn=body.abs()/rng.replace(0,np.nan); d=np.sign(body)
    yr=b.index.year
    variants={
      "impulso utente (2x rng,1.5x vol,primo)": (rng>=2*ar)&(b.vol>=1.5*av)&(dirn>=.6)&(mx<2*ar),
      "impulso forte (3x rng)":                 (rng>=3*ar)&(dirn>=.6),
      "impulso qualsiasi (2x rng)":             (rng>=2*ar)&(dirn>=.6),
      "volume alto senza range (vol>=2x, rng<1.2x)": (b.vol>=2*av)&(rng<1.2*ar)&(dirn>=.6),
    }
    for name,sig in variants.items():
        sig=sig.fillna(False).values
        for per,msk in [("IS",yr<=2022),("OOS",yr>=2023)]:
            idx=np.flatnonzero(sig & msk)
            r=dict(TF=f"M{tf}",segnale=name,per=per,n=len(idx))
            c=b.close.values; arv=ar.values
            for h in H:
                ok=idx[idx+h<len(c)]
                fr=d.values[ok]*(c[ok+h]-c[ok])          # $ move in impulse direction, entry at impulse close
                r[f"h{h}"]=round(fr.mean(),3); r[f"t{h}"]=round(fr.mean()/(fr.std()/np.sqrt(len(fr))),1) if len(fr)>2 else np.nan
            r["costo$"]=COST; r["avgrng$"]=round(np.nanmedian(arv[idx]),2)
            rows.append(r)
R=pd.DataFrame(rows)
print("Deriva media in $ nella direzione dell'impulso dopo h barre (ingresso a chiusura impulso). t = t-stat. Costo round-turn ~",COST,"$")
print(R[["TF","segnale","per","n","avgrng$"]+[f"h{h}" for h in H]+[f"t{h}" for h in H]].to_string(index=False))
R.to_csv("event_study.csv",index=False)
