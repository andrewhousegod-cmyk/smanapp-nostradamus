import pandas as pd, glob
S="../data/Touhid-HZ_xauusd-tick-data-2026/data/tick/"
out=[]
for f in sorted(glob.glob(S+"*.csv.gz")):
    t=pd.read_csv(f,usecols=['timestamp','bid'],engine="c"); t['timestamp']=pd.to_datetime(t['timestamp'],utc=True)
    g=t.set_index('timestamp').bid.resample('1s'); b=pd.DataFrame({'high':g.max(),'low':g.min(),'close':g.last()}).dropna(); out.append(b.astype('float32'))
pd.concat(out).sort_index().to_parquet("duka_s1.parquet"); print(sum(len(x) for x in out))
