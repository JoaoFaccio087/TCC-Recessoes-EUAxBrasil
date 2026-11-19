// Acesso à edição publicada com DuckDB-Wasm (D1, D16, D20; texto 4.7 e 5.3).
// A edição inteira é baixada uma vez (registerFileBuffer) e vira um conjunto de views.
// Todas as consultas seguintes rodam em memória no navegador.
import * as duckdb from '@duckdb/duckdb-wasm'
import mvpWasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url'
import mvpWorker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url'
import ehWasm from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url'
import ehWorker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url'

export const BASE = import.meta.env.VITE_DADOS_URL ?? '/dados/'

export interface Edicao {
  id_edicao: string
  publicado_em: string
  data_corte: string
  manifesto: string
}
interface Manifesto {
  versao_contrato: number
  id_edicao: string
  arquivos: { arquivo: string; linhas: number; sha256: string }[]
}
export type Linha = Record<string, string | number | boolean | null>

let banco: duckdb.AsyncDuckDB | null = null
let conexao: duckdb.AsyncDuckDBConnection | null = null

async function iniciar(): Promise<duckdb.AsyncDuckDBConnection> {
  if (conexao) return conexao
  const bundle = await duckdb.selectBundle({
    mvp: { mainModule: mvpWasm, mainWorker: mvpWorker },
    eh: { mainModule: ehWasm, mainWorker: ehWorker },
  })
  const worker = new Worker(bundle.mainWorker!)
  banco = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker)
  await banco.instantiate(bundle.mainModule, bundle.pthreadWorker)
  conexao = await banco.connect()
  return conexao
}

async function json<T>(caminho: string): Promise<T> {
  const r = await fetch(BASE + caminho, { cache: 'no-store' })
  if (!r.ok) throw new Error(`não foi possível ler ${caminho} (HTTP ${r.status})`)
  return r.json() as Promise<T>
}

async function bytes(caminho: string, cache: RequestCache): Promise<Uint8Array> {
  const r = await fetch(BASE + caminho, { cache })
  if (!r.ok) throw new Error(`não foi possível ler ${caminho} (HTTP ${r.status})`)
  return new Uint8Array(await r.arrayBuffer())
}

export async function lerIndice(): Promise<{ ativa: string; edicoes: Edicao[] }> {
  const atual = await json<{ id_edicao_ativa: string }>('atual.json')
  const lista = await json<{ edicoes: Edicao[] }>('edicoes.json')
  return { ativa: atual.id_edicao_ativa, edicoes: [...lista.edicoes].reverse() }
}

/** Baixa os Parquet da edição e recria as views com o nome de cada tabela do contrato. */
export async function abrirEdicao(edicao: Edicao): Promise<{ tabelas: string[]; ms: number }> {
  const t0 = performance.now()
  const con = await iniciar()
  const man = await json<Manifesto>(edicao.manifesto)
  const pasta = edicao.manifesto.slice(0, edicao.manifesto.lastIndexOf('/') + 1)
  const tabelas: string[] = []
  await Promise.all(man.arquivos.map(async (a) => {
    const nomeArquivo = `${edicao.id_edicao}__${a.arquivo}`
    await banco!.registerFileBuffer(nomeArquivo, await bytes(pasta + a.arquivo, 'force-cache'))
    const tabela = a.arquivo.replace(/\.parquet$/, '')
    await con.query(`CREATE OR REPLACE VIEW ${tabela} AS SELECT * FROM read_parquet('${nomeArquivo}')`)
    tabelas.push(tabela)
  }))
  // Fora da edição e sem cache: registro de todas as execuções (D18).
  try {
    await banco!.registerFileBuffer('controle_execucao.parquet',
      await bytes('controle_execucao.parquet', 'no-store'))
    await con.query(`CREATE OR REPLACE VIEW controle_execucao AS
                     SELECT * FROM read_parquet('controle_execucao.parquet')`)
  } catch {
    await con.query(`CREATE OR REPLACE VIEW controle_execucao AS SELECT NULL AS id_execucao WHERE false`)
  }
  return { tabelas, ms: performance.now() - t0 }
}

function normalizar(v: unknown): string | number | boolean | null {
  if (v === null || v === undefined) return null
  if (typeof v === 'bigint') return Number(v)
  if (typeof v === 'number' || typeof v === 'boolean' || typeof v === 'string') return v
  return String(v)
}

/** Executa SQL e devolve linhas simples. Datas e horários devem vir convertidos em texto no SQL. */
export async function consultar(sql: string, params: unknown[] = []): Promise<Linha[]> {
  const con = await iniciar()
  const tabela = params.length
    ? await (await con.prepare(sql)).query(...params)
    : await con.query(sql)
  const nomes = tabela.schema.fields.map((f) => f.name)
  return tabela.toArray().map((r) => {
    const o: Linha = {}
    const j = r.toJSON() as Record<string, unknown>
    for (const n of nomes) o[n] = normalizar(j[n])
    return o
  })
}

/** CSV com separador ';', ponto decimal e BOM UTF-8 (abre no Excel e em qualquer ferramenta). */
export function baixarCsv(linhas: Linha[], nomeArquivo: string): void {
  if (!linhas.length) return
  const cols = Object.keys(linhas[0])
  const esc = (v: unknown) => {
    if (v === null || v === undefined) return ''
    const s = String(v)
    return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const texto = [cols.join(';'), ...linhas.map((l) => cols.map((c) => esc(l[c])).join(';'))].join('\n')
  const blob = new Blob(['﻿' + texto], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = nomeArquivo
  a.click()
  URL.revokeObjectURL(a.href)
}
