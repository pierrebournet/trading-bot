import argparse, time, json, math
from datetime import datetime
import pandas as pd
import requests

BACKEND_URL = "https://backend-1055832982794.europe-west1.run.app/bot/strategy"

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0).rolling(period).mean()
    down = (-delta.clip(upper=0)).rolling(period).mean()
    rs = up / (down.replace(0, 1e-9))
    return 100 - (100 / (1 + rs))

def load_data(path, start=None, end=None):
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    need = ["timestamp","open","high","low","close","volume"]
    for n in need:
        if n not in [c.lower() for c in df.columns]:
            raise ValueError(f"Colonne manquante: {n}")
    df["timestamp"] = pd.to_datetime(df[cols["timestamp"]], utc=True)
    df = df.rename(columns={cols["open"]:"open", cols["high"]:"high",
                            cols["low"]:"low", cols["close"]:"close",
                            cols["volume"]:"volume"})
    if start:
        df = df[df["timestamp"] >= pd.to_datetime(start, utc=True)]
    if end:
        df = df[df["timestamp"] <= pd.to_datetime(end, utc=True)]
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def compute_indicators(df, short=10, long=30, rsi_len=14):
    df["short_ma"] = df["close"].rolling(short).mean()
    df["long_ma"]  = df["close"].rolling(long).mean()
    df["rsi"] = rsi(df["close"], period=rsi_len)
    df["support"] = df["low"].rolling(long).min()
    df["resistance"]= df["high"].rolling(long).max()
    return df

def run_replay(csv_path, speed, sleep_sec, start=None, end=None):
    df = load_data(csv_path, start, end)
    df = compute_indicators(df)

    sent = 0
    for _, row in df.iterrows():
        if math.isnan(row["short_ma"]) or math.isnan(row["long_ma"]) or math.isnan(row["rsi"]):
            continue
        market_data = {
            "price": float(row["close"]),
            "resistance": float(row["resistance"]),
            "support": float(row["support"]),
            "short_ma": float(row["short_ma"]),
            "long_ma": float(row["long_ma"]),
            "rsi": float(row["rsi"]),
            "timestamp": row["timestamp"].isoformat(),
        }
        try:
            resp = requests.post(BACKEND_URL, json=market_data, timeout=10)
            resp.raise_for_status()
            decision = resp.json()
            print(f"[{row['timestamp']}] sent -> decision={decision}")
        except Exception as e:
            print(f"POST error: {e}")

        time.sleep(sleep_sec / max(speed, 1))
        sent += 1

    print(f"Replay terminé. Bougies envoyées: {sent}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Replay feeder -> backend")
    p.add_argument("--file", required=True, help="Chemin CSV OHLCV")
    p.add_argument("--speed", type=float, default=1.0, help=">1 = plus rapide")
    p.add_argument("--sleep", type=float, default=1.0, help="secondes entre bougies (avant speed)")
    p.add_argument("--start", type=str, default=None, help="ISO start (ex: 2024-03-01T14:30:00Z)")
    p.add_argument("--end", type=str, default=None, help="ISO end")
    args = p.parse_args()

    run_replay(args.file, args.speed, args.sleep, start=args.start, end=args.end)
