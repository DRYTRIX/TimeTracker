# Version Manager for TimeTracker - PowerShell Wrapper

param(
    [Parameter(Position=0)]
    [string]$Action,

    [Parameter(Position=1)]
    [string]$Version,

    [Parameter(Position=2)]
    [string]$Message,

    [int]$BuildNumber,
    [switch]$NoPush,
    [string]$Tag
)

if (-not $Action) {
    Write-Host "Usage: .\version-manager.ps1 [action] [options]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  tag [version] [message]  - Create a version tag"
    Write-Host "  build [number]           - Create a build tag"
    Write-Host "  list                     - List all tags"
    Write-Host "  info [tag]               - Show tag information"
    Write-Host "  status                   - Show current status"
    Write-Host "  suggest                  - Suggest next version"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\version-manager.ps1 tag v1.2.3 'Release 1.2.3'"
    Write-Host "  .\version-manager.ps1 build 123"
    Write-Host "  .\version-manager.ps1 status"
    Write-Host ""
    exit 1
}

# Build arguments for Python script
$args = @($Action)

if ($Version) { $args += "--version", $Version }
if ($Message) { $args += "--message", $Message }
if ($BuildNumber) { $args += "--build-number", $BuildNumber }
if ($NoPush) { $args += "--no-push" }
if ($Tag) { $args += "--tag", $Tag }

# Run the Python script
python scripts/version-manager.py @args
