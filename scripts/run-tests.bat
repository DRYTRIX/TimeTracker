@echo off
REM TimeTracker Test Runner for Windows
REM Quick test execution script

echo ========================================
echo TimeTracker Test Runner
echo ========================================
echo.

REM Check if pytest is installed
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pytest not found!
    echo Please install test dependencies:
    echo   pip install -r requirements-test.txt
    exit /b 1
)

REM Parse command line arguments
if "%1"=="" goto usage
if "%1"=="smoke" goto smoke
if "%1"=="unit" goto unit
if "%1"=="integration" goto integration
if "%1"=="security" goto security
if "%1"=="all" goto all
if "%1"=="coverage" goto coverage
if "%1"=="fast" goto fast
if "%1"=="parallel" goto parallel
goto usage

:smoke
echo Running smoke tests (quick critical tests)...
python -m pytest -m smoke -v
goto end

:unit
echo Running unit tests...
python -m pytest -m unit -v
goto end

:integration
echo Running integration tests...
python -m pytest -m integration -v
goto end

:security
echo Running security tests...
python -m pytest -m security -v
goto end

:all
echo Running full test suite in parallel...
python -m pytest -v -n auto
goto end

:coverage
echo Running tests with coverage...
python -m pytest --cov=app --cov-report=html --cov-report=term
echo.
echo Coverage report generated in htmlcov/index.html
goto end

:fast
echo Running tests in parallel (fast mode)...
python -m pytest -n auto -v
goto end

:parallel
echo Running tests in parallel with 4 workers...
python -m pytest -n 4 -v
goto end

:usage
echo Usage: run-tests.bat [command]
echo.
echo Commands:
echo   smoke        - Run smoke tests (fastest, ^< 1 min)
echo   unit         - Run unit tests (2-5 min)
echo   integration  - Run integration tests (5-10 min)
echo   security     - Run security tests (3-5 min)
echo   all          - Run full test suite (15-30 min)
echo   coverage     - Run tests with coverage report
echo   fast         - Run tests in parallel (auto workers)
echo   parallel     - Run tests in parallel (4 workers)
echo.
echo Examples:
echo   run-tests.bat smoke
echo   run-tests.bat coverage
echo   run-tests.bat fast
goto end

:end

