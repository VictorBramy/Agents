Write-Host "Checking local server..." -ForegroundColor Cyan

# 1. Start Uvicorn if not running
$conn = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if (!$conn) {
    Write-Host "Starting Uvicorn server on port 8080..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8080" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "Uvicorn server is already running on port 8080." -ForegroundColor Green
}

# 2. Start Cloudflare Tunnel
Write-Host "Connecting to Cloudflare Free Secure Cloud..." -ForegroundColor Cyan
& ".\bin\cloudflared.exe" tunnel --url http://127.0.0.1:8080
