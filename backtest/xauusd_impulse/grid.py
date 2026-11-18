"""Systematic intraday grid for the impulse family on XAUUSD.
Setups x entries x exits x session x year, aggregated stats. Flat by 20:45 UTC, no entries after 20:00 UTC.
Execution on M1 path; stop updates apply from next bar (validated vs 1s ticks); SL before TP in same bar."""
import numpy as np, pandas as pd, numba as nb, sys, itertools, time
sys.path.insert(0, '.')
from engine import make_tf

ENTRIES = ["breakout", "market", "pullback", "fade"]
EXITS = ["TP1R", "TP2R", "TP3R", "TRAIL1R", "PARZ+BE+TRAIL", "TIME12"]
SESS = ["Asia", "Londra", "NY", "Sera"]
BUF = 0.05

def load(src):
    if src == "exness":
        m = pd.read_parquet("../data/sherwynjoel_xauusd-historical-data/xauusd_m1_full.parquet")
        m["spr"] = np.maximum(m.spread / 1000.0, 0.20)
    else:
        m = pd.read_parquet("duka_m1.parquet"); m = m[m.index >= "2026-08-18"].copy(); m["spr"] = 0.20
    return m

def prep(m):
    t = m.index
    mod = (t.hour * 60 + t.minute).values.astype(np.int64)
    wd = t.dayofweek.values.astype(np.int64)
    yr = t.year.values.astype(np.int64)
    day = (t.normalize().as_unit("ns").asi8 // 86_400_000_000_000).astype(np.int64)
    n = len(m); eod = np.empty(n, np.int64)
    # first index of each day with mod >= 1245, else next day start
    starts = np.r_[0, np.flatnonzero(np.diff(day)) + 1, n]
    for a, z in zip(starts[:-1], starts[1:]):
        w = np.flatnonzero(mod[a:z] >= 1245)
        eod[a:z] = a + w[0] if len(w) else z
    return mod, wd, yr, eod

@nb.njit(cache=True)
def exit_sim(k0, kend, d, E, SL, sch, H, L, C):
    R = abs(E - SL)
    if R <= 0 or k0 >= kend:
        return np.nan
    e = d * E; s = d * SL; best = e; banked = 0.0; w = 1.0; armed = False
    tp = 0.0
    if sch == 0: tp = 1.0
    elif sch == 1: tp = 2.0
    elif sch == 2: tp = 3.0
    for k in range(k0, kend):
        if d == 1:
            hi = H[k]; lo = L[k]
        else:
            hi = -L[k]; lo = -H[k]
        if lo <= s:
            return banked + w * (s - e) / R
        if tp > 0 and k > k0 and hi >= e + tp * R:
            return banked + tp
        if hi > best:
            best = hi
        prof = (best - e) / R
        if sch == 3:
            if best - R > s: s = best - R
        elif sch == 4:
            if (not armed) and prof >= 1.0 and k > k0:
                banked += 0.5; w = 0.5; armed = True
                if e > s: s = e
            if armed and best - R > s: s = best - R
    px = d * C[kend - 1]
    return banked + w * (px - e) / R

@nb.njit(cache=True)
def run_setup(sig, bo, bh, bl, bc, i0, i1, O, H, L, C, S, mod, wd, yr, eod, tf, PMAX, MAXHOLD,
              acc_n, acc_s, acc_s2, acc_w, acc_g, yr0):
    nbars = len(bo)
    for ii in range(len(sig)):
        i = sig[ii]
        if bc[i] == bo[i] or i + 1 >= nbars:
            continue
        d = 1 if bc[i] > bo[i] else -1
        rgi = bh[i] - bl[i]
        for en in range(4):
            k = -1; E = 0.0; SL = 0.0; dd = d; jbar = i + 1; cost_slip = 0.10
            if en == 0:  # pause -> breakout of structure extreme
                hi = bh[i]; lo = bl[i]; c = 0; box = 0.0; j = i + 1; legn = 1; status = 0
                while j < nbars and status == 0:
                    rg = hi - lo
                    lvl = hi if d == 1 else lo
                    inv = lo + 0.5 * rg if d == 1 else hi - 0.5 * rg
                    if c < 1:
                        if (d == 1 and bl[j] <= inv) or (d == -1 and bh[j] >= inv):
                            status = 2; break
                        cb = bc[j] > lvl if d == 1 else bc[j] < lvl
                        if cb:
                            if legn < 4:
                                if bh[j] > hi: hi = bh[j]
                                if bl[j] < lo: lo = bl[j]
                                legn += 1; j += 1; continue
                            status = 2; break
                        if d == 1:
                            if bh[j] > hi: hi = bh[j]
                            box = bl[j]
                        else:
                            if bl[j] < lo: lo = bl[j]
                            box = bh[j]
                        c += 1; j += 1; continue
                    if c >= PMAX:
                        status = 2; break
                    Ee = lvl + d * BUF
                    for kk in range(i0[j], i1[j]):
                        if d == 1:
                            if L[kk] <= inv: status = 2; break
                            if H[kk] >= Ee: k = kk; status = 1; break
                        else:
                            if H[kk] >= inv: status = 2; break
                            if L[kk] <= Ee: k = kk; status = 1; break
                    if status == 0:
                        if d == 1:
                            if bl[j] < box: box = bl[j]
                        else:
                            if bh[j] > box: box = bh[j]
                        c += 1; j += 1
                if status != 1:
                    continue
                E = lvl + d * BUF; SL = box - d * BUF; jbar = j
            elif en == 1:  # market at next bar open, SL at impulse midpoint
                k = i1[i]; E = O[k] if k < len(O) else 0.0
                SL = (bh[i] + bl[i]) / 2 - d * BUF
            elif en == 2:  # limit at 50% retrace inside the pause, SL beyond impulse origin
                lim = (bh[i] + bl[i]) / 2
                kend_w = i1[min(nbars - 1, i + PMAX)]
                for kk in range(i1[i], kend_w):
                    if (d == 1 and L[kk] <= lim) or (d == -1 and H[kk] >= lim):
                        k = kk; break
                if k < 0:
                    continue
                E = lim; SL = (bl[i] - BUF) if d == 1 else (bh[i] + BUF); cost_slip = 0.05
            else:  # fade: against the impulse at next open, SL beyond impulse extreme + 25% range
                dd = -d; k = i1[i]; E = O[k] if k < len(O) else 0.0
                SL = (bh[i] + 0.25 * rgi) if d == 1 else (bl[i] - 0.25 * rgi)
            if k < 0 or k >= len(O):
                continue
            if mod[k] >= 1200 or wd[k] >= 5 or eod[k] <= k:
                continue
            R = abs(E - SL)
            if R <= 0.05 or (dd == 1 and SL >= E) or (dd == -1 and SL <= E):
                continue
            hold = i1[min(nbars - 1, jbar + MAXHOLD)]
            kend = min(eod[k], hold)
            m = mod[k]
            ss = 0 if (m < 360 or m >= 1320) else (1 if m < 720 else (2 if m < 1020 else 3))
            y = yr[k] - yr0
            cost = (S[k] + cost_slip + 0.054) / R
            for ex in range(6):
                ke = kend
                if ex == 5:
                    ke = min(kend, k + 12 * tf)
                g = exit_sim(k, ke, dd, E, SL, 5 if ex == 5 else ex, H, L, C)
                if np.isnan(g):
                    continue
                r = g - cost
                acc_n[en, ex, y, ss] += 1; acc_s[en, ex, y, ss] += r; acc_s2[en, ex, y, ss] += r * r
                acc_g[en, ex, y, ss] += g
                if r > 0: acc_w[en, ex, y, ss] += 1

@nb.njit(cache=True)
def run_setup_rec(sig, bo, bh, bl, bc, i0, i1, O, H, L, C, S, mod, wd, yr, eod, tf, PMAX, MAXHOLD,
              rec_k, rec_en, rec_ex, rec_r, rec_g, rec_R, cnt):
    nbars = len(bo)
    for ii in range(len(sig)):
        i = sig[ii]
        if bc[i] == bo[i] or i + 1 >= nbars:
            continue
        d = 1 if bc[i] > bo[i] else -1
        rgi = bh[i] - bl[i]
        for en in range(4):
            k = -1; E = 0.0; SL = 0.0; dd = d; jbar = i + 1; cost_slip = 0.10
            if en == 0:  # pause -> breakout of structure extreme
                hi = bh[i]; lo = bl[i]; c = 0; box = 0.0; j = i + 1; legn = 1; status = 0
                while j < nbars and status == 0:
                    rg = hi - lo
                    lvl = hi if d == 1 else lo
                    inv = lo + 0.5 * rg if d == 1 else hi - 0.5 * rg
                    if c < 1:
                        if (d == 1 and bl[j] <= inv) or (d == -1 and bh[j] >= inv):
                            status = 2; break
                        cb = bc[j] > lvl if d == 1 else bc[j] < lvl
                        if cb:
                            if legn < 4:
                                if bh[j] > hi: hi = bh[j]
                                if bl[j] < lo: lo = bl[j]
                                legn += 1; j += 1; continue
                            status = 2; break
                        if d == 1:
                            if bh[j] > hi: hi = bh[j]
                            box = bl[j]
                        else:
                            if bl[j] < lo: lo = bl[j]
                            box = bh[j]
                        c += 1; j += 1; continue
                    if c >= PMAX:
                        status = 2; break
                    Ee = lvl + d * BUF
                    for kk in range(i0[j], i1[j]):
                        if d == 1:
                            if L[kk] <= inv: status = 2; break
                            if H[kk] >= Ee: k = kk; status = 1; break
                        else:
                            if H[kk] >= inv: status = 2; break
                            if L[kk] <= Ee: k = kk; status = 1; break
                    if status == 0:
                        if d == 1:
                            if bl[j] < box: box = bl[j]
                        else:
                            if bh[j] > box: box = bh[j]
                        c += 1; j += 1
                if status != 1:
                    continue
                E = lvl + d * BUF; SL = box - d * BUF; jbar = j
            elif en == 1:  # market at next bar open, SL at impulse midpoint
                k = i1[i]; E = O[k] if k < len(O) else 0.0
                SL = (bh[i] + bl[i]) / 2 - d * BUF
            elif en == 2:  # limit at 50% retrace inside the pause, SL beyond impulse origin
                lim = (bh[i] + bl[i]) / 2
                kend_w = i1[min(nbars - 1, i + PMAX)]
                for kk in range(i1[i], kend_w):
                    if (d == 1 and L[kk] <= lim) or (d == -1 and H[kk] >= lim):
                        k = kk; break
                if k < 0:
                    continue
                E = lim; SL = (bl[i] - BUF) if d == 1 else (bh[i] + BUF); cost_slip = 0.05
            else:  # fade: against the impulse at next open, SL beyond impulse extreme + 25% range
                dd = -d; k = i1[i]; E = O[k] if k < len(O) else 0.0
                SL = (bh[i] + 0.25 * rgi) if d == 1 else (bl[i] - 0.25 * rgi)
            if k < 0 or k >= len(O):
                continue
            if mod[k] >= 1200 or wd[k] >= 5 or eod[k] <= k:
                continue
            R = abs(E - SL)
            if R <= 0.05 or (dd == 1 and SL >= E) or (dd == -1 and SL <= E):
                continue
            hold = i1[min(nbars - 1, jbar + MAXHOLD)]
            kend = min(eod[k], hold)
            m = mod[k]
            ss = 0 if (m < 360 or m >= 1320) else (1 if m < 720 else (2 if m < 1020 else 3))
            cost = (S[k] + cost_slip + 0.054) / R
            for ex in range(6):
                ke = kend
                if ex == 5:
                    ke = min(kend, k + 12 * tf)
                g = exit_sim(k, ke, dd, E, SL, 5 if ex == 5 else ex, H, L, C)
                if np.isnan(g):
                    continue
                r = g - cost
                c_ = cnt[0]
                if c_ < len(rec_k):
                    rec_k[c_] = k; rec_en[c_] = en; rec_ex[c_] = ex; rec_r[c_] = r; rec_g[c_] = g; rec_R[c_] = R
                    cnt[0] = c_ + 1

def setups_for(b):
    rng = (b.high - b.low).values; body = (b.close - b.open).values
    ar = pd.Series(rng).shift(1).rolling(20).mean().values
    av = pd.Series(b.vol.values).shift(1).rolling(20).mean().values
    mx = pd.Series(rng).shift(1).rolling(20).max().values
    dh = pd.Series(b.high.values).shift(1).rolling(32).max().values
    dl = pd.Series(b.low.values).shift(1).rolling(32).min().values
    ema = b.close.ewm(span=200, adjust=False).mean().values
    c = b.close.values; up = body > 0
    with np.errstate(invalid="ignore", divide="ignore"):
        dirn = np.abs(body) / np.where(rng > 0, rng, np.nan)
        ctx = {"quiet": mx < 2 * ar, "don32": np.where(up, c > dh, c < dl),
               "ema": np.where(up, c > ema, c < ema)}
        ctx["don32+ema"] = ctx["don32"] & ctx["ema"]
        out = {}
        for KR, KV, cx in itertools.product([1.5, 2.0, 3.0], [1.0, 1.5, 2.0], ctx):
            s = (rng >= KR * ar) & (b.vol.values >= KV * av) & (dirn >= 0.6) & ctx[cx]
            out[(KR, KV, cx)] = np.flatnonzero(s).astype(np.int64)
    return out

def main(src):
    m = load(src); mod, wd, yr, eod = prep(m)
    O, H, L, C, S = (m[x].values.astype(np.float64) for x in ("open", "high", "low", "close", "spr"))
    yr0 = int(yr.min()); ny = int(yr.max()) - yr0 + 1
    rows = []
    for tf in [1, 3, 5, 15, 30]:
        t0 = time.time()
        b = make_tf(m, tf); st = setups_for(b)
        bo, bh, bl, bc = (b[x].values.astype(np.float64) for x in ("open", "high", "low", "close"))
        i0, i1 = b.i0.values.astype(np.int64), b.i1.values.astype(np.int64)
        for key, sig in st.items():
            sh = (4, 6, ny, 4)
            A = [np.zeros(sh) for _ in range(5)]
            run_setup(sig, bo, bh, bl, bc, i0, i1, O, H, L, C, S, mod, wd, yr, eod, tf, 8, 48, *A, yr0)
            n, s, s2, w, g = A
            for en, ex, y, ss in zip(*np.nonzero(n)):
                rows.append((f"M{tf}", key[0], key[1], key[2], ENTRIES[en], EXITS[ex], yr0 + y, SESS[ss],
                             n[en, ex, y, ss], s[en, ex, y, ss], s2[en, ex, y, ss], w[en, ex, y, ss], g[en, ex, y, ss]))
        print(f"M{tf} done {time.time()-t0:.0f}s", file=sys.stderr)
    df = pd.DataFrame(rows, columns=["TF", "KR", "KV", "ctx", "entry", "exit", "year", "sess", "n", "sum", "sum2", "wins", "gsum"])
    df.to_parquet(f"grid_{src}.parquet"); print(len(df), "rows")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "exness")
