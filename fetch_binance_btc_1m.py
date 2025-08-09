# fetch_binance_btc_1m.py
import pandas as pd
import requests
import time
from datetime import datetime

symbol = "BTCUSDT"
interval = "1m"  # bougies 1 minute
start_date = "2025-08-01"
end_date = "2025-08-08"

# Convertir en timestamps
start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

url = "https://api.binance.com/api/v3/klines"

all_klines = []
limit = 1000
current_ts = start_ts

while current_ts < end_ts:
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": current_ts,
        "endTime": end_ts,
        "limit": limit
    }
    resp = requests.get(url, params=params)
    data = resp.json()

    if not data:
        break

    all_klines.extend(data)
    current_ts = data[-1][0] + 60_000  # +1 min
    time.sleep(0.5)  # éviter d'être bloqué par l'API

# Convertir en DataFrame
df = pd.DataFrame(all_klines, columns=[
    "timestamp", "open", "high", "low", "close", "volume", 
    "close_time", "quote_asset_volume", "number_of_trades", 
    "taker_buy_base", "taker_buy_quote", "ignore"
])

# Convertir timestamp en lisible
df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

# Sauvegarder en CSV
output_file = f"BTCUSDT_1m_{start_date}_to_{end_date}.csv"
df.to_csv(output_file, index=False)

print(f"✅ Données sauvegardées dans {output_file} ({len(df)} lignes)")

