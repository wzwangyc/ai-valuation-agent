@echo off
echo =======================================================
echo Bloomberg AI Valuation Agent - Deployment Script
echo =======================================================
echo.

echo [1/3] Installing Python Backend Dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install Python dependencies.
    pause
    exit /b %errorlevel%
)
echo.

echo [2/3] Installing and Building Frontend Dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo Failed to install Node dependencies.
    pause
    exit /b %errorlevel%
)

echo Building Frontend Assets...
node node_modules\vite\bin\vite.js build
if %errorlevel% neq 0 (
    echo Failed to build React application.
    pause
    exit /b %errorlevel%
)
cd ..
echo.

echo [3/3] Starting FastAPI Server...
echo The application will be available at http://localhost:8080
python -m uvicorn api:app --host 0.0.0.0 --port 8080

pause
