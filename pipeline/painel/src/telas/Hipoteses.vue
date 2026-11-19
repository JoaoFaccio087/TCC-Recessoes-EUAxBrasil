<script setup lang="ts">
// Resultado das hipóteses H1 a H3 (texto 7.5), com as medianas e as ressalvas do texto.
import { onMounted, ref, watch } from 'vue'
import Status from '../componentes/Status.vue'
import { consultar, type Linha } from '../dados'
import { estado, medir } from '../estado'
import { num } from '../textos'

const ENUNCIADO: Record<string, string> = {
  H1: 'O intervalo entre a reação dos indicadores norte-americanos e a dos brasileiros diminuiu ao longo dos três episódios.',
  H2: 'A recessão de 2020 teve a queda mais intensa e a recuperação mais rápida entre os três episódios.',
  H3: 'A recessão de 1981-1982 produziu os efeitos mais prolongados sobre a economia brasileira.',
}
const CRITERIO: Record<string, string> = {
  H1: 'Sustentada se a mediana da defasagem, em valor absoluto, cair de 1981-1982 para 2007-2009 e de 2007-2009 para 2020, nos pares com reação nos três episódios. Com menos de 3 pares elegíveis, inconclusiva.',
  H2: 'Sustentada se 2020 tiver, ao mesmo tempo, a maior mediana da variação até o pior valor e a menor mediana do tempo de recuperação nas séries brasileiras de atividade.',
  H3: 'Sustentada se 1981-1982 tiver a maior mediana do tempo de recuperação nas mesmas séries de H2. Sem recuperação na janela conta como o fim da janela (60 meses).',
}
const NOMES: Record<string, string> = {
  pares_elegiveis: 'Pares elegíveis', mediana_abs_defasagem: 'Mediana da defasagem (valor absoluto)',
  mediana_abs_amplitude: 'Mediana da variação até o pior valor (valor absoluto)',
  mediana_recuperacao: 'Mediana do tempo de recuperação', nota: 'Nota',
}
const linhas = ref<Linha[]>([])
async function carregar() {
  await medir(async () => { linhas.value = await consultar(`SELECT * FROM resultado_hipotese ORDER BY hipotese`) })
}
onMounted(carregar)
watch(() => estado.versao, carregar)

function detalhe(l: Linha): [string, unknown][] {
  try { return Object.entries(JSON.parse(String(l.detalhe ?? '{}'))) } catch { return [] }
}
function valor(v: unknown): string {
  if (Array.isArray(v)) return v.join(', ')
  if (v && typeof v === 'object') return Object.entries(v).map(([k, x]) => `${k}: ${num(x)}`).join(' · ')
  return String(v)
}
</script>

<template>
  <div v-for="l in linhas" :key="String(l.hipotese)" class="cartao">
    <h3>{{ l.hipotese }} — <Status :codigo="l.resultado as string" /></h3>
    <p style="margin:0 0 6px">{{ ENUNCIADO[String(l.hipotese)] }}</p>
    <p class="muted" style="margin:0 0 8px">Critério: {{ CRITERIO[String(l.hipotese)] }} Casos considerados: {{ l.n_pares }}.</p>
    <dl class="ficha">
      <template v-for="[k, v] in detalhe(l)" :key="k"><dt>{{ NOMES[k] ?? k }}</dt><dd>{{ valor(v) }}</dd></template>
    </dl>
  </div>
  <div class="aviso">
    Os resultados indicam diferenças e associações temporais entre três episódios, não relações de causa e efeito.
    Em 2020 o choque foi global e simultâneo: uma defasagem pequena nesse episódio não indica, por si só, maior
    integração financeira do Brasil (texto 7.5).
  </div>
</template>
