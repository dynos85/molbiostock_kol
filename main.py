import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os

# Import custom modules from attached_assets
from attached_assets.database import Database
from attached_assets.components import (
    render_balance_stock,
    render_stock_in,
    render_stock_out,
    render_search_filter,
    render_reports
)
from attached_assets.auth import check_password
from attached_assets.backup import BackupManager
from attached_assets.export import export_data

# Set page configuration
st.set_page_config(
    page_title="Molbio Reagents Inventory",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS
with open('attached_assets/styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state
if 'refresh_dashboard' not in st.session_state:
    st.session_state.refresh_dashboard = False
if 'reset_stock_in_form' not in st.session_state:
    st.session_state.reset_stock_in_form = False
if 'reset_stock_out_form' not in st.session_state:
    st.session_state.reset_stock_out_form = False

# Authentication check
if not check_password():
    st.stop()

# Initialize database connection
if 'db' not in st.session_state:
    st.session_state.db = Database()

db = st.session_state.db

# App Header
st.markdown(
    """
    <div class="title-container">
        <div>
            <h1>🧪 Molbio Reagents Inventory</h1>
            <p>Track, Manage, and Analyze the reagents inventory</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar
with st.sidebar:
    st.subheader("User: admin")
    
    if st.button("📤 Logout", key="logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.divider()
    
    # Settings and Export section
    st.subheader("⚙️ Settings & Export")
    
    # Export current stock
    if st.button("Export Current Stock", key="export_stock"):
        excel_data, filename = export_data(db, "stock")
        st.download_button(
            label="📥 Download Excel File",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Export transactions
    if st.button("Export Transactions", key="export_transactions"):
        excel_data, filename = export_data(db, "transactions")
        st.download_button(
            label="📥 Download Excel File",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    st.divider()
    
    # Backup and Restore
    st.subheader("💾 Backup & Restore")
    backup_manager = BackupManager()
    
    # Create backup
    if st.button("Create Backup", key="create_backup"):
        backup_path = backup_manager.create_backup()
        if backup_path:
            st.success(f"Backup created: {os.path.basename(backup_path)}")
        else:
            st.error("Failed to create backup")
    
    # Restore backup
    with st.expander("Restore from Backup"):
        backups = backup_manager.list_backups()
        if backups:
            backup_options = [f"{b['filename']} ({b['created'].strftime('%Y-%m-%d %H:%M:%S')})" for b in backups]
            selected_backup = st.selectbox("Select Backup", backup_options)
            
            if st.button("Restore Selected Backup"):
                selected_idx = backup_options.index(selected_backup)
                if backup_manager.restore_backup(backups[selected_idx]['path']):
                    st.success("Backup restored successfully!")
                    st.session_state.db = Database()
                    st.rerun()
                else:
                    st.error("Failed to restore backup")
        else:
            st.info("No backups available")
    
    # Change password
    with st.expander("Change Password"):
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button("Change Password")
            
            if submit:
                if new_password != confirm_password:
                    st.error("New passwords don't match!")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters!")
                else:
                    if db.change_password("admin", current_password, new_password):
                        st.success("Password changed successfully!")
                    else:
                        st.error("Current password is incorrect!")

# Main content with tabs
tabs = st.tabs([
    "Current Stock 📦", 
    "Stock In 📥", 
    "Stock Out 📤", 
    "Search & Filter 🔍", 
    "Reports 📊"
])

# Current Stock Tab
with tabs[0]:
    render_balance_stock(db)

# Stock In Tab
with tabs[1]:
    render_stock_in(db)

# Stock Out Tab 
with tabs[2]:
    render_stock_out(db)

# Search & Filter Tab
with tabs[3]:
    render_search_filter(db)

# Reports Tab
with tabs[4]:
    render_reports(db)

# Footer
st.markdown(
    """
    <div class="footer">
        <p>© 2025 Molbio Reagents Inventory Management System | Version 1.0 | Designed by Subhadeep.S</p>
    </div>
    """,
    unsafe_allow_html=True
)
