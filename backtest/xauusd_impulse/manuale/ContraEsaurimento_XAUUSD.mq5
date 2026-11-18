// !!! RITIRATO 18/11/2026: strategia NON profittevole (errore di simulazione). NON USARE. !!!
//+------------------------------------------------------------------+
//| ContraEsaurimento_XAUUSD.mq5                                     |
//| Strategia "Contro l'esaurimento" su XAUUSD M3 (v1)               |
//| Regole identiche al backtest Python 2017-2026:                   |
//|  - candela chiusa con range >= 3x media range 20 candele prec.   |
//|  - corpo >= 60% del range                                        |
//|  - RSI(14) a chiusura >= 75 (candela rialzista) -> SELL          |
//|                       <= 25 (candela ribassista) -> BUY          |
//|  - media range 20 candele ("ATR") >= ATRMinUSD                   |
//|  - ingresso a mercato all'apertura della candela successiva      |
//|  - SL = TP = 0.5 x ATR, uscita a tempo dopo 12 candele           |
//|  - nessun ingresso 20:00-24:00 UTC, chiusura forzata 20:45 UTC   |
//|  - nessun ingresso venerdi NFP 12:00-15:00 UTC                   |
//| Usare su grafico XAUUSD M3. Registra ogni trade in CSV           |
//| (cartella Common\Files) per misurare lo slippage reale in demo.  |
//+------------------------------------------------------------------+
#property copyright "Backtest research"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input double RiskPercent      = 1.0;    // Rischio per trade (% equity)
input double RangeMult        = 3.0;    // Range candela segnale >= X volte la media
input double BodyMin          = 0.60;   // Corpo minimo (frazione del range)
input int    AvgBars          = 20;     // Candele per la media del range (ATR)
input int    RSIPeriod        = 14;     // Periodo RSI
input double RSILevel         = 75.0;   // Soglia RSI (speculare 100-X per i BUY)
input double ATRMinUSD        = 1.5;    // Filtro volatilita': media range minima in $ (prudente 2.5)
input double SLTP_ATR         = 0.5;    // Stop loss e take profit in multipli di ATR
input int    MaxBarsInTrade   = 12;     // Uscita a tempo dopo N candele
input int    LastEntryHourUTC = 20;     // Nessun ingresso da quest'ora UTC in poi
input int    FlatHourUTC      = 20;     // Chiusura forzata (ora UTC)
input int    FlatMinuteUTC    = 45;     // Chiusura forzata (minuti)
input bool   SkipNFP          = true;   // Salta il primo venerdi del mese 12-15 UTC
input int    ServerGMTOffset  = 1;      // SOLO Strategy Tester: fuso del server (BCM inverno = 1)
input double MaxSpreadUSD     = 0.60;   // Non entrare se lo spread supera X $ (sicurezza)
input int    DeviationPoints  = 30;     // Slippage massimo accettato (punti)
input long   MagicNumber      = 26111801;
input bool   LogCSV           = true;   // Registra i trade in Common\Files\ContraEsaurimento_log.csv

CTrade   trade;
int      rsiHandle = INVALID_HANDLE;
datetime lastBarTime = 0;
datetime entryBarTime = 0;

//--- ora UTC: dal vivo usa TimeGMT(); nel tester TimeGMT() = ora server, quindi si usa l'offset
long ServerOffsetSec()
{
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return (long)ServerGMTOffset * 3600;
   long d = (long)(TimeTradeServer() - TimeGMT());
   return (long)MathRound((double)d / 3600.0) * 3600;
}
datetime ToUTC(datetime serverTime) { return (datetime)((long)serverTime - ServerOffsetSec()); }

bool IsNFPWindow(datetime utc)
{
   MqlDateTime t; TimeToStruct(utc, t);
   return (t.day_of_week == 5 && t.day <= 7 && t.hour >= 12 && t.hour < 15);
}

bool HasPosition(ulong &ticket)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
      { ticket = tk; return true; }
   }
   return false;
}

double LotsForRisk(double slDistance)
{
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickValue <= 0 || tickSize <= 0 || slDistance <= 0) return 0;
   double riskMoney   = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0;
   double lossPerLot  = slDistance / tickSize * tickValue;
   double lots        = MathFloor(riskMoney / lossPerLot / step) * step;
   if(lots < vmin) return 0;            // rischio troppo alto anche con il lotto minimo: si salta
   return MathMin(lots, vmax);
}

void Log(string what, double requested, double filled, double sl, double tp, double lots, double atr, double spread)
{
   if(!LogCSV) return;
   int h = FileOpen("ContraEsaurimento_log.csv", FILE_READ | FILE_WRITE | FILE_CSV | FILE_COMMON | FILE_SHARE_READ, ';');
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0)
      FileWrite(h, "server_time", "utc_time", "evento", "prezzo_richiesto", "prezzo_eseguito", "slippage_usd", "sl", "tp", "lotti", "atr", "spread");
   FileSeek(h, 0, SEEK_END);
   datetime now = TimeCurrent();
   FileWrite(h, TimeToString(now, TIME_DATE | TIME_SECONDS), TimeToString(ToUTC(now), TIME_DATE | TIME_SECONDS), what,
             DoubleToString(requested, _Digits), DoubleToString(filled, _Digits), DoubleToString(filled - requested, _Digits),
             DoubleToString(sl, _Digits), DoubleToString(tp, _Digits), DoubleToString(lots, 2), DoubleToString(atr, 2), DoubleToString(spread, 2));
   FileClose(h);
}

int OnInit()
{
   if(_Period != PERIOD_M3) Print("ATTENZIONE: la strategia e' stata testata su M3. Timeframe attuale: ", EnumToString(_Period));
   rsiHandle = iRSI(_Symbol, _Period, RSIPeriod, PRICE_CLOSE);
   if(rsiHandle == INVALID_HANDLE) { Print("Errore creazione RSI"); return INIT_FAILED; }
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(DeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle); }

void OnTick()
{
   datetime utcNow = ToUTC(TimeCurrent());
   MqlDateTime u; TimeToStruct(utcNow, u);

   //--- gestione posizione aperta: uscita a tempo e chiusura serale
   ulong tk;
   if(HasPosition(tk))
   {
      bool flat = (u.hour > FlatHourUTC) || (u.hour == FlatHourUTC && u.min >= FlatMinuteUTC);
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      bool timeout = (TimeCurrent() - opened) >= (long)MaxBarsInTrade * PeriodSeconds(_Period);
      if(flat || timeout)
      {
         double px = PositionGetDouble(POSITION_PRICE_CURRENT);
         if(trade.PositionClose(tk)) Log(flat ? "CHIUSURA_20:45" : "CHIUSURA_TEMPO", px, trade.ResultPrice(), 0, 0, 0, 0, 0);
      }
   }

   //--- nuova candela?
   datetime bt = iTime(_Symbol, _Period, 0);
   if(bt == lastBarTime) return;
   lastBarTime = bt;

   if(HasPosition(tk)) return;                       // una posizione alla volta

   //--- filtri orari (sull'ora UTC di apertura della nuova candela = ingresso)
   datetime barUTC = ToUTC(bt);
   MqlDateTime b; TimeToStruct(barUTC, b);
   if(b.day_of_week == 0 || b.day_of_week == 6) return;
   if(b.hour >= LastEntryHourUTC) return;
   if(SkipNFP && IsNFPWindow(barUTC)) return;

   //--- candela segnale = indice 1 (appena chiusa); media range delle 20 precedenti = indici 2..21
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, _Period, 0, AvgBars + 3, r) < AvgBars + 3) return;
   double sum = 0;
   for(int i = 2; i < 2 + AvgBars; i++) sum += (r[i].high - r[i].low);
   double atr = sum / AvgBars;
   double rng = r[1].high - r[1].low;
   double body = MathAbs(r[1].close - r[1].open);
   if(atr < ATRMinUSD || rng <= 0) return;
   if(rng < RangeMult * atr) return;
   if(body < BodyMin * rng) return;

   double rsi[];
   ArraySetAsSeries(rsi, true);
   if(CopyBuffer(rsiHandle, 0, 1, 1, rsi) != 1) return;

   bool bull = r[1].close > r[1].open;
   bool sellSignal = bull && rsi[0] >= RSILevel;
   bool buySignal  = !bull && rsi[0] <= 100.0 - RSILevel;
   if(!sellSignal && !buySignal) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double spread = ask - bid;
   if(spread > MaxSpreadUSD) { Print("Segnale saltato: spread ", spread); return; }

   double dist = SLTP_ATR * atr;
   double lots = LotsForRisk(dist + spread);
   if(lots <= 0) { Print("Segnale saltato: lotto sotto il minimo per il rischio impostato"); return; }

   if(sellSignal)
   {
      double sl = NormalizeDouble(bid + dist, _Digits), tp = NormalizeDouble(bid - dist, _Digits);
      if(trade.Sell(lots, _Symbol, 0, sl, tp, "ContraEsaurimento SELL"))
         Log("SELL", bid, trade.ResultPrice(), sl, tp, lots, atr, spread);
   }
   else
   {
      double sl = NormalizeDouble(ask - dist, _Digits), tp = NormalizeDouble(ask + dist, _Digits);
      if(trade.Buy(lots, _Symbol, 0, sl, tp, "ContraEsaurimento BUY"))
         Log("BUY", ask, trade.ResultPrice(), sl, tp, lots, atr, spread);
   }
}
//+------------------------------------------------------------------+
