"""Conferência dos dados contra as fontes (RNF03; texto 7.6).

Para cada série e episódio da edição ativa, toma os meses (ou trimestres) de **pico**, de
**pior valor** e de **fim da janela de exibição** e compara o ``valor_original`` publicado com
o valor que a fonte devolve agora, numa consulta nova à API. Não grava nada no Bronze.

Resultados por ponto:
    CONFERE            igual à fonte (tolerância relativa de 1e-9)
    DIVERGE            diferente: revisão da fonte depois da coleta ou erro na pipeline
    AUSENTE_NA_FONTE   a fonte não devolveu valor para a data
    AUSENTE_NA_EDICAO  a edição não tem valor para a data (lacuna ou rejeição)

Saída: ``<TCC_DADOS>/conferencia/<instante>.csv`` e ``.md`` (resumo e pontos para conferência
manual no site de cada fonte).
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import pandas as pd

from .config import Config
from .conectores import conector
from .conectores.http import ErroColeta
from .gold import somar_periodos
from .silver import padronizar
from .validacao import conectar, edicao_ativa

TOL = 1e-9
CONFERE, DIVERGE = "CONFERE", "DIVERGE"
AUSENTE_NA_FONTE, AUSENTE_NA_EDICAO = "AUSENTE_NA_FONTE", "AUSENTE_NA_EDICAO"
COLUNAS = ["id_serie", "fonte", "codigo_origem", "id_episodio", "ponto", "t_rel", "data_ref",
           "valor_edicao", "valor_fonte", "dif_relativa", "resultado", "coletado_em", "url"]


def pontos_da_edicao(cfg: Config, pasta_edicao: Path, series: list[str] | None = None) -> pd.DataFrame:
    """Pico, pior valor e fim da janela de exibição de cada série × episódio, com o valor publicado."""
    con = conectar(pasta_edicao)
    try:
        resumo = con.execute("SELECT id_serie, id_episodio, frequencia, t_extremo "
                             "FROM fato_resumo_episodio").df()
        valores = con.execute(
            "SELECT id_serie, data_ref, valor_original, coletado_em FROM fato_valor_mensal "
            "UNION ALL SELECT id_serie, data_ref, valor_original, coletado_em FROM fato_valor_trimestral"
        ).df()
    finally:
        con.close()
    if series:
        resumo = resumo[resumo["id_serie"].isin(series)]
    valores["data_ref"] = pd.to_datetime(valores["data_ref"]).dt.date
    idx = {(r.id_serie, r.data_ref): (r.valor_original, r.coletado_em) for r in valores.itertuples()}
    ultima = valores.groupby("id_serie")["data_ref"].max().to_dict()

    linhas = []
    for r in resumo.itertuples():
        f = "T" if r.frequencia == "T" else "M"
        pico = cfg.pico(r.id_episodio, f)
        fim_jan = cfg.regras["janelas"][f]["exibicao"][1]
        alvo = [("pico", 0)]
        if not pd.isna(r.t_extremo):
            alvo.append(("pior valor", int(r.t_extremo)))
        # Fim da janela: último período publicado dentro da janela de exibição.
        t_fim = fim_jan
        while t_fim > 0 and somar_periodos(pico, t_fim, f) > ultima.get(r.id_serie, pico):
            t_fim -= 1
        alvo.append(("fim da janela", t_fim))
        for nome, t in alvo:
            d = somar_periodos(pico, t, f)
            v, coletado = idx.get((r.id_serie, d), (None, None))
            linhas.append({"id_serie": r.id_serie, "id_episodio": r.id_episodio, "ponto": nome,
                           "t_rel": t, "data_ref": d, "valor_edicao": v, "coletado_em": coletado})
    return pd.DataFrame(linhas)


def valores_da_fonte(cfg: Config, id_serie: str, sessao=None, **kw_http) -> dict[dt.date, float | None]:
    """Consulta nova à fonte (mesma janela da coleta), padronizada como na Silver."""
    s = cfg.series[id_serie]
    mod = conector(s["fonte"])
    inicio, fim = cfg.janela_coleta(id_serie)
    resp = mod.baixar(s, inicio, fim, sessao=sessao, **kw_http)
    saida: dict[dt.date, float | None] = {}
    for data_bruta, valor_bruto, unidade in mod.interpretar(resp.conteudo):
        estado, data, x = padronizar(s, mod, data_bruta, valor_bruto, unidade)
        if data is not None:
            saida[data] = x if estado == "ok" else None
    return saida


def comparar(v_edicao, v_fonte) -> tuple[str, float | None]:
    if v_edicao is None or (isinstance(v_edicao, float) and math.isnan(v_edicao)):
        return AUSENTE_NA_EDICAO, None
    if v_fonte is None:
        return AUSENTE_NA_FONTE, None
    dif = abs(v_edicao - v_fonte) / max(1.0, abs(v_fonte))
    return (CONFERE if dif <= TOL else DIVERGE), dif


def conferir(cfg: Config, raiz_publicacao: Path, series: list[str] | None = None,
             sessao=None, **kw_http) -> pd.DataFrame:
    pasta = edicao_ativa(raiz_publicacao)
    pts = pontos_da_edicao(cfg, pasta, series)
    linhas = []
    for id_s, grupo in pts.groupby("id_serie", sort=True):
        s = cfg.series[id_s]
        try:
            fonte = valores_da_fonte(cfg, id_s, sessao=sessao, **kw_http)
            erro = None
        except ErroColeta as e:
            fonte, erro = {}, str(e)
        for p in grupo.itertuples():
            res, dif = comparar(p.valor_edicao, fonte.get(p.data_ref))
            if erro and res == AUSENTE_NA_FONTE:
                res = f"ERRO_NA_CONSULTA: {erro[:120]}"
            linhas.append({
                "id_serie": id_s, "fonte": s["fonte"], "codigo_origem": s.get("codigo_origem"),
                "id_episodio": p.id_episodio, "ponto": p.ponto, "t_rel": p.t_rel, "data_ref": p.data_ref,
                "valor_edicao": p.valor_edicao, "valor_fonte": fonte.get(p.data_ref), "dif_relativa": dif,
                "resultado": res, "coletado_em": p.coletado_em, "url": s.get("url"),
            })
    df = pd.DataFrame(linhas, columns=COLUNAS)
    df.attrs["edicao"] = pasta.name
    return df


def relatorio(df: pd.DataFrame, destino_sem_extensao: Path, agora: dt.datetime | None = None) -> tuple[Path, Path]:
    """Grava CSV e um resumo em Markdown (com pontos sugeridos para conferência manual)."""
    agora = agora or dt.datetime.now().astimezone()
    destino_sem_extensao.parent.mkdir(parents=True, exist_ok=True)
    csv = destino_sem_extensao.with_suffix(".csv")
    md = destino_sem_extensao.with_suffix(".md")
    df.to_csv(csv, sep=";", index=False, encoding="utf-8-sig")

    cont = df["resultado"].value_counts()
    total = len(df)
    ok = int(cont.get(CONFERE, 0))
    linhas = [
        f"# Conferência dos dados contra as fontes (RNF03)",
        "",
        f"- Edição: `{df.attrs.get('edicao', '?')}`",
        f"- Executada em: {agora.isoformat(timespec='seconds')}",
        f"- Pontos conferidos: {total} ({df['id_serie'].nunique()} séries; pico, pior valor e fim da janela)",
        f"- **Conferem: {ok} de {total} ({ok / total:.0%})**" if total else "- Nenhum ponto conferido",
        "",
        "| Resultado | Pontos |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in cont.items()],
        "",
    ]
    problemas = df[df["resultado"] != CONFERE]
    if not problemas.empty:
        linhas += ["## Pontos que não conferem", "",
                   "| Série | Episódio | Ponto | Data | Edição | Fonte | Resultado |", "|---|---|---|---|---|---|---|"]
        for r in problemas.itertuples():
            linhas.append(f"| {r.id_serie} | {r.id_episodio} | {r.ponto} | {r.data_ref} | "
                          f"{r.valor_edicao} | {r.valor_fonte} | {r.resultado} |")
        linhas += ["", "DIVERGE pode ser revisão da fonte depois da coleta: rode `atualizar` e confira de novo. "
                       "Se persistir, é erro na pipeline.", ""]
    # Conferência manual: um ponto de pico por fonte, para abrir no site e comparar a olho.
    manual = (df[df["ponto"] == "pico"].sort_values(["fonte", "id_serie", "id_episodio"])
              .groupby("fonte").head(2))
    linhas += ["## Conferência manual sugerida (no site da fonte)", "",
               "| Fonte | Série | Código | Data | Valor publicado | Onde conferir | Conferido por / data |",
               "|---|---|---|---|---|---|---|"]
    for r in manual.itertuples():
        linhas.append(f"| {r.fonte} | {r.id_serie} | {r.codigo_origem} | {r.data_ref} | {r.valor_edicao} | {r.url} | |")
    md.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return csv, md
