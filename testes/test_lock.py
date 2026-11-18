import datetime as dt
import json
import os
import subprocess
import sys

import psutil
import pytest

from tcc_pipeline.lock import Trava, TravaOcupada


def _escrever(caminho, pid, inicio):
    caminho.write_text(json.dumps({"pid": pid, "inicio": inicio.isoformat()}), encoding="utf-8")


def _agora():
    return dt.datetime.now(dt.timezone.utc)


def test_adquire_e_remove_no_fim(tmp_path):
    lock = tmp_path / ".lock"
    with Trava(lock):
        dados = json.loads(lock.read_text(encoding="utf-8"))
        assert dados["pid"] == os.getpid()
    assert not lock.exists()


def test_remove_mesmo_com_falha(tmp_path):
    lock = tmp_path / ".lock"
    with pytest.raises(RuntimeError):
        with Trava(lock):
            raise RuntimeError("falha no meio da execução")
    assert not lock.exists()


def _pai_vivo():
    """PID de um processo vivo, criado antes do lock que o teste vai escrever."""
    return os.getppid() if os.getppid() else os.getpid()


def test_lock_valido_bloqueia(tmp_path):
    lock = tmp_path / ".lock"
    _escrever(lock, _pai_vivo(), _agora())
    with pytest.raises(TravaOcupada):
        Trava(lock).adquirir()
    assert lock.exists()


def test_pid_morto_e_esquecido(tmp_path):
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    lock = tmp_path / ".lock"
    _escrever(lock, proc.pid, _agora() - dt.timedelta(seconds=5))
    with Trava(lock) as t:
        assert t.esquecida_removida
        assert t.conteudo_removido["pid"] == proc.pid
    assert not lock.exists()


def test_lock_com_mais_de_2_horas_e_esquecido(tmp_path):
    lock = tmp_path / ".lock"
    _escrever(lock, _pai_vivo(), _agora() - dt.timedelta(hours=3))
    with Trava(lock) as t:
        assert t.esquecida_removida


def test_pid_reaproveitado_e_esquecido(tmp_path):
    # O processo do PID existe, mas nasceu depois do horário gravado no lock.
    lock = tmp_path / ".lock"
    _escrever(lock, os.getpid(), _agora() - dt.timedelta(minutes=90))
    criado = dt.datetime.fromtimestamp(psutil.Process().create_time(), dt.timezone.utc)
    if criado < _agora() - dt.timedelta(minutes=90):
        pytest.skip("processo de teste mais antigo que o lock simulado")
    with Trava(lock) as t:
        assert t.esquecida_removida
