/// <reference types="node" />
// Painel do TCC (seção 5 do engenharia_de_dados.md; texto 4.7 e 5.3).
// Em desenvolvimento e no preview, o Vite serve a pasta de publicação da pipeline
// (<TCC_DADOS>/publicacao) em /dados/. O painel não tem API própria (D1): só lê arquivos.
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs'
import { extname, join, normalize, resolve, sep } from 'node:path'
import type { Connect, Plugin } from 'vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const RAIZ_PROJETO = resolve(__dirname, '..')

/** Lê TCC_DADOS do ambiente ou do .env da raiz do projeto (mesma regra do Python). */
function pastaPublicacao(): string {
  let dados = process.env.TCC_DADOS
  const env = join(RAIZ_PROJETO, '.env')
  if (!dados && existsSync(env)) {
    for (const linha of readFileSync(env, 'utf-8').replace(/^﻿/, '').split(/\r?\n/)) {
      const m = linha.match(/^\s*TCC_DADOS\s*=\s*(.+?)\s*$/)
      if (m) dados = m[1].replace(/^["']|["']$/g, '')
    }
  }
  // TCC_PUBLICACAO permite apontar para outra raiz (ex.: a edição sintética de gerar-exemplo).
  return process.env.TCC_PUBLICACAO ?? join(dados ?? join(RAIZ_PROJETO, 'dados'), 'publicacao')
}

const TIPOS: Record<string, string> = {
  '.json': 'application/json; charset=utf-8',
  '.parquet': 'application/vnd.apache.parquet',
}
// Seção 6.3: atual.json, edicoes.json e controle_execucao.parquet sem cache; edições imutáveis.
const SEM_CACHE = new Set(['atual.json', 'edicoes.json', 'controle_execucao.parquet'])

function servirPublicacao(): Plugin {
  const raiz = pastaPublicacao()
  const middleware: Connect.NextHandleFunction = (req, res, next) => {
    const url = decodeURIComponent((req.url ?? '').split('?')[0])
    if (!url.startsWith('/dados/')) return next()
    const relativo = url.slice('/dados/'.length)
    const arquivo = normalize(join(raiz, relativo))
    if (!arquivo.startsWith(normalize(raiz) + sep) || !existsSync(arquivo) || !statSync(arquivo).isFile()) {
      res.statusCode = 404
      return res.end('não encontrado')
    }
    res.setHeader('Content-Type', TIPOS[extname(arquivo)] ?? 'application/octet-stream')
    res.setHeader('Cache-Control', SEM_CACHE.has(relativo) ? 'no-store'
      : 'public, max-age=31536000, immutable')
    createReadStream(arquivo).pipe(res)
  }
  return {
    name: 'tcc-servir-publicacao',
    configureServer(server) {
      server.config.logger.info(`  dados: /dados/ -> ${raiz}`)
      server.middlewares.use(middleware)
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware)
    },
  }
}

export default defineConfig({
  plugins: [vue(), servirPublicacao()],
  optimizeDeps: { exclude: ['@duckdb/duckdb-wasm'] },
  server: { port: 5173 },
})
