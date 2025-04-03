import pandas as pd
from datetime import datetime
import streamlit as st

def format_date(date_str):
    """Format date string to a more readable format"""
    if pd.isna(date_str) or date_str is None:
        return "No expiry date"
    elif isinstance(date_str, str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
        except ValueError:
            return date_str
    else:
        try:
            return date_str.strftime('%B %d, %Y')
        except AttributeError:
            return "No expiry date"

def create_monthly_transaction_chart(data):
    """Display monthly transactions in tabular format"""
    if 'item_name' in data.columns:
        st.subheader("Monthly Transactions Summary")
        
        # Prepare the data for display
        display_data = data.copy()
        display_data['month'] = pd.to_datetime(display_data['month'] + '-01').dt.strftime('%B %Y')
        
        # Rename columns for better display
        display_data = display_data.rename(columns={
            'month': 'Month',
            'item_name': 'Item',
            'category': 'Category',
            'stock_in': 'Stock In',
            'stock_out': 'Stock Out',
            'net_change': 'Net Change'
        })
        
        # Display the data in a table
        st.dataframe(
            display_data[['Month', 'Item', 'Category', 'Stock In', 'Stock Out', 'Net Change']],
            hide_index=True,
            use_container_width=True
        )
        
        return None

def create_stock_level_chart(data):
    """Create a visualization of current stock levels vs minimum stock using Streamlit charts"""
    # Sort data by current stock for better visualization
    data = data.sort_values('current_stock', ascending=True)
    
    # Create a combined dataframe for Streamlit chart
    st.subheader("Stock Levels vs Minimum Stock")
    
    # Create a dataframe with 'name' as index and both stock values as columns
    chart_data = pd.DataFrame({
        'Current Stock': data['current_stock'],
        'Minimum Stock': data['minimum_stock']
    }, index=data['name'])
    
    # Use Streamlit's bar chart for visualization
    st.bar_chart(chart_data, use_container_width=True)
    
    # Also show the data in a table format for clarity
    st.write("Stock Level Details:")
    st.dataframe(
        data[['name', 'current_stock', 'minimum_stock']].rename(
            columns={'name': 'Item', 'current_stock': 'Current Stock', 'minimum_stock': 'Minimum Stock'}
        ),
        hide_index=True,
        use_container_width=True
    )
    
    return None  # No figure to return as Streamlit renders charts directly