import streamlit as st
from sqlalchemy import text
import pandas as pd
import yfinance as yf
import datetime

# Cache TTL
TTL = 0 

def get_connection():
    """Returns the SQL connection object for Supabase."""
    return st.connection("supabase", type="sql")

def init_db():
    """Initializes the database tables if they don't exist."""
    conn = get_connection()
    with conn.session as s:
        # Investments Table
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS investments (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                asset_type TEXT NOT NULL,
                ticker TEXT NOT NULL,
                amount DECIMAL NOT NULL,
                quantity DECIMAL NOT NULL
            );
        '''))
        
        # Managed Assets Table
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS managed_assets (
                id SERIAL PRIMARY KEY,
                ticker TEXT NOT NULL UNIQUE,
                asset_type TEXT NOT NULL
            );
        '''))
        
        # Check for default managed assets
        result = s.execute(text("SELECT count(*) FROM managed_assets")).fetchone()[0]
        if result == 0:
            s.execute(text("INSERT INTO managed_assets (ticker, asset_type) VALUES (:t, :a)"), [{"t": "BTC", "a": "Crypto"}, {"t": "ETH", "a": "Crypto"}, {"t": "BNB", "a": "Crypto"}])
            
        s.commit()

def add_transaction(date, asset_type, ticker, amount, quantity):
    """Adds a new investment transaction."""
    conn = get_connection()
    with conn.session as s:
        s.execute(
            text("INSERT INTO investments (date, asset_type, ticker, amount, quantity) VALUES (:d, :a, :t, :am, :q)"),
            {"d": date, "a": asset_type, "t": ticker.upper(), "am": amount, "q": quantity}
        )
        s.commit()

def get_transactions():
    """Retrieves all transactions."""
    conn = get_connection()
    try:
        # caching logic handled by st.connection if needed, but for now we read fresh
        df = conn.query("SELECT * FROM investments ORDER BY date DESC", ttl=TTL)
        if df.empty:
             return pd.DataFrame(columns=["id", "date", "asset_type", "ticker", "amount", "quantity"])
        
        # Ensure numeric types for downstream math
        df['amount'] = pd.to_numeric(df['amount'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        return df
    except Exception:
        return pd.DataFrame()

def update_transaction(id, date, asset_type, ticker, amount, quantity):
    """Updates an existing transaction."""
    conn = get_connection()
    with conn.session as s:
        s.execute(
            text("UPDATE investments SET date = :d, asset_type = :a, ticker = :t, amount = :am, quantity = :q WHERE id = :id"),
            {"d": date, "a": asset_type, "t": ticker.upper(), "am": amount, "q": quantity, "id": id}
        )
        s.commit()

def delete_transaction(id):
    """Deletes a transaction."""
    conn = get_connection()
    with conn.session as s:
        s.execute(text("DELETE FROM investments WHERE id = :id"), {"id": id})
        s.commit()

def get_managed_assets(asset_type=None):
    """Retrieves managed assets."""
    conn = get_connection()
    try:
        if asset_type:
            df = conn.query("SELECT * FROM managed_assets WHERE asset_type = :a ORDER BY ticker", params={"a": asset_type}, ttl=TTL)
        else:
            df = conn.query("SELECT * FROM managed_assets ORDER BY asset_type, ticker", ttl=TTL)
        return df
    except Exception:
        return pd.DataFrame()

def add_managed_asset(ticker, asset_type):
    """Adds a new managed asset."""
    conn = get_connection()
    try:
        with conn.session as s:
             s.execute(
                text("INSERT INTO managed_assets (ticker, asset_type) VALUES (:t, :a)"),
                {"t": ticker.upper(), "a": asset_type}
             )
             s.commit()
        return True
    except Exception:
        return False

def delete_managed_asset(id):
    """Deletes a managed asset."""
    conn = get_connection()
    with conn.session as s:
        s.execute(text("DELETE FROM managed_assets WHERE id = :id"), {"id": id})
        s.commit()


# --- Pricing and Stats (Unchanged Logic, just helper) ---

def get_current_price(ticker, asset_type=None):
    """Fetches the current price of a stock or crypto using yfinance."""
    print(f"Fetching price for {ticker} ({asset_type})")
    
    if asset_type == "Crypto" and not ticker.endswith("-USD"):
        ticker = f"{ticker}-USD"
        
    try:
        ticker_obj = yf.Ticker(ticker)
        try:
            price = ticker_obj.fast_info.last_price
        except AttributeError:
            price = None
            
        if price is None or price == 0:
             history = ticker_obj.history(period="1d")
             if not history.empty:
                 price = history['Close'].iloc[-1]
                 
        return price
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None

def get_portfolio_stats():
    """Calculates portfolio statistics."""
    df = get_transactions()
    if df.empty:
        return None
    
    stats = []
    # Ensure numeric
    df['amount'] = pd.to_numeric(df['amount'])
    df['quantity'] = pd.to_numeric(df['quantity'])
    
    grouped = df.groupby(['ticker', 'asset_type'])[['amount', 'quantity']].sum().reset_index()
    
    total_invested = 0
    total_current_value = 0
    
    for _, row in grouped.iterrows():
        ticker = row['ticker']
        quantity = row['quantity']
        asset_type = row['asset_type']
        invested = row['amount']
        
        current_price = get_current_price(ticker, asset_type)
        current_value = (quantity * current_price) if current_price else 0
        
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
