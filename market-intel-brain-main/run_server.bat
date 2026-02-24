@echo off
echo Starting Production Server...
echo.

REM Set environment variables for production mode
set ENVIRONMENT=production
set REDIS_URL=redis://localhost:6379
set PYTHONPATH=/app
set LOG_LEVEL=INFO
set PORT=8000

REM Kill any existing processes on ports 8000-8003
echo Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :800') do (
    taskkill /PID %%a /F 2>nul
)

REM Start the server
echo Starting server on port 8000...
python production_server.py

pause
