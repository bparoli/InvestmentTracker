import yfinance as yf

def inspect_ticker(symbol):
    print(f"\n--- Inspecting {symbol} ---")
    try:
        t = yf.Ticker(symbol)
        info = t.info
        print(f"Name: {info.get('longName') or info.get('shortName')}")
        print(f"Type: {info.get('quoteType')}")
        print(f"Price: {t.fast_info.last_price}")
    except Exception as e:
        print(f"Error: {e}")

inspect_ticker("BTC")
inspect_ticker("BTC-USD")
