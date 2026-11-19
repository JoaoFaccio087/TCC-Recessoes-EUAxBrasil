# Publica a edição ativa em todos os destinos, com um comando só (D39).
#
# Uso:  .\scripts\publicar_tudo.ps1
#
# Rode à mão, depois de conferir a edição. NÃO é chamado pelo "atualizar" nem pelo Agendador.
# Para no primeiro erro, dizendo qual passo falhou. Passos:
#   1. Branch "dados" do repositório (scripts\publicar_dados.ps1): espelho de <TCC_DADOS>.
#   2. Dashboard (deshboard\alimentar_dashboard.py), lido do branch "dados" (fonte única).
#      Se o dashboard mudou: commit no main, push do main e novo publicar_dados.ps1, para o
#      branch "dados" levar o mesmo dashboard.
#   3. Branch "pipeline" do repositório do João: pipeline/ = código do main + dados/ do branch "dados".
# No fim, mostra o id_edicao de cada destino, para conferir que estão todos na mesma edição.
#
# Pré-requisitos: estar no branch main, sem alterações pendentes no código (arquivos não
# versionados, como .vscode/, não atrapalham).
# Atenção: o script faz push do main (origin) logo no início, porque o branch "dados" e o
# branch do João recebem o código do main. Commits locais ainda não enviados vão junto.
param(
    [string]$RemotoJoao = 'joao',
    [string]$UrlJoao = 'https://github.com/JoaoFaccio087/TCC-Recessoes-EUAxBrasil.git',
    [string]$BranchJoao = 'pipeline'
)
$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $raiz '.venv'
$dados = Join-Path $raiz 'dados'
$repoDados = Join-Path $env:USERPROFILE 'tcc-local\repo-dados'
$envFile = Join-Path $raiz '.env'
if (Test-Path $envFile) {
    foreach ($linha in Get-Content $envFile -Encoding UTF8) {
        if ($linha -match '^\s*TCC_VENV\s*=\s*(.+?)\s*$') { $venv = $Matches[1].Trim('"', "'") }
        if ($linha -match '^\s*TCC_DADOS\s*=\s*(.+?)\s*$') { $dados = $Matches[1].Trim('"', "'") }
        if ($linha -match '^\s*TCC_REPO_DADOS\s*=\s*(.+?)\s*$') { $repoDados = $Matches[1].Trim('"', "'") }
    }
}
$python = Join-Path $venv 'Scripts\python.exe'

function Invoke-Git {
    & git @args
    if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') falhou (código $LASTEXITCODE)" }
}

function Invoke-Passo([string]$nome, [scriptblock]$acao) {
    Write-Output ''
    Write-Output "=== $nome ==="
    try {
        & $acao
    } catch {
        Write-Output ''
        Write-Output "FALHOU no passo: $nome"
        Write-Output "Motivo: $($_.Exception.Message)"
        Write-Output 'Os passos seguintes não foram executados.'
        exit 1
    }
}

function Get-EdicaoNoGit([string]$ref, [string]$caminho) {
    $ErrorActionPreference = 'Continue'  # git show escreve no stderr se o arquivo não existir
    $txt = & git -C $raiz show "${ref}:$caminho" 2>$null
    if ($LASTEXITCODE -ne 0) { return '(não encontrado)' }
    $json = ($txt -join "`n") | ConvertFrom-Json
    if ($json.id_edicao_ativa) { return $json.id_edicao_ativa }
    return $json.id_edicao
}

Invoke-Passo 'Verificações iniciais' {
    if (-not (Test-Path $python)) { throw "Python do ambiente virtual não encontrado em $python" }
    $branch = (& git -C $raiz rev-parse --abbrev-ref HEAD).Trim()
    if ($branch -ne 'main') { throw "o repositório está no branch '$branch'; mude para o main." }
    $pendentes = @(& git -C $raiz status --porcelain --untracked-files=no)
    if ($pendentes.Count -gt 0) {
        throw "há alterações não commitadas no main: $($pendentes -join '; '). Faça commit antes."
    }
    if (Test-Path (Join-Path $dados '.lock')) { throw "a pipeline está rodando ($dados\.lock)." }
    $atual = Get-Content (Join-Path $dados 'publicacao\atual.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $script:edicaoLocal = $atual.id_edicao_ativa
    Write-Output "Edição ativa em TCC_DADOS: $script:edicaoLocal"
    Invoke-Git -C $raiz fetch -q origin
    Invoke-Git -C $raiz push -q origin main
}

Invoke-Passo '1/3 Branch dados (publicar_dados.ps1)' {
    & (Join-Path $PSScriptRoot 'publicar_dados.ps1') -Worktree $repoDados
}

Invoke-Passo '2/3 Dashboard (alimentar_dashboard.py, lido do branch dados)' {
    & $python -X utf8 (Join-Path $raiz 'deshboard\alimentar_dashboard.py') --origem (Join-Path $repoDados 'dados')
    if ($LASTEXITCODE -ne 0) { throw "alimentar_dashboard.py terminou com código $LASTEXITCODE" }
    Invoke-Git -C $raiz add deshboard
    & git -C $raiz diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Output 'Dashboard sem alterações.'
    } else {
        $ed = Get-Content (Join-Path $raiz 'deshboard\data\edicao.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        Invoke-Git -C $raiz commit -q -m "Dashboard: edição $($ed.id_edicao)"
        Invoke-Git -C $raiz push -q origin main
        Write-Output "Commit e push do main: Dashboard: edição $($ed.id_edicao)"
        & (Join-Path $PSScriptRoot 'publicar_dados.ps1') -Worktree $repoDados
    }
}

Invoke-Passo "3/3 Repositório do João (branch $BranchJoao)" {
    $remotos = @(& git -C $raiz remote)
    if ($remotos -notcontains $RemotoJoao) { Invoke-Git -C $raiz remote add $RemotoJoao $UrlJoao }
    Invoke-Git -C $raiz fetch -q $RemotoJoao $BranchJoao
    $wt = Join-Path $env:TEMP 'tcc-publicar-joao'
    if (Test-Path $wt) {
        $ErrorActionPreference = 'Continue'
        & git -C $raiz worktree remove --force $wt 2>$null
        Remove-Item -Recurse -Force $wt -ErrorAction SilentlyContinue
        & git -C $raiz worktree prune
        $ErrorActionPreference = 'Stop'
    }
    Invoke-Git -C $raiz worktree add -q -B publicar-joao $wt "$RemotoJoao/$BranchJoao"
    try {
        # pipeline/ inteira é refeita: código do main (sem dados/) + dados/ do branch dados.
        $destino = Join-Path $wt 'pipeline'
        if (Test-Path $destino) { Invoke-Git -C $wt rm -r -q --ignore-unmatch pipeline }
        if (Test-Path $destino) { Remove-Item -Recurse -Force $destino }
        New-Item -ItemType Directory -Force $destino | Out-Null
        $tar = Join-Path $env:TEMP 'tcc-publicar-joao.tar'
        Invoke-Git -C $raiz archive --format=tar -o $tar HEAD
        & tar -xf $tar -C $destino
        if ($LASTEXITCODE -ne 0) { throw "falha ao extrair o código (tar, código $LASTEXITCODE)" }
        Remove-Item $tar
        robocopy (Join-Path $repoDados 'dados') (Join-Path $destino 'dados') /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy falhou (código $LASTEXITCODE)" }
        Invoke-Git -C $wt add -A pipeline
        Invoke-Git -C $wt add -A -f pipeline/dados
        & git -C $wt diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Output "Branch $BranchJoao sem alterações."
        } else {
            $commit = (& git -C $raiz rev-parse --short HEAD).Trim()
            Invoke-Git -C $wt commit -q -m "pipeline/: código do main ($commit) e edição $script:edicaoLocal"
            Invoke-Git -C $wt push -q $RemotoJoao "publicar-joao:$BranchJoao"
            Write-Output "Enviado para $RemotoJoao/$BranchJoao."
        }
    } finally {
        $ErrorActionPreference = 'Continue'
        & git -C $raiz worktree remove --force $wt 2>$null
        & git -C $raiz branch -D publicar-joao 2>$null | Out-Null
    }
    Invoke-Git -C $raiz fetch -q $RemotoJoao $BranchJoao
}

Invoke-Git -C $raiz fetch -q origin
Write-Output ''
Write-Output '=== Edição em cada destino ==='
$destinos = [ordered]@{
    'TCC_DADOS (local)'                    = $script:edicaoLocal
    'branch dados (origin/dados)'          = Get-EdicaoNoGit 'origin/dados' 'dados/publicacao/atual.json'
    'dashboard (origin/main)'              = Get-EdicaoNoGit 'origin/main' 'deshboard/data/edicao.json'
    "João ($RemotoJoao/$BranchJoao)"       = Get-EdicaoNoGit "$RemotoJoao/$BranchJoao" 'pipeline/dados/publicacao/atual.json'
}
$destinos.GetEnumerator() | ForEach-Object { Write-Output ("{0,-36} {1}" -f $_.Key, $_.Value) }
$distintos = @($destinos.Values | Select-Object -Unique)
if ($distintos.Count -eq 1) {
    Write-Output "OK: todos os destinos na edição $($distintos[0])."
} else {
    Write-Output 'ATENÇÃO: os destinos estão em edições diferentes.'
    exit 1
}
