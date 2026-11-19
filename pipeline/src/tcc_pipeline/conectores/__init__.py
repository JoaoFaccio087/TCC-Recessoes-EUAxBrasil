"""Conectores das fontes oficiais (D13): FRED, Ipeadata, IBGE/SIDRA e Comex Stat.

Cada conector expõe ``FONTE``, ``PASTA``, ``baixar(serie, inicio, fim, sessao)``,
``interpretar(conteudo) -> [(data_bruta, valor_bruto, unidade)]`` e
``converter_data(data_bruta, frequencia) -> date``.
"""

from __future__ import annotations

from types import ModuleType

from . import comexstat, fred, ipeadata, sidra
from .http import ErroColeta

CONECTORES: dict[str, ModuleType] = {m.FONTE: m for m in (fred, ipeadata, sidra, comexstat)}


def conector(fonte: str) -> ModuleType:
    try:
        return CONECTORES[fonte]
    except KeyError:
        raise ErroColeta(f"conector da fonte {fonte!r} ainda não implementado") from None
