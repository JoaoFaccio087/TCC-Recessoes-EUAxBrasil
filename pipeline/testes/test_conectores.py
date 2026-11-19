import datetime as dt
import json

import pytest
import requests

from tcc_pipeline.conectores import fred, sidra
from tcc_pipeline.conectores.http import ErroColeta, LimiteTaxa, obter


class R:
    def __init__(self, status, conteudo=b"{}"):
        self.status_code, self.content = status, conteudo


class Roteiro:
    """Devolve respostas (ou exceções) em sequência."""

    def __init__(self, *passos):
        self.passos = list(passos)
        self.params = []

    def get(self, url, params=None, timeout=None):
        self.params.append(params)
        p = self.passos.pop(0)
        if isinstance(p, Exception):
            raise p
        return p


def test_nova_tentativa_com_espera_crescente():
    esperas = []
    s = Roteiro(requests.Timeout("lento"), R(503), R(200, b"ok"))
    r = obter("http://x", {"a": 1}, sessao=s, dormir=esperas.append)
    assert r.conteudo == b"ok"
    assert esperas == [2.0, 4.0]
    assert [t.status_http for t in r.tentativas] == [None, 503, 200]


def test_desiste_apos_3_tentativas():
    s = Roteiro(R(429), R(500), R(502))
    with pytest.raises(ErroColeta) as e:
        obter("http://x", sessao=s, dormir=lambda _: None)
    assert len(e.value.tentativas) == 3


def test_erro_4xx_nao_repete_e_oculta_a_chave():
    s = Roteiro(R(400, b'{"error_message": "Bad api_key SEGREDO"}'))
    with pytest.raises(ErroColeta) as e:
        obter("http://x", {"api_key": "SEGREDO"}, sessao=s, dormir=lambda _: None)
    assert len(e.value.tentativas) == 1
    assert "SEGREDO" not in str(e.value)
    assert e.value.parametros == {"api_key": "***"}


def test_limite_de_taxa_espaca_as_requisicoes():
    tempo = [0.0]
    esperas = []

    def dormir(s):
        esperas.append(s)
        tempo[0] += s

    lim = LimiteTaxa(120, relogio=lambda: tempo[0], dormir=dormir)
    lim.aguardar()
    lim.aguardar()
    tempo[0] += 0.2
    lim.aguardar()
    assert esperas == pytest.approx([0.5, 0.3])


def test_fred_sem_chave(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(ErroColeta, match="FRED_API_KEY"):
        fred.baixar({"codigo_origem": "INDPRO"}, dt.date(2020, 1, 1), dt.date(2020, 2, 1))


def test_fred_parametros_e_interpretacao(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k123")
    corpo = json.dumps({"observations": [{"date": "2020-01-01", "value": "101.5"},
                                         {"date": "2020-02-01", "value": "."}]}).encode()
    s = Roteiro(R(200, corpo))
    r = fred.baixar({"codigo_origem": "INDPRO"}, dt.date(2020, 1, 1), dt.date(2020, 2, 1), sessao=s)
    assert s.params[0]["api_key"] == "k123" and r.parametros["api_key"] == "***"
    assert fred.interpretar(r.conteudo) == [("2020-01-01", "101.5", None), ("2020-02-01", ".", None)]
    assert fred.converter_data("2020-01-01", "M") == dt.date(2020, 1, 1)
    with pytest.raises(ValueError):
        fred.converter_data("2020-01-15", "M")


def test_sidra_url_e_interpretacao():
    params = {"tabela": 8888, "nivel": "n1", "variavel": 12607, "classificacoes": {"544": "129314"}}
    url = sidra.montar_url(params, dt.date(2004, 12, 1), dt.date(2013, 12, 1), "M")
    assert url == ("https://apisidra.ibge.gov.br/values/t/8888/n1/all/v/12607/p/200412-201312"
                   "/c544/129314")
    corpo = json.dumps([
        {"NC": "Nível Territorial (Código)", "MN": "Unidade de Medida", "V": "Valor",
         "D2C": "Variável (Código)", "D3C": "Mês (Código)"},
        {"NC": "1", "MN": "Número-índice", "V": "114.9", "D2C": "12607", "D3C": "200711"},
    ]).encode()
    assert sidra.interpretar(corpo) == [("200711", "114.9", "Número-índice")]
    assert sidra.converter_data("200711", "M") == dt.date(2007, 11, 1)
    assert sidra.converter_data("201904", "T") == dt.date(2019, 10, 1)
    with pytest.raises(ValueError):
        sidra.converter_data("200713", "M")


def test_ipeadata_url_e_interpretacao():
    from tcc_pipeline.conectores import ipeadata

    corpo = json.dumps({"value": [
        {"SERCODIGO": "PAN12_TJOVER12", "VALDATA": "1981-07-01T00:00:00-03:00", "VALVALOR": 98.5},
        {"SERCODIGO": "PAN12_TJOVER12", "VALDATA": "1981-08-01T00:00:00-03:00", "VALVALOR": None},
    ]}).encode()
    s = Roteiro(R(200, corpo))
    r = ipeadata.baixar({"codigo_origem": "PAN12_TJOVER12"}, dt.date(1978, 7, 1),
                        dt.date(1987, 7, 1), sessao=s)
    assert r.url.endswith("ValoresSerie(SERCODIGO='PAN12_TJOVER12')")
    linhas = ipeadata.interpretar(r.conteudo)
    assert linhas == [("1981-07-01T00:00:00-03:00", 98.5, None),
                      ("1981-08-01T00:00:00-03:00", None, None)]
    assert ipeadata.converter_data(linhas[0][0], "M") == dt.date(1981, 7, 1)
    with pytest.raises(ValueError):
        ipeadata.converter_data("1981-07-15T00:00:00-03:00", "M")


class RoteiroPost(Roteiro):
    def post(self, url, params=None, json=None, timeout=None):
        self.params.append(json)
        return self.passos.pop(0)


def test_comexstat_consulta_anos_inteiros_e_interpreta():
    from tcc_pipeline.conectores import comexstat

    corpo = json.dumps({"success": True, "data": {"list": [
        {"year": "2008", "monthNumber": "01", "country": "Estados Unidos", "metricFOB": "1893820908"},
    ]}}).encode()
    s = RoteiroPost(R(200, corpo))
    r = comexstat.baixar({"comexstat": {"pais": 249}}, dt.date(2004, 12, 1), dt.date(2013, 12, 1),
                         sessao=s)
    enviado = s.params[0]
    assert enviado["period"] == {"from": "2004-01", "to": "2013-12"}
    assert enviado["filters"] == [{"filter": "country", "values": [249]}]
    assert r.parametros["corpo_json"] == enviado
    assert comexstat.interpretar(r.conteudo) == [("2008-01", "1893820908", None)]
    assert comexstat.converter_data("2008-01", "M") == dt.date(2008, 1, 1)
    with pytest.raises(ValueError):
        comexstat.interpretar(json.dumps({"success": False, "message": "erro"}).encode())
