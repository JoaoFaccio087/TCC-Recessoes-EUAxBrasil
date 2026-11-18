"""Registro das execuções (RF13; D18, D23).

Cada execução grava ``dados/controle/<id_execucao>.json``. Só quem detém o lock refaz
``publicacao/controle_execucao.parquet`` a partir desses arquivos, com ``os.replace``.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import duckdb
import pandas as pd

COLUNAS = {
    "id_execucao": "VARCHAR", "inicio": "TIMESTAMP", "fim": "TIMESTAMP", "comando": "VARCHAR",
    "series_processadas": "INTEGER", "registros": "BIGINT", "status": "VARCHAR",
    "id_edicao": "VARCHAR", "erro": "VARCHAR", "observacao": "VARCHAR",
}

SUCESSO, SEM_ALTERACOES, FALHA, BLOQUEADO = "SUCESSO", "SEM_ALTERACOES", "FALHA", "BLOQUEADO"


def novo_id(agora: dt.datetime | None = None) -> str:
    agora = agora or dt.datetime.now(dt.timezone.utc)
    return f"{agora.astimezone(dt.timezone.utc):%Y%m%dT%H%M%S%fZ}-{os.getpid()}"


def registrar(pasta_dados: Path, registro: dict) -> Path:
    pasta = Path(pasta_dados) / "controle"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{registro['id_execucao']}.json"
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps(registro, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, destino)
    return destino


def reconstruir_parquet(pasta_dados: Path, raiz_publicacao: Path) -> Path:
    regs = [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((Path(pasta_dados) / "controle").glob("*.json"))]
    df = pd.DataFrame([{c: r.get(c) for c in COLUNAS} for r in regs], columns=list(COLUNAS))
    for c in ("inicio", "fim"):
        df[c] = pd.to_datetime(df[c], utc=True).dt.tz_localize(None)
    raiz = Path(raiz_publicacao)
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / "controle_execucao.parquet"
    tmp = raiz / "controle_execucao.parquet.tmp"
    con = duckdb.connect()
    try:
        con.register("_df", df)
        sel = ", ".join(f"CAST({c} AS {t}) AS {c}" for c, t in COLUNAS.items())
        con.execute(f"COPY (SELECT {sel} FROM _df ORDER BY inicio) TO '{tmp.as_posix()}' "
                    "(FORMAT parquet, COMPRESSION zstd)")
    finally:
        con.close()
    os.replace(tmp, destino)
    return destino
