"""Leitura e checagem dos quatro arquivos de configuração (config/*.yaml)."""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
PASTA_CONFIG = RAIZ_PROJETO / "config"

SEM_DADOS = "SEM_DADOS"


def carregar_env(caminho: Path | str = RAIZ_PROJETO / ".env") -> None:
    """Lê ``CHAVE=valor`` do .env sem sobrescrever variáveis já definidas no ambiente."""
    caminho = Path(caminho)
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        if valor:
            os.environ.setdefault(chave.strip(), valor)


def pasta_dados() -> Path:
    """Pasta de dados (fora do Git e, de preferência, fora do OneDrive): ``TCC_DADOS``."""
    return Path(os.environ.get("TCC_DADOS") or RAIZ_PROJETO / "dados")


class ErroConfig(ValueError):
    """Configuração incoerente."""


def mes(texto: str) -> dt.date:
    """'2007-12' -> date(2007, 12, 1)."""
    ano, m = str(texto).split("-")
    return dt.date(int(ano), int(m), 1)


def trimestre(texto: str) -> dt.date:
    """'2007T4' -> date(2007, 10, 1) (primeiro dia do trimestre)."""
    ano, t = str(texto).upper().split("T")
    return dt.date(int(ano), 3 * (int(t) - 1) + 1, 1)


@dataclass(frozen=True)
class Config:
    series: dict
    episodios: dict
    fonte_episodios: dict
    pares: dict
    sem_par: list
    regras: dict

    def pico(self, id_episodio: str, frequencia: str) -> dt.date:
        ep = self.episodios[id_episodio]
        return ep["pico_trimestral"] if frequencia == "T" else ep["pico_mensal"]

    def regra_grupo(self, id_serie: str) -> dict:
        return self.regras["grupos"][self.series[id_serie]["grupo"]]

    def series_metricas(self) -> list[str]:
        """Séries que entram nas métricas (exclui as só de ficha e as auxiliares)."""
        return [s for s, m in self.series.items()
                if not m.get("apenas_ficha") and not m.get("auxiliar")]

    def dependencias(self, id_serie: str) -> list[str]:
        """Séries auxiliares usadas nos tratamentos da série (ex.: deflator)."""
        return [next(iter(p.values())) for p in self.series[id_serie].get("tratamentos") or []
                if isinstance(p, dict) and "deflacionar" in p]

    def janela_coleta(self, id_serie: str) -> tuple[dt.date, dt.date]:
        """Primeiro e último período a coletar: união das janelas de coleta dos episódios."""
        from .gold import somar_periodos

        s = self.series[id_serie]
        f = "T" if s["frequencia"] == "T" else "M"
        a, b = self.regras["janelas"][f]["coleta"]
        picos = [self.pico(str(e), f) for e in s["episodios"]]
        return somar_periodos(min(picos), a, f), somar_periodos(max(picos), b, f)

    def recortar(self, series: list[str] | None = None,
                 episodios: list[str] | None = None) -> "Config":
        """Subconjunto da configuração (ex.: PoC com 2 séries e 2 episódios).

        Mantém só os pares cuja série dos EUA e séries do Brasil (ou ``SEM_DADOS``) estão no recorte.
        """
        eps = list(self.episodios) if not episodios else list(episodios)
        desconhecidos = [e for e in eps if e not in self.episodios]
        if desconhecidos:
            raise ErroConfig(f"episódios desconhecidos: {desconhecidos}")
        ids = list(self.series) if not series else list(series)
        desconhecidas = [s for s in ids if s not in self.series]
        if desconhecidas:
            raise ErroConfig(f"séries desconhecidas: {desconhecidas}")
        ids += [d for s in list(ids) for d in self.dependencias(s) if d not in ids]

        novas = {}
        for s in ids:
            m = self.series[s]
            ep_s = [str(e) for e in m["episodios"] if str(e) in eps]
            if ep_s:
                novas[s] = {**m, "episodios": ep_s}
        pares = {}
        for id_par, p in self.pares.items():
            br = {e: p["br"][e] for e in eps}
            if p["eua"] in novas and all(v == SEM_DADOS or v in novas for v in br.values()):
                pares[id_par] = {**p, "br": br}
        return replace(self, series=novas,
                       episodios={e: self.episodios[e] for e in eps},
                       pares=pares, sem_par=[s for s in self.sem_par if s in novas])


def _ler(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar(pasta: Path | str = PASTA_CONFIG) -> Config:
    pasta = Path(pasta)
    series = _ler(pasta / "series.yaml")["series"]
    ep_raw = _ler(pasta / "episodios.yaml")
    pares_raw = _ler(pasta / "pares.yaml")
    regras = _ler(pasta / "regras.yaml")

    episodios = {}
    for id_ep, e in ep_raw["episodios"].items():
        episodios[str(id_ep)] = {
            **e,
            "pico_mensal": mes(e["pico_mensal"]),
            "vale_mensal": mes(e["vale_mensal"]),
            "pico_trimestral": trimestre(e["pico_trimestral"]),
            "vale_trimestral": trimestre(e["vale_trimestral"]),
        }
    fonte_ep = {k: ep_raw[k] for k in ("fonte", "url", "data_consulta")}

    pares = {}
    for id_par, p in pares_raw["pares"].items():
        pares[id_par] = {**p, "br": {str(k): v for k, v in p["br"].items()}}

    cfg = Config(series, episodios, fonte_ep, pares, pares_raw.get("sem_par", []), regras)
    checar(cfg)
    return cfg


def checar(cfg: Config) -> None:
    """Confere se as referências entre os arquivos fecham."""
    erros: list[str] = []
    grupos = cfg.regras["grupos"]
    for id_s, s in cfg.series.items():
        for d in cfg.dependencias(id_s):
            if d not in cfg.series or not cfg.series[d].get("auxiliar"):
                erros.append(f"série {id_s}: deflator {d!r} precisa ser uma série auxiliar")
            elif cfg.series[d]["frequencia"] != s["frequencia"]:
                erros.append(f"série {id_s}: deflator {d!r} com outra frequência")
        if s.get("auxiliar"):
            if s["tipo_medida"] != "nivel":
                erros.append(f"série auxiliar {id_s}: precisa ser nível")
        elif s.get("grupo") not in grupos:
            erros.append(f"série {id_s}: grupo {s['grupo']!r} sem regra em regras.yaml")
        if s["pais"] not in ("BR", "EUA"):
            erros.append(f"série {id_s}: país inválido {s['pais']!r}")
        if s["frequencia"] not in ("M", "T", "A"):
            erros.append(f"série {id_s}: frequência inválida {s['frequencia']!r}")
        if s["tipo_medida"] not in ("nivel", "taxa"):
            erros.append(f"série {id_s}: tipo_medida inválido {s['tipo_medida']!r}")
        for e in s["episodios"]:
            if str(e) not in cfg.episodios:
                erros.append(f"série {id_s}: episódio {e!r} não cadastrado")
    for id_par, p in cfg.pares.items():
        if p["eua"] not in cfg.series or cfg.series[p["eua"]]["pais"] != "EUA":
            erros.append(f"par {id_par}: série EUA {p['eua']!r} inválida")
        if set(p["br"]) != set(cfg.episodios):
            erros.append(f"par {id_par}: precisa de uma entrada por episódio")
        for id_ep, id_br in p["br"].items():
            if id_br == SEM_DADOS:
                continue
            if id_br not in cfg.series or cfg.series[id_br]["pais"] != "BR":
                erros.append(f"par {id_par}/{id_ep}: série BR {id_br!r} inválida")
            elif id_ep not in [str(e) for e in cfg.series[id_br]["episodios"]]:
                erros.append(f"par {id_par}/{id_ep}: {id_br} não cobre o episódio")
            elif cfg.series[id_br]["frequencia"] != cfg.series[p["eua"]]["frequencia"]:
                erros.append(f"par {id_par}/{id_ep}: frequências diferentes")
    hip = cfg.regras.get("hipoteses", {})
    for chave in ("h1_pares", "h2_h3_grupos"):
        for id_par in hip.get(chave, []):
            if id_par not in cfg.pares:
                erros.append(f"hipoteses.{chave}: {id_par!r} não é um par de pares.yaml")
    for id_s in cfg.sem_par:
        if id_s not in cfg.series:
            erros.append(f"sem_par: série {id_s!r} inexistente")
    if erros:
        raise ErroConfig("Configuração incoerente:\n- " + "\n- ".join(erros))
