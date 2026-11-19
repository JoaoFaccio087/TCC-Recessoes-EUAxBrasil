"""Etapa 7 do TCC II: conferência contra as fontes (RNF03) e pontuação SUS (RNF06)."""

import datetime as dt

import pytest

from fontes_falsas import SessaoFalsa
from tcc_pipeline import config, pipeline, sus
from tcc_pipeline.conferencia import CONFERE, DIVERGE, conferir, relatorio

POC = {"series": ["eua_prod_ind", "br_prod_ind"], "episodios": ["2007-2009", "2020"]}
SEM_ESPERA = {"dormir": lambda _: None}
TZ = dt.timezone(dt.timedelta(hours=-3))


@pytest.fixture(autouse=True)
def chave(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "teste")


@pytest.fixture
def edicao(tmp_path):
    cfg = config.carregar()
    r = pipeline.executar("atualizar", cfg, tmp_path, sessao=SessaoFalsa(),
                          agora=dt.datetime(2026, 11, 18, 10, 0, tzinfo=TZ), kw_http=SEM_ESPERA, **POC)
    assert r.codigo == pipeline.OK, r.registro["erro"]
    return cfg, tmp_path


def test_conferencia_confere_com_a_fonte(edicao):
    cfg, pasta = edicao
    df = conferir(cfg, pasta / "publicacao", sessao=SessaoFalsa(), **SEM_ESPERA)
    # 2 séries × 2 episódios × (pico, pior valor, fim da janela)
    assert len(df) == 12
    assert set(df["ponto"]) == {"pico", "pior valor", "fim da janela"}
    assert (df["resultado"] == CONFERE).all(), df[df["resultado"] != CONFERE]
    csv, md = relatorio(df, pasta / "conferencia" / "teste")
    assert csv.exists() and "Conferem: 12 de 12" in md.read_text("utf-8")


def test_conferencia_aponta_revisao_da_fonte(edicao):
    cfg, pasta = edicao
    df = conferir(cfg, pasta / "publicacao", sessao=SessaoFalsa(ajuste=0.5), **SEM_ESPERA)
    assert (df["resultado"] == DIVERGE).all()
    assert "Pontos que não conferem" in relatorio(df, pasta / "c" / "x")[1].read_text("utf-8")


def test_sus_pontuacao():
    assert sus.pontuar([3] * 10) == 50.0
    assert sus.pontuar([5, 1] * 5) == 100.0
    assert sus.pontuar([1, 5] * 5) == 0.0
    assert sus.pontuar([4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == 75.0
    with pytest.raises(sus.ErroRespostas):
        sus.pontuar([6] + [3] * 9)
    assert sus.adjetivo(75.0) == "Bom"
    assert sus.adjetivo(50.0) == "OK"


def test_sus_csv(tmp_path):
    csv = tmp_path / "r.csv"
    csv.write_text("participante;q1;q2;q3;q4;q5;q6;q7;q8;q9;q10\n"
                   "P01;4;2;4;2;4;2;4;2;4;2\nP02;5;1;5;1;5;1;5;1;5;1\n", encoding="utf-8")
    res = sus.avaliar(csv)
    assert res["n"] == 2 and res["media"] == 87.5 and res["atende_rnf06"]
    assert "ATENDIDO" in sus.texto(res)
