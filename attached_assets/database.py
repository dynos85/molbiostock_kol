import sqlite3
from datetime import datetime
import pandas as pd
import os

class Database:
    def __init__(self):
        # Ensure database file is in the correct location
        db_path = 'attached_assets/inventory.db'
        if not os.path.exists(db_path):
            print(f"Creating new database at {db_path}")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )''')

        # Insert default admin user if not exists
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", ("admin", "admin123"))

        # Items table with categories
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT,
            minimum_stock INTEGER DEFAULT 20,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Transactions table with enhanced tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            transaction_type TEXT,
            quantity INTEGER,
            date DATE,
            source_destination TEXT,
            expiry_date DATE,
            batch_number TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id)
        )''')

        self.conn.commit()

    def verify_user(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        result = cursor.fetchone()
        print(f"Verifying user {username}: {'Success' if result else 'Failed'}")
        return result is not None

    def add_item(self, name, category=None, minimum_stock=20):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO items (name, category, minimum_stock) VALUES (?, ?, ?)",
                (name, category, minimum_stock)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_item(self, item_id, name=None, category=None, minimum_stock=None):
        cursor = self.conn.cursor()
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if minimum_stock is not None:
            updates.append("minimum_stock = ?")
            params.append(minimum_stock)

        if updates:
            query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
            params.append(item_id)
            cursor.execute(query, params)
            self.conn.commit()
            return True
        return False

    def get_items(self, category=None):
        query = "SELECT * FROM items"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY name"
        return pd.read_sql_query(query, self.conn, params=params)

    def add_stock(self, item_id, quantity, expiry_date, source, batch_number=None, notes=None, created_by="admin"):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO transactions 
            (item_id, transaction_type, quantity, date, source_destination, expiry_date, batch_number, notes, created_by) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (int(item_id), "IN", quantity, datetime.now().date(), source, expiry_date, batch_number, notes, created_by))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding stock: {e}")
            return False

    def remove_stock(self, item_id, quantity, destination, expiry_date, batch_number=None, notes=None, created_by="admin"):
        cursor = self.conn.cursor()
        try:
            # If batch number is not provided, try to get it from the item/expiry combination
            if not batch_number:
                cursor.execute("""
                SELECT batch_number FROM transactions 
                WHERE item_id = ? AND expiry_date = ? AND transaction_type = 'IN'
                LIMIT 1
                """, (int(item_id), expiry_date))
                
                batch_result = cursor.fetchone()
                batch_number = batch_result[0] if batch_result else None
            
            cursor.execute("""
            INSERT INTO transactions 
            (item_id, transaction_type, quantity, date, source_destination, expiry_date, batch_number, notes, created_by) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (int(item_id), "OUT", quantity, datetime.now().date(), destination, expiry_date, batch_number, notes, created_by))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error removing stock: {e}")
            return False

    def get_current_stock(self):
        query = """
        SELECT 
            i.id,
            i.name,
            i.category,
            i.minimum_stock,
            COALESCE(SUM(CASE 
                WHEN t.transaction_type = 'IN' THEN t.quantity 
                WHEN t.transaction_type = 'OUT' THEN -t.quantity 
                ELSE 0
            END), 0) as current_stock
        FROM items i
        LEFT JOIN transactions t ON i.id = t.item_id
        GROUP BY i.id, i.name, i.category, i.minimum_stock
        ORDER BY i.category, i.name
        """
        return pd.read_sql_query(query, self.conn)

    def get_monthly_transactions(self):
        query = """
        SELECT 
            strftime('%Y-%m', t.date) as month,
            i.name as item_name,
            i.category,
            SUM(CASE WHEN t.transaction_type = 'IN' THEN t.quantity ELSE 0 END) as stock_in,
            SUM(CASE WHEN t.transaction_type = 'OUT' THEN t.quantity ELSE 0 END) as stock_out,
            SUM(CASE 
                WHEN t.transaction_type = 'IN' THEN t.quantity 
                WHEN t.transaction_type = 'OUT' THEN -t.quantity 
                ELSE 0
            END) as net_change
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        GROUP BY month, i.name, i.category
        ORDER BY month DESC, i.category, i.name
        """
        return pd.read_sql_query(query, self.conn)

    def get_low_stock_items(self):
        """Get items with stock less than 20"""
        query = """
        WITH current_stock AS (
            SELECT 
                i.id,
                i.name,
                COALESCE(SUM(CASE 
                    WHEN t.transaction_type = 'IN' THEN t.quantity 
                    ELSE -t.quantity 
                END), 0) as stock_level
            FROM items i
            LEFT JOIN transactions t ON i.id = t.item_id
            GROUP BY i.id, i.name
        )
        SELECT 
            name,
            stock_level as current_stock,
            20 as minimum_stock,
            (20 - stock_level) as shortage
        FROM current_stock
        WHERE stock_level < 20
        ORDER BY (20 - stock_level) DESC
        """
        return pd.read_sql_query(query, self.conn)

    def get_item_expiry_dates(self, item_id):
        query = """
        WITH stock_by_expiry AS (
            SELECT 
                expiry_date,
                batch_number,
                SUM(CASE 
                    WHEN transaction_type = 'IN' THEN quantity 
                    ELSE -quantity 
                END) as available_stock
            FROM transactions
            WHERE item_id = ? AND expiry_date IS NOT NULL
            GROUP BY expiry_date, batch_number
            HAVING available_stock > 0
        )
        SELECT expiry_date, batch_number, available_stock
        FROM stock_by_expiry
        WHERE expiry_date >= date('now')
        ORDER BY expiry_date
        """
        return pd.read_sql_query(query, self.conn, params=[int(item_id)])

    def get_available_stock(self, item_id, expiry_date):
        query = """
        SELECT COALESCE(
            SUM(CASE 
                WHEN transaction_type = 'IN' THEN quantity 
                ELSE -quantity 
            END),
            0
        ) as available_stock
        FROM transactions
        WHERE item_id = ? AND expiry_date = ?
        """
        result = pd.read_sql_query(query, self.conn, params=[int(item_id), expiry_date])
        return max(0, result.iloc[0]['available_stock'])

    def search_transactions(self, start_date=None, end_date=None, item_id=None, transaction_type=None):
        query = """
        SELECT 
            t.id,
            i.name as item_name,
            t.transaction_type,
            t.quantity,
            t.date,
            t.source_destination,
            t.expiry_date,
            t.batch_number,
            t.notes,
            t.created_by,
            t.created_at
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND t.date <= ?"
            params.append(end_date)
        if item_id:
            query += " AND t.item_id = ?"
            params.append(item_id)
        if transaction_type:
            query += " AND t.transaction_type = ?"
            params.append(transaction_type)

        query += " ORDER BY t.date DESC, t.created_at DESC"
        return pd.read_sql_query(query, self.conn, params=params)

    def get_all_transactions(self):
        query = """
        SELECT 
            t.id,
            i.name as item_name,
            i.category,
            t.transaction_type,
            t.quantity,
            t.date,
            t.source_destination,
            t.expiry_date,
            t.batch_number,
            t.notes,
            t.created_by,
            t.created_at
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        ORDER BY t.date DESC, t.created_at DESC
        """
        return pd.read_sql_query(query, self.conn)

    def get_expired_items(self):
        query = """
        WITH current_stock AS (
            SELECT 
                item_id,
                expiry_date,
                SUM(CASE 
                    WHEN transaction_type = 'IN' THEN quantity 
                    ELSE -quantity 
                END) as stock_level
            FROM transactions
            GROUP BY item_id, expiry_date
            HAVING stock_level > 0
        )
        SELECT 
            i.name as item_name,
            cs.stock_level as current_stock,
            cs.expiry_date
        FROM current_stock cs
        JOIN items i ON cs.item_id = i.id
        WHERE cs.expiry_date < date('now')
        ORDER BY cs.expiry_date DESC
        """
        return pd.read_sql_query(query, self.conn)

    def get_near_expiry_items(self):
        query = """
        WITH current_stock AS (
            SELECT 
                item_id,
                expiry_date,
                SUM(CASE 
                    WHEN transaction_type = 'IN' THEN quantity 
                    ELSE -quantity 
                END) as stock_level
            FROM transactions
            GROUP BY item_id, expiry_date
            HAVING stock_level > 0
        )
        SELECT 
            i.name as item_name,
            cs.stock_level as current_stock,
            cs.expiry_date
        FROM current_stock cs
        JOIN items i ON cs.item_id = i.id
        WHERE julianday(cs.expiry_date) - julianday('now') <= 60
            AND cs.expiry_date >= date('now')
        ORDER BY cs.expiry_date ASC
        """
        return pd.read_sql_query(query, self.conn)

    def add_user(self, username, password):
        """Add a new user to the database"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def change_password(self, username, current_password, new_password):
        """Change user password"""
        cursor = self.conn.cursor()
        # Verify current password
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, current_password))
        if cursor.fetchone():
            cursor.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
            self.conn.commit()
            return True
        return False