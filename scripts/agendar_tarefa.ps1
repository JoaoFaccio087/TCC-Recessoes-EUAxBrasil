# Cadastra (ou atualiza) a execução semanal da pipeline no Agendador de Tarefas do Windows
# (D6; texto 4.3, 5.2 e 6.3; Quadro 4).
#
# Uso:  .\scripts\agendar_tarefa.ps1 [-Dia Monday] [-Hora 08:00] [-Remover]
#
# - Semanal, "não iniciar nova instância" se outra estiver rodando (a trava dados/.lock cobre
#   também a execução manual, D14).
# - StartWhenAvailable: se o computador estiver desligado no horário, roda assim que possível
#   (risco "computador desligado na data agendada", Quadro 4).
# - Roda com o usuário atual, só com sessão aberta: não pede nem guarda senha.
param(
    [ValidateSet('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')]
    [string]$Dia = 'Monday',
    [string]$Hora = '08:00',
    [switch]$Remover
)

$nome = 'TCC - atualizar dados (recessoes EUA x Brasil)'
$raiz = Split-Path -Parent $PSScriptRoot
$script = Join-Path $PSScriptRoot 'executar_pipeline.ps1'

if ($Remover) {
    Unregister-ScheduledTask -TaskName $nome -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarefa removida: $nome"
    exit 0
}

$acao = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$script`" atualizar" `
    -WorkingDirectory $raiz
$gatilho = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Dia -At $Hora
$config = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilho -Settings $config `
    -Principal $principal -Description 'Pipeline do TCC: coleta, Silver, Gold, validacao e publicacao (atualizar). Codigos de saida: 0 OK, 1 falha, 2 validacao reprovada, 3 bloqueado.' `
    -Force | Out-Null

$t = Get-ScheduledTask -TaskName $nome
$info = $t | Get-ScheduledTaskInfo
Write-Output "Tarefa cadastrada: $nome"
Write-Output "  Quando: toda $Dia as $Hora (proxima: $($info.NextRunTime))"
Write-Output "  Comando: powershell.exe $($t.Actions[0].Arguments)"
Write-Output "  Nova instancia se ja estiver rodando: $($t.Settings.MultipleInstances)"
Write-Output "Para rodar agora: Start-ScheduledTask -TaskName '$nome'"
