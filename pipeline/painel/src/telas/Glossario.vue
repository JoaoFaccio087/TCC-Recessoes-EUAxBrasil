<script setup lang="ts">
// Glossário dos termos e medidas (RNF08).
const TERMOS: [string, string][] = [
  ['Pico', 'Mês (ou trimestre) em que a atividade nos EUA atinge o ponto mais alto antes da recessão, segundo o NBER. É o momento zero do gráfico (t = 0).'],
  ['Vale', 'Mês em que a atividade nos EUA atinge o ponto mais baixo antes da retomada (NBER). A faixa cinza do gráfico vai do pico ao vale.'],
  ['Número-índice (pico = 100)', 'Usado nas séries de nível (produção, PIB, exportações, ações, câmbio). 95 significa 5% abaixo do nível do pico.'],
  ['Pontos percentuais em relação ao pico', 'Usado nas taxas (desemprego, juros, inflação). +2 significa que a taxa está 2 pontos acima da taxa do pico.'],
  ['Reação', 'Primeiro mês após o pico de uma sequência de meses seguidos além do limiar do grupo, no sentido adverso (ex.: produção industrial com índice ≤ 98 por 2 meses).'],
  ['Pior valor', 'Valor mais distante do pico, no sentido adverso, nos 24 meses seguintes ao pico.'],
  ['Variação até o pior valor', 'Diferença entre o pior valor e o pico: mede a intensidade do impacto (em % para índices, em pontos percentuais para taxas).'],
  ['Duração da queda', 'Meses do pico até o pior valor.'],
  ['Recuperação', 'Meses do pico até a série voltar ao nível do pico, depois do pior valor, e ficar nele por 2 meses seguidos (até 60 meses).'],
  ['Defasagem', 'Reação do Brasil menos reação dos EUA no mesmo par. Positiva: o Brasil reagiu depois.'],
  ['Sentido adverso', 'Direção que representa piora: queda (produção, PIB, exportações, ações, câmbio real), alta (desemprego) ou qualquer direção (juros e inflação).'],
  ['Ajuste sazonal', 'Remove oscilações que se repetem todo ano na mesma época. Quando a fonte não publica a série ajustada, o painel aplica o método STL.'],
  ['Valor real (deflacionado)', 'Valor com a inflação descontada: exportações pelo índice de preços ao consumidor dos EUA, ações pelo índice de preços de cada país.'],
  ['Edição analítica', 'Retrato congelado dos dados e métodos publicado pela pipeline. Permite reproduzir um gráfico mesmo depois de revisões nas fontes.'],
  ['Data de coleta', 'Momento em que o valor foi baixado da fonte; aparece na exportação CSV.'],
  ['Sem dados / Sem reação / Não recuperou / Não se aplica', 'Situações em que uma medida não pode ser calculada. O motivo aparece ao passar o mouse sobre o status.'],
]
</script>

<template>
  <div class="cartao">
    <h3>Glossário</h3>
    <dl class="ficha" style="grid-template-columns: 260px 1fr; gap: 10px 16px">
      <template v-for="[t, d] in TERMOS" :key="t"><dt style="color:var(--texto-1);font-weight:600">{{ t }}</dt><dd>{{ d }}</dd></template>
    </dl>
  </div>
</template>
