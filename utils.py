import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import datetime
import uuid

# Constants
SHEET_INVESTMENTS = "investments"
SHEET_MANAGED = "managed_assets"

# Cache TTL: Time to live for cache. Set low for interactive editing.
TTL = 0 

def get_connection():
    """Returns the GSheets connection object."""
    return st.connection("gsheets", type=GSheetsConnection)

def init_db():
    """
    Checks if sheets exist/have headers. 
    If empty, initializes them.
    """
    conn = get_connection()
    
    # 1. Investments Sheet
    try:
        df_inv = conn.read(worksheet=SHEET_INVESTMENTS, ttl=TTL)
        if df_inv.empty or "id" not in df_inv.columns:
             # Initialize with headers
             initial_data = pd.DataFrame(columns=["id", "date", "asset_type", "ticker", "amount", "quantity"])
             conn.update(worksheet=SHEET_INVESTMENTS, data=initial_data)
    except Exception:
        # Likely sheet doesn't exist or is completely empty
        initial_data = pd.DataFrame(columns=["id", "date", "asset_type", "ticker", "amount", "quantity"])
        conn.update(worksheet=SHEET_INVESTMENTS, data=initial_data)

    # 2. Managed Assets Sheet
    try:
        df_mgd = conn.read(worksheet=SHEET_MANAGED, ttl=TTL)
        if df_mgd.empty or "id" not in df_mgd.columns:
            initial_managed = pd.DataFrame([
                {"id": str(uuid.uuid4()), "ticker": "BTC", "asset_type": "Crypto"},
                {"id": str(uuid.uuid4()), "ticker": "ETH", "asset_type": "Crypto"},
                {"id": str(uuid.uuid4()), "ticker": "BNB", "asset_type": "Crypto"}
            ])
            conn.update(worksheet=SHEET_MANAGED, data=initial_managed)
    except Exception:
        initial_managed = pd.DataFrame([
                {"id": str(uuid.uuid4()), "ticker": "BTC", "asset_type": "Crypto"},
                {"id": str(uuid.uuid4()), "ticker": "ETH", "asset_type": "Crypto"},
                {"id": str(uuid.uuid4()), "ticker": "BNB", "asset_type": "Crypto"}
            ])
        conn.update(worksheet=SHEET_MANAGED, data=initial_managed)

def add_transaction(date, asset_type, ticker, amount, quantity):
    """Adds a new investment transaction to the Sheet."""
    conn = get_connection()
    df = conn.read(worksheet=SHEET_INVESTMENTS, ttl=TTL)
    
    new_entry = pd.DataFrame([{
        "id": str(uuid.uuid4()),
        "date": date.strftime("%Y-%m-%d"),
        "asset_type": asset_type,
        "ticker": ticker.upper(),
        "amount": float(amount),
        "quantity": float(quantity)
    }])
    
    updated_df = pd.concat([df, new_entry], ignore_index=True)
    conn.update(worksheet=SHEET_INVESTMENTS, data=updated_df)

def get_transactions():
    """Retrieves all transactions from the Sheet."""
    conn = get_connection()
    try:
        df = conn.read(worksheet=SHEET_INVESTMENTS, ttl=TTL)
        if df.empty:
            return pd.DataFrame(columns=["id", "date", "asset_type", "ticker", "amount", "quantity"])
        # Ensure correct types
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        # Sort desc by date
        df = df.sort_values(by="date", ascending=False)
        return df
    except Exception:
        return pd.DataFrame()

def update_transaction(id, date, asset_type, ticker, amount, quantity):
    """Updates an existing transaction."""
    conn = get_connection()
    df = conn.read(worksheet=SHEET_INVESTMENTS, ttl=TTL)
    
    # Needs to be string for comparison if UUIDs are used
    df['id'] = df['id'].astype(str)
    id = str(id)
    
    if id in df['id'].values:
        df.loc[df['id'] == id, 'date'] = date.strftime("%Y-%m-%d")
        df.loc[df['id'] == id, 'asset_type'] = asset_type
        df.loc[df['id'] == id, 'ticker'] = ticker.upper()
        df.loc[df['id'] == id, 'amount'] = float(amount)
        df.loc[df['id'] == id, 'quantity'] = float(quantity)
        
        conn.update(worksheet=SHEET_INVESTMENTS, data=df)

def delete_transaction(id):
    """Deletes a transaction."""
    conn = get_connection()
    df = conn.read(worksheet=SHEET_INVESTMENTS, ttl=TTL)
    
    df['id'] = df['id'].astype(str)
    id = str(id)
    
    updated_df = df[df['id'] != id]
    conn.update(worksheet=SHEET_INVESTMENTS, data=updated_df)

def get_managed_assets(asset_type=None):
    """Retrieves managed assets."""
    conn = get_connection()
    try:
        df = conn.read(worksheet=SHEET_MANAGED, ttl=TTL)
        if df.empty:
            return pd.DataFrame(columns=["id", "ticker", "asset_type"])
            
        if asset_type:
            df = df[df['asset_type'] == asset_type]
            
        return df.sort_values(by="ticker")
    except Exception:
        return pd.DataFrame()

def add_managed_asset(ticker, asset_type):
    """Adds a new managed asset."""
    conn = get_connection()
    df = conn.read(worksheet=SHEET_MANAGED, ttl=TTL)
    
    # Check duplicate
    if ticker.upper() in df['ticker'].str.upper().values:
        return False
        
    new_entry = pd.DataFrame([{
        "id": str(uuid.uuid4()),
        "ticker": ticker.upper(),
        "asset_type": asset_type
    }])
    
    updated_df = pd.concat([df, new_entry], ignore_index=True)
    conn.update(worksheet=SHEET_MANAGED, data=updated_df)
    return True

def delete_managed_asset(id):
    """Deletes a managed asset."""
    conn = get_connection()
    df = conn.read(worksheet=SHEET_MANAGED, ttl=TTL)
    
    df['id'] = df['id'].astype(str)
    id = str(id)
    
    updated_df = df[df['id'] != id]
    conn.update(worksheet=SHEET_MANAGED, data=updated_df)


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
