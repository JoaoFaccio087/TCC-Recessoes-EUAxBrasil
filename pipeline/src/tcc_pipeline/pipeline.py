"""Orquestração de ``atualizar`` e ``reprocessar`` (seção 6; D6, D14, D18, D22, D23).

atualizar   = lock → coleta (Bronze) → Silver → Gold → validação → publicação → registro
reprocessar = lock → Silver → Gold → validação → publicação → registro (sem coleta, RF14)
"""

from __future__ import annotations

import datetime as dt
import traceback
from dataclasses import dataclass
from pathlib import Path

from . import bronze, controle, gold, silver
from .config import Config
from .lock import Trava, TravaOcupada
from .publicacao import SEM_ALTERACOES, ErroValidacao, id_livre, publicar

# Códigos de saída
OK, FALHA, VALIDACAO_REPROVADA, BLOQUEADO = 0, 1, 2, 3


@dataclass
class Execucao:
    codigo: int
    registro: dict


def _agora_local() -> dt.datetime:
    return dt.datetime.now().astimezone().replace(microsecond=0)


def executar(comando: str, cfg_completo: Config, pasta_dados: Path, *,
             series: list[str] | None = None, episodios: list[str] | None = None,
             sessao=None, agora: dt.datetime | None = None,
             kw_http: dict | None = None) -> Execucao:
    """``series``/``episodios`` recortam a coleta e a edição (ex.: PoC). A Silver é sempre
    reconstruída com todas as séries do Bronze."""
    if comando not in ("atualizar", "reprocessar"):
        raise ValueError(comando)
    cfg = cfg_completo.recortar(series, episodios)
    pasta_dados = Path(pasta_dados)
    raiz_pub = pasta_dados / "publicacao"
    inicio = dt.datetime.now(dt.timezone.utc)
    reg = {"id_execucao": controle.novo_id(inicio), "inicio": inicio.isoformat(), "fim": None,
           "comando": comando, "series_processadas": 0, "registros": 0, "status": None,
           "id_edicao": None, "erro": None, "observacao": None,
           "series": sorted(cfg.series), "episodios": list(cfg.episodios)}

    trava = Trava(pasta_dados / ".lock")
    try:
        trava.adquirir()
    except TravaOcupada as e:
        reg.update(status=controle.BLOQUEADO, erro=str(e),
                   fim=dt.datetime.now(dt.timezone.utc).isoformat())
        controle.registrar(pasta_dados, reg)
        return Execucao(BLOQUEADO, reg)

    codigo = FALHA
    try:
        if trava.esquecida_removida:
            reg["observacao"] = f"LOCK_ESQUECIDO_REMOVIDO {trava.conteudo_removido}"

        if comando == "atualizar":
            man = bronze.coletar(cfg, pasta_dados, reg["id_execucao"], sessao=sessao,
                                 **(kw_http or {}))
            reg["series_processadas"] = sum(a["status"] == bronze.OK for a in man["arquivos"])
            falhas = bronze.falhas(man)
            if falhas:
                raise RuntimeError("coleta falhou: " + "; ".join(
                    f"{a['id_serie']}: {a['erro']}" for a in falhas))

        obs, rej, meta = silver.reconstruir(cfg_completo, pasta_dados)
        silver.gravar(pasta_dados, obs, rej, meta)
        if comando == "reprocessar":
            reg["series_processadas"] = int(meta["id_serie"].isin(list(cfg.series)).sum())

        agora = agora or _agora_local()
        id_edicao = id_livre(raiz_pub, agora.strftime("%Y%m%d-%H%M"))
        tabelas = gold.montar_de_silver(cfg, obs, rej, meta, {
            "id_edicao": id_edicao, "data_corte": agora.date(),
            "publicado_em": agora.replace(tzinfo=None)})
        res = publicar(raiz_pub, tabelas, id_edicao, agora, agora.date(),
                       cfg.regras["cobertura_minima"])
        reg.update(status=res.status, registros=res.linhas,
                   id_edicao=res.id_edicao if res.status != SEM_ALTERACOES else None)
        if res.status == SEM_ALTERACOES:
            reg["observacao"] = ((reg["observacao"] + "; ") if reg["observacao"] else "") + \
                f"conteúdo igual ao da edição ativa {res.id_edicao}"
        codigo = OK
    except ErroValidacao as e:
        reg.update(status=controle.FALHA, erro=str(e))
        codigo = VALIDACAO_REPROVADA
    except Exception as e:  # registrar qualquer falha (RF13) e manter a edição anterior
        reg.update(status=controle.FALHA,
                   erro=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=5)}")
        codigo = FALHA
    finally:
        reg["fim"] = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            controle.registrar(pasta_dados, reg)
            controle.reconstruir_parquet(pasta_dados, raiz_pub)
        finally:
            trava.liberar()
    return Execucao(codigo, reg)
