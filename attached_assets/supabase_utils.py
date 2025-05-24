import json
import os
import sqlite3
import tempfile
import pandas as pd
from supabase import create_client, Client

# Supabase tables
TABLES = {
    "INVENTORY": "inventory",
    "TRANSACTIONS": "transactions",
    "USERS": "users",
    "TRANSFER_LOGS": "transfer_logs"
}

class SupabaseClient:
    """Utility class to handle Supabase operations"""
    
    def __init__(self, url=None, key=None):
        """Initialize the Supabase client"""
        # Try to get URL and key from environment variables if not provided
        self.url = url or os.environ.get("SUPABASE_URL")
        self.key = key or os.environ.get("SUPABASE_ANON_KEY")
        
        self.client = None
        if self.url and self.key:
            self.client = create_client(self.url, self.key)
    
    def is_connected(self):
        """Check if we have a valid Supabase connection"""
        return self.client is not None
    
    def test_connection(self):
        """Test the Supabase connection"""
        if not self.is_connected():
            return False
        
        try:
            # Try a simple query to test connection
            self.client.table(TABLES["TRANSFER_LOGS"]).select("*").limit(1).execute()
            return True
        except Exception as e:
            print(f"Error testing Supabase connection: {e}")
            return False
    
    def upload_data(self, db_path):
        """Upload data from SQLite database to Supabase"""
        if not self.is_connected():
            return False, "No Supabase connection"
        
        try:
            # Connect to SQLite database
            conn = sqlite3.connect(db_path)
            
            # Get inventory data
            inventory_df = pd.read_sql_query("SELECT * FROM inventory", conn)
            inventory_data = inventory_df.to_dict(orient="records")
            
            # Get transactions data
            transactions_df = pd.read_sql_query("SELECT * FROM transactions", conn)
            transactions_data = transactions_df.to_dict(orient="records")
            
            # Upload to Supabase
            # First clear existing data
            self.client.table(TABLES["INVENTORY"]).delete().neq("id", "0").execute()
            self.client.table(TABLES["TRANSACTIONS"]).delete().neq("id", "0").execute()
            
            # Insert new data
            self.client.table(TABLES["INVENTORY"]).insert(inventory_data).execute()
            self.client.table(TABLES["TRANSACTIONS"]).insert(transactions_data).execute()
            
            # Log the transfer
            self.log_transfer("to_supabase", "success")
            
            conn.close()
            return True, "Data successfully uploaded to Supabase"
        except Exception as e:
            self.log_transfer("to_supabase", "failure", str(e))
            return False, f"Error uploading data: {str(e)}"
    
    def download_data(self, db_path):
        """Download data from Supabase to SQLite database"""
        if not self.is_connected():
            return False, "No Supabase connection"
        
        try:
            # Get data from Supabase
            inventory_response = self.client.table(TABLES["INVENTORY"]).select("*").execute()
            transactions_response = self.client.table(TABLES["TRANSACTIONS"]).select("*").execute()
            
            inventory_data = inventory_response.data
            transactions_data = transactions_response.data
            
            # Connect to SQLite database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create temporary tables
            cursor.execute("DROP TABLE IF EXISTS temp_inventory")
            cursor.execute("DROP TABLE IF EXISTS temp_transactions")
            
            # Get schema from existing tables
            cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'inventory'")
            inventory_schema = cursor.fetchone()[0].replace("CREATE TABLE inventory", "CREATE TABLE temp_inventory")
            
            cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'transactions'")
            transactions_schema = cursor.fetchone()[0].replace("CREATE TABLE transactions", "CREATE TABLE temp_transactions")
            
            # Create temp tables with same schema
            cursor.execute(inventory_schema)
            cursor.execute(transactions_schema)
            
            # Insert data into temp tables
            for item in inventory_data:
                placeholders = ", ".join(["?"] * len(item))
                columns = ", ".join(item.keys())
                sql = f"INSERT INTO temp_inventory ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, list(item.values()))
            
            for item in transactions_data:
                placeholders = ", ".join(["?"] * len(item))
                columns = ", ".join(item.keys())
                sql = f"INSERT INTO temp_transactions ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, list(item.values()))
            
            # Replace original tables with temp tables
            cursor.execute("BEGIN TRANSACTION")
            cursor.execute("DROP TABLE inventory")
            cursor.execute("ALTER TABLE temp_inventory RENAME TO inventory")
            cursor.execute("DROP TABLE transactions")
            cursor.execute("ALTER TABLE temp_transactions RENAME TO transactions")
            cursor.execute("COMMIT")
            
            conn.commit()
            conn.close()
            
            # Log the transfer
            self.log_transfer("from_supabase", "success")
            
            return True, "Data successfully downloaded from Supabase"
        except Exception as e:
            self.log_transfer("from_supabase", "failure", str(e))
            return False, f"Error downloading data: {str(e)}"
    
    def log_transfer(self, transfer_type, status, details=None):
        """Log a data transfer operation"""
        if not self.is_connected():
            return
        
        try:
            log_data = {
                "transfer_type": transfer_type,
                "status": status,
                "details": details,
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            self.client.table(TABLES["TRANSFER_LOGS"]).insert(log_data).execute()
        except Exception as e:
            print(f"Error logging transfer: {e}")
