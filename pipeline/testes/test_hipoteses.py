"""H1, H2 e H3 com dados sintéticos de fato_resumo_episodio e fato_comparacao (D42)."""

import json

import pandas as pd
import pytest

from tcc_pipeline import config, hipoteses as hip
from tcc_pipeline.metricas import (COBERTURA_INSUFICIENTE, OK, RECUPERACAO_NAO_OBSERVADA,
                                   SEM_DADOS)

EPS = hip.EPISODIOS
PI, DES, EXP = "producao_industrial", "desemprego", "exportacoes_total"


@pytest.fixture
def cfg():
    return config.carregar()


def resumo(cfg, dados: dict) -> pd.DataFrame:
    """dados = {grupo: {episodio: (amplitude, t_recuperacao, status_recuperacao)}}.

    A série brasileira de cada episódio vem da ponte (pares.yaml), como na pipeline.
    """
    linhas = []
    for grupo, por_ep in dados.items():
        for e, (amp, t_rec, st) in por_ep.items():
            linhas.append({"id_serie": cfg.pares[grupo]["br"][e], "id_episodio": e,
                           "frequencia": "M", "amplitude": amp, "t_recuperacao": t_rec,
                           "status_recuperacao": st})
    return pd.DataFrame(linhas)


def ok(*amps_recs):
    """Três episódios OK: ok((amp, rec), (amp, rec), (amp, rec))."""
    return {e: (a, r, OK) for e, (a, r) in zip(EPS, amps_recs)}


def detalhe(linha: dict) -> dict:
    return json.loads(linha["detalhe"])


def cond(linha: dict, i: int = 0) -> dict:
    return detalhe(linha)["condicoes"][i]


# Intensidade: 2020 vence em PI e DES, perde em EXP. Recuperação: 2020 mais rápida em PI e EXP.
BASE = {
    PI: ok((-8, 33), (-15, 24), (-26, 7)),
    DES: ok((0.7, 7), (0.0, 1), (3.6, 23)),
    EXP: ok((-26, 34), (-23, 27), (-12, 10)),
}


def test_maioria_atendida(cfg):
    c = cond(hip.h2(resumo(cfg, BASE), cfg), 0)
    assert (c["medida"], c["comparaveis"], c["favoraveis"], c["estado"]) == \
        ("intensidade", 3, 2, hip.ATENDIDA)
    pi = next(g for g in c["grupos"] if g["grupo"] == PI)
    assert pi["series"] == {"1981-1982": "br_prod_ind_antiga", "2007-2009": "br_prod_ind",
                            "2020": "br_prod_ind"}
    assert pi["valores"] == {"1981-1982": 8, "2007-2009": 15, "2020": 26}
    assert pi["vencedor"] == "2020" and pi["empate"] is False and pi["excluido_motivo"] is None


def test_sem_maioria_nao_atendida(cfg):
    dados = {**BASE, DES: ok((5, 7), (0, 1), (3.6, 23))}   # agora só PI favorável
    c = cond(hip.h2(resumo(cfg, dados), cfg), 0)
    assert (c["comparaveis"], c["favoraveis"], c["estado"]) == (3, 1, hip.NAO_ATENDIDA)


def test_empate_comparavel_mas_nao_favoravel(cfg):
    dados = {**BASE, DES: ok((3.6, 7), (0.0, 1), (3.6, 23))}  # 1981 e 2020 empatam no maior
    c = cond(hip.h2(resumo(cfg, dados), cfg), 0)
    des = next(g for g in c["grupos"] if g["grupo"] == DES)
    assert des["empate"] is True and des["excluido_motivo"] is None
    assert (c["comparaveis"], c["favoraveis"]) == (3, 1)


def test_recuperacao_nao_observada_conta_60_e_empata(cfg):
    dados = {**BASE, PI: {"1981-1982": (-8, None, RECUPERACAO_NAO_OBSERVADA),
                          "2007-2009": (-15, 24, OK),
                          "2020": (-26, None, RECUPERACAO_NAO_OBSERVADA)}}
    c = cond(hip.h3(resumo(cfg, dados), cfg))
    pi = next(g for g in c["grupos"] if g["grupo"] == PI)
    assert pi["valores"] == {"1981-1982": 60, "2007-2009": 24, "2020": 60}
    assert pi["empate"] is True
    assert (c["comparaveis"], c["favoraveis"]) == (3, 1)   # só EXP favorável a 1981-1982
    assert c["estado"] == hip.NAO_ATENDIDA


def test_grupo_sem_a_medida_e_excluido_com_motivo(cfg):
    dados = {**BASE, EXP: {**BASE[EXP], "2020": (None, None, COBERTURA_INSUFICIENTE)}}
    linha = hip.h2(resumo(cfg, dados), cfg)
    for c in detalhe(linha)["condicoes"]:
        exp = next(g for g in c["grupos"] if g["grupo"] == EXP)
        assert exp["excluido_motivo"] == f"2020: {COBERTURA_INSUFICIENTE}"
        assert c["comparaveis"] == 2


def test_linha_ausente_conta_como_sem_dados(cfg):
    dados = {PI: BASE[PI], DES: BASE[DES], EXP: {e: BASE[EXP][e] for e in EPS[1:]}}
    c = cond(hip.h3(resumo(cfg, dados), cfg))
    exp = next(g for g in c["grupos"] if g["grupo"] == EXP)
    assert exp["excluido_motivo"] == f"1981-1982: {SEM_DADOS}"


def test_menos_de_dois_comparaveis_inconclusiva(cfg):
    dados = {PI: BASE[PI]}   # DES e EXP sem linhas
    linha = hip.h3(resumo(cfg, dados), cfg)
    assert cond(linha)["comparaveis"] == 1
    assert cond(linha)["estado"] == hip.INCONCLUSIVA_COND
    assert linha["resultado"] == hip.INCONCLUSIVA


def test_dois_comparaveis_exigem_os_dois(cfg):
    # H3 com PI e EXP: ambos com 1981-1982 mais lento → atendida; um só → não atendida.
    dados = {PI: BASE[PI], EXP: BASE[EXP]}
    assert cond(hip.h3(resumo(cfg, dados), cfg))["estado"] == hip.ATENDIDA
    dados = {PI: BASE[PI], EXP: ok((-26, 20), (-23, 27), (-12, 10))}
    c = cond(hip.h3(resumo(cfg, dados), cfg))
    assert (c["comparaveis"], c["favoraveis"], c["estado"]) == (2, 1, hip.NAO_ATENDIDA)


def test_combinacao_h2():
    assert hip.combinar([hip.NAO_ATENDIDA, hip.INCONCLUSIVA_COND]) == hip.NAO_SUSTENTADA
    assert hip.combinar([hip.ATENDIDA, hip.INCONCLUSIVA_COND]) == hip.INCONCLUSIVA
    assert hip.combinar([hip.ATENDIDA, hip.ATENDIDA]) == hip.SUSTENTADA


def test_h2_combina_condicoes(cfg):
    # Intensidade atendida (BASE); recuperação só com PI comparável → inconclusiva.
    dados = {g: {e: (a, None, COBERTURA_INSUFICIENTE) if g != PI else (a, r, s)
                 for e, (a, r, s) in BASE[g].items()} for g in BASE}
    linha = hip.h2(resumo(cfg, dados), cfg)
    estados = [c["estado"] for c in detalhe(linha)["condicoes"]]
    assert estados == [hip.ATENDIDA, hip.INCONCLUSIVA_COND]
    assert linha["resultado"] == hip.INCONCLUSIVA


def test_h3_sustentada_com_base(cfg):
    linha = hip.h3(resumo(cfg, BASE), cfg)
    assert cond(linha)["favoraveis"] == 2 and linha["resultado"] == hip.SUSTENTADA
    assert detalhe(linha)["criterio"] == "maioria estrita dos grupos comparaveis, minimo 2"


def test_h1_sem_inflacao(cfg):
    linhas = [{"id_par": p, "id_episodio": e, "status": OK, "defasagem": d}
              for p in ("inflacao", PI, DES, "acoes")
              for e, d in zip(EPS, (6, 3, 0))]
    linha = hip.h1(pd.DataFrame(linhas), cfg)
    det = detalhe(linha)
    assert "inflacao" not in det["pares_usados"]
    assert det["pares_elegiveis"] == ["acoes", DES, PI]
    assert linha["n_pares"] == 3 and linha["resultado"] == hip.SUSTENTADA
