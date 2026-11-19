<script setup lang="ts">
// EUA × Brasil alinhados ao pico (RF07), com filtros (RF08), ficha dos indicadores (RF11),
// avisos de ausência (RF12), medidas do par (RF06/RF10) e exportação CSV (RF15, D17, D27).
import { computed, onMounted, ref, watch } from 'vue'
import GraficoLinhas, { type Serie } from '../componentes/GraficoLinhas.vue'
import Status from '../componentes/Status.vue'
import { baixarCsv, consultar, type Linha } from '../dados'
import { estado, medir } from '../estado'
import { FREQ, num, PAIS, periodo, SENTIDO, unidadePainel } from '../textos'

const pares = ref<Linha[]>([])
const episodios = ref<Linha[]>([])
const idPar = ref('producao_industrial')
const idEp = ref('2007-2009')
const de = ref(-24)
const ate = ref(48)
const verEua = ref(true)
const verBr = ref(true)

const ponte = ref<Linha | null>(null)
const series = ref<Linha[]>([])
const pontos = ref<Linha[]>([])
const resumo = ref<Linha[]>([])
const comp = ref<Linha | null>(null)
const vale = ref<number | null>(null)

const freq = computed(() => String(series.value.find((s) => s.pais === 'EUA')?.frequencia ?? 'M'))
const tabela = computed(() => freq.value === 'T' ? 'fato_serie_alinhada_trimestral' : 'fato_serie_alinhada_mensal')
const janela = computed(() => freq.value === 'T'
  ? [Math.floor(de.value / 3), Math.ceil(ate.value / 3)] : [de.value, ate.value])

async function carregarListas() {
  pares.value = await consultar(`SELECT id_par, any_value(grupo) AS grupo FROM ponte_serie_br_eua
                                  GROUP BY id_par ORDER BY grupo`)
  episodios.value = await consultar(`SELECT id_episodio, nome FROM dim_episodio ORDER BY pico_mensal`)
  if (!pares.value.some((p) => p.id_par === idPar.value)) idPar.value = String(pares.value[0]?.id_par ?? '')
  if (!episodios.value.some((e) => e.id_episodio === idEp.value)) idEp.value = String(episodios.value[0]?.id_episodio ?? '')
}

async function carregar() {
  if (!idPar.value || !idEp.value) return
  await medir(async () => {
    const [p] = await consultar(`SELECT * FROM ponte_serie_br_eua WHERE id_par = ? AND id_episodio = ?`,
      [idPar.value, idEp.value])
    ponte.value = p ?? null
    const ids = [p?.id_serie_eua, p?.id_serie_br].filter((x): x is string => typeof x === 'string')
    const marc = ids.map(() => '?').join(',')
    series.value = await consultar(`
      SELECT s.*, CAST(s.inicio_disponivel AS VARCHAR) AS inicio, CAST(s.fim_disponivel AS VARCHAR) AS fim,
             m.descricao AS metodo
      FROM dim_serie s
      LEFT JOIN (SELECT DISTINCT id_serie, id_metodo FROM fato_resumo_episodio WHERE id_episodio = ?) r USING (id_serie)
      LEFT JOIN dim_metodo m USING (id_metodo)
      WHERE s.id_serie IN (${marc}) ORDER BY s.pais DESC`, [idEp.value, ...ids])
    const [a, b] = janela.value
    pontos.value = await consultar(`
      SELECT id_serie, CAST(t_rel AS INTEGER) AS t, valor_painel AS y, status, motivo
      FROM ${tabela.value} WHERE id_episodio = ? AND id_serie IN (${marc}) AND t_rel BETWEEN ? AND ?
      ORDER BY t_rel`, [idEp.value, ...ids, a, b])
    resumo.value = await consultar(`SELECT * FROM fato_resumo_episodio WHERE id_episodio = ? AND id_serie IN (${marc})`,
      [idEp.value, ...ids])
    const [c] = await consultar(`SELECT * FROM fato_comparacao WHERE id_par = ? AND id_episodio = ?`,
      [idPar.value, idEp.value])
    comp.value = c ?? null
    const unidade = freq.value === 'T' ? 'quarter' : 'month'
    const col = freq.value === 'T' ? ['pico_trimestral', 'vale_trimestral'] : ['pico_mensal', 'vale_mensal']
    const [v] = await consultar(`SELECT CAST(date_diff('${unidade}', ${col[0]}, ${col[1]}) AS INTEGER) AS t
                                 FROM dim_episodio WHERE id_episodio = ?`, [idEp.value])
    vale.value = v ? Number(v.t) : null
  })
}

onMounted(async () => { await carregarListas(); await carregar() })
watch(() => estado.versao, async () => { await carregarListas(); await carregar() })
watch([idPar, idEp, de, ate], carregar)

const serieEua = computed(() => series.value.find((s) => s.pais === 'EUA'))
const serieBr = computed(() => series.value.find((s) => s.pais === 'BR'))
const grafico = computed<Serie[]>(() => {
  const r: Serie[] = []
  const mk = (s: Linha | undefined, cor: string, ver: boolean) => {
    if (!s || !ver) return
    r.push({
      id: String(s.id_serie), nome: `${PAIS[String(s.pais)]}: ${s.nome}`, rotulo: PAIS[String(s.pais)], cor,
      pontos: pontos.value.filter((p) => p.id_serie === s.id_serie).map((p) => ({
        x: Number(p.t), y: p.y === null ? null : Number(p.y), status: p.status as string, motivo: p.motivo as string,
      })),
    })
  }
  mk(serieEua.value, 'var(--serie-1)', verEua.value)
  mk(serieBr.value, 'var(--serie-2)', verBr.value)
  return r
})
const tipoMedida = computed(() => String(serieEua.value?.tipo_medida ?? 'nivel'))
const nomeEp = computed(() => String(episodios.value.find((e) => e.id_episodio === idEp.value)?.nome ?? idEp.value))
const nomePar = computed(() => String(pares.value.find((p) => p.id_par === idPar.value)?.grupo ?? idPar.value))
const fontes = computed(() => series.value.map((s) => `${s.fonte} (${s.codigo_origem})`).join('; '))
const resumoDe = (id: unknown) => resumo.value.find((r) => r.id_serie === id)
const lacunasBr = computed(() => serieBr.value && pontos.value.some((p) => p.id_serie === serieBr.value!.id_serie && p.y === null))

async function exportar() {
  const ids = [ponte.value?.id_serie_eua, ponte.value?.id_serie_br].filter((x): x is string => typeof x === 'string')
  const marc = ids.map(() => '?').join(',')
  const [a, b] = janela.value
  // Mesma consulta da tela (seção 8.4), com fonte, método, edição e data de coleta (D17, D27).
  const linhas = await consultar(`
    SELECT a.id_edicao, a.id_episodio, s.pais, s.id_serie, s.nome, s.fonte, s.codigo_origem,
           a.t_rel, CAST(a.data_ref AS VARCHAR) AS data_ref, a.valor_tratado, a.valor_painel, s.tipo_medida,
           s.unidade, a.status, a.motivo, a.id_metodo, m.descricao AS metodo,
           CAST(a.coletado_em AS VARCHAR) AS coletado_em
    FROM ${tabela.value} a
    JOIN dim_serie s USING (id_serie)
    LEFT JOIN dim_metodo m USING (id_metodo)
    WHERE a.id_episodio = ? AND a.id_serie IN (${marc}) AND a.t_rel BETWEEN ? AND ?
    ORDER BY a.t_rel, s.pais`, [idEp.value, ...ids, a, b])
  baixarCsv(linhas, `${idPar.value}_${idEp.value}_${estado.aberta?.id_edicao}.csv`)
}
</script>

<template>
  <section class="filtros" aria-label="Filtros">
    <label>Indicador (par EUA × Brasil)
      <select v-model="idPar"><option v-for="p in pares" :key="String(p.id_par)" :value="p.id_par">{{ p.grupo }}</option></select>
    </label>
    <label>Episódio
      <select v-model="idEp"><option v-for="e in episodios" :key="String(e.id_episodio)" :value="e.id_episodio">{{ e.nome }} ({{ e.id_episodio }})</option></select>
    </label>
    <label>Meses antes do pico <input v-model.number="de" type="number" min="-36" max="0" step="1" /></label>
    <label>Meses depois do pico <input v-model.number="ate" type="number" min="0" max="72" step="1" /></label>
    <div class="marcar" role="group" aria-label="País">
      <label><input v-model="verEua" type="checkbox" /> Estados Unidos</label>
      <label><input v-model="verBr" type="checkbox" /> Brasil</label>
    </div>
    <button class="acao" type="button" @click="exportar">Exportar CSV</button>
  </section>

  <div v-if="ponte && !ponte.id_serie_br" class="aviso">
    <strong>Sem dados do Brasil neste episódio.</strong>
    {{ ponte.diferencas_metodologicas }} O gráfico mostra só a série dos Estados Unidos.
  </div>
  <div v-else-if="lacunasBr" class="aviso">
    Há meses sem valor na série brasileira dentro da janela: a linha é interrompida nesses pontos
    (passe o mouse para ver o motivo).
  </div>

  <GraficoLinhas
    :titulo="`${nomePar} — ${nomeEp}`"
    :subtitulo="`${unidadePainel(tipoMedida)}; ${freq === 'T' ? 'trimestres' : 'meses'} em relação ao pico da recessão nos EUA (NBER)`"
    :unidade="unidadePainel(tipoMedida)"
    :rotulo-x="freq === 'T' ? 'Trimestres desde o pico' : 'Meses desde o pico'"
    :fonte="`${fontes}. Pico e vale: NBER. Edição ${estado.aberta?.id_edicao}`"
    :series="grafico"
    :banda="vale !== null ? { x0: 0, x1: vale, rotulo: 'Recessão nos EUA (pico ao vale)' } : null"
    :referencia="tipoMedida === 'taxa' ? 0 : 100"
  />

  <section class="grade-4" aria-label="Medidas do par">
    <div class="cartao indicador">
      <div class="rotulo">Defasagem (Brasil − EUA)</div>
      <div class="valor">{{ comp?.defasagem === null || comp?.defasagem === undefined ? '—' : periodo(comp.defasagem, freq) }}</div>
      <div class="det"><Status :codigo="comp?.status as string" :motivo="comp?.motivo as string" />
        <span v-if="comp?.defasagem !== null && comp?.defasagem !== undefined"> · positivo = Brasil reagiu depois</span></div>
    </div>
    <div v-for="s in [serieEua, serieBr].filter(Boolean)" :key="String(s!.id_serie)" class="cartao indicador" style="grid-column: span 1">
      <div class="rotulo">{{ PAIS[String(s!.pais)] }} — reação</div>
      <div class="valor">{{ resumoDe(s!.id_serie)?.t_reacao === null ? '—' : periodo(resumoDe(s!.id_serie)?.t_reacao, freq) }}</div>
      <div class="det">
        <Status :codigo="resumoDe(s!.id_serie)?.status_reacao as string" />
        · pior valor {{ num(resumoDe(s!.id_serie)?.amplitude) }} {{ resumoDe(s!.id_serie)?.unidade_amplitude ?? '' }}
        <template v-if="resumoDe(s!.id_serie)?.t_extremo !== null"> em {{ periodo(resumoDe(s!.id_serie)?.t_extremo, freq) }}</template>
        · recuperação
        <template v-if="resumoDe(s!.id_serie)?.t_recuperacao !== null">{{ periodo(resumoDe(s!.id_serie)?.t_recuperacao, freq) }}</template>
        <Status v-else :codigo="resumoDe(s!.id_serie)?.status_recuperacao as string" />
      </div>
    </div>
    <div class="cartao indicador">
      <div class="rotulo">Diferença das variações (Brasil − EUA)</div>
      <div class="valor">{{ num(comp?.dif_amplitude) }}</div>
      <div class="det">pontos percentuais (variação do Brasil menos a dos EUA)</div>
    </div>
  </section>

  <section class="grade-2" aria-label="Ficha dos indicadores">
    <div v-for="s in series" :key="String(s.id_serie)" class="cartao">
      <h3>{{ PAIS[String(s.pais)] }}: {{ s.nome }}</h3>
      <dl class="ficha">
        <dt>Descrição</dt><dd>{{ s.descricao }}</dd>
        <dt>Fonte</dt><dd>{{ s.fonte }} — {{ s.produtor }} (código {{ s.codigo_origem }})</dd>
        <dt>Unidade na fonte</dt><dd>{{ s.unidade }}</dd>
        <dt>Periodicidade</dt><dd>{{ FREQ[String(s.frequencia)] }}</dd>
        <dt>Período coletado</dt><dd>{{ String(s.inicio).slice(0, 7) }} a {{ String(s.fim).slice(0, 7) }}</dd>
        <dt>Ajuste sazonal</dt><dd>{{ s.ajuste_sazonal ? 'sim' : 'não' }}</dd>
        <dt>Sentido adverso</dt><dd>{{ SENTIDO[String(s.sentido_adverso)] }}</dd>
        <dt>Método</dt><dd>{{ s.metodo ?? '—' }}</dd>
        <template v-if="s.aviso_metodologia"><dt>Atenção</dt><dd>{{ s.aviso_metodologia }}</dd></template>
        <dt>Origem</dt><dd><a :href="String(s.url)" target="_blank" rel="noopener">{{ s.url }}</a></dd>
      </dl>
    </div>
  </section>
  <div v-if="ponte?.diferencas_metodologicas && ponte?.id_serie_br" class="cartao">
    <h3>Diferenças metodológicas entre as séries</h3>
    <p style="margin:0">{{ ponte.diferencas_metodologicas }}</p>
    <p v-if="ponte.observacao" class="muted" style="margin:6px 0 0">{{ ponte.observacao }}</p>
  </div>
</template>
