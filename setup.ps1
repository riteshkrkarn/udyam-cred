# UdyamCred Setup Script
# Fixes virtual environment activation issues

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║ UdyamCred - Setup Script              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Function to setup a folder
function Setup-Venv {
    param(
        [string]$folder,
        [string]$name
    )
    
    Write-Host "📁 Setting up $name..." -ForegroundColor Cyan
    
    if (-Not (Test-Path $folder)) {
        Write-Host "❌ Folder not found: $folder" -ForegroundColor Red
        return $false
    }
    
    Push-Location $folder
    
    # Check if venv exists
    if (-Not (Test-Path ".venv")) {
        Write-Host "  📦 Creating virtual environment..." -ForegroundColor Yellow
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to create venv" -ForegroundColor Red
            Pop-Location
            return $false
        }
    } else {
        Write-Host "  ✓ Virtual environment already exists" -ForegroundColor Green
    }
    
    # Activate using batch file (more reliable than PowerShell script)
    Write-Host "  🚀 Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\activate.bat
    
    # Install requirements
    if (Test-Path "requirements.txt") {
        Write-Host "  📚 Installing dependencies..." -ForegroundColor Yellow
        & python -m pip install -r requirements.txt --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Some dependencies may have failed" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ℹ️  No requirements.txt found (that's OK)" -ForegroundColor Gray
    }
    
    Pop-Location
    Write-Host "✅ $name setup complete!" -ForegroundColor Green
    Write-Host ""
    return $true
}

# Setup Backend
Setup-Venv "d:\vs code\udyam-cred\be" "Backend (FastAPI)"

# Setup ML
Setup-Venv "d:\vs code\udyam-cred\ml" "ML (scikit-learn, etc.)"

Write-Host "═══════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣  Backend:" -ForegroundColor Yellow
Write-Host "   cd d:\vs code\udyam-cred\be" -ForegroundColor Gray
Write-Host "   .venv\Scripts\activate.bat" -ForegroundColor Gray
Write-Host "   python scripts/seed.py --seed 42 --shops 10" -ForegroundColor Gray
Write-Host "   uvicorn main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "2️⃣  ML (optional):" -ForegroundColor Yellow
Write-Host "   cd d:\vs code\udyam-cred\ml" -ForegroundColor Gray
Write-Host "   .venv\Scripts\activate.bat" -ForegroundColor Gray
Write-Host "   python train_models.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3️⃣  Frontend:" -ForegroundColor Yellow
Write-Host "   cd d:\vs code\udyam-cred\fe" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
