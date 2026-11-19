# Protótipo do painel

Página única e autocontida: abra `index.html` no navegador com dois cliques. Não precisa de internet nem de servidor.

## O que a página tem

1. **Capa com o globo**: arraste para girar. Estados Unidos e Brasil abrem um painel lateral com o resumo histórico das três recessões (estopim, impacto e saída).
2. **Antes dos números**: os conceitos de pico e vale, alinhamento das crises no mês de pico e as quatro medidas (reação, defasagem, pior momento e recuperação).
3. **Explorar os dados**: gráfico EUA × Brasil por indicador e crise, medidas, as três crises lado a lado e o quadro de defasagens.

## Dados

Os números vêm da edição publicada pela pipeline (contrato v1). A edição usada fica no rodapé da página.

Para atualizar com uma edição nova:

```powershell
cd painel\prototipo\fonte
python dados.py ..\..\..\pipeline\dados\publicacao\edicoes\<id_edicao>
npm install
python montar.py
```

O `dados.py` precisa do pacote `duckdb` (`pip install duckdb`). O `montar.py` gera de novo o `painel/prototipo/index.html`.

## Arquivos

| Arquivo | Função |
|---|---|
| `index.html` | Página pronta (gerada) |
| `fonte/pagina.html` | Estrutura e estilos |
| `fonte/app.js` | Globo, painel lateral e gráficos (D3) |
| `fonte/dados.py` | Converte a edição em Parquet para `dados.json` |
| `fonte/montar.py` | Junta tudo em um único `index.html` |
| `fonte/pontos.mjs`, `fonte/alvos.mjs` | Geram os pontos do globo e os contornos de EUA e Brasil a partir do `world-atlas` |

Os textos históricos do painel lateral ficam em `fonte/app.js` (constante `HIST`).
