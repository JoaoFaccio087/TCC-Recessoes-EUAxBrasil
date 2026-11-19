# Publica a edição ativa em todos os destinos, com um comando só (D39, D41).
#
# Uso:  .\scripts\publicar_tudo.ps1
#
# Rode à mão, depois de conferir a edição. NÃO é chamado pelo "atualizar" nem pelo Agendador.
# Para no primeiro erro, dizendo qual passo falhou. Passos:
#   1. Branch "dados" do repositório (scripts\publicar_dados.ps1): espelho de <TCC_DADOS>.
#   2. Dashboard (deshboard\alimentar_dashboard.py), lido do branch "dados" (fonte única).
#      Se o dashboard mudou: commit no main, push do main e novo publicar_dados.ps1, para o
#      branch "dados" levar o mesmo dashboard.
#   3. Branch "pipeline" do repositório do João: o main entra em pipeline/ por git subtree, com
#      histórico (na primeira vez, a cópia solta de pipeline/ é removida e vem o "subtree add";
#      depois, "subtree merge"); em seguida, pipeline/dados/ recebe a cópia do branch "dados".
#   4. Protótipo do painel (branch "painel" do repositório do João): dados.py lê a edição ativa
#      do branch "dados" e montar.py regera painel/prototipo/index.html; commit e push no "painel".
#      As dependências npm ficam fora do OneDrive (TCC_PROTOTIPO_NODE, padrão
#      %USERPROFILE%\tcc-local\prototipo-node) e são reinstaladas se o package.json mudar.
# No fim, mostra o id_edicao de cada destino, para conferir que estão todos na mesma edição.
#
# Pré-requisitos: estar no branch main, sem alterações pendentes no código (arquivos não
# versionados, como .vscode/, não atrapalham).
# Atenção: o script faz push do main (origin) logo no início, porque o branch "dados" e o
# branch do João recebem o código do main. Commits locais ainda não enviados vão junto.
param(
    [string]$RemotoJoao = 'joao',
    [string]$UrlJoao = 'https://github.com/JoaoFaccio087/TCC-Recessoes-EUAxBrasil.git',
    [string]$BranchJoao = 'pipeline',
    [string]$BranchPainel = 'painel'
)
$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $raiz '.venv'
$dados = Join-Path $raiz 'dados'
$repoDados = Join-Path $env:USERPROFILE 'tcc-local\repo-dados'
$nodeProto = Join-Path $env:USERPROFILE 'tcc-local\prototipo-node'
$envFile = Join-Path $raiz '.env'
if (Test-Path $envFile) {
    foreach ($linha in Get-Content $envFile -Encoding UTF8) {
        if ($linha -match '^\s*TCC_VENV\s*=\s*(.+?)\s*$') { $venv = $Matches[1].Trim('"', "'") }
        if ($linha -match '^\s*TCC_DADOS\s*=\s*(.+?)\s*$') { $dados = $Matches[1].Trim('"', "'") }
        if ($linha -match '^\s*TCC_REPO_DADOS\s*=\s*(.+?)\s*$') { $repoDados = $Matches[1].Trim('"', "'") }
        if ($linha -match '^\s*TCC_PROTOTIPO_NODE\s*=\s*(.+?)\s*$') { $nodeProto = $Matches[1].Trim('"', "'") }
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
    if ($json.edicao.id) { return $json.edicao.id }
    return $json.id_edicao
}

# Worktree temporária num branch local criado a partir de uma ref remota.
function New-WorktreeTemp([string]$nome, [string]$ref) {
    $wt = Join-Path $env:TEMP $nome
    $ErrorActionPreference = 'Continue'
    if (Test-Path $wt) {
        & git -C $raiz worktree remove --force $wt 2>$null
        Remove-Item -Recurse -Force $wt -ErrorAction SilentlyContinue
    }
    & git -C $raiz worktree prune
    $ErrorActionPreference = 'Stop'
    Invoke-Git -C $raiz worktree add -q -B $nome $wt $ref
    return $wt
}

function Remove-WorktreeTemp([string]$nome) {
    $ErrorActionPreference = 'Continue'
    & git -C $raiz worktree remove --force (Join-Path $env:TEMP $nome) 2>$null
    & git -C $raiz worktree prune
    & git -C $raiz branch -D $nome 2>$null | Out-Null
}

function Get-EdicaoBranchDados {
    $a = Get-Content (Join-Path $repoDados 'dados\publicacao\atual.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    return $a.id_edicao_ativa
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

Invoke-Passo '1/4 Branch dados (publicar_dados.ps1)' {
    & (Join-Path $PSScriptRoot 'publicar_dados.ps1') -Worktree $repoDados
}

Invoke-Passo '2/4 Dashboard (alimentar_dashboard.py, lido do branch dados)' {
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

Invoke-Passo "3/4 Repositório do João, branch $BranchJoao (git subtree)" {
    $remotos = @(& git -C $raiz remote)
    if ($remotos -notcontains $RemotoJoao) { Invoke-Git -C $raiz remote add $RemotoJoao $UrlJoao }
    Invoke-Git -C $raiz fetch -q $RemotoJoao $BranchJoao
    Invoke-Git -C $raiz fetch -q origin main
    $codigo = (& git -C $raiz rev-parse origin/main).Trim()
    $wt = New-WorktreeTemp 'publicar-joao' "$RemotoJoao/$BranchJoao"
    try {
        $subtree = "$(& git -C $wt log -1 --format=%H --grep='^git-subtree-dir: pipeline$')".Trim()
        if (-not $subtree) {
            # Primeira vez: a cópia solta de pipeline/ sai e o main entra com o histórico.
            if (Test-Path (Join-Path $wt 'pipeline')) {
                Invoke-Git -C $wt rm -r -q pipeline
                Invoke-Git -C $wt commit -q -m 'pipeline/: remove a cópia solta para trazer o código por git subtree, com histórico'
            }
            Invoke-Git -C $wt subtree add -q --prefix=pipeline $codigo -m "pipeline/: código do main ($($codigo.Substring(0,7))) por git subtree"
            Write-Output 'Migração para git subtree feita (subtree add).'
        } else {
            Invoke-Git -C $wt subtree merge -q --prefix=pipeline $codigo -m "pipeline/: atualiza com o main ($($codigo.Substring(0,7)))"
        }
        # Dados: cópia do branch "dados" (o main não versiona dados/; D39).
        robocopy (Join-Path $repoDados 'dados') (Join-Path $wt 'pipeline\dados') /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy falhou (código $LASTEXITCODE)" }
        Invoke-Git -C $wt add -A -f pipeline/dados
        & git -C $wt diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            Invoke-Git -C $wt commit -q -m "pipeline/dados: edição $(Get-EdicaoBranchDados)"
        }
        $novos = [int](& git -C $wt rev-list --count "$RemotoJoao/$BranchJoao..HEAD")
        if ($novos -eq 0) {
            Write-Output "Branch $BranchJoao sem alterações."
        } else {
            Invoke-Git -C $wt push -q $RemotoJoao "HEAD:$BranchJoao"
            Write-Output "Enviado para $RemotoJoao/$BranchJoao ($novos commit(s))."
        }
    } finally {
        Remove-WorktreeTemp 'publicar-joao'
    }
    Invoke-Git -C $raiz fetch -q $RemotoJoao $BranchJoao
}

Invoke-Passo "4/4 Protótipo do painel (branch $BranchPainel)" {
    Invoke-Git -C $raiz fetch -q $RemotoJoao $BranchPainel
    $wt = New-WorktreeTemp 'publicar-painel' "$RemotoJoao/$BranchPainel"
    try {
        $fonte = Join-Path $wt 'painel\prototipo\fonte'
        if (-not (Test-Path (Join-Path $fonte 'dados.py'))) { throw "dados.py não encontrado em $fonte" }
        # Dependências npm fora do OneDrive; reinstala se o package.json do protótipo mudou.
        New-Item -ItemType Directory -Force $nodeProto | Out-Null
        $pkgNovo = (Get-Content (Join-Path $fonte 'package.json') -Raw) -replace "`r", ''
        $pkgAtual = if (Test-Path (Join-Path $nodeProto 'package.json')) { (Get-Content (Join-Path $nodeProto 'package.json') -Raw) -replace "`r", '' } else { '' }
        if ($pkgNovo -ne $pkgAtual -or -not (Test-Path (Join-Path $nodeProto 'node_modules'))) {
            Copy-Item (Join-Path $fonte 'package.json') $nodeProto -Force
            Push-Location $nodeProto
            try { & npm install --no-audit --no-fund } finally { Pop-Location }
            if ($LASTEXITCODE -ne 0) { throw "npm install falhou (código $LASTEXITCODE)" }
        }
        $id = Get-EdicaoBranchDados
        $pastaEdicao = Join-Path $repoDados "dados\publicacao\edicoes\$id"
        & $python -X utf8 (Join-Path $fonte 'dados.py') $pastaEdicao | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "dados.py terminou com código $LASTEXITCODE" }
        & $python -X utf8 (Join-Path $fonte 'montar.py') (Join-Path $nodeProto 'node_modules') | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "montar.py terminou com código $LASTEXITCODE" }
        Invoke-Git -C $wt add painel/prototipo/fonte/dados.json painel/prototipo/index.html
        & git -C $wt diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Output "Protótipo sem alterações (edição $id)."
        } else {
            Invoke-Git -C $wt commit -q -m "Protótipo: edição $id"
            Invoke-Git -C $wt push -q $RemotoJoao "HEAD:$BranchPainel"
            Write-Output "Protótipo regerado com a edição $id e enviado para $RemotoJoao/$BranchPainel."
        }
    } finally {
        Remove-WorktreeTemp 'publicar-painel'
    }
    Invoke-Git -C $raiz fetch -q $RemotoJoao $BranchPainel
}

Invoke-Git -C $raiz fetch -q origin
Write-Output ''
Write-Output '=== Edição em cada destino ==='
$destinos = [ordered]@{
    'TCC_DADOS (local)'                    = $script:edicaoLocal
    'branch dados (origin/dados)'          = Get-EdicaoNoGit 'origin/dados' 'dados/publicacao/atual.json'
    'dashboard (origin/main)'              = Get-EdicaoNoGit 'origin/main' 'deshboard/data/edicao.json'
    "João ($RemotoJoao/$BranchJoao)"       = Get-EdicaoNoGit "$RemotoJoao/$BranchJoao" 'pipeline/dados/publicacao/atual.json'
    "protótipo ($RemotoJoao/$BranchPainel)" = Get-EdicaoNoGit "$RemotoJoao/$BranchPainel" 'painel/prototipo/fonte/dados.json'
}
$destinos.GetEnumerator() | ForEach-Object { Write-Output ("{0,-36} {1}" -f $_.Key, $_.Value) }
$distintos = @($destinos.Values | Select-Object -Unique)
if ($distintos.Count -eq 1) {
    Write-Output "OK: todos os destinos na edição $($distintos[0])."
} else {
    Write-Output 'ATENÇÃO: os destinos estão em edições diferentes.'
    exit 1
}
