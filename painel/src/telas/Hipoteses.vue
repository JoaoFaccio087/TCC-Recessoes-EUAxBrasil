<script setup lang="ts">
// Resultado das hipóteses H1 a H3 (texto 7.5). H1: mediana das defasagens. H2 e H3: comparação
// por indicador e maioria estrita dos indicadores comparáveis (D42).
import { onMounted, ref, watch } from 'vue'
import Status from '../componentes/Status.vue'
import { consultar, type Linha } from '../dados'
import { estado, medir } from '../estado'
import { num } from '../textos'

const EPISODIOS = ['1981-1982', '2007-2009', '2020']
const ENUNCIADO: Record<string, string> = {
  H1: 'O intervalo entre a reação dos indicadores norte-americanos e a dos brasileiros diminuiu ao longo dos três episódios.',
  H2: 'A recessão de 2020 teve a queda mais intensa e a recuperação mais rápida entre os três episódios.',
  H3: 'A recessão de 1981-1982 produziu os efeitos mais prolongados sobre a economia brasileira.',
}
const CRITERIO: Record<string, string> = {
  H1: 'Sustentada se a mediana da defasagem, em valor absoluto, cair de 1981-1982 para 2007-2009 e de 2007-2009 para 2020, nos pares com reação nos três episódios (produção industrial, desemprego, ações e exportações totais; inflação e juros ficam fora). Com menos de 3 pares elegíveis, inconclusiva.',
  H2: 'Comparação por indicador (produção industrial, desemprego e exportações totais); cada episódio é medido a partir do próprio pico. Em cada medida, a condição é atendida se 2020 vencer sozinho na maioria estrita dos indicadores comparáveis (mínimo 2). Sustentada se 2020 tiver a maior intensidade e o menor tempo de recuperação; uma condição não atendida torna a hipótese não sustentada.',
  H3: 'Mesma regra de H2: sustentada se 1981-1982 tiver o maior tempo de recuperação na maioria estrita dos indicadores comparáveis (mínimo 2). Sem recuperação na janela conta como o fim da janela (60 meses).',
}
const NOMES: Record<string, string> = {
  pares_usados: 'Pares considerados', pares_elegiveis: 'Pares elegíveis',
  mediana_abs_defasagem: 'Mediana da defasagem (valor absoluto)',
}
const MEDIDA: Record<string, string> = {
  intensidade: 'Intensidade (variação até o pior valor, em valor absoluto)',
  recuperacao: 'Tempo de recuperação (meses)',
}
const GRUPO: Record<string, string> = {
  producao_industrial: 'Produção industrial', desemprego: 'Desemprego (p.p.)',
  exportacoes_total: 'Exportações totais',
}

interface Grupo {
  grupo: string; valores: Record<string, number | null>; vencedor: string | string[] | null
  empate: boolean; excluido_motivo: string | null
}
interface Condicao {
  medida: string; episodio_esperado: string; comparaveis: number; favoraveis: number
  estado: string; grupos: Grupo[]
}

const linhas = ref<Linha[]>([])
async function carregar() {
  await medir(async () => { linhas.value = await consultar(`SELECT * FROM resultado_hipotese ORDER BY hipotese`) })
}
onMounted(carregar)
watch(() => estado.versao, carregar)

function json(l: Linha): Record<string, unknown> {
  try { return JSON.parse(String(l.detalhe ?? '{}')) } catch { return {} }
}
function condicoes(l: Linha): Condicao[] {
  const c = json(l).condicoes
  return Array.isArray(c) ? (c as Condicao[]) : []
}
function campos(l: Linha): [string, unknown][] {
  return Object.entries(json(l)).filter(([k]) => k !== 'condicoes' && k !== 'criterio')
}
function valor(v: unknown): string {
  if (Array.isArray(v)) return v.join(', ')
  if (v && typeof v === 'object') return Object.entries(v).map(([k, x]) => `${k}: ${num(x)}`).join(' · ')
  return String(v)
}
function resultadoGrupo(g: Grupo, esperado: string): string {
  if (g.excluido_motivo) return `Fora da comparação (${g.excluido_motivo})`
  if (g.empate) return `Empate (${valor(g.vencedor)}): não conta a favor`
  return g.vencedor === esperado ? `${g.vencedor}: a favor` : `${g.vencedor}: contra`
}
</script>

<template>
  <div v-for="l in linhas" :key="String(l.hipotese)" class="cartao">
    <h3>{{ l.hipotese }} — <Status :codigo="l.resultado as string" /></h3>
    <p style="margin:0 0 6px">{{ ENUNCIADO[String(l.hipotese)] }}</p>
    <p class="muted" style="margin:0 0 8px">Critério: {{ CRITERIO[String(l.hipotese)] }} Casos considerados: {{ l.n_pares }}.</p>
    <dl v-if="campos(l).length" class="ficha">
      <template v-for="[k, v] in campos(l)" :key="k"><dt>{{ NOMES[k] ?? k }}</dt><dd>{{ valor(v) }}</dd></template>
    </dl>
    <div v-for="c in condicoes(l)" :key="c.medida" style="margin-top:10px">
      <p style="margin:0 0 4px">
        <strong>{{ MEDIDA[c.medida] ?? c.medida }}</strong>, episódio esperado {{ c.episodio_esperado }}:
        {{ c.favoraveis }} de {{ c.comparaveis }} indicadores comparáveis a favor — condição {{ c.estado }}.
      </p>
      <table class="tabela">
        <thead>
          <tr><th>Indicador</th><th v-for="e in EPISODIOS" :key="e">{{ e }}</th><th>Resultado</th></tr>
        </thead>
        <tbody>
          <tr v-for="g in c.grupos" :key="g.grupo">
            <td>{{ GRUPO[g.grupo] ?? g.grupo }}</td>
            <td v-for="e in EPISODIOS" :key="e">{{ g.valores?.[e] == null ? '—' : num(g.valores[e]) }}</td>
            <td>{{ resultadoGrupo(g, c.episodio_esperado) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div class="aviso">
    Os resultados indicam diferenças e associações temporais entre três episódios, não relações de causa e efeito.
    Em 2020 o choque foi global e simultâneo: uma defasagem pequena nesse episódio não indica, por si só, maior
    integração financeira do Brasil (texto 7.5).
  </div>
</template>
