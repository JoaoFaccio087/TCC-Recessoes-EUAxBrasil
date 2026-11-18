"""Tratamentos da seção 4.3 (texto 7.3): desconto da inflação, 12 meses e STL."""

import math

import numpy as np
import pandas as pd
import pytest

from tcc_pipeline import config, tratamentos as tr


def mensal(valores, inicio="2000-01-01"):
    return pd.Series(valores, index=pd.date_range(inicio, periods=len(valores), freq="MS"),
                     dtype="float64")


@pytest.fixture(scope="module")
def cfg():
    return config.carregar()


def test_encadear_variacao():
    idx = tr.encadear_variacao(mensal([10, -50, 100]))
    assert idx.tolist() == pytest.approx([110, 55, 110])


def test_encadear_interrompe_na_lacuna():
    s = mensal([10, 10, 10]).drop(pd.Timestamp("2000-02-01"))
    assert tr.encadear_variacao(s).tolist() == pytest.approx([110])


def test_deflacionar_equivale_a_base_no_pico():
    nominal = mensal([100, 110, 121])
    precos = mensal([100, 110, 110])
    real = tr.deflacionar(nominal, precos)
    assert real.tolist() == pytest.approx([100, 100, 110])
    # Normalizar pelo pico (t = 1) dá o mesmo que usar a base do deflator no pico (D10).
    base_pico = nominal / (precos / precos.iloc[1])
    assert (real / real.iloc[1]).tolist() == pytest.approx((base_pico / base_pico.iloc[1]).tolist())


def test_deflacionar_sem_deflator_vira_lacuna():
    real = tr.deflacionar(mensal([100, 100, 100]), mensal([100, 100]))
    assert len(real) == 2


def test_var_12m():
    indice = mensal([100 * 1.01 ** i for i in range(25)])
    v = tr.var_12m(indice)
    assert v.index[0] == pd.Timestamp("2001-01-01") and len(v) == 13
    assert v.iloc[0] == pytest.approx((1.01 ** 12 - 1) * 100)


def test_stl_remove_sazonalidade_multiplicativa():
    n = 120
    tendencia = 100 * 1.002 ** np.arange(n)
    sazonal = 1 + 0.1 * np.sin(2 * math.pi * np.arange(n) / 12)
    s = mensal(tendencia * sazonal)
    aj = tr.ajuste_stl(s, "M", "nivel")
    assert len(aj) == n
    assert np.max(np.abs(aj.to_numpy() / tendencia - 1)) < 0.01
    assert np.max(np.abs(s.to_numpy() / tendencia - 1)) > 0.09


def test_stl_aditivo_e_trecho_curto():
    n = 60
    s = mensal(5 + np.sin(2 * math.pi * np.arange(n) / 12))
    longo = s.drop(s.index[48])  # lacuna: trecho de 48 meses e outro de 11 (curto demais)
    aj = tr.ajuste_stl(longo, "M", "taxa")
    assert len(aj) == 48
    assert np.max(np.abs(aj.to_numpy() - 5)) < 0.05


def test_ordem_e_metodo(cfg):
    assert [tr.nome(p) for p in tr.passos(cfg, "br_acoes")] == ["encadear_variacao", "deflacionar"]
    assert tr.id_metodo(cfg, "br_export_total") == "deflac_eua_cpi+stl+indice_pico_100"
    assert tr.id_metodo(cfg, "eua_inflacao") == "var12m+pp_pico"
    assert tr.id_metodo(cfg, "eua_prod_ind") == "indice_pico_100"
    assert tr.id_metodo(cfg, "br_desemprego_pnadc") == "stl+pp_pico"


def test_todas_as_series_declaram_o_que_o_grupo_exige(cfg):
    assert {s: f for s in cfg.series_metricas() if (f := tr.pendentes(cfg, s))} == {}


def test_aplicar_com_deflator(cfg):
    datas = pd.date_range("2019-01-01", periods=3, freq="MS").date
    valores = pd.DataFrame({
        "id_serie": ["eua_acoes"] * 3 + ["eua_cpi"] * 3,
        "data_ref": list(datas) * 2,
        "valor_original": [100.0, 110.0, 121.0, 100.0, 110.0, 110.0],
    })
    sub = cfg.recortar(["eua_acoes"])
    v, metodos, por_serie = tr.aplicar(sub, valores)
    assert set(v["id_serie"]) == {"eua_acoes"}  # a auxiliar não entra nos fatos
    assert v["valor_tratado"].tolist() == pytest.approx([100, 100, 110])
    assert v["valor_original"].tolist() == [100, 110, 121]
    assert por_serie["eua_acoes"] in set(metodos["id_metodo"])


def test_encadear_com_mes_base():
    idx = tr.encadear_variacao(mensal([10, -50, 100]), base="2000-02")
    assert idx.tolist() == pytest.approx([200, 100, 200])
    with pytest.raises(tr.ErroTratamento):
        tr.encadear_variacao(mensal([10, 10]), base="1999-12")


def test_ibovespa_com_base_do_ipca(cfg):
    assert tr.passos(cfg, "br_acoes")[0] == {"encadear_variacao": "1993-12"}
    assert "(1993-12 = 100)" in tr.metodo(cfg, "br_acoes")["descricao"]
