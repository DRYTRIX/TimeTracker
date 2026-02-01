@echo off
REM Generate mobile app icon (app_icon.png) from SVG or Python fallback.
setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set SVG=%PROJECT_ROOT%\app\static\images\timetracker-logo-icon.svg
set OUT=%PROJECT_ROOT%\mobile\assets\icon\app_icon.png

if not exist "%PROJECT_ROOT%\mobile\assets\icon" mkdir "%PROJECT_ROOT%\mobile\assets\icon"

REM Try ImageMagick first (exact SVG export)
where magick >nul 2>&1
if %errorlevel% equ 0 (
    magick "%SVG%" -resize 1024x1024 "%OUT%"
    if %errorlevel% equ 0 (
        echo Generated app_icon.png with ImageMagick
        exit /b 0
    )
)

REM Fallback: Python script (requires Pillow)
python "%SCRIPT_DIR%generate-mobile-icon.py"
exit /b %errorlevel%
