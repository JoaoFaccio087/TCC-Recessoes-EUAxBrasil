"""Tratamentos da seção 4.3, na ordem do texto 7.3:
(1) desconto da inflação, (2) padronização das unidades, (3) ajuste sazonal, (4) normalização pelo pico.

Cada série declara os passos 1 a 3 em ``series.yaml`` (campo ``tratamentos``). A normalização
(4) é feita na Gold, por episódio (``metricas.normalizar``). Os passos são aplicados sempre na
ordem do texto, qualquer que seja a ordem em que foram escritos.

Passos disponíveis:
    encadear_variacao          (1) variação % mensal -> número-índice encadeado (Ibovespa);
    {encadear_variacao: AAAA-MM}   idem, com 100 no mês-base indicado
    {deflacionar: <id_serie>}  (1) divide pelo índice de preços de uma série auxiliar
    var_12m                    (2) número-índice de preços -> variação % acumulada em 12 meses
    stl                        (3) ajuste sazonal STL (Cleveland et al., 1990); log para nível

Uma série cujo grupo exige um tratamento que ela não declara falha com ``ErroTratamento``,
em vez de entrar na edição sem o tratamento devido.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from .config import Config
from .gold import parametros_json


class ErroTratamento(RuntimeError):
    pass


GRUPOS_DEFLACIONADOS = {"acoes", "exportacoes"}
GRUPOS_COM_STL = {"producao_industrial", "desemprego", "exportacoes"}

# etapa do texto 7.3 (a ordem dentro da etapa 1 importa: encadear antes de deflacionar)
ETAPA = {"encadear_variacao": (1, 0), "deflacionar": (1, 1), "var_12m": (2, 0), "stl": (3, 0)}
STL_PARAMS = {"robust": True}
PERIODO = {"M": 12, "T": 4}
FREQ_PANDAS = {"M": "MS", "T": "QS"}


# ------------------------------------------------------------------ declaração

def nome(passo) -> str:
    return passo if isinstance(passo, str) else next(iter(passo))


def argumento(passo):
    return None if isinstance(passo, str) else next(iter(passo.values()))


def passos(cfg: Config, id_serie: str) -> list:
    lista = cfg.series[id_serie].get("tratamentos") or []
    desconhecidos = [nome(p) for p in lista if nome(p) not in ETAPA]
    if desconhecidos:
        raise ErroTratamento(f"{id_serie}: tratamentos desconhecidos {desconhecidos}")
    return sorted(lista, key=lambda p: ETAPA[nome(p)])


def pendentes(cfg: Config, id_serie: str) -> list[str]:
    """Tratamentos que o grupo da série exige e que ela não declara."""
    s = cfg.series[id_serie]
    nomes = {nome(p) for p in s.get("tratamentos") or []}
    falta = []
    if s["grupo"] in GRUPOS_DEFLACIONADOS and "deflacionar" not in nomes:
        falta.append("desconto da inflação")
    if not s.get("ajuste_sazonal") and s["grupo"] in GRUPOS_COM_STL and "stl" not in nomes:
        falta.append("ajuste sazonal (STL)")
    return falta


# ------------------------------------------------------------------ funções (pd.Series com DatetimeIndex)

def _regular(s: pd.Series, freq: str) -> pd.Series:
    """Reindexa para a frequência completa: lacunas viram NaN explícito."""
    s = s.sort_index()
    if s.empty:
        return s
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq=FREQ_PANDAS[freq]))


def encadear_variacao(var_pct: pd.Series, freq: str = "M", base: str | None = None) -> pd.Series:
    """Índice = produto acumulado de (1 + v/100), com 100 no mês ``base`` (AAAA-MM) ou, sem
    ``base``, no primeiro período.

    Uma lacuna interrompe o encadeamento: os períodos seguintes ficam sem valor, porque o
    nível depois dela é desconhecido.
    """
    s = _regular(var_pct.astype("float64"), freq)
    idx = ((1 + s / 100).cumprod(skipna=False) * 100).dropna()
    if base is None:
        return idx
    t = pd.Timestamp(f"{base}-01")
    if t not in idx.index:
        raise ErroTratamento(f"mês-base {base} fora do índice encadeado")
    return idx / idx[t] * 100


def deflacionar(nominal: pd.Series, indice_precos: pd.Series) -> pd.Series:
    """Valor real na base do índice de preços. Depois da normalização pelo pico (pico = 100) o
    resultado é o mesmo de usar a base no pico de cada episódio (D10)."""
    return (nominal / indice_precos.reindex(nominal.index) * 100).dropna()


def var_12m(indice: pd.Series, freq: str = "M") -> pd.Series:
    if freq != "M":
        raise ErroTratamento("var_12m só se aplica a séries mensais")
    s = _regular(indice.astype("float64"), freq)
    return ((s / s.shift(12) - 1) * 100).dropna()


def ajuste_stl(serie: pd.Series, freq: str, tipo_medida: str) -> pd.Series:
    """Série dessazonalizada por STL em cada trecho contínuo com pelo menos 2 ciclos completos.

    Nível: STL sobre o log (sazonalidade multiplicativa). Taxa: STL aditivo. Trechos curtos
    demais ficam sem valor.
    """
    periodo = PERIODO[freq]
    s = _regular(serie.astype("float64"), freq)
    trecho = s.isna().cumsum()
    partes = []
    for _, bloco in s[s.notna()].groupby(trecho[s.notna()]):
        if len(bloco) < 2 * periodo + 1:
            continue
        y = np.log(bloco) if tipo_medida == "nivel" else bloco
        r = STL(y, period=periodo, **STL_PARAMS).fit()
        aj = y - r.seasonal
        partes.append(np.exp(aj) if tipo_medida == "nivel" else aj)
    return pd.concat(partes).sort_index() if partes else s.iloc[:0]


# ------------------------------------------------------------------ dim_metodo

_DESCR = {
    "encadear_variacao": "variação % mensal encadeada em número-índice",
    "var_12m": "variação % acumulada em 12 meses calculada a partir do número-índice",
    "stl": "ajuste sazonal STL (Cleveland et al., 1990; período {periodo}, robusto, {escala})",
}
_NORM = {
    "nivel": ("indice_pico_100", "número-índice com o pico = 100"),
    "taxa": ("pp_pico", "diferença em p.p. em relação ao pico"),
}


def metodo(cfg: Config, id_serie: str) -> dict:
    s = cfg.series[id_serie]
    ids, descr, params = [], [], []
    for p in passos(cfg, id_serie):
        n, arg = nome(p), argumento(p)
        if n == "deflacionar":
            d = cfg.series[arg]
            ids.append(f"deflac_{arg}")
            descr.append(f"deflacionado por {d['nome']} ({d['fonte']} {d['codigo_origem']})")
            params.append({"passo": n, "deflator": arg, "codigo_deflator": d["codigo_origem"]})
        elif n == "stl":
            ids.append("stl")
            escala = "log do nível" if s["tipo_medida"] == "nivel" else "aditivo"
            descr.append(_DESCR[n].format(periodo=PERIODO[s["frequencia"]], escala=escala))
            params.append({"passo": n, "periodo": PERIODO[s["frequencia"]],
                           "log": s["tipo_medida"] == "nivel", **STL_PARAMS})
        elif n == "encadear_variacao":
            ids.append("encadear")
            descr.append(_DESCR[n] + (f" ({arg} = 100)" if arg else ""))
            params.append({"passo": n, "base": arg})
        else:
            ids.append("var12m")
            descr.append(_DESCR[n])
            params.append({"passo": n})
    id_norm, descr_norm = _NORM[s["tipo_medida"]]
    if not descr:
        descr.append("valor da fonte, sem tratamento adicional")
    return {
        "id_metodo": "+".join(ids + [id_norm]),
        "descricao": "; ".join(descr) + f"; normalizado como {descr_norm} (texto 7.3).",
        "parametros": parametros_json(normalizacao=id_norm, tratamentos=params),
        "versao": "1",
    }


def id_metodo(cfg: Config, id_serie: str) -> str:
    return metodo(cfg, id_serie)["id_metodo"]


# ------------------------------------------------------------------ aplicação

def _serie(valores: pd.DataFrame, id_s: str) -> pd.Series:
    v = valores[valores["id_serie"] == id_s]
    return pd.Series(v["valor_original"].to_numpy("float64"),
                     index=pd.to_datetime(v["data_ref"])).sort_index()


def tratar(cfg: Config, id_serie: str, valores: pd.DataFrame) -> pd.Series:
    """Valor tratado (passos 1 a 3) de uma série, indexado por data."""
    s = cfg.series[id_serie]
    f = s["frequencia"]
    x = _serie(valores, id_serie)
    for p in passos(cfg, id_serie):
        n, arg = nome(p), argumento(p)
        if n == "encadear_variacao":
            x = encadear_variacao(x, f, arg)
        elif n == "deflacionar":
            x = deflacionar(x, _serie(valores, arg))
        elif n == "var_12m":
            x = var_12m(x, f)
        elif n == "stl":
            x = ajuste_stl(x, f, s["tipo_medida"])
    return x


def aplicar(cfg: Config, valores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    """valores: id_serie, data_ref, valor_original, ... (séries das métricas e auxiliares).

    Devolve (valores das séries das métricas com ``valor_tratado``, dim_metodo, id_metodo por
    série). Datas sem valor tratado (ex.: os 12 primeiros meses de var_12m, mês sem deflator)
    saem da tabela e aparecem como lacuna na série alinhada.
    """
    metricas = [s for s in cfg.series_metricas() if s in set(valores["id_serie"])]
    erros = {s: f for s in metricas if (f := pendentes(cfg, s))}
    if erros:
        detalhe = "; ".join(f"{s}: {', '.join(f)}" for s, f in sorted(erros.items()))
        raise ErroTratamento(f"tratamentos exigidos e não declarados: {detalhe}")

    partes = []
    for id_s in metricas:
        tratado = tratar(cfg, id_s, valores)
        v = valores[valores["id_serie"] == id_s].copy()
        v["valor_tratado"] = pd.to_datetime(v["data_ref"]).map(tratado).astype("float64").to_numpy()
        partes.append(v[v["valor_tratado"].notna()])
    saida = (pd.concat(partes, ignore_index=True) if partes
             else valores.iloc[:0].assign(valor_tratado=pd.Series(dtype="float64")))

    todos = [s for s in cfg.series_metricas()]
    metodos = pd.DataFrame([metodo(cfg, s) for s in todos]).drop_duplicates("id_metodo")
    return saida, metodos.reset_index(drop=True), {s: id_metodo(cfg, s) for s in todos}
