from logger import log_decision

def execute_trade(data: dict, decision: str):
    if decision == "HOLD":
        print("⏸️ Aucune action nécessaire.")
        return
    
    # Simulation de l'exécution d’un ordre
    print(f"💰 Exécution d’un ordre : {decision} à {data['price']} USD")
    
    # Log de la décision
    log_decision(data, decision)

# Test local
if __name__ == "__main__":
    data = {
        "price": 102,
        "resistance": 105,
        "support": 95,
        "short_ma": 100,
        "long_ma": 98,
        "rsi": 28
    }
    decision = "BUY"
    execute_trade(data, decision)
