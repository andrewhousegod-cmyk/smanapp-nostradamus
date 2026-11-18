import pandas as pd, numpy as np, sys
sys.path.insert(0,'.'); from grid import *
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
def trades(src):
    m=load(src); mod,wd,yr,eod=prep(m)
    O,H,L,C,S=(m[x].values.astype(np.float64) for x in ("open","high","low","close","spr"))
    # ex-ante regime: previous day range vs its 20-day average (known before the session)
    dr=(m.high.resample("1D").max()-m.low.resample("1D").min()).dropna(); dr.index=dr.index.tz_localize(None) if dr.index.tz else dr.index
    reg=(dr/dr.rolling(20).mean()).shift(1)
    out=[]
    for tf in [15,30]:
        b=make_tf(m,tf); st=setups_for(b)
        bo,bh,bl,bc=(b[x].values.astype(np.float64) for x in ("open","high","low","close")); i0,i1=b.i0.values.astype(np.int64),b.i1.values.astype(np.int64)
        for key,sig in st.items():
            N=len(sig)*24+10; A=[np.zeros(N,np.int64),np.zeros(N,np.int64),np.zeros(N,np.int64),np.zeros(N),np.zeros(N),np.zeros(N),np.zeros(1,np.int64)]
            run_setup_rec(sig,bo,bh,bl,bc,i0,i1,O,H,L,C,S,mod,wd,yr,eod,tf,8,48,*A)
            c=A[6][0]
            d=pd.DataFrame({"k":A[0][:c],"entry":np.array(ENTRIES)[A[1][:c]],"exit":np.array(EXITS)[A[2][:c]],"r":A[3][:c],"g":A[4][:c],"R$":A[5][:c]})
            d["TF"]=f"M{tf}"; d["KR"],d["KV"],d["ctx"]=key; out.append(d)
    T=pd.concat(out); T["t"]=m.index.values[T.k.values]; T["mod"]=mod[T.k.values]; T["year"]=yr[T.k.values]
    T["day"]=pd.to_datetime(T.t).dt.tz_localize(None).dt.normalize() if pd.to_datetime(T.t).dt.tz is not None else pd.to_datetime(T.t).dt.normalize()
    T["reg"]=T.day.map(reg); T["dow"]=pd.to_datetime(T.t).dt.dayofweek
    return T
T=trades("exness"); T.to_parquet("family_exness.parquet")
F=T[(T.entry=="breakout")&(T["mod"]>=720)&(T["mod"]<1020)&(T.exit.isin(["TP3R","PARZ+BE+TRAIL","TIME12"]))]
print("FAMIGLIA: M15/M30, breakout, NY 12-17 UTC, uscite TP3R/PARZ/TIME12, tutte le 36 definizioni di setup -> media per trade (R netto)")
print(F.groupby(["year","TF"]).r.agg(["size","mean"]).round(3).unstack().to_string())
print("\nPer regime di volatilita' del giorno prima (range ieri / media 20gg):")
F=F.assign(regq=pd.cut(F.reg,[0,0.8,1.0,1.25,10],labels=["<0.8","0.8-1","1-1.25",">1.25"]))
print(F.groupby(["regq",F.year>=2023],observed=True).r.agg(["size","mean"]).round(3).unstack().to_string())
print("\nPer giorno della settimana:"); print(F.groupby(["dow",F.year>=2023]).r.agg(["size","mean"]).round(3).unstack().to_string())
print("\nPer ora d'ingresso UTC:"); print(F.groupby([F["mod"]//60,F.year>=2023]).r.agg(["size","mean"]).round(3).unstack().to_string())
