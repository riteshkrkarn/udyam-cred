@echo off
REM UdyamCred Setup Script (Batch version - no PowerShell issues!)

setlocal enabledelayedexpansion

echo.
echo ════════════════════════════════════════
echo  UdyamCred - Setup Script
echo ════════════════════════════════════════
echo.

REM Setup Backend
echo [1/2] Setting up Backend (FastAPI)...
cd /d "d:\vs code\udyam-cred\be"

if not exist ".venv" (
    echo  Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  ERROR: Failed to create venv
        goto error
    )
)

echo  Activating virtual environment...
call .venv\Scripts\activate.bat

echo  Installing dependencies...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo  WARNING: Some dependencies may have failed
) else (
    echo  Dependencies installed successfully
)

echo  [✓] Backend setup complete!
echo.

REM Setup ML
echo [2/2] Setting up ML folder...
cd /d "d:\vs code\udyam-cred\ml"

if not exist ".venv" (
    echo  Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  ERROR: Failed to create venv
        goto error
    )
)

echo  Activating virtual environment...
call .venv\Scripts\activate.bat

if exist "requirements.txt" (
    echo  Installing dependencies...
    python -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo  WARNING: Some dependencies may have failed
    ) else (
        echo  Dependencies installed successfully
    )
) else (
    echo  No requirements.txt found (that's OK)
)

echo  [✓] ML setup complete!
echo.

echo ════════════════════════════════════════
echo  ✓ Setup Complete!
echo ════════════════════════════════════════
echo.
echo Next steps:
echo.
echo [1] Backend:
echo     cd d:\vs code\udyam-cred\be
echo     .venv\Scripts\activate.bat
echo     python scripts/seed.py --seed 42 --shops 10
echo     uvicorn main:app --reload
echo.
echo [2] Frontend:
echo     cd d:\vs code\udyam-cred\fe
echo     npm run dev
echo.
echo [3] ML (optional):
echo     cd d:\vs code\udyam-cred\ml
echo     .venv\Scripts\activate.bat
echo     python train_models.py
echo.
pause

exit /b 0

:error
echo.
echo ✗ Setup failed!
echo.
echo Make sure you have Python installed:
echo   python --version
echo.
pause
exit /b 1
