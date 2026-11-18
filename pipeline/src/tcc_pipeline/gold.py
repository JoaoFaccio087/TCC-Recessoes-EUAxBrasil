"""Montagem das tabelas Gold do contrato v1 a partir dos valores tratados.

Recebe os valores já tratados por série e data (``valor_tratado``) e devolve um DataFrame
por tabela do contrato. É usado pela edição sintética e será usado pela pipeline real
(depois da Silver e dos tratamentos da seção 4.3).
"""

from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from . import VERSAO_CONTRATO, __version__
from . import metricas as m
from .config import SEM_DADOS, Config
from .contrato import TABELAS
from .hipoteses import avaliar


def somar_periodos(data: dt.date, t: int, frequencia: str) -> dt.date:
    meses = t * (3 if frequencia == "T" else 1)
    total = data.year * 12 + (data.month - 1) + meses
    return dt.date(total // 12, total % 12 + 1, 1)


def _rotulo(data: dt.date, frequencia: str) -> str:
    if frequencia == "T":
        return f"{data.year}T{(data.month - 1) // 3 + 1}"
    return f"{data.year}-{data.month:02d}"


def montar(
    cfg: Config,
    valores: pd.DataFrame,
    rejeitadas: pd.DataFrame,
    metodos: pd.DataFrame,
    metodo_da_serie: dict[str, str],
    edicao: dict,
) -> dict[str, pd.DataFrame]:
    """Monta todas as tabelas da edição.

    valores: id_serie, data_ref (date), valor_original, valor_tratado, coletado_em, id_execucao
    rejeitadas: colunas de observacao_rejeitada
    metodos: colunas de dim_metodo
    metodo_da_serie: id_serie -> id_metodo
    edicao: id_edicao, data_corte (date), publicado_em (datetime)
    """
    id_ed = edicao["id_edicao"]
    data_corte: dt.date = edicao["data_corte"]
    freq = {s: d["frequencia"] for s, d in cfg.series.items()}

    valores = valores.copy()
    valores["status"] = m.OK
    valores["id_edicao"] = id_ed
    v_m = valores[valores["id_serie"].map(freq) == "M"]
    v_t = valores[valores["id_serie"].map(freq) == "T"]

    rej = {(r.id_serie, r.data_ref): r.motivo for r in rejeitadas.itertuples()}
    idx_val = {(r.id_serie, r.data_ref): (r.valor_tratado, r.coletado_em)
               for r in valores.itertuples()}

    # ------------------------------------------------------------ séries alinhadas
    alinhadas = {"M": [], "T": []}
    resumos = []
    painel: dict[tuple[str, str], pd.Series] = {}
    for id_s in cfg.series_metricas():
        s = cfg.series[id_s]
        f = s["frequencia"]
        jan = cfg.regras["janelas"][f]
        regra = m.Regra.de_config(cfg, id_s)
        for id_ep in map(str, s["episodios"]):
            pico = cfg.pico(id_ep, f)
            linhas = []
            for t in range(jan["coleta"][0], jan["coleta"][1] + 1):
                d = somar_periodos(pico, t, f)
                if d > data_corte:
                    break
                if (id_s, d) in idx_val:
                    vt, coletado = idx_val[(id_s, d)]
                    linhas.append((t, d, float(vt), m.OK, None, coletado))
                elif (id_s, d) in rej:
                    linhas.append((t, d, None, m.REJEITADO, rej[(id_s, d)], None))
                else:
                    linhas.append((t, d, None, m.SEM_DADOS, "sem valor na fonte ou no tratamento", None))
            df = pd.DataFrame(linhas, columns=["t_rel", "data_ref", "valor_tratado", "status",
                                               "motivo", "coletado_em"])
            serie_tratada = df.set_index("t_rel")["valor_tratado"].astype("float64")
            vp = m.normalizar(serie_tratada, s["tipo_medida"])
            df["valor_painel"] = vp.values
            df["id_edicao"], df["id_episodio"], df["id_serie"] = id_ed, id_ep, id_s
            df["id_metodo"] = metodo_da_serie[id_s]
            alinhadas[f].append(df)
            painel[(id_s, id_ep)] = vp

            res = m.resumir(vp, regra)
            resumos.append({
                "id_edicao": id_ed, "id_episodio": id_ep, "id_serie": id_s, "frequencia": f,
                "valor_pico": serie_tratada.get(0) if res.valor_pico_painel is not None else None,
                "t_reacao": res.t_reacao, "t_extremo": res.t_extremo, "amplitude": res.amplitude,
                "unidade_amplitude": res.unidade_amplitude, "duracao_queda": res.duracao_queda,
                "t_recuperacao": res.t_recuperacao, "status_reacao": res.status_reacao,
                "status_recuperacao": res.status_recuperacao, "cobertura": res.cobertura,
                "id_metodo": metodo_da_serie[id_s],
            })
    resumo = pd.DataFrame(resumos, columns=TABELAS["fato_resumo_episodio"].nomes)
    idx_res = resumo.set_index(["id_serie", "id_episodio"])

    # ------------------------------------------------------------ ponte e comparação
    ponte, comp = [], []
    for id_par, p in cfg.pares.items():
        f = cfg.series[p["eua"]]["frequencia"]
        for id_ep in cfg.episodios:
            id_br = p["br"][id_ep]
            sem = id_br == SEM_DADOS
            ponte.append({
                "id_par": id_par, "id_episodio": id_ep, "grupo": p["grupo"],
                "id_serie_eua": p["eua"], "id_serie_br": None if sem else id_br,
                "unidade_comparacao": p["unidade_comparacao"],
                "diferencas_metodologicas": p.get("diferencas_metodologicas"),
                "observacao": SEM_DADOS if sem else p.get("observacao"),
            })
            linha = {"id_edicao": id_ed, "id_episodio": id_ep, "id_par": id_par, "frequencia": f,
                     "defasagem": None, "dif_amplitude": None,
                     "unidade_defasagem": "trimestres" if f == "T" else "meses"}
            if sem:
                comp.append({**linha, "status": SEM_DADOS,
                             "motivo": "sem série brasileira no episódio"})
                continue
            rb, re_ = idx_res.loc[(id_br, id_ep)], idx_res.loc[(p["eua"], id_ep)]
            if pd.notna(rb["amplitude"]) and pd.notna(re_["amplitude"]):
                linha["dif_amplitude"] = float(rb["amplitude"] - re_["amplitude"])
            if rb["status_reacao"] == m.OK and re_["status_reacao"] == m.OK:
                linha["defasagem"] = m.defasagem(int(rb["t_reacao"]), int(re_["t_reacao"]))
                comp.append({**linha, "status": m.OK, "motivo": None})
            else:
                status = rb["status_reacao"] if rb["status_reacao"] != m.OK else re_["status_reacao"]
                comp.append({**linha, "status": status,
                             "motivo": f"reação BR: {rb['status_reacao']}; "
                                       f"reação EUA: {re_['status_reacao']}"})
    ponte_df = pd.DataFrame(ponte, columns=TABELAS["ponte_serie_br_eua"].nomes)
    comp_df = pd.DataFrame(comp, columns=TABELAS["fato_comparacao"].nomes)

    # ------------------------------------------------------------ dimensões
    ext = valores.groupby("id_serie")["data_ref"].agg(["min", "max"])
    dim_serie = pd.DataFrame([{
        "id_serie": id_s, "codigo_origem": s.get("codigo_origem"), "nome": s["nome"],
        "descricao": s.get("descricao", s["nome"]), "pais": s["pais"], "fonte": s["fonte"],
        "produtor": s.get("produtor"), "grupo": s["grupo"], "frequencia": s["frequencia"],
        "tipo_medida": s["tipo_medida"], "unidade": s.get("unidade"),
        "ajuste_sazonal": _com_ajuste_sazonal(s),
        "sentido_adverso": cfg.regras["grupos"][s["grupo"]]["sentido_adverso"],
        "inicio_disponivel": ext["min"].get(id_s), "fim_disponivel": ext["max"].get(id_s),
        "aviso_metodologia": s.get("aviso_metodologia"), "url": s.get("url"),
    } for id_s, s in cfg.series.items() if not s.get("auxiliar")])

    dim_episodio = pd.DataFrame([{
        "id_episodio": id_ep, "nome": e["nome"], "pico_mensal": e["pico_mensal"],
        "vale_mensal": e["vale_mensal"], "pico_trimestral": e["pico_trimestral"],
        "vale_trimestral": e["vale_trimestral"], "fonte": cfg.fonte_episodios["fonte"],
        "data_consulta": dt.date.fromisoformat(str(cfg.fonte_episodios["data_consulta"])),
    } for id_ep, e in cfg.episodios.items()])

    vazia = pd.DataFrame(columns=TABELAS["fato_serie_alinhada_mensal"].nomes)
    al_m = pd.concat(alinhadas["M"], ignore_index=True) if alinhadas["M"] else vazia.copy()
    al_t = pd.concat(alinhadas["T"], ignore_index=True) if alinhadas["T"] else vazia.copy()
    tempos = set()
    for df, f in ((v_m, "M"), (v_t, "T"), (al_m, "M"), (al_t, "T")):
        tempos.update((d, f) for d in df["data_ref"])
    if rejeitadas.empty:
        rejeitadas = pd.DataFrame(columns=TABELAS["observacao_rejeitada"].nomes)
    dim_tempo = pd.DataFrame([{
        "data_ref": d, "frequencia": f, "ano": d.year, "trimestre": (d.month - 1) // 3 + 1,
        "mes": d.month if f == "M" else None, "rotulo": _rotulo(d, f),
    } for d, f in sorted(tempos)])

    dim_edicao = pd.DataFrame([{
        "id_edicao": id_ed, "versao_contrato": VERSAO_CONTRATO, "data_corte": data_corte,
        "publicado_em": edicao["publicado_em"], "versao_regras": str(cfg.regras["versao"]),
        "versao_codigo": edicao.get("versao_codigo", __version__),
    }])

    return {
        "dim_serie": dim_serie,
        "dim_episodio": dim_episodio,
        "dim_tempo": dim_tempo,
        "dim_metodo": metodos,
        "dim_edicao": dim_edicao,
        "ponte_serie_br_eua": ponte_df,
        "fato_valor_mensal": v_m,
        "fato_valor_trimestral": v_t,
        "fato_serie_alinhada_mensal": al_m,
        "fato_serie_alinhada_trimestral": al_t,
        "fato_resumo_episodio": resumo,
        "fato_comparacao": comp_df,
        "resultado_hipotese": avaliar(resumo, comp_df, cfg),
        "observacao_rejeitada": rejeitadas,
    }


def montar_de_silver(cfg: Config, obs: pd.DataFrame, rej: pd.DataFrame, meta: pd.DataFrame,
                     edicao: dict) -> dict[str, pd.DataFrame]:
    """Gold a partir da Silver: valor da coleta mais recente, tratamentos e tabelas do contrato."""
    from . import silver, tratamentos

    ids = set(cfg.series_metricas())
    ids |= {d for s in ids for d in cfg.dependencias(s)}
    ult = silver.ultimos_valores(obs[obs["id_serie"].isin(ids)])
    valores = pd.DataFrame({
        "id_serie": ult["id_serie"],
        "data_ref": pd.to_datetime(ult["data_ref"]).dt.date,
        "valor_original": ult["valor"].astype("float64"),
        "coletado_em": pd.to_datetime(ult["coletado_em"]),
        "id_execucao": ult["id_execucao"],
    })
    faltando = sorted(ids - set(valores["id_serie"]))
    if faltando:
        raise ValueError(f"séries sem observações na Silver: {faltando}")
    valores, metodos, metodo_da_serie = tratamentos.aplicar(cfg, valores)

    rej_atual = silver.rejeicoes_atuais(rej[rej["id_serie"].isin(ids)], meta)
    if not rej_atual.empty:
        rej_atual = rej_atual.assign(data_ref=pd.to_datetime(rej_atual["data_ref"]).dt.date)
    return montar(cfg, valores, rej_atual[TABELAS["observacao_rejeitada"].nomes]
                  if not rej_atual.empty else rej_atual, metodos, metodo_da_serie, edicao)


def _com_ajuste_sazonal(s: dict) -> bool:
    """Dessazonalizada na fonte ou pelo STL da pipeline."""
    return bool(s.get("ajuste_sazonal")) or "stl" in (s.get("tratamentos") or [])


def parametros_json(**kw) -> str:
    return json.dumps(kw, ensure_ascii=False, sort_keys=True)
