# Verifica indipendente su TradingView (18/11/2026)

Costi: 0,354 $/oncia andata e ritorno (spread 0,20 + slippage 0,10 + commissione 0,054), rischio 1%, leva 1:100, capitale 1160 $.

## Impulso–Pausa–Continuazione, sessione New York (12–17 UTC), uscita a tempo 12 candele — `impulso_pausa_NY.pine`

| Feed | TF | Periodo | Trade | Vincenti | Profit factor | Netto | Drawdown max |
|---|---|---|---|---|---|---|---|
| OANDA | M30 | 2017–2022 | 143 | 44,1% | 1,56 | +51% | 8,6% |
| OANDA | M30 | 2023–nov 2026 | 90 | 36,7% | 1,31 | +17% | 11,6% |
| OANDA | M30 | 2017–nov 2026 | 233 | 41,2% | 1,48 | +81% | 12,8% |
| Pepperstone | M30 | 2017–nov 2026 | 252 | 40,9% | 1,59 | +125% | 10,8% |
| OANDA | M15 | 2017–nov 2026 | 457 | 33,0% | 1,10 | +30% | 30,0% |
| OANDA | M5 | 2017–nov 2026 | 888 | 25,7% | 0,60 | −97% | 97% |

Python (Exness, M30): 227 trade, 41% vincenti, rapporto vincita/perdita 2,2 → coerente.

## Contro l'esaurimento M3 — `contro_esaurimento_M3.pine` (RITIRATA)

| Feed | TF | Periodo | Trade | Vincenti | Profit factor | Netto |
|---|---|---|---|---|---|---|
| OANDA | M3 | 2024–nov 2026 | 335 | 55,5% | 0,74 | −34% |

## Stesse regole su altri mercati (M30, 12–17 UTC, costi in % del prezzo, capitale 100k per sizing preciso)

| Mercato | Trade | Vincenti | Profit factor | Netto | Drawdown max |
|---|---|---|---|---|---|
| Argento OANDA:XAGUSD | 201 | 37,8% | 1,27 | +40% | 15,4% |
| Nasdaq PEPPERSTONE:NAS100 | 241 | 29,5% | 1,24 | +56% | 23,8% |
| S&P500 PEPPERSTONE:US500 | 220 | 32,3% | 1,28 | +51% | 21,4% |
| DAX PEPPERSTONE:GER40 | 116 | 37,1% | 0,91 | −7% | 22,2% |

## Stesse regole sull'oro in altre sessioni (OANDA M30)

| Sessione (UTC) | Trade | Vincenti | Profit factor | Netto | Drawdown max |
|---|---|---|---|---|---|
| Asia 00–06 | 81 | 32,1% | 1,02 | +1,5% | 12,6% |
| Londra 06–12 | 276 | 17,8% | 0,72 | −53% | 57% |
| New York 12–17 | 233 | 41,2% | 1,48 | +81% | 12,8% |
