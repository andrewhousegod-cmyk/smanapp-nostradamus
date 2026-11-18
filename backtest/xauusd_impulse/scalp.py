"""Scalping box-breakout study on XAUUSD (1 pip = 0.10 $).
Lateral box of N bars on base TF, compressed (height <= K * avg bar range of last 100 bars * sqrt(N)/2),
breakout bar closes outside the box with range >= 1.5x avg and tick volume >= 1.5x avg.
Market entry at next M1 open. SL = box midpoint (variant: box opposite side).
Measures frequency, $-excursions before SL vs random-walk expectation, and the 6-order ladder.
Flat by 20:45 UTC, max hold 4h, no entries 20:00-24:00 UTC, NFP Fridays 12:00-15:00 UTC excluded."""
import numpy as np, pandas as pd, numba as nb, sys
sys.path.insert(0, '.'); from engine import make_tf; from grid import load, prep
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
LEVELS = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
COST = 0.354

@nb.njit(cache=True)
def path(k0, kend, d, E, SL, H, L, C, levels, be_after, rladder, S, trail, pess):
    """returns (hit flags for each level before SL (no BE), ladder R gross)."""
    R = abs(E - SL); e = d * E; s0 = d * SL
    nl = len(levels)
    hit = np.zeros(nl)
    tps = np.empty(nl)
    for i in range(nl):
        tps[i] = e + (levels[i] * R if rladder else levels[i])
    # 1) excursion flags (pure: SL fixed)
    best = e
    for k in range(k0, kend):
        hi = H[k] if d == 1 else -L[k]; lo = L[k] if d == 1 else -H[k]
        if lo <= s0: break
        if k > k0 and hi > best: best = hi
    for i in range(nl):
        if best >= tps[i]: hit[i] = 1.0
    # 2) ladder: orders 0..nl-1 at tps, order nl = runner trailing 'trail' $ after first TP
    s = s0; open_ = np.ones(nl + 1); pnl = 0.0; ntp = 0; rbest = e; rs = s0
    for k in range(k0, kend):
        hi = H[k] if d == 1 else -L[k]; lo = L[k] if d == 1 else -H[k]
        # stop check (all open fixed orders share s; runner uses rs)
        if lo <= s:
            for i in range(nl):
                if open_[i] == 1.0: pnl += (s - e); open_[i] = 0.0
        if open_[nl] == 1.0 and lo <= rs:
            pnl += (rs - e); open_[nl] = 0.0
        if open_.sum() == 0: break
        if k == k0: continue
        for i in range(nl):
            if open_[i] == 1.0 and hi >= tps[i]:
                pnl += tps[i] - e; open_[i] = 0.0; ntp += 1
        if hi > rbest: rbest = hi
        if be_after > 0 and ntp >= be_after and s < e: s = e
        if ntp >= 1:
            if rs < s: rs = s
            if rbest - trail > rs: rs = rbest - trail
        if pess:  # same-bar adverse after updates
            if lo <= s:
                for i in range(nl):
                    if open_[i] == 1.0: pnl += (s - e); open_[i] = 0.0
            if open_[nl] == 1.0 and lo <= rs:
                pnl += (rs - e); open_[nl] = 0.0
    px = d * C[kend - 1]
    for i in range(nl + 1):
        if open_[i] == 1.0: pnl += px - e
    return hit, pnl / (nl + 1) / R

def setups(m, tf, N, K, sl_mode):
    b = make_tf(m, tf)
    rng = (b.high - b.low); a100 = rng.shift(1).rolling(100).mean(); a20 = rng.shift(1).rolling(20).mean()
    v20 = b.vol.shift(1).rolling(20).mean()
    bh = b.high.shift(1).rolling(N).max(); bl = b.low.shift(1).rolling(N).min(); hgt = bh - bl
    comp = hgt <= K * a100 * np.sqrt(N) / 2
    up = b.close > bh; dn = b.close < bl
    sig = comp & (up | dn) & (rng >= 1.5 * a20) & (b.vol >= 1.5 * v20)
    idx = np.flatnonzero(sig.values)
    d = np.where(up.values[idx], 1, -1)
    mid = ((bh + bl) / 2).values[idx]
    opp = np.where(d == 1, bl.values[idx], bh.values[idx])
    SL = mid if sl_mode == "mid" else opp
    k = b.i1.values[idx]
    return k, d, SL, hgt.values[idx], (rng / a20).values[idx], (b.vol / v20).values[idx]

def run(src="exness", pess=False):
    m = load(src); mod, wd, yr, eod = prep(m)
    O, H, L, C = (m[x].values.astype(np.float64) for x in ("open", "high", "low", "close"))
    t = m.index
    nfp = np.zeros(len(m), bool)
    fri = (t.dayofweek == 4) & (t.day <= 7) & (mod >= 720) & (mod < 900); nfp[fri] = True
    days = len(np.unique(t.normalize()[wd < 5]))
    rows = []
    for tf, N in [(1, 30), (1, 60), (3, 20), (5, 12), (5, 24)]:
        for K in [2.0, 3.0]:
            for slm in ["mid", "opp"]:
                k, d, SL, hgt, spd, vr = setups(m, tf, N, K, slm)
                for j in range(len(k)):
                    kk = k[j]
                    if kk >= len(O) or mod[kk] >= 1200 or wd[kk] >= 5 or eod[kk] <= kk or nfp[kk]:
                        continue
                    E = O[kk]; R = abs(E - SL[j])
                    if R < 1.0 or R > 12.0 or (d[j] == 1 and SL[j] >= E) or (d[j] == -1 and SL[j] <= E):
                        continue
                    kend = min(eod[kk], kk + 240)
                    rec = dict(tf=tf, N=N, K=K, sl=slm, k=kk, d=d[j], R=R, year=yr[kk], hour=mod[kk] // 60, spd=spd[j], vr=vr[j])
                    for lad, rl in [("$2-10", False), ("R0.5-2.5", True)]:
                        lv = LEVELS if not rl else np.array([0.5, 1.0, 1.5, 2.0, 2.5])
                        for be in [0, 1, 2, 3]:
                            hit, g = path(kk + 1, kend, d[j], E, SL[j], H, L, C, lv, be, rl, 0.0, 3.0, pess)
                            rec[f"{lad}|BE{be}"] = g
                        if not rl:
                            for i, lvv in enumerate(LEVELS): rec[f"hit{int(lvv)}"] = hit[i]
                    rows.append(rec)
    df = pd.DataFrame(rows); df["days"] = days
    return df

if __name__ == "__main__":
    pess = len(sys.argv) > 2 and sys.argv[2] == "pess"
    df = run(sys.argv[1] if len(sys.argv) > 1 else "exness", pess)
    df.to_parquet(f"scalp_{sys.argv[1] if len(sys.argv)>1 else 'exness'}{'_pess' if pess else ''}.parquet"); print(len(df))
