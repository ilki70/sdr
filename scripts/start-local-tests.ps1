$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

try {
  docker info | Out-Null
} catch {
  throw "Docker Desktop nao esta em execucao. Inicie o Docker e tente novamente."
}

Write-Host "Starting infra (MySQL, Redis, Qdrant, Adminer)..."
docker compose up -d
if ($LASTEXITCODE -ne 0) {
  throw "docker compose up -d failed."
}

Write-Host "Bootstrapping backend (migrations + seed)..."
Push-Location backend
.\scripts\bootstrap_local.ps1
Pop-Location

Write-Host "Starting backend..."
Start-Process powershell -ArgumentList "-NoProfile -Command cd '$PWD\\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

Write-Host "Starting WhatsApp gateway..."
$goExe = "C:\\Program Files\\Go\\bin\\go.exe"
if (Test-Path $goExe) {
  Start-Process powershell -ArgumentList "-NoProfile -Command cd '$PWD\\services\\whatsapp-gateway'; & '$goExe' run ."
} else {
  Write-Warning "Go nao encontrado em C:\\Program Files\\Go\\bin\\go.exe. O gateway WhatsApp nao foi iniciado."
}

Write-Host "Starting celery worker..."
Start-Process powershell -ArgumentList "-NoProfile -Command cd '$PWD\\backend'; celery -A app.workers.celery_app.celery_app worker --pool solo --loglevel info"

Write-Host "Starting frontend..."
Start-Process powershell -ArgumentList "-NoProfile -Command cd '$PWD\\frontend'; npm run dev -- --hostname 127.0.0.1 --port 3000"

Write-Host "Done. Open http://127.0.0.1:3000/login"
