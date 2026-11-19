<script setup lang="ts">
// Tela de manutenção (RF13, D15, D16, D18): execuções, edições publicadas e observações rejeitadas.
import { computed, onMounted, ref, watch } from 'vue'
import Status from '../componentes/Status.vue'
import { consultar, type Linha } from '../dados'
import { estado, medir } from '../estado'

const execucoes = ref<Linha[]>([])
const rejeitadas = ref<Linha[]>([])
const aberta = ref<string | null>(null)

async function carregar() {
  await medir(async () => {
    execucoes.value = await consultar(`
      SELECT id_execucao, CAST(inicio AS VARCHAR) AS inicio, CAST(fim AS VARCHAR) AS fim, comando,
             series_processadas, registros, status, id_edicao, erro, observacao
      FROM controle_execucao ORDER BY inicio DESC`)
    rejeitadas.value = await consultar(`
      SELECT id_serie, CAST(data_ref AS VARCHAR) AS data_ref, valor_bruto, motivo,
             CAST(coletado_em AS VARCHAR) AS coletado_em, id_execucao
      FROM observacao_rejeitada ORDER BY id_serie, data_ref`)
  })
}
onMounted(carregar)
watch(() => estado.versao, carregar)

const ultima = computed(() => execucoes.value[0])
const ultimoSucesso = computed(() => execucoes.value.find((e) => e.status === 'SUCESSO'))
const falhas30 = computed(() => falhasRecentes(execucoes.value))
/** Instante em data local. Sem fuso no texto = UTC (TIMESTAMP do controle de execução). */
function instante(s: unknown): Date | null {
  if (!s) return null
  const t = String(s).replace(' ', 'T')
  return new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(t) ? t : `${t}Z`)
}
const quando = (s: unknown) => instante(s)?.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' }) ?? '—'
function duracao(e: Linha) {
  const a = instante(e.inicio)
  const b = instante(e.fim)
  if (!a || !b) return '—'
  const s = (b.getTime() - a.getTime()) / 1000
  return s < 60 ? `${s.toFixed(0)} s` : `${(s / 60).toFixed(1)} min`
}
const falhasRecentes = (lista: Linha[]) => lista.filter((e) => e.status === 'FALHA'
  && Date.now() - (instante(e.inicio)?.getTime() ?? 0) < 30 * 864e5).length
</script>

<template>
  <section class="grade-4" aria-label="Situação">
    <div class="cartao indicador">
      <div class="rotulo">Última execução</div>
      <div class="valor" style="font-size:1.1rem"><Status :codigo="ultima?.status as string" /></div>
      <div class="det">{{ quando(ultima?.inicio) }} · {{ ultima?.comando }}</div>
    </div>
    <div class="cartao indicador">
      <div class="rotulo">Edição ativa</div>
      <div class="valor" style="font-size:1.1rem">{{ estado.ativa }}</div>
      <div class="det">{{ estado.edicoes.length }} edições publicadas</div>
    </div>
    <div class="cartao indicador">
      <div class="rotulo">Última publicação com sucesso</div>
      <div class="valor" style="font-size:1.1rem">{{ quando(ultimoSucesso?.inicio) }}</div>
      <div class="det">{{ ultimoSucesso?.registros ?? '—' }} registros</div>
    </div>
    <div class="cartao indicador">
      <div class="rotulo">Falhas nos últimos 30 dias</div>
      <div class="valor" style="font-size:1.1rem">{{ falhas30 }}</div>
      <div class="det">o painel mantém a última edição válida</div>
    </div>
  </section>

  <div class="cartao tabela-rolagem">
    <h3>Execuções da pipeline ({{ execucoes.length }})</h3>
    <table class="tabela">
      <thead><tr><th>Início</th><th>Comando</th><th>Status</th><th class="num">Séries</th><th class="num">Registros</th><th>Duração</th><th>Edição</th><th>Detalhe</th></tr></thead>
      <tbody>
        <template v-for="e in execucoes" :key="String(e.id_execucao)">
          <tr>
            <td>{{ quando(e.inicio) }}</td><td>{{ e.comando }}</td><td><Status :codigo="e.status as string" /></td>
            <td class="num">{{ e.series_processadas }}</td><td class="num">{{ e.registros }}</td><td>{{ duracao(e) }}</td>
            <td>{{ e.id_edicao ?? '—' }}</td>
            <td>
              <span v-if="e.observacao" class="muted">{{ e.observacao }} </span>
              <button v-if="e.erro" class="botao-texto" type="button"
                      @click="aberta = aberta === e.id_execucao ? null : String(e.id_execucao)">
                {{ aberta === e.id_execucao ? 'Ocultar erro' : 'Ver erro' }}
              </button>
            </td>
          </tr>
          <tr v-if="aberta === e.id_execucao"><td colspan="8"><pre style="white-space:pre-wrap;margin:0;font-size:.78rem">{{ e.erro }}</pre></td></tr>
        </template>
      </tbody>
    </table>
  </div>

  <div class="grade-2">
    <div class="cartao tabela-rolagem">
      <h3>Edições publicadas</h3>
      <table class="tabela">
        <thead><tr><th>Edição</th><th>Publicada em</th><th>Data de corte</th><th></th></tr></thead>
        <tbody>
          <tr v-for="e in estado.edicoes" :key="e.id_edicao">
            <td>{{ e.id_edicao }}</td><td>{{ quando(e.publicado_em) }}</td><td>{{ e.data_corte }}</td>
            <td>{{ e.id_edicao === estado.ativa ? 'ativa' : '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="cartao tabela-rolagem">
      <h3>Observações rejeitadas nesta edição ({{ rejeitadas.length }})</h3>
      <p v-if="!rejeitadas.length" class="muted">Nenhuma observação foi reprovada na validação da Silver.</p>
      <table v-else class="tabela">
        <thead><tr><th>Série</th><th>Mês</th><th>Valor bruto</th><th>Motivo</th><th>Coletado em</th></tr></thead>
        <tbody>
          <tr v-for="r in rejeitadas" :key="`${r.id_serie}-${r.data_ref}-${r.coletado_em}`">
            <td>{{ r.id_serie }}</td><td>{{ r.data_ref }}</td><td>{{ r.valor_bruto }}</td><td>{{ r.motivo }}</td><td>{{ quando(r.coletado_em) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
