"""Validação de uma edição antes de publicar (engenharia_de_dados.md, seção 9)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb

from .contrato import REFERENCIAS, TABELAS

TOL = 1e-9


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _sql_str(texto: str) -> str:
    return "'" + str(texto).replace("'", "''") + "'"


def conectar(pasta: Path) -> duckdb.DuckDBPyConnection:
    """Abre a edição no DuckDB com uma view por tabela (como o painel fará)."""
    con = duckdb.connect()
    for t in TABELAS.values():
        arq = pasta / t.arquivo
        if arq.exists():
            con.execute(f"CREATE VIEW {t.nome} AS SELECT * FROM read_parquet({_sql_str(arq.as_posix())})")
    return con


def validar_edicao(pasta: Path | str, cobertura_minima: float = 0.90) -> list[str]:
    """Devolve a lista de erros (vazia = edição aprovada)."""
    pasta = Path(pasta)
    erros: list[str] = []

    faltando = [t.arquivo for t in TABELAS.values() if not (pasta / t.arquivo).exists()]
    if faltando:
        return [f"arquivos ausentes: {faltando}"]
    con = conectar(pasta)

    # Esquema
    for t in TABELAS.values():
        real = [(r[0], r[1]) for r in con.execute(f"DESCRIBE {t.nome}").fetchall()]
        if real != list(t.colunas):
            erros.append(f"{t.nome}: esquema difere do contrato: {real}")
    if erros:
        return erros

    # Unicidade
    for t in TABELAS.values():
        chave = ", ".join(t.chave)
        n = con.execute(
            f"SELECT count(*) FROM (SELECT {chave} FROM {t.nome} GROUP BY ALL HAVING count(*) > 1)"
        ).fetchone()[0]
        if n:
            erros.append(f"{t.nome}: {n} chaves duplicadas em ({chave})")

    # Integridade
    for tab, col, dim, col_dim in REFERENCIAS:
        orfaos = con.execute(
            f"SELECT DISTINCT {col} FROM {tab} WHERE {col} IS NOT NULL "
            f"AND {col} NOT IN (SELECT {col_dim} FROM {dim})"
        ).fetchall()
        if orfaos:
            erros.append(f"{tab}.{col}: sem correspondência em {dim}: {[o[0] for o in orfaos][:5]}")

    # Alinhamento: t_rel = 0 no pico; valor_painel = 100 (nível) ou 0 (taxa)
    for f, tab, col_pico in (("M", "fato_serie_alinhada_mensal", "pico_mensal"),
                             ("T", "fato_serie_alinhada_trimestral", "pico_trimestral")):
        ruins = con.execute(f"""
            SELECT a.id_episodio, a.id_serie, a.data_ref, a.valor_painel
            FROM {tab} a JOIN dim_serie s USING (id_serie) JOIN dim_episodio e USING (id_episodio)
            WHERE a.t_rel = 0 AND (
                a.data_ref <> e.{col_pico}
                OR (a.status = 'OK' AND abs(a.valor_painel -
                    CASE s.tipo_medida WHEN 'nivel' THEN 100 ELSE 0 END) > {TOL}))
        """).fetchall()
        if ruins:
            erros.append(f"{tab}: alinhamento incorreto em t_rel = 0: {ruins[:5]}")
        fora = con.execute(
            f"SELECT count(*) FROM {tab} a JOIN dim_serie s USING (id_serie) WHERE s.frequencia <> '{f}'"
        ).fetchone()[0]
        if fora:
            erros.append(f"{tab}: {fora} linhas com frequência diferente de {f}")

    # Cobertura (exceto séries/episódios SEM_DADOS)
    baixas = con.execute(f"""
        SELECT id_episodio, id_serie, cobertura FROM fato_resumo_episodio
        WHERE status_reacao <> 'SEM_DADOS' AND cobertura < {cobertura_minima}
    """).fetchall()
    if baixas:
        erros.append(f"cobertura abaixo de {cobertura_minima:.0%}: {baixas}")

    con.close()

    # Manifesto
    manifesto = pasta / "manifesto.json"
    if not manifesto.exists():
        erros.append("manifesto.json ausente")
    else:
        dados = json.loads(manifesto.read_text(encoding="utf-8"))
        for a in dados["arquivos"]:
            arq = pasta / a["arquivo"]
            if not arq.exists():
                erros.append(f"manifesto: {a['arquivo']} ausente")
            elif sha256_arquivo(arq) != a["sha256"]:
                erros.append(f"manifesto: hash de {a['arquivo']} não confere")
        listados = {a["arquivo"] for a in dados["arquivos"]}
        if listados != {t.arquivo for t in TABELAS.values()}:
            erros.append("manifesto: lista de arquivos difere do contrato")
    return erros


def edicao_ativa(raiz_publicacao: Path | str) -> Path:
    raiz = Path(raiz_publicacao)
    atual = json.loads((raiz / "atual.json").read_text(encoding="utf-8"))
    return (raiz / atual["manifesto"]).parent
