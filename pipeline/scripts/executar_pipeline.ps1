# Disparo da pipeline pelo Agendador de Tarefas do Windows ou manualmente (D6).
# Uso: .\scripts\executar_pipeline.ps1 [comando] [argumentos extras]   (padrão: atualizar)
# No Agendador: execução semanal, "não iniciar nova instância" se outra estiver em execução.
# O ambiente virtual vem de TCC_VENV no .env (fora do OneDrive); sem ele, usa .\.venv.
param([string]$Comando = "atualizar", [Parameter(ValueFromRemainingArguments = $true)] $Extras)

$raiz = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $raiz ".venv"
$envFile = Join-Path $raiz ".env"
if (Test-Path $envFile) {
    foreach ($linha in Get-Content $envFile -Encoding UTF8) {
        if ($linha -match '^\s*TCC_VENV\s*=\s*(.+?)\s*$') { $venv = $Matches[1].Trim('"', "'") }
    }
}
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Python do ambiente virtual não encontrado em $python"
    exit 1
}
Set-Location $raiz
# O PowerShell transforma "a,b" em array; volta a juntar com vírgula (ex.: --series a,b).
$argumentos = @(foreach ($e in $Extras) { if ($e -is [array]) { $e -join ',' } else { $e } })
& $python -m tcc_pipeline $Comando @argumentos
exit $LASTEXITCODE
