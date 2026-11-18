"""Camada Silver, reconstruída inteira a partir do Bronze (seções 2.1 e 6.2; D15).

Percorre as coletas em ordem cronológica e padroniza data (primeiro dia do mês/trimestre),
valor (DOUBLE), unidade e símbolos de ausência. Em ``observacao`` entra uma linha só quando o
valor de ``(id_serie, data_ref)`` é novo ou mudou em relação à coleta anterior: a versão
revisada é registrada sem apagar a anterior. Observações reprovadas vão para
``observacao_rejeitada`` com o motivo e não entram em ``observacao``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import os
from pathlib import Path

import duckdb
import pandas as pd

from . import bronze
from .config import Config
from .conectores import conector

AUSENCIA = {"", ".", "..", "...", "-", "x", "X"}

COLUNAS_OBS = ["id_serie", "data_ref", "valor", "coletado_em", "id_execucao", "arquivo_bronze"]
COLUNAS_REJ = ["id_serie", "data_ref", "valor_bruto", "motivo", "coletado_em", "id_execucao"]
COLUNAS_META = ["id_serie", "fonte", "codigo_origem", "ultima_coleta", "id_execucao",
                "n_observacoes", "inicio", "fim"]


class ErroBronze(RuntimeError):
    """Arquivo do Bronze ausente ou com hash diferente do manifesto."""


def _faixa(serie: dict) -> tuple[float, float, bool]:
    """(mínimo, máximo, mínimo exclusivo)."""
    if "faixa" in serie:
        a, b = serie["faixa"]
        return float(a), float(b), False
    if serie["tipo_medida"] == "nivel":
        return 0.0, math.inf, True
    return -math.inf, math.inf, False


def padronizar(serie: dict, mod, data_bruta: str, valor_bruto, unidade: str | None):
    """Devolve ('ok', data, valor), ('ausente', None, None) ou ('rejeitada', data|None, motivo)."""
    texto = "" if valor_bruto is None else str(valor_bruto).strip()
    try:
        data = mod.converter_data(str(data_bruta), serie["frequencia"])
    except ValueError:
        return "rejeitada", None, "data fora do padrão"
    if texto in AUSENCIA:
        return "ausente", data, None
    esperado = serie.get("unidade_fonte")
    if esperado and unidade and unidade != esperado:
        return "rejeitada", data, f"unidade incoerente: {unidade!r} (esperado {esperado!r})"
    try:
        valor = float(texto)
    except ValueError:
        return "rejeitada", data, "tipo inválido"
    if not math.isfinite(valor):
        return "rejeitada", data, "tipo inválido"
    a, b, excl = _faixa(serie)
    if (valor <= a if excl else valor < a) or valor > b:
        return "rejeitada", data, "valor fora da faixa plausível"
    return "ok", data, valor


def reconstruir(cfg: Config, pasta_dados: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pasta_dados = Path(pasta_dados)
    ultimo: dict[tuple[str, dt.date], float] = {}
    obs, rej, meta = [], [], {}
    for man in bronze.manifestos(pasta_dados):
        id_exec = man["id_execucao"]
        for a in man["arquivos"]:
            id_s = a["id_serie"]
            if a["status"] != bronze.OK or id_s not in cfg.series:
                continue
            serie = cfg.series[id_s]
            caminho = pasta_dados / a["caminho"]
            if not caminho.exists():
                raise ErroBronze(f"arquivo do Bronze ausente: {caminho}")
            conteudo = caminho.read_bytes()
            if hashlib.sha256(conteudo).hexdigest() != a["sha256"]:
                raise ErroBronze(f"hash do Bronze não confere: {caminho}")
            mod = conector(a["fonte"])
            coletado = (dt.datetime.fromisoformat(a["coletado_em"])
                        .astimezone(dt.timezone.utc).replace(tzinfo=None))
            n = 0
            datas = []
            for data_bruta, valor_bruto, unidade in mod.interpretar(conteudo):
                estado, data, x = padronizar(serie, mod, data_bruta, valor_bruto, unidade)
                if estado == "rejeitada":
                    rej.append((id_s, data, None if valor_bruto is None else str(valor_bruto),
                                x, coletado, id_exec))
                    continue
                if estado == "ausente":
                    continue
                n += 1
                datas.append(data)
                if ultimo.get((id_s, data)) != x:
                    ultimo[(id_s, data)] = x
                    obs.append((id_s, data, x, coletado, id_exec, a["caminho"]))
            meta[id_s] = (id_s, a["fonte"], a.get("codigo_origem"), coletado, id_exec, n,
                          min(datas, default=None), max(datas, default=None))
    return (pd.DataFrame(obs, columns=COLUNAS_OBS),
            pd.DataFrame(rej, columns=COLUNAS_REJ),
            pd.DataFrame(list(meta.values()), columns=COLUNAS_META))


_TIPOS = {
    "observacao": {"id_serie": "VARCHAR", "data_ref": "DATE", "valor": "DOUBLE",
                   "coletado_em": "TIMESTAMP", "id_execucao": "VARCHAR", "arquivo_bronze": "VARCHAR"},
    "observacao_rejeitada": {"id_serie": "VARCHAR", "data_ref": "DATE", "valor_bruto": "VARCHAR",
                             "motivo": "VARCHAR", "coletado_em": "TIMESTAMP", "id_execucao": "VARCHAR"},
    "serie_metadado": {"id_serie": "VARCHAR", "fonte": "VARCHAR", "codigo_origem": "VARCHAR",
                       "ultima_coleta": "TIMESTAMP", "id_execucao": "VARCHAR",
                       "n_observacoes": "INTEGER", "inicio": "DATE", "fim": "DATE"},
}


def gravar(pasta_dados: Path, obs: pd.DataFrame, rej: pd.DataFrame, meta: pd.DataFrame) -> None:
    pasta = Path(pasta_dados) / "silver"
    pasta.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        for nome, df in (("observacao", obs), ("observacao_rejeitada", rej), ("serie_metadado", meta)):
            tipos = _TIPOS[nome]
            con.register("_df", df[list(tipos)])
            sel = ", ".join(f"CAST({c} AS {t}) AS {c}" for c, t in tipos.items())
            destino = pasta / f"{nome}.parquet"
            tmp = destino.with_suffix(".parquet.tmp")
            con.execute(f"COPY (SELECT {sel} FROM _df ORDER BY ALL) TO '{tmp.as_posix()}' "
                        "(FORMAT parquet, COMPRESSION zstd)")
            con.unregister("_df")
            os.replace(tmp, destino)
    finally:
        con.close()


def ultimos_valores(obs: pd.DataFrame) -> pd.DataFrame:
    """Para cada (id_serie, data_ref), o valor da coleta mais recente (entrada da Gold)."""
    if obs.empty:
        return obs.copy()
    return (obs.sort_values(["id_serie", "data_ref", "coletado_em"])
               .groupby(["id_serie", "data_ref"], as_index=False).last())


def rejeicoes_atuais(rej: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Rejeições da coleta mais recente de cada série (estado atual, para a edição)."""
    if rej.empty:
        return rej.copy()
    atual = rej.merge(meta[["id_serie", "id_execucao"]], on=["id_serie", "id_execucao"])
    return atual.drop_duplicates(["id_serie", "data_ref", "coletado_em"])
