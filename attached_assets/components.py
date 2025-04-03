import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from attached_assets.utils import format_date, create_monthly_transaction_chart, create_stock_level_chart

def render_balance_stock(db):
    st.markdown("<h2 class='subheader'>Current Stock Levels</h2>", unsafe_allow_html=True)

    # Get stock data
    stock_data = db.get_current_stock()

    # Add search option
    search = st.text_input("🔍 Search Items", key="stock_search")

    # Filter data based on search
    filtered_data = stock_data.copy()
    if search:
        filtered_data = filtered_data[filtered_data['name'].str.contains(search, case=False)]

    # Display the stock data with enhanced styling
    if not filtered_data.empty:
        st.markdown('<div class="stock-table">', unsafe_allow_html=True)
        st.dataframe(
            filtered_data[['name', 'current_stock']],
            column_config={
                "name": st.column_config.TextColumn(
                    "Item Name",
                    help="Name of the inventory item",
                    width="medium"
                ),
                "current_stock": st.column_config.NumberColumn(
                    "Current Stock",
                    help="Available quantity in inventory",
                    format="%d",
                    width="small"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No items found matching the search criteria.")

    # Create metrics for overall inventory status
    col1, col2 = st.columns(2)
    with col1:
        total_items = len(stock_data)
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Total Items</h3>
                <div class="metric-value">{total_items}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        total_stock = stock_data['current_stock'].sum()
        st.markdown(
            f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #2ec4b6, #4cc9f0);">
                <h3>Total Stock</h3>
                <div class="metric-value">{total_stock:,}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Create a container for the stock data
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)


        # Add new item form in expander
        with st.expander("➕ Add New Item"):
            with st.form(key="add_item_form"):
                new_item = st.text_input("Item Name", key="new_item_name")
                min_stock = st.number_input("Minimum Stock Level", value=20, min_value=0, key="min_stock_input")
                submit = st.form_submit_button("Add Item")

                if submit and new_item:
                    if db.add_item(new_item, minimum_stock=min_stock):
                        st.success(f"Added {new_item} successfully!")
                        # Clear the form using form_submit_success flag
                        if 'new_item_name' in st.session_state:
                            del st.session_state.new_item_name
                        if 'min_stock_input' in st.session_state:
                            del st.session_state.min_stock_input
                        st.rerun()
                    else:
                        st.error("Item already exists!")

        st.markdown("</div>", unsafe_allow_html=True)


def render_stock_in(db):
    st.subheader("📥 Stock In Entry")

    # Initialize session state for form
    if 'stock_in_date' not in st.session_state or st.session_state.reset_stock_in_form:
        st.session_state.stock_in_date = datetime.now()
        st.session_state.stock_in_source = ""
        st.session_state.stock_in_quantity = 1
        st.session_state.stock_in_batch = ""
        st.session_state.stock_in_notes = ""

    if st.session_state.reset_stock_in_form:
        st.session_state.reset_stock_in_form = False

    items = db.get_items()
    if not items.empty:
        col1, col2 = st.columns(2)

        with col1:
            date = st.date_input("Date of Receipt", key="stock_in_date")
            item = st.selectbox("Select Item", items['name'], key="stock_in_item")
            quantity = st.number_input("Quantity", min_value=1, key="stock_in_quantity")
            batch = st.text_input("Batch Number", key="stock_in_batch")

        with col2:
            expiry_date = st.date_input("Expiry Date", datetime.now() + timedelta(days=365), key="stock_in_expiry")
            source = st.text_input("Received From", key="stock_in_source")
            notes = st.text_area("Notes", key="stock_in_notes", height=100)

        success_container = st.empty()

        if st.button("Submit Stock In", key="submit_stock_in", type="primary"):
            if not source:
                st.error("Please enter the source!")
                return

            if not batch:
                st.error("Please enter the batch number!")
                return

            item_id = items[items['name'] == item].iloc[0]['id']
            if db.add_stock(item_id, quantity, expiry_date, source, batch, notes):
                success_container.success("Stock added successfully!")
                st.session_state.refresh_dashboard = True
                st.session_state.reset_stock_in_form = True
                st.rerun()
            else:
                st.error("Failed to add stock. Please try again.")
    else:
        st.warning("No items available. Please add items in the Balance Stock section.")

def render_stock_out(db):
    st.subheader("📤 Stock Out Entry")

    if 'stock_out_date' not in st.session_state or st.session_state.reset_stock_out_form:
        st.session_state.stock_out_date = datetime.now()
        st.session_state.stock_out_dest = ""
        st.session_state.stock_out_notes = ""

    if st.session_state.reset_stock_out_form:
        st.session_state.reset_stock_out_form = False

    items = db.get_items()
    if not items.empty:
        col1, col2 = st.columns(2)

        with col1:
            date = st.date_input("Date", key="stock_out_date")
            item = st.selectbox("Select Item", items['name'], key="stock_out_item")

        if item:
            item_id = items[items['name'] == item].iloc[0]['id']
            expiry_dates = db.get_item_expiry_dates(item_id)

            if not expiry_dates.empty:
                with col2:
                    # Create a list of batch/expiry options
                    batch_expiry_options = expiry_dates.apply(
                        lambda x: f"Batch: {x['batch_number']} (Expires: {format_date(x['expiry_date'])})", 
                        axis=1
                    ).tolist()

                    selected_batch_expiry = st.selectbox(
                        "Select Batch/Expiry",
                        batch_expiry_options,
                        key="stock_out_expiry"
                    )

                    # Find the selected row using string matching
                    selected_idx = batch_expiry_options.index(selected_batch_expiry)
                    selected_row = expiry_dates.iloc[selected_idx]
                    actual_expiry = selected_row['expiry_date']
                    batch_number = selected_row['batch_number']
                    available_stock = selected_row['available_stock']

                    st.info(f"Available Stock: {available_stock}")

                    if available_stock > 0:
                        quantity = st.number_input(
                            "Quantity",
                            min_value=1,
                            max_value=available_stock,
                            value=min(1, available_stock),
                            key="stock_out_quantity"
                        )
                        destination = st.text_input("Supplied To/For", key="stock_out_dest")
                        notes = st.text_area("Notes", key="stock_out_notes")

                        if st.button("Submit Stock Out", key="submit_stock_out", type="primary"):
                            if not destination:
                                st.error("Please enter the destination!")
                                return

                            if db.remove_stock(item_id, quantity, destination, actual_expiry, batch_number, notes):
                                st.success("Stock out recorded successfully!")
                                st.session_state.refresh_dashboard = True
                                st.session_state.reset_stock_out_form = True
                                st.rerun()
                            else:
                                st.error("Failed to record stock out. Please try again.")
                    else:
                        st.warning("No stock available for the selected batch/expiry date.")
            else:
                st.warning("No stock available for this item.")
    else:
        st.warning("No items available. Please add items in the Balance Stock section.")

def render_search_filter(db):
    st.subheader("🔍 Search & Filter Transactions")

    # Search filters
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    with col3:
        transaction_type = st.selectbox(
            "Transaction Type",
            ["All", "IN", "OUT"]
        )

    # Get and display filtered transactions
    type_filter = transaction_type if transaction_type != "All" else None
    transactions = db.search_transactions(start_date, end_date, transaction_type=type_filter)

    if not transactions.empty:
        st.dataframe(
            transactions,
            column_config={
                "date": "Date",
                "item_name": "Item",
                "transaction_type": "Type",
                "quantity": st.column_config.NumberColumn("Quantity", format="%d"),
                "source_destination": "Source/Destination",
                "expiry_date": "Expiry Date",
                "batch_number": "Batch",
                "notes": "Notes",
                "created_by": "Created By",
                "created_at": "Created At"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No transactions found for the selected criteria.")

def render_reports(db):
    st.subheader("📈 Reports")

    # Expired items report
    st.markdown("### 🚫 Expired Items")
    expired_items = db.get_expired_items()
    if not expired_items.empty:
        st.dataframe(
            expired_items,
            column_config={
                "item_name": "Item",
                "current_stock": st.column_config.NumberColumn("Current Stock", format="%d"),
                "expiry_date": st.column_config.DateColumn("Expiry Date")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("No expired items found.")

    # Near expiry report
    st.markdown("### ⚠️ Items Near Expiry (Next 60 Days)")
    near_expiry = db.get_near_expiry_items()
    if not near_expiry.empty:
        st.dataframe(
            near_expiry,
            column_config={
                "item_name": "Item",
                "current_stock": st.column_config.NumberColumn("Current Stock", format="%d"),
                "expiry_date": st.column_config.DateColumn("Expiry Date")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("No items are near expiry.")

    # Low stock report
    st.markdown("### 📉 Low Stock Items")
    low_stock = db.get_low_stock_items()
    if not low_stock.empty:
        st.dataframe(
            low_stock,
            column_config={
                "name": "Item",
                "current_stock": st.column_config.NumberColumn("Current Stock", format="%d"),
                "minimum_stock": st.column_config.NumberColumn("Minimum Stock", format="%d"),
                "shortage": st.column_config.NumberColumn("Shortage", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("No items are below minimum stock levels.")

    # Monthly transaction summary
    st.markdown("### Monthly Transaction Summary")
    monthly_data = db.get_monthly_transactions()
    if not monthly_data.empty:
        # The chart is rendered directly in the function now
        create_monthly_transaction_chart(monthly_data)
    else:
        st.info("No transaction data available for summary.")