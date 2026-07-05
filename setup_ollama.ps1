Write-Host "=== Setup Ollama para el Agente Conversacional ===" -ForegroundColor Cyan

# 1. Verificar si Ollama ya está instalado
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "Descargando e instalando Ollama..." -ForegroundColor Yellow
    $installer = "$env:TEMP\OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installer
    Start-Process -Wait -FilePath $installer
    Write-Host "Ollama instalado. Cerra y abre de nuevo la terminal, o ejecuta:" -ForegroundColor Green
    Write-Host "  refreshenv" -ForegroundColor Gray
    Write-Host "  ollama serve" -ForegroundColor Gray
} else {
    Write-Host "Ollama ya está instalado." -ForegroundColor Green
}

# 2. Verificar que el modelo esté descargado
$models = & ollama list 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Arrancando Ollama..." -ForegroundColor Yellow
    Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve"
    Start-Sleep -Seconds 3
}

$hasModel = $models -match "llama3.2"
if (-not $hasModel) {
    Write-Host "Descargando modelo llama3.2..." -ForegroundColor Yellow
    & ollama pull llama3.2
} else {
    Write-Host "Modelo llama3.2 ya descargado." -ForegroundColor Green
}

# 3. Crear .env si no existe
if (-not (Test-Path ".env")) {
    @"
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.2
"@ | Set-Content ".env"
    Write-Host ".env creado para Ollama." -ForegroundColor Green
}

Write-Host ""
Write-Host "Todo listo. Ejecuta:" -ForegroundColor Cyan
Write-Host "  python main.py" -ForegroundColor White
