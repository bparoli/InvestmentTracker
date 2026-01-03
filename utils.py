import sqlite3
import pandas as pd
import yfinance as yf
import datetime

DB_PATH = "data/investments.db"

def init_db():
    """Initializes the SQLite database with the investments table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            ticker TEXT NOT NULL,
            amount REAL NOT NULL,
            quantity REAL NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS managed_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            asset_type TEXT NOT NULL
        )
    ''')
    
    # Check if defaults exist, if not add them
    c.execute("SELECT count(*) FROM managed_assets")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO managed_assets (ticker, asset_type) VALUES (?, ?)", 
                      [('BTC', 'Crypto'), ('ETH', 'Crypto'), ('BNB', 'Crypto')])
    
    conn.commit()
    conn.close()

def add_transaction(date, asset_type, ticker, amount, quantity):
    """Adds a new investment transaction to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO investments (date, asset_type, ticker, amount, quantity)
        VALUES (?, ?, ?, ?, ?)
    ''', (date.strftime("%Y-%m-%d"), asset_type, ticker.upper(), amount, quantity))
    conn.commit()
    conn.close()

def get_transactions():
    """Retrieves all transactions from the database as a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM investments ORDER BY date DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def get_current_price(ticker, asset_type=None):
    """Fetches the current price of a stock or crypto using yfinance."""
    print(f"Fetching price for {ticker} ({asset_type})")
    
    # Heuristic: If explicitly Crypto, ensure -USD suffix
    if asset_type == "Crypto" and not ticker.endswith("-USD"):
        ticker = f"{ticker}-USD"
        
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Try fast_info first
        try:
            price = ticker_obj.fast_info.last_price
        except AttributeError:
            price = None
            
        # Fallback to history if fast_info fails or returns 0/None
        if price is None or price == 0:
             history = ticker_obj.history(period="1d")
             if not history.empty:
                 price = history['Close'].iloc[-1]
                 
        print(f"Price for {ticker}: {price}")
        return price
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None

def get_portfolio_stats():
    """Calculates portfolio statistics based on current prices."""
    df = get_transactions()
    if df.empty:
        return None
    
    # Calculate stats per ticker
    stats = []
    
    # Group by ticker to minimize API calls
    grouped = df.groupby(['ticker', 'asset_type'])[['amount', 'quantity']].sum().reset_index()
    
    total_invested = 0
    total_current_value = 0
    
    for _, row in grouped.iterrows():
        ticker = row['ticker']
        quantity = row['quantity']
        asset_type = row['asset_type']
        invested = row['amount']
        
        current_price = get_current_price(ticker, asset_type)
        current_value = (quantity * current_price) if current_price else 0 # Handle missing price
        
        stats.append({
            "Ticker": ticker,
            "Type": asset_type,
            "Invested": invested,
            "Quantity": quantity,
            "Current Price": current_price,
            "Current Value": current_value,
            "Profit/Loss": current_value - invested,
            "Return %": ((current_value - invested) / invested * 100) if invested > 0 else 0
        })
        
        total_invested += invested
        total_current_value += current_value
        
    return {
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "details": pd.DataFrame(stats)
    }

def update_transaction(id, date, asset_type, ticker, amount, quantity):
    """Updates an existing transaction in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE investments
        SET date = ?, asset_type = ?, ticker = ?, amount = ?, quantity = ?
        WHERE id = ?
    ''', (date.strftime("%Y-%m-%d"), asset_type, ticker.upper(), amount, quantity, id))
    conn.commit()
    conn.close()

def delete_transaction(id):
    """Deletes a transaction from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM investments WHERE id = ?', (id,))
    conn.commit()
    conn.close()

def get_managed_assets(asset_type=None):
    """Retrieves managed assets, optionally filtered by type."""
    conn = sqlite3.connect(DB_PATH)
    if asset_type:
        df = pd.read_sql_query("SELECT * FROM managed_assets WHERE asset_type = ? ORDER BY ticker", conn, params=(asset_type,))
    else:
        df = pd.read_sql_query("SELECT * FROM managed_assets ORDER BY asset_type, ticker", conn)
    conn.close()
    return df

def add_managed_asset(ticker, asset_type):
    """Adds a new managed asset."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO managed_assets (ticker, asset_type) VALUES (?, ?)", (ticker.upper(), asset_type))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def delete_managed_asset(id):
    """Deletes a managed asset."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM managed_assets WHERE id = ?", (id,))
    conn.commit()
    conn.close()
