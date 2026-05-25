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

# ── Branding ───────────────────────────────────────────────────────────────
HYPE_ERP_NAME    = 'Hype ERP'
HYPE_ERP_VERSION = 'v3.0.0'
HYPE_ERP_TAGLINE = 'Enterprise Resource Planning System'
HYPE_ERP_FOOTER  = f'Powered by {HYPE_ERP_NAME} | All rights reserved | {HYPE_ERP_VERSION}'

# ── Colours (design system) ───────────────────────────────────────────────
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
CURRENCY   = '₹'

# ── Optional Module Imports ──────────────────────────────────────────────
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

# ── State ─────────────────────────────────────────────────────────────────────────────
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
