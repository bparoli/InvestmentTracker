import streamlit as st
import pandas as pd
import datetime
import auth
from utils import init_db, add_transaction, get_transactions, get_portfolio_stats, update_transaction, delete_transaction, get_managed_assets, add_managed_asset, delete_managed_asset

# Page Config
st.set_page_config(page_title="Investment Tracker", page_icon="📈", layout="wide")

# Initialize DB
init_db()

# Authentication
auth.login()
user_email = auth.get_user_email()

if not user_email:
    st.stop()

# Title
st.title("📈 My Investment Tracker")

# Sidebar for Navigation
with st.sidebar:
    st.write(f"👤 **{user_email}**")
    auth.logout()
    st.divider()

page = st.sidebar.radio("Navigate", ["Dashboard", "Add Transaction", "History", "Administration"])

if page == "Add Transaction":
    st.header("➕ Add New Investment")
    
    # Layout - Asset Type Selection (Outside Form for interactivity)
    col_type, col_dummy = st.columns([1, 1])
    with col_type:
        asset_type = st.selectbox("Asset Type", ["Stock", "Crypto", "ETF"])

    # Form Content (Removed st.form for reactivity)
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("Date", datetime.date.today())
        # Check for managed assets
        managed_assets = get_managed_assets(asset_type)
        if not managed_assets.empty:
           # Create list with "Other" option
           asset_options = managed_assets['ticker'].tolist()
           asset_options.append("Other...")
           
           selected_ticker = st.selectbox("Ticker Symbol", asset_options)
           if selected_ticker == "Other...":
               ticker = st.text_input("Enter Ticker Symbol (e.g., SOL)").upper()
           else:
               ticker = selected_ticker
        else:
            ticker = st.text_input("Ticker Symbol (e.g., AAPL, BTC-USD)").upper()
        
    with col2:
        amount = st.number_input("Amount Invested ($)", min_value=0.01, step=10.0)
        quantity = st.number_input("Quantity Bought", min_value=0.00000001, step=0.01, format="%.8f")

    if quantity > 0:
        price_per_unit = amount / quantity
        st.info(f"💰 Price per Unit: **${price_per_unit:,.2f}**")

    # Save Button
    if st.button("Save Transaction", type="primary"):
        if ticker and amount > 0 and quantity > 0:
            add_transaction(date, asset_type, ticker, amount, quantity)
            st.success(f"Saved: {quantity} {ticker} for ${amount} on {date}")
            # Optional: Clear form logic requires session state trickery, but simple rerun clears basic inputs if not stored in session state? 
            # Actually st.text_input keeps value on rerun unless key is changed or value passed. 
            # For now, simple save is enough.
        else:
            st.error("Please fill in all fields correctly.")

elif page == "Dashboard":
    st.header("📊 Portfolio Overview")
    
    with st.spinner("Fetching latest prices..."):
        stats = get_portfolio_stats()
        
    if stats:
        # Top Level Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invested", f"${stats['total_invested']:,.2f}")
        col2.metric("Current Value", f"${stats['total_current_value']:,.2f}")
        
        total_pl = stats['total_current_value'] - stats['total_invested']
        pl_percent = (total_pl / stats['total_invested'] * 100) if stats['total_invested'] > 0 else 0
        col3.metric("Total Profit/Loss", f"${total_pl:,.2f}", f"{pl_percent:.2f}%")
        
        st.markdown("---")
        
        # Breakdown
        st.subheader("Asset Performance")
        details_df = stats['details']
        
        # Formatting for display
        display_df = details_df.copy()
        display_df['Invested'] = display_df['Invested'].apply(lambda x: f"${x:,.2f}")
        display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:,.2f}" if x else "N/A")
        display_df['Current Value'] = display_df['Current Value'].apply(lambda x: f"${x:,.2f}")
        display_df['Profit/Loss'] = display_df['Profit/Loss'].apply(lambda x: f"${x:,.2f}")
        display_df['Return %'] = display_df['Return %'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_df)
        
        # Charts
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Allocation by Asset")
            st.bar_chart(details_df.set_index("Ticker")["Current Value"])
            
        with col_chart2:
             st.subheader("Invested vs Current")
             chart_data = details_df.melt(id_vars=["Ticker"], value_vars=["Invested", "Current Value"], var_name="Type", value_name="Amount")
             st.bar_chart(chart_data, x="Ticker", y="Amount", color="Type", stack=False)

    else:
        st.info("No investments found. Go to 'Add Transaction' to start tracking!")

elif page == "History":
    st.header("📜 Transaction History")
    df = get_transactions()
    
    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None

    if not df.empty:
        # Headers
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1, 1, 0.5, 0.5])
        c1.markdown("**Date | Ticker**")
        c2.markdown("**Type**")
        c3.markdown("**Amount**")
        c4.markdown("**Quantity**")
        c5.markdown("**Price/Unit**")
        c6.markdown("")
        c7.markdown("")
        
        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1, 1, 0.5, 0.5])
                
                # Display Row
                c1.write(f"{row['date']} | **{row['ticker']}**")
                c2.write(row['asset_type'])
                c3.write(f"${row['amount']:,.2f}")
                c4.write(f"{row['quantity']:.8f}")
                price_per_unit = row['amount'] / row['quantity'] if row['quantity'] else 0
                c5.write(f"${price_per_unit:,.2f}")
                
                # Edit Button
                if c6.button("✏️", key=f"edit_{row['id']}", help="Edit Transaction"):
                    st.session_state.edit_id = row['id']
                    st.rerun()
                
                # Delete Button
                if c7.button("🗑️", key=f"delete_{row['id']}", help="Delete Transaction"):
                    delete_transaction(row['id'])
                    st.toast(f"Transaction {row['id']} deleted.")
                    st.rerun()
                
                # Edit Form (Conditional)
                if st.session_state.edit_id == row['id']:
                    with st.expander(f"Editing {row['ticker']}", expanded=True):
                        with st.form(key=f"edit_form_{row['id']}"):
                            c_edit1, c_edit2 = st.columns(2)
                            with c_edit1:
                                new_date = st.date_input("Date", pd.to_datetime(row['date']))
                                new_asset_type = st.selectbox("Type", ["Stock", "Crypto", "ETF"], 
                                                            index=["Stock", "Crypto", "ETF"].index(row['asset_type']) if row['asset_type'] in ["Stock", "Crypto", "ETF"] else 0)
                                
                                # Check for managed assets
                                managed_assets = get_managed_assets(new_asset_type)
                                if not managed_assets.empty:
                                   asset_options = managed_assets['ticker'].tolist()
                                   asset_options.append("Other...")
                                   
                                   current_index = 0
                                   if row['ticker'] in asset_options:
                                       current_index = asset_options.index(row['ticker'])
                                   else:
                                       current_index = len(asset_options) - 1 # Default to Other if not found
                                   
                                   selected_ticker = st.selectbox("Ticker", asset_options, index=current_index, key=f"edit_ticker_select_{row['id']}")
                                   if selected_ticker == "Other...":
                                       new_ticker = st.text_input("Enter Ticker", row['ticker'], key=f"edit_ticker_text_{row['id']}").upper()
                                   else:
                                       new_ticker = selected_ticker
                                else:
                                    new_ticker = st.text_input("Ticker", row['ticker'], key=f"edit_ticker_text_{row['id']}").upper()
                            with c_edit2:
                                new_amount = st.number_input("Amount ($)", value=float(row['amount']), min_value=0.01)
                                new_quantity = st.number_input("Quantity", value=float(row['quantity']), min_value=0.00000001, format="%.8f")
                            
                            if new_quantity > 0:
                                st.caption(f"Price/Unit: ${new_amount/new_quantity:,.2f}")

                            col_save, col_cancel = st.columns([1, 1])
                            with col_save:
                                if st.form_submit_button("💾 Save Changes"):
                                    update_transaction(row['id'], new_date, new_asset_type, new_ticker, new_amount, new_quantity)
                                    st.session_state.edit_id = None
                                    st.success("Updated!")
                                    st.rerun()
                            with col_cancel:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state.edit_id = None
                                    st.rerun()
                st.divider()

    else:
        st.info("No history available.")

elif page == "Administration":
    st.header("⚙️ Administration")
    
    st.subheader("Manage Assets")
    st.write("Add specific cryptocurrencies or stocks to appear in the dropdown list.")
    
    # Add Asset Form
    with st.form("add_asset_form"):
        c1, c2 = st.columns([2, 2])
        with c1:
            new_asset_ticker = st.text_input("Ticker Symbol (e.g. SOL, ADA)").upper()
        with c2:
            new_asset_type = st.selectbox("Asset Type", ["Crypto", "Stock", "ETF"])
            
        submitted = st.form_submit_button("Add Asset")
        if submitted:
            if new_asset_ticker:
                if add_managed_asset(new_asset_ticker, new_asset_type):
                    st.success(f"Added {new_asset_ticker} to managed assets.")
                    st.rerun()
                else:
                    st.error(f"Asset {new_asset_ticker} already exists.")
            else:
                st.error("Please enter a ticker symbol.")
            
    st.divider()
    
    # List Assets
    managed_df = get_managed_assets()
    if not managed_df.empty:
        st.write("### Managed Assets List")
        
        for index, row in managed_df.iterrows():
            c1, c2, c3 = st.columns([1, 2, 1])
            c1.write(f"**{row['ticker']}**")
            c2.write(row['asset_type'])
            if c3.button("🗑️ Delete", key=f"del_asset_{row['id']}"):
                delete_managed_asset(row['id'])
                st.toast(f"Deleted {row['ticker']}")
                st.rerun()
    else:
        st.info("No managed assets found.")


