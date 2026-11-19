"""Pontuação do questionário System Usability Scale (BROOKE, 1996; RNF06; texto 7.6).

Entrada: CSV com ``participante`` e ``q1`` a ``q10`` (respostas de 1 a 5).
Itens ímpares (positivos) valem resposta − 1; pares (negativos) valem 5 − resposta.
Pontuação = soma × 2,5 (0 a 100).

Adjetivo: o da escala de Bangor, Kortum e Miller (2009) cuja pontuação média é a mais
próxima da obtida. Médias por adjetivo usadas aqui (conferir com a Tabela da referência
antes de citar no texto).
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pandas as pd

ITENS = [f"q{i}" for i in range(1, 11)]
META_RNF06 = 70.0
# Médias da pontuação SUS por adjetivo (Bangor; Kortum; Miller, 2009).
ADJETIVOS = [
    (12.5, "Pior imaginável"),
    (20.3, "Péssimo"),
    (35.7, "Ruim"),
    (50.9, "OK"),
    (71.4, "Bom"),
    (85.5, "Excelente"),
    (90.9, "Melhor imaginável"),
]


class ErroRespostas(ValueError):
    pass


def pontuar(respostas: list[int]) -> float:
    if len(respostas) != 10:
        raise ErroRespostas(f"são 10 respostas, vieram {len(respostas)}")
    if any(not isinstance(r, int) or not 1 <= r <= 5 for r in respostas):
        raise ErroRespostas(f"respostas fora da escala 1 a 5: {respostas}")
    soma = sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(respostas))
    return soma * 2.5


def adjetivo(pontuacao: float) -> str:
    return min(ADJETIVOS, key=lambda a: abs(a[0] - pontuacao))[1]


def avaliar(caminho_csv: Path | str) -> dict:
    df = pd.read_csv(caminho_csv, sep=None, engine="python", dtype={"participante": str})
    faltando = [c for c in ["participante", *ITENS] if c not in df.columns]
    if faltando:
        raise ErroRespostas(f"colunas ausentes no CSV: {faltando}")
    df = df.dropna(subset=ITENS, how="all")
    linhas = []
    for r in df.itertuples(index=False):
        resp = [int(getattr(r, q)) for q in ITENS]
        p = pontuar(resp)
        linhas.append({"participante": r.participante, "pontuacao": p, "adjetivo": adjetivo(p)})
    if not linhas:
        raise ErroRespostas("nenhuma resposta no CSV")
    notas = [l["pontuacao"] for l in linhas]
    media = statistics.fmean(notas)
    return {
        "participantes": linhas,
        "n": len(notas),
        "media": media,
        "desvio_padrao": statistics.stdev(notas) if len(notas) > 1 else 0.0,
        "mediana": statistics.median(notas),
        "minimo": min(notas),
        "maximo": max(notas),
        "adjetivo_media": adjetivo(media),
        "meta_rnf06": META_RNF06,
        "atende_rnf06": media >= META_RNF06,
    }


def texto(res: dict) -> str:
    linhas = [f"{p['participante']:>12}: {p['pontuacao']:5.1f}  {p['adjetivo']}" for p in res["participantes"]]
    linhas += [
        "",
        f"Participantes: {res['n']}",
        f"Média: {res['media']:.1f} (desvio padrão {res['desvio_padrao']:.1f}; mediana {res['mediana']:.1f}; "
        f"de {res['minimo']:.1f} a {res['maximo']:.1f})",
        f"Adjetivo da média (Bangor, Kortum e Miller, 2009): {res['adjetivo_media']}",
        f"RNF06 (média ≥ {res['meta_rnf06']:.0f}): {'ATENDIDO' if res['atende_rnf06'] else 'NÃO ATENDIDO'}",
    ]
    return "\n".join(linhas)
