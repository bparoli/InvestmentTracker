import sqlite3
import pandas as pd

DB_PATH = "data/investments.db"

def inspect_db():
    print(f"Connecting to {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Check tables
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
        print("Tables found:")
        print(tables)
        
        # Check managed_assets
        if 'managed_assets' in tables['name'].values:
            print("\nContent of managed_assets:")
            df = pd.read_sql_query("SELECT * FROM managed_assets", conn)
            print(df)
        else:
            print("\nTable 'managed_assets' NOT found.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_db()
