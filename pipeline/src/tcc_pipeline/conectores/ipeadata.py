"""Conector do Ipeadata (API OData v4 em http://www.ipeadata.gov.br/api/odata4, sem chave).

Baixa a série inteira (``ValoresSerie``): a API é lenta para filtros por data e as séries
usadas são pequenas. A Gold recorta a janela de cada episódio.
"""

from __future__ import annotations

import datetime as dt
import json

from .http import Resposta, obter

FONTE = "Ipeadata"
PASTA = "ipeadata"
URL = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"


def baixar(serie: dict, inicio: dt.date, fim: dt.date, sessao=None, **kw) -> Resposta:
    return obter(URL.format(codigo=serie["codigo_origem"]), None, sessao=sessao, **kw)


def interpretar(conteudo: bytes) -> list[tuple[str, object, str | None]]:
    """(data, valor, unidade). ``VALVALOR`` nulo = ausência."""
    dados = json.loads(conteudo)
    return [(o["VALDATA"], o["VALVALOR"], None) for o in dados["value"]]


def converter_data(texto: str, frequencia: str) -> dt.date:
    """'1981-07-01T00:00:00-03:00' -> 1981-07-01. Exige o primeiro dia do mês/trimestre/ano."""
    d = dt.date.fromisoformat(str(texto)[:10])
    if d.day != 1 or (frequencia == "T" and d.month not in (1, 4, 7, 10)) \
            or (frequencia == "A" and d.month != 1):
        raise ValueError(f"data fora do padrão: {texto}")
    return d
