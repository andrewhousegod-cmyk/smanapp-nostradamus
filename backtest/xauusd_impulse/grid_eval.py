"""Pre-registered evaluation of the grid.
A variant = (TF, KR, KV, ctx, entry, exit, session|ALL).
Criteria (decided before looking):
 1. IS = 2017-2022 selection, OOS = 2023-2026 confirmation.
 2. Multiple-testing: with ~N variants, significance requires |t| > Bonferroni threshold.
 3. Persistence: rank correlation between IS and OOS net expectancy across all variants.
 4. Walk-forward: each year pick best variants on the previous 3 years, trade the next year blind.
"""
import pandas as pd, numpy as np
from scipy import stats
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 200)
g = pd.read_parquet("grid_exness.parquet")
K = ["TF", "KR", "KV", "ctx", "entry", "exit"]
allsess = g.groupby(K + ["year"], as_index=False)[["n", "sum", "sum2", "wins", "gsum"]].sum(); allsess["sess"] = "ALL"
g = pd.concat([g, allsess], ignore_index=True)
V = K + ["sess"]
def agg(df):
    a = df.groupby(V)[["n", "sum", "sum2", "wins", "gsum"]].sum()
    a["mean"] = a["sum"] / a.n
    var = (a.sum2 / a.n - a["mean"] ** 2).clip(lower=1e-12)
    a["t"] = a["mean"] / np.sqrt(var / a.n); a["win"] = 100 * a.wins / a.n; a["gross"] = a.gsum / a.n
    return a[["n", "mean", "t", "win", "gross"]]
IS = agg(g[g.year <= 2022]); OOS = agg(g[g.year >= 2023])
J = IS.join(OOS, lsuffix="_IS", rsuffix="_OOS", how="inner")
J = J[(J.n_IS >= 100) & (J.n_OOS >= 50)]
N = len(J); tb = stats.norm.isf(0.05 / N / 2)
print(f"Varianti valutabili (>=100 trade IS, >=50 OOS): {N}.  Soglia Bonferroni |t| > {tb:.2f}")
print(f"Netto >0 in IS: {100*(J.mean_IS>0).mean():.1f}%   Netto >0 in OOS: {100*(J.mean_OOS>0).mean():.1f}%   in entrambi: {100*((J.mean_IS>0)&(J.mean_OOS>0)).mean():.1f}%")
print(f"Lordo >0 in IS: {100*(J.gross_IS>0).mean():.1f}%   Lordo >0 in OOS: {100*(J.gross_OOS>0).mean():.1f}%")
print(f"Significative dopo correzione (t_IS > {tb:.2f}): {(J.t_IS>tb).sum()}   di cui positive anche OOS: {((J.t_IS>tb)&(J.mean_OOS>0)).sum()}")
rho = stats.spearmanr(J.mean_IS, J.mean_OOS).statistic
print(f"Correlazione di rango IS->OOS dell'expectancy netta: {rho:.3f}")
rg = stats.spearmanr(J.gross_IS, J.gross_OOS).statistic
print(f"Correlazione di rango IS->OOS dell'expectancy LORDA: {rg:.3f}")
print("\nTOP 25 varianti per t in IS e loro esito OOS:")
print(J.sort_values("t_IS", ascending=False).head(25).round(3).to_string())
print("\nTOP 15 per t in OOS (solo per vedere cosa sarebbe servito sapere prima) e il loro IS:")
print(J.sort_values("t_OOS", ascending=False).head(15).round(3).to_string())
# Breakdown by dimension: median net & gross expectancy, IS vs OOS
for dim in ["TF", "entry", "exit", "ctx", "sess"]:
    x = J.groupby(level=dim)[["mean_IS", "mean_OOS", "gross_IS", "gross_OOS"]].median().round(3)
    print(f"\nMediana per {dim}:"); print(x.to_string())
# Walk-forward
print("\nWALK-FORWARD: ogni anno scelgo le varianti migliori (t) sui 3 anni precedenti, le opero l'anno dopo alla cieca")
res = []
for Y in range(2020, 2027):
    tr = agg(g[(g.year >= Y - 3) & (g.year <= Y - 1)]); tr = tr[tr.n >= 60]
    te = agg(g[g.year == Y])
    for top in [1, 5, 20]:
        pick = tr.sort_values("t", ascending=False).head(top).index
        x = te.reindex(pick).dropna()
        if len(x) == 0: continue
        res.append(dict(anno=Y, top=top, trade=int(x.n.sum()), R_medio=round((x["mean"] * x.n).sum() / x.n.sum(), 3),
                        R_tot=round((x["mean"] * x.n).sum() / top, 1), scelta=str(pick[0])))
W = pd.DataFrame(res); print(W.to_string(index=False))
print(W.groupby("top").apply(lambda d: pd.Series({"anni_positivi": (d.R_medio > 0).sum(), "anni": len(d),
      "R_medio_pesato": round((d.R_medio * d.trade).sum() / d.trade.sum(), 3)})).to_string())
J.to_parquet("grid_J.parquet")
