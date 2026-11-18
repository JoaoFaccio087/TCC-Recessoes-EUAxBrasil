<div align="center">

# Recessões dos EUA e seus efeitos no Brasil

**Business Intelligence na análise comparativa dos impactos das recessões norte-americanas sobre a economia brasileira**

Trabalho de Conclusão de Curso · Engenharia de Software · UNIVAG · 2026

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-Parquet-FFF000?logo=duckdb&logoColor=black)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)

</div>

---

## Sobre o projeto

Quando os Estados Unidos entram em recessão, o Brasil sente? Quanto, em quanto tempo e por quanto tempo?

Este projeto coleta indicadores oficiais dos dois países, alinha as séries no mês de pico de cada recessão americana datada pelo NBER e mede, para cada indicador, a **reação**, a **defasagem** entre os dois países, o **pior valor** e o **tempo de recuperação**. O resultado é apresentado em um painel web que permite comparar as três crises na mesma régua.

| Episódio | Pico (NBER) | Vale (NBER) | Contexto |
|---|---|---|---|
| 1981-1982 | jul/1981 | nov/1982 | Juros altos do Federal Reserve e crise da dívida externa |
| 2007-2009 | dez/2007 | jun/2009 | Crise financeira global |
| 2020 | fev/2020 | abr/2020 | Pandemia de covid-19 |

## Indicadores

| Grupo | Estados Unidos | Brasil |
|---|---|---|
| Produção industrial | FRED | Ipeadata e IBGE/SIDRA |
| Desemprego | FRED | Ipeadata e IBGE/SIDRA |
| Juros | FRED | Ipeadata |
| Inflação | FRED | IBGE/SIDRA |
| PIB | FRED | IBGE/SIDRA |
| Mercado acionário | FRED | Ipeadata |
| Exportações | FRED (produção industrial) | Ipeadata e Comex Stat |
| Câmbio real | sem par | FRED (OCDE) |

O detalhamento das séries, dos limiares e das regras de cálculo está no capítulo de Metodologia do texto do TCC.

## Arquitetura

```text
 Fontes oficiais            Pipeline em Python (execução semanal)              Painel web
┌──────────────┐      ┌─────────┐    ┌─────────┐    ┌─────────┐      ┌──────────────────────┐
│ FRED         │      │ Bronze  │    │ Silver  │    │  Gold   │      │ Vue 3 + TypeScript   │
│ Ipeadata     │ ───▶ │ dados   │ ─▶ │ dados   │ ─▶ │ modelo  │ ───▶ │ DuckDB-Wasm lê os    │
│ IBGE/SIDRA   │      │ brutos  │    │ tratados│    │ dimens. │      │ Parquet no navegador │
│ Comex Stat   │      └─────────┘    └─────────┘    └─────────┘      └──────────────────────┘
└──────────────┘          Agendador de Tarefas do Windows · edições analíticas versionadas
```

- **Lakehouse local em camadas (Bronze, Silver e Gold)**, com os dados guardados em Parquet.
- **Pipeline em Python**, com pandas e DuckDB, executada toda semana pelo Agendador de Tarefas do Windows.
- **Edições analíticas**: cada publicação recebe um identificador, um manifesto com hash dos arquivos e fica disponível para consulta, o que permite reproduzir qualquer análise.
- **Painel sem servidor próprio**: o navegador lê a edição publicada diretamente dos arquivos Parquet com DuckDB-Wasm.

## Estrutura do repositório

```text
.
├── documentacao/   Texto do TCC, decisões do grupo e materiais de apoio
├── pipeline/       Engenharia de dados: coleta, tratamento, modelo dimensional e publicação
└── painel/         Painel web em Vue 3 e TypeScript
```

> Em organização: o código da pipeline e do painel está sendo reunido neste repositório a partir dos repositórios de trabalho de cada frente.

## Como executar

As instruções de instalação e uso ficam no README de cada pasta:

- [`pipeline/`](pipeline/README.md): ambiente Python, chave da API do FRED, comandos e agendamento.
- [`painel/`](painel/README.md): instalação com npm e execução local.

## Equipe

| Integrante | GitHub |
|---|---|
| Arthur Napoli Di Loreto | [@Arthur-Di-Loreto](https://github.com/Arthur-Di-Loreto) |
| Gabriel Pires Correa | [@gabriel-correa11](https://github.com/gabriel-correa11) |
| João Pedro Faccio | [@JoaoFaccio087](https://github.com/JoaoFaccio087) |
| Lucas Lellis Barros | [@LucasLellisBarros0](https://github.com/LucasLellisBarros0) |
| Nicolly Mendes Cescon | [@NicollyMendes](https://github.com/NicollyMendes) |

**Orientador:** Prof. Germano Neto

Centro Universitário de Várzea Grande (UNIVAG) · Faculdade de Engenharia de Software

## Fontes de dados

- [FRED](https://fred.stlouisfed.org/), Federal Reserve Bank of St. Louis
- [Ipeadata](http://www.ipeadata.gov.br/), Instituto de Pesquisa Econômica Aplicada
- [SIDRA](https://sidra.ibge.gov.br/), Instituto Brasileiro de Geografia e Estatística
- [Comex Stat](https://comexstat.mdic.gov.br/), Ministério do Desenvolvimento, Indústria, Comércio e Serviços
- [Cronologia de ciclos de negócios](https://www.nber.org/research/business-cycle-dating), National Bureau of Economic Research

---

<div align="center">
<sub>Projeto acadêmico desenvolvido para a disciplina de Trabalho de Conclusão de Curso.</sub>
</div>
