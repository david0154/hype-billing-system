# ===========================================================================
# Hype ERP v3.0.0 - PyInstaller Build Script (PowerShell)
# Developer: David | Nexuzy Lab
# Run: .\build_pyinstaller.ps1
# ===========================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hype ERP v3.0.0 - PyInstaller Build" -ForegroundColor Cyan
Write-Host "  Developer: David | Nexuzy Lab" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Clean old build
Write-Host "[1/4] Cleaning old build files..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
# Note: Do NOT delete HypeERP.spec - we preserve it with all our fixes
Write-Host "      Done." -ForegroundColor Green

# Step 2: Encrypt Firebase key
Write-Host "[2/4] Encrypting serviceAccountKey.json..." -ForegroundColor Yellow
if (Test-Path "serviceAccountKey.json") {
    python encrypt_key.py
    Write-Host "      Encrypted -> serviceAccountKey.enc" -ForegroundColor Green
} else {
    Write-Host "      WARNING: serviceAccountKey.json not found - skipping encryption." -ForegroundColor Red
    Write-Host "      EXE will run without Firebase cloud sync." -ForegroundColor Red
}

# Step 3: PyInstaller build using spec file
Write-Host "[3/4] Running PyInstaller with HypeERP.spec..." -ForegroundColor Yellow
Write-Host ""

python -m PyInstaller HypeERP.spec --clean --noconfirm 2>&1

# Step 4: Result
Write-Host ""
if (Test-Path "dist\HypeERP.exe") {
    $size = [math]::Round((Get-Item "dist\HypeERP.exe").Length / 1MB, 1)
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "  Output: dist\HypeERP.exe ($size MB)" -ForegroundColor Green
    Write-Host "  Next: Run Inno Setup with hype_billing_installer.iss" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Debugging Tips:" -ForegroundColor Cyan
    Write-Host "  If exe crashes silently, check logs at:" -ForegroundColor Cyan
    Write-Host "  %LOCALAPPDATA%\\HypeERP\\hype_erp.log" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  BUILD FAILED - check errors above" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}
