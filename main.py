# =============================================================================
# HYPE ERP — Full Enterprise Resource Planning System
# Developer: David | GitHub: https://github.com/david0154
# Version: 3.0.0
# =============================================================================

from tkinter import *
from tkinter import messagebox, ttk, filedialog
import logging
import threading
import os
import tempfile
import sqlite3
from datetime import datetime, date
import sys
import json
import webbrowser
import time
import hashlib
import multiprocessing
from modules.window_utils import set_icon, get_runtime_path

# Windows single-instance lock (prevents multiple app instances)
try:
    import win32event
    import win32api
    import winerror
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ── Branding ───────────────────────────────────────────────────────────────────
HYPE_ERP_NAME    = 'Hype ERP'
HYPE_ERP_VERSION = 'v3.0.0'
HYPE_ERP_TAGLINE = 'Enterprise Resource Planning System'
HYPE_ERP_FOOTER  = f'Powered by {HYPE_ERP_NAME} | All rights reserved | {HYPE_ERP_VERSION}'

# ── Colours (design system) ───────────────────────────────────────────────────
C_BG       = '#0b0c1a'   # main background
C_SURFACE  = '#12142a'   # cards / panels
C_HEADER   = '#111327'   # top bar
C_ACCENT   = '#e94560'   # brand red
C_BLUE     = '#2563eb'   # blue accent
C_GREEN    = '#16a34a'
C_ORANGE   = '#ea580c'
C_PURPLE   = '#7c3aed'
C_TEAL     = '#0d9488'
C_TEXT     = '#e2e8f0'   # primary text
C_MUTED    = '#64748b'   # secondary text
C_BORDER   = '#1e2038'

FONT_UI    = 'Segoe UI'
CURRENCY   = '\u20b9'

# ── Optional Module Imports ─────────────────────────────────────────────────
try:
    from about import show_about as _show_about_fn
    HAS_ABOUT = True
except ImportError:
    HAS_ABOUT = False

try:
    from tally_features import TallyWindow, init_tally_tables
    HAS_TALLY = True
except ImportError:
    HAS_TALLY = False
    def init_tally_tables(): pass
    TallyWindow = None

try:
    from modules.hsn_config import HSNConfigModule
    HAS_HSN_CONFIG = True
except ImportError:
    HAS_HSN_CONFIG = False
    HSNConfigModule = None

try:
    from ai_assistant import AIAssistantWindow, predict_sales, is_model_installed, smart_product_search
    HAS_AI = True
except ImportError:
    HAS_AI = False
    AIAssistantWindow = None
    def predict_sales(n=7): return None
    def is_model_installed(k): return False
    def smart_product_search(q, p): return p

try:
    from firebase_deep import FirebaseDashboardWindow, firebase_manager, load_firebase_config
    HAS_FIREBASE_DEEP = True
except ImportError:
    HAS_FIREBASE_DEEP = False
    FirebaseDashboardWindow = None
    firebase_manager = None
    def load_firebase_config(): return {}

try:
    from firebase_sync import initialize_firebase_sync, shutdown_firebase_sync, get_firebase_sync_manager
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    def initialize_firebase_sync(*a, **k): return None
    def shutdown_firebase_sync(*a, **k): pass
    def get_firebase_sync_manager(): return None

try:
    from auto_install import run_auto_install
    HAS_AUTO_INSTALL = True
except ImportError:
    HAS_AUTO_INSTALL = False
    def run_auto_install(log_callback=None, done_callback=None):
        if done_callback: done_callback(True)

try:
    from modules.erp_main_menu import ERPMainMenu
    HAS_ERP_MODULES = True
except ImportError:
    HAS_ERP_MODULES = False
    ERPMainMenu = None

try:
    from billing_window import BillingWindow
    HAS_BILLING_MODULE = True
except ImportError:
    HAS_BILLING_MODULE = False
    BillingWindow = None

# ── State ─────────────────────────────────────────────────────────────────────
CURRENT_USER    = None
CURRENT_ROLE    = None
FIREBASE_SYNC   = None
root            = None
LOGIN_WINDOW    = None
APP_STARTED     = False
LOGIN_IN_PROGRESS = False
LOGIN_WINDOW_LOCK = threading.Lock()
WINDOW_CREATION_LOCK = threading.RLock()  # Recursive lock for window creation
APP_INSTANCE_LOCK = None  # Windows mutex for single instance

# ── Logging Setup ─────────────────────────────────────────────────────────────
def setup_logging():
    """Setup comprehensive logging to both console and file for EXE debugging."""
    log_dir = None
    
    # For frozen EXE, use LOCALAPPDATA
    if getattr(sys, 'frozen', False):
        log_dir = os.path.join(
            os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~'),
            'HypeERP'
        )
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'hype_erp.log')
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # File handler
    try:
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
    except Exception:
        fh = None
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if fh:
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

logger = setup_logging()

# ✅ Custom exception hook for windowed exe - catches unhandled exceptions
def custom_exception_hook(exc_type, exc_value, exc_traceback):
    """Log uncaught exceptions and show error dialog in windowed mode."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical(
        'Uncaught exception during startup:',
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    
    # Show error in windowed mode
    try:
        root_err = Tk()
        root_err.withdraw()
        error_msg = f'{exc_type.__name__}: {exc_value}\n\nCheck logs at:\n%LOCALAPPDATA%\\HypeERP\\hype_erp.log'
        messagebox.showerror('Application Startup Error', error_msg)
        root_err.destroy()
    except Exception:
        pass

sys.excepthook = custom_exception_hook

# ── GST Rates ────────────────────────────────────────────────────────────────
GST_RATES = {
    'Cosmetics':          {'SGST': 6,   'CGST': 6,   'IGST': 12},
    'Grocery':            {'SGST': 2.5, 'CGST': 2.5, 'IGST': 5},
    'Drinks':             {'SGST': 6,   'CGST': 6,   'IGST': 12},
    'Electronics':        {'SGST': 9,   'CGST': 9,   'IGST': 18},
    'Clothing':           {'SGST': 6,   'CGST': 6,   'IGST': 12},
    'Food & Beverage':    {'SGST': 2.5, 'CGST': 2.5, 'IGST': 5},
    'Dairy':              {'SGST': 2.5, 'CGST': 2.5, 'IGST': 5},
    'Pharmaceuticals':    {'SGST': 2.5, 'CGST': 2.5, 'IGST': 5},
    'Automotive':         {'SGST': 9,   'CGST': 9,   'IGST': 18},
    'Furniture':          {'SGST': 12,  'CGST': 12,  'IGST': 24},
    'Books':              {'SGST': 0,   'CGST': 0,   'IGST': 0},
    'Education Services': {'SGST': 0,   'CGST': 0,   'IGST': 0},
    'Healthcare':         {'SGST': 0,   'CGST': 0,   'IGST': 0},
    'Agriculture':        {'SGST': 0,   'CGST': 0,   'IGST': 0},
    'Construction':       {'SGST': 12,  'CGST': 12,  'IGST': 24},
    'Metals':             {'SGST': 18,  'CGST': 18,  'IGST': 36},
    'Chemicals':          {'SGST': 18,  'CGST': 18,  'IGST': 36},
    'Tobacco':            {'SGST': 28,  'CGST': 28,  'IGST': 56},
    'Petroleum Products': {'SGST': 0,   'CGST': 0,   'IGST': 0},
    'Services':           {'SGST': 18,  'CGST': 18,  'IGST': 36},
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()

def _is_hashed(pwd: str) -> bool:
    return len(pwd) == 64 and all(c in '0123456789abcdef' for c in pwd.lower())

def _migrate_passwords(conn):
    try:
        c = conn.cursor()
        c.execute('SELECT id, password FROM users')
        for uid, pwd in c.fetchall():
            if not _is_hashed(pwd):
                conn.execute('UPDATE users SET password=? WHERE id=?', (_hash_password(pwd), uid))
        conn.commit()
    except Exception:
        pass

    try:
        c = conn.cursor()
        c.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in c.fetchall()]
        if 'phone' not in cols:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
            except Exception:
                pass
    except Exception:
        pass

def _migrate_products(conn):
    """✅ Add category_code column to products table if it doesn't exist"""
    try:
        c = conn.cursor()
        c.execute("PRAGMA table_info(products)")
        cols = [row[1] for row in c.fetchall()]
        if 'category_code' not in cols:
            conn.execute('ALTER TABLE products ADD COLUMN category_code TEXT')
            conn.commit()
    except Exception:
        pass

# ── Firebase key ─────────────────────────────────────────────────────────────────
FIREBASE_SECRET_KEY = b'J6TmP2PtNyXGZX28P8b2_CO2xRJ2c-xk2AIIJtu1gPc='

def _firebase_configured():
    """True only when a real serviceAccountKey file exists."""
    enc = get_runtime_path('serviceAccountKey.enc')
    key = get_runtime_path('serviceAccountKey.json')
    return os.path.exists(enc) or os.path.exists(key)

def load_firebase_key_temp():
    enc_path = get_runtime_path('serviceAccountKey.enc')
    if not os.path.exists(enc_path):
        return None
    try:
        from cryptography.fernet import Fernet
        with open(enc_path, 'rb') as f:
            data = f.read()
        cipher = Fernet(FIREBASE_SECRET_KEY)
        decrypted = cipher.decrypt(data)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        tmp.write(decrypted)
        tmp.close()
        return tmp.name
    except Exception:
        return None

# ── Database path ────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _app_dir = os.path.join(
        os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~'),
        'HypeERP'
    )
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(_app_dir, exist_ok=True)
DB_PATH = os.path.join(_app_dir, 'hype_billing_system.db')

# Log startup info now that variables are defined
logger.info(f'=== {HYPE_ERP_NAME} {HYPE_ERP_VERSION} Started ===')
logger.info(f'Running from: {os.path.abspath(__file__)}')
logger.info(f'Database path: {DB_PATH}')
logger.info(f'Python version: {sys.version}')
logger.info(f'Platform: {sys.platform}')
logger.info(f'Frozen: {getattr(sys, "frozen", False)}')


def _get_login_firebase_credentials_path():
    try:
        temp_path = load_firebase_key_temp()
        if temp_path and os.path.exists(temp_path):
            return temp_path
    except Exception as exc:
        logger.warning(f'Unable to load temp Firebase credentials: {exc}')

    runtime_path = get_runtime_path('serviceAccountKey.json')
    if os.path.exists(runtime_path):
        return runtime_path

    enc_path = get_runtime_path('serviceAccountKey.enc')
    if os.path.exists(enc_path):
        return enc_path

    logger.warning('No Firebase credentials found for login flow')
    return None


# ── Database init ────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'cashier',
            full_name TEXT, email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, barcode TEXT UNIQUE,
            category TEXT, category_code TEXT, unit TEXT DEFAULT 'pcs',
            purchase_price REAL DEFAULT 0.0, selling_price REAL DEFAULT 0.0,
            stock INTEGER DEFAULT 0, min_stock INTEGER DEFAULT 10,
            gst_rate REAL DEFAULT 18.0, hsn_code TEXT, last_sold TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL, date TEXT NOT NULL,
            customer_name TEXT, customer_phone TEXT, customer_gstin TEXT,
            subtotal REAL DEFAULT 0.0, gst_amount REAL DEFAULT 0.0,
            discount REAL DEFAULT 0.0, total_amount REAL DEFAULT 0.0,
            payment_method TEXT DEFAULT 'Cash', payment_status TEXT DEFAULT 'Paid',
            notes TEXT, created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL, product_id INTEGER,
            product_name TEXT NOT NULL, quantity INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0.0, gst_rate REAL DEFAULT 0.0,
            gst_amount REAL DEFAULT 0.0, total REAL DEFAULT 0.0,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT, gstin TEXT,
            total_purchases REAL DEFAULT 0.0, visit_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT NOT NULL, address TEXT, phone TEXT, email TEXT,
            gstin TEXT, owner_name TEXT, state_code TEXT DEFAULT '29',
            logo_path TEXT, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS category_hsn_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            hsn_code TEXT NOT NULL,
            description TEXT,
            gst_rate REAL DEFAULT 18.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    _migrate_passwords(conn)
    _migrate_products(conn)
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO users (username,password,role,full_name) VALUES (?,?,?,?)',
                  ('admin', _hash_password('admin123'), 'admin', 'Administrator'))
    conn.commit()
    conn.close()
    try: init_tally_tables()
    except Exception: pass
    try: _init_default_hsn_codes()
    except Exception as e:
        print(f"Note: Could not initialize HSN codes: {e}")

def _init_default_hsn_codes():
    """Initialize default HSN codes for standard categories"""
    DEFAULT_HSN = {
        'Cosmetics': '3304', 'Grocery': '0901', 'Drinks': '2202',
        'Electronics': '8471', 'Clothing': '6201', 'Food & Beverage': '1905',
        'Dairy': '0401', 'Pharmaceuticals': '3004', 'Automotive': '8704',
        'Furniture': '9403', 'Books': '4901', 'Education Services': '9209',
        'Healthcare': '6211', 'Agriculture': '1001', 'Construction': '6810',
        'Metals': '7208', 'Chemicals': '2817', 'Tobacco': '2402',
        'Services': '9999', 'Petroleum Products': '2710',
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for cat, hsn in DEFAULT_HSN.items():
            c.execute("INSERT OR IGNORE INTO category_hsn_mapping (category, hsn_code) VALUES (?, ?)",
                     (cat, hsn))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing HSN codes: {e}")

def get_setting(key, default=''):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT value FROM settings WHERE key=?', (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def _is_local_db_blank(db_path=None):
    db_path = DB_PATH if db_path is None else db_path
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        for table in ('products', 'customers', 'invoices'):
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if c.fetchone() is None:
                continue
            c.execute(f'SELECT COUNT(1) FROM {table}')
            if c.fetchone()[0] > 0:
                conn.close()
                return False
        conn.close()
        return True
    except Exception:
        return False


def _query_local_user(username, password_hash, db_path=None):
    db_path = DB_PATH if db_path is None else db_path
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT username, role FROM users WHERE username=? AND password=?',
                  (username, password_hash))
        result = c.fetchone()
        conn.close()
        if result:
            logger.info(f'Local user authentication SUCCESS for user={username}, role={result[1]}')
        else:
            logger.warning(f'Local user authentication FAILED for user={username}')
        return result
    except Exception as e:
        logger.error(f'Error querying local user {username}: {e}')
        return None


def _authenticate_user_and_restore(username, password_hash, firebase_sync_manager=None, db_path=None):
    """Enhanced authentication that works for ALL users (admin, manager, cashier)"""
    db_path = DB_PATH if db_path is None else db_path
    logger.info(f'[AUTH] Starting authentication for user={username}')
    
    # Step 1: Try local database first (fastest)
    row = _query_local_user(username, password_hash, db_path=db_path)
    if row:
        logger.info(f'[AUTH] ✅ Local authentication SUCCESS for user={username}, role={row[1]}')
        return row
    
    logger.info(f'[AUTH] User {username} not in local DB, checking Firebase...')
    
    # Step 2: Get Firebase manager if not provided
    if firebase_sync_manager is None:
        try:
            from firebase_sync import get_firebase_sync_manager
            credentials_path = _get_login_firebase_credentials_path()
            firebase_sync_manager = get_firebase_sync_manager(credentials_path=credentials_path)
        except Exception as e:
            logger.warning(f'[AUTH] Firebase manager error: {e}')
            firebase_sync_manager = None

    # If Firebase is not available, log warning but DON'T return None yet
    # (users might still exist locally or be created during app startup)
    if not firebase_sync_manager or not getattr(firebase_sync_manager, 'db', None):
        logger.warning(f'[AUTH] Firebase not available for user {username}, but continuing with offline-first mode')

    try:
        store_id = int(get_setting('store_id', '1'))
    except Exception:
        store_id = 1

    # Step 3: Auto-restore ALL data if local DB is completely empty (only if Firebase available)
    if firebase_sync_manager and getattr(firebase_sync_manager, 'db', None):
        if _is_local_db_blank(db_path):
            try:
                logger.info(f'[AUTH] Local DB blank, auto-restoring from Firebase (store_id={store_id})...')
                firebase_sync_manager.auto_restore_all_data(store_id)
                logger.info(f'[AUTH] Auto-restore completed successfully')
            except Exception as ex:
                logger.warning(f'[AUTH] Auto-restore error: {ex}')
            
            # Try local auth again after restore
            row = _query_local_user(username, password_hash, db_path=db_path)
            if row:
                logger.info(f'[AUTH] ✅ Authentication SUCCESS after restore: user={username}, role={row[1]}')
                return row

        # Step 4: Try individual user restore from Firebase (works for any user)
        if not row:
            try:
                logger.info(f'[AUTH] Attempting to restore user {username} from Firebase...')
                restored = firebase_sync_manager.restore_user_from_firebase(username, password_hash=password_hash)
                if restored:
                    logger.info(f'[AUTH] ✅ User restored from Firebase: {username}')
                    row = _query_local_user(username, password_hash, db_path=db_path)
                    if row:
                        logger.info(f'[AUTH] ✅ Authentication SUCCESS after Firebase restore: user={username}, role={row[1]}')
                        return row
                else:
                    logger.warning(f'[AUTH] Firebase restore returned False for user {username}')
            except Exception as e:
                logger.error(f'[AUTH] Firebase user restore failed for {username}: {e}')

        # Step 5: Last resort - Check if user exists in Firebase backup data
        if not row:
            try:
                from firebase_sync import _normalize_password_for_restore
                logger.info(f'[AUTH] Checking Firebase users collection for {username}...')
                users_doc = firebase_sync_manager.db.collection('stores').document(str(store_id)).collection('users').document('backup').get()
                if users_doc.exists:
                    users_data = users_doc.to_dict().get('users', [])
                    for u in users_data:
                        if u.get('username') == username:
                            logger.info(f'[AUTH] Found user {username} in Firebase backup, verifying password...')
                            # Normalize and verify password
                            normalized_pwd = _normalize_password_for_restore(u.get('password'))
                            if password_hash == normalized_pwd or password_hash == u.get('password'):
                                role = u.get('role', 'cashier')  # Default to cashier if no role specified
                                logger.info(f'[AUTH] Password verified, creating local entry for {username} with role={role}')
                                # Create user in local DB
                                conn = sqlite3.connect(db_path)
                                cursor = conn.cursor()
                                try:
                                    cursor.execute(
                                        'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
                                        (username, normalized_pwd, role, u.get('full_name', username))
                                    )
                                    conn.commit()
                                    logger.info(f'[AUTH] ✅ Created user {username} in local DB with role {role}')
                                    row = (username, role)
                                except sqlite3.IntegrityError as ie:
                                    logger.warning(f'[AUTH] User {username} already exists in local DB: {ie}')
                                    # Try to query again
                                    row = _query_local_user(username, password_hash, db_path=db_path)
                                except Exception as e:
                                    logger.warning(f'[AUTH] Could not create user {username}: {e}')
                                finally:
                                    conn.close()
                                if row:
                                    return row
                            else:
                                logger.warning(f'[AUTH] Password mismatch for {username} in Firebase')
            except Exception as e:
                logger.error(f'[AUTH] Firebase backup check error: {e}')
    else:
        logger.info(f'[AUTH] Firebase not available, skipping Firebase restore operations for {username}')

    logger.error(f'[AUTH] ❌ Authentication FAILED for user={username} (not found in local DB or Firebase)')
    return None


def set_setting(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, value))
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_gst_rates():
    raw = get_setting('gst_rates_json', '')
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return GST_RATES.copy()

def save_gst_rates(rates):
    try:
        set_setting('gst_rates_json', json.dumps(rates))
    except Exception:
        pass


def get_gst_rate_for_category(category):
    try:
        category = str(category or '').strip()
        if not category:
            return 18.0
        rates = load_gst_rates()
        if isinstance(rates, dict):
            entry = rates.get(category)
            if isinstance(entry, dict):
                sgst = float(entry.get('SGST') or 0)
                cgst = float(entry.get('CGST') or 0)
                if sgst or cgst:
                    return sgst + cgst
                igst = entry.get('IGST')
                if igst is not None:
                    return float(igst)
    except Exception:
        pass
    return 18.0


def get_product_categories():
    categories = set(load_gst_rates().keys())
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS product_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()
        cur.execute('SELECT name FROM product_categories ORDER BY name')
        for row in cur.fetchall():
            if row and row[0]:
                categories.add(row[0])
        conn.close()
    except Exception:
        pass
    return sorted(categories)


def generate_invoice_number():
    prefix = get_setting('invoice_prefix', 'INV')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM invoices')
    count = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{datetime.now().strftime('%Y%m')}-{count:04d}"

def get_dashboard_stats():
    s = {'invoices': 0, 'products': 0, 'low_stock': 0, 'revenue': 0.0, 'today': 0.0}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM invoices'); s['invoices'] = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM products'); s['products'] = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM products WHERE stock < min_stock'); s['low_stock'] = c.fetchone()[0]
        c.execute('SELECT COALESCE(SUM(total_amount),0) FROM invoices'); s['revenue'] = c.fetchone()[0]
        today = date.today().isoformat()
        c.execute('SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE date=?', (today,))
        s['today'] = c.fetchone()[0]
        conn.close()
    except Exception:
        pass
    return s

# ── TTK style ────────────────────────────────────────────────────────────────────
def apply_dark_style():
    s = ttk.Style()
    try: s.theme_use('clam')
    except Exception: pass
    s.configure('Dark.Treeview',
                 background=C_SURFACE, foreground=C_TEXT,
                 fieldbackground=C_SURFACE, rowheight=30,
                 font=(FONT_UI, 9))
    s.configure('Dark.Treeview.Heading',
                 background=C_HEADER, foreground='#94a3b8',
                 font=(FONT_UI, 9, 'bold'), relief='flat')
    s.map('Dark.Treeview', background=[('selected', C_ACCENT)])
    s.configure('Dark.TScrollbar', background=C_SURFACE,
                 troughcolor=C_BG, arrowcolor=C_MUTED)

# ── AI helpers ──────────────────────────────────────────────────────────────────
def _show_ai_prediction():
    if not HAS_AI:
        messagebox.showinfo('AI', 'AI module not available.'); return
    try:
        if not is_model_installed('sales_predictor'):
            if messagebox.askyesno('AI', 'Sales predictor not installed.\nOpen AI Assistant?'):
                AIAssistantWindow(root)
            return
        preds = predict_sales(7, db_path=DB_PATH)
        if preds:
            days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
            msg = f'{HYPE_ERP_NAME} — AI Sales Forecast (Next 7 Days):\n\n'
            for i, v in enumerate(preds):
                msg += f'  {days[i%7]}: {CURRENCY}{v:,.0f}  {"\u2588"*min(int(v/500),20)}\n'
            msg += f'\n  Weekly Total: {CURRENCY}{sum(preds):,.0f}'
            messagebox.showinfo(f'\U0001f916 AI Prediction', msg)
        else:
            messagebox.showinfo('AI', 'Model is still training. Try again.')
    except Exception as e:
        messagebox.showwarning('AI', str(e))

def _trigger_full_sync():
    global FIREBASE_SYNC
    if not _firebase_configured():
        messagebox.showwarning('Firebase', 'Firebase not configured.\nAdd serviceAccountKey.json to use cloud sync.')
        return
    if FIREBASE_AVAILABLE and FIREBASE_SYNC:
        def do():
            try:
                FIREBASE_SYNC.full_sync(1)
                root.after(0, lambda: messagebox.showinfo('Sync', 'Firebase sync complete!'))
            except Exception as e:
                root.after(0, lambda: messagebox.showwarning('Sync', str(e)))
        threading.Thread(target=do, daemon=True).start()
        messagebox.showinfo('Sync', '\U0001f504 Syncing in background...')
    else:
        messagebox.showwarning('Firebase', 'Firebase not connected.')

def _trigger_backup():
    if not _firebase_configured():
        messagebox.showwarning('Backup', 'Firebase not configured.\nAdd serviceAccountKey.json first.')
        return
    try:
        if not HAS_FIREBASE_DEEP or not firebase_manager:
            messagebox.showwarning('Backup', 'Firebase Deep module not available.'); return
        if not firebase_manager.db:
            ok, msg = firebase_manager.initialize('serviceAccountKey.json')
            if not ok:
                messagebox.showerror('Firebase', msg); return
        cfg = load_firebase_config()
        shop_id = cfg.get('shop_id', get_setting('shop_id', 'default_shop'))
        firebase_manager.backup_database(
            shop_id, DB_PATH,
            callback=lambda ok, m: root.after(0, lambda: messagebox.showinfo('Backup', m))
        )
        messagebox.showinfo('Backup', 'Cloud backup started...')
    except Exception as e:
        messagebox.showerror('Backup Error', str(e))

# ───────────────────────────────────────────────────────────────────────────────
# LOGIN WINDOW
# ───────────────────────────────────────────────────────────────────────────────
def show_login():
    global CURRENT_USER, CURRENT_ROLE, LOGIN_WINDOW, LOGIN_IN_PROGRESS, APP_STARTED

    # Use recursive lock to prevent any race conditions
    with WINDOW_CREATION_LOCK:
        logger.info('[LOGIN] show_login() called')
        
        # ✅ REMOVED: PID file check was causing child process issues with sklearn/multiprocessing
        # The Windows single-instance mutex (APP_INSTANCE_LOCK) is sufficient for PyInstaller
        
        # Check 1: If login is already in progress, don't do anything
        if LOGIN_IN_PROGRESS:
            logger.warning('[LOGIN] ⚠️ Login in progress, ignoring duplicate request')
            return

        # Check 2: If main app is already running, bring to foreground
        if APP_STARTED and root is not None:
            try:
                if root.winfo_exists():
                    logger.info('[LOGIN] Main app already running, bringing to foreground')
                    root.deiconify()
                    root.focus_force()
                    return
            except Exception as e:
                logger.error(f'[LOGIN] Error checking main app: {e}')

        # Check 3: If login window already exists, bring to foreground
        if LOGIN_WINDOW is not None:
            try:
                if LOGIN_WINDOW.winfo_exists():
                    logger.info('[LOGIN] Login window exists, bringing to foreground')
                    LOGIN_WINDOW.deiconify()
                    LOGIN_WINDOW.focus_force()
                    return
                else:
                    logger.info('[LOGIN] Previous login window was destroyed')
                    LOGIN_WINDOW = None
            except Exception as e:
                logger.error(f'[LOGIN] Error checking login window: {e}')
                LOGIN_WINDOW = None

        # Check 4: Prevent window creation race condition - FINAL CHECK
        if LOGIN_WINDOW is not None:
            logger.warning('[LOGIN] LOGIN_WINDOW is not None after cleanup, aborting creation')
            return

        logger.info('[LOGIN] Creating new login window...')
        
        # Create window and assign INSIDE the lock to prevent race conditions
        try:
            lw = Tk()
            lw.title(f'{HYPE_ERP_NAME} — Login')
            lw.geometry('440x520')
            lw.configure(bg=C_BG)
            lw.resizable(False, False)
            set_icon(lw)
            
            # ✅ Show window explicitly - critical for windowed exe
            lw.deiconify()
            lw.lift()
            lw.focus_force()
            
            LOGIN_WINDOW = lw
            logger.info('[LOGIN] ✅ New login window created and assigned')
        except Exception as e:
            logger.error(f'[LOGIN] Failed to create window: {e}')
            LOGIN_WINDOW = None
            return

    def _close_login_window():
        global LOGIN_WINDOW
        try:
            if LOGIN_WINDOW is not None and LOGIN_WINDOW.winfo_exists():
                LOGIN_WINDOW.destroy()
        finally:
            LOGIN_WINDOW = None

    # gradient-like header
    hdr = Frame(lw, bg=C_HEADER, pady=28)
    hdr.pack(fill='x')
    Label(hdr, text='\U0001f3e2', font=(FONT_UI, 40), bg=C_HEADER, fg='white').pack()
    Label(hdr, text=HYPE_ERP_NAME, font=(FONT_UI, 22, 'bold'),
          bg=C_HEADER, fg=C_ACCENT).pack()
    Label(hdr, text=HYPE_ERP_TAGLINE, font=(FONT_UI, 9),
          bg=C_HEADER, fg=C_MUTED).pack(pady=(2, 0))

    body = Frame(lw, bg=C_BG, padx=44, pady=22)
    body.pack(fill='both', expand=True)

    def field(parent, label, show=None):
        Label(parent, text=label, bg=C_BG, fg='#94a3b8',
              font=(FONT_UI, 9)).pack(anchor='w', pady=(12, 3))
        v = StringVar()
        e = Entry(parent, textvariable=v, bg=C_SURFACE, fg=C_TEXT,
                  insertbackground=C_TEXT, font=(FONT_UI, 12),
                  relief='flat', bd=0, highlightthickness=1,
                  highlightbackground=C_BORDER, highlightcolor=C_ACCENT)
        if show:
            e.config(show=show)
        e.pack(fill='x', ipady=8)
        return v

    user_var = field(body, 'Username')
    pass_var = field(body, 'Password', show='\u2022')

    err_lbl = Label(body, text='', bg=C_BG, fg='#f87171', font=(FONT_UI, 9))
    err_lbl.pack(pady=(8, 0))

    def do_login():
        global CURRENT_USER, CURRENT_ROLE, LOGIN_IN_PROGRESS, LOGIN_WINDOW

        if LOGIN_IN_PROGRESS:
            return

        uname = user_var.get().strip()
        password = pass_var.get()
        
        if not uname or not password:
            err_lbl.config(text='⚠️ Enter username and password')
            return
        
        password_hash = _hash_password(password)
        LOGIN_IN_PROGRESS = True

        try:
            from firebase_sync import firebase_sync_manager
        except Exception:
            firebase_sync_manager = None

        sign_in_btn.config(state='disabled')
        try:
            row = _authenticate_user_and_restore(uname, password_hash, firebase_sync_manager=firebase_sync_manager)
            if row:
                CURRENT_USER, CURRENT_ROLE = row
                logger.info(f'[LOGIN] ✅ Login successful for {CURRENT_USER} ({CURRENT_ROLE})')
                try:
                    if LOGIN_WINDOW is not None and LOGIN_WINDOW.winfo_exists():
                        LOGIN_WINDOW.destroy()
                finally:
                    LOGIN_WINDOW = None
                # Schedule main app launch to prevent blocking
                lw.after(50, launch_main_app)
            else:
                logger.warning(f'[LOGIN] ❌ Login failed for {uname}')
                err_lbl.config(text='\u274c Incorrect username or password')
        except Exception as e:
            logger.error(f'[LOGIN] Exception during login: {e}')
            err_lbl.config(text=f'⚠️ Login error: {str(e)[:40]}')
        finally:
            LOGIN_IN_PROGRESS = False
            try:
                sign_in_btn.config(state='normal')
            except Exception:
                pass

    def start_login_flow():
        global CURRENT_USER, CURRENT_ROLE, LOGIN_IN_PROGRESS

        if LOGIN_IN_PROGRESS:
            return

        uname = user_var.get().strip()
        password = pass_var.get()
        password_hash = _hash_password(password)
        LOGIN_IN_PROGRESS = True

        def show_status(text, color=C_BLUE):
            try:
                if LOGIN_WINDOW is not None and LOGIN_WINDOW.winfo_exists():
                    LOGIN_WINDOW.after(0, lambda: err_lbl.config(text=text, fg=color))
            except Exception:
                pass

        def finish_login(row, error_message=None):
            global CURRENT_USER, CURRENT_ROLE, LOGIN_IN_PROGRESS, LOGIN_WINDOW
            LOGIN_IN_PROGRESS = False
            try:
                if row:
                    CURRENT_USER, CURRENT_ROLE = row
                    if LOGIN_WINDOW is not None and LOGIN_WINDOW.winfo_exists():
                        LOGIN_WINDOW.destroy()
                    LOGIN_WINDOW = None
                    launch_main_app()
                    return

                if error_message:
                    err_lbl.config(text=f'⚠️ {error_message}', fg='#f87171')
                else:
                    err_lbl.config(text='❌ Incorrect username or password', fg='#f87171')
            finally:
                try:
                    sign_in_btn.config(state='normal')
                except Exception:
                    pass

        sign_in_btn.config(state='disabled')
        show_status('Checking credentials...', C_BLUE)

        def worker():
            row = None
            error_message = None
            credentials_path = _get_login_firebase_credentials_path()
            logger.info(f'Login attempt for user={uname}, db_path={DB_PATH}, credentials_path={credentials_path}')
            try:
                row = _query_local_user(uname, password_hash, db_path=DB_PATH)
                if row:
                    logger.info(f'Local login succeeded for user={uname}')
                else:
                    if _is_local_db_blank(DB_PATH):
                        show_status('Restoring data from Firebase...', C_BLUE)
                        logger.info(f'Local DB is blank, attempting Firebase restore for user={uname}')
                    firebase_sync_manager = get_firebase_sync_manager(credentials_path=credentials_path)
                    logger.info(f'Firebase manager ready: {type(firebase_sync_manager).__name__}, db={bool(getattr(firebase_sync_manager, "db", None))}, creds={getattr(firebase_sync_manager, "credentials_path", None)}')
                    row = _authenticate_user_and_restore(uname, password_hash, firebase_sync_manager=firebase_sync_manager)
            except Exception as exc:
                error_message = str(exc) or 'Unable to complete sign in right now.'
                logger.exception(f'Login worker failed for user={uname}: {error_message}')

            try:
                if LOGIN_WINDOW is not None and LOGIN_WINDOW.winfo_exists():
                    LOGIN_WINDOW.after(0, lambda: finish_login(row, error_message))
            except Exception:
                finish_login(row, error_message)

        threading.Thread(target=worker, daemon=True).start()

    sign_in_btn = Button(body, text='Sign In', bg=C_ACCENT, fg='white',
                         font=(FONT_UI, 12, 'bold'), relief='flat',
                         padx=20, pady=10, cursor='hand2',
                         activebackground='#c73652', activeforeground='white',
                         command=start_login_flow)
    sign_in_btn.pack(fill='x', pady=(18, 0))

    lw.protocol('WM_DELETE_WINDOW', _close_login_window)
    lw.bind('<Return>', lambda e: start_login_flow())
    Label(body, text=HYPE_ERP_FOOTER, bg=C_BG, fg='#2d2d4e',
          font=(FONT_UI, 7)).pack(side='bottom', pady=8)
    
    # ✅ Ensure window is rendered and visible before mainloop
    lw.update_idletasks()
    lw.mainloop()

# ───────────────────────────────────────────────────────────────────────────────
# MODULE WINDOWS
# ───────────────────────────────────────────────────────────────────────────────
def _win_base(title, w=1000, h=600):
    win = Toplevel(root)
    win.title(title)
    win.geometry(f'{w}x{h}')
    win.configure(bg=C_BG)
    set_icon(win)
    return win

def _win_header(win, icon, title):
    hdr = Frame(win, bg=C_HEADER, pady=10)
    hdr.pack(fill='x')
    Label(hdr, text=f'{icon}  {title}', font=(FONT_UI, 14, 'bold'),
          bg=C_HEADER, fg=C_TEXT).pack(side='left', padx=16)
    Label(hdr, text=HYPE_ERP_VERSION, font=(FONT_UI, 8),
          bg=C_HEADER, fg=C_MUTED).pack(side='right', padx=16)
    return hdr

def _win_footer(win):
    Label(win, text=HYPE_ERP_FOOTER, bg=C_HEADER, fg='#2d3561',
          font=(FONT_UI, 7)).pack(side='bottom', fill='x', ipady=3)

def open_billing_window():
    if HAS_BILLING_MODULE:
        BillingWindow(root, DB_PATH, current_user=CURRENT_USER,
                      get_setting_fn=get_setting,
                      generate_invoice_fn=generate_invoice_number)
    else:
        # Fallback basic billing
        win = _win_base(f'{HYPE_ERP_NAME} — Billing', 1100, 720)
        _win_header(win, '\U0001f9fe', f'{HYPE_ERP_NAME} — GST Invoice')
        Label(win, text='billing_window.py not found — please ensure it is in the same folder.',
              bg=C_BG, fg='#f87171', font=(FONT_UI, 11)).pack(pady=40)
        _win_footer(win)

def open_products_window():
    win = _win_base(f'{HYPE_ERP_NAME} — Products', 1050, 640)
    _win_header(win, '\U0001f4e6', 'Product Management')

    toolbar = Frame(win, bg=C_SURFACE, pady=6)
    toolbar.pack(fill='x', padx=12, pady=(8, 0))

    cols = ('ID', 'Name', 'Category', 'Sell Price', 'Stock', 'Min', 'GST%', 'Barcode')
    frame = Frame(win, bg=C_BG)
    frame.pack(fill='both', expand=True, padx=12, pady=6)
    tree = ttk.Treeview(frame, columns=cols, show='headings',
                        height=18, style='Dark.Treeview')
    for col, w in zip(cols, [50, 220, 120, 90, 70, 60, 60, 130]):
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor='center' if col not in ('Name', 'Category', 'Barcode') else 'w')
    sb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=sb.set)
    tree.pack(side='left', fill='both', expand=True)
    sb.pack(side='right', fill='y')

    def refresh():
        for i in tree.get_children(): tree.delete(i)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id,name,category,selling_price,stock,min_stock,gst_rate,barcode FROM products ORDER BY name')
        for row in c.fetchall():
            tags = ('low',) if row[4] < row[5] else ()
            tree.insert('', 'end', values=row, tags=tags)
        tree.tag_configure('low', foreground='#fbbf24')
        conn.close()

    def adjust_price_dialog():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a product first.', parent=win); return
        row = tree.item(sel[0])['values']
        prod_id, name, curr_price = row[0], row[1], row[3]
        
        d = Toplevel(win)
        d.title(f'Adjust Price: {name}')
        d.geometry('380x240')
        d.configure(bg=C_BG)
        set_icon(d)
        Label(d, text=f'Adjust Price: {name}', bg=C_BG, fg=C_ACCENT,
              font=(FONT_UI, 11, 'bold')).pack(pady=12)
        Label(d, text=f'Current Price: {CURRENCY}{curr_price}', bg=C_BG, fg='#94a3b8',
              font=(FONT_UI, 9)).pack()
        
        Label(d, text='New Price:', bg=C_BG, fg='#94a3b8', font=(FONT_UI, 9)).pack(anchor='w', padx=28, pady=(12, 2))
        price_var = StringVar(value=str(curr_price))
        Entry(d, textvariable=price_var, bg=C_SURFACE, fg=C_TEXT, insertbackground=C_TEXT,
              relief='flat', highlightthickness=1, highlightbackground=C_BORDER).pack(fill='x', padx=28, ipady=6)
        
        def save_price():
            try:
                new_price = float(price_var.get())
                conn = sqlite3.connect(DB_PATH)
                conn.execute('UPDATE products SET selling_price = ? WHERE id = ?', (new_price, prod_id))
                conn.commit(); conn.close()
                refresh(); d.destroy()
                messagebox.showinfo(HYPE_ERP_NAME, f'Price updated to {CURRENCY}{new_price}!')
            except Exception as e:
                messagebox.showerror('Error', str(e))
        
        Button(d, text='\u2714 Save', bg=C_ACCENT, fg='white', command=save_price,
               relief='flat', padx=14, pady=7, font=(FONT_UI, 9, 'bold')).pack(pady=12)

    def restock_dialog():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a product first.', parent=win); return
        row = tree.item(sel[0])['values']
        prod_id, name, curr_stock = row[0], row[1], row[4]
        
        d = Toplevel(win)
        d.title(f'Restock: {name}')
        d.geometry('380x240')
        d.configure(bg=C_BG)
        set_icon(d)
        Label(d, text=f'Restock: {name}', bg=C_BG, fg=C_ACCENT,
              font=(FONT_UI, 11, 'bold')).pack(pady=12)
        Label(d, text=f'Current Stock: {curr_stock} units', bg=C_BG, fg='#94a3b8',
              font=(FONT_UI, 9)).pack()
        
        Label(d, text='Add Quantity:', bg=C_BG, fg='#94a3b8', font=(FONT_UI, 9)).pack(anchor='w', padx=28, pady=(12, 2))
        qty_var = StringVar(value='0')
        Entry(d, textvariable=qty_var, bg=C_SURFACE, fg=C_TEXT, insertbackground=C_TEXT,
              relief='flat', highlightthickness=1, highlightbackground=C_BORDER).pack(fill='x', padx=28, ipady=6)
        
        def save_restock():
            try:
                add_qty = int(qty_var.get())
                new_stock = curr_stock + add_qty
                conn = sqlite3.connect(DB_PATH)
                conn.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, prod_id))
                conn.commit(); conn.close()
                refresh(); d.destroy()
                messagebox.showinfo(HYPE_ERP_NAME, f'Stock updated to {new_stock} units!')
            except Exception as e:
                messagebox.showerror('Error', str(e))
        
        Button(d, text='\u2714 Save', bg=C_ACCENT, fg='white', command=save_restock,
               relief='flat', padx=14, pady=7, font=(FONT_UI, 9, 'bold')).pack(pady=12)

    def delete_product():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a product first.', parent=win); return
        row = tree.item(sel[0])['values']
        prod_id, name = row[0], row[1]
        
        if messagebox.askyesno('Confirm', f'Delete product "{name}"?', parent=win):
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute('DELETE FROM products WHERE id = ?', (prod_id,))
                conn.commit(); conn.close()
                refresh()
                messagebox.showinfo(HYPE_ERP_NAME, f'Product "{name}" deleted!')
            except Exception as e:
                messagebox.showerror('Error', str(e), parent=win)

    def add_product_dialog():
        d = Toplevel(win)
        d.title('Add Product')
        d.geometry('500x620')
        d.configure(bg=C_BG)
        set_icon(d)
        Label(d, text='\U0001f4e6  Add New Product', bg=C_BG, fg=C_ACCENT,
              font=(FONT_UI, 13, 'bold')).pack(pady=14)

        canvas = Canvas(d, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(d, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y', pady=(0, 12), padx=(0, 8))
        canvas.pack(side='left', fill='both', expand=True, padx=(12, 0), pady=(0, 12))

        frm = Frame(canvas, bg=C_BG)
        canvas.create_window((0, 0), window=frm, anchor='nw')

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        frm.bind('<Configure>', _on_frame_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', _on_mousewheel)
        canvas.bind('<Enter>', lambda e: canvas.focus_set())

        gst_var = StringVar(value='18.0')
        hsn_var = StringVar()
        cat_code_var = StringVar()
        fields = [
            ('Product Name *', StringVar()), ('Barcode / SKU', StringVar()),
            ('Category', StringVar(value='Grocery')), ('Category Code', cat_code_var), ('Unit', StringVar(value='pcs')),
            ('Purchase Price', StringVar(value='0.00')), ('Selling Price *', StringVar(value='0.00')),
            ('Stock Qty', StringVar(value='0')), ('Min Stock Alert', StringVar(value='10')),
            ('GST Rate (%)', gst_var), ('HSN Code', hsn_var),
        ]
        # Build fields; category field will have a Manage button
        category_combo = None
        def load_category_options():
            return get_product_categories()

        for lbl, var in fields:
            Label(frm, text=lbl, bg=C_BG, fg='#94a3b8',
                  font=(FONT_UI, 9)).pack(anchor='w', pady=(6, 2))
            if lbl.startswith('Category') and not lbl.startswith('Category Code'):
                cat_frame = Frame(frm, bg=C_BG)
                cat_frame.pack(fill='x')
                category_combo = ttk.Combobox(cat_frame, textvariable=var,
                                              values=load_category_options(),
                                              state='normal', postcommand=lambda: category_combo.configure(values=load_category_options()))
                category_combo.pack(side='left', fill='x', expand=True, ipady=5)

                def on_category_changed(event=None):
                    category_value = category_combo.get().strip()
                    if category_value:
                        # Auto-populate GST rate
                        gst_var.set(f"{get_gst_rate_for_category(category_value):.2f}")
                        
                        # Auto-populate HSN code from category mapping
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute("SELECT hsn_code FROM category_hsn_mapping WHERE category=?", (category_value,))
                            result = c.fetchone()
                            conn.close()
                            if result and result[0]:
                                hsn_var.set(result[0])
                            else:
                                hsn_var.set('')
                        except Exception:
                            hsn_var.set('')

                category_combo.bind('<<ComboboxSelected>>', on_category_changed)
                category_combo.bind('<FocusOut>', on_category_changed)

                def manage_categories():
                    m = Toplevel(d)
                    m.title('Manage Categories')
                    m.geometry('360x360')
                    set_icon(m)
                    Label(m, text='Product Categories', bg=C_BG, fg=C_ACCENT, font=(FONT_UI, 12, 'bold')).pack(pady=8)
                    lb = Listbox(m)
                    lb.pack(fill='both', expand=True, padx=12, pady=8)
                    def load_cats():
                        lb.delete(0, 'end')
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cur = conn.cursor()
                            cur.execute("CREATE TABLE IF NOT EXISTS product_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
                            conn.commit()
                            cur.execute('SELECT name FROM product_categories ORDER BY name')
                            for r in cur.fetchall():
                                if r and r[0]:
                                    lb.insert('end', r[0])
                            conn.close()
                        except Exception:
                            pass
                    load_cats()
                    add_var = StringVar()
                    Entry(m, textvariable=add_var).pack(fill='x', padx=12)
                    def add_cat():
                        v = add_var.get().strip()
                        if not v:
                            return
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cur = conn.cursor()
                            cur.execute('INSERT OR IGNORE INTO product_categories (name) VALUES (?)', (v,))
                            conn.commit()
                            conn.close()
                            load_cats(); add_var.set('')
                            if category_combo:
                                category_combo.configure(values=load_category_options())
                        except Exception as e:
                            messagebox.showerror('Error', str(e), parent=m)
                    Button(m, text='Add Category', command=add_cat, bg=C_ACCENT, fg='white').pack(pady=8)
                Button(cat_frame, text='Manage', command=manage_categories, bg=C_SURFACE, fg=C_TEXT, padx=8).pack(side='right', padx=(8,0))
            else:
                Entry(frm, textvariable=var, bg=C_SURFACE, fg=C_TEXT,
                      insertbackground=C_TEXT, relief='flat',
                      highlightthickness=1, highlightbackground=C_BORDER,
                      highlightcolor=C_ACCENT).pack(fill='x', ipady=5)

        def save():
            try:
                hsn_code = hsn_var.get().strip()
                category = fields[2][1].get().strip()
                
                # If HSN code is not provided, try to get it from category mapping
                if not hsn_code and category:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT hsn_code FROM category_hsn_mapping WHERE category=?", (category,))
                    result = c.fetchone()
                    conn.close()
                    if result:
                        hsn_code = result[0]
                
                conn = sqlite3.connect(DB_PATH)
                conn.execute("""
                    INSERT INTO products (name,barcode,category,category_code,unit,purchase_price,
                    selling_price,stock,min_stock,gst_rate,hsn_code)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (fields[0][1].get(), fields[1][1].get(), category, cat_code_var.get(),
                      fields[4][1].get(), fields[5][1].get(), fields[6][1].get(), fields[7][1].get(),
                      fields[8][1].get(), gst_var.get(), hsn_code))
                conn.commit(); conn.close()
                refresh(); d.destroy()
                messagebox.showinfo(HYPE_ERP_NAME, 'Product added!')
                # Immediate sync: products and categories
                try:
                    import firebase_sync
                    fsm = getattr(firebase_sync, 'firebase_sync_manager', None)
                    if fsm and getattr(fsm, 'db', None):
                        try:
                            store_id = int(get_setting('store_id', '1'))
                        except Exception:
                            store_id = 1
                        try:
                            fsm.sync_table_to_firestore('products', f'stores/{store_id}/products')
                            fsm.sync_table_to_firestore('product_categories', f'stores/{store_id}/product_categories')
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror('Error', str(e))

        Button(d, text='\U0001f4be  Save Product', bg=C_ACCENT, fg='white',
               command=save, relief='flat', padx=18, pady=9,
               font=(FONT_UI, 10, 'bold')).pack(pady=14)

    for txt, cmd, col in [
        ('+ Add Product', add_product_dialog, C_ACCENT),
        ('\U0001f4b2 Adjust Price', adjust_price_dialog, C_BLUE),
        ('\U0001f4e6 Restock', restock_dialog, C_GREEN),
        ('\U0001f5d1 Delete', delete_product, '#e74c3c'),
        ('\U0001f504 Refresh', refresh, C_SURFACE),
    ]:
        Button(toolbar, text=txt, bg=col, fg=C_TEXT, command=cmd,
               relief='flat', padx=12, pady=5,
               font=(FONT_UI, 9, 'bold')).pack(side='left', padx=4)

    refresh()
    _win_footer(win)

def view_sales_report():
    win = _win_base(f'{HYPE_ERP_NAME} — Sales Report', 1050, 620)
    _win_header(win, '\U0001f4c9', 'Sales Report')
    cols = ('Invoice', 'Date', 'Customer', 'Subtotal', 'GST', 'Total', 'Payment', 'Status')
    frame = Frame(win, bg=C_BG)
    frame.pack(fill='both', expand=True, padx=12, pady=8)
    tree = ttk.Treeview(frame, columns=cols, show='headings',
                        height=20, style='Dark.Treeview')
    for col, w in zip(cols, [140, 100, 160, 90, 80, 100, 90, 80]):
        tree.heading(col, text=col)
        tree.column(col, width=w)
    sb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=sb.set)
    tree.pack(side='left', fill='both', expand=True)
    sb.pack(side='right', fill='y')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT invoice_number,date,customer_name,subtotal,gst_amount,total_amount,payment_method,payment_status FROM invoices ORDER BY date DESC')
        for row in c.fetchall(): tree.insert('', 'end', values=row)
    except Exception: pass
    conn.close()
    _win_footer(win)

def view_customer_history():
    win = _win_base(f'{HYPE_ERP_NAME} — Customers', 950, 580)
    _win_header(win, '\U0001f9d1', 'Customer History')
    cols = ('ID', 'Name', 'Phone', 'Email', 'GSTIN', 'Total Purchases', 'Visits')
    frame = Frame(win, bg=C_BG)
    frame.pack(fill='both', expand=True, padx=12, pady=8)
    tree = ttk.Treeview(frame, columns=cols, show='headings',
                        height=18, style='Dark.Treeview')
    for col, w in zip(cols, [50, 180, 110, 160, 130, 120, 60]):
        tree.heading(col, text=col)
        tree.column(col, width=w)
    sb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=sb.set)
    tree.pack(side='left', fill='both', expand=True)
    sb.pack(side='right', fill='y')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT id,name,phone,email,gstin,total_purchases,visit_count FROM customers ORDER BY total_purchases DESC')
        for row in c.fetchall(): tree.insert('', 'end', values=row)
    except Exception: pass
    conn.close()
    _win_footer(win)

def manage_gst_config_window():
    win = _win_base(f'{HYPE_ERP_NAME} — GST Config', 700, 520)
    _win_header(win, '\U0001f4cb', 'GST Rate Configuration')
    rates = load_gst_rates()
    cols = ('Category', 'SGST %', 'CGST %', 'IGST %')
    frame = Frame(win, bg=C_BG)
    frame.pack(fill='both', expand=True, padx=12, pady=8)
    tree = ttk.Treeview(frame, columns=cols, show='headings',
                        height=18, style='Dark.Treeview')
    for col, w in zip(cols, [260, 140, 140, 140]):
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor='center' if col != 'Category' else 'w')
    vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=vsb.set)
    tree.pack(side='left', fill='both', expand=True)
    vsb.pack(side='right', fill='y')

    def refresh_rates():
        tree.delete(*tree.get_children())
        for cat, r in sorted(rates.items()):
            tree.insert('', 'end', values=(cat, r.get('SGST', 0), r.get('CGST', 0), r.get('IGST', 0)))

    def open_rate_dialog(existing=None):
        d = Toplevel(win)
        d.title('Edit GST Rate' if existing else 'Add GST Rate')
        d.geometry('420x320')
        d.configure(bg=C_BG)
        set_icon(d)

        title = 'Edit GST Rate' if existing else 'Add GST Rate'
        Label(d, text=title, bg=C_BG, fg=C_ACCENT,
              font=(FONT_UI, 12, 'bold')).pack(pady=14)

        cat_var = StringVar(value=existing[0] if existing else '')
        sgst_var = StringVar(value=str(existing[1]) if existing else '0')
        cgst_var = StringVar(value=str(existing[2]) if existing else '0')
        igst_var = StringVar(value=str(existing[3]) if existing else '0')

        form = Frame(d, bg=C_BG)
        form.pack(padx=24, pady=4, fill='both', expand=True)

        for label, var in [
            ('Category', cat_var), ('SGST %', sgst_var),
            ('CGST %', cgst_var), ('IGST %', igst_var)
        ]:
            Label(form, text=label, bg=C_BG, fg='#94a3b8',
                  font=(FONT_UI, 9)).pack(anchor='w', pady=(8, 0))
            Entry(form, textvariable=var, bg=C_SURFACE, fg=C_TEXT,
                  insertbackground=C_TEXT, relief='flat',
                  highlightthickness=1, highlightbackground=C_BORDER,
                  width=32).pack(ipady=6)

        def save_rate():
            category = cat_var.get().strip()
            if not category:
                messagebox.showwarning('Input', 'Category is required.', parent=d)
                return
            try:
                sgst = float(sgst_var.get() or 0)
                cgst = float(cgst_var.get() or 0)
                igst = float(igst_var.get() or 0)
            except ValueError:
                messagebox.showwarning('Input', 'Enter valid numeric GST values.', parent=d)
                return
            if existing and existing[0] != category and category in rates:
                messagebox.showwarning('Input', 'Category already exists.', parent=d)
                return
            if existing and existing[0] != category:
                rates.pop(existing[0], None)
            rates[category] = {'SGST': sgst, 'CGST': cgst, 'IGST': igst}
            save_gst_rates(rates)
            refresh_rates()
            d.destroy()

        Button(d, text='💾 Save', bg=C_ACCENT, fg=C_TEXT,
               command=save_rate, relief='flat', padx=18, pady=8,
               font=(FONT_UI, 10, 'bold')).pack(pady=16)

    def add_rate():
        open_rate_dialog()

    def edit_rate():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a rate to edit.', parent=win)
            return
        open_rate_dialog(tuple(tree.item(sel[0])['values']))

    def delete_rate():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a rate to delete.', parent=win)
            return
        category = tree.item(sel[0])['values'][0]
        if not messagebox.askyesno('Confirm', f'Delete GST rate for {category}?', parent=win):
            return
        rates.pop(category, None)
        save_gst_rates(rates)
        refresh_rates()

    refresh_rates()
    btn_frame = Frame(win, bg=C_BG)
    btn_frame.pack(fill='x', padx=12, pady=(0, 8))
    for text, cmd, color in [
        ('+ Add Rate', add_rate, C_ACCENT),
        ('✏ Edit Rate', edit_rate, C_BLUE),
        ('🗑 Delete Rate', delete_rate, '#e74c3c'),
    ]:
        Button(btn_frame, text=text, bg=color, fg=C_TEXT,
               command=cmd, relief='flat', padx=12, pady=7,
               font=(FONT_UI, 9, 'bold')).pack(side='left', padx=4)
    _win_footer(win)

def manage_hsn_config_window():
    """Open HSN Code Configuration Window"""
    if HAS_HSN_CONFIG and HSNConfigModule:
        hsn_module = HSNConfigModule(root, DB_PATH)
        hsn_module.open()
    else:
        messagebox.showerror(HYPE_ERP_NAME, 'HSN Configuration module not found.\nPlease ensure modules/hsn_config.py exists.')

def manage_settings_window():
    win = _win_base(f'{HYPE_ERP_NAME} — Settings', 580, 500)
    _win_header(win, '\u2699\ufe0f', 'Settings')
    keys = [
        ('shop_name', 'Shop Name'), ('owner_name', 'Owner Name'),
        ('shop_address', 'Address'), ('shop_phone', 'Phone'),
        ('shop_gstin', 'GSTIN'), ('invoice_prefix', 'Invoice Prefix'),
        ('state_code', 'State Code'),
    ]
    vars_ = {}
    frm = Frame(win, bg=C_BG)
    frm.pack(padx=36, pady=16, fill='both', expand=True)
    for i, (key, lbl) in enumerate(keys):
        Label(frm, text=lbl, bg=C_BG, fg='#94a3b8',
              font=(FONT_UI, 9), width=18, anchor='e').grid(row=i, column=0, pady=8, padx=(0, 10))
        var = StringVar(value=get_setting(key, ''))
        Entry(frm, textvariable=var, bg=C_SURFACE, fg=C_TEXT,
              insertbackground=C_TEXT, relief='flat',
              highlightthickness=1, highlightbackground=C_BORDER,
              highlightcolor=C_ACCENT, width=34).grid(row=i, column=1, pady=8, ipady=6)
        vars_[key] = var

    # Auto-restore on login toggle
    auto_restore_var = BooleanVar(value=(get_setting('auto_restore_on_login', 'false') == 'true'))
    Label(frm, text='Auto-Restore on Login', bg=C_BG, fg='#94a3b8',
          font=(FONT_UI, 9), width=18, anchor='e').grid(row=len(keys), column=0, pady=8, padx=(0, 10))
    Checkbutton(frm, variable=auto_restore_var, bg=C_BG).grid(row=len(keys), column=1, sticky='w')

    def restore_preview():
        try:
            import firebase_sync
            fsm = getattr(firebase_sync, 'firebase_sync_manager', None)
            if not (fsm and getattr(fsm, 'db', None)):
                messagebox.showwarning(HYPE_ERP_NAME, 'Firebase not initialized or not connected.')
                return
            try:
                store_id = int(get_setting('store_id', '1'))
            except Exception:
                store_id = 1
            cols = ['products', 'employees', 'payroll', 'payslips', 'invoices', 'customers', 'users']
            parts = []
            for col in cols:
                try:
                    if col in ('users',):
                        doc = fsm.db.collection('system').document(col).get()
                        if doc.exists:
                            d = doc.to_dict()
                            parts.append(f"{col}: {len(d) if isinstance(d, dict) else '1'}")
                        else:
                            parts.append(f"{col}: 0")
                    else:
                        doc = fsm.db.collection('stores').document(str(store_id)).collection(col).document('backup').get()
                        if doc.exists:
                            d = doc.to_dict()
                            key = 'products' if col == 'products' else col
                            ln = 0
                            for k in d:
                                if isinstance(d[k], list):
                                    ln = len(d[k]); break
                            parts.append(f"{col}: {ln}")
                        else:
                            parts.append(f"{col}: 0")
                except Exception:
                    parts.append(f"{col}: ?")
            messagebox.showinfo(HYPE_ERP_NAME, '\n'.join(parts), parent=win)
        except Exception as e:
            messagebox.showerror(HYPE_ERP_NAME, str(e), parent=win)

    Button(frm, text='Restore Preview', command=restore_preview, bg=C_SURFACE, fg=C_TEXT).grid(row=len(keys)+1, column=1, sticky='w', pady=(6,0))

    def save():
        for k, v in vars_.items(): set_setting(k, v.get())
        # Persist auto-restore setting
        set_setting('auto_restore_on_login', 'true' if auto_restore_var.get() else 'false')
        messagebox.showinfo(HYPE_ERP_NAME, '\u2705 Settings saved!')

    Button(win, text='\U0001f4be  Save Settings', bg=C_ACCENT, fg='white',
           command=save, relief='flat', padx=18, pady=9,
           font=(FONT_UI, 10, 'bold')).pack(pady=12)
    _win_footer(win)

def manage_users_window():
    win = _win_base(f'{HYPE_ERP_NAME} — Users', 780, 480)
    _win_header(win, '\U0001f465', 'User Management')
    cols = ('ID', 'Username', 'Role', 'Full Name', 'Email', 'Created')
    frame = Frame(win, bg=C_BG)
    frame.pack(fill='both', expand=True, padx=12, pady=6)
    tree = ttk.Treeview(frame, columns=cols, show='headings',
                        height=14, style='Dark.Treeview')
    for col, w in zip(cols, [40, 130, 90, 160, 180, 130]):
        tree.heading(col, text=col)
        tree.column(col, width=w)
    sb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=sb.set)
    tree.pack(side='left', fill='both', expand=True)
    sb.pack(side='right', fill='y')

    def refresh():
        for i in tree.get_children(): tree.delete(i)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id,username,role,full_name,email,created_at FROM users ORDER BY id')
        for row in c.fetchall(): tree.insert('', 'end', values=row)
        conn.close()

    def change_password_dialog():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a user first.', parent=win); return
        uid, uname = tree.item(sel[0])['values'][0], tree.item(sel[0])['values'][1]
        d = Toplevel(win)
        d.title(f'Change Password — {uname}')
        d.geometry('360x240')
        d.configure(bg=C_BG)
        set_icon(d)
        Label(d, text=f'Change Password: {uname}', bg=C_BG, fg=C_ACCENT,
              font=(FONT_UI, 11, 'bold')).pack(pady=14)
        p1, p2 = StringVar(), StringVar()
        for lbl, var in [('New Password', p1), ('Confirm Password', p2)]:
            Label(d, text=lbl, bg=C_BG, fg='#94a3b8', font=(FONT_UI, 9)).pack(anchor='w', padx=24)
            Entry(d, textvariable=var, show='\u2022', bg=C_SURFACE, fg=C_TEXT,
                  insertbackground=C_TEXT, relief='flat',
                  highlightthickness=1, highlightbackground=C_BORDER).pack(fill='x', padx=24, ipady=6, pady=(0, 8))

        def apply():
            if not p1.get():
                messagebox.showwarning('Input', 'Password cannot be empty.', parent=d); return
            if p1.get() != p2.get():
                messagebox.showwarning('Mismatch', 'Passwords do not match.', parent=d); return
            conn = sqlite3.connect(DB_PATH)
            conn.execute('UPDATE users SET password=? WHERE id=?', (_hash_password(p1.get()), uid))
            conn.commit(); conn.close()
            d.destroy()
            messagebox.showinfo(HYPE_ERP_NAME, f'Password updated for {uname}!')

        Button(d, text='\u2714 Apply', bg=C_ACCENT, fg='white',
               command=apply, relief='flat', padx=16, pady=7,
               font=(FONT_UI, 10, 'bold')).pack(pady=8)

    def add_user_dialog():
        d = Toplevel(win)
        d.title('Add User')
        d.geometry('400x380')
        d.configure(bg=C_BG)
        set_icon(d)
        Label(d, text='\U0001f464  Add New User', bg=C_BG, fg=C_ACCENT,
              font=(FONT_UI, 12, 'bold')).pack(pady=14)
        fields = [('Username', StringVar()), ('Password', StringVar()),
                  ('Full Name', StringVar()), ('Email', StringVar())]
        role_var = StringVar(value='cashier')
        frm = Frame(d, bg=C_BG)
        frm.pack(fill='both', expand=True, padx=28)
        for lbl, var in fields:
            Label(frm, text=lbl, bg=C_BG, fg='#94a3b8', font=(FONT_UI, 9)).pack(anchor='w', pady=(6, 2))
            e = Entry(frm, textvariable=var, bg=C_SURFACE, fg=C_TEXT,
                      insertbackground=C_TEXT, relief='flat',
                      highlightthickness=1, highlightbackground=C_BORDER)
            if lbl == 'Password': e.config(show='\u2022')
            e.pack(fill='x', ipady=5)
        Label(frm, text='Role', bg=C_BG, fg='#94a3b8', font=(FONT_UI, 9)).pack(anchor='w', pady=(6, 2))
        ttk.Combobox(frm, textvariable=role_var,
                     values=['admin', 'manager', 'cashier'],
                     state='readonly').pack(fill='x')

        def save():
            uname = fields[0][1].get().strip()
            plain = fields[1][1].get()
            if not uname or not plain:
                messagebox.showwarning('Input', 'Username and Password required.', parent=d); return
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute('INSERT INTO users (username,password,role,full_name,email) VALUES (?,?,?,?,?)',
                             (uname, _hash_password(plain), role_var.get(),
                              fields[2][1].get(), fields[3][1].get()))
                conn.commit(); conn.close()
                refresh(); d.destroy()
                messagebox.showinfo(HYPE_ERP_NAME, f'User "{uname}" created!')
                # Immediate sync of users to Firebase to reduce data-loss window
                try:
                    import firebase_sync
                    fsm = getattr(firebase_sync, 'firebase_sync_manager', None)
                    if fsm and getattr(fsm, 'db', None):
                        try:
                            fsm.sync_table_to_firestore('users', 'system/users')
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror('Error', str(e))

        Button(d, text='\U0001f4be  Save User', bg=C_ACCENT, fg='white',
               command=save, relief='flat', padx=16, pady=8,
               font=(FONT_UI, 10, 'bold')).pack(pady=12)

    def delete_user():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a user first.', parent=win)
            return
        uid, uname = tree.item(sel[0])['values'][0], tree.item(sel[0])['values'][1]
        if not messagebox.askyesno('Confirm', f'Delete user "{uname}"?', parent=win):
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('DELETE FROM users WHERE id=?', (uid,))
            conn.commit(); conn.close()
            refresh()
            messagebox.showinfo(HYPE_ERP_NAME, f'User "{uname}" deleted!')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    refresh()
    bf = Frame(win, bg=C_BG)
    bf.pack(pady=8)
    for txt, cmd, col in [
        ('+ Add User', add_user_dialog, C_ACCENT),
        ('\U0001f511 Change Password', change_password_dialog, C_BLUE),
        ('🗑 Delete User', delete_user, '#e74c3c'),
        ('\U0001f504 Refresh', refresh, C_SURFACE),
    ]:
        Button(bf, text=txt, bg=col, fg=C_TEXT, command=cmd,
               relief='flat', padx=12, pady=5,
               font=(FONT_UI, 9, 'bold')).pack(side='left', padx=4)
    _win_footer(win)

def manage_my_account_window():
    win = _win_base(f'{HYPE_ERP_NAME} — My Account', 420, 320)
    _win_header(win, '\U0001f464', 'My Account')
    Label(win, text=f'Username: {CURRENT_USER}', bg=C_BG, fg=C_TEXT,
          font=(FONT_UI, 11)).pack(pady=(20, 4))
    Label(win, text=f'Role: {CURRENT_ROLE}', bg=C_BG, fg='#94a3b8',
          font=(FONT_UI, 10)).pack()
    Frame(win, bg=C_BORDER, height=1).pack(fill='x', padx=30, pady=18)
    p1, p2 = StringVar(), StringVar()
    frm = Frame(win, bg=C_BG)
    frm.pack(padx=30)
    for lbl, var in [('New Password', p1), ('Confirm', p2)]:
        Label(frm, text=lbl, bg=C_BG, fg='#94a3b8', font=(FONT_UI, 9),
              width=14, anchor='e').grid(row=len(vars(frm).get('_r', [])), column=0, pady=6, padx=(0, 8))
        Entry(frm, textvariable=var, show='\u2022', bg=C_SURFACE, fg=C_TEXT,
              insertbackground=C_TEXT, relief='flat',
              highlightthickness=1, highlightbackground=C_BORDER, width=22
              ).grid(row=list({'p1':0,'p2':1}[x] for x in ['p1' if var is p1 else 'p2'])[0],
                     column=1, pady=6, ipady=5)

    frm2 = Frame(win, bg=C_BG); frm2.pack(padx=30, fill='x')
    Label(frm2, text='New Password', bg=C_BG, fg='#94a3b8',
          font=(FONT_UI, 9), width=14, anchor='e').grid(row=0, column=0, pady=6, padx=(0,8))
    Entry(frm2, textvariable=p1, show='\u2022', bg=C_SURFACE, fg=C_TEXT,
          insertbackground=C_TEXT, relief='flat',
          highlightthickness=1, highlightbackground=C_BORDER, width=22
          ).grid(row=0, column=1, pady=6, ipady=5)
    Label(frm2, text='Confirm', bg=C_BG, fg='#94a3b8',
          font=(FONT_UI, 9), width=14, anchor='e').grid(row=1, column=0, pady=6, padx=(0,8))
    Entry(frm2, textvariable=p2, show='\u2022', bg=C_SURFACE, fg=C_TEXT,
          insertbackground=C_TEXT, relief='flat',
          highlightthickness=1, highlightbackground=C_BORDER, width=22
          ).grid(row=1, column=1, pady=6, ipady=5)

    def change_pwd():
        if not p1.get():
            messagebox.showwarning('Input', 'Enter a new password.', parent=win); return
        if p1.get() != p2.get():
            messagebox.showwarning('Mismatch', 'Passwords do not match.', parent=win); return
        conn = sqlite3.connect(DB_PATH)
        conn.execute('UPDATE users SET password=? WHERE username=?',
                     (_hash_password(p1.get()), CURRENT_USER))
        conn.commit(); conn.close()
        messagebox.showinfo(HYPE_ERP_NAME, '\u2705 Password changed!')
        p1.set(''); p2.set('')

    Button(win, text='\U0001f511  Change Password', bg=C_BLUE, fg='white',
           command=change_pwd, relief='flat', padx=16, pady=8,
           font=(FONT_UI, 10, 'bold')).pack(pady=12)
    _win_footer(win)

def manage_stock_window():
    if HAS_ERP_MODULES:
        try:
            from modules.inventory_analysis import InventoryAnalysisModule
            InventoryAnalysisModule(root, DB_PATH).open(); return
        except Exception: pass
    open_products_window()

def view_ledger_report():
    if HAS_TALLY and TallyWindow:
        TallyWindow(root)
    elif HAS_ERP_MODULES:
        try:
            from modules.account import AccountingModule
            AccountingModule(root, DB_PATH).open(); return
        except Exception: pass
    else:
        messagebox.showinfo(HYPE_ERP_NAME, 'Tally / Accounting module not found.')

def view_trial_balance():
    view_ledger_report()

def open_about():
    if HAS_ABOUT:
        _show_about_fn(root); return
    msg = (f'{HYPE_ERP_NAME} {HYPE_ERP_VERSION}\n'
           f'{HYPE_ERP_TAGLINE}\n\n'
           f'Developer: David\nGitHub: https://github.com/david0154\n\n'
           f'Modules: Billing, Inventory, HR, Payroll, CRM,\n'
           f'POS, Projects, Accounting, AI, Cloud\n\n'
           f'{HYPE_ERP_FOOTER}')
    messagebox.showinfo(f'About {HYPE_ERP_NAME}', msg)

# ───────────────────────────────────────────────────────────────────────────────
# MAIN DASHBOARD
# ───────────────────────────────────────────────────────────────────────────────
def launch_main_app():
    global root, FIREBASE_SYNC, APP_STARTED

    with WINDOW_CREATION_LOCK:
        if APP_STARTED and root is not None and root.winfo_exists():
            try:
                logger.info(f'Main app already started, user={CURRENT_USER}, role={CURRENT_ROLE}')
                root.deiconify()
                root.focus_force()
            except Exception as e:
                logger.error(f'Error bringing main app to foreground: {e}')
            return

        logger.info(f'Launching main app for user={CURRENT_USER}, role={CURRENT_ROLE}')
        
        # Validate manager role
        if CURRENT_ROLE == 'manager':
            logger.info(f'Manager login detected for user={CURRENT_USER}')
        elif CURRENT_ROLE == 'admin':
            logger.info(f'Admin login detected for user={CURRENT_USER}')
        elif CURRENT_ROLE == 'cashier':
            logger.info(f'Cashier login detected for user={CURRENT_USER}')
        else:
            logger.warning(f'Unknown role for user={CURRENT_USER}: {CURRENT_ROLE}')

        APP_STARTED = True
        root = Tk()
        root.title(f'{HYPE_ERP_NAME} {HYPE_ERP_VERSION}')
        root.geometry('1366x768')
        root.configure(bg=C_BG)
        root.state('zoomed') if sys.platform == 'win32' else None
        set_icon(root)
        
        # ✅ Ensure main window is visible and in foreground
        root.deiconify()
        root.lift()
        root.focus_force()
        
        apply_dark_style()

        # Show loading status
        loading_frame = Frame(root, bg=C_BG)
        loading_frame.pack(fill='both', expand=True)
        Label(loading_frame, text='Loading...', font=(FONT_UI, 20, 'bold'),
              bg=C_BG, fg=C_ACCENT).pack(expand=True)
        root.update()

        # Firebase init (only if configured)
        if FIREBASE_AVAILABLE and _firebase_configured():
            try:
                key_path = _get_login_firebase_credentials_path()
                if key_path and os.path.exists(key_path):
                    try:
                        store_id = int(get_setting('store_id', '1'))
                    except Exception:
                        store_id = 1
                    logger.info(f'Initializing Firebase sync with credentials path: {key_path}, store_id={store_id}')
                    FIREBASE_SYNC = initialize_firebase_sync(credentials_path=key_path, store_id=store_id)
                    logger.info(f'✅ Firebase sync initialized successfully')
                    
                    # ⚡ LOAD DATA FROM FIREBASE ⚡
                    try:
                        from firebase_upload_manager import get_upload_manager
                        upload_mgr = get_upload_manager(FIREBASE_SYNC)
                        
                        if upload_mgr and FIREBASE_SYNC:
                            # Load data synchronously to ensure it's available before UI renders
                            logger.info(f"📥 Loading data from Firebase for store_id={store_id}...")
                            try:
                                # Call load_all_data directly
                                result = upload_mgr.load_all_data(store_id, DB_PATH)
                                if result:
                                    logger.info("✅ Firebase data loaded successfully to local DB")
                                else:
                                    logger.warning("Load returned no data, but continuing...")
                            except Exception as load_error:
                                logger.warning(f"Could not load data synchronously: {load_error}, trying background sync...")
                                # Fall back to background
                                def _background_load():
                                    try:
                                        upload_mgr.load_all_data(store_id, DB_PATH)
                                        logger.info("✅ Background data load finished")
                                    except Exception as bg_error:
                                        logger.error(f"Error in background data load: {bg_error}")
                                
                                load_thread = threading.Thread(target=_background_load, daemon=True)
                                load_thread.start()
                        else:
                            logger.warning("Upload manager or Firebase sync not available")
                    except Exception as e:
                        logger.warning(f"Could not initialize Firebase upload manager: {e}")
                    
                else:
                    logger.warning('Firebase credentials were not available during app startup')
            except Exception as exc:
                logger.error(f'Firebase initialization failed during startup: {exc}')
        else:
            logger.info('Firebase not configured or not available')

    # Clear loading screen and build main UI
    for widget in root.winfo_children():
        widget.destroy()

    # ── TOP BAR ─────────────────────────────────────────────────────────────
    topbar = Frame(root, bg=C_HEADER, pady=0)
    topbar.pack(fill='x')
    # left logo
    logo_f = Frame(topbar, bg=C_HEADER)
    logo_f.pack(side='left', padx=16, pady=10)
    Label(logo_f, text='\U0001f3e2', font=(FONT_UI, 18), bg=C_HEADER, fg=C_ACCENT).pack(side='left')
    Label(logo_f, text=f'  {HYPE_ERP_NAME}', font=(FONT_UI, 17, 'bold'),
          bg=C_HEADER, fg=C_TEXT).pack(side='left')
    Label(logo_f, text=f'  {HYPE_ERP_TAGLINE}', font=(FONT_UI, 9),
          bg=C_HEADER, fg=C_MUTED).pack(side='left', padx=8)
    # right user info
    user_f = Frame(topbar, bg=C_HEADER)
    user_f.pack(side='right', padx=16, pady=10)
    Label(user_f, text=f'\U0001f464  {CURRENT_USER}', font=(FONT_UI, 10, 'bold'),
          bg=C_HEADER, fg=C_TEXT).pack(side='left')
    role_color = {'admin': C_ACCENT, 'manager': C_BLUE, 'cashier': C_GREEN}.get(CURRENT_ROLE, C_MUTED)
    Label(user_f, text=f'  [{CURRENT_ROLE.upper()}]', font=(FONT_UI, 8, 'bold'),
          bg=C_HEADER, fg=role_color).pack(side='left')
    # clock
    clock_lbl = Label(user_f, text='', font=(FONT_UI, 9),
                      bg=C_HEADER, fg=C_MUTED)
    clock_lbl.pack(side='left', padx=(16, 0))
    def _tick():
        clock_lbl.config(text=datetime.now().strftime('  %d %b %Y  %H:%M:%S'))
        root.after(1000, _tick)
    _tick()

    # ── STAT CARDS ────────────────────────────────────────────────────────────
    cards_outer = Frame(root, bg=C_BG)
    cards_outer.pack(fill='x', padx=20, pady=(14, 0))

    card_defs = [
        ('invoices', '\U0001f9fe', 'Total Invoices',  C_ACCENT),
        ('products', '\U0001f4e6', 'Products',         C_BLUE),
        ('low_stock','\u26a0\ufe0f',  'Low Stock Alert',  C_ORANGE),
        ('revenue',  '\U0001f4b0', 'Total Revenue',    C_GREEN),
        ('today',    '\U0001f4c5', "Today's Sales",    C_PURPLE),
    ]
    stat_val_labels = {}

    def _make_card(parent, key, icon, label, color, col):
        card = Frame(parent, bg=C_SURFACE,
                     highlightthickness=1, highlightbackground=C_BORDER)
        card.grid(row=0, column=col, sticky='ew', padx=6)
        # top accent bar
        Frame(card, bg=color, height=3).pack(fill='x')
        inner = Frame(card, bg=C_SURFACE, padx=14, pady=12)
        inner.pack(fill='both', expand=True)
        Label(inner, text=icon, font=(FONT_UI, 20), bg=C_SURFACE, fg=color).pack(anchor='w')
        vl = Label(inner, text='0', font=(FONT_UI, 22, 'bold'), bg=C_SURFACE, fg=C_TEXT)
        vl.pack(anchor='w')
        Label(inner, text=label, font=(FONT_UI, 8), bg=C_SURFACE, fg=C_MUTED).pack(anchor='w')
        stat_val_labels[key] = vl
        parent.columnconfigure(col, weight=1)

    for i, (key, icon, lbl, col) in enumerate(card_defs):
        _make_card(cards_outer, key, icon, lbl, col, i)

    def refresh_stats():
        s = get_dashboard_stats()
        for key, lbl in stat_val_labels.items():
            v = s.get(key, 0)
            text = f'{CURRENCY}{v:,.0f}' if key in ('revenue', 'today') else str(v)
            try: lbl.config(text=text)
            except Exception: pass

    refresh_stats()

    # ── QUICK ACTION BUTTONS ──────────────────────────────────────────────────
    qa_outer = Frame(root, bg=C_BG)
    qa_outer.pack(fill='x', padx=20, pady=12)

    # Build quick actions — Firebase only shown if serviceAccountKey exists
    quick_actions = [
        ('\U0001f9fe', 'New Invoice',    open_billing_window,    C_ACCENT),
        ('\U0001f4e6', 'Products',       open_products_window,   C_BLUE),
        ('\U0001f4c9', 'Sales Report',   view_sales_report,      C_GREEN),
        ('\U0001f9d1', 'Customers',      view_customer_history,  C_PURPLE),
        ('\U0001f3ed', 'ERP Modules',
         lambda: ERPMainMenu(root, DB_PATH).open() if HAS_ERP_MODULES
                 else messagebox.showinfo(HYPE_ERP_NAME, 'ERP modules not found.'),
         C_TEAL),
        ('\U0001f916', 'AI Assistant',
         lambda: AIAssistantWindow(root) if HAS_AI
                 else messagebox.showinfo(HYPE_ERP_NAME, 'AI module not available.'),
         C_ORANGE),
    ]
    # Firebase hidden from UI - works automatically in background
    # Only show About button
    quick_actions.append(('\u2139\ufe0f', 'About', open_about, '#475569'))

    def _qa_btn(parent, icon, label, cmd, color, col):
        f = Frame(parent, bg=C_SURFACE,
                  highlightthickness=1, highlightbackground=C_BORDER,
                  cursor='hand2')
        f.grid(row=0, column=col, sticky='ew', padx=5)
        inner = Frame(f, bg=C_SURFACE, padx=10, pady=10)
        inner.pack(fill='both', expand=True)
        Label(inner, text=icon, font=(FONT_UI, 16), bg=C_SURFACE, fg=color).pack()
        Label(inner, text=label, font=(FONT_UI, 9, 'bold'), bg=C_SURFACE, fg=C_TEXT).pack()
        for w in (f, inner) + tuple(inner.winfo_children() if inner.winfo_children() else []):
            try:
                w.bind('<Button-1>', lambda e, c=cmd: c())
                w.bind('<Enter>', lambda e, fr=f: fr.config(highlightbackground=color))
                w.bind('<Leave>', lambda e, fr=f: fr.config(highlightbackground=C_BORDER))
            except Exception:
                pass
        parent.columnconfigure(col, weight=1)

    for i, (icon, lbl, cmd, col) in enumerate(quick_actions):
        _qa_btn(qa_outer, icon, lbl, cmd, col, i)

    # Bind children after pack
    def _bind_qa_children():
        for child in qa_outer.winfo_children():
            for icon_lbl in child.winfo_children():
                for w in icon_lbl.winfo_children():
                    pass  # labels already bound via pack-time loop above
    root.after(100, _bind_qa_children)

    # ── MAIN CONTENT AREA ─────────────────────────────────────────────────────────
    content = Frame(root, bg=C_BG)
    content.pack(fill='both', expand=True, padx=20, pady=(0, 8))

    # Recent invoices table
    inv_frame = Frame(content, bg=C_SURFACE,
                      highlightthickness=1, highlightbackground=C_BORDER)
    inv_frame.pack(side='left', fill='both', expand=True, padx=(0, 8))

    inv_hdr = Frame(inv_frame, bg=C_SURFACE)
    inv_hdr.pack(fill='x', padx=12, pady=(10, 4))
    Label(inv_hdr, text='\U0001f4cb  Recent Invoices', font=(FONT_UI, 11, 'bold'),
          bg=C_SURFACE, fg=C_TEXT).pack(side='left')
    Button(inv_hdr, text='\U0001f504 Refresh', bg=C_BORDER, fg=C_MUTED,
           command=lambda: [refresh_stats(), refresh_recent()],
           relief='flat', font=(FONT_UI, 8), padx=8, pady=3).pack(side='right')
    Button(inv_hdr, text='+ New Invoice', bg=C_ACCENT, fg='white',
           command=open_billing_window,
           relief='flat', font=(FONT_UI, 8, 'bold'), padx=10, pady=3).pack(side='right', padx=6)

    cols = ('Invoice No', 'Date', 'Customer', 'Total', 'Payment', 'Status')
    inv_tree = ttk.Treeview(inv_frame, columns=cols, show='headings',
                             height=14, style='Dark.Treeview')
    for col, w in zip(cols, [140, 100, 180, 100, 100, 80]):
        inv_tree.heading(col, text=col)
        inv_tree.column(col, width=w)
    rsb = ttk.Scrollbar(inv_frame, orient='vertical', command=inv_tree.yview)
    inv_tree.configure(yscroll=rsb.set)
    inv_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=(0, 8))
    rsb.pack(side='right', fill='y', pady=(0, 8))

    def refresh_recent():
        for i in inv_tree.get_children(): inv_tree.delete(i)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute('SELECT invoice_number,date,customer_name,total_amount,payment_method,payment_status FROM invoices ORDER BY id DESC LIMIT 60')
            for row in c.fetchall():
                inv_tree.insert('', 'end', values=row)
        except Exception: pass
        conn.close()

    refresh_recent()

    # Right side panel — low stock + shortcuts
    right_panel = Frame(content, bg=C_BG, width=260)
    right_panel.pack(side='right', fill='y')
    right_panel.pack_propagate(False)

    # Low stock widget
    ls_frame = Frame(right_panel, bg=C_SURFACE,
                     highlightthickness=1, highlightbackground=C_BORDER)
    ls_frame.pack(fill='x', pady=(0, 8))
    Label(ls_frame, text='\u26a0\ufe0f  Low Stock Alerts', font=(FONT_UI, 10, 'bold'),
          bg=C_SURFACE, fg='#fbbf24').pack(anchor='w', padx=12, pady=(10, 4))
    ls_list = Listbox(ls_frame, bg=C_SURFACE, fg='#fbbf24',
                      selectbackground=C_BORDER, relief='flat',
                      font=(FONT_UI, 9), height=7, bd=0)
    ls_list.pack(fill='x', padx=12, pady=(0, 10))

    def refresh_low_stock():
        ls_list.delete(0, 'end')
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute('SELECT name, stock, min_stock FROM products WHERE stock < min_stock ORDER BY stock LIMIT 15')
            rows = c.fetchall()
            if not rows:
                ls_list.insert('end', '  \u2705 All stock levels OK')
                ls_list.config(fg='#4ade80')
            else:
                ls_list.config(fg='#fbbf24')
                for name, stk, mn in rows:
                    ls_list.insert('end', f'  {name[:22]} ({stk}/{mn})')
        except Exception: pass
        conn.close()

    refresh_low_stock()

    # Quick links
    ql_frame = Frame(right_panel, bg=C_SURFACE,
                     highlightthickness=1, highlightbackground=C_BORDER)
    ql_frame.pack(fill='x')
    Label(ql_frame, text='\U0001f517  Quick Links', font=(FONT_UI, 10, 'bold'),
          bg=C_SURFACE, fg=C_TEXT).pack(anchor='w', padx=12, pady=(10, 4))
    for lbl, cmd in [
        ('\U0001f4e6 Add Product',        open_products_window),
        ('\U0001f4c9 Sales Report',        view_sales_report),
        ('\U0001f9d1 Customer List',       view_customer_history),
        ('\U0001f4cb GST Rates',           manage_gst_config_window),
        ('\U0001f4b3 HSN Codes',          manage_hsn_config_window),
        ('\u2699\ufe0f  Settings',          manage_settings_window),
        ('\U0001f916 AI Assistant',        lambda: AIAssistantWindow(root) if HAS_AI else None),
    ]:
        btn = Button(ql_frame, text=lbl, bg=C_SURFACE, fg='#94a3b8',
                     command=cmd, relief='flat', anchor='w',
                     font=(FONT_UI, 9), padx=14, pady=5,
                     activebackground=C_BORDER, activeforeground=C_TEXT,
                     cursor='hand2')
        btn.pack(fill='x')
        btn.bind('<Enter>', lambda e, b=btn: b.config(fg=C_TEXT, bg=C_BORDER))
        btn.bind('<Leave>', lambda e, b=btn: b.config(fg='#94a3b8', bg=C_SURFACE))

    # ── STATUS BAR ─────────────────────────────────────────────────────────────
    status_bar = Frame(root, bg=C_HEADER, pady=3)
    status_bar.pack(side='bottom', fill='x')
    statusIndicator = Label(status_bar, text=f'\u25cf  {HYPE_ERP_NAME} Ready',
                            bg=C_HEADER, fg='#4ade80', font=(FONT_UI, 8))
    statusIndicator.pack(side='left', padx=14)
    fb_status = Label(status_bar,
                      text='\u2601\ufe0f Firebase: Connected' if (FIREBASE_AVAILABLE and _firebase_configured())
                           else '\u26d4 Firebase: Not configured',
                      bg=C_HEADER,
                      fg='#4ade80' if (FIREBASE_AVAILABLE and _firebase_configured()) else C_MUTED,
                      font=(FONT_UI, 8))
    fb_status.pack(side='left', padx=12)
    Label(status_bar, text=HYPE_ERP_FOOTER,
          bg=C_HEADER, fg='#1e2038', font=(FONT_UI, 7)).pack(side='right', padx=14)

    # ── MENU BAR ──────────────────────────────────────────────────────────────────
    menubar = Menu(root, bg=C_HEADER, fg=C_TEXT,
                   activebackground=C_ACCENT, activeforeground='white',
                   relief='flat', bd=0)

    def _menu(label):
        m = Menu(menubar, tearoff=0, bg=C_SURFACE, fg=C_TEXT,
                 activebackground=C_ACCENT, activeforeground='white',
                 relief='flat')
        menubar.add_cascade(label=label, menu=m)
        return m

    um = _menu('Users')
    if CURRENT_ROLE == 'admin':
        um.add_command(label='\U0001f465 Manage Users', command=manage_users_window)
    um.add_command(label='\U0001f464 My Account', command=manage_my_account_window)

    sm = _menu('Store')
    if CURRENT_ROLE == 'admin':
        sm.add_command(label='\U0001f3ea Store Settings', command=manage_settings_window)
    sm.add_command(label='\u2699\ufe0f General Settings', command=manage_settings_window)
    sm.add_separator()
    sm.add_command(label='\U0001f4e6 Products', command=open_products_window)
    sm.add_command(label='\U0001f4ca Stock Management', command=manage_stock_window)

    bm = _menu('Billing')
    bm.add_command(label='\U0001f9fe New Invoice', command=open_billing_window)
    bm.add_command(label='\U0001f4cb GST Configuration', command=manage_gst_config_window)
    bm.add_command(label='\U0001f4b3 HSN Code Configuration', command=manage_hsn_config_window)
    bm.add_separator()
    bm.add_command(label='\U0001f4c8 Sales Report', command=view_sales_report)
    bm.add_command(label='\U0001f9d1 Customer History', command=view_customer_history)

    em = _menu('ERP')
    em.add_command(label='\U0001f3e2 Open ERP Modules',
                   command=lambda: ERPMainMenu(root, DB_PATH).open() if HAS_ERP_MODULES
                   else messagebox.showinfo(HYPE_ERP_NAME, 'ERP modules not found.'))
    if HAS_ERP_MODULES:
        em.add_separator()
        for mod_lbl, mod_cls, mod_file in [
            ('\U0001f4e6 Inventory',     'InventoryAnalysisModule', 'modules.inventory_analysis'),
            ('\U0001f465 HR',            'HRModule',                'modules.hr_module'),
            ('\U0001f4b0 Payroll',       'PayrollModule',           'modules.payroll_module'),
            ('\U0001f91d CRM',           'CRMModule',               'modules.crm_module'),
            ('\U0001f4c1 Projects',      'ProjectsModule',          'modules.projects_module'),
            ('\U0001f6d2 POS',           'POSModule',               'modules.pos_module'),
            ('\U0001f4ca Reports',       'ReportingModule',         'modules.reporting_module'),
            ('\U0001f3e6 Accounting',    'AccountingModule',        'modules.account'),
        ]:
            em.add_command(
                label=mod_lbl,
                command=lambda mf=mod_file, mc=mod_cls: getattr(
                    __import__(mf, fromlist=[mc]), mc)(root, DB_PATH).open()
            )

    acm = _menu('Accounts')
    acm.add_command(label='\U0001f4d2 Hype Account Suite',
                    command=lambda: TallyWindow(root) if HAS_TALLY
                    else messagebox.showinfo(HYPE_ERP_NAME, 'Account Suite not loaded.'))
    acm.add_separator()
    acm.add_command(label='\U0001f4ca Ledger', command=view_ledger_report)
    acm.add_command(label='\u2696\ufe0f Trial Balance', command=view_trial_balance)

    aim = _menu('AI')
    aim.add_command(label='\U0001f916 AI Assistant',
                    command=lambda: AIAssistantWindow(root) if HAS_AI
                    else messagebox.showinfo(HYPE_ERP_NAME, 'AI not loaded.'))
    aim.add_separator()
    aim.add_command(label='\U0001f4c8 Sales Prediction', command=_show_ai_prediction)

    # Cloud menu — only show if Firebase configured
    if _firebase_configured():
        cm = _menu('Cloud')
        cm.add_command(label='\u2601\ufe0f Firebase Dashboard',
                       command=lambda: FirebaseDashboardWindow(root) if HAS_FIREBASE_DEEP
                       else messagebox.showinfo(HYPE_ERP_NAME, 'Firebase module not loaded.'))
        cm.add_separator()
        cm.add_command(label='\U0001f504 Sync Now', command=_trigger_full_sync)
        cm.add_command(label='\U0001f4be Backup', command=_trigger_backup)

    hm = _menu('Help')
    hm.add_command(label=f'\u2139\ufe0f About {HYPE_ERP_NAME}', command=open_about)
    hm.add_command(label='\u2b50 Star on GitHub',
                   command=lambda: webbrowser.open('https://github.com/david0154/hype-billing-system'))
    hm.add_separator()
    hm.add_command(label='\U0001f4e6 Install Dependencies',
                   command=lambda: (
                       run_auto_install(),
                       messagebox.showinfo(HYPE_ERP_NAME, 'Installing in background...')))

    root.config(menu=menubar)

    if HAS_AUTO_INSTALL:
        def _log(msg):
            try: statusIndicator.config(text=f'\u25cf  {msg[:50]}')
            except Exception: pass
        threading.Thread(target=lambda: run_auto_install(log_callback=_log), daemon=True).start()

    def on_close():
        logger.info(f'Application closing for user={CURRENT_USER}')
        try:
            if FIREBASE_AVAILABLE and FIREBASE_SYNC:
                logger.info('Shutting down Firebase sync')
                shutdown_firebase_sync(FIREBASE_SYNC)
        except Exception as e: 
            logger.error(f'Error shutting down Firebase: {e}')
        logger.info('=== Application Shutdown ===')
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', on_close)
    
    # ✅ Ensure all rendering is complete before mainloop
    root.update_idletasks()
    
    # ✅ Run app with error handling for windowed exe
    try:
        root.mainloop()
    except Exception as e:
        logger.critical(f'CRITICAL ERROR in main loop: {e}', exc_info=True)
        messagebox.showerror('Application Error', f'Critical Error:\n\n{str(e)}\n\nCheck logs at: %LOCALAPPDATA%\\HypeERP\\hype_erp.log')
        raise

# ── ENTRY POINT ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # ✅ CRITICAL: Add multiprocessing support for PyInstaller
    try:
        multiprocessing.freeze_support()
        logger.info('✅ multiprocessing.freeze_support() executed')
    except Exception as e:
        logger.warning(f'⚠️ freeze_support error: {e}')
    
    # ✅ Windows single-instance lock (prevent multiple app instances)
    if HAS_WIN32:
        try:
            APP_INSTANCE_LOCK = win32event.CreateMutex(None, False, 'HYPE_ERP_SINGLE_INSTANCE')
            last_error = win32api.GetLastError()
            if last_error == winerror.ERROR_ALREADY_EXISTS:
                logger.warning('Application already running - exiting')
                print('⚠️  Hype ERP is already running!')
                sys.exit(0)
            logger.info('✅ Single-instance mutex created successfully')
        except Exception as e:
            logger.warning(f'⚠️ Could not create instance lock: {e}')
    else:
        logger.info('ℹ️  pywin32 not available - single-instance lock disabled (Linux/Mac)')
    
    banner = f"""
+{'='*56}+
|  {HYPE_ERP_NAME} {HYPE_ERP_VERSION:<48}|
|  {HYPE_ERP_TAGLINE:<54}|
|  Developer: David | github.com/david0154 {'':<14}|
|  Default login : admin / admin123 {'':<20}|
+{'='*56}+
    """
    try:
        print(banner)
    except UnicodeEncodeError:
        print(banner.encode('ascii', errors='replace').decode('ascii'))
    
    logger.info('Initializing database')
    init_db()
    logger.info('Database initialized successfully')
    
    # Initialize background Firebase auto-sync if credentials are available.
    try:
        if _firebase_configured() and FIREBASE_AVAILABLE:
            logger.info('Firebase is configured, initializing background sync')
            # Prefer temporary decrypted key if present
            creds_temp = load_firebase_key_temp() or 'serviceAccountKey.json'
            try:
                store_id = int(get_setting('store_id', '1'))
            except Exception:
                store_id = 1
            logger.info(f'Starting Firebase background sync with store_id={store_id}')
            FIREBASE_SYNC = initialize_firebase_sync(credentials_path=creds_temp, store_id=store_id, interval_seconds=300)
            logger.info('Firebase background sync started')
        else:
            logger.info('Firebase not configured, skipping background sync')
    except Exception as e:
        logger.error(f'Failed to initialize Firebase background sync: {e}')
        FIREBASE_SYNC = None
    
    logger.info('Showing login window')
    show_login()