"""Impulse -> pause -> continuation pattern engine for XAUUSD.

Decisions are taken only at TF bar close (no look-ahead). Execution (pending stop
order, SL, TP) is simulated on the M1 path; when one M1 bar touches both levels
the worse outcome is assumed (conservative).
Prices are BID; ask = bid + spr (spr column, USD).
"""
import numpy as np, pandas as pd
from dataclasses import dataclass, asdict

@dataclass
class P:
    N: int = 20          # lookback bars for "normal" range/volume
    KR: float = 2.0      # impulse range >= KR * avg range
    KV: float = 1.5      # impulse tick volume >= KV * avg volume
    BODY: float = 0.6    # body / range of impulse (directional close)
    QUIET: float = 2.0   # no bar in lookback with range >= QUIET*avg (first move after quiet)
    PMIN: int = 1        # min pause bars before arming the stop order
    LEGMAX: int = 4      # max consecutive strong bars forming the impulse leg
    PMAX: int = 8        # max pause bars (beyond = it became a range -> cancel)
    RETR: float = 0.5    # pause may not retrace more than RETR of impulse
    RR: float = 2.0
    MAXHOLD: int = 48    # TF bars
    BUF: float = 0.05    # USD beyond level for trigger / SL
    SLIP: float = 0.05   # USD slippage on stop fills (entry & SL)
    COMM: float = 5.40   # USD per lot round turn
    DON: int = 0          # >0: impulse must CLOSE beyond prior DON-bar extreme (exit from lateral range)
    ALIGN: bool = False   # impulse direction must agree with EMA200 side
    USEQUIET: bool = True
    BASELINE: bool = False  # True: replace impulse filter with ordinary bars (null test)

def make_tf(m1, tf):
    key = m1.index.floor(f"{tf}min")
    g = m1.groupby(key, sort=True)
    b = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(),
                      "close": g.close.last(), "vol": g.tick_volume.sum()})
    pos = np.arange(len(m1))
    s = pd.Series(pos, index=key).groupby(level=0)
    b["i0"] = s.min().values; b["i1"] = s.max().values + 1
    return b

def find_setups(b, p, rng_seed=0):
    rng = (b.high - b.low).values
    body = (b.close - b.open).values
    ar = pd.Series(rng).shift(1).rolling(p.N).mean().values
    av = pd.Series(b.vol.values).shift(1).rolling(p.N).mean().values
    mx = pd.Series(rng).shift(1).rolling(p.N).max().values
    with np.errstate(invalid="ignore", divide="ignore"):
        dirn = np.abs(body) / np.where(rng > 0, rng, np.nan)
        quiet = (mx < p.QUIET * ar) if p.USEQUIET else np.ones(len(b), bool)
        if not p.BASELINE:
            sig = (rng >= p.KR * ar) & (b.vol.values >= p.KV * av) & (dirn >= p.BODY) & quiet
            c = b.close.values; up = body > 0
            if p.DON:
                dh = pd.Series(b.high.values).shift(1).rolling(p.DON).max().values
                dl = pd.Series(b.low.values).shift(1).rolling(p.DON).min().values
                sig &= np.where(up, c > dh, c < dl)
            if p.ALIGN:
                ema = b.close.ewm(span=200, adjust=False).mean().values
                sig &= np.where(up, c > ema, c < ema)
        else:  # ordinary directional bars of normal size: does the impulse add information?
            sig = (rng < 1.2 * ar) & (rng > 0.6 * ar) & (dirn >= p.BODY)
            idx = np.flatnonzero(sig)
            r = np.random.default_rng(rng_seed)
            keep = r.choice(idx, size=min(len(idx), 60000), replace=False) if len(idx) else idx
            sig = np.zeros(len(b), bool); sig[keep] = True
    return np.flatnonzero(sig), ar

def run(m1, tf, p=P(), cost=True, rng_seed=0):
    b = make_tf(m1, tf)
    O, H, L, C = (m1[c].values for c in ("open", "high", "low", "close"))
    S = m1.spr.values if cost else np.zeros(len(m1))
    slip = p.SLIP if cost else 0.0
    T = m1.index.values
    bh, bl, bo, bc = b.high.values, b.low.values, b.open.values, b.close.values
    i0, i1 = b.i0.values, b.i1.values
    sigs, ar = find_setups(b, p, rng_seed)
    ema = b.close.ewm(span=200, adjust=False).mean().values
    out = []
    nb = len(b)
    for i in sigs:
        d = 1 if bc[i] > bo[i] else -1
        if bc[i] == bo[i]:
            continue
        hi, lo = bh[i], bl[i]                            # leg extremes
        rec = dict(t=T[i0[i]], tf=tf, dir=d, imp_range=hi - lo, avg_range=ar[i], hour=pd.Timestamp(T[i0[i]]).hour, align=bool(d * (bc[i] - ema[i]) > 0))
        c = 0; box = None; status = None; j = i + 1; legn = 1
        while j < nb and status is None:
            rg = hi - lo
            lvl = hi if d == 1 else lo                   # breakout level = structure extreme
            inv = lo + (1 - p.RETR) * rg if d == 1 else hi - (1 - p.RETR) * rg
            if c < p.PMIN:
                if (d == 1 and bl[j] <= inv) or (d == -1 and bh[j] >= inv):
                    status = "deep_retrace"; break
                closes_beyond = (bc[j] > lvl) if d == 1 else (bc[j] < lvl)
                if closes_beyond:
                    if c == 0 and legn < p.LEGMAX:          # strong close at new extreme: leg extends
                        hi = max(hi, bh[j]); lo = min(lo, bl[j]); legn += 1; j += 1; continue
                    status = "no_pause"; break               # continued without a real pause
                # pause bar: wicks beyond allowed, close back inside
                if d == 1: hi = max(hi, bh[j]); box = bl[j] if box is None else min(box, bl[j])
                else: lo = min(lo, bl[j]); box = bh[j] if box is None else max(box, bh[j])
                c += 1; j += 1; continue
            if c >= p.PMAX:
                status = "expired"; break
            # armed: stop order at lvl+-BUF, SL beyond pause box; walk M1 path of bar j
            E = lvl + d * p.BUF
            SL = box - d * p.BUF
            trig = None
            for k in range(i0[j], i1[j]):
                if d == 1:
                    if L[k] <= inv: status = "reversal"; break
                    if H[k] >= E: trig = k; break
                else:
                    if H[k] >= inv: status = "reversal"; break
                    if L[k] <= E: trig = k; break
            if status: break
            if trig is None:
                box = min(box, bl[j]) if d == 1 else max(box, bh[j])
                c += 1; j += 1; continue
            # ---- trade ----
            k = trig
            if d == 1:
                fill = max(E, O[k]) + S[k] + slip
            else:
                fill = min(E, O[k]) - slip
            Rp = abs(E - SL) + (S[k] if d == 1 else 0) + slip  # risk distance incl. entry costs
            TP = E + d * p.RR * abs(E - SL)
            res = None; exit_px = None; mfe = 0.0
            kend = min(len(m1), i1[min(nb - 1, j + p.MAXHOLD)])
            first = True
            while k < kend:
                if d == 1:
                    mfe = max(mfe, H[k] - E)
                    hit_sl = L[k] <= SL; hit_tp = H[k] >= TP and not first
                    if hit_sl: res = "SL"; exit_px = min(SL, O[k] if not first else SL) - slip; break
                    if hit_tp: res = "TP"; exit_px = TP; break
                else:
                    mfe = max(mfe, E - L[k])
                    hit_sl = H[k] + S[k] >= SL; hit_tp = L[k] + S[k] <= TP and not first
                    if hit_sl: res = "SL"; exit_px = max(SL, (O[k] + S[k]) if not first else SL) + slip; break
                    if hit_tp: res = "TP"; exit_px = TP; break
                first = False; k += 1
            # MFE until SL hit (or window end), ignoring TP: how far the continuation ran
            if d == 1:
                seg = L[trig:kend] <= SL; e = trig + (np.argmax(seg) if seg.any() else len(seg))
                mfe = (H[trig:e + 1].max() - E) if e >= trig else 0.0
            else:
                seg = H[trig:kend] + S[trig:kend] >= SL; e = trig + (np.argmax(seg) if seg.any() else len(seg))
                mfe = (E - L[trig:e + 1].min()) if e >= trig else 0.0
            if res is None:
                k = kend - 1; res = "TIME"; exit_px = C[k] if d == 1 else C[k] + S[k]
            pnl_px = (exit_px - fill) * d
            rec.update(status="triggered", pause=c, leg=legn, t_in=T[trig], t_out=T[k], fill=fill, sl=SL, tp=TP,
                       risk_px=Rp, res=res, R=pnl_px / Rp, mfe_vs_imp=mfe / rg, leg_range=rg)
            break
        if status is not None:
            rec["status"] = status; rec["pause"] = c
        elif "res" not in rec:
            rec["status"] = "eod"
        out.append(rec)
    return pd.DataFrame(out)

def equity(tr, start_usd=1160.0, risk=0.02, comm=5.40):
    """Sequential (one position at a time) compounding with MT5 lot rounding (0.01)."""
    tr = tr[tr.status == "triggered"].sort_values("t_in")
    eq = start_usd; busy_until = None; rows = []
    for r in tr.itertuples():
        if busy_until is not None and r.t_in < busy_until:
            continue
        lots = np.floor(eq * risk / (r.risk_px * 100) / 0.01) * 0.01
        if lots < 0.01:
            continue
        pnl = r.R * r.risk_px * 100 * lots - comm * lots
        eq += pnl; busy_until = r.t_out
        rows.append((r.t_in, lots, pnl, eq, pnl / (r.risk_px * 100 * lots)))
    e = pd.DataFrame(rows, columns=["t", "lots", "pnl", "equity", "Rnet"])
    return e
