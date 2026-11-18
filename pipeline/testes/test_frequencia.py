import pandas as pd
import pytest

from tcc_pipeline.frequencia import para_mensal, para_trimestral


def test_para_mensal_taxa_media_e_nivel_ultimo():
    idx = pd.to_datetime(["2020-01-02", "2020-01-15", "2020-01-31", "2020-02-03", "2020-02-28"])
    s = pd.Series([1.0, 2.0, 3.0, 10.0, 20.0], index=idx)
    taxa = para_mensal(s, "taxa")
    nivel = para_mensal(s, "nivel")
    assert list(taxa.index) == list(pd.to_datetime(["2020-01-01", "2020-02-01"]))
    assert list(taxa) == pytest.approx([2.0, 15.0])
    assert list(nivel) == [3.0, 20.0]


def test_para_mensal_semanal_com_mes_vazio_vira_lacuna():
    idx = pd.to_datetime(["2020-01-06", "2020-01-13", "2020-03-02"])
    s = pd.Series([1.0, 3.0, 5.0], index=idx)
    r = para_mensal(s, "taxa")
    assert list(r.index) == list(pd.to_datetime(["2020-01-01", "2020-03-01"]))


def test_para_trimestral():
    idx = pd.date_range("2019-10-01", periods=6, freq="MS")
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], index=idx)
    assert list(para_trimestral(s, "taxa")) == pytest.approx([2.0, 5.0])
    nivel = para_trimestral(s, "nivel")
    assert list(nivel.index) == list(pd.to_datetime(["2019-10-01", "2020-01-01"]))
    assert list(nivel) == [3.0, 6.0]


def test_tipo_invalido():
    s = pd.Series([1.0], index=pd.to_datetime(["2020-01-01"]))
    with pytest.raises(ValueError):
        para_mensal(s, "outro")
