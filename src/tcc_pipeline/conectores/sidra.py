"""Conector do IBGE/SIDRA (API em https://apisidra.ibge.gov.br, sem chave)."""

from __future__ import annotations

import datetime as dt
import json

from .http import ErroColeta, Resposta, obter

FONTE = "IBGE/SIDRA"
PASTA = "sidra"
URL = "https://apisidra.ibge.gov.br/values"

_ROTULOS_PERIODO = ("Mês (Código)", "Trimestre (Código)", "Trimestre Móvel (Código)")


def codigo_periodo(d: dt.date, frequencia: str) -> str:
    if frequencia == "T":
        return f"{d.year}{(d.month - 1) // 3 + 1:02d}"
    return f"{d.year}{d.month:02d}"


def montar_url(params: dict, inicio: dt.date, fim: dt.date, frequencia: str) -> str:
    periodos = f"{codigo_periodo(inicio, frequencia)}-{codigo_periodo(fim, frequencia)}"
    partes = [URL, "t", str(params["tabela"]), params.get("nivel", "n1"), "all",
              "v", str(params["variavel"]), "p", periodos]
    for cls, cat in (params.get("classificacoes") or {}).items():
        partes += [f"c{cls}", str(cat)]
    return "/".join(partes)


def baixar(serie: dict, inicio: dt.date, fim: dt.date, sessao=None, **kw) -> Resposta:
    params = serie.get("sidra")
    if not params:
        raise ErroColeta(f"série sem parâmetros 'sidra' em series.yaml ({serie.get('nome')})")
    url = montar_url(params, inicio, fim, serie["frequencia"])
    return obter(url, None, sessao=sessao, **kw)


def interpretar(conteudo: bytes) -> list[tuple[str, str, str | None]]:
    """(código do período, valor, unidade). A primeira linha da resposta é o cabeçalho."""
    dados = json.loads(conteudo)
    if not dados:
        return []
    cabecalho = dados[0]
    col = next((k for k, v in cabecalho.items() if v in _ROTULOS_PERIODO), None)
    if col is None:
        raise ValueError(f"resposta do SIDRA sem coluna de período: {cabecalho}")
    return [(linha[col], linha["V"], linha.get("MN")) for linha in dados[1:]]


def converter_data(texto: str, frequencia: str) -> dt.date:
    """'200712' -> 2007-12-01 (mês); '201904' -> 2019-10-01 (trimestre)."""
    if len(texto) != 6 or not texto.isdigit():
        raise ValueError(f"período fora do padrão: {texto}")
    ano, n = int(texto[:4]), int(texto[4:])
    if frequencia == "T":
        if not 1 <= n <= 4:
            raise ValueError(f"trimestre inválido: {texto}")
        return dt.date(ano, 3 * (n - 1) + 1, 1)
    if not 1 <= n <= 12:
        raise ValueError(f"mês inválido: {texto}")
    return dt.date(ano, n, 1)
