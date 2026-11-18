"""Edição sintética no contrato v1 (comando ``gerar-exemplo``).

Gera valores determinísticos com formato de recessão para todas as séries × episódios do
mapa e monta a edição com as mesmas funções da Gold real. Serve para os protótipos do painel
lerem os nomes definitivos antes da pipeline real. **Os números não são dados reais.**

Casos incluídos de propósito, para o painel exercitar os estados da seção 7.7:
- lacuna: ``br_acoes`` em 1981-1982, t_rel = 5 (``SEM_DADOS`` no mês);
- observação rejeitada: ``br_desemprego_pme_antiga`` em 1981-1982, t_rel = 3 (``REJEITADO``);
- ``RECUPERACAO_NAO_OBSERVADA``: ``br_prod_ind_antiga`` em 1981-1982;
- pares ``SEM_DADOS``: PIB e exportações Brasil → EUA em 1981-1982.
"""

from __future__ import annotations

import datetime as dt
import random
import zlib
from pathlib import Path

import pandas as pd

from . import gold
from .config import Config
from .publicacao import Resultado, id_livre, publicar

ID_EXECUCAO = "exemplo-sintetico"
DATA_CORTE = dt.date(2026, 11, 17)
COLETADO_EM = dt.datetime(2026, 11, 17, 12, 0, 0)

LACUNA = ("br_acoes", "1981-1982", 5)
REJEITADA = ("br_desemprego_pme_antiga", "1981-1982", 3)
SEM_RECUPERACAO = ("br_prod_ind_antiga", "1981-1982")

# Faixas de profundidade (índice: pontos abaixo de 100; taxa: p.p.) e nível base por grupo.
PERFIS = {
    "producao_industrial": {"prof": (5, 15), "base": (80, 120)},
    "cambio_real": {"prof": (8, 25), "base": (80, 130)},
    "exportacoes": {"prof": (10, 30), "base": (1_500, 20_000)},
    "pib": {"prof": (2, 8), "base": (100, 200)},
    "acoes": {"prof": (15, 40), "base": (50, 150)},
    "desemprego": {"prof": (1, 5), "base": (4, 10)},
    "juros": {"prof": (1.5, 5), "base": (2, 15)},
    "inflacao": {"prof": (1.5, 5), "base": (2, 10)},
}


def _rng(*partes: str) -> random.Random:
    return random.Random(zlib.crc32("|".join(partes).encode("utf-8")))


def _forma(t: int, prof: float, t_fundo: int, t_volta: int) -> float:
    """Desvio adverso (≥ 0) em relação ao pico: sobe até o fundo e volta a zero."""
    if t <= 0:
        return 0.0
    if t <= t_fundo:
        return prof * t / t_fundo
    if t <= t_fundo + t_volta:
        return prof * (1 - (t - t_fundo) / t_volta)
    return 0.0


def serie_sintetica(cfg: Config, id_serie: str, id_episodio: str) -> pd.DataFrame:
    """Valores tratados de uma série na janela de coleta de um episódio."""
    s = cfg.series[id_serie]
    f = s["frequencia"]
    regra = cfg.regras["grupos"][s["grupo"]]
    perfil = PERFIS[s["grupo"]]
    r = _rng(id_serie, id_episodio)
    escala = 3 if f == "T" else 1

    prof = r.uniform(*perfil["prof"])
    base = r.uniform(*perfil["base"])
    t_fundo = max(1, round(r.randint(3, 14) / escala))
    t_volta = max(2, round(r.randint(6, 36) / escala))
    if (id_serie, id_episodio) == SEM_RECUPERACAO:
        t_volta = 10_000
    sinal = r.choice([-1, 1]) if regra["sentido_adverso"] == "ambos" else (
        1 if regra["sentido_adverso"] == "alta" else -1)
    tendencia = r.uniform(0.0005, 0.002) * escala  # crescimento fora da recessão
    ruido = 0.25 if s["tipo_medida"] == "nivel" else 0.03

    pico = cfg.pico(id_episodio, f)
    a, b = cfg.regras["janelas"][f]["coleta"]
    linhas = []
    for t in range(a, b + 1):
        d = gold.somar_periodos(pico, t, f)
        if d > DATA_CORTE:
            break
        desvio = sinal * _forma(t, prof, t_fundo, t_volta)
        e = 0.0 if t == 0 else r.gauss(0, ruido)
        if s["tipo_medida"] == "nivel":
            fim_queda = t_fundo + t_volta
            cresc = tendencia * (t if t < 0 else max(0, t - fim_queda))
            painel = 100 * (1 + cresc) + desvio + e
            valor = base * painel / 100
        else:
            valor = max(0.05, base + desvio + e) if t != 0 else base
        valor = base if t == 0 else round(valor, 6)
        linhas.append({"id_serie": id_serie, "data_ref": d, "valor_original": valor,
                       "valor_tratado": valor})
    return pd.DataFrame(linhas)


def gerar(cfg: Config, raiz: Path | str, id_edicao: str | None = None,
          agora: dt.datetime | None = None) -> Resultado:
    agora = agora or dt.datetime.now().astimezone()
    id_edicao = id_edicao or id_livre(raiz, agora.strftime("%Y%m%d-%H%M"))

    partes = [serie_sintetica(cfg, id_s, str(ep))
              for id_s in cfg.series_metricas() for ep in cfg.series[id_s]["episodios"]]
    valores = pd.concat(partes, ignore_index=True)
    valores["coletado_em"] = COLETADO_EM
    valores["id_execucao"] = ID_EXECUCAO

    # Lacuna e observação rejeitada
    rejeitadas = []
    for (id_s, id_ep, t), rejeitar in ((LACUNA, False), (REJEITADA, True)):
        f = cfg.series[id_s]["frequencia"]
        d = gold.somar_periodos(cfg.pico(id_ep, f), t, f)
        alvo = (valores["id_serie"] == id_s) & (valores["data_ref"] == d)
        if rejeitar:
            rejeitadas.append({"id_serie": id_s, "data_ref": d, "valor_bruto": "-999",
                               "motivo": "valor fora da faixa plausível", "coletado_em": COLETADO_EM,
                               "id_execucao": ID_EXECUCAO})
        valores = valores[~alvo]
    rejeitadas_df = pd.DataFrame(rejeitadas)

    metodos = pd.DataFrame([
        {"id_metodo": "sintetico_indice_pico_100",
         "descricao": "DADOS SINTÉTICOS. Nível normalizado como número-índice com o pico = 100.",
         "parametros": gold.parametros_json(normalizacao="indice_pico_100", sintetico=True),
         "versao": "1"},
        {"id_metodo": "sintetico_pp_pico",
         "descricao": "DADOS SINTÉTICOS. Taxa normalizada como diferença em p.p. em relação ao pico.",
         "parametros": gold.parametros_json(normalizacao="pp_pico", sintetico=True),
         "versao": "1"},
    ])
    metodo_da_serie = {
        id_s: "sintetico_indice_pico_100" if s["tipo_medida"] == "nivel" else "sintetico_pp_pico"
        for id_s, s in cfg.series.items()
    }
    publicado_em = agora.replace(tzinfo=None, microsecond=0)
    tabelas = gold.montar(cfg, valores, rejeitadas_df, metodos, metodo_da_serie, {
        "id_edicao": id_edicao, "data_corte": DATA_CORTE, "publicado_em": publicado_em,
        "versao_codigo": "exemplo-sintetico",
    })
    return publicar(raiz, tabelas, id_edicao, agora.replace(microsecond=0), DATA_CORTE,
                    cfg.regras["cobertura_minima"])
