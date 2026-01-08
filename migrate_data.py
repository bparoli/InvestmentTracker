import streamlit as st
import sqlite3
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid

ST_DB_PATH = "data/investments.db"
SHEET_INVESTMENTS = "investments"
SHEET_MANAGED = "managed_assets"

st.title("💾 Database Migration Tool")
st.write("This script will move your data from the local SQLite file to your new Google Sheet.")

if st.button("Start Migration"):
    # 1. Read from SQLite
    try:
        conn_sql = sqlite3.connect(ST_DB_PATH)
        
        # Investments
        df_inv = pd.read_sql_query("SELECT * FROM investments", conn_sql)
        st.write(f"Found {len(df_inv)} investment records.")
        
        # Managed Assets
        # Check if table exists first
        try:
            df_assets = pd.read_sql_query("SELECT * FROM managed_assets", conn_sql)
            st.write(f"Found {len(df_assets)} managed assets.")
        except:
            df_assets = pd.DataFrame()
            st.warning("No 'managed_assets' table found or empty.")
            
        conn_sql.close()
        
    except Exception as e:
        st.error(f"Error reading SQLite: {e}")
        st.stop()

    # 2. Add UUIDs if missing (SQLite id was integer)
    # Google Sheets works better with string IDs to avoid row shifting issues, 
    # but we can keep int IDs if we want. Let's convert to string to be safe for future uuid usage.
    if not df_inv.empty:
        df_inv['id'] = df_inv['id'].astype(str)
        # Ensure columns match what utils.py expects
        # utils.py expects: id, date, asset_type, ticker, amount, quantity
        # Date in SQLite is string YYYY-MM-DD, which is fine.

    if not df_assets.empty:
        df_assets['id'] = df_assets['id'].astype(str)

    # 3. Write to Google Sheets
    try:
        conn_gs = st.connection("gsheets", type=GSheetsConnection)
        
        if not df_inv.empty:
            st.info("Uploading investments... (this may take a moment)")
            conn_gs.update(worksheet=SHEET_INVESTMENTS, data=df_inv)
            st.success("✅ Investments uploaded!")
            
        if not df_assets.empty:
            st.info("Uploading managed assets...")
            conn_gs.update(worksheet=SHEET_MANAGED, data=df_assets)
            st.success("✅ Managed Assets uploaded!")
            
    except Exception as e:
        st.error(f"Error uploading to Google Sheets: {e}")
        
    st.balloons()
    st.success("Migration Complete! You can now verify your Google Sheet and delete this script.")
