"""PoC de ponta a ponta sem rede: FRED e SIDRA falsos → Bronze → Silver → Gold → publicação."""

import dataclasses
import datetime as dt
import json
import os

import duckdb
import pytest

from fontes_falsas import SessaoFalsa
from tcc_pipeline import config, pipeline
from tcc_pipeline.silver import padronizar
from tcc_pipeline.conectores import sidra
from tcc_pipeline.validacao import edicao_ativa, validar_edicao

POC = {"series": ["eua_prod_ind", "br_prod_ind"], "episodios": ["2007-2009", "2020"]}
TZ = dt.timezone(dt.timedelta(hours=-3))
SEM_ESPERA = {"dormir": lambda _: None}


@pytest.fixture
def cfg():
    return config.carregar()


@pytest.fixture(autouse=True)
def chave(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "teste")


def rodar(cfg, pasta, comando="atualizar", sessao=None, hora=10, **kw):
    return pipeline.executar(comando, cfg, pasta, sessao=sessao or SessaoFalsa(),
                             agora=dt.datetime(2026, 11, 18, hora, 0, tzinfo=TZ),
                             kw_http=SEM_ESPERA, **{**POC, **kw})


def q(pasta, sql):
    return duckdb.connect().execute(sql.replace("$P", (pasta / "publicacao").as_posix())
                                    .replace("$S", (pasta / "silver").as_posix())).fetchall()


def test_padronizar_silver(cfg):
    s = cfg.series["br_prod_ind"]
    assert padronizar(s, sidra, "200801", "117.2", "Número-índice")[0] == "ok"
    assert padronizar(s, sidra, "200801", "...", "Número-índice")[0] == "ausente"
    assert padronizar(s, sidra, "200801", "abc", "Número-índice")[2] == "tipo inválido"
    assert padronizar(s, sidra, "200801", "5000", "Número-índice")[2] == "valor fora da faixa plausível"
    assert padronizar(s, sidra, "2008-1", "117", "Número-índice")[2] == "data fora do padrão"
    assert padronizar(s, sidra, "200801", "117", "%")[2].startswith("unidade incoerente")


def test_atualizar_publica_edicao_valida(cfg, tmp_path):
    sessao = SessaoFalsa(sidra_extras={"200803": "abc", "200804": "..."})
    r = rodar(cfg, tmp_path, sessao=sessao)
    assert r.codigo == pipeline.OK, r.registro["erro"]
    assert r.registro["status"] == "SUCESSO" and r.registro["series_processadas"] == 2
    assert not (tmp_path / ".lock").exists()

    pasta = edicao_ativa(tmp_path / "publicacao")
    assert validar_edicao(pasta) == []

    man = json.loads(next((tmp_path / "bronze" / "_manifestos").glob("*.json")).read_text("utf-8"))
    assert {a["id_serie"] for a in man["arquivos"]} == set(POC["series"])
    assert all(a["sha256"] and a["status"] == "OK" for a in man["arquivos"])
    assert "teste" not in json.dumps(man)  # chave do FRED fora do manifesto

    e = pasta.as_posix()
    rej = duckdb.sql(f"SELECT data_ref, motivo FROM '{e}/observacao_rejeitada.parquet'").fetchall()
    assert rej == [(dt.date(2008, 3, 1), "tipo inválido")]
    st = duckdb.sql(f"""SELECT t_rel, status FROM '{e}/fato_serie_alinhada_mensal.parquet'
                        WHERE id_serie='br_prod_ind' AND data_ref IN ('2008-03-01','2008-04-01')
                        ORDER BY 1""").fetchall()
    assert st == [(3, "REJEITADO"), (4, "SEM_DADOS")]

    res = duckdb.sql(f"""SELECT id_episodio, id_serie, t_reacao, t_extremo, t_recuperacao, status_recuperacao
                         FROM '{e}/fato_resumo_episodio.parquet' ORDER BY 1, 2""").fetchall()
    # EUA: queda de 12 pontos em 20 meses; BR: 15 pontos em 26 meses (fontes_falsas.valor).
    # Os dois cruzam 98 em t = 2, mas no Brasil t = 3 (rejeitado) e t = 4 (ausente) quebram
    # a sequência, então a reação brasileira em 2007-2009 só se confirma em t = 5.
    assert res[0] == ("2007-2009", "br_prod_ind", 5, 13, 26, "OK")
    assert res[1] == ("2007-2009", "eua_prod_ind", 2, 10, 20, "OK")
    comp = duckdb.sql(f"SELECT id_episodio, id_par, defasagem, status FROM '{e}/fato_comparacao.parquet' "
                      "ORDER BY 1").fetchall()
    assert comp == [("2007-2009", "producao_industrial", 3, "OK"), ("2020", "producao_industrial", 0, "OK")]

    ctrl = q(tmp_path, "SELECT status, comando FROM '$P/controle_execucao.parquet'")
    assert ctrl == [("SUCESSO", "atualizar")]


def test_sem_alteracoes_revisao_e_reprocessar(cfg, tmp_path):
    assert rodar(cfg, tmp_path, hora=10).registro["status"] == "SUCESSO"
    # Mesma coleta: Silver não cresce e nada é publicado.
    n1 = q(tmp_path, "SELECT count(*) FROM '$S/observacao.parquet'")[0][0]
    r2 = rodar(cfg, tmp_path, hora=10)  # mesmo minuto da edição ativa
    assert r2.registro["status"] == "SEM_ALTERACOES"
    assert q(tmp_path, "SELECT count(*) FROM '$S/observacao.parquet'")[0][0] == n1
    # Revisão de valores: a Silver acrescenta as novas versões e uma edição nova é publicada.
    r3 = rodar(cfg, tmp_path, sessao=SessaoFalsa(ajuste=0.5), hora=12)
    assert r3.registro["status"] == "SUCESSO"
    assert q(tmp_path, "SELECT count(*) FROM '$S/observacao.parquet'")[0][0] == 2 * n1
    # Reprocessar sem coleta: mesmo conteúdo da edição ativa.
    r4 = rodar(cfg, tmp_path, comando="reprocessar", hora=13)
    assert r4.codigo == pipeline.OK and r4.registro["status"] == "SEM_ALTERACOES"
    lista = json.loads((tmp_path / "publicacao" / "edicoes.json").read_text("utf-8"))
    assert [e["id_edicao"] for e in lista["edicoes"]] == ["20261118-1000", "20261118-1200"]
    status = [s for (s,) in q(tmp_path, "SELECT status FROM '$P/controle_execucao.parquet' ORDER BY inicio")]
    assert status == ["SUCESSO", "SEM_ALTERACOES", "SUCESSO", "SEM_ALTERACOES"]


def test_conteudo_novo_no_mesmo_minuto_ganha_sufixo(cfg, tmp_path):
    assert rodar(cfg, tmp_path, hora=10).registro["id_edicao"] == "20261118-1000"
    r = rodar(cfg, tmp_path, sessao=SessaoFalsa(ajuste=0.5), hora=10)
    assert r.codigo == pipeline.OK, r.registro["erro"]
    assert r.registro["id_edicao"] == "20261118-1000-2"
    r = rodar(cfg, tmp_path, sessao=SessaoFalsa(ajuste=1.0), hora=10)
    assert r.registro["id_edicao"] == "20261118-1000-3"
    atual = json.loads((tmp_path / "publicacao" / "atual.json").read_text("utf-8"))
    assert atual["id_edicao_ativa"] == "20261118-1000-3"
    assert validar_edicao(edicao_ativa(tmp_path / "publicacao")) == []


def test_falha_na_coleta_mantem_edicao_anterior(cfg, tmp_path):
    rodar(cfg, tmp_path, hora=10)
    atual = (tmp_path / "publicacao" / "atual.json").read_text("utf-8")
    r = rodar(cfg, tmp_path, sessao=SessaoFalsa(ajuste=1, falhar={"fred"}), hora=11)
    assert r.codigo == pipeline.FALHA and r.registro["status"] == "FALHA"
    assert "eua_prod_ind" in r.registro["erro"]
    assert (tmp_path / "publicacao" / "atual.json").read_text("utf-8") == atual
    assert not (tmp_path / ".lock").exists()
    man = sorted((tmp_path / "bronze" / "_manifestos").glob("*.json"))[-1]
    falha = [a for a in json.loads(man.read_text("utf-8"))["arquivos"] if a["status"] == "FALHA"][0]
    assert len(falha["tentativas"]) == 3
    assert q(tmp_path, "SELECT status FROM '$P/controle_execucao.parquet' ORDER BY inicio") == \
        [("SUCESSO",), ("FALHA",)]


def test_lock_ocupado_registra_bloqueado(cfg, tmp_path):
    lock = tmp_path / ".lock"
    lock.write_text(json.dumps({"pid": os.getpid(),
                                "inicio": dt.datetime.now(dt.timezone.utc).isoformat()}))
    r = rodar(cfg, tmp_path)
    assert r.codigo == pipeline.BLOQUEADO and r.registro["status"] == "BLOQUEADO"
    assert lock.exists()  # o lock de outra execução não é removido
    assert len(list((tmp_path / "controle").glob("*.json"))) == 1
    lock.unlink()
    # A próxima execução com o lock inclui o registro bloqueado no parquet.
    rodar(cfg, tmp_path)
    assert q(tmp_path, "SELECT status FROM '$P/controle_execucao.parquet' ORDER BY inicio") == \
        [("BLOQUEADO",), ("SUCESSO",)]


def test_lock_esquecido_e_removido(cfg, tmp_path):
    (tmp_path / ".lock").write_text(json.dumps({"pid": 999999, "inicio": "2026-01-01T00:00:00+00:00"}))
    r = rodar(cfg, tmp_path)
    assert r.codigo == pipeline.OK
    assert r.registro["observacao"].startswith("LOCK_ESQUECIDO_REMOVIDO")


def test_serie_com_tratamento_pendente_falha(cfg, tmp_path):
    """Grupo que exige deflação sem o tratamento declarado: falha sem publicar."""
    series = {**cfg.series, "eua_acoes": {**cfg.series["eua_acoes"], "tratamentos": []}}
    r = rodar(dataclasses.replace(cfg, series=series), tmp_path, series=["eua_acoes"],
              episodios=["2020"])
    assert r.codigo == pipeline.FALHA and "desconto da inflação" in r.registro["erro"]
    assert not (tmp_path / "publicacao" / "atual.json").exists()


def test_serie_deflacionada_coleta_o_deflator(cfg, tmp_path):
    r = rodar(cfg, tmp_path, series=["eua_acoes"], episodios=["2020"])
    assert r.codigo == pipeline.OK, r.registro["erro"]
    assert r.registro["series"] == ["eua_acoes", "eua_cpi"]
    e = edicao_ativa(tmp_path / "publicacao").as_posix()
    met = duckdb.sql(f"SELECT DISTINCT id_metodo FROM '{e}/fato_serie_alinhada_mensal.parquet'").fetchall()
    assert met == [("deflac_eua_cpi+indice_pico_100",)]
    series = duckdb.sql(f"SELECT id_serie FROM '{e}/dim_serie.parquet'").fetchall()
    assert ("eua_cpi",) not in series  # auxiliar fica fora da dim_serie
