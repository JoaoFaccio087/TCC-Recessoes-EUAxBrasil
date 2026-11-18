"""Mudança de frequência (RF03; D21 e D26).

Regra: **taxa** usa a média do período; **nível** usa o último valor do período.
Entrada: ``pd.Series`` com ``DatetimeIndex``. Saída indexada pelo primeiro dia do mês ou do
trimestre, sem os períodos vazios (lacunas ficam como ausência de linha).
"""

from __future__ import annotations

import pandas as pd


def _converter(serie: pd.Series, tipo_medida: str, regra_pandas: str) -> pd.Series:
    if not isinstance(serie.index, pd.DatetimeIndex):
        raise TypeError("a série precisa de DatetimeIndex")
    serie = serie.dropna().sort_index()
    agrupado = serie.resample(regra_pandas)
    if tipo_medida == "taxa":
        saida = agrupado.mean()
    elif tipo_medida == "nivel":
        saida = agrupado.last()
    else:
        raise ValueError(f"tipo_medida inválido: {tipo_medida!r}")
    return saida.dropna()


def para_mensal(serie: pd.Series, tipo_medida: str) -> pd.Series:
    """Diária ou semanal → mensal (D21)."""
    return _converter(serie, tipo_medida, "MS")


def para_trimestral(serie: pd.Series, tipo_medida: str) -> pd.Series:
    """Mensal → trimestral (D26)."""
    return _converter(serie, tipo_medida, "QS")
