# Instruções: como usar os dados para análise

Este guia é para quem vai **analisar** os dados do TCC (recessões dos EUA × economia brasileira): fazer tabelas, gráficos, conferir hipóteses ou escrever o capítulo de resultados. Para operar a pipeline (coletar, reprocessar, agendar), veja o [`README.md`](README.md). As regras de cálculo e as decisões estão em [`engenharia_de_dados.md`](engenharia_de_dados.md).

Todas as consultas deste guia foram testadas na edição `20261117-2317`.

---

## 1. Onde estão os dados

Use sempre a **edição ativa da camada Gold**. Ela já passou por todos os tratamentos e validações.

Nos exemplos, troque `C:\Users\SEU_USUARIO\tcc-local\dados` pela pasta definida em `TCC_DADOS` no seu `.env` (padrão sugerido: `%USERPROFILE%\tcc-local\dados`).

```text
C:\Users\SEU_USUARIO\tcc-local\dados\publicacao\
├── atual.json                     ← diz qual é a edição ativa
├── edicoes.json                   ← lista de todas as edições publicadas
└── edicoes\20261117-2317\         ← EDIÇÃO ATIVA: 14 arquivos .parquet + manifesto.json
```

- A pasta da edição ativa muda quando a pipeline publica uma edição nova (toda segunda, 08:00, se as fontes mudarem). Confira o nome em `atual.json`.
- Uma edição **nunca muda** depois de publicada. Para reproduzir uma análise, use sempre a mesma pasta e cite o `id_edicao`.
- **Não use** `bronze\` (respostas brutas das fontes) nem `silver\` (observações antes dos tratamentos) para a análise final.

### 1.1 Sem rodar a pipeline: baixar os dados do GitHub

Quem não roda a pipeline obtém os mesmos dados no branch **`dados`** do repositório, que tem o código e a pasta `dados/` (Bronze, Silver, edições publicadas, registros de execução e relatórios de conferência):

```powershell
git clone -b dados https://github.com/LucasLellisBarros0/engenharia-de-dados-TCC.git tcc-dados
# edição ativa: tcc-dados\dados\publicacao\atual.json
# arquivos:     tcc-dados\dados\publicacao\edicoes\<id_edicao>\*.parquet
```

Nos exemplos deste guia, troque a pasta `...\tcc-local\dados` por `...\tcc-dados\dados`. Para atualizar depois: `git -C tcc-dados pull`. O branch é atualizado por quem mantém a pipeline, com `.\scripts\publicar_dados.ps1`.

## 2. Como abrir os dados

### 2.1 Python do projeto (recomendado)

O ambiente do projeto já tem `duckdb` e `pandas`. Esta função abre a edição ativa com uma tabela virtual (view) para cada arquivo:

```powershell
& $env:USERPROFILE\tcc-local\.venv\Scripts\python.exe
```

```python
from tcc_pipeline.validacao import conectar, edicao_ativa

con = conectar(edicao_ativa(r"C:\Users\SEU_USUARIO\tcc-local\dados\publicacao"))
con.sql("SHOW TABLES").df()                                   # as 14 tabelas
df = con.sql("SELECT * FROM fato_resumo_episodio").df()       # resultado em DataFrame
```

Também funciona em notebook (Jupyter ou VS Code) com o mesmo ambiente.

### 2.2 Um arquivo direto em DataFrame

```python
import duckdb
pasta = r"C:\Users\SEU_USUARIO\tcc-local\dados\publicacao\edicoes\20261117-2317"
resumo = duckdb.read_parquet(rf"{pasta}\fato_resumo_episodio.parquet").df()
series = duckdb.read_parquet(rf"{pasta}\dim_serie.parquet").df()
```

Em outro Python, com `pyarrow` instalado (`pip install pandas pyarrow`), também funciona `pd.read_parquet(caminho)`. O ambiente do projeto não tem `pyarrow`; nele, use o `duckdb` como acima.

### 2.3 DuckDB, DBeaver ou outra ferramenta SQL

Leia o arquivo direto, sem importar:

```sql
SELECT * FROM 'C:/Users/SEU_USUARIO/tcc-local/dados/publicacao/edicoes/20261117-2317/fato_resumo_episodio.parquet';
```

### 2.4 Excel ou planilha

O Excel não abre Parquet. Use o botão **Exportar CSV** do painel (`cd painel` e depois `npm run dev`). O CSV sai com o filtro da tela, a fonte, o método, a edição e a data de coleta. Também dá para gravar um CSV pelo Python: `df.to_csv("saida.csv", sep=";", index=False, encoding="utf-8-sig")`.

---

## 3. O modelo de dados (esquema em constelação)

```text
                 dim_tempo         dim_episodio        dim_metodo
                      │                  │                  │
 dim_serie ───── fato_valor_mensal / fato_valor_trimestral  │
     │           fato_serie_alinhada_mensal / _trimestral ──┘
     │           fato_resumo_episodio
     └── ponte_serie_br_eua ── fato_comparacao          dim_edicao (todas as fatos)
```

| Tabela | Uma linha por… | Use para |
|---|---|---|
| `fato_resumo_episodio` | série × recessão | **Medidas de impacto**: reação, pior valor, variação, duração da queda, recuperação |
| `fato_comparacao` | par EUA × Brasil × recessão | **Defasagem** e diferença das variações entre os dois países |
| `fato_serie_alinhada_mensal` | série × recessão × mês relativo ao pico | **Gráficos alinhados ao pico** e comparação entre recessões |
| `fato_serie_alinhada_trimestral` | série × recessão × trimestre relativo | O mesmo, para o PIB |
| `fato_valor_mensal` / `_trimestral` | série × data | Valores no calendário (original e tratado) |
| `resultado_hipotese` | hipótese | Resultado de H1 a H3 e o detalhe para conferir (medianas da H1; comparação por indicador em H2 e H3) |
| `dim_serie` | série | Nome, país, grupo, fonte, código, unidade, frequência, avisos |
| `dim_episodio` | recessão | Pico e vale (mensal e trimestral), segundo o NBER |
| `ponte_serie_br_eua` | par × recessão | Qual série do Brasil se compara com qual dos EUA em cada recessão |
| `dim_metodo` | método | Descrição dos tratamentos de cada série |
| `dim_tempo`, `dim_edicao` | data / edição | Calendário e dados da edição |
| `observacao_rejeitada` | valor reprovado | Auditoria (vazia na edição atual) |

Dicionário completo das colunas: seção 8 do `engenharia_de_dados.md`.

---

## 4. Conceitos que você precisa saber antes de analisar

### 4.1 Tempo relativo ao pico (`t_rel`)

- `t_rel = 0` é o **pico** da recessão nos EUA (NBER). `t_rel = 6` é 6 meses depois; `t_rel = -12`, 12 meses antes.
- Nas tabelas trimestrais, `t_rel` conta **trimestres**.
- Picos: **jul/1981**, **dez/2007** e **fev/2020** (no trimestral: 1981T3, 2007T4 e 2019T4).
- As tabelas alinhadas vão de −36 a +72 meses. O painel mostra de −24 a +48.

### 4.2 Três colunas de valor (não confundir)

| Coluna | O que é | Exemplo (ações do Brasil) |
|---|---|---|
| `valor_original` | O número exatamente como veio da fonte | Variação % mensal do Ibovespa |
| `valor_tratado` | Depois dos tratamentos (deflação, 12 meses, ajuste sazonal) | Ibovespa real, dez/1993 = 100 |
| `valor_painel` | `valor_tratado` normalizado pelo pico de **cada** recessão | 100 no pico; 75 = 25% abaixo do pico |

Para comparar recessões ou países, use **`valor_painel`**.

### 4.3 Nível ou taxa (`tipo_medida`)

| `tipo_medida` | Séries | `valor_painel` | `amplitude` |
|---|---|---|---|
| `nivel` | produção industrial, PIB, exportações, ações, câmbio real | número-índice, pico = 100 | em **%** |
| `taxa` | desemprego, juros, inflação | diferença em **pontos percentuais** em relação ao pico | em **p.p.** |

A coluna `unidade_amplitude` diz qual unidade vale em cada linha. **Não tire média nem mediana misturando % e p.p.** Por isso H2 e H3 comparam os episódios indicador a indicador, e cada episódio é medido a partir do próprio pico (D42).

### 4.4 As medidas (seção 7.3 do engenharia_de_dados.md)

| Coluna | Significado |
|---|---|
| `t_reacao` | Primeiro mês depois do pico de uma sequência de meses seguidos além do limiar do grupo (ex.: produção ≤ 98 por 2 meses) |
| `t_extremo` / `duracao_queda` | Mês do pior valor nos 24 meses depois do pico |
| `amplitude` | Variação entre o pico e o pior valor (negativa = queda; no desemprego, positiva = alta) |
| `t_recuperacao` | Meses do pico até voltar ao nível do pico (e ficar 2 meses), até 60 meses |
| `defasagem` (em `fato_comparacao`) | Reação do Brasil − reação dos EUA. **Positivo = Brasil reagiu depois** |

### 4.5 Valores vazios têm motivo

Um valor nulo nunca é "zero". O motivo está nas colunas de status:

| Status | Significado |
|---|---|
| `OK` | Calculado |
| `SEM_DADOS` | Não há série ou observação (ex.: PIB do Brasil em 1981-1982) |
| `REACAO_NAO_OBSERVADA` | A série não passou do limiar nos 24 meses depois do pico |
| `RECUPERACAO_NAO_OBSERVADA` | Não voltou ao nível do pico em 60 meses |
| `NAO_APLICAVEL` | Pior valor e recuperação de juros e inflação (podem reagir nos dois sentidos) |
| `COBERTURA_INSUFICIENTE`, `REJEITADO`, `INCOMPATIVEL` | Lacunas, valor reprovado na validação, série sem par |

### 4.6 O Brasil muda de série entre recessões

A produção industrial e o desemprego brasileiros vêm de pesquisas diferentes em cada recessão. Para comparar EUA × Brasil, use sempre a `ponte_serie_br_eua`, que diz qual série vale em cada recessão.

| Grupo | EUA | 1981-1982 | 2007-2009 | 2020 |
|---|---|---|---|---|
| Produção industrial | `eua_prod_ind` | `br_prod_ind_antiga` | `br_prod_ind` | `br_prod_ind` |
| Desemprego | `eua_desemprego` | `br_desemprego_pme_antiga` | `br_desemprego_pme_nova` | `br_desemprego_pnadc` |
| Juros | `eua_juros` | `br_juros` | `br_juros` | `br_juros` |
| Inflação (12 meses) | `eua_inflacao` | `br_inflacao` | `br_inflacao` | `br_inflacao` |
| PIB (trimestral) | `eua_pib` | sem dados | `br_pib_trim` | `br_pib_trim` |
| Ações (reais) | `eua_acoes` | `br_acoes` | `br_acoes` | `br_acoes` |
| Exportações totais × produção dos EUA | `eua_prod_ind` | `br_export_total` | `br_export_total` | `br_export_total` |
| Exportações para os EUA × produção dos EUA | `eua_prod_ind` | sem dados | `br_export_eua` | `br_export_eua` |
| Câmbio real (sem par) | — | `br_cambio_real` | `br_cambio_real` | `br_cambio_real` |

`br_pib_anual` (variação anual) só aparece na ficha do indicador, fora das medidas.

---

## 5. Receitas prontas (testadas)

Todas usam a conexão `con` da seção 2.1. Troque `.df()` por `.fetchall()` se preferir listas.

### 5.1 Medidas de impacto de um grupo nas três recessões

```python
con.sql("""
SELECT r.id_episodio, s.pais, s.nome, r.t_reacao, r.t_extremo,
       ROUND(r.amplitude, 1) AS variacao, r.unidade_amplitude, r.t_recuperacao,
       r.status_reacao, r.status_recuperacao
FROM fato_resumo_episodio r JOIN dim_serie s USING (id_serie)
WHERE s.grupo = 'producao_industrial'
ORDER BY r.id_episodio, s.pais
""").df()
```

Grupos: `producao_industrial`, `desemprego`, `juros`, `inflacao`, `pib`, `acoes`, `exportacoes`, `cambio_real`.

### 5.2 Defasagem Brasil − EUA de todos os pares

```python
con.sql("""
SELECT id_par, id_episodio, defasagem, unidade_defasagem,
       ROUND(dif_amplitude, 1) AS dif_variacao, status
FROM fato_comparacao
ORDER BY id_par, id_episodio
""").df()
```

### 5.3 Série EUA × Brasil alinhada ao pico, em formato largo (uma coluna por país)

Bom para gráfico ou para levar ao Excel.

```python
largo = con.sql("""
PIVOT (
  SELECT a.t_rel, s.pais, a.valor_painel
  FROM fato_serie_alinhada_mensal a
  JOIN ponte_serie_br_eua p
    ON a.id_episodio = p.id_episodio AND a.id_serie IN (p.id_serie_eua, p.id_serie_br)
  JOIN dim_serie s USING (id_serie)
  WHERE p.id_par = 'producao_industrial' AND a.id_episodio = '2020'
    AND a.t_rel BETWEEN -24 AND 48
) ON pais USING first(valor_painel) ORDER BY t_rel
""").df()
```

Para o PIB, troque para `fato_serie_alinhada_trimestral` e use a janela de −8 a 16.

### 5.4 Uma série nas três recessões (uma coluna por recessão)

```python
con.sql("""
PIVOT (
  SELECT t_rel, id_episodio, valor_painel
  FROM fato_serie_alinhada_mensal
  WHERE id_serie = 'eua_desemprego' AND t_rel BETWEEN -24 AND 48
) ON id_episodio USING first(valor_painel) ORDER BY t_rel
""").df()
```

### 5.5 Comparação de H2 e H3 por indicador (reproduz o resultado oficial)

Regra da D42 (seção 7.6 do `engenharia_de_dados.md`): em cada indicador (produção industrial, desemprego e exportações totais), a série brasileira de cada episódio vem da ponte, e cada episódio é medido a partir do próprio pico. "Não recuperou" conta como o fim da janela (60 meses). A condição é atendida se o episódio esperado vencer sozinho na maioria estrita dos indicadores comparáveis (mínimo 2); empate não conta a favor.

```python
con.sql("""
PIVOT (
  SELECT p.id_par AS indicador, p.id_episodio,
         ROUND(ABS(r.amplitude), 1) AS intensidade,
         CASE r.status_recuperacao WHEN 'OK' THEN r.t_recuperacao
              WHEN 'RECUPERACAO_NAO_OBSERVADA' THEN 60 END AS recuperacao
  FROM ponte_serie_br_eua p
  LEFT JOIN fato_resumo_episodio r
         ON r.id_serie = p.id_serie_br AND r.id_episodio = p.id_episodio
  WHERE p.id_par IN ('producao_industrial', 'desemprego', 'exportacoes_total')
) ON id_episodio USING first(intensidade) AS int, first(recuperacao) AS rec
ORDER BY indicador
""").df()
```

Resultado esperado na edição `20261123-2037` (intensidade em % do pico, ou p.p. no desemprego; recuperação em meses):

| Indicador | 1981-1982 | 2007-2009 | 2020 |
|---|---|---|---|
| Produção industrial | 8,4 · 33 | 15,2 · 24 | **26,0 · 7** |
| Desemprego | 0,7 · 7 | 0,0 · **1** | **3,6** · 23 |
| Exportações totais | **26,1 · 34** | 23,0 · 27 | 12,4 · **10** |

Intensidade: 2020 vence em 2 de 3 indicadores. Recuperação mais rápida: 2020 em 2 de 3. Recuperação mais lenta: 1981-1982 em 2 de 3. É o mesmo que está em `resultado_hipotese` (H2 e H3 sustentadas).

### 5.6 Resultado das hipóteses

```python
con.sql("SELECT hipotese, resultado, n_pares, detalhe FROM resultado_hipotese ORDER BY hipotese").df()
```

`detalhe` é um JSON (`json.loads` no Python). Na H1: pares considerados, pares elegíveis e medianas. Na H2 e na H3: as condições, cada uma com os indicadores, as séries usadas em cada episódio, os valores, o vencedor, o empate e o motivo de exclusão.

### 5.7 Valores no calendário (original × tratado, com data de coleta)

```python
con.sql("""
SELECT data_ref, valor_original, valor_tratado, coletado_em
FROM fato_valor_mensal
WHERE id_serie = 'br_juros' AND data_ref BETWEEN '2007-10-01' AND '2008-03-01'
ORDER BY data_ref
""").df()
```

### 5.8 Onde há lacunas

```python
con.sql("""
SELECT id_episodio, id_serie, COUNT(*) AS meses_sem_valor, MIN(t_rel) AS de, MAX(t_rel) AS ate
FROM fato_serie_alinhada_mensal
WHERE valor_painel IS NULL AND t_rel BETWEEN -24 AND 48
GROUP BY ALL ORDER BY 1, 2
""").df()
```

Na edição atual, só três séries de 1981-1982 têm meses vazios, todos **antes** do pico: inflação do Brasil (17 meses), Ibovespa (5) e PME antiga (6).

### 5.9 Como cada série foi tratada

```python
con.sql("""
SELECT DISTINCT r.id_serie, m.descricao
FROM fato_resumo_episodio r JOIN dim_metodo m USING (id_metodo)
ORDER BY 1
""").df()
```

### 5.10 Gráfico rápido no Python

O ambiente do projeto não tem `matplotlib`. Instale uma vez (`& $env:USERPROFILE\tcc-local\.venv\Scripts\python.exe -m pip install matplotlib`) e use o `largo` da receita 5.3:

```python
import matplotlib.pyplot as plt
ax = largo.plot(x="t_rel", y=["EUA", "BR"], color=["#2a78d6", "#eb6834"], linewidth=2)
ax.axvline(0, linestyle="--", color="gray"); ax.axhline(100, color="lightgray")
ax.set_xlabel("Meses desde o pico"); ax.set_ylabel("Número-índice (pico = 100)")
ax.set_title("Produção industrial — 2020"); plt.show()
```

Use as mesmas cores do painel (azul = EUA, laranja = Brasil): são distinguíveis por pessoas com daltonismo (RNF09). Coloque título, unidade e fonte em todo gráfico do texto.

---

## 6. Cuidados (leia antes de tirar conclusões)

1. **Não misture mensal e trimestral.** O PIB está nas tabelas trimestrais, e o `t_rel` dele conta trimestres.
2. **Sempre compare pela ponte.** O Brasil usa séries diferentes em cada recessão (seção 4.6).
3. **Nulo não é zero.** Leia o status (seção 4.5).
4. **Juros de 1981-1982 são nominais** e acompanham a inflação alta da época. Por isso ficam fora de H1.
5. **Selic com ruído (pendência).** A série Over/Selic do Ipeadata oscila cerca de 1 p.p. de um mês para o outro sem mudança da Selic meta (ex.: 4,66% em jan/2020 e 3,54% em fev/2020, enquanto a meta era 4,50% e 4,25%). Até isso ser resolvido, trate as medidas de reação dos juros brasileiros com cautela (`PENDENCIAS.md`, item 1.5).
6. **Reação em 1981-1982 (pendência).** A produção industrial brasileira já estava caindo antes do pico dos EUA, e a reação só é buscada depois do pico. A defasagem de +14 meses nesse episódio superestima o atraso do Brasil (`PENDENCIAS.md`, item 1.1).
7. **2020 foi um choque global e simultâneo.** Defasagem pequena nesse episódio não indica, sozinha, maior integração financeira.
8. **Três recessões não provam causa.** Os resultados mostram diferenças e associações no tempo (texto 7.5).
9. **Os valores podem ser revisados pelas fontes.** Cada valor tem `coletado_em`. Cite sempre a edição usada.

## 7. Como citar e reproduzir

No texto, em tabelas ou figuras, informe:

> Fonte: elaborado pelos autores com dados de FRED, Ipeadata, IBGE/SIDRA e Comex Stat (edição analítica 20261117-2317, data de corte 17/11/2026). Picos e vales: NBER.

Para reproduzir uma análise antiga, abra a pasta da edição citada em vez da ativa:

```python
from pathlib import Path
con = conectar(Path(r"C:\Users\SEU_USUARIO\tcc-local\dados\publicacao\edicoes\20261117-2303"))
```

Para ter dados novos, quem mantém a pipeline roda `.\scripts\executar_pipeline.ps1 atualizar`, ou espera a execução semanal. Se as fontes não mudaram, nenhuma edição nova é publicada.
