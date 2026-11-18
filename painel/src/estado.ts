// Estado compartilhado: edição aberta e "versão" que as telas observam para refazer consultas.
import { reactive } from 'vue'
import type { Edicao } from './dados'

export const estado = reactive({
  edicoes: [] as Edicao[],
  ativa: '',            // edição indicada em atual.json
  aberta: null as Edicao | null,
  versao: 0,            // muda a cada troca de edição
  carregando: true,
  erro: '' as string,
  msCarga: 0,
  msUltimaConsulta: 0,  // RNF05: tempo da última consulta da tela
})

/** Mede o tempo de uma atualização de tela (consulta + montagem). */
export async function medir<T>(f: () => Promise<T>): Promise<T> {
  const t0 = performance.now()
  try {
    return await f()
  } finally {
    estado.msUltimaConsulta = performance.now() - t0
  }
}
