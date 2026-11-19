"""HTTP com nova tentativa automática (D24) e limite de requisições por minuto."""

from __future__ import annotations

import datetime as dt
import threading
import time
from dataclasses import asdict, dataclass, field

import requests

TENTATIVAS = 3
ESPERA_BASE_S = 2.0
TIMEOUT_S = 60
OCULTAR = {"api_key"}


@dataclass
class Tentativa:
    numero: int
    instante_utc: str
    status_http: int | None
    erro: str | None
    duracao_s: float


@dataclass
class Resposta:
    conteudo: bytes
    status_http: int
    url: str
    parametros: dict
    tentativas: list[Tentativa] = field(default_factory=list)

    def tentativas_dict(self) -> list[dict]:
        return [asdict(t) for t in self.tentativas]


class ErroColeta(RuntimeError):
    def __init__(self, mensagem: str, tentativas: list[Tentativa] | None = None,
                 url: str | None = None, parametros: dict | None = None):
        super().__init__(mensagem)
        self.tentativas = tentativas or []
        self.url = url
        self.parametros = parametros or {}


class LimiteTaxa:
    """Espaça as requisições para não passar de ``por_minuto``."""

    def __init__(self, por_minuto: int, relogio=time.monotonic, dormir=time.sleep):
        self.intervalo = 60.0 / por_minuto
        self._ultimo: float | None = None
        self._relogio, self._dormir = relogio, dormir
        self._trava = threading.Lock()

    def aguardar(self) -> None:
        with self._trava:
            agora = self._relogio()
            if self._ultimo is not None:
                falta = self._ultimo + self.intervalo - agora
                if falta > 0:
                    self._dormir(falta)
                    agora += falta
            self._ultimo = agora


def _sem_segredos(parametros: dict) -> dict:
    return {k: ("***" if k in OCULTAR else v) for k, v in (parametros or {}).items()}


def _repetir(status: int | None, erro: Exception | None) -> bool:
    if erro is not None:
        return isinstance(erro, (requests.Timeout, requests.ConnectionError))
    return status == 429 or (status is not None and status >= 500)


def obter(
    url: str,
    parametros: dict | None = None,
    *,
    sessao=None,
    timeout: float = TIMEOUT_S,
    tentativas: int = TENTATIVAS,
    espera_base: float = ESPERA_BASE_S,
    limite: LimiteTaxa | None = None,
    dormir=time.sleep,
    corpo_json: dict | None = None,
) -> Resposta:
    """GET (ou POST com ``corpo_json``) com até ``tentativas`` tentativas e espera crescente
    (2 s, 4 s, ...).

    Repete em timeout, erro de conexão, HTTP 429 e 5xx. Outros erros HTTP falham na hora.
    Os parâmetros registrados nunca incluem a chave da API.
    """
    sessao = sessao or requests
    publicos = _sem_segredos(parametros)
    if corpo_json is not None:
        publicos = {**publicos, "corpo_json": corpo_json}
    registro: list[Tentativa] = []
    for n in range(1, tentativas + 1):
        if limite:
            limite.aguardar()
        inicio = time.monotonic()
        instante = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        resp, erro = None, None
        try:
            if corpo_json is None:
                resp = sessao.get(url, params=parametros, timeout=timeout)
            else:
                resp = sessao.post(url, params=parametros, json=corpo_json, timeout=timeout)
        except requests.RequestException as e:
            erro = e
        status = resp.status_code if resp is not None else None
        registro.append(Tentativa(n, instante, status,
                                  f"{type(erro).__name__}: {erro}" if erro else None,
                                  round(time.monotonic() - inicio, 3)))
        if erro is None and status is not None and 200 <= status < 300:
            return Resposta(resp.content, status, url, publicos, registro)
        if not _repetir(status, erro) or n == tentativas:
            detalhe = f"HTTP {status}" if erro is None else registro[-1].erro
            if resp is not None and erro is None:
                corpo = resp.content[:300].decode("utf-8", "replace")
                for segredo in (str(parametros.get(k)) for k in OCULTAR if parametros and k in parametros):
                    corpo = corpo.replace(segredo, "***")
                detalhe += f": {corpo}"
            raise ErroColeta(f"falha ao obter {url} após {n} tentativa(s): {detalhe}",
                             registro, url, publicos)
        dormir(espera_base * 2 ** (n - 1))
    raise AssertionError("inalcançável")
