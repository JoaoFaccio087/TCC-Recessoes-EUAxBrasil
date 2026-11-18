<script setup lang="ts">
// Quadro-resumo das medidas de impacto por indicador e episódio (RF10), com filtros (RF08)
// e motivo de cada ausência (RF12).
import { computed, onMounted, ref, watch } from 'vue'
import Status from '../componentes/Status.vue'
import { baixarCsv, consultar, type Linha } from '../dados'
import { estado, medir } from '../estado'
import { num, PAIS, periodo } from '../textos'

const linhas = ref<Linha[]>([])
const pais = ref('')
const grupo = ref('')
const episodio = ref('')

const SQL = `
  SELECT r.id_episodio, s.pais, s.grupo, s.id_serie, s.nome, s.fonte, r.frequencia, r.valor_pico,
         r.t_reacao, r.status_reacao, r.t_extremo, r.amplitude, r.unidade_amplitude, r.duracao_queda,
         r.t_recuperacao, r.status_recuperacao, r.cobertura, r.id_metodo, r.id_edicao
  FROM fato_resumo_episodio r JOIN dim_serie s USING (id_serie)
  ORDER BY s.grupo, r.id_episodio, s.pais DESC`

async function carregar() {
  await medir(async () => { linhas.value = await consultar(SQL) })
}
onMounted(carregar)
watch(() => estado.versao, carregar)

const grupos = computed(() => [...new Set(linhas.value.map((l) => String(l.grupo)))])
const episodios = computed(() => [...new Set(linhas.value.map((l) => String(l.id_episodio)))].sort())
const filtradas = computed(() => linhas.value.filter((l) =>
  (!pais.value || l.pais === pais.value) && (!grupo.value || l.grupo === grupo.value)
  && (!episodio.value || l.id_episodio === episodio.value)))
const NOME_GRUPO: Record<string, string> = {
  producao_industrial: 'Produção industrial', desemprego: 'Desemprego', juros: 'Juros', inflacao: 'Inflação',
  cambio_real: 'Câmbio real', exportacoes: 'Exportações', pib: 'PIB', acoes: 'Mercado acionário',
}
</script>

<template>
  <section class="filtros" aria-label="Filtros">
    <label>País <select v-model="pais"><option value="">Todos</option><option value="EUA">Estados Unidos</option><option value="BR">Brasil</option></select></label>
    <label>Grupo <select v-model="grupo"><option value="">Todos</option><option v-for="g in grupos" :key="g" :value="g">{{ NOME_GRUPO[g] ?? g }}</option></select></label>
    <label>Episódio <select v-model="episodio"><option value="">Todos</option><option v-for="e in episodios" :key="e" :value="e">{{ e }}</option></select></label>
    <button class="acao" type="button" @click="baixarCsv(filtradas, `quadro_resumo_${estado.aberta?.id_edicao}.csv`)">Exportar CSV</button>
  </section>
  <div class="cartao tabela-rolagem">
    <h3>Medidas de impacto ({{ filtradas.length }} linhas)</h3>
    <p class="muted" style="margin:0 0 8px">
      Reação, pior valor e recuperação contados a partir do pico (t = 0). Variação: % do nível do pico para índices,
      pontos percentuais para taxas. Passe o mouse sobre um status para ver o motivo.
    </p>
    <table class="tabela">
      <thead>
        <tr><th>Grupo</th><th>Episódio</th><th>País</th><th>Indicador</th><th class="num">Reação</th>
          <th class="num">Pior valor em</th><th class="num">Variação até o pior valor</th><th class="num">Recuperação</th><th class="num">Cobertura</th></tr>
      </thead>
      <tbody>
        <tr v-for="l in filtradas" :key="`${l.id_episodio}-${l.id_serie}`">
          <td>{{ NOME_GRUPO[String(l.grupo)] ?? l.grupo }}</td>
          <td>{{ l.id_episodio }}</td>
          <td>{{ PAIS[String(l.pais)] }}</td>
          <td>{{ l.nome }}</td>
          <td class="num"><template v-if="l.t_reacao !== null">{{ periodo(l.t_reacao, l.frequencia) }}</template><Status v-else :codigo="l.status_reacao as string" /></td>
          <td class="num"><template v-if="l.t_extremo !== null">{{ periodo(l.t_extremo, l.frequencia) }}</template><Status v-else :codigo="l.status_recuperacao === 'NAO_APLICAVEL' ? 'NAO_APLICAVEL' : 'SEM_DADOS'" /></td>
          <td class="num">{{ l.amplitude === null ? '—' : `${num(l.amplitude)} ${l.unidade_amplitude}` }}</td>
          <td class="num"><template v-if="l.t_recuperacao !== null">{{ periodo(l.t_recuperacao, l.frequencia) }}</template><Status v-else :codigo="l.status_recuperacao as string" /></td>
          <td class="num">{{ num(Number(l.cobertura) * 100, 0) }}%</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
