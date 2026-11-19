<script setup lang="ts">
// Gráfico de linhas alinhado ao pico (RF07, RF09; RNF09: título, legenda, unidade, fonte e
// cores distinguíveis por daltônicos). SVG próprio, sem biblioteca: régua vertical com dica,
// rótulos diretos no fim de cada linha, faixa da recessão, linha interrompida nas lacunas
// e tabela como alternativa ao gráfico.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export interface Ponto { x: number; y: number | null; status?: string | null; motivo?: string | null }
export interface Serie { id: string; nome: string; rotulo?: string; cor: string; pontos: Ponto[] }

const props = defineProps<{
  titulo: string
  subtitulo?: string
  unidade: string
  rotuloX: string
  fonte: string
  series: Serie[]
  banda?: { x0: number; x1: number; rotulo: string } | null
  referencia?: number | null
  casas?: number
}>()

const caixa = ref<HTMLDivElement | null>(null)
const largura = ref(720)
const ALTURA = 340
const M = { topo: 16, dir: 132, base: 40, esq: 56 }
let observador: ResizeObserver | null = null
onMounted(() => {
  observador = new ResizeObserver(([e]) => { largura.value = Math.max(320, e.contentRect.width) })
  if (caixa.value) observador.observe(caixa.value)
})
onBeforeUnmount(() => observador?.disconnect())

const verTabela = ref(false)
const casas = computed(() => props.casas ?? 1)
const fmt = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : v.toLocaleString('pt-BR', {
    minimumFractionDigits: casas.value, maximumFractionDigits: casas.value })

const xs = computed(() => {
  const todos = props.series.flatMap((s) => s.pontos.map((p) => p.x))
  return todos.length ? [Math.min(...todos), Math.max(...todos)] : [0, 1]
})
const ys = computed(() => {
  const v = props.series.flatMap((s) => s.pontos.map((p) => p.y)).filter((y): y is number => y !== null)
  if (props.referencia !== null && props.referencia !== undefined) v.push(props.referencia)
  if (!v.length) return [0, 1]
  let [a, b] = [Math.min(...v), Math.max(...v)]
  const folga = (b - a || 1) * 0.08
  return [a - folga, b + folga]
})
const larguraUtil = computed(() => largura.value - M.esq - M.dir)
const alturaUtil = ALTURA - M.topo - M.base
const px = (x: number) => M.esq + ((x - xs.value[0]) / (xs.value[1] - xs.value[0] || 1)) * larguraUtil.value
const py = (y: number) => M.topo + (1 - (y - ys.value[0]) / (ys.value[1] - ys.value[0] || 1)) * alturaUtil

function marcas(a: number, b: number, n: number, inteiro = false): number[] {
  const passo0 = (b - a) / n
  const pot = 10 ** Math.floor(Math.log10(passo0 || 1))
  let passo = [1, 2, 2.5, 5, 10].map((m) => m * pot).find((p) => p >= passo0) ?? pot * 10
  if (inteiro) passo = Math.max(1, Math.round(passo))
  const r: number[] = []
  for (let v = Math.ceil(a / passo) * passo; v <= b + 1e-9; v += passo) r.push(+v.toFixed(10))
  return r
}
const marcasY = computed(() => marcas(ys.value[0], ys.value[1], 5))
const marcasX = computed(() => marcas(xs.value[0], xs.value[1], Math.max(4, Math.floor(larguraUtil.value / 70)), true))

/** Caminho SVG com quebra nas lacunas (y nulo). */
function caminho(s: Serie): string {
  let d = ''
  let novo = true
  for (const p of s.pontos) {
    if (p.y === null) { novo = true; continue }
    d += `${novo ? 'M' : 'L'}${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`
    novo = false
  }
  return d
}
/** Rótulo direto no último ponto com valor; afastados para não colidir. */
const rotulos = computed(() => {
  const r = props.series.map((s) => {
    const ult = [...s.pontos].reverse().find((p) => p.y !== null)
    return { s, y: ult ? py(ult.y!) : null, valor: ult?.y ?? null }
  }).filter((r) => r.y !== null) as { s: Serie; y: number; valor: number }[]
  r.sort((a, b) => a.y - b.y)
  for (let i = 1; i < r.length; i++) if (r[i].y - r[i - 1].y < 16) r[i].y = r[i - 1].y + 16
  return r
})

// ------------------------------------------------------------ régua e dica
const xAtivo = ref<number | null>(null)
const todosX = computed(() => [...new Set(props.series.flatMap((s) => s.pontos.map((p) => p.x)))].sort((a, b) => a - b))
function mover(ev: PointerEvent) {
  const svg = ev.currentTarget as SVGSVGElement
  const r = svg.getBoundingClientRect()
  const x = ((ev.clientX - r.left) / r.width) * largura.value
  if (x < M.esq || x > M.esq + larguraUtil.value) { xAtivo.value = null; return }
  let melhor = todosX.value[0]
  for (const v of todosX.value) if (Math.abs(px(v) - x) < Math.abs(px(melhor) - x)) melhor = v
  xAtivo.value = melhor
}
function teclado(ev: KeyboardEvent) {
  const lista = todosX.value
  if (!lista.length) return
  const i = xAtivo.value === null ? lista.indexOf(0) : lista.indexOf(xAtivo.value)
  if (ev.key === 'ArrowRight') xAtivo.value = lista[Math.min(lista.length - 1, Math.max(0, i) + 1)]
  else if (ev.key === 'ArrowLeft') xAtivo.value = lista[Math.max(0, i - 1)]
  else return
  ev.preventDefault()
}
const dica = computed(() => {
  if (xAtivo.value === null) return null
  const x = xAtivo.value
  return {
    x,
    linhas: props.series.map((s) => {
      const p = s.pontos.find((q) => q.x === x)
      return { s, y: p?.y ?? null, motivo: p && p.y === null ? (p.motivo ?? p.status ?? 'sem dado') : null }
    }),
  }
})
const dicaEsquerda = computed(() => xAtivo.value !== null && px(xAtivo.value) > largura.value * 0.6)

// ------------------------------------------------------------ tabela
const linhasTabela = computed(() => todosX.value.map((x) => ({
  x, valores: props.series.map((s) => s.pontos.find((p) => p.x === x) ?? null),
})))
</script>

<template>
  <figure class="grafico">
    <figcaption>
      <h3>{{ titulo }}</h3>
      <p v-if="subtitulo" class="sub">{{ subtitulo }}</p>
    </figcaption>
    <div class="topo">
      <ul class="legenda" aria-label="Legenda">
        <li v-for="s in series" :key="s.id"><span class="chave" :style="{ background: s.cor }" />{{ s.nome }}</li>
        <li v-if="banda"><span class="chave-banda" />{{ banda.rotulo }}</li>
      </ul>
      <button class="botao-texto" type="button" @click="verTabela = !verTabela">
        {{ verTabela ? 'Ver gráfico' : 'Ver tabela' }}
      </button>
    </div>

    <div v-show="!verTabela" ref="caixa" class="area">
      <svg :viewBox="`0 0 ${largura} ${ALTURA}`" :width="largura" :height="ALTURA" role="img"
           :aria-label="`${titulo}. ${unidade}. Use as setas para percorrer os meses.`" tabindex="0"
           @pointermove="mover" @pointerleave="xAtivo = null" @keydown="teclado" @blur="xAtivo = null">
        <rect v-if="banda" class="banda" :x="px(Math.max(banda.x0, xs[0]))" :y="M.topo"
              :width="Math.max(0, px(Math.min(banda.x1, xs[1])) - px(Math.max(banda.x0, xs[0])))"
              :height="alturaUtil" />
        <g class="grade">
          <line v-for="v in marcasY" :key="'gy' + v" :x1="M.esq" :x2="M.esq + larguraUtil" :y1="py(v)" :y2="py(v)" />
        </g>
        <line v-if="referencia !== null && referencia !== undefined" class="referencia"
              :x1="M.esq" :x2="M.esq + larguraUtil" :y1="py(referencia)" :y2="py(referencia)" />
        <line class="pico" :x1="px(0)" :x2="px(0)" :y1="M.topo" :y2="M.topo + alturaUtil" />
        <text class="rotulo-pico" :x="px(0) + 4" :y="M.topo + 11">pico</text>
        <g class="eixo">
          <text v-for="v in marcasY" :key="'ty' + v" :x="M.esq - 8" :y="py(v) + 4" text-anchor="end">{{ fmt(v) }}</text>
          <text v-for="v in marcasX" :key="'tx' + v" :x="px(v)" :y="ALTURA - M.base + 18" text-anchor="middle">{{ v }}</text>
          <text :x="M.esq + larguraUtil / 2" :y="ALTURA - 4" text-anchor="middle">{{ rotuloX }}</text>
        </g>
        <path v-for="s in series" :key="'l' + s.id" class="linha" :d="caminho(s)" :stroke="s.cor" />
        <g v-for="r in rotulos" :key="'r' + r.s.id" class="direto">
          <text :x="M.esq + larguraUtil + 8" :y="r.y + 4">
            <tspan class="marca" :fill="r.s.cor">━</tspan> {{ r.s.rotulo ?? r.s.nome }}
          </text>
        </g>
        <g v-if="dica">
          <line class="regua" :x1="px(dica.x)" :x2="px(dica.x)" :y1="M.topo" :y2="M.topo + alturaUtil" />
          <template v-for="l in dica.linhas" :key="'p' + l.s.id">
            <circle v-if="l.y !== null" class="ponto" :cx="px(dica.x)" :cy="py(l.y)" r="4.5" :fill="l.s.cor" />
          </template>
        </g>
      </svg>
      <div v-if="dica" class="dica" :style="{ left: `${(px(dica.x) / largura) * 100}%` }"
           :class="{ esquerda: dicaEsquerda }" role="status">
        <div class="dica-titulo">{{ rotuloX }}: {{ dica.x }}</div>
        <div v-for="l in dica.linhas" :key="'d' + l.s.id" class="dica-linha">
          <span class="traco" :style="{ background: l.s.cor }" />
          <strong>{{ l.y === null ? '—' : fmt(l.y) }}</strong>
          <span class="nome">{{ l.s.nome }}</span>
          <span v-if="l.motivo" class="motivo">{{ l.motivo }}</span>
        </div>
      </div>
    </div>

    <div v-if="verTabela" class="tabela-rolagem">
      <table class="tabela">
        <thead><tr><th>{{ rotuloX }}</th><th v-for="s in series" :key="'h' + s.id">{{ s.nome }}</th></tr></thead>
        <tbody>
          <tr v-for="l in linhasTabela" :key="l.x">
            <td>{{ l.x }}</td>
            <td v-for="(p, i) in l.valores" :key="i" class="num">
              {{ p && p.y !== null ? fmt(p.y) : (p?.status ?? '—') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="fonte">{{ unidade }} · Fonte: {{ fonte }}</p>
  </figure>
</template>

<style scoped>
.grafico { margin: 0; background: var(--superficie); border: 1px solid var(--borda); border-radius: 8px; padding: 16px 16px 10px; }
h3 { margin: 0; font-size: 1rem; color: var(--texto-1); }
.sub { margin: 2px 0 0; color: var(--texto-2); font-size: .85rem; }
.topo { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 10px 0 4px; flex-wrap: wrap; }
.legenda { display: flex; gap: 16px; list-style: none; margin: 0; padding: 0; color: var(--texto-2); font-size: .85rem; flex-wrap: wrap; }
.legenda li { display: flex; align-items: center; gap: 6px; }
.chave { width: 16px; height: 2px; border-radius: 1px; display: inline-block; }
.chave-banda { width: 14px; height: 10px; background: var(--banda); display: inline-block; border-radius: 2px; }
.area { position: relative; }
svg { display: block; max-width: 100%; height: auto; touch-action: none; }
svg:focus-visible { outline: 2px solid var(--foco); outline-offset: 2px; border-radius: 4px; }
.banda { fill: var(--banda); }
.grade line { stroke: var(--grade); stroke-width: 1; }
.referencia { stroke: var(--eixo); stroke-width: 1.5; }
.pico { stroke: var(--texto-3); stroke-width: 1; stroke-dasharray: 3 3; }
.rotulo-pico { fill: var(--texto-3); font-size: 11px; }
.eixo text { fill: var(--texto-3); font-size: 11px; font-variant-numeric: tabular-nums; }
.linha { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.direto text { fill: var(--texto-2); font-size: 12px; }
.direto .marca { font-size: 12px; }
.regua { stroke: var(--texto-3); stroke-width: 1; }
.ponto { stroke: var(--superficie); stroke-width: 2; }
.dica { position: absolute; top: 8px; transform: translateX(12px); background: var(--superficie); border: 1px solid var(--borda); border-radius: 6px; padding: 8px 10px; font-size: .8rem; pointer-events: none; box-shadow: 0 4px 14px rgba(0,0,0,.12); min-width: 170px; color: var(--texto-2); }
.dica.esquerda { transform: translateX(calc(-100% - 12px)); }
.dica-titulo { color: var(--texto-3); margin-bottom: 4px; }
.dica-linha { display: flex; align-items: baseline; gap: 6px; }
.dica-linha strong { color: var(--texto-1); font-variant-numeric: tabular-nums; }
.traco { width: 12px; height: 2px; display: inline-block; align-self: center; }
.motivo { color: var(--texto-3); font-size: .75rem; }
.fonte { margin: 6px 0 0; color: var(--texto-3); font-size: .78rem; }
.tabela-rolagem { max-height: 340px; overflow: auto; }
</style>
