# Fix OneDrive file locking issues for npm install
# This PowerShell script handles locked files better than batch files

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DesktopDir = Join-Path $ProjectRoot "desktop"
$NodeModulesDir = Join-Path $DesktopDir "node_modules"

Write-Host "Fixing OneDrive file locking issues..." -ForegroundColor Cyan
Write-Host ""

# Check if in OneDrive
if ($ProjectRoot -like "*OneDrive*") {
    Write-Host "WARNING: Project is in OneDrive!" -ForegroundColor Yellow
    Write-Host "OneDrive file locking causes npm install to fail." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "RECOMMENDED: Exclude node_modules from OneDrive sync:" -ForegroundColor Cyan
    Write-Host "  1. Right-click: $DesktopDir\node_modules" -ForegroundColor White
    Write-Host "  2. Choose 'Always keep on this device'" -ForegroundColor White
    Write-Host "  3. Or exclude it from OneDrive sync entirely" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 0
    }
    Write-Host ""
}

Set-Location $DesktopDir

# Clean npm cache
Write-Host "Cleaning npm cache..." -ForegroundColor Cyan
try {
    npm cache clean --force 2>&1 | Out-Null
    Write-Host "  [OK] Cache cleaned" -ForegroundColor Green
} catch {
    Write-Host "  [WARNING] Cache clean had issues, continuing..." -ForegroundColor Yellow
}
Write-Host ""

# Remove node_modules with retries and better error handling
if (Test-Path $NodeModulesDir) {
    Write-Host "Removing node_modules..." -ForegroundColor Cyan
    Write-Host "  (This may take a moment, especially with OneDrive locking)" -ForegroundColor Yellow
    Write-Host ""
    
    # Method 1: Try Remove-Item with -Recurse -Force
    $maxRetries = 5
    $retry = 0
    $removed = $false
    
    while ($retry -lt $maxRetries -and -not $removed) {
        $retry++
        Write-Host "  Attempt $retry/$maxRetries..." -ForegroundColor Yellow
        
        try {
            # Try to remove locked files first
            Get-ChildItem -Path $NodeModulesDir -Recurse -Force -ErrorAction SilentlyContinue | 
                ForEach-Object {
                    try {
                        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
                    } catch {
                        # Ignore individual file errors
                    }
                }
            
            # Remove directory
            Remove-Item -Path $NodeModulesDir -Recurse -Force -ErrorAction Stop
            $removed = $true
            Write-Host "  [OK] node_modules removed" -ForegroundColor Green
        } catch {
            if ($retry -lt $maxRetries) {
                Write-Host "  [WARNING] Attempt $retry failed, waiting 3 seconds..." -ForegroundColor Yellow
                Start-Sleep -Seconds 3
            } else {
                Write-Host "  [ERROR] Failed to remove after $maxRetries attempts" -ForegroundColor Red
                Write-Host ""
                Write-Host "Manual steps required:" -ForegroundColor Yellow
                Write-Host "  1. Close ALL programs (VS Code, terminals, File Explorer, etc.)"
                Write-Host "  2. Open PowerShell as Administrator"
                Write-Host "  3. Run: Remove-Item -Path '$NodeModulesDir' -Recurse -Force"
                Write-Host "  4. Or manually delete the folder in File Explorer"
                Write-Host ""
                Write-Host "Or exclude from OneDrive sync first (recommended)"
                exit 1
            }
        }
    }
    Write-Host ""
}

# Remove package-lock.json
if (Test-Path "package-lock.json") {
    Write-Host "Removing package-lock.json..." -ForegroundColor Cyan
    try {
        Remove-Item -Path "package-lock.json" -Force
        Write-Host "  [OK] Removed" -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] Could not remove package-lock.json" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Reinstall dependencies
Write-Host "Reinstalling dependencies..." -ForegroundColor Cyan
Write-Host "  (This may take several minutes)" -ForegroundColor Yellow
Write-Host ""

try {
    npm install --prefer-offline --no-audit --loglevel=warn
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Dependencies installed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. IMPORTANT: Exclude node_modules from OneDrive sync" -ForegroundColor Yellow
        Write-Host "     - Right-click: $DesktopDir\node_modules" -ForegroundColor White
        Write-Host "     - Choose 'Always keep on this device'" -ForegroundColor White
        Write-Host "  2. Run the build: scripts\build-desktop-simple.bat" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "[ERROR] Installation failed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Try these solutions:" -ForegroundColor Yellow
        Write-Host "  1. EXCLUDE node_modules from OneDrive sync (MOST IMPORTANT!)"
        Write-Host "  2. Run PowerShell as Administrator"
        Write-Host "  3. Temporarily disable antivirus real-time scanning"
        Write-Host "  4. Move project outside OneDrive folder"
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "[ERROR] Installation failed: $_" -ForegroundColor Red
    exit 1
}
