"""Critérios das hipóteses H1 a H3 (engenharia_de_dados.md, seção 7.6; texto 7.5).

Entradas: os DataFrames de ``fato_resumo_episodio`` e ``fato_comparacao`` (colunas do
contrato), mais a configuração. Saída: linhas de ``resultado_hipotese``.

H1: mediana das defasagens nos pares de ``h1_pares`` com reação nos três episódios.

H2 e H3 (D42): comparação por indicador. Em cada grupo de ``h2_h3_grupos``, a série
brasileira de cada episódio vem da ponte (``pares.yaml``); cada episódio é medido a partir do
próprio pico. Um grupo é favorável quando o episódio esperado vence sozinho; empate não conta
a favor; sem a medida num episódio, o grupo sai da comparação daquela medida. A condição é
atendida com maioria estrita dos grupos comparáveis (mínimo ``h2_h3_minimo_grupos``).
"""

from __future__ import annotations

import json
import math

import pandas as pd

from .metricas import OK, RECUPERACAO_NAO_OBSERVADA, SEM_DADOS

SUSTENTADA = "sustentada"
NAO_SUSTENTADA = "não sustentada"
INCONCLUSIVA = "inconclusiva"

ATENDIDA = "atendida"
NAO_ATENDIDA = "não atendida"
INCONCLUSIVA_COND = "inconclusiva"

EPISODIOS = ["1981-1982", "2007-2009", "2020"]
CRITERIO_H2_H3 = "maioria estrita dos grupos comparaveis, minimo {}"


def _linha(h: str, resultado: str, n: int, detalhe: dict) -> dict:
    return {"hipotese": h, "resultado": resultado, "n_pares": n,
            "detalhe": json.dumps(detalhe, ensure_ascii=False)}


# ------------------------------------------------------------------------------------- H1
def h1(comparacao: pd.DataFrame, cfg) -> dict:
    regras = cfg.regras["hipoteses"]
    pares = list(regras["h1_pares"])
    ok = comparacao[(comparacao["id_par"].isin(pares)) & (comparacao["status"] == OK)]
    por_par = ok.groupby("id_par")["id_episodio"].nunique()
    elegiveis = sorted(por_par[por_par == len(EPISODIOS)].index)
    det = {"pares_usados": pares, "pares_elegiveis": elegiveis}
    if len(elegiveis) < regras["h1_minimo_pares"]:
        return _linha("H1", INCONCLUSIVA, len(elegiveis), det)
    sel = ok[ok["id_par"].isin(elegiveis)]
    med = {e: float(sel.loc[sel["id_episodio"] == e, "defasagem"].abs().median()) for e in EPISODIOS}
    det["mediana_abs_defasagem"] = med
    caiu = med[EPISODIOS[0]] > med[EPISODIOS[1]] > med[EPISODIOS[2]]
    return _linha("H1", SUSTENTADA if caiu else NAO_SUSTENTADA, len(elegiveis), det)


# --------------------------------------------------------------------------------- H2 e H3
def _intensidade(r) -> tuple[float | None, str | None]:
    """abs(amplitude); sem amplitude, o motivo é o status da linha (ou 'nulo')."""
    if r["amplitude"] is None or pd.isna(r["amplitude"]):
        st = r["status_recuperacao"]
        return None, st if isinstance(st, str) and st not in (OK, RECUPERACAO_NAO_OBSERVADA) else "nulo"
    return abs(float(r["amplitude"])), None


def _recuperacao(cfg):
    def medir(r) -> tuple[float | None, str | None]:
        """t_recuperacao; RECUPERACAO_NAO_OBSERVADA conta como o fim da janela (60 meses)."""
        st = r["status_recuperacao"]
        if st == OK and not pd.isna(r["t_recuperacao"]):
            return float(r["t_recuperacao"]), None
        if st == RECUPERACAO_NAO_OBSERVADA:
            f = "T" if r["frequencia"] == "T" else "M"
            return float(cfg.regras["janelas"][f]["busca_recuperacao_max"]), None
        return None, st if isinstance(st, str) and st != OK else "nulo"
    return medir


def _num(v: float) -> float | int:
    return int(v) if float(v).is_integer() else v


def _comparar_grupo(grupo: str, resumo: pd.DataFrame, cfg, medir, maior_vence: bool,
                    esperado: str) -> tuple[dict, bool, bool]:
    """Um grupo numa medida. Devolve (detalhe, comparável, favorável)."""
    if grupo not in cfg.pares:  # fora do recorte de séries desta execução
        return ({"grupo": grupo, "series": {}, "valores": {}, "vencedor": None, "empate": False,
                 "excluido_motivo": "grupo fora do recorte"}, False, False)
    series = dict(cfg.pares[grupo]["br"])
    valores: dict[str, float | None] = {}
    motivos: list[str] = []
    for e in EPISODIOS:
        id_s = series.get(e, SEM_DADOS)
        linha = resumo[(resumo["id_serie"] == id_s) & (resumo["id_episodio"] == e)]
        if id_s == SEM_DADOS or linha.empty:
            valores[e], motivo = None, SEM_DADOS
        else:
            valores[e], motivo = medir(linha.iloc[0])
        if motivo:
            motivos.append(f"{e}: {motivo}")
    det = {"grupo": grupo, "series": series,
           "valores": {e: (None if v is None else _num(v)) for e, v in valores.items()},
           "vencedor": None, "empate": False, "excluido_motivo": None}
    if motivos:
        det["excluido_motivo"] = "; ".join(motivos)
        return det, False, False
    alvo = max(valores.values()) if maior_vence else min(valores.values())
    vencedores = [e for e, v in valores.items() if math.isclose(v, alvo, rel_tol=0, abs_tol=1e-9)]
    if len(vencedores) > 1:
        det["empate"] = True
        det["vencedor"] = vencedores
        return det, True, False
    det["vencedor"] = vencedores[0]
    return det, True, vencedores[0] == esperado


def _condicao(resumo: pd.DataFrame, cfg, medida: str, esperado: str, maior_vence: bool) -> dict:
    regras = cfg.regras["hipoteses"]
    medir = _intensidade if medida == "intensidade" else _recuperacao(cfg)
    grupos, comparaveis, favoraveis = [], 0, 0
    for g in regras["h2_h3_grupos"]:
        det, comp, fav = _comparar_grupo(g, resumo, cfg, medir, maior_vence, esperado)
        grupos.append(det)
        comparaveis += comp
        favoraveis += fav
    if comparaveis < regras["h2_h3_minimo_grupos"]:
        estado = INCONCLUSIVA_COND
    elif favoraveis > comparaveis / 2:
        estado = ATENDIDA
    else:
        estado = NAO_ATENDIDA
    return {"medida": medida, "episodio_esperado": esperado,
            "vence": "maior valor" if maior_vence else "menor valor",
            "comparaveis": comparaveis, "favoraveis": favoraveis, "estado": estado,
            "grupos": grupos}


def _detalhe(cfg, condicoes: list[dict]) -> dict:
    return {"criterio": CRITERIO_H2_H3.format(cfg.regras["hipoteses"]["h2_h3_minimo_grupos"]),
            "condicoes": condicoes}


def _n_grupos(condicoes: list[dict]) -> int:
    """Grupos comparáveis em pelo menos uma condição."""
    return len({g["grupo"] for c in condicoes for g in c["grupos"] if g["excluido_motivo"] is None})


def combinar(estados: list[str]) -> str:
    """Resultado a partir das condições: não atendida > inconclusiva > sustentada."""
    if NAO_ATENDIDA in estados:
        return NAO_SUSTENTADA
    if INCONCLUSIVA_COND in estados:
        return INCONCLUSIVA
    return SUSTENTADA


def h2(resumo: pd.DataFrame, cfg) -> dict:
    conds = [_condicao(resumo, cfg, "intensidade", "2020", maior_vence=True),
             _condicao(resumo, cfg, "recuperacao", "2020", maior_vence=False)]
    return _linha("H2", combinar([c["estado"] for c in conds]), _n_grupos(conds),
                  _detalhe(cfg, conds))


def h3(resumo: pd.DataFrame, cfg) -> dict:
    conds = [_condicao(resumo, cfg, "recuperacao", "1981-1982", maior_vence=True)]
    return _linha("H3", combinar([c["estado"] for c in conds]), _n_grupos(conds),
                  _detalhe(cfg, conds))


def avaliar(resumo: pd.DataFrame, comparacao: pd.DataFrame, cfg) -> pd.DataFrame:
    return pd.DataFrame([h1(comparacao, cfg), h2(resumo, cfg), h3(resumo, cfg)])
