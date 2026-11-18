"""Conector do Comex Stat (API do MDIC em https://api-comexstat.mdic.gov.br, sem chave).

Consulta ``POST /general`` com o fluxo de exportação, detalhe mensal e filtro por país.
Atenção: a API interpreta ``period`` como anos × meses (de "2004-12" a "2013-12" devolve só
os dezembros). Por isso a consulta vai sempre de janeiro do primeiro ano a dezembro do último.
Valores em US$ FOB (unidades, não milhões). Dados desde 1997.
"""

from __future__ import annotations

import datetime as dt
import json

from .http import ErroColeta, Resposta, obter

FONTE = "Comex Stat"
PASTA = "comexstat"
URL = "https://api-comexstat.mdic.gov.br/general"


def corpo(params: dict, inicio: dt.date, fim: dt.date) -> dict:
    return {
        "flow": params.get("fluxo", "export"),
        "monthDetail": True,
        "period": {"from": f"{inicio.year}-01", "to": f"{fim.year}-12"},
        "filters": [{"filter": "country", "values": [int(params["pais"])]}],
        "details": ["country"],
        "metrics": ["metricFOB"],
    }


def baixar(serie: dict, inicio: dt.date, fim: dt.date, sessao=None, **kw) -> Resposta:
    params = serie.get("comexstat")
    if not params:
        raise ErroColeta(f"série sem parâmetros 'comexstat' em series.yaml ({serie.get('nome')})")
    return obter(URL, {"language": "pt"}, sessao=sessao, corpo_json=corpo(params, inicio, fim), **kw)


def interpretar(conteudo: bytes) -> list[tuple[str, object, str | None]]:
    dados = json.loads(conteudo)
    if not dados.get("success", True):
        raise ValueError(f"Comex Stat recusou a consulta: {dados.get('message')}")
    return [(f"{o['year']}-{o['monthNumber']}", o["metricFOB"], None)
            for o in dados["data"]["list"]]


def converter_data(texto: str, frequencia: str) -> dt.date:
    """'2007-11' -> 2007-11-01."""
    ano, _, mes = str(texto).partition("-")
    if frequencia != "M" or not (ano.isdigit() and mes.isdigit() and len(ano) == 4):
        raise ValueError(f"período fora do padrão: {texto}")
    return dt.date(int(ano), int(mes), 1)
