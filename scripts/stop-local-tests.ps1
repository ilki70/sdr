Write-Host "Stopping local services (docker infra only)..."
docker compose down
Write-Host "If backend/frontend were started in separate terminals, close those processes manually."
