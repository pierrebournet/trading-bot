# replay_feeder_window.py
import csv, json, time, requests
from datetime import datetime, time as dtime, timezone

BACKEND_URL = "https://backend-1055832982794.europe-west1.run.app/bot/strategy"
CSV_PATH = "data/mes_2m_2024.csv"  # <-- ton fichier (mets le bon chemin)

# Fenêtre heure FR (16:00 -> 17:30)
START_FR = dtime(16, 0)
END_FR   = dtime(17, 30)

def in_window_utc(ts_iso: str) -> bool:
    """
    Attend un timestamp ISO en UTC, ex: 2024-06-12T16:02:00Z
    (Si ton CSV est déjà en heure FR, retire la conversion ou adapte.)
    """
    # Convertit la chaîne ISO 'Z' en objet datetime UTC
    dt_utc = datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    # ⚠️ Simplification: on compare l'heure UTC à la fenêtre FR.
    # Pour être ultra exact avec les décalages saisonniers, remplace par un champ heure FR dans le CSV,
    # ou utilise zoneinfo("Europe/Paris") pour convertir.
    t = dt_utc.time()
    return START_FR <= t <= END_FR

def row_to_payload(row: dict) -> dict:
    """
    Adapte ici les noms de colonnes à ton CSV.
    Exemples possibles: open, high, low, close, ma_short, ma_long, rsi, resistance, support, timestamp
    """
    price = float(row.get("close") or row.get("price"))
    short_ma = float(row.get("ma_short", price))
    long_ma  = float(row.get("ma_long",  price))
    rsi      = float(row.get("rsi",      50))
    resistance = float(row.get("resistance", price + 3))
    support    = float(row.get("support",    price - 3))

    return {
        "price": price,
        "resistance": resistance,
        "support": support,
        "short_ma": short_ma,
        "long_ma": long_ma,
        "rsi": rsi
    }

def main():
    sent = 0
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp")  # ex: "2024-06-12T16:02:00Z"
            if not ts:
                continue
            if not in_window_utc(ts):
                continue

            payload = row_to_payload(row)
            try:
                resp = requests.post(BACKEND_URL, json=payload, timeout=5)
                print(ts, resp.status_code, resp.text)
                sent += 1
                time.sleep(0.2)  # cadence (~5 req/s); ajuste si besoin
            except Exception as e:
                print("ERR", e)
    print("Envoyé:", sent, "bougies dans la fenêtre 16:00–17:30 FR")

if __name__ == "__main__":
    print("📼 Replay 16:00–17:30 →", BACKEND_URL)
    main()
