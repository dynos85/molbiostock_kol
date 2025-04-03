import streamlit as st
from database import Database
from attached_assets.auth import check_password  # Updated import path
from components import render_balance_stock, render_stock_in, render_stock_out, render_search_filter, render_reports
from utils import create_monthly_transaction_chart
from backup import BackupManager
from export import export_data
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Molbio Reagents Stock Inventory",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional custom styles for enhanced UI
st.markdown("""
    <style>
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    .title-container {
        display: flex;
        align-items: center;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    
    .title-container h1 {
        margin-left: 10px;
        color: white;
    }
    
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transition: transform 0.2s;
    }
    
    .card:hover {
        transform: translateY(-2px);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #4361ee, #3a0ca3);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    
    @media (max-width: 768px) {
        .container {
            padding: 0.5rem;
        }
        
        .card {
            padding: 1rem;
        }
    }
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #f0f0f0;
        padding: 10px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    if not check_password():
        return

    # Initialize database and backup manager
    db = Database()
    backup_mgr = BackupManager()

    # Title with improved styling and light green color
    st.markdown(
        """
        <div class="title-container" style="background: linear-gradient(135deg, #90EE90, #98FB98);">
            <span style="font-size: 2.5rem;">🧪</span>
            <h1>Molbio Reagents Stock Inventory</h1>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Sidebar for additional features
    with st.sidebar:
        st.subheader("📊 Dashboard Options")

        # Logout button at the top
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()

        # User Management Section
        st.markdown("### 👤 User Management")

        # Create New User
        with st.expander("Create New User"):
            with st.form("create_user_form"):
                new_username = st.text_input("Username", key="new_user")
                new_password = st.text_input("Password", type="password", key="new_pass")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")
                create_user = st.form_submit_button("Create User")

                if create_user:
                    if new_password != confirm_password:
                        st.error("Passwords do not match!")
                    elif not new_username or not new_password:
                        st.error("Username and password are required!")
                    else:
                        if db.add_user(new_username, new_password):
                            st.success("User created successfully!")
                            # Clear form fields
                            st.session_state.new_user = ""
                            st.session_state.new_pass = ""
                            st.session_state.confirm_pass = ""
                            st.rerun()
                        else:
                            st.error("Username already exists!")

        # Change Password
        with st.expander("Change Password"):
            with st.form("change_password_form"):
                current_password = st.text_input("Current Password", type="password", key="current_pass")
                new_password = st.text_input("New Password", type="password", key="change_new_pass")
                confirm_new_password = st.text_input("Confirm New Password", type="password", key="change_confirm_pass")
                change_password = st.form_submit_button("Change Password")

                if change_password:
                    if new_password != confirm_new_password:
                        st.error("New passwords do not match!")
                    elif not current_password or not new_password:
                        st.error("All fields are required!")
                    else:
                        if db.change_password(st.session_state.username, current_password, new_password):
                            st.success("Password changed successfully!")
                            # Clear form fields
                            st.session_state.current_pass = ""
                            st.session_state.change_new_pass = ""
                            st.session_state.change_confirm_pass = ""
                            st.rerun()
                        else:
                            st.error("Current password is incorrect!")

        # Data Export
        st.markdown("### 📥 Export Data")
        export_type = st.selectbox("Select Export Type", ["Stock Levels", "Transaction History"])
        if st.button("Export to Excel"):
            data_type = "stock" if export_type == "Stock Levels" else "transactions"
            excel_data, filename = export_data(db, data_type)
            st.download_button(
                label="Download Excel File",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Backup Management
        st.markdown("### 💾 Backup Management")
        if st.button("Create Backup"):
            backup_path = backup_mgr.create_backup()
            if backup_path:
                st.success("Backup created successfully!")

        # Restore from backup
        backups = backup_mgr.list_backups()
        if backups:
            selected_backup = st.selectbox(
                "Select Backup to Restore",
                options=[b['filename'] for b in backups],
                format_func=lambda x: f"{x} ({pd.to_datetime(next(b['created'] for b in backups if b['filename'] == x)).strftime('%Y-%m-%d %H:%M')})"
            )
            if st.button("Restore Backup"):
                backup_file = next(b['path'] for b in backups if b['filename'] == selected_backup)
                if backup_mgr.restore_backup(backup_file):
                    st.success("Backup restored successfully!")
                    st.rerun()

    # Main content tabs
    tabs = st.tabs([
        "📊 Balance Stock",
        "📥 Stock In",
        "📤 Stock Out",
        "🔍 Search & Filter",
        "📈 Reports"
    ])

    with tabs[0]:
        render_balance_stock(db)

        # Stock movement analysis
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h2 class='subheader'>📈 Stock Movement Analysis</h2>", unsafe_allow_html=True)
        
        monthly_data = db.get_monthly_transactions()
        if not monthly_data.empty:
            # Extract unique items, months, and years
            all_items = ["All Items"] + sorted(monthly_data['item_name'].unique().tolist())
            years = ["All Years"] + sorted(monthly_data['month'].str[:4].unique().tolist())
            months = ["All Months"] + [
                datetime.strptime(m, "%m").strftime("%B")
                for m in sorted(monthly_data['month'].str[5:7].unique().tolist())
            ]

            # Create filters
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_item = st.selectbox("Item Name", all_items)
            with col2:
                selected_month = st.selectbox("Month", months)
            with col3:
                selected_year = st.selectbox("Year", years)

            # Filter data
            filtered_data = monthly_data.copy()
            if selected_item != "All Items":
                filtered_data = filtered_data[filtered_data['item_name'] == selected_item]
            if selected_month != "All Months":
                month_num = datetime.strptime(selected_month, "%B").strftime("%m")
                filtered_data = filtered_data[filtered_data['month'].str[5:7] == month_num]
            if selected_year != "All Years":
                filtered_data = filtered_data[filtered_data['month'].str[:4] == selected_year]

            if not filtered_data.empty:
                st.plotly_chart(create_monthly_transaction_chart(filtered_data), use_container_width=True)
            else:
                st.info("No data available for the selected filters.")
        else:
            st.info("No transaction data available yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        render_stock_in(db)

    with tabs[2]:
        render_stock_out(db)

    with tabs[3]:
        render_search_filter(db)

    with tabs[4]:
        render_reports(db)

    # Add footer
    st.markdown(
        """
        <div class="footer">
            Designed by Subhadeep.S
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    # Initialize session state variables
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if 'refresh_dashboard' not in st.session_state:
        st.session_state.refresh_dashboard = True
    
    if 'reset_stock_in_form' not in st.session_state:
        st.session_state.reset_stock_in_form = False
    
    if 'reset_stock_out_form' not in st.session_state:
        st.session_state.reset_stock_out_form = False
    
    if 'stock_in_source' not in st.session_state:
        st.session_state.stock_in_source = ""
    
    if 'stock_out_dest' not in st.session_state:
        st.session_state.stock_out_dest = ""
    
    main()