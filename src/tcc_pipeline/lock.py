"""Trava por arquivo de lock (D14, D22).

Uso::

    with Trava(Path("dados/.lock")) as trava:
        ...  # atualizar ou reprocessar
        if trava.esquecida_removida: registrar LOCK_ESQUECIDO_REMOVIDO

O lock é criado com abertura exclusiva e guarda PID e horário de início. É removido no
``__exit__`` (equivale ao ``finally``), inclusive quando a execução falha. Um lock é tratado
como esquecido se o processo do PID não existe mais, se o PID foi reaproveitado por um
processo criado depois do lock, ou se o lock tem mais de ``idade_maxima``.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import psutil

IDADE_MAXIMA = dt.timedelta(hours=2)
_TOLERANCIA_ESCRITA = dt.timedelta(seconds=60)


class TravaOcupada(RuntimeError):
    """Outra execução válida detém o lock."""

    def __init__(self, caminho: Path, conteudo: dict | None):
        self.conteudo = conteudo or {}
        super().__init__(f"lock ocupado em {caminho}: {self.conteudo}")


def _agora() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Trava:
    def __init__(self, caminho: Path | str, idade_maxima: dt.timedelta = IDADE_MAXIMA):
        self.caminho = Path(caminho)
        self.idade_maxima = idade_maxima
        self.esquecida_removida = False
        self.conteudo_removido: dict | None = None
        self._pid = os.getpid()

    # ------------------------------------------------------------ aquisição
    def _criar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": self._pid, "inicio": _agora().isoformat()}, f)

    def _ler(self) -> dict | None:
        try:
            with open(self.caminho, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def esquecida(self, conteudo: dict | None) -> bool:
        """O lock existente pode ser removido?"""
        if conteudo is None:
            # Ilegível: pode estar sendo escrito agora. Só é esquecido se for antigo.
            try:
                mtime = dt.datetime.fromtimestamp(self.caminho.stat().st_mtime, dt.timezone.utc)
            except OSError:
                return True
            return _agora() - mtime > _TOLERANCIA_ESCRITA
        try:
            inicio = dt.datetime.fromisoformat(conteudo["inicio"])
            pid = int(conteudo["pid"])
        except (KeyError, TypeError, ValueError):
            return True
        if _agora() - inicio > self.idade_maxima:
            return True
        if not psutil.pid_exists(pid):
            return True
        try:
            criado = dt.datetime.fromtimestamp(psutil.Process(pid).create_time(), dt.timezone.utc)
        except psutil.Error:
            return True
        # PID reaproveitado: o processo atual nasceu depois do lock.
        return criado > inicio + dt.timedelta(seconds=1)

    def adquirir(self) -> "Trava":
        try:
            self._criar()
            return self
        except FileExistsError:
            pass
        conteudo = self._ler()
        if not self.esquecida(conteudo):
            raise TravaOcupada(self.caminho, conteudo)
        self.caminho.unlink(missing_ok=True)
        self.esquecida_removida = True
        self.conteudo_removido = conteudo
        try:
            self._criar()
        except FileExistsError:
            raise TravaOcupada(self.caminho, self._ler()) from None
        return self

    def liberar(self) -> None:
        conteudo = self._ler()
        if conteudo is not None and conteudo.get("pid") != self._pid:
            return  # não é nosso; não remover
        self.caminho.unlink(missing_ok=True)

    def __enter__(self) -> "Trava":
        return self.adquirir()

    def __exit__(self, *exc) -> None:
        self.liberar()
