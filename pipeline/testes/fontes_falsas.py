"""Sessão HTTP falsa que imita o FRED e o SIDRA, para testar a pipeline sem rede."""

from __future__ import annotations

import datetime as dt
import json
import math
import re

PICOS = [dt.date(2007, 12, 1), dt.date(2020, 2, 1)]
ULTIMO_MES = dt.date(2026, 9, 1)


def _meses(inicio: dt.date, fim: dt.date):
    d = inicio
    while d <= min(fim, ULTIMO_MES):
        yield d
        d = dt.date(d.year + d.month // 12, d.month % 12 + 1, 1)


def _dist(a: dt.date, b: dt.date) -> int:
    return (a.year - b.year) * 12 + a.month - b.month


def valor(d: dt.date, profundidade: float, duracao: int) -> float:
    """100 antes do pico; queda em forma de seno até ``duracao`` meses; 101 depois."""
    for p in PICOS:
        t = _dist(d, p)
        if 0 < t < duracao:
            return 100 - profundidade * math.sin(math.pi * t / duracao)
        if duracao <= t <= 72:
            return 101.0
    return 100.0


class Resp:
    def __init__(self, status: int, conteudo: bytes):
        self.status_code, self.content = status, conteudo


class SessaoFalsa:
    def __init__(self, ajuste: float = 0.0, falhar: set[str] | None = None,
                 sidra_extras: dict[str, str] | None = None):
        self.ajuste = ajuste  # soma ao valor (simula revisão)
        self.falhar = falhar or set()  # "fred" | "sidra" -> HTTP 500
        self.sidra_extras = sidra_extras or {}  # período AAAAMM -> valor bruto
        self.chamadas: list[str] = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append(url)
        if "stlouisfed" in url:
            if "fred" in self.falhar:
                return Resp(500, b"erro interno")
            ini = dt.date.fromisoformat(params["observation_start"])
            fim = dt.date.fromisoformat(params["observation_end"])
            obs = [{"date": d.isoformat(), "value": f"{valor(d, 12, 20) + self.ajuste:.4f}"}
                   for d in _meses(ini, fim)]
            return Resp(200, json.dumps({"observations": obs}).encode())
        if "apisidra" in url:
            if "sidra" in self.falhar:
                return Resp(500, b"erro interno")
            a, b = re.search(r"/p/(\d{6})-(\d{6})", url).groups()
            ini = dt.date(int(a[:4]), int(a[4:]), 1)
            fim = dt.date(int(b[:4]), int(b[4:]), 1)
            linhas = [{"MN": "Número-índice", "V": "Valor", "D3C": "Mês (Código)"}]
            for d in _meses(max(ini, dt.date(2002, 1, 1)), fim):
                cod = f"{d.year}{d.month:02d}"
                v = self.sidra_extras.get(cod, f"{valor(d, 15, 26) + self.ajuste:.5f}")
                linhas.append({"MN": "Número-índice", "V": v, "D3C": cod})
            return Resp(200, json.dumps(linhas, ensure_ascii=False).encode())
        return Resp(404, b"")
