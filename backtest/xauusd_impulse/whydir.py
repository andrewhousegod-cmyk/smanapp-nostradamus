"""Why does an impulse after lateral continue or reverse?
Events: TF 5/15/30/60, no bar >=2x avg in prior 20, impulse range >=2x avg20, tick volume >=2x avg20, body >=60%.
Label: symmetric first touch +1x impulse vs -1x impulse within 12 bars (M1 path). All features known at impulse close.
Learn on 2017-2022, test on 2023-2026."""
import sys; sys.path.insert(0, '.')
import numpy as np, pandas as pd, numba as nb
from engine import make_tf; from grid import load, prep
@nb.njit(cache=True)
def sym(k0,kend,d,E,X,H,L):
    e=d*E
    for k in range(k0,kend):
        hi=(H[k] if d==1 else -L[k])-e; lo=(L[k] if d==1 else -H[k])-e
        up=hi>=X; dn=-lo>=X
        if up and dn: return 0
        if up: return 1
        if dn: return -1
    return 2
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)

def build():
    m = load("exness"); mod, wd, yr, eod = prep(m); H, L, C = (m[c].values.astype(np.float64) for c in ["high", "low", "close"])
    news = pd.read_parquet("news_us.parquet"); nt = news.t.values.astype("datetime64[ns]")
    d1 = m.close.resample("1D").last().dropna(); d1.index = d1.index.tz_localize(None) if d1.index.tz else d1.index
    dh = m.high.resample("1D").max().dropna(); dl = m.low.resample("1D").min().dropna()
    for s in (dh, dl): s.index = s.index.tz_localize(None) if s.index.tz else s.index
    pdh = dh.shift(1); pdl = dl.shift(1); mom20 = np.sign(d1 - d1.shift(20)).shift(1)
    rows = []
    for tf in [5, 15, 30, 60]:
        b = make_tf(m, tf); rg = (b.high - b.low); body = (b.close - b.open)
        a20 = rg.shift(1).rolling(20).mean(); a10 = rg.shift(1).rolling(10).mean(); a100 = rg.shift(1).rolling(100).mean()
        v20 = b.vol.shift(1).rolling(20).mean(); mx = rg.shift(1).rolling(20).max()
        bh20 = b.high.shift(1).rolling(20).max(); bl20 = b.low.shift(1).rolling(20).min()
        ema = b.close.ewm(span=200, adjust=False).mean(); ema50 = b.close.ewm(span=50, adjust=False).mean()
        dlt = b.close.diff(); up = dlt.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
        ok = (a20.notna() & a100.notna() & (rg > 0)).values
        ev = ok & (mx < 2 * a20).values & (rg >= 2 * a20).values & (b.vol >= 2 * v20).values & (body.abs() >= 0.6 * rg).values
        bt = b.index.tz_localize(None) if b.index.tz else b.index
        for i in np.flatnonzero(ev):
            k = int(b.i1.values[i])
            if k >= len(H) or eod[k] <= k: continue
            kend = min(eod[k], int(b.i1.values[min(len(b) - 1, i + 12)]))
            d = int(np.sign(body.values[i])); imp = rg.values[i]; E = b.close.values[i]
            r1 = sym(k, kend, d, E, imp, H, L); r05 = sym(k, kend, d, E, 0.5 * imp, H, L)
            o, h, l, c = b.open.values[i], b.high.values[i], b.low.values[i], b.close.values[i]
            t0 = bt[i]; day = t0.normalize()
            t0n = np.datetime64(t0); t1n = t0n + np.timedelta64(tf, "m")
            nidx = np.searchsorted(nt, t0n - np.timedelta64(5, "m")); news_in = nidx < len(nt) and nt[nidx] < t1n
            sday = np.searchsorted(nt, np.datetime64(day)); news_day = sday < len(nt) and nt[sday] < np.datetime64(day + pd.Timedelta(days=1))
            dayopen = m.open.values[min(len(m)-1, np.searchsorted(m.index.values, np.datetime64(day)))]
            rows.append(dict(
                tf=tf, year=yr[k], hour=t0.hour, minute=t0.minute, dow=t0.dayofweek, d=d, imp=imp, r1=r1, r05=r05,
                ratio=imp / a20.values[i], vratio=b.vol.values[i] / v20.values[i], bodyf=abs(c - o) / imp,
                close_loc=((c - l) / imp) if d == 1 else ((h - c) / imp),
                wick_against=((h - c) / imp) if d == 1 else ((c - l) / imp),
                comp=a10.values[i] / a100.values[i], box_w=(bh20.values[i] - bl20.values[i]) / a20.values[i],
                brk=int((c > bh20.values[i]) if d == 1 else (c < bl20.values[i])),
                brk_dist=(((c - bh20.values[i]) if d == 1 else (bl20.values[i] - c)) / imp),
                ema200_al=int(np.sign(c - ema.values[i]) == d), ema50_al=int(np.sign(c - ema50.values[i]) == d),
                dist_ema=d * (c - ema.values[i]) / a20.values[i],
                pre_drift=d * (b.close.values[i - 1] - b.close.values[i - 21]) / a20.values[i],
                rsi_dir=rsi.values[i] if d == 1 else 100 - rsi.values[i],
                d1_mom_al=int(mom20.get(day, np.nan) == d),
                pd_brk=int((c > pdh.get(day, np.inf)) if d == 1 else (c < pdl.get(day, -np.inf))),
                round_dist=min(c % 10, 10 - c % 10) / a20.values[i],
                day_move=d * (c - dayopen) / a20.values[i],
                news_in=int(news_in), news_day=int(news_day)))
    D = pd.DataFrame(rows); D.to_parquet("whydir.parquet"); return D

if __name__ == "__main__":
    import os
    D = pd.read_parquet('whydir.parquet') if os.path.exists('whydir.parquet') else build()
    D["IS"] = D.year <= 2022
    X = D[D.r1.isin([1, -1])].copy(); X["cont"] = (X.r1 == 1).astype(int)
    print(f"Eventi con esito deciso: {len(X)} (2017-22: {X.IS.sum()}, 2023-26: {(~X.IS).sum()}); continua {100*X.cont.mean():.1f}%")
    feats = ["ratio", "vratio", "bodyf", "close_loc", "wick_against", "comp", "box_w", "brk_dist", "dist_ema", "pre_drift", "rsi_dir", "round_dist", "day_move", "hour"]
    flags = ["brk", "ema200_al", "ema50_al", "d1_mom_al", "pd_brk", "news_in", "news_day", "tf", "dow"]
    print("\n=== 1) OGNI CARATTERISTICA DA SOLA: % che CONTINUA per quintile, 2017-22 | 2023-26 (coerente = stesso lato del 50% in entrambi e scarto >=5 punti) ===")
    res = []
    for f in feats + flags:
        g = X[f] if f in flags else pd.qcut(X[f].rank(method="first"), 5, labels=["Q1 basso", "Q2", "Q3", "Q4", "Q5 alto"])
        t = X.groupby([g, "IS"], observed=True).cont.agg(["size", "mean"]).unstack("IS")
        t.columns = [f"{a}_{'IS' if b else 'OOS'}" for a, b in t.columns]
        t = t.fillna(0)
        for lev, r in t.iterrows():
            if r.size_IS < 30 or r.size_OOS < 30: continue
            ci, co = 100 * r.mean_IS, 100 * r.mean_OOS
            coh = "SI" if (ci - 50) * (co - 50) > 0 and abs(ci - 50) >= 5 and abs(co - 50) >= 5 else ""
            res.append((f, str(lev), int(r.size_IS), round(ci, 1), int(r.size_OOS), round(co, 1), coh))
    R = pd.DataFrame(res, columns=["caratteristica", "livello", "n_17_22", "cont_17_22", "n_23_26", "cont_23_26", "coerente"])
    print(R.to_string(index=False))
    print("\nLivelli coerenti:", (R.coerente == "SI").sum(), "su", len(R))
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    cols = feats + flags
    tr = X[X.IS]; te = X[~X.IS]
    sc = StandardScaler().fit(tr[cols]);
    print("\n=== 2) MODELLO: imparo sul 2017-22, provo sul 2023-26 (AUC 0,50 = moneta; 0,55+ = qualcosa; 0,60+ = utile) ===")
    for name, mdl, Xtr, Xte in [("Regressione logistica", LogisticRegression(C=0.3, max_iter=2000), sc.transform(tr[cols]), sc.transform(te[cols])),
                                ("Gradient boosting (alberi)", HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=40), tr[cols].values, te[cols].values)]:
        mdl.fit(Xtr, tr.cont); p_tr = mdl.predict_proba(Xtr)[:, 1]; p_te = mdl.predict_proba(Xte)[:, 1]
        print(f"\n{name}: AUC 2017-22 (dove ha imparato) = {roc_auc_score(tr.cont, p_tr):.3f}   AUC 2023-26 (nuovi) = {roc_auc_score(te.cont, p_te):.3f}")
        q = pd.qcut(p_te, 5, labels=["20% piu' 'inversione'", "Q2", "Q3", "Q4", "20% piu' 'continuazione'"])
        tt = te.assign(q=q).groupby("q", observed=True).cont.agg(["size", "mean"]); tt["mean"] = (100 * tt["mean"]).round(1)
        print("  2023-26, % che continua per gruppo di previsione:"); print(tt.to_string())
EOF
