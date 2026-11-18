import sys; sys.path.insert(0, '.')
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from engine import make_tf

OUT = "../img2/"
import os; os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, AQUA, RED, GREEN, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#008300", "#8a8984"
INK, INK2, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"
plt.rcParams.update({"text.parse_math": False, "font.size": 12, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False})

def candles(ax, o, h, l, c, w=0.6):
    for i, (oo, hh, ll, cc) in enumerate(zip(o, h, l, c)):
        colr = AQUA if cc >= oo else RED
        ax.plot([i, i], [ll, hh], color=colr, lw=1.2, zorder=2)
        ax.add_patch(Rectangle((i - w / 2, min(oo, cc)), w, max(abs(cc - oo), 1e-6), color=colr, zorder=3))

# ---------- 1) schema ----------
def schema():
    rng = np.random.default_rng(11); o = []; h = []; l = []; c = []; p = 100.0
    def bar(step, wick=0.25):
        nonlocal p
        oo = p; cc = p + step; o.append(oo); c.append(cc)
        h.append(max(oo, cc) + abs(rng.normal(0, wick))); l.append(min(oo, cc) - abs(rng.normal(0, wick))); p = cc
    for _ in range(16): bar(rng.normal(0, 0.35))          # lateralità
    k = len(o); bar(2.6, 0.15)                              # impulso
    bar(0.9, 0.1)                                           # seconda candela forte (gamba)
    pz = len(o); bar(-0.35, 0.2); bar(0.15, 0.2)            # pausa
    hi = max(h[k:]) ; box = min(l[pz:])
    E = hi + 0.05; SL = box - 0.05
    e_i = len(o); bar(1.1, 0.2); bar(0.8, 0.3); bar(1.2, 0.3); bar(-0.4, 0.3); bar(0.9, 0.3); bar(0.5, 0.3)
    fig = plt.figure(figsize=(7, 8.2)); ax = fig.add_subplot(111)
    candles(ax, o, h, l, c)
    ax.axvspan(-0.5, k - 0.5, color=GRAY, alpha=0.08); ax.text(0, max(h[:k]) + 0.5, "1. LATERALITÀ\nnessuna candela grande\nnelle 20 precedenti", fontsize=10.5, color=INK)
    ax.add_patch(Rectangle((k - 0.5, l[k] - 0.15), 2, max(h[k:k+2]) - l[k] + 0.3, fill=False, ec=ORANGE, lw=2, zorder=4))
    ax.annotate("2. IMPULSO (anche 2–4 candele)\nrange ≥ 1,5× media · volume ≥ media\ncorpo ≥ 60%", xy=(k + 1.5, l[k] + 1.0), xytext=(k + 3.5, l[k] - 0.6),
                fontsize=10.5, arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.5))
    ax.add_patch(Rectangle((pz - 0.5, box - 0.1), 2, hi - box + 0.2, fill=False, ec=BLUE, lw=2, zorder=4))
    ax.annotate("3. PAUSA (1–8 candele)\nnon chiude oltre il massimo\nnon ritraccia oltre metà impulso", xy=(pz + 1, box), xytext=(0, box + 2.3),
                fontsize=10.5, arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.5))
    ax.hlines(E, pz - 0.5, len(o), color=INK, lw=1.5, ls="--"); ax.text(len(o) - 0.3, E, " 4. ORDINE BUY STOP sopra il massimo\n (ingresso solo tra 12 e 17 UTC)", va="center", fontsize=10.5)
    ax.hlines(SL, pz - 0.5, len(o), color=RED, lw=2); ax.text(len(o) - 0.3, SL, " STOP LOSS\n sotto la pausa", va="center", fontsize=10.5, color=RED, fontweight="bold")
    ax.axvspan(e_i - 0.5, len(o) - 0.5, color=AQUA, alpha=0.07)
    ax.text(e_i - 9.5, max(h) - 1.2, "5. USCITA A TEMPO: dopo 12 candele (6 ore)\no alle 20:45 UTC. Niente take profit fisso,\nniente break even.", fontsize=10.5, color=INK)
    ax.set_xlim(-1, len(o) + 7); ax.set_xticks([]); ax.set_ylabel("prezzo")
    ax.set_title("Schema: Impulso → Pausa → Continuazione · M30 · New York (esempio BUY)", loc="left", fontsize=12.5, color=INK)
    fig.text(0.02, 0.01, "SELL = situazione speculare (impulso ribassista, ordine sell stop sotto il minimo, stop sopra la pausa).", fontsize=9.5, color=INK2)
    fig.savefig(OUT + "1_schema.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- 2-3) real examples ----------
def examples():
    m = pd.read_parquet("duka_m1.parquet"); b = make_tf(m, 30)
    T = pd.read_pickle("ny_examples.pkl")
    picks = [("2026-08-19 12:30", "VINTO"), ("2026-11-11 14:30", "VINTO"), ("2026-10-27 10:30", "VINTO"), ("2026-09-25 14:30", "PERSO")]
    def one(ax, tstr):
        r = T[pd.to_datetime(T.t) == pd.Timestamp(tstr)].iloc[0]
        ti = pd.Timestamp(r.t).tz_localize("UTC") if pd.Timestamp(r.t).tzinfo is None else pd.Timestamp(r.t)
        tin = pd.Timestamp(r.t_in).tz_localize("UTC"); tout = pd.Timestamp(r.t_out).tz_localize("UTC")
        flat = tin.normalize() + pd.Timedelta(hours=20, minutes=45)
        if tout > flat: tout = flat
        idx = b.index.get_indexer([ti])[0]
        lo, hi_ = idx - 14, min(len(b) - 1, b.index.searchsorted(tout) + 2)
        seg = b.iloc[lo:hi_ + 1]
        candles(ax, seg.open.values, seg.high.values, seg.low.values, seg.close.values)
        ji = idx - lo; ei = seg.index.searchsorted(tin.floor("30min")); xi = seg.index.searchsorted(tout.floor("30min"))
        d = int(r.dir); E = r.fill; SL = r.sl
        px_out = m.close[m.index <= tout].iloc[-1] if r.res != "SL" else SL
        Rv = d * (px_out - E) / abs(E - SL) - 0.354 / abs(E - SL)
        ax.add_patch(Rectangle((ji - 0.5, seg.low.iloc[ji] - 1), 1, seg.high.iloc[ji] - seg.low.iloc[ji] + 2, fill=False, ec=ORANGE, lw=2, zorder=4))
        ax.hlines(E, ei - 0.5, xi + 0.5, color=INK, lw=1.4, ls="--"); ax.hlines(SL, ei - 0.5, xi + 0.5, color=RED, lw=2)
        ax.text(xi + 0.7, SL, "SL", color=RED, va="center", fontweight="bold")
        ax.scatter([ei], [E], marker="^" if d == 1 else "v", s=120, color=BLUE, zorder=6)
        ax.scatter([xi], [px_out], marker="X", s=110, color=INK, zorder=6)
        ax.axvspan(ei - 0.5, xi + 0.5, color=AQUA if Rv > 0 else RED, alpha=0.07)
        srv = lambda t: (t + pd.Timedelta(hours=1)).strftime("%H:%M")
        side = "BUY" if d == 1 else "SELL"
        esito = {"SL": "stop loss", "TIME": "uscita a tempo"}[r.res] if tout != flat or r.res == "SL" else "chiusura 21:45 server"
        ax.set_title(f"{ti:%d/%m/%Y} · impulso {srv(ti)} → {side} stop a {E:.2f} alle {srv(tin)} · uscita {srv(tout)} ({esito})\n"
                     f"stop {abs(E-SL):.2f} $ · pausa {int(r.pause)} candela/e → {'VINTO' if Rv>0 else 'PERSO'} {Rv:+.2f}R netto   (orari = server BCM)",
                     loc="left", fontsize=10, color=INK)
        ax.set_xticks([]); ax.set_ylabel("prezzo $")
    for part, sel in [(2, picks[:2]), (3, picks[2:])]:
        fig, axes = plt.subplots(2, 1, figsize=(7, 9.4))
        for ax, (ts, _) in zip(axes, sel): one(ax, ts)
        fig.suptitle("Esempi reali XAUUSD M30 (ago–nov 2026, dati mai usati per costruire la regola)", fontsize=12, x=0.02, ha="left", color=INK)
        fig.tight_layout(); fig.savefig(OUT + f"{part}_esempi_reali.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- 4) sessions ----------
def bars(ax, labels, pf, notes, title, colors):
    y = np.arange(len(labels))[::-1]
    ax.barh(y, [v - 1 for v in pf], left=1, color=colors, height=0.6)
    ax.axvline(1, color=INK2, lw=1.2)
    for yy, v, n in zip(y, pf, notes):
        ax.text(max(v, 1) + 0.02, yy, f"PF {v:.2f}  ·  {n}", va="center", fontsize=10, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlim(0.5, 2.3)
    ax.set_title(title, loc="left", fontsize=11.5, color=INK); ax.set_xlabel("profit factor (sotto 1 = perde, sopra 1 = guadagna)")

def sessions():
    fig, ax = plt.subplots(figsize=(7, 4.6))
    bars(ax, ["Asia 00–06 UTC\n(01–07 Italia)", "Londra 06–12 UTC\n(07–13 Italia)", "New York 12–17 UTC\n(13–18 Italia)"],
         [1.02, 0.72, 1.48], ["81 trade · +1,5%", "276 trade · −53%", "233 trade · +81%"],
         "Stessa strategia sull'oro M30, 2017–2026, in ogni sessione (TradingView, OANDA)",
         [GRAY, RED, BLUE])
    fig.tight_layout(); fig.savefig(OUT + "4_sessioni.png", dpi=200, bbox_inches="tight"); plt.close(fig)

def tf_markets():
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 8.6), gridspec_kw={"height_ratios": [3, 5]})
    bars(a1, ["M5", "M15", "M30"], [0.60, 1.10, 1.48], ["888 trade · −97%", "457 trade · +30% (DD 30%)", "233 trade · +81% (DD 13%)"],
         "Timeframe: oro, sessione New York, 2017–2026", [RED, GRAY, BLUE])
    bars(a2, ["Oro (OANDA)", "Oro (Pepperstone)", "Argento", "S&P 500", "Nasdaq 100", "DAX"],
         [1.48, 1.59, 1.27, 1.28, 1.24, 0.91],
         ["+81% · DD 13%", "+125% · DD 11%", "+40% · DD 15%", "+51% · DD 21%", "+56% · DD 24%", "−7% · DD 22%"],
         "Mercati: stesse identiche regole, M30, 12–17 UTC, 2017–2026", [BLUE, BLUE, BLUE, BLUE, BLUE, RED])
    fig.tight_layout(); fig.savefig(OUT + "5_timeframe_mercati.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- 6) equity ----------
def equity():
    T = pd.read_parquet("family_exness.parquet").rename(columns={"R$": "Rd"})
    x = T[(T.TF == "M30") & (T.entry == "breakout") & (T["mod"] >= 720) & (T["mod"] < 1020) & (T.ctx == "quiet") & (T.KV == 1.0) & (T.KR == 1.5) & (T.exit == "TIME12")].drop_duplicates("k").sort_values("k")
    eq = 1000 * np.cumprod(1 + 0.01 * x.r.values)
    t = pd.to_datetime(x.t).dt.tz_localize(None) if pd.to_datetime(x.t).dt.tz is not None else pd.to_datetime(x.t)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 8.6), gridspec_kw={"height_ratios": [3, 2]})
    a1.plot(t.values, eq, color=BLUE, lw=2); a1.axvspan(pd.Timestamp("2023-01-01"), t.max(), color=ORANGE, alpha=0.08)
    a1.text(pd.Timestamp("2023-02-01"), eq.min(), "2023–2026: periodo di verifica", fontsize=9.5, color=INK2)
    dd = 100 * (1 - (eq / np.maximum.accumulate(eq)).min())
    a1.set_title(f"1000 € · rischio 1% per trade · netto costi: → {eq[-1]:.0f} €, drawdown max {dd:.0f}%", loc="left", fontsize=11.5, color=INK)
    a1.set_ylabel("€")
    yr = x.groupby(t.dt.year.values).r.agg(["size", "sum"])
    a2.bar(yr.index, yr["sum"], color=[BLUE if v > 0 else RED for v in yr["sum"]], width=0.6)
    for xx, (n, s) in yr.iterrows(): a2.text(xx, s + (0.4 if s >= 0 else -0.9), f"{s:+.1f}R\n({int(n)})", ha="center", fontsize=8.5, color=INK2)
    a2.axhline(0, color=INK2, lw=1); a2.set_ylim(min(yr["sum"].min()-3,-3), yr["sum"].max()+6); a2.set_ylabel("R per anno"); a2.set_title("Risultato per anno (R totali, numero trade)", loc="left", fontsize=11, color=INK)
    fig.tight_layout(); fig.savefig(OUT + "6_capitale.png", dpi=200, bbox_inches="tight"); plt.close(fig)

schema(); examples(); sessions(); tf_markets(); equity(); print("ok")
