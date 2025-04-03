import sqlite3
import os
import shutil
from datetime import datetime
import streamlit as st
import zipfile

class BackupManager:
    def __init__(self, db_path='attached_assets/inventory.db', backup_dir='backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
    def create_backup(self):
        """Create a backup of the database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'inventory_backup_{timestamp}.db')
        
        try:
            # Create backup directory if it doesn't exist
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            # Create ZIP archive
            zip_path = backup_path + '.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, os.path.basename(backup_path))
                
            # Remove uncompressed backup
            os.remove(backup_path)
            
            return zip_path
            
        except Exception as e:
            st.error(f"Backup failed: {str(e)}")
            return None
            
    def restore_backup(self, backup_file):
        """Restore database from backup"""
        try:
            # Extract ZIP file
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(self.backup_dir)
                
            # Get extracted DB file
            db_file = os.path.splitext(backup_file)[0]
            
            # Close current database connection
            # This assumes the database connection is stored in session state
            if 'db' in st.session_state:
                st.session_state.db.conn.close()
                
            # Replace current DB with backup
            shutil.copy2(db_file, self.db_path)
            
            # Remove extracted file
            os.remove(db_file)
            
            return True
            
        except Exception as e:
            st.error(f"Restore failed: {str(e)}")
            return False
            
    def list_backups(self):
        """List available backups"""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith('.zip'):
                backup_path = os.path.join(self.backup_dir, file)
                timestamp = datetime.fromtimestamp(os.path.getctime(backup_path))
                backups.append({
                    'filename': file,
                    'path': backup_path,
                    'created': timestamp,
                    'size': os.path.getsize(backup_path)
                })
        return sorted(backups, key=lambda x: x['created'], reverse=True)
