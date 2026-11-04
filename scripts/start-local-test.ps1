# PowerShell script to start TimeTracker Local Test Environment with SQLite

Write-Host "Starting TimeTracker Local Test Environment with SQLite..." -ForegroundColor Green
Write-Host ""

# Check if docker-compose is available
try {
    $null = docker-compose --version
} catch {
    Write-Host "Error: docker-compose is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop or Docker Compose" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Docker is running
try {
    $null = docker info
} catch {
    Write-Host "Error: Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Building and starting containers..." -ForegroundColor Cyan
docker-compose -f docker/docker-compose.local-test.yml up --build

Write-Host ""
Write-Host "Local test environment stopped." -ForegroundColor Green
Read-Host "Press Enter to exit"
