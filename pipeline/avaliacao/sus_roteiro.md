# Avaliação de usabilidade do painel (SUS) — roteiro de aplicação

Referências: questionário System Usability Scale (BROOKE, 1996); interpretação pela escala de adjetivos de Bangor, Kortum e Miller (2009). Meta do **RNF06**: média ≥ 70. Texto oficial, seção 7.6.

## 1. Preparação (moderador)

1. Abrir o painel na edição ativa (`npm run dev` em `painel/` e acessar http://localhost:5173), em tela de pelo menos 1366 × 768 (RNF10).
2. Começar cada sessão pela aba **EUA × Brasil**, com o filtro padrão (produção industrial, 2007-2009).
3. Anotar para cada participante: código (P01, P02...), perfil (estudante, professor, pesquisador; área), data, tempo por tarefa e se concluiu sem ajuda.
4. Não explicar o painel antes das tarefas. Se o participante travar por mais de 2 minutos, registrar "com ajuda" e seguir.

## 2. Tarefas representativas (texto 7.6)

| # | Tarefa | Concluída quando |
|---|---|---|
| T1 | Compare a produção industrial dos EUA e do Brasil na recessão de 2020. Quantos meses depois do pico cada país reagiu? | Diz 1 mês para os dois (defasagem 0) |
| T2 | Na aba de comparação de episódios, veja a produção industrial do Brasil. Em qual episódio a queda foi mais intensa? | Diz 2020 (−26 %) |
| T3 | No quadro-resumo, encontre em quanto tempo o desemprego dos EUA voltou ao nível do pico na recessão de 1981-1982. | Diz 43 meses |
| T4 | Descubra de que fonte vem a série de exportações do Brasil para os EUA e desde quando ela existe. | Diz Comex Stat, desde 1997 (aviso da ficha, aba EUA × Brasil, par de exportações para os EUA) |
| T5 | Exporte em CSV os dados do PIB dos EUA e do Brasil em 2007-2009, de 12 meses antes a 24 meses depois do pico. | Arquivo CSV baixado com o filtro aplicado |
| T6 | Por que não há comparação do PIB brasileiro em 1981-1982? | Lê o aviso: sem PIB trimestral antes de 1996 |

As respostas esperadas valem para a edição `20261117-2317`. Se a edição mudar, conferir os números antes da sessão.

## 3. Questionário (logo após as tarefas)

Instrução ao participante: *"Para cada afirmação, marque de 1 (discordo totalmente) a 5 (concordo totalmente). Responda pela sua primeira impressão. Se não souber responder, marque 3."*

| # | Afirmação | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Eu acho que gostaria de usar este sistema com frequência. | | | | | |
| 2 | Eu achei o sistema desnecessariamente complexo. | | | | | |
| 3 | Eu achei o sistema fácil de usar. | | | | | |
| 4 | Eu acho que precisaria da ajuda de uma pessoa com conhecimentos técnicos para usar o sistema. | | | | | |
| 5 | Eu achei que as várias funções do sistema estão bem integradas. | | | | | |
| 6 | Eu achei que o sistema apresenta muita inconsistência. | | | | | |
| 7 | Eu imagino que a maioria das pessoas aprenderia a usar este sistema rapidamente. | | | | | |
| 8 | Eu achei o sistema muito complicado de usar. | | | | | |
| 9 | Eu me senti muito confiante usando o sistema. | | | | | |
| 10 | Eu precisei aprender muitas coisas antes de conseguir usar o sistema. | | | | | |

A tradução acima é de trabalho. Se o grupo citar uma versão validada em português, substituir o texto dos itens e registrar a referência no texto do TCC.

## 4. Registro e pontuação

Lançar as respostas em `avaliacao/respostas_sus.csv` (modelo: `respostas_sus_modelo.csv`), uma linha por participante, e rodar:

```powershell
.\scripts\executar_pipeline.ps1 sus avaliacao\respostas_sus.csv
```

A saída traz a pontuação de cada participante (0 a 100), a média, o desvio padrão, a mediana, o adjetivo de Bangor, Kortum e Miller (2009) e se o RNF06 foi atendido. O número de participantes não está fixado no texto: definir com o orientador.

## 5. Conferência dos dados (RNF03)

Antes das sessões, rodar a conferência automática e a manual sugerida no relatório:

```powershell
.\scripts\executar_pipeline.ps1 conferir
```

O relatório (`<TCC_DADOS>\conferencia\<instante>.md`) lista o resultado de cada ponto (pico, pior valor e fim da janela de cada série e episódio) e uma tabela de pontos para conferir a olho no site de cada fonte, com espaço para quem conferiu e quando.
