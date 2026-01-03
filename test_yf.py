import yfinance as yf

def test_ticker(symbol):
    print(f"Testing {symbol}...")
    try:
        t = yf.Ticker(symbol)
        price = t.fast_info.last_price
        history = t.history(period="1d")
        
        print(f"  Fast Info Price: {price}")
        if not history.empty:
            print(f"  History Price: {history['Close'].iloc[-1]}")
        else:
            print("  History Empty")
    except Exception as e:
        print(f"  Error: {e}")

test_ticker("BTC")
test_ticker("BTC-USD")
