#!/usr/bin/env bash
# PyInstaller Build Script (for Linux, Mac, or Windows with WSL)
# Run: bash build_pyinstaller.sh

set -e

echo ""
echo "========================================"
echo "  Hype ERP v3.0.0 - PyInstaller Build"
echo "  Developer: David | Nexuzy Lab"
echo "========================================"
echo ""

# Step 1: Clean old build
echo "[1/3] Cleaning old build files..."
rm -rf dist build || true
echo "      Done."

# Step 2: Encrypt Firebase key if present
echo "[2/3] Preparing Firebase config..."
if [ -f "serviceAccountKey.json" ]; then
    python3 encrypt_key.py || true
    echo "      Encrypted -> serviceAccountKey.enc"
else
    echo "      WARNING: serviceAccountKey.json not found"
fi

# Step 3: PyInstaller build using spec file
echo "[3/3] Running PyInstaller with HypeERP.spec..."
echo ""

python3 -m PyInstaller HypeERP.spec --clean --noconfirm

echo ""
if [ -f "dist/HypeERP" ] || [ -f "dist/HypeERP.exe" ]; then
    BINARY="dist/HypeERP"
    [ -f "dist/HypeERP.exe" ] && BINARY="dist/HypeERP.exe"
    
    echo "========================================"
    echo "  BUILD SUCCESSFUL!"
    echo "  Output: $BINARY"
    echo "========================================"
    echo ""
    echo "📝 Debugging Tips:"
    echo "  If exe crashes, check logs at:"
    echo "  ~/.HypeERP/hype_erp.log or %LOCALAPPDATA%\HypeERP\hype_erp.log"
    echo ""
else
    echo "========================================"
    echo "  BUILD FAILED - check errors above"
    echo "========================================"
    exit 1
fi

