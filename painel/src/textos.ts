// Textos em português para códigos do contrato (RNF08, RF12).
export type Tom = 'bom' | 'alerta' | 'critico' | 'neutro'

export const STATUS: Record<string, { texto: string; tom: Tom; icone: string; explicacao: string }> = {
  OK: { texto: 'Calculada', tom: 'bom', icone: '✓', explicacao: 'Medida calculada.' },
  SEM_DADOS: { texto: 'Sem dados', tom: 'neutro', icone: '–',
    explicacao: 'Não há série ou observações para o episódio.' },
  INCOMPATIVEL: { texto: 'Incompatível', tom: 'neutro', icone: '≠',
    explicacao: 'Série sem par ou par sem frequência comum.' },
  RECUPERACAO_NAO_OBSERVADA: { texto: 'Não recuperou', tom: 'alerta', icone: '…',
    explicacao: 'A série não voltou ao nível do pico dentro da janela de 60 meses (20 trimestres).' },
  REACAO_NAO_OBSERVADA: { texto: 'Sem reação', tom: 'neutro', icone: '○',
    explicacao: 'A série não ultrapassou o limiar do grupo pelo número mínimo de meses seguidos nos 24 meses após o pico.' },
  COBERTURA_INSUFICIENTE: { texto: 'Lacunas', tom: 'critico', icone: '!',
    explicacao: 'Lacunas na série impedem o cálculo.' },
  NAO_APLICAVEL: { texto: 'Não se aplica', tom: 'neutro', icone: '–',
    explicacao: 'Pior valor e recuperação não se aplicam a juros e inflação (podem reagir nos dois sentidos).' },
  REJEITADO: { texto: 'Rejeitado', tom: 'critico', icone: '!',
    explicacao: 'Observação reprovada na validação; tratada como lacuna.' },
  // Execuções (RF13)
  SUCESSO: { texto: 'Sucesso', tom: 'bom', icone: '✓', explicacao: 'Nova edição publicada.' },
  SEM_ALTERACOES: { texto: 'Sem alterações', tom: 'neutro', icone: '=',
    explicacao: 'Conteúdo igual ao da edição ativa; nada publicado.' },
  FALHA: { texto: 'Falha', tom: 'critico', icone: '✕',
    explicacao: 'A execução falhou; o painel mantém a edição anterior.' },
  BLOQUEADO: { texto: 'Bloqueado', tom: 'alerta', icone: '⏸',
    explicacao: 'Outra execução estava em andamento (trava).' },
  // Hipóteses
  sustentada: { texto: 'Sustentada', tom: 'bom', icone: '✓', explicacao: '' },
  'não sustentada': { texto: 'Não sustentada', tom: 'critico', icone: '✕', explicacao: '' },
  inconclusiva: { texto: 'Inconclusiva', tom: 'alerta', icone: '?', explicacao: '' },
}

export function status(codigo: string | null | undefined) {
  if (!codigo) return { texto: '—', tom: 'neutro' as Tom, icone: '', explicacao: '' }
  return STATUS[codigo] ?? { texto: codigo, tom: 'neutro' as Tom, icone: '', explicacao: '' }
}

export const PAIS: Record<string, string> = { EUA: 'Estados Unidos', BR: 'Brasil' }
export const FREQ: Record<string, string> = { M: 'mensal', T: 'trimestral', A: 'anual' }
export const SENTIDO: Record<string, string> = { queda: 'queda', alta: 'alta', ambos: 'qualquer direção' }

export function unidadePainel(tipoMedida: string): string {
  return tipoMedida === 'taxa' ? 'Diferença em pontos percentuais em relação ao pico'
    : 'Número-índice (pico = 100)'
}

export function num(v: unknown, casas = 1): string {
  if (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) return '—'
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

export function periodo(n: unknown, freq: unknown): string {
  if (n === null || n === undefined) return '—'
  const t = freq === 'T' ? 'trimestre' : 'mês'
  const p = freq === 'T' ? 'trimestres' : 'meses'
  return `${n} ${Math.abs(Number(n)) === 1 ? t : p}`
}
