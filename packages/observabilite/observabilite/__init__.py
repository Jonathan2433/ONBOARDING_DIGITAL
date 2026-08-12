"""Journalisation JSON et masquage des secrets, partages par l'API et le worker.

LOT 1, sous-etape T4, story MVP-L01-US004.

Cahier des charges §28.1 pour le format, §28.2 pour la confidentialite,
§28.3 pour la rotation.
"""

from observabilite.correlation import (
    CLE_CORRELATION_MESSAGE,
    EN_TETE_CORRELATION,
    correlation_courante,
    definir_correlation,
    effacer_correlation,
    engendrer,
)
from observabilite.journalisation import (
    CHAMPS_DU_CAHIER,
    FormateurJson,
    configurer_journalisation,
)
from observabilite.masquage import MASQUE, cle_est_sensible, masquer

__all__ = [
    "CHAMPS_DU_CAHIER",
    "CLE_CORRELATION_MESSAGE",
    "EN_TETE_CORRELATION",
    "MASQUE",
    "FormateurJson",
    "cle_est_sensible",
    "configurer_journalisation",
    "correlation_courante",
    "definir_correlation",
    "effacer_correlation",
    "engendrer",
    "masquer",
]

__version__ = "0.1.0"
