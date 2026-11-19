"""Medidas de impacto por série e episódio (engenharia_de_dados.md, seção 7; RF04, RF06).

As funções recebem a série já alinhada ao pico: um ``pd.Series`` com índice ``t_rel``
(inteiro, meses ou trimestres) e valores em ``valor_painel`` (índice com pico = 100 para
nível, p.p. em relação ao pico para taxa). ``NaN`` representa lacuna ou observação
rejeitada na Silver; as duas quebram sequências (texto 7.4).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

# Estados (seção 7.7). OK e REACAO_NAO_OBSERVADA completam a lista para os casos com cálculo.
OK = "OK"
SEM_DADOS = "SEM_DADOS"
INCOMPATIVEL = "INCOMPATIVEL"
RECUPERACAO_NAO_OBSERVADA = "RECUPERACAO_NAO_OBSERVADA"
REACAO_NAO_OBSERVADA = "REACAO_NAO_OBSERVADA"
COBERTURA_INSUFICIENTE = "COBERTURA_INSUFICIENTE"
NAO_APLICAVEL = "NAO_APLICAVEL"
REJEITADO = "REJEITADO"

BASE = {"nivel": 100.0, "taxa": 0.0}


@dataclass(frozen=True)
class Regra:
    """Regra de um grupo (regras.yaml) já resolvida para a frequência da série."""

    tipo_medida: str  # nivel | taxa
    sentido_adverso: str  # queda | alta | ambos
    limiar: float
    n: int
    janela_busca: tuple[int, int] = (0, 24)
    recuperacao_max: int = 60
    recuperacao_periodos: int = 2
    pior_e_recuperacao: bool = True

    @classmethod
    def de_config(cls, cfg, id_serie: str) -> "Regra":
        serie = cfg.series[id_serie]
        g = cfg.regra_grupo(id_serie)
        jan = cfg.regras["janelas"]["T" if serie["frequencia"] == "T" else "M"]
        return cls(
            tipo_medida=serie["tipo_medida"],
            sentido_adverso=g["sentido_adverso"],
            limiar=float(g["limiar"]),
            n=int(g["n"]),
            janela_busca=tuple(jan["busca_reacao_pior"]),
            recuperacao_max=int(jan["busca_recuperacao_max"]),
            recuperacao_periodos=int(cfg.regras["recuperacao_periodos"]),
            pior_e_recuperacao=bool(g.get("pior_e_recuperacao", True)),
        )


@dataclass
class Resumo:
    valor_pico_painel: float | None
    t_reacao: int | None
    t_extremo: int | None
    amplitude: float | None
    unidade_amplitude: str
    duracao_queda: int | None
    t_recuperacao: int | None
    status_reacao: str
    status_recuperacao: str
    cobertura: float

    def como_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- normalização (RF04)

def normalizar(valores: pd.Series, tipo_medida: str) -> pd.Series:
    """Converte ``valor_tratado`` (índice t_rel) em ``valor_painel``.

    Nível: número-índice com o pico = 100. Taxa: diferença em p.p. em relação ao pico.
    Sem valor no pico, devolve tudo ``NaN`` (não há base de comparação).
    """
    v0 = valores.get(0, math.nan)
    if v0 is None or pd.isna(v0) or (tipo_medida == "nivel" and v0 == 0):
        return pd.Series(math.nan, index=valores.index, dtype="float64")
    if tipo_medida == "nivel":
        return valores / v0 * 100.0
    if tipo_medida == "taxa":
        return valores - v0
    raise ValueError(f"tipo_medida inválido: {tipo_medida!r}")


# ---------------------------------------------------------------- testes de sentido

def _desvio(v: float, regra: Regra) -> float:
    return v - BASE[regra.tipo_medida]


def alem_do_limiar(v: float, regra: Regra) -> bool:
    """O valor está além do limiar no sentido adverso?

    Nível: o limiar é o próprio índice (ex.: ≤ 98 na queda). Taxa: o limiar é a variação
    em p.p. (ex.: ≥ +0,5 na alta). ``ambos``: |desvio| ≥ limiar em qualquer direção.
    """
    if pd.isna(v):
        return False
    s = regra.sentido_adverso
    if s == "ambos":
        return abs(_desvio(v, regra)) >= regra.limiar
    if regra.tipo_medida == "nivel":
        return v <= regra.limiar if s == "queda" else v >= regra.limiar
    return v <= -regra.limiar if s == "queda" else v >= regra.limiar


def no_nivel_do_pico(v: float, regra: Regra) -> bool:
    """A série voltou ao nível do pico (índice ≥ 100, ou p.p. ≤ 0 quando a alta é adversa)?"""
    if pd.isna(v):
        return False
    d = _desvio(v, regra)
    return d >= 0 if regra.sentido_adverso == "queda" else d <= 0


# ---------------------------------------------------------------- medidas

def _sequencia(serie: pd.Series, inicio: int, tamanho: int, cond) -> bool:
    for t in range(inicio, inicio + tamanho):
        v = serie.get(t, math.nan)
        if not cond(v):
            return False
    return True


def cobertura(serie: pd.Series, janela: tuple[int, int]) -> float:
    a, b = janela
    esperados = range(a, b + 1)
    presentes = sum(1 for t in esperados if not pd.isna(serie.get(t, math.nan)))
    return presentes / len(esperados)


def reacao(serie: pd.Series, regra: Regra) -> tuple[int | None, str]:
    """Primeiro ``t_rel > 0`` que inicia N períodos consecutivos além do limiar (D3)."""
    a, b = regra.janela_busca
    for t in range(max(1, a), b + 1):
        if _sequencia(serie, t, regra.n, lambda v: alem_do_limiar(v, regra)):
            return t, OK
    janela = range(max(1, a), b + 1)
    if any(pd.isna(serie.get(t, math.nan)) for t in janela):
        return None, COBERTURA_INSUFICIENTE
    return None, REACAO_NAO_OBSERVADA


def pior_valor(serie: pd.Series, regra: Regra) -> tuple[int | None, float | None]:
    """Valor mais distante do pico no sentido adverso, na janela de busca. Empate: o primeiro."""
    a, b = regra.janela_busca
    trecho = serie.loc[(serie.index >= a) & (serie.index <= b)].dropna().sort_index()
    if trecho.empty:
        return None, None
    t = trecho.idxmin() if regra.sentido_adverso == "queda" else trecho.idxmax()
    return int(t), float(trecho[t])


def recuperacao(serie: pd.Series, regra: Regra, t_extremo: int) -> tuple[int | None, str]:
    """Do pico até o primeiro período após o pior valor em que a série volta ao nível do pico
    e nele permanece por ``recuperacao_periodos`` seguidos, dentro de ``recuperacao_max`` (D4, D11)."""
    k = regra.recuperacao_periodos
    for t in range(t_extremo + 1, regra.recuperacao_max - k + 2):
        if _sequencia(serie, t, k, lambda v: no_nivel_do_pico(v, regra)):
            return t, OK
    janela = range(t_extremo + 1, regra.recuperacao_max + 1)
    if any(pd.isna(serie.get(t, math.nan)) for t in janela):
        return None, COBERTURA_INSUFICIENTE
    return None, RECUPERACAO_NAO_OBSERVADA


def resumir(serie: pd.Series, regra: Regra) -> Resumo:
    """Todas as medidas de uma série num episódio (linha de ``fato_resumo_episodio``)."""
    unidade = "%" if regra.tipo_medida == "nivel" else "p.p."
    serie = serie.astype("float64")
    cob = cobertura(serie, regra.janela_busca)
    v0 = serie.get(0, math.nan)
    if serie.dropna().empty:
        return Resumo(None, None, None, None, unidade, None, None, SEM_DADOS, SEM_DADOS, 0.0)
    if pd.isna(v0):
        return Resumo(None, None, None, None, unidade, None, None,
                      COBERTURA_INSUFICIENTE, COBERTURA_INSUFICIENTE, cob)

    t_reacao, st_reacao = reacao(serie, regra)

    if not regra.pior_e_recuperacao or regra.sentido_adverso == "ambos":
        return Resumo(float(v0), t_reacao, None, None, unidade, None, None,
                      st_reacao, NAO_APLICAVEL, cob)

    t_ext, v_ext = pior_valor(serie, regra)
    if t_ext is None:
        return Resumo(float(v0), t_reacao, None, None, unidade, None, None,
                      st_reacao, COBERTURA_INSUFICIENTE, cob)
    amplitude = v_ext - float(v0)  # índice: pontos de índice = % do pico; taxa: p.p.
    t_rec, st_rec = recuperacao(serie, regra, t_ext)
    return Resumo(float(v0), t_reacao, t_ext, amplitude, unidade, t_ext, t_rec,
                  st_reacao, st_rec, cob)


def defasagem(t_reacao_br: int | None, t_reacao_eua: int | None) -> int | None:
    """``t_reacao`` BR − ``t_reacao`` EUA. Positivo: o Brasil reagiu depois."""
    if t_reacao_br is None or t_reacao_eua is None:
        return None
    return t_reacao_br - t_reacao_eua
