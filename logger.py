from datetime import datetime

LOG_FILE = "trading.log"

def log_decision(data: dict, decision: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] INPUT={data} -> DECISION={decision}\n"

    with open(LOG_FILE, "a") as f:
        f.write(entry)

# Exemple d’utilisation
if __name__ == "__main__":
    fake_data = {
        "price": 102,
        "resistance": 105,
        "support": 95,
        "short_ma": 100,
        "long_ma": 98,
        "rsi": 28
    }
    log_decision(fake_data, "BUY")
