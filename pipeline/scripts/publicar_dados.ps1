# Publica os dados da pipeline no branch "dados" do GitHub.
#
# Uso:  .\scripts\publicar_dados.ps1 [-Worktree <pasta>] [-SemEnviar]
#
# O branch "dados" = código do main + pasta dados/ com uma cópia de <TCC_DADOS>
# (Bronze, Silver, publicação com as edições, registros de execução e relatórios de
# conferência). Ficam fora: a trava (.lock), a edição sintética (exemplo/) e bancos .duckdb.
#
# O branch é mantido num worktree fora do OneDrive (padrão: %USERPROFILE%\tcc-local\repo-dados).
# A cada execução: atualiza o código com o main, espelha <TCC_DADOS> em dados/, faz commit
# se algo mudou e envia (git push). Não roda enquanto a pipeline estiver com a trava.
param(
    [string]$Worktree = (Join-Path $env:USERPROFILE 'tcc-local\repo-dados'),
    [switch]$SemEnviar
)
$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $PSScriptRoot
$dados = Join-Path $raiz 'dados'
$envFile = Join-Path $raiz '.env'
if (Test-Path $envFile) {
    foreach ($linha in Get-Content $envFile -Encoding UTF8) {
        if ($linha -match '^\s*TCC_DADOS\s*=\s*(.+?)\s*$') { $dados = $Matches[1].Trim('"', "'") }
    }
}
if (-not (Test-Path (Join-Path $dados 'publicacao\atual.json'))) {
    Write-Error "Nenhuma edição publicada em $dados (rode a pipeline antes)."
}
if (Test-Path (Join-Path $dados '.lock')) {
    Write-Error "A pipeline está rodando (trava em $dados\.lock). Tente de novo quando terminar."
}

# Sem bloco param: $args repassa tudo ao git (inclusive -C, -A, -f) sem o PowerShell interpretar.
function Invoke-Git {
    & git @args
    if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') falhou (código $LASTEXITCODE)" }
}

# 1. Worktree do branch "dados" (criado na primeira vez)
Invoke-Git -C $raiz fetch origin
if (-not (Test-Path (Join-Path $Worktree '.git'))) {
    Invoke-Git -C $raiz worktree add $Worktree dados
}
Invoke-Git -C $Worktree pull --ff-only origin dados

# 2. Código atualizado com o main
# O main não versiona dados/ (D39). Quando um arquivo de dados/ mudou neste branch e foi
# apagado no main, o merge dá conflito; ele é resolvido no passo 4 pela cópia nova dos dados
# (git add). Conflito fora de dados/ interrompe o script com o merge desfeito.
& git -C $Worktree merge --no-edit origin/main
if ($LASTEXITCODE -ne 0) {
    $conflitos = @(& git -C $Worktree diff --name-only --diff-filter=U)
    $fora = @($conflitos | Where-Object { $_ -notlike 'dados/*' })
    if ($conflitos.Count -eq 0 -or $fora.Count -gt 0) {
        & git -C $Worktree merge --abort
        throw "merge do main no branch dados com conflito fora de dados/: $($fora -join ', ')"
    }
    Write-Output "Merge do main: $($conflitos.Count) conflito(s) em dados/, resolvidos pela cópia nova."
}

# 3. Espelho dos dados (robocopy: códigos 0 a 7 são sucesso)
$destino = Join-Path $Worktree 'dados'
# Bancos .duckdb de consulta local ficam fora (podem estar abertos num cliente e travar a cópia).
robocopy $dados $destino /MIR /XD exemplo /XF .lock *.duckdb *.duckdb.* /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy falhou (código $LASTEXITCODE)" }

# 4. Commit e envio
# -f: dados/ fica no .gitignore do main (código); só neste branch a pasta é versionada.
Invoke-Git -C $Worktree add -A -f dados
$emMerge = Test-Path (Join-Path (& git -C $Worktree rev-parse --absolute-git-dir) 'MERGE_HEAD')
& git -C $Worktree diff --cached --quiet
if ($LASTEXITCODE -eq 0 -and $emMerge) {
    Invoke-Git -C $Worktree commit -q --no-edit
    Write-Output 'Commit: merge do main (dados sem alterações).'
} elseif ($LASTEXITCODE -eq 0) {
    Write-Output 'Dados sem alterações desde o último envio.'
} else {
    $atual = Get-Content (Join-Path $dados 'publicacao\atual.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $mensagem = "Dados: edição ativa $($atual.id_edicao_ativa) ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"
    Invoke-Git -C $Worktree commit -q -m $mensagem
    Write-Output "Commit: $mensagem"
}
if ($SemEnviar) {
    Write-Output "Envio pulado (-SemEnviar). Worktree: $Worktree"
} else {
    Invoke-Git -C $Worktree push origin dados
    Write-Output 'Enviado para origin/dados.'
}
