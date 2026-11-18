import math

import pandas as pd
import pytest

from tcc_pipeline import metricas as m


def serie(valores, inicio=0):
    return pd.Series(valores, index=range(inicio, inicio + len(valores)), dtype="float64")


# Regra de teste da seção 7.5: reação com 2 meses seguidos ≤ 98; recuperação 2 meses ≥ 100.
REGRA_75 = m.Regra(tipo_medida="nivel", sentido_adverso="queda", limiar=98, n=2,
                   janela_busca=(0, 6), recuperacao_max=6, recuperacao_periodos=2)
EUA = serie([100, 97, 95, 96, 100, 101, 102])
BR = serie([100, 100, 98, 94, 96, 100, 101])


def test_exemplo_sintetico_secao_7_5():
    eua, br = m.resumir(EUA, REGRA_75), m.resumir(BR, REGRA_75)
    assert (eua.t_reacao, br.t_reacao) == (1, 2)
    assert (eua.t_extremo, br.t_extremo) == (2, 3)
    assert eua.amplitude == pytest.approx(-5) and br.amplitude == pytest.approx(-6)
    assert eua.unidade_amplitude == "%"
    assert (eua.duracao_queda, br.duracao_queda) == (2, 3)
    assert (eua.t_recuperacao, br.t_recuperacao) == (4, 5)
    assert eua.status_recuperacao == br.status_recuperacao == m.OK
    assert m.defasagem(br.t_reacao, eua.t_reacao) == 1


def test_normalizar_nivel_e_taxa():
    v = serie([50.0, 40.0, 55.0], inicio=-1)
    assert list(m.normalizar(v, "nivel")) == pytest.approx([125, 100, 137.5])
    assert list(m.normalizar(v, "taxa")) == pytest.approx([10, 0, 15])
    assert m.normalizar(serie([1.0, math.nan], inicio=-1), "nivel").isna().all()


def test_lacuna_quebra_a_sequencia():
    s = serie([100, 97, math.nan, 97, 96, 99, 100])
    t, st = m.reacao(s, REGRA_75)
    assert (t, st) == (3, m.OK)


def test_reacao_nao_observada_e_cobertura_insuficiente():
    sem = serie([100, 99, 99, 100, 101, 102, 103])
    assert m.reacao(sem, REGRA_75) == (None, m.REACAO_NAO_OBSERVADA)
    com_lacuna = serie([100, 99, math.nan, 100, 101, 102, 103])
    assert m.reacao(com_lacuna, REGRA_75) == (None, m.COBERTURA_INSUFICIENTE)


def test_pior_valor_empate_fica_com_o_primeiro():
    s = serie([100, 95, 94, 94, 99, 100, 100])
    assert m.pior_valor(s, REGRA_75) == (2, 94.0)


def test_recuperacao_nao_observada():
    s = serie([100, 97, 95, 96, 100, 99, 99])
    r = m.resumir(s, REGRA_75)
    assert r.t_recuperacao is None and r.status_recuperacao == m.RECUPERACAO_NAO_OBSERVADA


def test_recuperacao_comeca_depois_do_pior_valor():
    # Meses 1 e 2 no nível do pico antes da queda não contam (D11).
    s = serie([100, 100, 101, 95, 99, 100, 100])
    r = m.resumir(s, REGRA_75)
    assert r.t_extremo == 3 and r.t_recuperacao == 5


def test_desemprego_alta_em_pp():
    regra = m.Regra(tipo_medida="taxa", sentido_adverso="alta", limiar=0.5, n=2,
                    janela_busca=(0, 6), recuperacao_max=8)
    s = serie([0, 0.2, 0.6, 1.4, 0.9, 0.3, -0.1, -0.2, 0.0])
    r = m.resumir(s, regra)
    assert r.t_reacao == 2 and r.t_extremo == 3
    assert r.amplitude == pytest.approx(1.4) and r.unidade_amplitude == "p.p."
    assert r.t_recuperacao == 6


def test_ambos_reage_em_qualquer_direcao_e_nao_aplica_pior_valor():
    regra = m.Regra(tipo_medida="taxa", sentido_adverso="ambos", limiar=1.0, n=2,
                    janela_busca=(0, 6), pior_e_recuperacao=False)
    queda = serie([0, -0.5, -1.2, -1.5, -0.8, 0, 0])
    alta = serie([0, 1.0, 1.1, 0.3, 0, 0, 0])
    rq, ra = m.resumir(queda, regra), m.resumir(alta, regra)
    assert (rq.t_reacao, ra.t_reacao) == (2, 1)
    assert rq.status_recuperacao == ra.status_recuperacao == m.NAO_APLICAVEL
    assert rq.t_extremo is None and rq.amplitude is None


def test_reacao_so_conta_depois_do_pico():
    s = serie([97, 97, 100, 99, 99, 99, 99, 99, 99], inicio=-2)
    assert m.reacao(s, REGRA_75) == (None, m.REACAO_NAO_OBSERVADA)


def test_sem_dados_e_sem_pico():
    vazia = serie([math.nan] * 7)
    assert m.resumir(vazia, REGRA_75).status_reacao == m.SEM_DADOS
    sem_pico = serie([math.nan, 97, 95, 96, 100, 101, 102])
    assert m.resumir(sem_pico, REGRA_75).status_reacao == m.COBERTURA_INSUFICIENTE


def test_pib_trimestral_n1():
    regra = m.Regra(tipo_medida="nivel", sentido_adverso="queda", limiar=99, n=1,
                    janela_busca=(0, 8), recuperacao_max=20)
    s = serie([100, 98.5, 97, 99.5, 100.2, 100.5] + [101] * 15)
    r = m.resumir(s, regra)
    assert (r.t_reacao, r.t_extremo, r.t_recuperacao) == (1, 2, 4)
