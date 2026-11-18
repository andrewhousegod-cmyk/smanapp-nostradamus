import pandas as pd, glob, sys
S="data/Touhid-HZ_xauusd-tick-data-2026/data/tick/"
out=[]
for f in sorted(glob.glob(S+"*.csv.gz")):
    t=pd.read_csv(f,usecols=['timestamp','ask','bid'])
    t['timestamp']=pd.to_datetime(t['timestamp'],utc=True)
    t=t.set_index('timestamp'); t['spr']=t.ask-t.bid
    g=t.resample('1min')
    b=pd.DataFrame({'open':g.bid.first(),'high':g.bid.max(),'low':g.bid.min(),'close':g.bid.last(),
                    'ask_high':g.ask.max(),'ask_low':g.ask.min(),'tick_volume':g.bid.count(),'spread':g.spr.mean(),'spread_max':g.spr.max()}).dropna()
    out.append(b); print(f[-20:],len(t),len(b),file=sys.stderr)
m=pd.concat(out); m=m[~m.index.duplicated()].sort_index()
m.to_parquet("work/duka_m1.parquet"); print(m.index.min(),m.index.max(),len(m)); print(m.describe().T[['mean','50%','max']])
