# =============================================================================
# FIREBASE UPLOAD MANAGER
# Handles immediate data upload and restore for HYPE Billing System
# =============================================================================

import firebase_admin
from firebase_admin import credentials, firestore
import sqlite3
import json
import os
import threading
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FirebaseUploadManager:
    """Manages real-time Firebase uploads and data restoration"""
    
    def __init__(self, firebase_sync_manager=None):
        """Initialize with Firebase sync manager instance"""
        self.fsm = firebase_sync_manager
        self.upload_queue = []
        self.upload_lock = threading.Lock()
        
    def upload_products(self, store_id: int, db_path: str) -> bool:
        """Upload all products to Firebase immediately"""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            logger.warning("Firebase not initialized for product upload")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM products')
            products = cursor.fetchall()
            
            if not products:
                logger.info("No products to upload")
                conn.close()
                return True
            
            products_data = [dict(p) for p in products]
            
            db = self.fsm.db
            batch = db.batch()
            
            for product in products_data:
                doc_id = product.get('id') or product.get('name', 'unknown')
                ref = db.collection(f'stores/{store_id}/products').document(str(doc_id))
                batch.set(ref, product, merge=True)
            
            backup_ref = db.collection(f'stores/{store_id}/products').document('backup')
            batch.set(backup_ref, {
                'products': products_data,
                'last_upload': datetime.now().isoformat(),
                'total_count': len(products_data)
            })
            
            batch.commit()
            conn.close()
            
            logger.info(f"✅ Uploaded {len(products_data)} products to Firebase (store {store_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading products: {e}")
            return False
    
    def upload_invoices(self, store_id: int, db_path: str) -> bool:
        """Upload all invoices to Firebase immediately"""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            logger.warning("Firebase not initialized for invoice upload")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM invoices')
            invoices = cursor.fetchall()
            
            if not invoices:
                logger.info("No invoices to upload")
                conn.close()
                return True
            
            invoices_data = []
            db = self.fsm.db
            batch = db.batch()
            
            for invoice in invoices:
                inv_dict = dict(invoice)
                inv_id = inv_dict.get('id', inv_dict.get('invoice_number', 'unknown'))
                
                cursor.execute('SELECT * FROM invoice_items WHERE invoice_id = ?', (inv_id,))
                items = cursor.fetchall()
                inv_dict['items'] = [dict(item) for item in items]
                
                invoices_data.append(inv_dict)
                
                ref = db.collection(f'stores/{store_id}/invoices').document(str(inv_id))
                batch.set(ref, inv_dict, merge=True)
            
            backup_ref = db.collection(f'stores/{store_id}/invoices').document('backup')
            batch.set(backup_ref, {
                'invoices': invoices_data,
                'last_upload': datetime.now().isoformat(),
                'total_count': len(invoices_data)
            })
            
            batch.commit()
            conn.close()
            
            logger.info(f"✅ Uploaded {len(invoices_data)} invoices to Firebase (store {store_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading invoices: {e}")
            return False
    
    def upload_customers(self, store_id: int, db_path: str) -> bool:
        """Upload all customers to Firebase immediately"""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            logger.warning("Firebase not initialized for customer upload")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM customers')
            customers = cursor.fetchall()
            
            if not customers:
                logger.info("No customers to upload")
                conn.close()
                return True
            
            customers_data = [dict(c) for c in customers]
            db = self.fsm.db
            batch = db.batch()
            
            for customer in customers_data:
                cust_id = customer.get('id') or customer.get('name', 'unknown')
                ref = db.collection(f'stores/{store_id}/customers').document(str(cust_id))
                batch.set(ref, customer, merge=True)
            
            backup_ref = db.collection(f'stores/{store_id}/customers').document('backup')
            batch.set(backup_ref, {
                'customers': customers_data,
                'last_upload': datetime.now().isoformat(),
                'total_count': len(customers_data)
            })
            
            batch.commit()
            conn.close()
            
            logger.info(f"✅ Uploaded {len(customers_data)} customers to Firebase (store {store_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading customers: {e}")
            return False
    
    def upload_users(self, db_path: str) -> bool:
        """Upload all users to Firebase immediately"""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            logger.warning("Firebase not initialized for user upload")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users')
            users = cursor.fetchall()
            
            if not users:
                logger.info("No users to upload")
                conn.close()
                return True
            
            users_data = [dict(u) for u in users]
            db = self.fsm.db
            
            db.collection('system').document('users').set({
                'users': users_data,
                'last_upload': datetime.now().isoformat(),
                'total_count': len(users_data)
            })
            
            conn.close()
            
            logger.info(f"✅ Uploaded {len(users_data)} users to Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading users: {e}")
            return False
    
    def upload_stock(self, store_id: int, db_path: str) -> bool:
        """Upload all stock data to Firebase immediately"""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            logger.warning("Firebase not initialized for stock upload")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock'")
            if not cursor.fetchone():
                conn.close()
                logger.info("Stock table does not exist")
                return True
            
            cursor.execute('SELECT * FROM stock')
            stock_data = [dict(row) for row in cursor.fetchall()]
            
            if not stock_data:
                logger.info("No stock data to upload")
                conn.close()
                return True
            
            db = self.fsm.db
            
            db.collection(f'stores/{store_id}/stock').document('backup').set({
                'stock': stock_data,
                'last_upload': datetime.now().isoformat(),
                'total_count': len(stock_data)
            })
            
            conn.close()
            
            logger.info(f"✅ Uploaded {len(stock_data)} stock records to Firebase (store {store_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading stock: {e}")
            return False
    
    def upload_all_data(self, store_id: int, db_path: str) -> dict:
        """Upload ALL data types to Firebase"""
        logger.info(f"🚀 STARTING COMPLETE DATA UPLOAD (store {store_id})...")
        
        results = {
            'products': self.upload_products(store_id, db_path),
            'invoices': self.upload_invoices(store_id, db_path),
            'customers': self.upload_customers(store_id, db_path),
            'users': self.upload_users(db_path),
            'stock': self.upload_stock(store_id, db_path),
        }
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ UPLOAD COMPLETE: {success_count}/{len(results)} data types uploaded successfully")
        
        return results

    # -------------------------------------------------------------------------
    # RESTORE / LOAD  (reads from the backup documents this class writes)
    # -------------------------------------------------------------------------

    def _restore_table(self, db_path: str, table: str, rows: list, pk_col: str = 'id') -> bool:
        """Insert rows from Firebase into a local SQLite table, skipping duplicates."""
        if not rows:
            return True
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Get current column names so we don't try to insert unknown columns
            cursor.execute(f'PRAGMA table_info({table})')
            cols = {row[1] for row in cursor.fetchall()}
            if not cols:
                conn.close()
                logger.warning(f"Table '{table}' not found in local DB — skipping restore")
                return False
            for row in rows:
                # Filter to only known columns
                filtered = {k: v for k, v in row.items() if k in cols}
                if not filtered:
                    continue
                placeholders = ', '.join(['?'] * len(filtered))
                col_names = ', '.join(filtered.keys())
                try:
                    conn.execute(
                        f'INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})',
                        list(filtered.values())
                    )
                except Exception as row_err:
                    logger.debug(f"Row insert skipped for {table}: {row_err}")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error restoring table '{table}': {e}")
            return False

    def restore_products_from_firebase(self, store_id: int, db_path: str) -> bool:
        """Load products from Firebase backup into local DB."""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            return False
        try:
            doc = self.fsm.db.collection(f'stores/{store_id}/products').document('backup').get()
            if not doc.exists:
                logger.info(f"No products backup found in Firebase for store {store_id}")
                return True
            products = doc.to_dict().get('products', [])
            result = self._restore_table(db_path, 'products', products)
            logger.info(f"✅ Restored {len(products)} products from Firebase (store {store_id})")
            return result
        except Exception as e:
            logger.error(f"Error restoring products from Firebase: {e}")
            return False

    def restore_invoices_from_firebase(self, store_id: int, db_path: str) -> bool:
        """Load invoices (and their items) from Firebase backup into local DB."""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            return False
        try:
            doc = self.fsm.db.collection(f'stores/{store_id}/invoices').document('backup').get()
            if not doc.exists:
                logger.info(f"No invoices backup found in Firebase for store {store_id}")
                return True
            invoices = doc.to_dict().get('invoices', [])
            items_all = []
            invoices_clean = []
            for inv in invoices:
                items = inv.pop('items', []) or []
                invoices_clean.append(inv)
                items_all.extend(items)
            r1 = self._restore_table(db_path, 'invoices', invoices_clean)
            r2 = self._restore_table(db_path, 'invoice_items', items_all)
            logger.info(f"✅ Restored {len(invoices_clean)} invoices, {len(items_all)} items from Firebase")
            return r1 and r2
        except Exception as e:
            logger.error(f"Error restoring invoices from Firebase: {e}")
            return False

    def restore_customers_from_firebase(self, store_id: int, db_path: str) -> bool:
        """Load customers from Firebase backup into local DB."""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            return False
        try:
            doc = self.fsm.db.collection(f'stores/{store_id}/customers').document('backup').get()
            if not doc.exists:
                logger.info(f"No customers backup found in Firebase for store {store_id}")
                return True
            customers = doc.to_dict().get('customers', [])
            result = self._restore_table(db_path, 'customers', customers)
            logger.info(f"✅ Restored {len(customers)} customers from Firebase")
            return result
        except Exception as e:
            logger.error(f"Error restoring customers from Firebase: {e}")
            return False

    def restore_users_from_firebase(self, db_path: str) -> bool:
        """Load users from Firebase backup into local DB."""
        if not self.fsm or not getattr(self.fsm, 'db', None):
            return False
        try:
            doc = self.fsm.db.collection('system').document('users').get()
            if not doc.exists:
                logger.info("No users backup found in Firebase")
                return True
            users = doc.to_dict().get('users', [])
            result = self._restore_table(db_path, 'users', users)
            logger.info(f"✅ Restored {len(users)} users from Firebase")
            return result
        except Exception as e:
            logger.error(f"Error restoring users from Firebase: {e}")
            return False

    def load_all_data(self, store_id: int, db_path: str) -> dict:
        """
        Load ALL data from Firebase backup documents and populate local SQLite DB.
        Uses self-contained restore methods — no dependency on FirebaseSync internals.
        """
        logger.info(f"📥 STARTING COMPLETE DATA LOAD (store {store_id})...")
        
        results = {
            'products':  self.restore_products_from_firebase(store_id, db_path),
            'invoices':  self.restore_invoices_from_firebase(store_id, db_path),
            'customers': self.restore_customers_from_firebase(store_id, db_path),
            'users':     self.restore_users_from_firebase(db_path),
        }
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ LOAD COMPLETE: {success_count}/{len(results)} data types loaded successfully")
        
        return results
    
    def sync_everything(self, store_id: int, db_path: str) -> bool:
        """Perform complete bidirectional sync: upload then load"""
        try:
            logger.info("🔄 STARTING COMPLETE BIDIRECTIONAL SYNC...")
            
            upload_results = self.upload_all_data(store_id, db_path)
            load_results = self.load_all_data(store_id, db_path)
            
            total_success = sum(1 for r in list(upload_results.values()) + list(load_results.values()) if r)
            total_ops = len(upload_results) + len(load_results)
            
            logger.info(f"✅ SYNC COMPLETE: {total_success}/{total_ops} operations successful")
            
            return total_success > 0
            
        except Exception as e:
            logger.error(f"Error in complete sync: {e}")
            return False


# Singleton instance
_upload_manager = None

def get_upload_manager(firebase_sync_manager=None):
    """Get or create Firebase upload manager"""
    global _upload_manager
    if _upload_manager is None:
        _upload_manager = FirebaseUploadManager(firebase_sync_manager)
    elif firebase_sync_manager and _upload_manager.fsm is None:
        _upload_manager.fsm = firebase_sync_manager
    return _upload_manager