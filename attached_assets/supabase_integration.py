import streamlit as st
import pandas as pd
import os
import json
import sqlite3
from datetime import datetime
from .supabase_utils import SupabaseClient

def render_supabase_integration(db):
    """
    Render the Supabase integration UI component
    
    Parameters:
        db: Database instance
    """
    st.subheader("🔄 Supabase Data Synchronization")
    
    # Initialize Supabase client
    supabase = SupabaseClient()
    
    # Check if Supabase is configured
    if not supabase.is_connected():
        st.warning("⚠️ Supabase connection is not configured. Please add your Supabase URL and API key in the settings.")
        
        with st.expander("Configure Supabase Connection"):
            with st.form("supabase_config_form"):
                supabase_url = st.text_input("Supabase URL", placeholder="https://your-project-id.supabase.co")
                supabase_key = st.text_input("Supabase API Key", placeholder="your-supabase-anon-key", type="password")
                
                submit = st.form_submit_button("Save Configuration")
                if submit:
                    if not supabase_url or not supabase_key:
                        st.error("Both Supabase URL and API Key are required")
                    else:
                        # Store in environment variables for now
                        # In a real app, we would store these securely
                        os.environ["SUPABASE_URL"] = supabase_url
                        os.environ["SUPABASE_ANON_KEY"] = supabase_key
                        
                        # Reinitialize client
                        supabase = SupabaseClient(supabase_url, supabase_key)
                        
                        if supabase.test_connection():
                            st.success("✅ Connected to Supabase successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect to Supabase. Please check your credentials.")
        
        return
    
    # Display connection status
    if supabase.test_connection():
        st.success("✅ Connected to Supabase")
    else:
        st.error("❌ Not connected to Supabase. Please check your connection settings.")
        return
    
    # Create two columns for the buttons
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📤 Upload to Supabase")
        st.write("Transfer current Streamlit database to Supabase")
        
        if st.button("Upload Data to Supabase", key="upload_to_supabase"):
            with st.spinner("Uploading data to Supabase..."):
                # Get SQLite database path
                db_path = db.get_db_path()
                
                # Upload data
                success, message = supabase.upload_data(db_path)
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    with col2:
        st.markdown("### 📥 Download from Supabase")
        st.write("Import data from Supabase to Streamlit database")
        
        if st.button("Download Data from Supabase", key="download_from_supabase"):
            with st.spinner("Downloading data from Supabase..."):
                # Show warning and confirmation
                proceed = st.warning("⚠️ This will overwrite your current local database. Are you sure?")
                
                if st.button("Yes, I'm Sure", key="confirm_download"):
                    # Get SQLite database path
                    db_path = db.get_db_path()
                    
                    # Download data
                    success, message = supabase.download_data(db_path)
                    
                    if success:
                        st.success(message)
                        st.info("Reloading database...")
                        # Reinitialize database connection to reflect changes
                        st.session_state.db = type(db)()
                        st.rerun()
                    else:
                        st.error(message)
    
    # Show sync history
    if supabase.is_connected():
        st.markdown("### 📋 Synchronization History")
        
        try:
            # Get sync logs from Supabase
            response = supabase.client.table("transfer_logs").select("*").order("timestamp", ascending=False).limit(10).execute()
            logs = response.data
            
            if logs:
                logs_df = pd.DataFrame(logs)
                logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])
                logs_df = logs_df[["timestamp", "transfer_type", "status", "details"]]
                logs_df.columns = ["Timestamp", "Operation", "Status", "Details"]
                logs_df["Operation"] = logs_df["Operation"].map({
                    "to_supabase": "Upload to Supabase",
                    "from_supabase": "Download from Supabase"
                })
                
                st.dataframe(logs_df, use_container_width=True)
            else:
                st.info("No synchronization history yet.")
        except Exception as e:
            st.error(f"Error fetching synchronization history: {str(e)}")
