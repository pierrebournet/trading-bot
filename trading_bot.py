import requests
import time

API_URL = "https://backend-1055832982794.europe-west1.run.app/bot/strategy"

market_data = {
    "price": 102,
    "resistance": 105,
    "support": 95,
    "short_ma": 100,
    "long_ma": 98,
    "rsi": 28
}

def call_strategy_api(data):
    try:
        response = requests.post(API_URL, json=data)
        response.raise_for_status()
        decision = response.json().get("decision")
        print(f"🎯 Décision de trading : {decision}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de l'appel API : {e}")

if __name__ == "__main__":
    print("📡 Lancement du bot de trading...\n")
    while True:
        call_strategy_api(market_data)
        time.sleep(10)
