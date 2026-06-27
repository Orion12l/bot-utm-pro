# Configura variables de PostgreSQL en el servicio del bot en Railway.
# Requiere: npx @railway/cli login y railway link en este directorio.

$ErrorActionPreference = "Stop"

$postgresService = $env:RAILWAY_POSTGRES_SERVICE
if (-not $postgresService) {
    $postgresService = "Postgres"
}

$botService = $env:RAILWAY_BOT_SERVICE
if (-not $botService) {
    $botService = "bot-utm-pro"
}

$refs = @(
    "DATABASE_PUBLIC_URL=${{$postgresService.DATABASE_PUBLIC_URL}}",
    "RAILWAY_TCP_PROXY_DOMAIN=${{$postgresService.RAILWAY_TCP_PROXY_DOMAIN}}",
    "RAILWAY_TCP_PROXY_PORT=${{$postgresService.RAILWAY_TCP_PROXY_PORT}}",
    "PGUSER=${{$postgresService.PGUSER}}",
    "PGPASSWORD=${{$postgresService.PGPASSWORD}}",
    "PGDATABASE=${{$postgresService.PGDATABASE}}"
)

Write-Host "Configurando variables en servicio '$botService'..."

foreach ($ref in $refs) {
    npx --yes @railway/cli variable set $ref --service $botService
    Write-Host "OK $ref"
}

Write-Host "Listo. Redeploy en curso."
npx --yes @railway/cli redeploy --service $botService --yes