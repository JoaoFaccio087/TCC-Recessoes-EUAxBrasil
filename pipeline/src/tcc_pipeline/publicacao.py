"""Publicação de uma edição analítica (engenharia_de_dados.md, seções 6.2 e 8.3).

Fluxo: grava os Parquet numa pasta temporária, escreve o manifesto, valida, renomeia a
pasta para ``edicoes/<id_edicao>/`` e só então troca ``edicoes.json`` e ``atual.json`` com
``os.replace``. Se a validação falhar, ``atual.json`` fica intocado e o painel continua na
edição anterior.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from . import VERSAO_CONTRATO
from .contrato import TABELAS, Tabela
from .validacao import sha256_arquivo, validar_edicao

SUCESSO = "SUCESSO"
SEM_ALTERACOES = "SEM_ALTERACOES"
FALHA = "FALHA"

# Colunas que mudam a cada edição sem mudar os dados (ignoradas na detecção de SEM_ALTERACOES).
_FORA_DO_CONTEUDO = {"id_edicao", "publicado_em", "data_corte"}
_FORA_POR_TABELA = {"observacao_rejeitada": {"coletado_em", "id_execucao"}}


class ErroValidacao(RuntimeError):
    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("validação reprovou a edição:\n- " + "\n- ".join(erros))


@dataclass
class Resultado:
    status: str
    id_edicao: str | None
    pasta: Path | None
    linhas: int


def _sql_str(texto: str) -> str:
    return "'" + str(texto).replace("'", "''") + "'"


def _escrever_json(caminho: Path, dados: dict) -> None:
    """Escrita atômica: arquivo temporário + os.replace."""
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)


def _hash_conteudo(df: pd.DataFrame, t: Tabela) -> str:
    """Hash do conteúdo sem colunas que mudam a cada edição (para SEM_ALTERACOES)."""
    fora = _FORA_DO_CONTEUDO | _FORA_POR_TABELA.get(t.nome, set())
    cols = [c for c in t.nomes if c not in fora]
    ordem = [c for c in t.ordem if c in cols] or cols
    texto = df[cols].sort_values(ordem, kind="stable").to_csv(index=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def escrever_parquet(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, t: Tabela, destino: Path) -> int:
    faltando = [c for c in t.nomes if c not in df.columns]
    if faltando:
        raise ValueError(f"{t.nome}: colunas ausentes {faltando}")
    con.register("_df", df[t.nomes])
    selecao = ", ".join(f"CAST({c} AS {tipo}) AS {c}" for c, tipo in t.colunas)
    ordem = ", ".join(t.ordem) if t.ordem else "ALL"
    con.execute(
        f"COPY (SELECT {selecao} FROM _df ORDER BY {ordem}) TO {_sql_str(destino.as_posix())} "
        "(FORMAT parquet, COMPRESSION zstd)"
    )
    con.unregister("_df")
    return len(df)


def _manifesto_ativo(raiz: Path) -> dict | None:
    atual = raiz / "atual.json"
    if not atual.exists():
        return None
    ref = json.loads(atual.read_text(encoding="utf-8"))
    return json.loads((raiz / ref["manifesto"]).read_text(encoding="utf-8"))


def id_livre(raiz: Path | str, base: str) -> str:
    """``base`` (AAAAMMDD-HHMM) ou, se já usado no mesmo minuto, ``base-2``, ``base-3``...

    Chamado por quem tem o lock, antes de montar a Gold (o id vai dentro das tabelas).
    """
    raiz = Path(raiz)
    lista_path = raiz / "edicoes.json"
    usados = {e["id_edicao"] for e in json.loads(lista_path.read_text(encoding="utf-8"))["edicoes"]} \
        if lista_path.exists() else set()
    candidato, n = base, 1
    while candidato in usados or (raiz / "edicoes" / candidato).exists():
        n += 1
        candidato = f"{base}-{n}"
    return candidato


def publicar(
    raiz: Path | str,
    tabelas: dict[str, pd.DataFrame],
    id_edicao: str,
    publicado_em: dt.datetime,
    data_corte: dt.date,
    cobertura_minima: float = 0.90,
) -> Resultado:
    raiz = Path(raiz)
    pasta_edicoes = raiz / "edicoes"
    final = pasta_edicoes / id_edicao
    tmp = pasta_edicoes / f"{id_edicao}.{os.getpid()}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    arquivos, total = [], 0
    con = duckdb.connect()
    try:
        for t in TABELAS.values():
            n = escrever_parquet(con, tabelas[t.nome], t, tmp / t.arquivo)
            total += n
            arquivos.append({"arquivo": t.arquivo, "linhas": n,
                             "sha256": sha256_arquivo(tmp / t.arquivo),
                             "sha256_conteudo": _hash_conteudo(tabelas[t.nome], t)})
    finally:
        con.close()

    manifesto = {"versao_contrato": VERSAO_CONTRATO, "id_edicao": id_edicao,
                 "publicado_em": publicado_em.isoformat(), "data_corte": data_corte.isoformat(),
                 "arquivos": arquivos}
    _escrever_json(tmp / "manifesto.json", manifesto)

    erros = validar_edicao(tmp, cobertura_minima)
    if erros:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ErroValidacao(erros)

    ativo = _manifesto_ativo(raiz)
    if ativo is not None:
        antes = {a["arquivo"]: a.get("sha256_conteudo") for a in ativo["arquivos"]}
        agora = {a["arquivo"]: a["sha256_conteudo"] for a in arquivos}
        if antes == agora:
            shutil.rmtree(tmp, ignore_errors=True)
            return Resultado(SEM_ALTERACOES, ativo["id_edicao"], None, total)

    if final.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        raise FileExistsError(f"edição {id_edicao} já existe em {final} (usar id_livre)")
    os.replace(tmp, final)

    caminho_manifesto = f"edicoes/{id_edicao}/manifesto.json"
    lista_path = raiz / "edicoes.json"
    lista = (json.loads(lista_path.read_text(encoding="utf-8")) if lista_path.exists()
             else {"versao_contrato": VERSAO_CONTRATO, "edicoes": []})
    lista["edicoes"].append({"id_edicao": id_edicao, "publicado_em": publicado_em.isoformat(),
                             "data_corte": data_corte.isoformat(), "manifesto": caminho_manifesto})
    _escrever_json(lista_path, lista)
    _escrever_json(raiz / "atual.json", {"versao_contrato": VERSAO_CONTRATO,
                                         "id_edicao_ativa": id_edicao,
                                         "manifesto": caminho_manifesto})
    return Resultado(SUCESSO, id_edicao, final, total)
