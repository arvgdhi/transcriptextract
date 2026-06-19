# YouTube Transcript Downloader - Setup & Launch
# Run this once in PowerShell (right-click -> Run with PowerShell, or paste into terminal)

Write-Host ""
Write-Host "  YouTube Transcript Downloader" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# 1. Check Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: Python is not installed or not on your PATH." -ForegroundColor Red
    Write-Host "  Download it from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "  Press Enter to exit"
    exit 1
}

$pyVersion = python --version 2>&1
Write-Host "  Found $pyVersion" -ForegroundColor DarkGray

# 2. Install youtube-transcript-api if not already installed
Write-Host "  Checking dependencies..." -ForegroundColor DarkGray
$installed = python -c "import youtube_transcript_api; print('ok')" 2>$null
if ($installed -ne "ok") {
    Write-Host "  Installing youtube-transcript-api..." -ForegroundColor Yellow
    python -m pip install youtube-transcript-api --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: pip install failed. Try running as Administrator." -ForegroundColor Red
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Host "  Installed." -ForegroundColor Green
} else {
    Write-Host "  youtube-transcript-api already installed." -ForegroundColor DarkGray
}

# 3. Launch server.py from the same folder as this script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverPath = Join-Path $scriptDir "server.py"

if (-not (Test-Path $serverPath)) {
    Write-Host "  ERROR: server.py not found in $scriptDir" -ForegroundColor Red
    Write-Host "  Make sure server.py and this script are in the same folder." -ForegroundColor Yellow
    Read-Host "  Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "  Starting server... (close this window to stop)" -ForegroundColor Cyan
Write-Host ""

# Run server.py — it will open the browser automatically
python $serverPath
