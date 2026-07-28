"""Controle minimal du squelette de l'API.

Ce test n'a qu'un objet : garantir que la chaine de tests s'execute reellement.
Sans lui, ``pytest`` ne collecterait aucun test et sortirait en erreur ou en
faux vert selon la configuration - exactement le type de controle qui ne peut
pas echouer, et qui ne prouve donc rien.

Les tests reels de configuration, de sante et de migration arrivent en T3.
"""

from app import __version__


def test_le_paquet_api_est_importable_et_versionne() -> None:
    assert __version__ == "0.1.0"
