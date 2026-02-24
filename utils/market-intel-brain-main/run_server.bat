@echo off
echo Starting Hybrid API Server...
echo.

REM Set environment variables for hybrid mode
set ENABLE_ENCRYPTION=false
set ENABLE_AUDIT_LOGGING=false
set ENABLE_ZERO_TRUST=false
set ENABLE_OBSERVABILITY=false

REM Kill any existing processes on ports 8000-8003
echo Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :800') do (
    taskkill /PID %%a /F 2>nul
)

REM Start the server
echo Starting server on port 8080...
python hybrid_api_server_fixed.py

pause
