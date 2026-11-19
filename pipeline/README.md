# TCC: recessões EUA × Brasil (frente de engenharia de dados)

O documento de referência é o [`engenharia_de_dados.md`](engenharia_de_dados.md). Ele reúne as decisões, o mapa das séries, as regras de cálculo e o contrato de saída v1.

## Instalação (Windows, Python 3.13)

O código fica nesta pasta, que está no OneDrive. O ambiente virtual e os dados ficam fora dele, em `%USERPROFILE%\tcc-local\`, para evitar conflitos de sincronização e problemas com o lock.

```powershell
py -3.13 -m venv $env:USERPROFILE\tcc-local\.venv
& $env:USERPROFILE\tcc-local\.venv\Scripts\python.exe -m pip install -e .[dev]
copy .env.example .env   # preencher FRED_API_KEY, TCC_DADOS e TCC_VENV
```

O `.env` não entra no Git. Ele define:

| Variável | Uso |
|---|---|
| `FRED_API_KEY` | Chave da API do FRED, obrigatória para as séries dos EUA |
| `TCC_DADOS` | Pasta de dados: Bronze, Silver, publicação, controle e lock (padrão: `./dados`) |
| `TCC_VENV` | Ambiente virtual usado por `scripts\executar_pipeline.ps1` (padrão: `./.venv`) |

## Comandos

O script `scripts\executar_pipeline.ps1` chama o Python do `TCC_VENV`. É o mesmo comando usado pelo Agendador de Tarefas.

```powershell
.\scripts\executar_pipeline.ps1 atualizar --series eua_prod_ind,br_prod_ind --episodios 2007-2009,2020   # PoC
.\scripts\executar_pipeline.ps1 reprocessar --series eua_prod_ind,br_prod_ind --episodios 2007-2009,2020
.\scripts\executar_pipeline.ps1 validar
.\scripts\executar_pipeline.ps1 gerar-exemplo     # edição sintética em <TCC_DADOS>\exemplo\publicacao
.\scripts\executar_pipeline.ps1 conferir          # compara a edição ativa com as fontes (RNF03)
.\scripts\executar_pipeline.ps1 sus avaliacao
espostas_sus.csv   # pontua o SUS (RNF06)
& $env:USERPROFILE\tcc-local\.venv\Scripts\python.exe -m pytest
```

- `atualizar`: lock, coleta (Bronze), Silver, Gold, validação, publicação e registro.
- `reprocessar`: o mesmo fluxo sem a coleta. A Silver e a Gold são refeitas a partir do Bronze.
- Sem `--series` e `--episodios`, os comandos usam todas as séries e episódios. As quatro fontes (FRED, Ipeadata, IBGE/SIDRA e Comex Stat) têm conector, e a coleta completa leva cerca de 1 minuto.
- Com `--series`, os deflatores de que as séries precisam (`eua_cpi`, `br_ipca_indice`) entram no recorte automaticamente.
- Os tratamentos (desconto da inflação, 12 meses, STL) são declarados por série em `config/series.yaml` (`tratamentos`) e ficam em `src/tcc_pipeline/tratamentos.py`. Se uma série de um grupo que exige tratamento não declarar o tratamento, a execução falha e nada é publicado.

### O que fica em `TCC_DADOS`

```text
.lock                             # existe só durante atualizar/reprocessar (D14, D22)
controle/<id_execucao>.json       # um registro por execução (D23)
bronze/<fonte>/<id_serie>/<coleta_utc>.json
bronze/_manifestos/<id_execucao>.json
silver/observacao.parquet | observacao_rejeitada.parquet | serie_metadado.parquet
publicacao/atual.json | edicoes.json | controle_execucao.parquet | edicoes/<id_edicao>/
exemplo/publicacao/...            # edição sintética
conferencia/<instante>.md | .csv  # relatórios do comando conferir
```

## Agendamento (Agendador de Tarefas do Windows)

```powershell
powershell -ExecutionPolicy Bypass -File .\scriptsgendar_tarefa.ps1                 # segunda, 08:00
powershell -ExecutionPolicy Bypass -File .\scriptsgendar_tarefa.ps1 -Dia Friday -Hora 19:00
powershell -ExecutionPolicy Bypass -File .\scriptsgendar_tarefa.ps1 -Remover
Start-ScheduledTask -TaskName 'TCC - atualizar dados (recessoes EUA x Brasil)'   # rodar agora
```

A tarefa roda `atualizar` toda semana. Ela não inicia uma segunda instância se outra estiver rodando, e roda assim que possível se o computador estava desligado no horário. O resultado de cada execução aparece na aba **Manutenção** do painel.

## Painel (Vue 3 + TypeScript + DuckDB-Wasm)

```powershell
cd painel
npm install        # node_modules é uma junção para %USERPROFILE%\tcc-local\painel_node_modules (fora do OneDrive)
npm run dev        # http://localhost:5173
npm run build      # gera painel\dist
```

O Vite serve `<TCC_DADOS>\publicacao` em `/dados/`, e o painel lê a edição ativa direto dos Parquet, sem API própria. Para abrir a edição sintética, defina `TCC_PUBLICACAO=<TCC_DADOS>\exemplo\publicacao` antes do `npm run dev`. Para publicar fora da máquina, sirva `painel\dist` e copie a pasta `publicacao` para `dist\dados` (ou defina `VITE_DADOS_URL` no build).

Na primeira instalação em outra máquina, crie a junção antes do `npm install`:
`cmd /c mklink /J painel\node_modules %USERPROFILE%\tcc-local\painel_node_modules`.

Abas: EUA × Brasil (RF07, RF08, RF11, RF12, RF15), Comparar episódios (RF09), Quadro-resumo (RF10), Hipóteses (7.5), Manutenção (RF13) e Glossário (RNF08). O rodapé mostra o tempo de carga e o da última consulta (RNF05).

## Dados no GitHub (branch `dados`)

Os dados não vão para o `main`. O branch `dados` tem o código e a pasta `dados/`, uma cópia de `TCC_DADOS` sem a trava e sem a edição sintética. Para atualizá-lo depois de uma edição nova:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publicar_dados.ps1          # mescla o main, copia os dados, faz commit e envia
powershell -ExecutionPolicy Bypass -File .\scripts\publicar_dados.ps1 -SemEnviar
```

O script usa um worktree em `%USERPROFILE%\tcc-local\repo-dados` (fora do OneDrive) e não roda enquanto a pipeline estiver com a trava. Como obter os dados sem rodar a pipeline: [`INSTRUCOES.md`](INSTRUCOES.md), seção 1.1.

### Publicar tudo de uma vez (D39)

Depois de conferir uma edição nova, um comando atualiza todos os destinos, na ordem, e para no primeiro erro:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publicar_tudo.ps1
```

1. branch `dados` (`publicar_dados.ps1`);
2. dashboard (`deshboard\alimentar_dashboard.py`), que lê os dados do branch `dados` (worktree `TCC_REPO_DADOS`, padrão `%USERPROFILE%\tcc-local\repo-dados`); se mudou, commit e push do `main` e novo `publicar_dados.ps1`;
3. branch `pipeline` do repositório oficial (JoaoFaccio087/TCC-Recessoes-EUAxBrasil): o `main` entra em `pipeline/` por `git subtree`, com histórico, e `pipeline/dados/` recebe a cópia do branch `dados` (D41);
4. protótipo do painel (branch `painel` do repositório oficial): `dados.py` e `montar.py` regeram `painel/prototipo/index.html` com a edição ativa. As dependências npm ficam em `TCC_PROTOTIPO_NODE` (padrão `%USERPROFILE%\tcc-local\prototipo-node`, fora do OneDrive) e são instaladas na primeira vez.

No fim, o script mostra o `id_edicao` de cada destino. Ele faz push do `main` logo no início e **não** é chamado pelo `atualizar` nem pelo Agendador: rode à mão.

## Avaliação (SUS e conferência dos dados)

O roteiro, as tarefas, o questionário e o modelo de respostas ficam em [`avaliacao/`](avaliacao/sus_roteiro.md).

## Edição sintética (para o painel)

O comando `gerar-exemplo` publica uma edição completa no contrato v1 (seção 8). **Os valores são sintéticos**: os métodos aparecem como `sintetico_*` e `dim_edicao.versao_codigo = exemplo-sintetico`.

A edição traz de propósito alguns casos para o painel testar os estados da seção 7.7:

- um mês `REJEITADO` (`br_desemprego_pme_antiga`, 1981-1982, t_rel 3);
- uma lacuna (`br_acoes`, 1981-1982, t_rel 5);
- uma série sem recuperação (`br_prod_ind_antiga`, 1981-1982);
- dois pares `SEM_DADOS` em 1981-1982 (PIB e exportações para os EUA).

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | OK (`SUCESSO` ou `SEM_ALTERACOES`) |
| 1 | Falha (coleta, tratamento ou erro inesperado). Nada é publicado. |
| 2 | Validação reprovada. Nada é publicado. |
| 3 | Bloqueado pelo lock de outra execução |
