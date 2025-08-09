# backtest_es_csv_risk.py
import sys, math
import pandas as pd
import numpy as np

# === Paramètres marché / contrat (ES futures mini) ===
TICK_VALUE = 5.0          # $/point
POINTS_PER_TRADE_FEE = 1  # frais+slippage (points aller-retour)

# === Fenêtre horaire (Europe/Paris déjà dans tes CSV Yahoo) ===
START = "16:00:00"
END   = "17:30:00"

# === Risk config ===
ATR_LEN = 14
ATR_MIN = 0.5   # ignore si trop calme
ATR_MAX = 8.0   # ignore si trop violent
RISK_PER_TRADE = 0.005  # 0.5% du capital
MAX_CONSEC_LOSSES = 3
MAX_DAILY_LOSS_PTS = 20.0
DAILY_PROFIT_LOCK_PTS = 30.0
MAX_CONTRACTS = 2
MIN_CONTRACTS = 1

def rsi(series, length=14):
    delta = series.diff()
    up = np.where(delta>0, delta, 0.0)
    dn = np.where(delta<0, -delta, 0.0)
    roll_up = pd.Series(up, index=series.index).ewm(alpha=1/length, adjust=False).mean()
    roll_dn = pd.Series(dn, index=series.index).ewm(alpha=1/length, adjust=False).mean()
    rs = roll_up / (roll_dn.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def true_range(df):
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        (df['high'] - df['low']),
        (df['high'] - prev_close).abs(),
        (df['low'] - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr

def atr(df, length=14):
    tr = true_range(df)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def position_size(capital, stop_pts):
    if stop_pts <= 0: 
        return 0
    risk_dollars = capital * RISK_PER_TRADE
    dollars_per_contract = stop_pts * TICK_VALUE
    contracts = math.floor(risk_dollars / dollars_per_contract)
    return int(max(MIN_CONTRACTS, min(MAX_CONTRACTS, contracts)))

def backtest(csv_path):
    df = pd.read_csv(csv_path)
    # colonnes attendues: timestamp, open, high, low, close, volume
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    # fenêtre horaire
    df = df[(df['timestamp'].dt.time >= pd.to_datetime(START).time()) &
            (df['timestamp'].dt.time <= pd.to_datetime(END).time())].copy()
    if df.empty:
        print("❌ Aucune donnée dans la fenêtre horaire.")
        return

    df['rsi'] = rsi(df['close'], 14)
    df['atr'] = atr(df, ATR_LEN)

    capital = 50000.0
    equity = [capital]
    trades = []
    daily_pl_pts = 0.0
    consec_losses = 0

    in_pos = False
    side = None
    entry = None
    stop = None
    target = None
    contracts = 0
    last_trade_minute = None

    for i, row in df.iterrows():
        ts = row['timestamp']
        c  = row['close']
        h  = row['high']
        l  = row['low']
        a  = row['atr']
        r  = row['rsi']

        # stop-day guards
        if daily_pl_pts <= -MAX_DAILY_LOSS_PTS: break
        if daily_pl_pts >=  DAILY_PROFIT_LOCK_PTS: break
        if consec_losses >= MAX_CONSEC_LOSSES: break

        # sortie si en position
        if in_pos:
            # check stop/target
            exit_price = None
            reason = None
            if side == 'LONG':
                if l <= stop:
                    exit_price = stop
                    reason = 'SL'
                elif h >= target:
                    exit_price = target
                    reason = 'TP'
            else:
                if h >= stop:
                    exit_price = stop
                    reason = 'SL'
                elif l <= target:
                    exit_price = target
                    reason = 'TP'

            if exit_price is not None:
                gross_pts = (exit_price - entry) if side=='LONG' else (entry - exit_price)
                net_pts   = gross_pts - POINTS_PER_TRADE_FEE
                pnl_usd   = net_pts * TICK_VALUE * contracts
                capital  += pnl_usd
                equity.append(capital)
                daily_pl_pts += net_pts * contracts
                consec_losses = 0 if net_pts > 0 else consec_losses + 1

                trades.append({
                    'timestamp': ts,
                    'side': side,
                    'entry': entry,
                    'exit': exit_price,
                    'reason': reason,
                    'contracts': contracts,
                    'gross_pts': round(gross_pts,2),
                    'net_pts': round(net_pts,2),
                    'pnl_usd': round(pnl_usd,2),
                    'capital': round(capital,2)
                })
                in_pos = False
                side = entry = stop = target = None
                contracts = 0
                continue  # pas de nouvelle entrée sur la même bougie

        # pas d’entrée si conditions non réunies
        if in_pos: 
            continue
        if pd.isna(a) or a < ATR_MIN or a > ATR_MAX:
            continue

        minute_key = ts.floor('T')
        if last_trade_minute is not None and minute_key == last_trade_minute:
            continue  # cooldown même minute

        # signal RSI
        go_long  = r < 30
        go_short = r > 70

        if go_long:
            stop_pts = max(a, 0.5)
            tp_pts   = 1.5 * stop_pts
            cts = position_size(capital, stop_pts)
            if cts > 0:
                in_pos = True
                side = 'LONG'
                entry = c
                stop = entry - stop_pts
                target = entry + tp_pts
                contracts = cts
                last_trade_minute = minute_key

        elif go_short:
            stop_pts = max(a, 0.5)
            tp_pts   = 1.5 * stop_pts
            cts = position_size(capital, stop_pts)
            if cts > 0:
                in_pos = True
                side = 'SHORT'
                entry = c
                stop = entry + stop_pts
                target = entry - tp_pts
                contracts = cts
                last_trade_minute = minute_key

        equity.append(capital)

    # stats
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame({'timestamp': pd.Series(equity).index, 'equity': equity})

    wins = (trades_df['pnl_usd'] > 0).sum() if not trades_df.empty else 0
    total = len(trades_df)
    winrate = (wins/total*100) if total>0 else 0
    pnl_pts = trades_df['net_pts'].sum() if not trades_df.empty else 0
    pnl_usd = trades_df['pnl_usd'].sum() if not trades_df.empty else 0

    trades_df.to_csv('backtest_es_trades_risk.csv', index=False)
    equity_df.to_csv('backtest_es_equity_risk.csv', index=False)

    print(f"📊 Trades: {total} | ✅ Gains: {wins} | Win rate: {winrate:.1f}%")
    print(f"💰 PnL cumulé: {pnl_pts:.2f} pts  (~${pnl_usd:.2f})  avec sizing dynamique, frais inclus")
    print("📝 Détails -> backtest_es_trades_risk.csv | 📈 Equity -> backtest_es_equity_risk.csv")

if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv)>1 else "ES_F_5m_30d_16h00_17h30_FR.csv"
    backtest(csv)
