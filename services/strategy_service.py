# services/strategy_service.py

def evaluate_strategy(data):
    price = data["price"]
    resistance = data["resistance"]
    support = data["support"]
    short_ma = data["short_ma"]
    long_ma = data["long_ma"]
    rsi = data["rsi"]

    if price > short_ma > long_ma and rsi < 30 and price < resistance:
        return "BUY"
    elif price < short_ma < long_ma and rsi > 70 and price > support:
        return "SELL"
    else:
        return "HOLD"


