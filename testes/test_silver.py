"""Silver: descarte do mês parcial nas séries do Ipeadata (D38)."""

import datetime as dt
import hashlib
import json

import pytest

from tcc_pipeline import bronze, config
from tcc_pipeline.silver import MES_PARCIAL, mes_parcial, reconstruir

UTC = dt.timezone.utc


@pytest.fixture
def cfg():
    return config.carregar()


def _bronze_ipeadata(pasta, id_serie, codigo, meses_valores, coletado_em):
    """Grava um Bronze sintético do Ipeadata (arquivo + manifesto) e devolve a pasta de dados."""
    conteudo = json.dumps({"value": [
        {"SERCODIGO": codigo, "VALDATA": f"{d.isoformat()}T00:00:00-03:00", "VALVALOR": v}
        for d, v in meses_valores]}).encode()
    caminho = f"bronze/ipeadata/{id_serie}/sintetico.json"
    (pasta / caminho).parent.mkdir(parents=True)
    (pasta / caminho).write_bytes(conteudo)
    manifesto = {"id_execucao": "20261118T120000Z-1", "arquivos": [{
        "id_serie": id_serie, "fonte": "Ipeadata", "codigo_origem": codigo, "status": bronze.OK,
        "caminho": caminho, "sha256": hashlib.sha256(conteudo).hexdigest(),
        "coletado_em": coletado_em.isoformat()}]}
    (pasta / "bronze/_manifestos").mkdir(parents=True)
    (pasta / "bronze/_manifestos/20261118T120000Z-1.json").write_text(json.dumps(manifesto))
    return pasta


def test_mes_corrente_do_ipeadata_vai_para_rejeitadas(cfg, tmp_path):
    coleta = dt.datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
    _bronze_ipeadata(tmp_path, "br_juros", "PAN12_TJOVER12",
                     [(dt.date(2026, 9, 1), 13.76), (dt.date(2026, 10, 1), 13.62),
                      (dt.date(2026, 11, 1), 6.29)], coleta)
    obs, rej, meta = reconstruir(cfg, tmp_path)

    datas = set(obs.loc[obs.id_serie == "br_juros", "data_ref"])
    assert dt.date(2026, 11, 1) not in datas  # mês corrente fora da Silver
    assert dt.date(2026, 10, 1) in datas  # mês anterior continua
    assert rej[["data_ref", "motivo"]].values.tolist() == [[dt.date(2026, 11, 1), MES_PARCIAL]]
    assert meta.set_index("id_serie").loc["br_juros", "fim"] == dt.date(2026, 10, 1)


def test_regra_vale_so_para_o_ipeadata_e_usa_horario_de_brasilia():
    nov = dt.date(2026, 11, 1)
    coleta = dt.datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
    assert mes_parcial("Ipeadata", nov, coleta)
    assert not mes_parcial("Ipeadata", dt.date(2026, 10, 1), coleta)
    for fonte in ("FRED", "IBGE/SIDRA", "Comex Stat"):
        assert not mes_parcial(fonte, nov, coleta)
    # 1/12 às 02:00 UTC ainda é 30/11 em Brasília: o mês corrente é novembro.
    virada = dt.datetime(2026, 12, 1, 2, 0, tzinfo=UTC)
    assert mes_parcial("Ipeadata", nov, virada)
    assert not mes_parcial("Ipeadata", dt.date(2026, 10, 1), virada)
