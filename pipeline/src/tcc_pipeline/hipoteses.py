"""Critérios das hipóteses H1 a H3 (engenharia_de_dados.md, seção 7.6; texto 7.5).

Entradas: os DataFrames de ``fato_resumo_episodio`` e ``fato_comparacao`` (colunas do
contrato), mais a configuração. Saída: linhas de ``resultado_hipotese``.
"""

from __future__ import annotations

import json

import pandas as pd

from .metricas import OK, RECUPERACAO_NAO_OBSERVADA

SUSTENTADA = "sustentada"
NAO_SUSTENTADA = "não sustentada"
INCONCLUSIVA = "inconclusiva"

EPISODIOS = ["1981-1982", "2007-2009", "2020"]

NOTA_UNIDADES = (
    "Questão em aberto: as medianas juntam unidades diferentes (amplitude em % e em p.p.; "
    "recuperação em meses e, no PIB, em trimestres)."
)


def _linha(h: str, resultado: str, n: int, detalhe: dict) -> dict:
    return {"hipotese": h, "resultado": resultado, "n_pares": n,
            "detalhe": json.dumps(detalhe, ensure_ascii=False)}


def h1(comparacao: pd.DataFrame, cfg) -> dict:
    regras = cfg.regras["hipoteses"]
    pares = regras["h1_pares"]
    ok = comparacao[(comparacao["id_par"].isin(pares)) & (comparacao["status"] == OK)]
    por_par = ok.groupby("id_par")["id_episodio"].nunique()
    elegiveis = sorted(por_par[por_par == len(EPISODIOS)].index)
    det = {"pares_elegiveis": elegiveis}
    if len(elegiveis) < regras["h1_minimo_pares"]:
        return _linha("H1", INCONCLUSIVA, len(elegiveis), det)
    sel = ok[ok["id_par"].isin(elegiveis)]
    med = {e: float(sel.loc[sel["id_episodio"] == e, "defasagem"].abs().median()) for e in EPISODIOS}
    det["mediana_abs_defasagem"] = med
    caiu = med[EPISODIOS[0]] > med[EPISODIOS[1]] > med[EPISODIOS[2]]
    return _linha("H1", SUSTENTADA if caiu else NAO_SUSTENTADA, len(elegiveis), det)


def _series_atividade(resumo: pd.DataFrame, cfg) -> pd.DataFrame:
    regras = cfg.regras["hipoteses"]
    ids = [s for s, m in cfg.series.items()
           if m["pais"] == "BR" and m.get("grupo") in regras["h2_h3_grupos"]
           and not m.get("apenas_ficha") and s not in regras["h2_h3_excluir_series"]]
    return resumo[resumo["id_serie"].isin(ids)].copy()


def _tempo_recuperacao(df: pd.DataFrame, cfg) -> pd.Series:
    """Tempo de recuperação; RECUPERACAO_NAO_OBSERVADA conta como o fim da janela."""
    fim = df["frequencia"].map(
        lambda f: cfg.regras["janelas"]["T" if f == "T" else "M"]["busca_recuperacao_max"])
    t = df["t_recuperacao"].astype("float64")
    return t.where(df["status_recuperacao"] == OK,
                   fim.where(df["status_recuperacao"] == RECUPERACAO_NAO_OBSERVADA))


def _medianas(resumo: pd.DataFrame, cfg) -> tuple[dict, dict, int]:
    df = _series_atividade(resumo, cfg)
    df["t_rec"] = _tempo_recuperacao(df, cfg)
    amp, rec = {}, {}
    for e in EPISODIOS:
        d = df[df["id_episodio"] == e]
        a = d["amplitude"].dropna().abs()
        r = d["t_rec"].dropna()
        amp[e] = float(a.median()) if not a.empty else None
        rec[e] = float(r.median()) if not r.empty else None
    return amp, rec, int(df["id_serie"].nunique())


def h2(resumo: pd.DataFrame, cfg) -> dict:
    amp, rec, n = _medianas(resumo, cfg)
    det = {"mediana_abs_amplitude": amp, "mediana_recuperacao": rec, "nota": NOTA_UNIDADES}
    if None in amp.values() or None in rec.values():
        return _linha("H2", INCONCLUSIVA, n, det)
    outros = [e for e in EPISODIOS if e != "2020"]
    ok = all(amp["2020"] > amp[e] for e in outros) and all(rec["2020"] < rec[e] for e in outros)
    return _linha("H2", SUSTENTADA if ok else NAO_SUSTENTADA, n, det)


def h3(resumo: pd.DataFrame, cfg) -> dict:
    _, rec, n = _medianas(resumo, cfg)
    det = {"mediana_recuperacao": rec,
           "nota": NOTA_UNIDADES + " RECUPERACAO_NAO_OBSERVADA conta como o fim da janela."}
    if None in rec.values():
        return _linha("H3", INCONCLUSIVA, n, det)
    ok = all(rec["1981-1982"] > rec[e] for e in EPISODIOS if e != "1981-1982")
    return _linha("H3", SUSTENTADA if ok else NAO_SUSTENTADA, n, det)


def avaliar(resumo: pd.DataFrame, comparacao: pd.DataFrame, cfg) -> pd.DataFrame:
    return pd.DataFrame([h1(comparacao, cfg), h2(resumo, cfg), h3(resumo, cfg)])
