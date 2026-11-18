"""Pre-registered evaluation of the full sweep.
IS = 2017-2022 (selection), OOS = 2023-2026 (confirmation).
1) effect of every variable (median over all other combos) IS vs OOS
2) share of variants positive in both, and rank correlation IS->OOS
3) top variants by IS t-stat and their OOS
4) walk-forward of the whole selection process (pick best on previous 3 years, trade next year blind)
5) multiple-testing threshold on the full period."""
import numpy as np, pandas as pd, itertools, glob
from scipy import stats
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400); pd.set_option("display.max_columns", 30)
NS = [10, 20, 50, 100]; KRS = [1.25, 1.5, 2.0, 2.5, 3.0]; KVS = [0.0, 1.0, 1.5, 2.0]; BODYS = [0.5, 0.6, 0.7]
PAUSE = [(lg, pmin, pmax, rt) for lg in (1, 4) for pmin in (1, 2) for pmax in (4, 8) for rt in (0.382, 0.5, 0.618)]
EXITS = ["TIME6", "TIME12", "TIME24", "TP2R", "TP3R"]; SESS = ["BUY", "SELL", "TUTTE"]
frames = []; yearly = {}
for f in sorted(glob.glob("htf_M*.npz")):
    tf = int(f.split("_M")[1].split(".")[0]); z = np.load(f); yr0 = int(z["yr0"])
    n = z["n"].astype(np.float64); s = z["s"]; s2 = z["s2"]
    # add ALL sessions
    n = np.concatenate([n, n.sum(-1, keepdims=True)], -1); s = np.concatenate([s, s.sum(-1, keepdims=True)], -1); s2 = np.concatenate([s2, s2.sum(-1, keepdims=True)], -1)
    years = np.arange(yr0, yr0 + n.shape[7])
    yearly[tf] = (n, s, s2, years)
    isY = years <= 2022; ooY = years >= 2023
    def agg(mask):
        return n[..., mask, :].sum(7), s[..., mask, :].sum(7), s2[..., mask, :].sum(7)
    nI, sI, s2I = agg(isY); nO, sO, s2O = agg(ooY); nA, sA, s2A = agg(np.ones_like(isY))
    idx = np.indices(nI.shape).reshape(nI.ndim, -1).T
    d = pd.DataFrame(idx, columns=["p", "N", "quiet", "KR", "KV", "BODY", "exit", "sess"])
    d["TF"] = tf
    for lab, (a, b, c) in {"IS": (nI, sI, s2I), "OOS": (nO, sO, s2O), "ALL": (nA, sA, s2A)}.items():
        a = a.ravel(); b = b.ravel(); c = c.ravel()
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = b / a; var = c / a - mean ** 2; t = mean / np.sqrt(np.maximum(var, 1e-12) / a)
        d[f"n_{lab}"] = a; d[f"m_{lab}"] = mean; d[f"t_{lab}"] = t
    frames.append(d)
D = pd.concat(frames, ignore_index=True)
D["legmax"] = [PAUSE[i][0] for i in D.p]; D["pmin"] = [PAUSE[i][1] for i in D.p]; D["pmax"] = [PAUSE[i][2] for i in D.p]; D["retr"] = [PAUSE[i][3] for i in D.p]
D["N"] = np.array(NS)[D.N]; D["KR"] = np.array(KRS)[D.KR]; D["KV"] = np.array(KVS)[D.KV]; D["BODY"] = np.array(BODYS)[D.BODY]
D["exit"] = np.array(EXITS)[D.exit]; D["sess"] = np.array(SESS)[D.sess]; D["quiet"] = np.where(D.quiet == 1, "si", "no")
V = D[(D.n_IS >= 40) & (D.n_OOS >= 25)].copy()
Ntest = len(V); tb = stats.norm.isf(0.05 / Ntest / 2)
print(f"Strategie totali: {len(D):,}   valutabili (>=100 trade IS, >=50 OOS): {Ntest:,}   soglia di significatività corretta: t > {tb:.2f}")
print(f"Positive (netto) in IS: {100*(V.m_IS>0).mean():.1f}%  in OOS: {100*(V.m_OOS>0).mean():.1f}%  in entrambi: {100*((V.m_IS>0)&(V.m_OOS>0)).mean():.1f}%")
print(f"Correlazione di rango IS -> OOS: {stats.spearmanr(V.m_IS, V.m_OOS).statistic:.3f}")
print(f"Strategie con t (intero periodo) oltre la soglia corretta: {(V.t_ALL > tb).sum()}")
print("\n=== EFFETTO DI OGNI VARIABILE (mediana del R netto per trade su tutte le altre combinazioni) ===")
for var in ["TF", "N", "quiet", "KR", "KV", "BODY", "legmax", "pmin", "pmax", "retr", "sess", "exit"]:
    g = V.groupby(var).agg(varianti=("m_IS", "size"), R_IS=("m_IS", "median"), R_OOS=("m_OOS", "median"),
                           pos_entrambi=("m_IS", lambda x: 100 * ((x > 0) & (V.loc[x.index, "m_OOS"] > 0)).mean()))
    print(f"\n-- {var} --"); print(g.round(3).to_string())
print("\n=== TOP 25 PER t IN-SAMPLE (2017-22) E LORO ESITO 2023-26 ===")
cols = ["TF", "N", "quiet", "KR", "KV", "BODY", "legmax", "pmin", "pmax", "retr", "sess", "exit", "n_IS", "m_IS", "t_IS", "n_OOS", "m_OOS", "t_OOS"]
print(V.sort_values("t_IS", ascending=False).head(25)[cols].round(3).to_string(index=False))
print("\n=== WALK-FORWARD DEL PROCESSO DI SCELTA (scelgo sui 3 anni precedenti, opero l'anno dopo alla cieca) ===")
rows = []
keys = ["p", "N", "quiet", "KR", "KV", "BODY", "exit", "sess"]
for Y in range(2020, 2027):
    recs = []
    for tf, (n, s, s2, years) in yearly.items():
        tr = (years >= Y - 3) & (years <= Y - 1); te = years == Y
        a = n[..., tr, :].sum(7).ravel(); b = s[..., tr, :].sum(7).ravel(); c = s2[..., tr, :].sum(7).ravel()
        an = n[..., te, :].sum(7).ravel(); bs = s[..., te, :].sum(7).ravel()
        with np.errstate(invalid="ignore", divide="ignore"):
            m = b / a; t = m / np.sqrt(np.maximum(c / a - m ** 2, 1e-12) / a)
        ok = a >= 25
        t[~ok] = -np.inf
        top = np.argsort(-t)[:50]
        for rank, ii in enumerate(top):
            recs.append((tf, rank, t[ii], an[ii], bs[ii]))
    R = pd.DataFrame(recs, columns=["tf", "rank", "t", "n_next", "s_next"]).sort_values("t", ascending=False)
    for k in [1, 10, 50]:
        x = R.head(k); nn = x.n_next.sum(); rows.append(dict(anno=Y, top=k, trade=int(nn), R_medio=round(x.s_next.sum() / max(nn, 1), 3), R_tot=round(x.s_next.sum() / k, 2)))
W = pd.DataFrame(rows); print(W.to_string(index=False))
print(W.groupby("top").apply(lambda d: pd.Series({"anni_positivi": int((d.R_medio > 0).sum()), "anni": len(d), "R_medio_pesato": round((d.R_medio * d.trade).sum() / max(d.trade.sum(), 1), 3)})).to_string())
V.to_parquet("htf_V.parquet")
