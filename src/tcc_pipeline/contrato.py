"""Contrato de saída v1 (engenharia_de_dados.md, seção 8).

Fonte única de nomes, tipos (DuckDB), chaves e ordenação das tabelas de cada edição.
Usado pela publicação (cast e ordem das colunas) e pela validação (esquema, unicidade).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tabela:
    nome: str
    colunas: tuple[tuple[str, str], ...]
    chave: tuple[str, ...]
    ordem: tuple[str, ...] = field(default=())

    @property
    def arquivo(self) -> str:
        return f"{self.nome}.parquet"

    @property
    def nomes(self) -> list[str]:
        return [c for c, _ in self.colunas]


_VALOR = (
    ("id_edicao", "VARCHAR"), ("id_serie", "VARCHAR"), ("data_ref", "DATE"),
    ("valor_original", "DOUBLE"), ("valor_tratado", "DOUBLE"), ("status", "VARCHAR"),
    ("coletado_em", "TIMESTAMP"), ("id_execucao", "VARCHAR"),
)
_ALINHADA = (
    ("id_edicao", "VARCHAR"), ("id_episodio", "VARCHAR"), ("id_serie", "VARCHAR"),
    ("t_rel", "SMALLINT"), ("data_ref", "DATE"), ("valor_tratado", "DOUBLE"),
    ("valor_painel", "DOUBLE"), ("status", "VARCHAR"), ("motivo", "VARCHAR"),
    ("id_metodo", "VARCHAR"), ("coletado_em", "TIMESTAMP"),
)

TABELAS: dict[str, Tabela] = {t.nome: t for t in [
    # ---------------------------------------------------------------- dimensões (8.1)
    Tabela("dim_serie", (
        ("id_serie", "VARCHAR"), ("codigo_origem", "VARCHAR"), ("nome", "VARCHAR"),
        ("descricao", "VARCHAR"), ("pais", "VARCHAR"), ("fonte", "VARCHAR"),
        ("produtor", "VARCHAR"), ("grupo", "VARCHAR"), ("frequencia", "VARCHAR"),
        ("tipo_medida", "VARCHAR"), ("unidade", "VARCHAR"), ("ajuste_sazonal", "BOOLEAN"),
        ("sentido_adverso", "VARCHAR"), ("inicio_disponivel", "DATE"),
        ("fim_disponivel", "DATE"), ("aviso_metodologia", "VARCHAR"), ("url", "VARCHAR"),
    ), ("id_serie",), ("id_serie",)),
    Tabela("dim_episodio", (
        ("id_episodio", "VARCHAR"), ("nome", "VARCHAR"), ("pico_mensal", "DATE"),
        ("vale_mensal", "DATE"), ("pico_trimestral", "DATE"), ("vale_trimestral", "DATE"),
        ("fonte", "VARCHAR"), ("data_consulta", "DATE"),
    ), ("id_episodio",), ("id_episodio",)),
    Tabela("dim_tempo", (
        ("data_ref", "DATE"), ("frequencia", "VARCHAR"), ("ano", "SMALLINT"),
        ("trimestre", "TINYINT"), ("mes", "TINYINT"), ("rotulo", "VARCHAR"),
    ), ("data_ref", "frequencia"), ("frequencia", "data_ref")),
    Tabela("dim_metodo", (
        ("id_metodo", "VARCHAR"), ("descricao", "VARCHAR"), ("parametros", "VARCHAR"),
        ("versao", "VARCHAR"),
    ), ("id_metodo",), ("id_metodo",)),
    Tabela("dim_edicao", (
        ("id_edicao", "VARCHAR"), ("versao_contrato", "INTEGER"), ("data_corte", "DATE"),
        ("publicado_em", "TIMESTAMP"), ("versao_regras", "VARCHAR"), ("versao_codigo", "VARCHAR"),
    ), ("id_edicao",), ("id_edicao",)),
    Tabela("ponte_serie_br_eua", (
        ("id_par", "VARCHAR"), ("id_episodio", "VARCHAR"), ("grupo", "VARCHAR"),
        ("id_serie_eua", "VARCHAR"), ("id_serie_br", "VARCHAR"),
        ("unidade_comparacao", "VARCHAR"), ("diferencas_metodologicas", "VARCHAR"),
        ("observacao", "VARCHAR"),
    ), ("id_par", "id_episodio"), ("id_episodio", "id_par")),
    # ---------------------------------------------------------------- fatos (8.2)
    Tabela("fato_valor_mensal", _VALOR, ("id_serie", "data_ref"), ("id_serie", "data_ref")),
    Tabela("fato_valor_trimestral", _VALOR, ("id_serie", "data_ref"), ("id_serie", "data_ref")),
    Tabela("fato_serie_alinhada_mensal", _ALINHADA, ("id_episodio", "id_serie", "t_rel"),
           ("id_episodio", "id_serie", "t_rel")),
    Tabela("fato_serie_alinhada_trimestral", _ALINHADA, ("id_episodio", "id_serie", "t_rel"),
           ("id_episodio", "id_serie", "t_rel")),
    Tabela("fato_resumo_episodio", (
        ("id_edicao", "VARCHAR"), ("id_episodio", "VARCHAR"), ("id_serie", "VARCHAR"),
        ("frequencia", "VARCHAR"), ("valor_pico", "DOUBLE"), ("t_reacao", "SMALLINT"),
        ("t_extremo", "SMALLINT"), ("amplitude", "DOUBLE"), ("unidade_amplitude", "VARCHAR"),
        ("duracao_queda", "SMALLINT"), ("t_recuperacao", "SMALLINT"),
        ("status_reacao", "VARCHAR"), ("status_recuperacao", "VARCHAR"),
        ("cobertura", "DOUBLE"), ("id_metodo", "VARCHAR"),
    ), ("id_episodio", "id_serie"), ("id_episodio", "id_serie")),
    Tabela("fato_comparacao", (
        ("id_edicao", "VARCHAR"), ("id_episodio", "VARCHAR"), ("id_par", "VARCHAR"),
        ("frequencia", "VARCHAR"), ("defasagem", "SMALLINT"), ("unidade_defasagem", "VARCHAR"),
        ("dif_amplitude", "DOUBLE"), ("status", "VARCHAR"), ("motivo", "VARCHAR"),
    ), ("id_episodio", "id_par"), ("id_episodio", "id_par")),
    # ---------------------------------------------------------------- apoio (8.3)
    Tabela("resultado_hipotese", (
        ("hipotese", "VARCHAR"), ("resultado", "VARCHAR"), ("n_pares", "INTEGER"),
        ("detalhe", "VARCHAR"),
    ), ("hipotese",), ("hipotese",)),
    Tabela("observacao_rejeitada", (
        ("id_serie", "VARCHAR"), ("data_ref", "DATE"), ("valor_bruto", "VARCHAR"),
        ("motivo", "VARCHAR"), ("coletado_em", "TIMESTAMP"), ("id_execucao", "VARCHAR"),
    ), ("id_serie", "data_ref", "coletado_em"), ("id_serie", "data_ref")),
]}

# Chaves estrangeiras: (tabela, coluna) -> (dimensão, coluna). Nulos são permitidos.
REFERENCIAS: list[tuple[str, str, str, str]] = [
    (fato, "id_serie", "dim_serie", "id_serie")
    for fato in ("fato_valor_mensal", "fato_valor_trimestral", "fato_serie_alinhada_mensal",
                 "fato_serie_alinhada_trimestral", "fato_resumo_episodio", "observacao_rejeitada")
] + [
    (fato, "id_episodio", "dim_episodio", "id_episodio")
    for fato in ("fato_serie_alinhada_mensal", "fato_serie_alinhada_trimestral",
                 "fato_resumo_episodio", "fato_comparacao", "ponte_serie_br_eua")
] + [
    (fato, "id_metodo", "dim_metodo", "id_metodo")
    for fato in ("fato_serie_alinhada_mensal", "fato_serie_alinhada_trimestral",
                 "fato_resumo_episodio")
] + [
    (fato, "id_edicao", "dim_edicao", "id_edicao")
    for fato in ("fato_valor_mensal", "fato_valor_trimestral", "fato_serie_alinhada_mensal",
                 "fato_serie_alinhada_trimestral", "fato_resumo_episodio", "fato_comparacao")
] + [
    ("fato_comparacao", "id_par", "ponte_serie_br_eua", "id_par"),
    ("ponte_serie_br_eua", "id_serie_eua", "dim_serie", "id_serie"),
    ("ponte_serie_br_eua", "id_serie_br", "dim_serie", "id_serie"),
]
