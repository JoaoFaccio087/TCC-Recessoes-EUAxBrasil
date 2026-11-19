"""Conector do FRED (API REST, chave em ``FRED_API_KEY``, 120 requisições por minuto)."""

from __future__ import annotations

import datetime as dt
import json
import os

from .http import ErroColeta, LimiteTaxa, Resposta, obter

FONTE = "FRED"
PASTA = "fred"
URL = "https://api.stlouisfed.org/fred/series/observations"
LIMITE = LimiteTaxa(120)


def baixar(serie: dict, inicio: dt.date, fim: dt.date, sessao=None, **kw) -> Resposta:
    chave = os.environ.get("FRED_API_KEY")
    if not chave:
        raise ErroColeta("FRED_API_KEY não definida (preencher no .env)")
    parametros = {
        "series_id": serie["codigo_origem"],
        "api_key": chave,
        "file_type": "json",
        "observation_start": inicio.isoformat(),
        "observation_end": fim.isoformat(),
    }
    return obter(URL, parametros, sessao=sessao, limite=LIMITE, **kw)


def interpretar(conteudo: bytes) -> list[tuple[str, str, str | None]]:
    """(data, valor, unidade) como vieram da fonte. ``.`` = ausência no FRED."""
    dados = json.loads(conteudo)
    return [(o["date"], o["value"], None) for o in dados["observations"]]


def converter_data(texto: str, frequencia: str) -> dt.date:
    """O FRED já usa o primeiro dia do mês/trimestre (AAAA-MM-DD)."""
    d = dt.date.fromisoformat(texto)
    if d.day != 1 or (frequencia == "T" and d.month not in (1, 4, 7, 10)):
        raise ValueError(f"data fora do padrão: {texto}")
    return d
