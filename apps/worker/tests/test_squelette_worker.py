"""Controle minimal du squelette du worker.

Meme role que son equivalent cote API : garantir que la chaine de tests
s'execute reellement, et non qu'elle passe faute d'avoir quoi que ce soit a
collecter.
"""

from worker import __version__


def test_le_paquet_worker_est_importable_et_versionne() -> None:
    assert __version__ == "0.1.0"
