<script setup lang="ts">
// Um indicador nos três episódios, no mesmo gráfico (RF09). Cor fixa por episódio,
// na ordem cronológica (slots 1 a 3), qualquer que seja o filtro.
import { computed, onMounted, ref, watch } from 'vue'
import GraficoLinhas, { type Serie } from '../componentes/GraficoLinhas.vue'
import Status from '../componentes/Status.vue'
import { baixarCsv, consultar, type Linha } from '../dados'
import { estado, medir } from '../estado'
import { num, PAIS, periodo, unidadePainel } from '../textos'

const CORES = ['var(--serie-1)', 'var(--serie-2)', 'var(--serie-3)']
const listaSeries = ref<Linha[]>([])
const episodios = ref<Linha[]>([])
const idSerie = ref('br_prod_ind')
const pais = ref('')
const de = ref(-24)
const ate = ref(48)
const serie = ref<Linha | null>(null)
const pontos = ref<Linha[]>([])
const resumo = ref<Linha[]>([])

async function carregarListas() {
  listaSeries.value = await consultar(`
    SELECT s.id_serie, s.nome, s.pais, s.frequencia FROM dim_serie s
    WHERE s.id_serie IN (SELECT id_serie FROM fato_resumo_episodio)
    ORDER BY s.pais DESC, s.grupo, s.nome`)
  episodios.value = await consultar(`SELECT id_episodio, nome FROM dim_episodio ORDER BY pico_mensal`)
}
const opcoes = computed(() => listaSeries.value.filter((s) => !pais.value || s.pais === pais.value))
watch(opcoes, (o) => { if (o.length && !o.some((s) => s.id_serie === idSerie.value)) idSerie.value = String(o[0].id_serie) })

async function carregar() {
  await medir(async () => {
    const [s] = await consultar(`SELECT * FROM dim_serie WHERE id_serie = ?`, [idSerie.value])
    serie.value = s ?? null
    const t = s?.frequencia === 'T'
    const tab = t ? 'fato_serie_alinhada_trimestral' : 'fato_serie_alinhada_mensal'
    const [a, b] = t ? [Math.floor(de.value / 3), Math.ceil(ate.value / 3)] : [de.value, ate.value]
    pontos.value = await consultar(`SELECT id_episodio, CAST(t_rel AS INTEGER) AS t, valor_painel AS y, status, motivo
      FROM ${tab} WHERE id_serie = ? AND t_rel BETWEEN ? AND ? ORDER BY t_rel`, [idSerie.value, a, b])
    resumo.value = await consultar(`SELECT * FROM fato_resumo_episodio WHERE id_serie = ?`, [idSerie.value])
  })
}
onMounted(async () => { await carregarListas(); await carregar() })
watch(() => estado.versao, async () => { await carregarListas(); await carregar() })
watch([idSerie, de, ate], carregar)

const grafico = computed<Serie[]>(() => episodios.value.map((e, i) => ({
  id: String(e.id_episodio), nome: String(e.id_episodio), cor: CORES[i % CORES.length],
  pontos: pontos.value.filter((p) => p.id_episodio === e.id_episodio).map((p) => ({
    x: Number(p.t), y: p.y === null ? null : Number(p.y), status: p.status as string, motivo: p.motivo as string,
  })),
})).filter((s) => s.pontos.length))
const semEpisodio = computed(() => episodios.value.filter((e) => !pontos.value.some((p) => p.id_episodio === e.id_episodio)))
const freq = computed(() => String(serie.value?.frequencia ?? 'M'))
const tipo = computed(() => String(serie.value?.tipo_medida ?? 'nivel'))

async function exportar() {
  const t = freq.value === 'T'
  const tab = t ? 'fato_serie_alinhada_trimestral' : 'fato_serie_alinhada_mensal'
  const [a, b] = t ? [Math.floor(de.value / 3), Math.ceil(ate.value / 3)] : [de.value, ate.value]
  const linhas = await consultar(`
    SELECT a.id_edicao, a.id_episodio, s.pais, s.id_serie, s.nome, s.fonte, s.codigo_origem, a.t_rel,
           CAST(a.data_ref AS VARCHAR) AS data_ref, a.valor_tratado, a.valor_painel, s.tipo_medida, s.unidade,
           a.status, a.motivo, a.id_metodo, m.descricao AS metodo, CAST(a.coletado_em AS VARCHAR) AS coletado_em
    FROM ${tab} a JOIN dim_serie s USING (id_serie) LEFT JOIN dim_metodo m USING (id_metodo)
    WHERE a.id_serie = ? AND a.t_rel BETWEEN ? AND ? ORDER BY a.id_episodio, a.t_rel`, [idSerie.value, a, b])
  baixarCsv(linhas, `${idSerie.value}_episodios_${estado.aberta?.id_edicao}.csv`)
}
</script>

<template>
  <section class="filtros" aria-label="Filtros">
    <label>País
      <select v-model="pais"><option value="">Todos</option><option value="EUA">Estados Unidos</option><option value="BR">Brasil</option></select>
    </label>
    <label>Indicador
      <select v-model="idSerie">
        <option v-for="s in opcoes" :key="String(s.id_serie)" :value="s.id_serie">{{ PAIS[String(s.pais)] }}: {{ s.nome }}</option>
      </select>
    </label>
    <label>Meses antes do pico <input v-model.number="de" type="number" min="-36" max="0" /></label>
    <label>Meses depois do pico <input v-model.number="ate" type="number" min="0" max="72" /></label>
    <button class="acao" type="button" @click="exportar">Exportar CSV</button>
  </section>

  <div v-if="semEpisodio.length" class="aviso">
    Sem dados desta série em: {{ semEpisodio.map((e) => e.id_episodio).join(', ') }}.
    <template v-if="serie?.aviso_metodologia">{{ serie.aviso_metodologia }}</template>
    No Brasil, algumas séries mudam de um episódio para outro (por exemplo, PME e PNAD Contínua):
    use a aba "EUA × Brasil" para ver a série de cada episódio.
  </div>

  <GraficoLinhas
    :titulo="`${PAIS[String(serie?.pais)] ?? ''}: ${serie?.nome ?? ''} nos três episódios`"
    :subtitulo="`${unidadePainel(tipo)}; cada episódio alinhado ao seu próprio pico`"
    :unidade="unidadePainel(tipo)"
    :rotulo-x="freq === 'T' ? 'Trimestres desde o pico' : 'Meses desde o pico'"
    :fonte="`${serie?.fonte ?? ''} (${serie?.codigo_origem ?? ''}). Edição ${estado.aberta?.id_edicao}`"
    :series="grafico"
    :referencia="tipo === 'taxa' ? 0 : 100"
  />

  <div class="cartao">
    <h3>Medidas por episódio</h3>
    <table class="tabela">
      <thead><tr><th>Episódio</th><th class="num">Reação</th><th class="num">Pior valor (variação)</th><th class="num">Duração da queda</th><th class="num">Recuperação</th></tr></thead>
      <tbody>
        <tr v-for="r in resumo" :key="String(r.id_episodio)">
          <td>{{ r.id_episodio }}</td>
          <td class="num"><template v-if="r.t_reacao !== null">{{ periodo(r.t_reacao, freq) }}</template><Status v-else :codigo="r.status_reacao as string" /></td>
          <td class="num">{{ num(r.amplitude) }} {{ r.amplitude !== null ? r.unidade_amplitude : '' }}</td>
          <td class="num">{{ periodo(r.duracao_queda, freq) }}</td>
          <td class="num"><template v-if="r.t_recuperacao !== null">{{ periodo(r.t_recuperacao, freq) }}</template><Status v-else :codigo="r.status_recuperacao as string" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
