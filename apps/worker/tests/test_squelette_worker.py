"""Amorcage du worker Dramatiq.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §16.4 : sept files nommees `default`, `emails`,
`imports`, `media`, `exports`, `maintenance`, `security`.

Ces tests n'exigent aucun Redis : ils portent sur la DECLARATION des files et
sur la lecture de la configuration, pas sur l'echange de messages. La
persistance des jobs, l'outbox et l'idempotence relevent du LOT 11.
"""

from __future__ import annotations

import pytest

from worker import __version__
from worker.main import FILES_PAR_DEFAUT, files_declarees, url_redis

# Les sept files, reprises litteralement du cahier §16.4.
SEPT_FILES_DU_CAHIER = (
    "default",
    "emails",
    "imports",
    "media",
    "exports",
    "maintenance",
    "security",
)


def test_le_paquet_worker_est_importable_et_versionne() -> None:
    assert __version__ == "0.1.0"


def test_les_sept_files_du_cahier_sont_declarees_par_defaut() -> None:
    """Une file oubliee ferait disparaitre des messages en silence."""
    assert FILES_PAR_DEFAUT == SEPT_FILES_DU_CAHIER
    assert len(FILES_PAR_DEFAUT) == 7


def test_la_liste_de_files_est_lue_dans_l_environnement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`DRAMATIQ_QUEUES` de `.env.example` fait foi quand elle est renseignee."""
    monkeypatch.setenv("DRAMATIQ_QUEUES", "default, emails ,media")
    assert files_declarees() == ("default", "emails", "media")


def test_une_liste_vide_retombe_sur_les_sept_files_du_cahier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Temoin negatif : une variable vide ne doit pas donner zero file.

    Un worker sans file demarrerait, serait declare sain, et ne traiterait
    jamais rien — la panne la plus difficile a diagnostiquer.
    """
    monkeypatch.setenv("DRAMATIQ_QUEUES", "   ")
    assert files_declarees() == SEPT_FILES_DU_CAHIER


def test_l_url_du_courtier_est_construite_depuis_l_environnement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDIS_HOST", "redis-de-test")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_PASSWORD", "valeur-de-test")
    assert url_redis() == "redis://:valeur-de-test@redis-de-test:6380/0"


def test_aucun_acteur_metier_n_est_declare() -> None:
    """Garde-fou de perimetre du LOT 1.

    Il n'existe aucun metier avant le LOT 2 : declarer un acteur ici serait une
    anticipation a refuser. Si ce test echoue, c'est que du code metier a ete
    ajoute trop tot.
    """
    import worker.main as module

    acteurs = [
        nom
        for nom, objet in vars(module).items()
        if hasattr(objet, "send") and hasattr(objet, "fn")
    ]
    assert acteurs == []
