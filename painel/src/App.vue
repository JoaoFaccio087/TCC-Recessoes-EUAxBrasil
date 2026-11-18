<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { abrirEdicao, lerIndice } from './dados'
import { estado } from './estado'
import Comparativo from './telas/Comparativo.vue'
import Episodios from './telas/Episodios.vue'
import Resumo from './telas/Resumo.vue'
import Hipoteses from './telas/Hipoteses.vue'
import Manutencao from './telas/Manutencao.vue'
import Glossario from './telas/Glossario.vue'

const ABAS = [
  { id: 'comparativo', nome: 'EUA × Brasil', comp: Comparativo },
  { id: 'episodios', nome: 'Comparar episódios', comp: Episodios },
  { id: 'resumo', nome: 'Quadro-resumo', comp: Resumo },
  { id: 'hipoteses', nome: 'Hipóteses', comp: Hipoteses },
  { id: 'manutencao', nome: 'Manutenção', comp: Manutencao },
  { id: 'glossario', nome: 'Glossário', comp: Glossario },
]
const aba = ref(new URLSearchParams(location.search).get('aba') ?? 'comparativo')
function trocarAba(id: string) {
  aba.value = id
  const u = new URL(location.href)
  u.searchParams.set('aba', id)
  history.replaceState(null, '', u)
}

async function abrir(id: string) {
  const e = estado.edicoes.find((x) => x.id_edicao === id)
  if (!e) return
  estado.carregando = true
  estado.erro = ''
  try {
    const r = await abrirEdicao(e)
    estado.aberta = e
    estado.msCarga = r.ms
    estado.versao++
  } catch (err) {
    estado.erro = `Não foi possível abrir a edição ${id}: ${(err as Error).message}`
  } finally {
    estado.carregando = false
  }
}

onMounted(async () => {
  try {
    const idx = await lerIndice()
    estado.edicoes = idx.edicoes
    estado.ativa = idx.ativa
    await abrir(idx.ativa)
  } catch (err) {
    estado.erro = `Nenhuma edição publicada encontrada (${(err as Error).message}). ` +
      'Rode a pipeline (atualizar) ou gerar-exemplo e confira TCC_DADOS.'
    estado.carregando = false
  }
})
const dataHora = (s: string) => new Date(s).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <header class="cabecalho">
    <div>
      <h1>Recessões norte-americanas e a economia brasileira</h1>
      <div class="sub">1981-1982 · 2007-2009 · 2020 — indicadores alinhados ao pico de cada recessão (NBER)</div>
    </div>
    <label class="filtros" v-if="estado.edicoes.length">
      <span class="muted">Edição analítica</span>
      <select :value="estado.aberta?.id_edicao" @change="abrir(($event.target as HTMLSelectElement).value)">
        <option v-for="e in estado.edicoes" :key="e.id_edicao" :value="e.id_edicao">
          {{ e.id_edicao }} ({{ dataHora(e.publicado_em) }}){{ e.id_edicao === estado.ativa ? ' — ativa' : '' }}
        </option>
      </select>
    </label>
  </header>
  <nav class="abas" role="tablist">
    <button v-for="a in ABAS" :key="a.id" role="tab" :aria-selected="aba === a.id" @click="trocarAba(a.id)">
      {{ a.nome }}
    </button>
  </nav>
  <main>
    <div v-if="estado.erro" class="erro">{{ estado.erro }}</div>
    <div v-else-if="estado.carregando && !estado.aberta" class="muted">Carregando a edição…</div>
    <template v-else-if="estado.aberta">
      <div v-if="estado.aberta.id_edicao !== estado.ativa" class="aviso">
        Você está vendo a edição {{ estado.aberta.id_edicao }}, que não é a ativa ({{ estado.ativa }}).
      </div>
      <component :is="ABAS.find((a) => a.id === aba)?.comp ?? Comparativo" :key="aba" />
      <p class="muted">
        Edição {{ estado.aberta.id_edicao }} · data de corte {{ estado.aberta.data_corte }} ·
        carga {{ Math.round(estado.msCarga) }} ms · última consulta {{ Math.round(estado.msUltimaConsulta) }} ms
      </p>
    </template>
  </main>
</template>
