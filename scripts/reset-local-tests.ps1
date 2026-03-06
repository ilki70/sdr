$ErrorActionPreference = "Stop"

Write-Host "Stopping local stack and removing test volumes..."
docker compose down -v
if ($LASTEXITCODE -ne 0) {
  throw "docker compose down -v failed."
}

Write-Host "Local test volumes removed."
