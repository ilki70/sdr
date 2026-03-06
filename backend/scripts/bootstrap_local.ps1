$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

function Invoke-Native {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [string[]]$Arguments = @()
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $Command $($Arguments -join ' ')"
  }
}

function Wait-ForMySql {
  param(
    [int]$MaxAttempts = 30
  )

  $script = @'
import sys
import pymysql
from app.core.config import get_settings

settings = get_settings()
url = settings.mysql_url.replace("mysql+asyncmy://", "")
creds, host_part = url.split("@", 1)
user, password = creds.split(":", 1)
host_port, database = host_part.split("/", 1)
host, port = host_port.split(":", 1)

try:
    connection = pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        connect_timeout=2,
        read_timeout=2,
        write_timeout=2,
    )
    connection.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
'@

  for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $script | python -
    if ($LASTEXITCODE -eq 0) {
      Write-Host "MySQL ready."
      return
    }
    Write-Host "Waiting for MySQL... attempt $attempt/$MaxAttempts"
    Start-Sleep -Seconds 2
  }

  throw "MySQL did not become ready in time."
}

$env:PYTHONPATH = (Get-Location).Path

Write-Host "Installing backend dependencies..."
Invoke-Native -Command "pip" -Arguments @("install", "-r", "requirements.txt")

Write-Host "Waiting for MySQL..."
Wait-ForMySql

Write-Host "Applying migrations..."
Invoke-Native -Command "alembic" -Arguments @("upgrade", "head")

Write-Host "Seeding deep test data..."
Invoke-Native -Command "python" -Arguments @("-m", "scripts.seed_deep_test_data")

Write-Host "Bootstrap completed."
