# backtest_es_csv.py
import pandas as pd
from pathlib import Path

CSV_PATH = "ES_F_1m_7jours_16h_17h30_FR.csv"  # ton fichier téléchargé
SHORT_MA = 20
LONG_MA = 50
RSI_PERIOD = 14
ROLL_WINDOW = 20          # pour support/résistance
MAX_HOLD_BARS = 10
POINT_VALUE = 5           # $/point (MES = 5$, ES = 50$). Change si tu backtestes ES.
CONTRACTS = 1

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, 1e-12))
    return 100 - (100 / (1 + rs))

def decide(mkt):
    """
    Même logique simple que nos 3 stratégies de démo:
    - Breakout: prix > resistance => BUY ; prix < support => SELL
    - MA: short_ma > long_ma => BUY ; short_ma < long_ma => SELL
    - RSI: rsi<30 => BUY ; rsi>70 => SELL
    On renvoie le 1er signal “fort” trouvé, sinon HOLD.
    """
    price = mkt["price"]
    res = mkt["resistance"]
    sup = mkt["support"]
    sma = mkt["short_ma"]
    lma = mkt["long_ma"]
    r = mkt["rsi"]

    # 1) Breakout
    if price > res:
        return "BUY", "breakout_up"
    if price < sup:
        return "SELL", "breakout_down"

    # 2) MA crossover
    if sma > lma:
        return "BUY", "ma_crossover_up"
    if sma < lma:
        return "SELL", "ma_crossover_down"

    # 3) RSI bornes
    if r < 30:
        return "BUY", "rsi_oversold"
    if r > 70:
        return "SELL", "rsi_overbought"

    return "HOLD", "neutral"

def main():
    path = Path(CSV_PATH)
    if not path.exists():
        print(f"❌ Fichier introuvable: {path.resolve()}")
        return

    df = pd.read_csv(path, parse_dates=["timestamp"])
    # On s’assure des colonnes attendues
    needed = {"timestamp","open","high","low","close","volume"}
    if not needed.issubset(set(map(str.lower, df.columns))):
        print("❌ Le CSV doit contenir: timestamp, open, high, low, close, volume")
        return

    # normalise les noms
    df.columns = [c.lower() for c in df.columns]

    # Indicateurs
    df["short_ma"] = df["close"].rolling(SHORT_MA).mean()
    df["long_ma"]  = df["close"].rolling(LONG_MA).mean()
    df["rsi"]      = rsi(df["close"], RSI_PERIOD)
    df["resistance"] = df["high"].rolling(ROLL_WINDOW).max().shift(1)  # résistance du passé
    df["support"]    = df["low"].rolling(ROLL_WINDOW).min().shift(1)   # support du passé

    # On démarre après le “warm-up” des indicateurs
    start_idx = max(SHORT_MA, LONG_MA, RSI_PERIOD, ROLL_WINDOW) + 1

    position = None   # None / "LONG" / "SHORT"
    entry_price = None
    entry_time = None
    bars_held = 0

    trades = []
    equity = []
    cum_pnl_points = 0.0
    cum_pnl_dollars = 0.0

    for i in range(start_idx, len(df)-1):  # -1 pour disposer du "next close"
        row = df.iloc[i]
        ts = row["timestamp"]
        price = row["close"]
        mkt = {
            "price": price,
            "resistance": row["resistance"],
            "support": row["support"],
            "short_ma": row["short_ma"],
            "long_ma": row["long_ma"],
            "rsi": row["rsi"]
        }
        signal, reason = decide(mkt)

        exit_now = False
        exit_reason = None

        # Si en position, on regarde sortie
        if position is not None:
            bars_held += 1
            # Opposite signal -> sortie
            if (position == "LONG" and signal == "SELL") or (position == "SHORT" and signal == "BUY"):
                exit_now = True
                exit_reason = "opposite_signal"
            # Ou temps max en barres
            elif bars_held >= MAX_HOLD_BARS:
                exit_now = True
                exit_reason = "time_exit"

            if exit_now:
                next_close = df.iloc[i+1]["close"]  # exécution au close suivant
                if position == "LONG":
                    pnl_points = (next_close - entry_price)
                else:
                    pnl_points = (entry_price - next_close)
                pnl_dollars = pnl_points * POINT_VALUE * CONTRACTS
                cum_pnl_points += pnl_points
                cum_pnl_dollars += pnl_dollars

                trades.append({
                    "entry_time": entry_time,
                    "exit_time": df.iloc[i+1]["timestamp"],
                    "side": position,
                    "entry_price": entry_price,
                    "exit_price": next_close,
                    "pnl_points": pnl_points,
                    "pnl_dollars": pnl_dollars,
                    "exit_reason": exit_reason,
                    "bars_held": bars_held
                })

                position = None
                entry_price = None
                entry_time = None
                bars_held = 0

        # Si pas en position, on peut entrer
        if position is None and signal in ("BUY", "SELL"):
            position = "LONG" if signal == "BUY" else "SHORT"
            entry_price = price
            entry_time = ts
            bars_held = 0

        equity.append({
            "timestamp": ts,
            "cum_pnl_points": cum_pnl_points,
            "cum_pnl_dollars": cum_pnl_dollars
        })

    # Résultats
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity)

    if not trades_df.empty:
        wins = (trades_df["pnl_dollars"] > 0).sum()
        total = len(trades_df)
        winrate = 100.0 * wins / total
        print(f"📊 Trades: {total} | ✅ Gains: {wins} | Win rate: {winrate:.1f}%")
        print(f"💰 PnL cumulé: {cum_pnl_points:.2f} pts  (~${cum_pnl_dollars:.2f})  "
              f"avec {CONTRACTS} contrat(s), {POINT_VALUE}$/pt")
    else:
        print("⚠️ Aucun trade généré (fenêtre trop courte ou règles trop strictes).")

    trades_csv = "backtest_es_trades.csv"
    equity_csv = "backtest_es_equity.csv"
    trades_df.to_csv(trades_csv, index=False)
    equity_df.to_csv(equity_csv, index=False)
    print(f"📝 Détails des trades -> {trades_csv}")
    print(f"📈 Courbe d’equity -> {equity_csv}")

if __name__ == "__main__":
    main()
