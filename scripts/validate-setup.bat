@echo off
REM TimeTracker CI/CD Setup Validation Script for Windows
REM Runs the Python validation script

echo ========================================
echo TimeTracker CI/CD Setup Validation
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.11 or higher
    exit /b 1
)

REM Run the validation script
python scripts\validate-setup.py
exit /b %ERRORLEVEL%
