# XAUUSD – Impulso → pausa → continuazione (M1–M30)

Ricerca statistica sul pattern: primo impulso (range ≥ 2× media 20 barre, tick volume ≥ 1,5× media,
corpo ≥ 60%, nessun impulso nelle 20 barre precedenti) → pausa di 1–8 candele senza chiusure oltre
l'estremo e ritracciamento ≤ 50% → ingresso stop oltre l'estremo della struttura, SL oltre la pausa, TP 2R.

## Dati (non inclusi nel repo)
- Storico: Exness MT5 `XAUUSDm` M1 2017-04-28 → 2026-08-18 (GitHub `sherwynjoel/xauusd-historical-data`), spread reale per minuto.
- Ultimi 3 mesi: tick Dukascopy 2026 (GitHub `Touhid-HZ/xauusd-tick-data-2026`) → `build_m1.py`.

## Esecuzione
Decisioni solo a chiusura barra; esecuzione simulata sul percorso M1 (caso peggiore se SL e TP nella stessa barra M1).
Costi: spread, slippage 0,05 $ su ingresso/SL, commissione 5,40 $/lotto round turn. Sizing 2% su 1000 € (≈1160 $), lotti 0,01.
Test nullo: stessa logica su candele direzionali di dimensione normale.

Risultati: `results/`.
