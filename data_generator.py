import random

def generate_market_data():
    base_price = 100
    price = round(random.uniform(base_price - 5, base_price + 5), 2)
    resistance = price + round(random.uniform(2, 10), 2)
    support = price - round(random.uniform(2, 10), 2)
    short_ma = round(price + random.uniform(-2, 2), 2)
    long_ma = round(price + random.uniform(-3, 3), 2)
    rsi = round(random.uniform(20, 80), 2)

    return {
        "price": price,
        "resistance": resistance,
        "support": support,
        "short_ma": short_ma,
        "long_ma": long_ma,
        "rsi": rsi
    }

# Test rapide
if __name__ == "__main__":
    for _ in range(5):
        print(generate_market_data())
