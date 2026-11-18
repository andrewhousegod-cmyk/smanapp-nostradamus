"""Full parameter sweep of impulse -> pause -> continuation.
Trade outcome of a candidate impulse bar depends only on the bar + pause params + exit,
so trades are simulated once per (candidate, pause combo) and aggregated into every
filter combo the candidate satisfies. Conservative M1 execution: SL checked first in
each M1 bar; TP never on the entry bar; flat 20:45 UTC; no entries after 20:00 UTC.
Output per TF: arrays n/sum/sum2 indexed by
[pause(24), N(4), quiet(2), KR(5), KV(4), BODY(3), exit(5), year(10), session(4)]."""
import sys, time, numpy as np, pandas as pd, numba as nb
sys.path.insert(0, '.')
from engine import make_tf
from grid import load, prep

NS = [10, 20, 50, 100]; KRS = [1.25, 1.5, 2.0, 2.5, 3.0]; KVS = [0.0, 1.0, 1.5, 2.0]; BODYS = [0.5, 0.6, 0.7]
PAUSE = [(lg, pmin, pmax, rt) for lg in (1, 4) for pmin in (1, 2) for pmax in (4, 8) for rt in (0.382, 0.5, 0.618)]
EXITS = ["TIME6", "TIME12", "TIME24", "TP2R", "TP3R"]
SESS_EDGES = (360, 720, 1020)   # Asia <6, London 6-12, NY 12-17, Late 17-20 (UTC minutes)
BUF = 0.05; SLIP = 0.05; COMM = 0.054

@nb.njit(cache=True)
def sim_one(i, d, legmax, pmin, pmax, retr, bo, bh, bl, bc, i0, i1, O, H, L, C, S, mod, wd, eod, out, DAY):
    """returns entry M1 index (or -1) and fills out[5] with net R for each exit."""
    nb_ = len(bo)
    hi = bh[i]; lo = bl[i]; c = 0; box = 0.0; j = i + 1; legn = 1
    k = -1
    while j < nb_:
        rg = hi - lo
        lvl = hi if d == 1 else lo
        inv = hi - retr * rg if d == 1 else lo + retr * rg
        if c < pmin:
            if (d == 1 and bl[j] <= inv) or (d == -1 and bh[j] >= inv):
                return -1, 0.0
            cb = bc[j] > lvl if d == 1 else bc[j] < lvl
            if cb:
                if c == 0 and legn < legmax:
                    if bh[j] > hi: hi = bh[j]
                    if bl[j] < lo: lo = bl[j]
                    legn += 1; j += 1; continue
                return -1, 0.0
            if d == 1:
                if bh[j] > hi: hi = bh[j]
                box = bl[j] if c == 0 else min(box, bl[j])
            else:
                if bl[j] < lo: lo = bl[j]
                box = bh[j] if c == 0 else max(box, bh[j])
            c += 1; j += 1; continue
        if c >= pmax:
            return -1, 0.0
        E = lvl + d * BUF
        st = 0
        for kk in range(i0[j], i1[j]):
            if d == 1:
                if L[kk] <= inv: st = 2; break
                if H[kk] >= E: k = kk; st = 1; break
            else:
                if H[kk] >= inv: st = 2; break
                if L[kk] <= E: k = kk; st = 1; break
        if st == 2:
            return -1, 0.0
        if st == 1:
            break
        if d == 1:
            if bl[j] < box: box = bl[j]
        else:
            if bh[j] > box: box = bh[j]
        c += 1; j += 1
    if k < 0 or k >= len(O):
        return -1, 0.0
    if wd[k] >= 5:
        return -1, 0.0
    SL = box - d * BUF
    if d == 1:
        fill = max(E, O[k]) + S[k] + SLIP
    else:
        fill = min(E, O[k]) - SLIP
    R = abs(fill - SL) if d == 1 else abs(SL - fill)
    if R <= 0.05:
        return -1, 0.0
    cost_extra = COMM / R   # commission in R; spread/slippage already inside fill / exits
    e = d * fill
    s = d * SL if d == 1 else -SL
    # horizons in M1 indices
    jb = j
    h6 = i1[min(nb_ - 1, jb + 6)]
    h12 = i1[min(nb_ - 1, jb + 12)]
    h24 = i1[min(nb_ - 1, jb + 24)]
    tp2 = e + 2 * R; tp3 = e + 3 * R
    r6 = np.nan; r12 = np.nan; r24 = np.nan; rt2 = np.nan; rt3 = np.nan
    x6 = h6 - 1; x12 = h12 - 1; x24 = h24 - 1; xt2 = h24 - 1; xt3 = h24 - 1
    for kk in range(k, h24):
        if d == 1:
            hi_ = H[kk]; lo_ = L[kk]; cl = C[kk]
        else:
            hi_ = -(L[kk] + S[kk]); lo_ = -(H[kk] + S[kk]); cl = -(C[kk] + S[kk])
        if lo_ <= s:
            ex = (s - SLIP * 1.0 if True else s)
            rr = (ex - e) / R
            if np.isnan(r6):
                r6 = rr; x6 = kk
            if np.isnan(r12):
                r12 = rr; x12 = kk
            if np.isnan(r24):
                r24 = rr; x24 = kk
            if np.isnan(rt2):
                rt2 = rr; xt2 = kk
            if np.isnan(rt3):
                rt3 = rr; xt3 = kk
            break
        if kk > k:
            if np.isnan(rt2) and hi_ >= tp2:
                rt2 = 2.0; xt2 = kk
            if np.isnan(rt3) and hi_ >= tp3:
                rt3 = 3.0; xt3 = kk
        if kk == h6 - 1 and np.isnan(r6): r6 = (cl - e) / R
        if kk == h12 - 1 and np.isnan(r12): r12 = (cl - e) / R
        if kk == h24 - 1:
            if np.isnan(r24): r24 = (cl - e) / R
            if np.isnan(rt2): rt2 = (cl - e) / R
            if np.isnan(rt3): rt3 = (cl - e) / R
    if h24 <= k:
        return -1, 0.0
    if np.isnan(r6): r6 = r24
    if np.isnan(r12): r12 = r24
    sw = fill * 0.05 / 365.0 / R
    out[0] = r6 - cost_extra - sw * (DAY[x6] - DAY[k]); out[1] = r12 - cost_extra - sw * (DAY[x12] - DAY[k]); out[2] = r24 - cost_extra - sw * (DAY[x24] - DAY[k])
    out[3] = rt2 - cost_extra - sw * (DAY[xt2] - DAY[k]); out[4] = rt3 - cost_extra - sw * (DAY[xt3] - DAY[k])
    return k, R

@nb.njit(cache=True)
def run_tf(cand, dirs, ratio, vr, quiet, bodyf, pauses, bo, bh, bl, bc, i0, i1, O, H, L, C, S, mod, wd, eod, yr, yr0,
           KRS, KVS, BODYS, ACC_N, ACC_S, ACC_S2, DAY):
    out = np.zeros(5)
    for p in range(pauses.shape[0]):
        legmax = int(pauses[p, 0]); pmin = int(pauses[p, 1]); pmax = int(pauses[p, 2]); retr = pauses[p, 3]
        for ci in range(len(cand)):
            i = cand[ci]
            k, R = sim_one(i, dirs[ci], legmax, pmin, pmax, retr, bo, bh, bl, bc, i0, i1, O, H, L, C, S, mod, wd, eod, out, DAY)
            if k < 0:
                continue
            y = yr[k] - yr0
            m = mod[k]
            ss = 0 if dirs[ci] == 1 else 1
            for ni in range(ratio.shape[1]):
                rt = ratio[ci, ni]; v = vr[ci, ni]
                for qi in range(2):
                    if qi == 1 and not quiet[ci, ni]:
                        continue
                    for a in range(len(KRS)):
                        if rt < KRS[a]: break
                        for b in range(len(KVS)):
                            if v < KVS[b]: break
                            for cc in range(len(BODYS)):
                                if bodyf[ci] < BODYS[cc]: break
                                for ex in range(5):
                                    r = out[ex]
                                    ACC_N[p, ni, qi, a, b, cc, ex, y, ss] += 1
                                    ACC_S[p, ni, qi, a, b, cc, ex, y, ss] += r
                                    ACC_S2[p, ni, qi, a, b, cc, ex, y, ss] += r * r

def main(tfs):
    m = load("exness"); mod, wd, yrs, eod = prep(m)
    O, H, L, C, S = (m[x].values.astype(np.float64) for x in ("open", "high", "low", "close", "spr"))
    yr0 = int(yrs.min()); ny = int(yrs.max()) - yr0 + 1
    DAY = (m.index.normalize().as_unit('ns').asi8 // 86_400_000_000_000).astype(np.int64)
    pauses = np.array(PAUSE, dtype=np.float64)
    for tf in tfs:
        t0 = time.time()
        b = make_tf(m, tf)
        bo, bh, bl, bc = (b[x].values.astype(np.float64) for x in ("open", "high", "low", "close"))
        i0, i1 = b.i0.values.astype(np.int64), b.i1.values.astype(np.int64)
        rng = pd.Series(bh - bl); vol = pd.Series(b.vol.values.astype(float))
        body = np.abs(bc - bo); bodyf = body / np.where(rng.values > 0, rng.values, np.nan)
        R_ = np.zeros((len(b), len(NS))); V_ = np.zeros_like(R_); Q_ = np.zeros(R_.shape, bool)
        for ni, N in enumerate(NS):
            ar = rng.shift(1).rolling(N).mean().values; av = vol.shift(1).rolling(N).mean().values
            mx = rng.shift(1).rolling(N).max().values
            with np.errstate(invalid="ignore", divide="ignore"):
                R_[:, ni] = rng.values / ar; V_[:, ni] = vol.values / av; Q_[:, ni] = mx < 2 * ar
        with np.errstate(invalid="ignore"):
            cmask = (np.nanmax(R_, axis=1) >= KRS[0]) & (bodyf >= BODYS[0]) & (bc != bo) & np.all(np.isfinite(R_), axis=1)
        cand = np.flatnonzero(cmask).astype(np.int64)
        dirs = np.where(bc[cand] > bo[cand], 1, -1).astype(np.int64)
        sh = (len(PAUSE), len(NS), 2, len(KRS), len(KVS), len(BODYS), 5, ny, 2)
        AN = np.zeros(sh, np.float32); AS = np.zeros(sh, np.float64); AS2 = np.zeros(sh, np.float64)
        run_tf(cand, dirs, R_[cand], np.nan_to_num(V_[cand]), Q_[cand], bodyf[cand], pauses, bo, bh, bl, bc, i0, i1,
               O, H, L, C, S, mod, wd, eod, yrs, yr0, np.array(KRS), np.array(KVS), np.array(BODYS), AN, AS, AS2, DAY)
        np.savez_compressed(f"htf_M{tf}.npz", n=AN, s=AS, s2=AS2, yr0=yr0)
        print(f"M{tf}: {len(cand)} candidati, {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or [120, 240, 1440])
