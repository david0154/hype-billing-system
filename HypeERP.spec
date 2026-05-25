# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Only bundle firebase_runtime_config.json if it exists (it's created at runtime)
_base_datas = [('icon.ico', '.'), ('logo.png', '.'), ('modules', 'modules'), ('serviceAccountKey.enc', '.')]
if os.path.exists('firebase_runtime_config.json'):
    _base_datas.append(('firebase_runtime_config.json', '.'))

datas = _base_datas
binaries = []
hiddenimports = [
    'modules.account', 'modules.account_invoice', 'modules.account_asset',
    'modules.account_tax', 'modules.account_statement', 'modules.sale',
    'modules.purchase', 'modules.stock', 'modules.production',
    'modules.hr_module', 'modules.payroll_module', 'modules.crm_module',
    'modules.projects_module', 'modules.timesheet', 'modules.pos_module',
    'modules.stock_package', 'modules.quality_control', 'modules.marketing',
    'modules.reporting_module', 'modules.erp_main_menu', 'modules.mode_selector',
    'modules.scrollable_frame', 'modules.erp_branding', 'modules.inventory_analysis',
    'modules.vendor_module', 'modules.firebase_settings_ui', 'modules.window_utils',
    'modules.data_service', 'modules.hsn_config',
    # sklearn - use safe top-level imports only (avoid renamed internal modules)
    'sklearn', 'sklearn.utils', 'sklearn.neighbors', 'sklearn.tree',
    'sklearn.ensemble', 'sklearn.linear_model', 'sklearn.preprocessing',
    # firebase / google
    'firebase_admin', 'firebase_admin.credentials', 'firebase_admin.firestore',
    'firebase_admin.auth', 'firebase_admin.storage',
    'google.cloud', 'google.cloud.firestore', 'google.cloud.firestore_v1',
    'google.cloud.firestore_v1.base_client',
    'google.auth', 'google.auth.credentials', 'google.auth.transport',
    'google.auth.transport.requests',
    'google.oauth2', 'google.oauth2.credentials', 'google.oauth2.service_account',
    'grpc',
    # reportlab
    'reportlab', 'reportlab.pdfgen', 'reportlab.pdfgen.canvas',
    'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.styles',
    'reportlab.lib.units', 'reportlab.lib.colors',
    'reportlab.platypus', 'reportlab.platypus.tables',
    # image / crypto
    'PIL', 'PIL._tkinter_finder', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw',
    'cryptography', 'cryptography.fernet', 'cryptography.hazmat',
    'cryptography.hazmat.primitives', 'cryptography.hazmat.primitives.ciphers',
    # data
    'joblib', 'numpy', 'pandas',
    'pandas._libs', 'pandas._libs.tslibs',
    'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timedeltas', 'pandas._libs.skiplist',
    # stdlib
    'sqlite3', 'json', 'shutil', 'tempfile', 'multiprocessing',
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
    'tkinter.filedialog', 'tkinter.simpledialog', 'tkinter.scrolledtext',
    # windows
    'win32event', 'win32api', 'winerror',
]

tmp_ret = collect_all('firebase_admin')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('google.cloud.firestore')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('google.auth')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sklearn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_multiprocessing.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HypeERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)