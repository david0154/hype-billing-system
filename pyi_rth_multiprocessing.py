# PyInstaller runtime hook for multiprocessing support
# This hook ensures that multiprocessing and sklearn work correctly in frozen exe
import multiprocessing
import sys

# Enable freeze_support for multiprocessing before app startup
try:
    multiprocessing.freeze_support()
except Exception as e:
    # If freeze_support fails, app will still run but multiprocessing may not work correctly
    pass

# For Windows, ensure proper spawn method for child processes
if sys.platform == 'win32':
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except (RuntimeError, ValueError):
        # Method already set, ignore
        pass
