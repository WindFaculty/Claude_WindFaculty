# PowerShell Environment Bootstrap Script for Claude_WindFaculty

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Claude WindFaculty PowerShell Bootstrapper" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check Python installation
Write-Host "[1/5] Checking Python availability..." -ForegroundColor Yellow
try {
    $pythonVer = & python --version
    Write-Host "Found $pythonVer" -ForegroundColor Green
} catch {
    Write-Error "Python was not found in your environment PATH. Please install Python 3.8+."
    Exit 1
}

# 2. Check and establish Virtual Environment
Write-Host "[2/5] Establishing Python Virtual Environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "Creating new virtual environment in .venv..." -ForegroundColor Gray
    try {
        & python -m venv .venv
        Write-Host "Virtual environment established." -ForegroundColor Green
    } catch {
        Write-Error "Failed to establish Python virtual environment."
        Exit 1
    }
} else {
    Write-Host "Existing .venv directory detected." -ForegroundColor Green
}

# 3. Upgrade pip and install baseline dependencies
Write-Host "[3/5] Installing essential workspace dependencies..." -ForegroundColor Yellow
try {
    # Activate virtual environment locally in task session
    $venvPython = Join-Path (Get-Item ".").FullName ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        # Fallback for alternative venv structures
        $venvPython = Join-Path (Get-Item ".").FullName ".venv\bin\python.exe"
    }
    
    Write-Host "Upgrading pip..." -ForegroundColor Gray
    & $venvPython -m pip install --upgrade pip --quiet
    
    Write-Host "Installing pytest..." -ForegroundColor Gray
    & $venvPython -m pip install pytest --quiet

    Write-Host "Installing optional Semble code search (opt-in)..." -ForegroundColor Gray
    & $venvPython -m pip install "semble[mcp]" --quiet
    
    Write-Host "Dependencies successfully updated." -ForegroundColor Green
} catch {
    Write-Warning "Dependency installation returned issues. Continuing with system python."
    $venvPython = "python"
}

# 4. Generate local .env
Write-Host "[4/5] Syncing environment configurations..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "Generating .env from .env.example..." -ForegroundColor Gray
    Copy-Item ".env.example" ".env"
    Write-Host ".env file successfully created." -ForegroundColor Green
} else {
    Write-Host "Existing .env file detected." -ForegroundColor Green
}

# 5. Run verify script
Write-Host "[5/5] Executing environment validation suite..." -ForegroundColor Yellow
& $venvPython scripts/bootstrap/verify_environment.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "BOOTSTRAP SUCCESSFUL: Môi trường đã sẵn sàng!" -ForegroundColor Green
    Write-Host "Run tests using: .venv\Scripts\activate; pytest" -ForegroundColor Gray
    Write-Host "=========================================" -ForegroundColor Cyan
    Exit 0
} else {
    Write-Host "=========================================" -ForegroundColor Red
    Write-Error "BOOTSTRAP FAILED: Gặp lỗi khi verify môi trường!"
    Write-Host "=========================================" -ForegroundColor Red
    Exit 1
}
