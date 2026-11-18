"""Probability map. Events = directional impulse bars (range >= 1.5x avg20, body >= 60%) on M1..M30.
Entry next M1 open in impulse direction. Geometry in ATR units (ATR = avg range of 20 prior bars of that TF):
SL in {0.5,1,1.5,2,3} ATR, TP in {0.25,0.5,1,1.5,2,3} ATR. Horizon 12 TF bars, flat 20:45 UTC.
Outcome per cell: +TP, -SL or time-exit P&L (ATR). Cost 0.354$ converted to ATR.
Baseline: random bars, same TF and same hour distribution, random direction."""
import numpy as np, pandas as pd, numba as nb, sys
sys.path.insert(0, '.'); from engine import make_tf; from grid import load, prep
SLs = np.array([0.5, 1, 1.5, 2, 3.]); TPs = np.array([0.25, 0.5, 1, 1.5, 2, 3.])

@nb.njit(cache=True)
def cells(k0, kend, d, E, A, H, L, C, SLs, TPs):
    nS = len(SLs); nT = len(TPs); res = np.zeros((nS, nT)); done = np.zeros((nS, nT))
    e = d * E; mae = 0.0; mfe = 0.0
    for k in range(k0, kend):
        hi = ((H[k] if d == 1 else -L[k]) - e) / A; lo = ((L[k] if d == 1 else -H[k]) - e) / A
        if -lo > mae: mae = -lo
        for a in range(nS):
            if mae >= SLs[a]:
                for b in range(nT):
                    if done[a, b] == 0: res[a, b] = -SLs[a]; done[a, b] = 1
        if k > k0 and hi > mfe: mfe = hi
        for b in range(nT):
            if mfe >= TPs[b]:
                for a in range(nS):
                    if done[a, b] == 0: res[a, b] = TPs[b]; done[a, b] = 1
    fin = ((C[kend - 1] if d == 1 else -C[kend - 1]) - e) / A
    for a in range(nS):
        for b in range(nT):
            if done[a, b] == 0: res[a, b] = fin
    return res

def build(src="exness"):
    m = load(src); mod, wd, yr, eod = prep(m)
    O, H, L, C = (m[x].values.astype(np.float64) for x in ("open", "high", "low", "close"))
    t = m.index
    dr = (m.high.resample("1D").max() - m.low.resample("1D").min()).dropna()
    reg = (dr / dr.rolling(20).mean()).shift(1); reg.index = reg.index.normalize()
    recs = []; R = []
    rng_ = np.random.default_rng(7)
    for tf in [1, 3, 5, 15, 30]:
        b = make_tf(m, tf); rg = (b.high - b.low); body = b.close - b.open
        a20 = rg.shift(1).rolling(20).mean(); a10 = rg.shift(1).rolling(10).mean(); a100 = rg.shift(1).rolling(100).mean()
        v20 = b.vol.shift(1).rolling(20).mean(); mx20 = rg.shift(1).rolling(20).max()
        dh = b.high.shift(1).rolling(32).max(); dl = b.low.shift(1).rolling(32).min()
        ema = b.close.ewm(span=200, adjust=False).mean()
        dlt = b.close.diff(); up = dlt.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
        F = pd.DataFrame({"exp": rg / a20, "comp": a10 / a100, "vr": b.vol / v20, "quiet": mx20 < 2 * a20,
                          "dirn": body.abs() / rg.replace(0, np.nan), "d": np.sign(body), "A": a20, "i1": b.i1,
                          "ema": np.sign(b.close - ema), "rsi": rsi,
                          "brk": np.where(body > 0, b.close > dh, b.close < dl)})
        ev = F[(F.exp >= 1.5) & (F.dirn >= 0.6) & F.A.notna() & F.comp.notna()].copy(); ev["kind"] = "pattern"
        # random baseline: sample bars with same hour distribution
        allb = F[F.A.notna() & F.comp.notna()].copy(); allb["h"] = b.index.hour[F.A.notna() & F.comp.notna()]
        evh = b.index.hour[ev.index.map(b.index.get_loc)] if False else pd.Index(b.loc[ev.index].index.hour)
        pick = []
        for h, cnt in pd.Series(evh).value_counts().items():
            pool = allb.index[allb.h == h]; pick.extend(rng_.choice(pool, min(cnt, len(pool)), replace=False))
        rb = F.loc[pick].copy(); rb["d"] = rng_.choice([-1, 1], len(rb)); rb["kind"] = "casuale"
        for df in (ev, rb):
            for idx, r in zip(df.index, df.itertuples()):
                k = int(r.i1)
                if k >= len(O) or mod[k] >= 1200 or wd[k] >= 5 or eod[k] <= k or r.d == 0: continue
                kend = min(eod[k], b.i1.values[min(len(b) - 1, b.index.get_loc(idx) + 12)])
                res = cells(k + 1, kend, int(r.d), O[k], r.A, H, L, C, SLs, TPs)
                R.append(res.ravel())
                al = r.ema * r.d
                recs.append((tf, r.kind, k, yr[k], mod[k] // 60, wd[k], r.exp, r.comp, r.vr, bool(r.quiet), bool(r.brk), al,
                             r.rsi if r.d > 0 else 100 - r.rsi, r.A, 0.354 / r.A, reg.get(t[k].normalize(), np.nan)))
        print(f"M{tf} done", file=sys.stderr)
    D = pd.DataFrame(recs, columns=["tf", "kind", "k", "year", "hour", "dow", "exp", "comp", "vr", "quiet", "brk", "trend", "rsi_dir", "ATR", "costATR", "reg"])
    G = np.array(R)
    D.to_parquet(f"probmap_ev_{src}.parquet"); np.save(f"probmap_res_{src}.npy", G)

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "exness")
