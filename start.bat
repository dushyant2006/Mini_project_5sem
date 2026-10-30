@echo off
setlocal enabledelayedexpansion

title CodeDrift - Autonomous API Breaking-Change Guard
color 0B

echo ======================================================================
echo                     CODEDRIFT ENTERPRISE SYSTEM                       
echo    Autonomous API Breaking-Change ^& Dependency Degradation Guard     
echo ======================================================================
echo.

:: Step 1: Detect Python executable
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.8+ and retry.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version.split()[0])"') do set PY_VER=%%i
echo [INFO] Detected Python Version: %PY_VER%
echo.

:: Step 2: Ensure current directory is in PYTHONPATH
set PYTHONPATH=%CD%\src;%PYTHONPATH%

:: Step 3: Run full automated verification test suite
echo [1/3] Running Automated Invariant Test Suite (22 Tests)...
python run_tests.py
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [WARNING] Test suite reported warnings or errors.
    echo Proceeding to server initialization...
    echo.
) else (
    echo [SUCCESS] All automated test gates verified and passed.
    echo.
)

:: Step 4: Verify fixture and ML weight assets
echo [2/3] Verifying Fixtures ^& Model Weights...
if exist "data\fixtures\v1\payment_gateway.py" (
    echo   [OK] Payment Gateway v1 Fixture
) else (
    echo   [WARN] Missing v1 fixture file
)

if exist "data\fixtures\v2\payment_gateway.py" (
    echo   [OK] Payment Gateway v2 Fixture
) else (
    echo   [WARN] Missing v2 fixture file
)

if exist "models\degradation_weights.json" (
    echo   [OK] ML Degradation Weights Ready
) else (
    echo   [WARN] Missing models\degradation_weights.json
)
echo.

:: Step 5: Start Enterprise Web Platform & Gateway
echo [3/3] Launching CodeDrift Enterprise Platform on http://127.0.0.1:8080 ...
echo [INFO] Press Ctrl+C in this terminal window to stop the server anytime.
echo.

python -m codedrift ui --host 127.0.0.1 --port 8080

pause
