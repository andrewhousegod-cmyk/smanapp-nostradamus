import sys; sys.path.insert(0, '.')
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from engine import make_tf
from grid import load

OUT = "../img/"
BLUE, ORANGE, AQUA, RED, GREEN, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#008300", "#8a8984"
INK, INK2, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"
plt.rcParams.update({"text.parse_math": False, "font.size": 12, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.facecolor": SURF, "figure.facecolor": SURF, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False})
SLs = [0.5, 1, 1.5, 2, 3.]; TPs = [0.25, 0.5, 1, 1.5, 2, 3.]
col = lambda s, t: SLs.index(s) * len(TPs) + TPs.index(t)

def candles(ax, o, h, l, c, x0=0, w=0.6):
    for i, (oo, hh, ll, cc) in enumerate(zip(o, h, l, c)):
        x = x0 + i; colr = AQUA if cc >= oo else RED
        ax.plot([x, x], [ll, hh], color=colr, lw=1.2, zorder=2)
        ax.add_patch(Rectangle((x - w / 2, min(oo, cc)), w, max(abs(cc - oo), 1e-6), color=colr, zorder=3))

def rsi(close, n=14):
    d = close.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

# ---------- 1) Schema ----------
def fig_schema():
    rng = np.random.default_rng(3)
    n = 22; o = []; c = []; h = []; l = []; p = 100.0
    for i in range(n):
        step = rng.normal(0.25, 0.5); oo = p; cc = p + step; hh = max(oo, cc) + abs(rng.normal(0, .25)); ll = min(oo, cc) - abs(rng.normal(0, .25))
        o.append(oo); c.append(cc); h.append(hh); l.append(ll); p = cc
    # exhaustion candle
    oo = p; cc = p + 4.2; o.append(oo); c.append(cc); h.append(cc + 0.4); l.append(oo - 0.1); p = cc
    A = 1.2; E = p + 0.05
    # after: retrace
    path = [-0.3, -0.5, -0.2, -0.4]
    for s in path:
        oo = p; cc = p + s; o.append(oo); c.append(cc); h.append(max(oo, cc) + .15); l.append(min(oo, cc) - .2); p = cc
    fig = plt.figure(figsize=(7, 8.6)); gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.08)
    ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1], sharex=ax)
    candles(ax, o, h, l, c)
    k = n
    ax.add_patch(Rectangle((k - 0.5, l[k] - 0.3), 1, h[k] - l[k] + 0.6, fill=False, ec=ORANGE, lw=2, zorder=4))
    ax.annotate("1. Candela di ESAURIMENTO\nrange ≥ 3× la media delle 20 precedenti\ncorpo ≥ 60% del range", xy=(k - 0.5, h[k] - 1), xytext=(24, 103.4),
                fontsize=11, color=INK, arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.5))
    ax.axhline(E, xmin=0, xmax=1, color=INK2, lw=1, ls="--"); ax.axhline(E + 0.5 * A, color=RED, lw=2); ax.axhline(E - 0.5 * A, color=GREEN, lw=2)
    ax.text(n + 5.6, E + 0.5 * A + 0.45, " STOP LOSS +0,5 ATR", color=RED, va="center", fontsize=11, fontweight="bold")
    ax.text(n + 5.6, E + 0.12, " INGRESSO SELL (apertura\n candela successiva)", color=INK, va="center", fontsize=11)
    ax.text(n + 5.6, E - 0.5 * A - 0.45, " TAKE PROFIT −0,5 ATR", color=GREEN, va="center", fontsize=11, fontweight="bold")
    ax.annotate("", xy=(k + 1, E - 0.3), xytext=(k + 1, E + 0.9), arrowprops=dict(arrowstyle="-|>", color=INK, lw=2))
    ax.axvspan(k + 0.5, k + 12.5, color=BLUE, alpha=0.05)
    ax.text(k + 1.2, min(l) + 0.3, "max 12 candele (36 min)\npoi chiusura a mercato", fontsize=10, color=INK2)
    ax.set_xlim(-1, n + 19); ax.set_ylabel("prezzo"); ax.set_title("Schema: 'Contro l'esaurimento' – XAUUSD M3 (esempio SELL)", fontsize=13, color=INK, loc="left")
    ax.tick_params(labelbottom=False)
    r = np.array(rsi(pd.Series(c)).values, dtype=float); r[:14] = np.linspace(45, 60, 14); r[k] = 82; r[k+1:] = np.linspace(74, 62, len(r) - k - 1)
    ax2.plot(range(len(c)), r, color=BLUE, lw=2); ax2.axhline(75, color=ORANGE, lw=1.5, ls="--"); ax2.axhline(25, color=ORANGE, lw=1.5, ls="--")
    ax2.scatter([k], [r[k]], s=60, color=ORANGE, zorder=5)
    ax2.text(k + 0.5, min(r[k], 98) - 5, "2. RSI(14) ≥ 75", color=INK, fontsize=11, va="top")
    ax2.set_ylim(0, 100); ax2.set_yticks([25, 50, 75]); ax2.set_ylabel("RSI(14)"); ax2.set_xlabel("candele M3")
    fig.text(0.02, 0.005, "3. Filtro obbligatorio: ATR(20) su M3 ≥ 1,5 $ (prudente ≥ 2,5 $).  BUY = situazione speculare (candela ribassista, RSI ≤ 25).",
             fontsize=9.5, color=INK2)
    fig.savefig(OUT + "1_schema.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- 2-3) Real examples from untouched holdout ----------
def fig_examples():
    m = load("duka"); b3 = make_tf(m, 3)
    D = pd.read_parquet("probmap_ev_duka.parquet"); G = np.load("probmap_res_duka.npy")
    msk = ((D.kind == "pattern") & (D.tf == 3) & (D.exp > 3) & (D.rsi_dir > 75) & (D.ATR >= 1.5)).values
    X = D[msk].copy(); X["r"] = -G[msk, col(0.5, 0.5)]
    X["esito"] = np.where(np.isclose(X.r, 0.5), "TP", np.where(np.isclose(X.r, -0.5), "SL", "TEMPO"))
    X["net"] = (X.r - 0.354 / X.ATR) / 0.5
    rs = rsi(b3.close)
    i1 = b3.i1.values
    picks = list(X[X.esito == "TP"].index[[0, 7, 15]]) + list(X[X.esito == "SL"].index[:1])
    for part, sel in [(2, picks[:2]), (3, picks[2:])]:
        fig, axes = plt.subplots(2, 1, figsize=(7, 9.4))
        for ax, idx in zip(axes, sel):
            r_ = X.loc[idx]; k = int(r_.k); j = int(np.flatnonzero(i1 == k)[0])
            lo, hi = j - 25, min(len(b3) - 1, j + 14)
            seg = b3.iloc[lo:hi + 1]
            candles(ax, seg.open.values, seg.high.values, seg.low.values, seg.close.values)
            js = j - lo; d = 1 if b3.close.iloc[j] > b3.open.iloc[j] else -1
            E = m.open.values[k]; A = r_.ATR; tp = E - d * 0.5 * A; sl = E + d * 0.5 * A
            ax.add_patch(Rectangle((js - 0.5, b3.low.iloc[j] - 0.3), 1, b3.high.iloc[j] - b3.low.iloc[j] + 0.6, fill=False, ec=ORANGE, lw=2, zorder=4))
            ax.hlines(E, js + 0.5, js + 13, color=INK2, lw=1, ls="--"); ax.hlines(tp, js + 0.5, js + 13, color=GREEN, lw=2); ax.hlines(sl, js + 0.5, js + 13, color=RED, lw=2)
            ax.text(js + 13.2, tp, "TP", color=GREEN, va="center", fontweight="bold"); ax.text(js + 13.2, sl, "SL", color=RED, va="center", fontweight="bold")
            side = "SELL" if d == 1 else "BUY"
            t = pd.Timestamp(m.index.values[k]).tz_localize("UTC") if pd.Timestamp(m.index.values[k]).tzinfo is None else pd.Timestamp(m.index.values[k])
            srv = t + pd.Timedelta(hours=1)
            res = {"TP": "VINTO (take profit)", "SL": "PERSO (stop loss)", "TEMPO": "chiuso a tempo"}[r_.esito]
            ax.set_title(f"{srv:%d/%m/%Y %H:%M} ora server BCM – {side} a {E:.2f}\n"
                         f"candela {r_.exp:.1f}× la media · RSI {r_.rsi_dir if d==1 else 100-r_.rsi_dir:.0f} · ATR {A:.2f}$ · stop/target {0.5*A:.2f}$  →  {res}, {r_.net:+.2f}R netto",
                         fontsize=10.5, loc="left", color=INK)
            ax.set_xticks([]); ax.set_ylabel("prezzo $")
        fig.suptitle(f"Esempi reali dal campione mai usato (ago–nov 2026) – XAUUSD M3", fontsize=13, x=0.02, ha="left", color=INK)
        fig.tight_layout(); fig.savefig(OUT + f"{part}_esempi_reali.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    return X

# ---------- 4) Exhaustion evidence ----------
def fig_evidence():
    P = pd.read_parquet("probmap_P.parquet")
    groups = [("Grandezza candela\n(× media)", "exp", [1.5, 2, 3, 4, 99], ["1,5–2×", "2–3×", "3–4×", ">4×"]),
              ("RSI nella direzione\ndella candela", "rsi_dir", [0, 50, 70, 80, 100], ["<50", "50–70", "70–80", ">80"]),
              ("Volume\n(× media)", "vr", [0, 1.5, 2, 3, 99], ["<1,5×", "1,5–2×", "2–3×", ">3×"])]
    fig, axes = plt.subplots(3, 1, figsize=(7, 9.6))
    for ax, (title, f, bins, labs) in zip(axes, groups):
        g = P.assign(b=pd.cut(P[f], bins, labels=labs)).groupby(["b", "IS"], observed=True).lift.mean().unstack() * 100
        x = np.arange(len(labs)); w = 0.36
        b1 = ax.bar(x - w / 2 - 0.01, g[True].values, w, color=BLUE, label="2017–2022")
        b2 = ax.bar(x + w / 2 + 0.01, g[False].values, w, color=ORANGE, label="2023–2026")
        for bars in (b1, b2):
            for rr in bars:
                v = rr.get_height(); ax.text(rr.get_x() + rr.get_width() / 2, v - 0.4 if v < 0 else v + 0.2, f"{v:+.1f}", ha="center", va="top" if v < 0 else "bottom", fontsize=9, color=INK2)
        ax.axhline(0, color=INK2, lw=1); ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel("punti % vs caso")
        ax.set_title(title.replace("\n", " "), loc="left", fontsize=11.5, color=INK); ax.set_ylim(min(-10.5, g.values.min() - 1.5), 2.5)
    axes[0].legend(loc="lower left", frameon=False, ncol=2)
    fig.suptitle("Più l'impulso è 'forte', più è probabile che sia FINITO\nProbabilità di continuazione (stop = target = 1 ATR) rispetto a un ingresso casuale",
                 fontsize=12.5, x=0.02, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(OUT + "4_esaurimento_prova.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- 5) Results ----------
def fig_results():
    out = []
    for src, f, g in [("storico", "probmap_ev.parquet", "probmap_res.npy"), ("holdout", "probmap_ev_duka.parquet", "probmap_res_duka.npy")]:
        D = pd.read_parquet(f); G = np.load(g)
        m = ((D.kind == "pattern") & (D.tf == 3) & (D.exp > 3) & (D.rsi_dir > 75) & (D.ATR >= 1.5)).values
        q = ((D.kind == "casuale") & (D.tf == 3) & (D.ATR >= 1.5)).values
        x = D[m].copy(); x["r"] = -G[m, col(0.5, 0.5)]; x["net"] = (x.r - 0.354 / x.ATR) / 0.5; x["src"] = src
        out.append(x)
        if src == "storico": rq_hist = (D[q].year, G[q, col(0.5, 0.5)])
        else: rq_ho = G[q, col(0.5, 0.5)]
    X = pd.concat(out)
    seg = {"2017–2022": X[(X.src == "storico") & (X.year <= 2022)], "2023–ago 2026": X[(X.src == "storico") & (X.year >= 2023)], "ago–nov 2026\n(mai usato)": X[X.src == "holdout"]}
    rnd = {"2017–2022": np.isclose(rq_hist[1][rq_hist[0].values <= 2022], 0.5).mean(), "2023–ago 2026": np.isclose(rq_hist[1][rq_hist[0].values >= 2023], 0.5).mean(), "ago–nov 2026\n(mai usato)": np.isclose(rq_ho, 0.5).mean()}
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(7, 9.4), gridspec_kw={"height_ratios": [1, 1.1]})
    labs = list(seg); x = np.arange(3); w = 0.36
    wp = [100 * (s.r > 0).mean() if False else 100 * np.isclose(s.r, 0.5).mean() for s in seg.values()]
    wr = [100 * v for v in rnd.values()]
    b1 = ax.bar(x - w / 2 - 0.01, wp, w, color=BLUE, label="Strategia (contro l'esaurimento)")
    b2 = ax.bar(x + w / 2 + 0.01, wr, w, color=GRAY, label="Ingresso casuale, stessa geometria")
    for bars in (b1, b2):
        for rr in bars: ax.text(rr.get_x() + rr.get_width() / 2, rr.get_height() + 1, f"{rr.get_height():.0f}%", ha="center", fontsize=10, color=INK)
    for i, s in enumerate(seg.values()):
        ax.text(i - w / 2 - 0.01, 4, f"n={len(s)}\nnetto\n{s.net.mean():+.2f}R", ha="center", fontsize=9, color="white", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylim(0, 92); ax.set_ylabel("% trade a take profit")
    ax.legend(frameon=False, loc="upper left", fontsize=9.5); ax.set_title("Percentuale di vincita: strategia contro caso", loc="left", fontsize=12, color=INK)
    X = X.sort_values(["year", "k"]) ; X = pd.concat([X[X.src == "storico"].sort_values("k"), X[X.src == "holdout"].sort_values("k")])
    eq = 1000 * np.cumprod(1 + 0.01 * X.net.values)
    ax2.plot(np.arange(len(eq)), eq, color=BLUE, lw=2)
    nh = (X.src == "storico").sum(); ax2.axvspan(nh, len(eq), color=ORANGE, alpha=0.12); ax2.text(nh + 3, eq.min(), "mai usato", color=INK2, fontsize=9.5)
    yrs = X.year.values; first = [np.argmax(yrs == y) for y in sorted(set(yrs[X.src.values == "storico"]))]
    for p in [f for i_, f in enumerate(first) if i_ == 0 or f - first[i_-1] >= 15]: ax2.axvline(p, color=GRID, lw=1); ax2.text(p + 2, eq.max() * 1.01, str(yrs[p]), fontsize=8.5, color=INK2)
    dd = 100 * (1 - (eq / np.maximum.accumulate(eq)).min())
    ax2.set_title(f"Capitale 1000 € con rischio 1% per trade (netto costi): → {eq[-1]:.0f} €, drawdown max {dd:.0f}%", loc="left", fontsize=11.5, color=INK)
    ax2.set_xlabel("numero di trade (2019 → nov 2026)"); ax2.set_ylabel("€")
    fig.tight_layout(); fig.savefig(OUT + "5_risultati.png", dpi=200, bbox_inches="tight"); plt.close(fig)

fig_schema(); X = fig_examples(); fig_evidence(); fig_results(); print("ok")
