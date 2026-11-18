# Pendências do projeto

**Atualizado em 18/11/2026.** Situação: a pipeline está completa, com dados reais das 4 fontes, as 3 recessões, a edição publicada em Parquet, o painel de referência, o agendamento e a conferência dos dados (117 de 117 pontos conferem). Detalhes das decisões em [`engenharia_de_dados.md`](engenharia_de_dados.md) (D0 a D36).

Legenda de prioridade: 🔴 alta (afeta resultado ou risco de perda) · 🟡 média · 🟢 baixa.

---

## 1. Decisões do grupo (metodologia)

| # | Prioridade | Pendência | Responsável |
|---|---|---|---|
| 1.1 | 🔴 | **Reação antes do pico em 1981-1982 (afeta H1).** A reação só é buscada depois do pico (t > 0). A produção industrial brasileira já tinha caído cerca de 15% entre out/1980 e jul/1981, antes do pico dos EUA, e a pipeline registra reação em t = 18 e defasagem de +14 meses ("Brasil reagiu depois"). Isso favorece H1 justamente no episódio que dá o ponto de partida. Opções: (a) registrar como limitação no 7.5; (b) marcar "reação anterior ao pico" quando a série já estiver além do limiar em t = 0; (c) buscar a reação também antes do pico. Decidir pelo método, não pelo resultado | Grupo |
| 1.2 | 🔴 | **H1 inconclusiva com os dados reais.** Só 2 pares (produção industrial e inflação) têm reação nos três episódios, e o critério exige 3. Nos dois, a defasagem cai (14 → 6 → 0 e 3 → 2 → 0). Não ajustar limiares para mudar o resultado; se quiser mostrar outros parâmetros, apresentar como análise de sensibilidade (texto 7.4) | Grupo |
| 1.3 | 🟡 | **Unidades misturadas nas medianas de H2 e H3:** variação em % (índices) e em p.p. (desemprego); recuperação em trimestres (PIB) e em meses (demais). Também falta dizer se "exportações" em H2 e H3 são as totais, as para os EUA ou ambas (hoje: só as totais) | Grupo |
| 1.5 | 🔴 | **Ruído na série Over/Selic do Ipeadata (`PAN12_TJOVER12`).** A taxa "anualizada pelo Ipea" oscila cerca de 1 a 1,7 p.p. de um mês para o outro sem mudança da Selic meta: out/2007 a mar/2008 vai de 10,0% a 11,7% (meta parada em 11,25%); jan/2020 = 4,66% e fev/2020 = 3,54% (meta 4,50% e 4,25%). O limiar de reação dos juros é 1 p.p., então o ruído pode criar ou deslocar reações (2020: o pico ficou em 3,54%, abaixo da meta, e a reação saiu em t = 5). Verificar no Ipeadata uma série mensal sem esse efeito (taxa acumulada no mês convertida por 252 dias úteis, ou a meta) e registrar a escolha como decisão nova | Lucas + Grupo |
| 1.4 | 🟢 | Termo do processo: o texto usa "ETL" (2.1.5), mas a solução é **ELT** em camadas (bruto gravado no Bronze antes de transformar). Ajustar a palavra ou explicar | Grupo / João |

## 2. Texto oficial ("Cópia de Documentação - TCC")

| # | Prioridade | Pendência | Responsável |
|---|---|---|---|
| 2.1 | 🔴 | **Figura 3 desatualizada em relação ao contrato.** Faltam: `coletado_em` nas tabelas alinhadas (RNF01); `inicio_disponivel`, `fim_disponivel` e `aviso_metodologia` na `dim_serie` (RF11); `data_ref`, `valor_tratado` e `motivo` nas alinhadas; `valor_pico`, `status_reacao`, `duracao_queda`, `unidade_amplitude` e `cobertura` no resumo; `frequencia`, `unidade_defasagem` e `motivo` na comparação; `fonte` e `data_consulta` na `dim_episodio`. Completar a figura ou dizer na legenda que ela mostra os campos principais | João |
| 2.2 | 🟡 | **2.2.3** trata o SGS como fonte de dados ("os utiliza como fonte"), o que contradiz a D13. Deixar o SGS só como portal correlato | João |
| 2.3 | 🟡 | **2.1.3** promete acompanhar "no painel" a participação dos EUA e da China nas exportações, preços de commodities e fluxos de capital, que não estão no mapa. Tirar a promessa ou incluir séries (a participação dos EUA sai das séries atuais; a da China é uma consulta a mais no Comex Stat; as outras duas exigem séries novas) | João + Lucas |
| 2.4 | 🟢 | **2.1.2** diz que o canal dos juros aparece "no endividamento externo", que ficou fora do mapa (Q3) | João |
| 2.5 | 🟢 | **2.1.6** fala em tratamento específico para o saldo comercial, que não existe no mapa | João |
| 2.6 | 🟢 | **2.1.5** lista "país" e "fonte" como dimensões; no modelo são colunas da `dim_serie` | João |
| 2.7 | 🟡 | **Quadro 6:** confirmar a cobertura conferida em 17/11 (D28). Ressalvas a citar: PME antiga começa em 1980-01; IPCA em 1979-12 (inflação em 12 meses só a partir de 1980-12; Ibovespa real a partir de 1979-12). Os meses faltantes são todos anteriores ao pico de 1981 e não afetam as medidas | João |
| 2.8 | 🟢 | **7.3:** a conversão do Over/Selic é condicional ("quando divulgada em % ao mês"). O Ipeadata já entrega em % a.a.; pode-se simplificar o trecho | João |

## 3. Avaliação (etapa 7 do TCC II)

| # | Prioridade | Pendência | Responsável |
|---|---|---|---|
| 3.1 | 🔴 | **Aplicar o SUS** com usuários (roteiro, tarefas e questionário em [`avaliacao/sus_roteiro.md`](avaliacao/sus_roteiro.md)) e definir o número de participantes com o orientador. Pontuar com `.\scripts\executar_pipeline.ps1 sus avaliacao\respostas_sus.csv` | Grupo + Prof. Germano |
| 3.2 | 🟡 | Revisar a **tradução do questionário** (é de trabalho) ou adotar uma versão validada em português e citá-la | Grupo |
| 3.3 | 🟡 | Conferir as **médias da escala de Bangor, Kortum e Miller (2009)** usadas em `src/tcc_pipeline/sus.py` com a tabela do artigo antes de citar no texto | Lucas |
| 3.4 | 🟢 | Fazer a **conferência manual** dos pontos sugeridos no relatório de `conferir` (abrir o site de cada fonte e anotar quem conferiu e quando). Relatório: `<TCC_DADOS>\conferencia\20261117-233558.md` | Lucas / João |
| 3.5 | 🟢 | Se a edição mudar antes das sessões, reconferir as respostas esperadas das tarefas T1 a T6 | Moderador |

## 4. Painel (frente do Gabriel e do Arthur)

| # | Prioridade | Pendência | Responsável |
|---|---|---|---|
| 4.1 | 🟡 | Revisar o visual e a navegação do painel de referência em `painel/` e evoluir a partir dele | Gabriel e Arthur |
| 4.2 | 🟡 | **Publicar o painel para acesso externo** (hoje só roda nesta máquina). É um site estático: `painel\dist` + a pasta `publicacao` em `/dados/`. Escolher a hospedagem gratuita (RNF13) | Gabriel e Arthur + Lucas |
| 4.3 | 🟢 | Testar em 1366 × 768 (RNF10) e no modo claro (o desenvolvimento foi visto no modo escuro) | Gabriel e Arthur |
| 4.4 | 🟢 | Manter o suporte a `id_edicao` com sufixo (`20261118-1000-2`, D31) se o seletor de edição for refeito | Gabriel e Arthur |

## 5. Engenharia de dados (Lucas)

| # | Prioridade | Pendência | Responsável |
|---|---|---|---|
| 5.1 | 🔴 | **Primeiro commit no Git.** Nada está versionado ainda; é o maior risco de perda. `.env`, `painel/node_modules` e `painel/dist` já estão fora pelos `.gitignore` | Lucas |
| 5.2 | 🟡 | **Demonstrar ao vivo o cenário de falha** (Quadro 8, etapa 5): validação reprovada e painel mantendo a edição anterior. Hoje está coberto só por testes automatizados | Lucas |
| 5.3 | 🟡 | Implementar o ajuste que o grupo decidir nos itens 1.1 e 1.3 (regras em `config/regras.yaml`, cálculo em `metricas.py` e `hipoteses.py`) e reprocessar (`reprocessar`, sem nova coleta) | Lucas |
| 5.4 | 🟢 | Opcional: comando que gera um arquivo `.duckdb` com views sobre a edição ativa, para consulta no DBeaver ou no DuckDB UI (os Parquet continuam sendo a fonte oficial) | Lucas |
| 5.5 | 🟢 | Acompanhar a primeira execução agendada (segunda, 23/11, 08:00) na aba Manutenção | Lucas |

## 6. Cronograma

| # | Prioridade | Pendência | Responsável |
|---|---|---|---|
| 6.1 | 🟡 | Definir as datas das etapas do TCC II (Quadro 8) | Grupo + Prof. Germano |

---

**Ao concluir um item:** riscar aqui e, se mudar mapa, regra ou contrato, registrar uma decisão nova na seção 2 do `engenharia_de_dados.md` (regra da seção 12).
