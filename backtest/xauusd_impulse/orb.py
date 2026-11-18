import pandas as pd, numpy as np
e=pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
e["spr"]=np.maximum(e.spread/1000,0.25)   # bar spread is the MIN of the bar -> floor at 0.25
O,H,L,C,S=(e[c].values for c in ["open","high","low","close","spr"]); T=e.index
day=T.normalize(); mins=(T.hour*60+T.minute).values
starts=np.r_[0,np.flatnonzero(day[1:]!=day[:-1])+1, len(e)]
def orb(b0,b1,end,RR,slmode):
    out=[]
    for a,z in zip(starts[:-1],starts[1:]):
        m=mins[a:z]; box=np.flatnonzero((m>=b0)&(m<b1))+a; post=np.flatnonzero((m>=b1)&(m<end))+a
        if len(box)<(b1-b0)*0.8 or len(post)<10: continue
        hi,lo=H[box].max(),L[box].min(); rg=hi-lo
        if rg<=0: continue
        pos=None
        for k in post:
            if pos is None:
                up=H[k]+S[k]>=hi+0.05; dn=L[k]<=lo-0.05
                if up and dn: pos=None; break
                if up: d=1; E=hi+0.05; fill=max(E,O[k]+S[k])+0.05
                elif dn: d=-1; E=lo-0.05; fill=min(E,O[k])-0.05
                else: continue
                sl=(lo-0.05 if d==1 else hi+0.05) if slmode=="box" else E-d*rg/2
                risk=abs(fill-sl)+ (0 if d==1 else S[k]); tp=E+d*RR*abs(E-sl); pos=(d,fill,sl,tp,risk,k); continue
            d,fill,sl,tp,risk,k0=pos
            if d==1:
                if L[k]<=sl: out.append(((sl-0.05-fill)/risk,T[k0])); pos="x"; break
                if H[k]>=tp: out.append(((tp-fill)/risk,T[k0])); pos="x"; break
            else:
                if H[k]+S[k]>=sl: out.append(((fill-sl-0.05)/risk,T[k0])); pos="x"; break
                if L[k]+S[k]<=tp: out.append(((fill-tp)/risk,T[k0])); pos="x"; break
        if isinstance(pos,tuple):
            d,fill,sl,tp,risk,k0=pos; k=post[-1]; px=C[k] if d==1 else C[k]+S[k]; out.append((d*(px-fill)/risk,T[k0]))
    r=pd.DataFrame(out,columns=["R","t"]); r["comm"]=0; return r
for name,b0,b1,end in [("Londra box 07:00-08:00 UTC",420,480,960),("NY box 13:30-14:00 UTC",810,840,1200),("NY box 13:00-14:00 UTC",780,840,1200)]:
    for RR in [1,2]:
        for slm in ["box","half"]:
            r=orb(b0,b1,end,RR,slm); r["IS"]=r.t.dt.year<=2022
            s=" | ".join(f"{'IS' if k else 'OOS'} n={len(g)} win={100*(g.R>0).mean():.0f}% E={g.R.mean():+.3f}R t={g.R.mean()/(g.R.std()/np.sqrt(len(g))):+.1f}" for k,g in r.groupby("IS"))
            print(f"{name} RR={RR} SL={slm:4s} | {s}")
