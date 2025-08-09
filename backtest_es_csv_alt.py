# backtest_es_csv_alt.py
# Bouton B (agressif) : 3 stratégies + grid search léger + money management agressif

import argparse
import pandas as pd
import numpy as np
from itertools import product

POINT_VALUE = {"MES": 5.0, "ES": 50.0}

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def strategy_ema_crossover(df, fast=8, slow=21):
    f = ema(df["close"], fast)
    s = ema(df["close"], slow)
    sig = pd.Series(0, index=df.index)
    sig[(f > s) & (f.shift(1) <= s.shift(1))] = 1   # buy cross up
    sig[(f < s) & (f.shift(1) >= s.shift(1))] = -1  # sell cross down
    return sig.rename("ema_x")

def strategy_breakout_range(df, lookback=15, buffer=0.0):
    hh = df["high"].rolling(lookback).max().shift(1)
    ll = df["low"].rolling(lookback).min().shift(1)
    up_break = (df["close"] > (hh + buffer))
    dn_break = (df["close"] < (ll - buffer))
    sig = pd.Series(0, index=df.index)
    sig[up_break] = 1
    sig[dn_break] = -1
    return sig.rename("brk")

def strategy_pullback(df, impulse_look=10, retrace=0.5):
    """Impulse haussière -> pullback ~50% -> long ; inverse pour short"""
    rolling_max = df["close"].rolling(impulse_look).max()
    rolling_min = df["close"].rolling(impulse_look).min()
    # Détection impulsion haussière
    prev_peak = rolling_max.shift(1)
    prev_trough = rolling_min.shift(1)
    baseline = df["close"].shift(impulse_look)
    sig = pd.Series(0, index=df.index)
    # Long: on est en dessous du milieu de l’impulsion mais au-dessus du creux
    mid_up = ((prev_peak - prev_trough) * retrace + prev_trough)
    cond_long = (baseline.notna()) & (df["close"] <= mid_up) & (df["close"] > prev_trough)
    # Short symétrique
    mid_dn = (prev_peak - (prev_peak - prev_trough) * retrace)
    cond_short = (baseline.notna()) & (df["close"] >= mid_dn) & (df["close"] < prev_peak)
    sig[cond_long] = 1
    sig[cond_short] = -1
    return sig.rename("pb")

def simulate(df, signals, atr_mult_sl=1.5, rr_target=1.5, trail_mult=1.0,
             contracts=5, symbol="MES", fee_per_contract=1.0):
    """
    Exécute un seul trade à la fois. Entrée à close du signal.
    SL = ATR*atr_mult_sl, TP = RR*SL ; Trailing au fur et à mesure (trail_mult*ATR courant).
    """
    pv = POINT_VALUE.get(symbol.upper(), 5.0)
    df = df.copy()
    df["atr"] = atr(df, 14)
    # Agrège plusieurs signaux : priorité EMA > Breakout > Pullback le même bar
    agg = pd.Series(0, index=df.index)
    # priorité simple (tu peux changer l’ordre)
    for col in ["ema_x", "brk", "pb"]:
        if col in signals.columns:
            agg = agg.where(agg != 0, signals[col])

    in_trade = False
    direction = 0
    entry = sl = tp = None
    eq = 0.0
    equity_curve = []
    records = []

    for i in range(len(df)):
        ts, o,h,l,c, a = df.index[i], df["open"].iat[i], df["high"].iat[i], df["low"].iat[i], df["close"].iat[i], df["atr"].iat[i]
        signal = 0 if pd.isna(agg.iat[i]) else int(agg.iat[i])

        # Gère trailing si en position
        if in_trade:
            # trailing pour un long : remonte SL
            if direction == 1 and not pd.isna(a):
                trail = c - trail_mult * a
                sl = max(sl, trail)
            # trailing pour un short : abaisse SL
            if direction == -1 and not pd.isna(a):
                trail = c + trail_mult * a
                sl = min(sl, trail)

            # Check stop / tp avec range de la bougie
            exit_reason = None
            exit_price = None
            if direction == 1:
                # SL touché ?
                if not pd.isna(sl) and l <= sl:
                    exit_price = sl
                    exit_reason = "SL"
                # TP touché ?
                elif not pd.isna(tp) and h >= tp:
                    exit_price = tp
                    exit_reason = "TP"
            else:  # short
                if not pd.isna(sl) and h >= sl:
                    exit_price = sl
                    exit_reason = "SL"
                elif not pd.isna(tp) and l <= tp:
                    exit_price = tp
                    exit_reason = "TP"

            # Si sorti
            if exit_price is not None:
                pnl_pts = (exit_price - entry) * direction
                pnl_usd = pnl_pts * pv * contracts
                fees = fee_per_contract * contracts * 2  # aller/retour
                eq += (pnl_usd - fees)
                records.append([ts, direction, entry, exit_price, pnl_pts, pnl_usd, fees, exit_reason])
                in_trade = False
                direction = 0
                entry = sl = tp = None

        # Si pas en trade, peut-on entrer ?
        if not in_trade and signal != 0 and not pd.isna(a) and a > 0:
            direction = signal
            entry = c
            risk_pts = atr_mult_sl * a
            sl = entry - risk_pts if direction == 1 else entry + risk_pts
            tp = entry + rr_target * risk_pts if direction == 1 else entry - rr_target * risk_pts
            # frais d’entrée (on les déduira à la sortie avec aller/retour simplifié)
            in_trade = True

        equity_curve.append([ts, eq])

    trades = pd.DataFrame(records, columns=["timestamp","direction","entry","exit","pnl_pts","pnl_usd","fees","exit_reason"])
    equity = pd.DataFrame(equity_curve, columns=["timestamp","equity"])
    wins = (trades["pnl_usd"] > 0).sum()
    total = len(trades)
    winrate = 100.0 * wins / total if total > 0 else 0.0
    return eq, winrate, total, trades, equity

def run_grid(df, contracts, symbol):
    # Grille légère de paramètres
    ema_fast_list = [8, 12]
    ema_slow_list = [21, 26]
    brk_look_list = [10, 20]
    atr_mult_list = [1.2, 1.5, 2.0]
    rr_list = [1.2, 1.5, 2.0]
    trail_list = [0.5, 1.0]

    best = None
    best_detail = None

    for f,s,lb,am,rr,tr in product(ema_fast_list, ema_slow_list, brk_look_list, atr_mult_list, rr_list, trail_list):
        sig_ema = strategy_ema_crossover(df, f, s)
        sig_brk = strategy_breakout_range(df, lb, buffer=0.0)
        sig_pb  = strategy_pullback(df, impulse_look=10, retrace=0.5)
        sigs = pd.concat([sig_ema, sig_brk, sig_pb], axis=1)

        eq, wr, n, trades, equity = simulate(
            df, sigs,
            atr_mult_sl=am, rr_target=rr, trail_mult=tr,
            contracts=contracts, symbol=symbol
        )
        score = (eq, wr, n)  # priorité PnL, puis winrate, puis nb trades
        if (best is None) or (score > best):
            best = score
            best_detail = {
                "ema_fast": f, "ema_slow": s, "brk_look": lb,
                "atr_mult": am, "rr": rr, "trail_mult": tr,
                "eq": eq, "winrate": wr, "trades": n,
                "trades_df": trades, "equity_df": equity
            }
    return best_detail

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="Chemin du CSV (colonnes: timestamp, open, high, low, close, volume)")
    ap.add_argument("--symbol", default="MES", help="MES (5$/pt) ou ES (50$/pt)")
    ap.add_argument("--contracts", type=int, default=5, help="Nb de contrats (agressif)")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    # Colonnes attendues
    # Normalise noms
    df.columns = [c.strip().lower() for c in df.columns]
    # timestamp en datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").set_index("timestamp")
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").set_index("datetime")
        df.index.name = "timestamp"
    else:
        raise ValueError("Aucune colonne timestamp/datetime trouvée.")

    for col in ["open","high","low","close"]:
        if col not in df.columns:
            raise ValueError(f"Colonne requise manquante: {col}")

    best = run_grid(df, contracts=args.contracts, symbol=args.symbol)

    # Sauvegardes
    base = args.csv.rsplit(".",1)[0]
    trades_csv = f"{base}_alt_trades.csv"
    equity_csv = f"{base}_alt_equity.csv"
    best["trades_df"].to_csv(trades_csv, index=False)
    best["equity_df"].to_csv(equity_csv, index=False)

    pv = POINT_VALUE.get(args.symbol.upper(), 5.0)
    kept = 0.90  # 90% gardé après prop-fee
    kept_usd = best["eq"] * kept

    print(f"🔧 Meilleurs params -> EMA({best['ema_fast']}/{best['ema_slow']}), Breakout LB={best['brk_look']}, "
          f"ATR*SL={best['atr_mult']}, RR={best['rr']}, Trail={best['trail_mult']}*ATR")
    print(f"📊 Trades: {best['trades']} | Win rate: {best['winrate']:.1f}%")
    print(f"💰 PnL cumulé: ${best['eq']:.2f}   (contrats={args.contracts}, symbol={args.symbol}, point=${pv:.0f})")
    print(f"🏦 Après prélèvement 10% prop: ${kept_usd:.2f} (tu gardes 90%)")
    print(f"📝 Détails -> {trades_csv} | 📈 Equity -> {equity_csv}")

if __name__ == "__main__":
    main()
