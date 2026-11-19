"""Linha de comando: ``python -m tcc_pipeline <comando>`` (engenharia_de_dados.md, seção 6.1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config
from .publicacao import ErroValidacao

# Códigos de saída (iguais aos de pipeline.py)
OK = 0
FALHA = 1
VALIDACAO_REPROVADA = 2
BLOQUEADO = 3


def _lista(texto: str | None) -> list[str] | None:
    return [x.strip() for x in texto.split(",") if x.strip()] if texto else None


def _gerar_exemplo(args) -> int:
    from .exemplo import gerar

    cfg = config.carregar(args.config)
    raiz = args.raiz or config.pasta_dados() / "exemplo" / "publicacao"
    try:
        r = gerar(cfg, raiz, args.id_edicao)
    except ErroValidacao as e:
        print(e, file=sys.stderr)
        return VALIDACAO_REPROVADA
    print(f"{r.status}: edição {r.id_edicao} ({r.linhas} linhas) em {Path(raiz).resolve()}")
    return OK


def _validar(args) -> int:
    from .validacao import edicao_ativa, validar_edicao

    cfg = config.carregar(args.config)
    raiz = args.raiz or config.pasta_dados() / "publicacao"
    pasta = Path(args.edicao) if args.edicao else edicao_ativa(raiz)
    erros = validar_edicao(pasta, cfg.regras["cobertura_minima"])
    if erros:
        print(f"REPROVADA: {pasta}", file=sys.stderr)
        for e in erros:
            print(f"- {e}", file=sys.stderr)
        return VALIDACAO_REPROVADA
    print(f"APROVADA: {pasta}")
    return OK


def _conferir(args) -> int:
    import datetime as dt

    from .conferencia import CONFERE, conferir, relatorio

    cfg = config.carregar(args.config)
    pasta = config.pasta_dados()
    df = conferir(cfg, pasta / "publicacao", series=_lista(args.series))
    agora = dt.datetime.now().astimezone()
    csv, md = relatorio(df, pasta / "conferencia" / agora.strftime("%Y%m%d-%H%M%S"), agora)
    ok = int((df["resultado"] == CONFERE).sum())
    print(f"{ok} de {len(df)} pontos conferem com a fonte (edição {df.attrs.get('edicao')})")
    for r in df[df["resultado"] != CONFERE].itertuples():
        print(f"- {r.id_serie} {r.id_episodio} {r.ponto} {r.data_ref}: edição {r.valor_edicao}, "
              f"fonte {r.valor_fonte} -> {r.resultado}")
    print(f"relatório: {md}\ntabela: {csv}")
    return OK if ok == len(df) else FALHA


def _sus(args) -> int:
    from .sus import ErroRespostas, avaliar, texto

    try:
        res = avaliar(args.respostas)
    except ErroRespostas as e:
        print(e, file=sys.stderr)
        return FALHA
    print(texto(res))
    return OK


def _executar(args) -> int:
    from .pipeline import executar

    cfg = config.carregar(args.config)
    pasta = config.pasta_dados()
    r = executar(args.comando, cfg, pasta, series=_lista(args.series),
                 episodios=_lista(args.episodios))
    reg = r.registro
    print(f"{reg['status']}: {args.comando} {reg['id_execucao']} "
          f"(séries: {reg['series_processadas']}, linhas: {reg['registros']}, "
          f"edição: {reg['id_edicao'] or '-'})")
    if reg.get("observacao"):
        print(f"observação: {reg['observacao']}")
    if reg.get("erro"):
        print(reg["erro"], file=sys.stderr)
    print(f"dados em {pasta}")
    return r.codigo


def main(argv: list[str] | None = None) -> int:
    config.carregar_env()
    p = argparse.ArgumentParser(prog="tcc_pipeline")
    p.add_argument("--config", default=config.PASTA_CONFIG, help="pasta com os YAML")
    sub = p.add_subparsers(dest="comando", required=True)

    g = sub.add_parser("gerar-exemplo", help="publica uma edição sintética no contrato v1")
    g.add_argument("--raiz", default=None, help="padrão: <TCC_DADOS>/exemplo/publicacao")
    g.add_argument("--id-edicao", default=None, help="padrão: AAAAMMDD-HHMM de agora")
    g.set_defaults(func=_gerar_exemplo)

    v = sub.add_parser("validar", help="valida a edição ativa (ou --edicao)")
    v.add_argument("--raiz", default=None, help="padrão: <TCC_DADOS>/publicacao")
    v.add_argument("--edicao", default=None, help="pasta de uma edição específica")
    v.set_defaults(func=_validar)

    c = sub.add_parser("conferir", help="compara a edição ativa com uma consulta nova às fontes (RNF03)")
    c.add_argument("--series", help="lista separada por vírgulas (padrão: todas)")
    c.set_defaults(func=_conferir)

    s = sub.add_parser("sus", help="pontua o questionário SUS (RNF06)")
    s.add_argument("respostas", help="CSV com participante e q1..q10 (1 a 5)")
    s.set_defaults(func=_sus)

    for nome, ajuda in (("atualizar", "coleta + reprocessar + validar + publicar"),
                        ("reprocessar", "refaz Silver e Gold a partir do Bronze, sem coleta")):
        c = sub.add_parser(nome, help=ajuda)
        c.add_argument("--series", help="lista separada por vírgulas (padrão: todas)")
        c.add_argument("--episodios", help="lista separada por vírgulas (padrão: todos)")
        c.set_defaults(func=_executar)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
