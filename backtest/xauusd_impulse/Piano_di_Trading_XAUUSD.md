---
title: "Piano di Trading XAUUSD – versione basata sui dati"
subtitle: "Bozza v0.1 – 18/11/2026 – struttura del 'Piano di Trading 2024.09.08' compilata con il backtest 2017–2026"
---

**Legenda dello stato di ogni regola**

- **[DIMOSTRATO]**: confermato su 2017–22, 2023–26 e campione mai usato (ago–nov 2026), al netto dei costi.
- **[PLAUSIBILE]**: positivo in tutti i periodi ma statisticamente debole (pochi trade). Va confermato in demo.
- **[SMENTITO]**: testato e negativo al netto dei costi. Non va usato.
- **[DA DEFINIRE]**: dipende da dati che mancano (es. fuso orario del server BCM).

Dati: MT5 Exness XAUUSD M1, aprile 2017 → agosto 2026 (3,28 milioni di barre) + tick Dukascopy agosto–novembre 2026.
Costi: spread 0,20 $ (come BCM negli screenshot) + slippage 0,05 $ per lato + commissione 5,40 $/lotto.
1 pip = 0,10 $. Tutte le operazioni chiuse entro le 20:45 UTC.

# 0. STRATEGIA PRINCIPALE v1: "Contro l'esaurimento" su M3 (scalping)

**Il pattern.** Sui timeframe piccoli, la candela "forte" (molto più grande delle precedenti, con l'RSI già tirato nella sua direzione) **di solito non è l'inizio del movimento ma la sua fine**: nei minuti successivi il prezzo ritraccia almeno mezzo ATR molto più spesso del caso. È l'opposto dell'intuizione "entro sull'impulso". I dati (2017–2026 + campione mai usato) lo confermano in tutti i periodi.

**Layout del grafico (MT5)**

- XAUUSD, **M3**.
- **RSI(14)** sulla chiusura, livelli 25 e 75.
- **ATR(20)** (approssima il range medio delle ultime 20 candele).
- Volumi tick (informativi, non obbligatori).

**Segnale (tutte le condizioni a chiusura candela)**

| # | Condizione SELL (contro una candela rialzista) | Condizione BUY (specchio) |
|---|---|---|
| 1 | Candela rialzista con **range ≥ 3 × la media delle 20 candele precedenti** | Candela ribassista con range ≥ 3 × la media |
| 2 | **Corpo ≥ 60%** del range | idem |
| 3 | **RSI(14) ≥ 75** alla chiusura della candela | RSI(14) ≤ 25 |
| 4 | **ATR(20) M3 ≥ 1,5 $** (versione prudente: ≥ 2,5 $) | idem |
| 5 | Ingresso tra 00:00 e 20:00 UTC, mai di venerdì NFP 12–15 UTC | idem |

**Esecuzione e gestione**

- **Ingresso:** all'apertura della candela successiva, **contro** la candela segnale.
- **Stop loss = take profit = 0,5 × ATR(20)** (oggi circa 0,75–1,25 $, cioè 7–12 pip).
- **Uscita a tempo:** se dopo 12 candele (36 minuti) non ha toccato né TP né SL, chiusura a mercato. Chiusura forzata alle 20:45 UTC.
- **Niente break even, niente parziali:** con stop e target così vicini non servono e aggiungono costi.
- **Rischio:** 1% per trade (vedi le perdite consecutive sotto).

**Numeri (netti: spread 0,20 $ + slippage + commissione)**

| Campione | Trade | Vincenti | Vincenti con ingresso casuale | R medio netto |
|---|---|---|---|---|
| ATR ≥ 1,5 $, 2017–2022 | 128 | 67% | 52% | 0,00 |
| ATR ≥ 1,5 $, 2023–ago 2026 | 341 | 68% | 52% | +0,11 |
| ATR ≥ 1,5 $, **ago–nov 2026 (mai usato)** | 42 | **76%** | 46% | **+0,31** |
| ATR ≥ 2,5 $, 2017–ago 2026 | 236 | circa 70% | circa 50% | **+0,19** |
| ATR ≥ 2,5 $, ago–nov 2026 (mai usato) | 37 | 73% | 46% | +0,27 |

- Frequenza attuale (oro intorno a 4000 $, ATR alto): **circa 13–15 segnali al mese su M3**.
- Massimo storico di perdite consecutive: 5. Drawdown massimo con l'1% di rischio: 19%.
- Anni negativi: 2021–2023 (ATR basso → i costi pesano di più). **Il vantaggio lordo è stabile; quello netto c'è solo quando l'oro è volatile in dollari, come oggi.** Per questo il filtro ATR è obbligatorio.

**Stato: [DIMOSTRATO al lordo in 3 campioni] / [PLAUSIBILE al netto].** Da confermare in demo, soprattutto lo slippage reale sull'ingresso subito dopo un picco.

**Varianti testate e scartate:** lo stesso fade su M5 (netto circa 0 sullo storico) e su M15–M30 (nessun vantaggio). Il "fade largo" (espansione > 3× **o** RSI > 75 **o** volume > 3×) ha 4 segnali al giorno ma un netto di circa 0.

# 1. Struttura del piano

## 1.1 Money management

| Regola | Valore | Stato |
|---|---|---|
| Rischio per operazione | **1%** in fase di verifica, 2% solo dopo la conferma in demo | [PLAUSIBILE] |
| Capitale di esempio | 1000 € → rischio 10–20 € a trade | — |
| Lotto | rischio € / (stop in $ × 100). Con stop mediano 3,85 $ e rischio 2% → circa **0,06 lotti** | — |
| Stop troppo largo | se lo stop supera **10 $** (100 pip), il lotto scende sotto 0,02: saltare il trade o ridurre il rischio | — |
| Limite giornaliero | massimo **2 trade al giorno** con questa strategia. Il segnale è raro e un secondo segnale nella stessa sessione è spesso rumore | [DA DEFINIRE] |
| Pausa dopo perdite | stop operativo dopo **7 perdite consecutive**, il massimo storico (5–7). Oltre 7 consecutive siamo fuori dalla statistica: rivedere | [DIMOSTRATO come soglia storica] |

## 1.2 Strategia operativa: "Primo impulso dopo lateralità, sessione di New York" (M30)

| Elemento | Regola | Stato |
|---|---|---|
| Strumento | XAUUSD | — |
| Timeframe | **M30** (M1–M5 esclusi: vedi §1.5) | [PLAUSIBILE] |
| Fascia oraria | candela impulso tra le **12:00 e le 16:00 UTC**. Italia: 13–17 in inverno, 14–18 in estate. Le 16:00 UTC sono negative in tutte le varianti (circa −0,3R) | [PLAUSIBILE] (le 16 sono escluse a posteriori: da verificare) |
| Lateralità | nessuna candela con range ≥ 2× la media nelle **20 candele precedenti** | [PLAUSIBILE] |
| Impulso | range ≥ **1,5–2×** la media delle 20 precedenti, **volume tick ≥ media**, corpo ≥ 60% del range | [PLAUSIBILE] |
| Pausa | almeno **1 candela** che non chiude oltre l'estremo dell'impulso e non ritraccia oltre il 50% dell'impulso | [PLAUSIBILE] |
| Ingresso | **ordine stop** 0,05 $ oltre l'estremo della struttura (impulso + pausa). Ordine valido per massimo 8 candele, cancellato se il prezzo ritraccia oltre il 50% | [PLAUSIBILE] |
| Notizie | nessun ingresso nei venerdì NFP 12:00–15:00 UTC. CPI/FOMC: [DA DEFINIRE] (manca il calendario storico) | [DA DEFINIRE] |

**Numeri storici della strategia (2017–2026, netti)**

| Variante | Trade/mese | Vincenti | Vincita media / perdita media | R medio | 1000 € → | Drawdown max | Max perdite consecutive |
|---|---|---|---|---|---|---|---|
| Impulso ≥ 1,5×, uscita a tempo (6 h) | 2,0 | 41% | +2,19R / −0,97R | **+0,32R** | 3217 € | 16% | 6 |
| Impulso ≥ 1,5×, TP 3R | 2,0 | 42% | +1,76R / −0,97R | +0,18R | 1911 € | 17% | 5 |
| Impulso ≥ 2×, uscita a tempo | 1,4 | 41% | +2,41R / −0,92R | +0,31R | 2243 € | 12% | 7 |

Limiti noti: circa 230 trade in 9 anni, t = 1,7–2,4. È stata selezionata tra molte varianti, il 17% dei mesi non ha trade e solo circa il 50% dei mesi è positivo: i guadagni arrivano da pochi mesi molto buoni.

## 1.3 Regole di ingresso e uscita

| Regola | Stato |
|---|---|
| **Stop loss** oltre la pausa (minimo/massimo delle candele di pausa ± 0,05 $). Mediana 3,85 $, 10° percentile 1,55 $, 90° percentile 12 $ | [PLAUSIBILE] |
| **Uscita principale: a tempo**, cioè 12 candele M30 (6 ore) o le 20:45 UTC se arrivano prima | [PLAUSIBILE] |
| Alternativa: TP fisso a 3R (rendimento più basso ma più regolare) | [PLAUSIBILE] |

## 1.4 Gestione delle posizioni

| Regola del piano originale | Cosa dicono i dati | Stato |
|---|---|---|
| Spostare a **break even** dopo un certo profitto | Su questa strategia **azzera il vantaggio** (da +0,32R a 0,00R): il movimento ha bisogno di respiro | [SMENTITO per questa strategia] |
| **Profitti parziali** (6 ordini, TP a scala 20–100 pip + runner in trailing) | Testato su 160 combinazioni: lordo circa 0, netto negativo in tutte. La scala cambia la forma dei risultati, non il valore atteso | [SMENTITO] |
| Trailing stop | Neutro o negativo rispetto all'uscita a tempo | [SMENTITO come miglioramento] |
| Non chiudere esattamente sui livelli tecnici | Già incluso: ingresso e stop a ± 0,05 $ dai livelli | — |

## 1.5 Cosa è stato testato e scartato (per non ripeterlo)

| Idea | Risultato | Stato |
|---|---|---|
| Scalping M1–M5 sulla rottura della lateralità con volume | Da 2 a 11 setup al giorno, ma il prezzo raggiunge i target **meno spesso del caso** (es. +10 $: 17% contro 22% atteso). Netto da −0,06 a −0,17R | [SMENTITO] |
| Contro la falsa rottura (fade) su M1–M5 | Lordo da 0 a +0,05R, netto negativo ovunque | [SMENTITO] |
| Tenere aperto in perdita "perché poi gira" | Già sotto di 3 $, la probabilità di arrivare a +6 $ è il 24%, contro il 20% di un ingresso casuale. Non c'è un effetto "torna indietro" da sfruttare | [SMENTITO] |
| Orari fissi, breakout del range di apertura Londra/NY, notizie NFP | Nessun vantaggio stabile | [SMENTITO] |
| Griglia di 17.040 varianti intraday | Nessuna supera la soglia statistica corretta. Il walk-forward non guadagna | [SMENTITO come metodo per scegliere a posteriori] |

# 2. Risultati e verifica

| Finestra | Metrica da controllare | Allarme |
|---|---|---|
| Settimanale | trade eseguiti contro segnali previsti (tutti i segnali vanno presi) | segnale saltato o preso fuori regola |
| Mensile | R totale, numero di trade, slippage medio reale contro 0,05 $ | slippage medio > 0,15 $ |
| Trimestrale | R medio per trade contro storico (+0,2/+0,3R) | R medio < 0 dopo **30 trade** |
| Dopo 50 trade | confronto statistico con il backtest | se il R medio è sotto −0,1R la strategia è da fermare |

# 3. Routine

- **Prima della sessione (12:00 UTC):** controllare il calendario macro. Niente ingressi 30 minuti prima e dopo CPI, FOMC e NFP.
- **12:00–16:00 UTC:** attendere solo il setup; nessun altro trade.
- **20:45 UTC:** tutto chiuso.
- **Fine giornata:** annotare il trade nel registro (vedi §4).

# 4. Analisi degli errori

Registro di ogni trade: data/ora, setup rispettato (sì/no), ingresso/stop/uscita previsti contro reali, slippage, errore (esecuzione / gestione / emotivo).

Regola anti-overfitting (dal tuo piano, confermata dai dati): **non cambiare i parametri** prima di 50 trade reali.

# 5. Regole di trading

Valgono integralmente le regole 5.1–5.10 del piano originale, con due precisazioni dai dati:

- **5.5 (gestione dinamica):** per questa strategia niente break even e niente parziali (vedi §1.4).
- **5.8 (non lasciare incustodito):** l'uscita è a tempo e lo stop è sempre a mercato, quindi un Expert Advisor può gestirla da solo.

# Prossimi passi per passare da [PLAUSIBILE] a [DIMOSTRATO]

1. Fuso orario del server BCM, per convertire esattamente la fascia oraria.
2. Stesse regole su argento e indici USA (prova indipendente e più trade).
3. Expert Advisor MQL5 in **demo** per 3–6 mesi, o almeno 30–50 trade.
