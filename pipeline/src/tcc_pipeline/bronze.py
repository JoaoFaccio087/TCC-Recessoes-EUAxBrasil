"""Camada Bronze: bytes originais de cada coleta e um manifesto por execução (RF02; seção 6.2).

Arquivos:
    bronze/<fonte>/<id_serie>/<coleta_utc>.json
    bronze/_manifestos/<id_execucao>.json
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from .config import Config
from .conectores import conector
from .conectores.http import ErroColeta

OK = "OK"
FALHA = "FALHA"


def _escrever_json(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)


def coletar(cfg: Config, pasta_dados: Path, id_execucao: str, sessao=None, **kw_http) -> dict:
    """Coleta completa de cada série do ``cfg`` (já recortado) e grava o manifesto.

    Uma série que falha não interrompe as demais; o manifesto registra o erro e as tentativas.
    """
    pasta_dados = Path(pasta_dados)
    entradas = []
    for id_s, s in cfg.series.items():
        if s.get("apenas_ficha"):
            continue
        inicio, fim = cfg.janela_coleta(id_s)
        entrada = {"id_serie": id_s, "fonte": s["fonte"], "codigo_origem": s.get("codigo_origem"),
                   "inicio": inicio.isoformat(), "fim": fim.isoformat()}
        try:
            mod = conector(s["fonte"])
            resp = mod.baixar(s, inicio, fim, sessao=sessao, **kw_http)
        except ErroColeta as e:
            entradas.append({**entrada, "status": FALHA, "erro": str(e), "url": e.url,
                             "parametros": e.parametros,
                             "tentativas": [t.__dict__ for t in e.tentativas]})
            continue
        agora = dt.datetime.now(dt.timezone.utc)
        relativo = Path("bronze") / mod.PASTA / id_s / f"{agora:%Y%m%dT%H%M%S%fZ}.json"
        destino = pasta_dados / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(resp.conteudo)
        entradas.append({
            **entrada, "status": OK, "url": resp.url, "parametros": resp.parametros,
            "coletado_em": agora.isoformat(), "status_http": resp.status_http,
            "tamanho": len(resp.conteudo), "sha256": hashlib.sha256(resp.conteudo).hexdigest(),
            "caminho": relativo.as_posix(), "tentativas": resp.tentativas_dict(),
        })
    manifesto = {"id_execucao": id_execucao,
                 "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(),
                 "arquivos": entradas}
    _escrever_json(pasta_dados / "bronze" / "_manifestos" / f"{id_execucao}.json", manifesto)
    return manifesto


def falhas(manifesto: dict) -> list[dict]:
    return [a for a in manifesto["arquivos"] if a["status"] != OK]


def manifestos(pasta_dados: Path) -> list[dict]:
    """Todos os manifestos, em ordem cronológica (o id_execucao começa pelo instante UTC)."""
    pasta = Path(pasta_dados) / "bronze" / "_manifestos"
    if not pasta.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pasta.glob("*.json"))]
