"""Edição sintética: gera, valida e consulta como o painel fará (seção 8.4)."""

import datetime as dt
import json

import pytest

from tcc_pipeline import config
from tcc_pipeline import metricas as m
from tcc_pipeline.contrato import TABELAS
from tcc_pipeline.exemplo import gerar
from tcc_pipeline.publicacao import SEM_ALTERACOES, SUCESSO
from tcc_pipeline.validacao import conectar, edicao_ativa, validar_edicao

AGORA = dt.datetime(2026, 11, 17, 14, 0, tzinfo=dt.timezone(dt.timedelta(hours=-3)))

CONSULTA_PAINEL = """
SELECT a.id_edicao, a.id_episodio, s.pais, s.id_serie, s.nome, s.fonte, s.codigo_origem,
       a.t_rel, a.data_ref, a.valor_painel, s.tipo_medida, a.status, a.motivo,
       a.id_metodo, m.descricao AS metodo, a.coletado_em
FROM fato_serie_alinhada_mensal a
JOIN ponte_serie_br_eua p
  ON a.id_episodio = p.id_episodio
 AND a.id_serie IN (p.id_serie_eua, p.id_serie_br)
JOIN dim_serie s USING (id_serie)
LEFT JOIN dim_metodo m USING (id_metodo)
WHERE p.id_par = ? AND a.id_episodio = ? AND a.t_rel BETWEEN ? AND ?
ORDER BY a.t_rel, s.pais
"""


@pytest.fixture(scope="module")
def cfg():
    return config.carregar()


@pytest.fixture(scope="module")
def edicao(tmp_path_factory, cfg):
    raiz = tmp_path_factory.mktemp("publicacao")
    r = gerar(cfg, raiz, "20261117-1400", AGORA)
    assert r.status == SUCESSO
    return raiz, r


def test_config_coerente(cfg):
    assert len(cfg.series) == 21
    assert {s for s, m in cfg.series.items() if m.get("auxiliar")} == {"eua_cpi", "br_ipca_indice"}
    assert len(cfg.series_metricas()) == 18
    assert cfg.pico("2020", "T") == dt.date(2019, 10, 1)


def test_edicao_publicada_e_valida(edicao, cfg):
    raiz, r = edicao
    pasta = edicao_ativa(raiz)
    assert pasta == r.pasta
    assert validar_edicao(pasta, cfg.regras["cobertura_minima"]) == []
    for t in TABELAS.values():
        assert (pasta / t.arquivo).exists()
    tamanho = sum(p.stat().st_size for p in pasta.iterdir())
    assert tamanho < 1_000_000
    lista = json.loads((raiz / "edicoes.json").read_text(encoding="utf-8"))
    assert [e["id_edicao"] for e in lista["edicoes"]] == ["20261117-1400"]


def test_consulta_do_painel(edicao):
    raiz, _ = edicao
    con = conectar(edicao_ativa(raiz))
    linhas = con.execute(CONSULTA_PAINEL, ["producao_industrial", "2007-2009", -24, 48]).fetchall()
    assert len(linhas) == 2 * 73
    paises = {l[2] for l in linhas}
    assert paises == {"BR", "EUA"}
    no_pico = [l for l in linhas if l[7] == 0]
    assert all(l[9] == pytest.approx(100) for l in no_pico)


def test_casos_especiais(edicao):
    raiz, _ = edicao
    con = conectar(edicao_ativa(raiz))
    q = lambda sql: con.execute(sql).fetchall()
    assert q("""SELECT status, motivo FROM fato_serie_alinhada_mensal
                WHERE id_serie='br_desemprego_pme_antiga' AND id_episodio='1981-1982' AND t_rel=3""") \
        == [(m.REJEITADO, "valor fora da faixa plausível")]
    assert q("""SELECT status, valor_painel FROM fato_serie_alinhada_mensal
                WHERE id_serie='br_acoes' AND id_episodio='1981-1982' AND t_rel=5""") \
        == [(m.SEM_DADOS, None)]
    assert q("""SELECT status_recuperacao FROM fato_resumo_episodio
                WHERE id_serie='br_prod_ind_antiga' AND id_episodio='1981-1982'""") \
        == [(m.RECUPERACAO_NAO_OBSERVADA,)]
    assert set(q("""SELECT id_par FROM fato_comparacao
                    WHERE id_episodio='1981-1982' AND status='SEM_DADOS'""")) \
        == {("pib",), ("exportacoes_eua",)}
    assert q("""SELECT DISTINCT status_recuperacao FROM fato_resumo_episodio r
                JOIN dim_serie s USING (id_serie) WHERE s.grupo IN ('juros','inflacao')""") \
        == [(m.NAO_APLICAVEL,)]
    assert q("SELECT count(*) FROM resultado_hipotese")[0][0] == 3


def test_mesmo_conteudo_nao_publica_de_novo(edicao, cfg):
    raiz, _ = edicao
    r = gerar(cfg, raiz, "20261117-1500", AGORA)
    assert r.status == SEM_ALTERACOES
    assert not (raiz / "edicoes" / "20261117-1500").exists()
