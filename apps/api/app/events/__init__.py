"""Evenements — modele de donnees §17.

LOT 8. `T1` pose quatre tables locales ; `T2` ajoute leur lecture paginee.
"""

from app.events.lecture import ClassementEvenement, EvenementLu, PageDEvenements
from app.events.modeles import (
    ETATS_EVENEMENT,
    EtatEvenement,
    Event,
    EventCircleScope,
    EventMedia,
    EventOfficeScope,
)

__all__ = [
    "ETATS_EVENEMENT",
    "ClassementEvenement",
    "EtatEvenement",
    "EvenementLu",
    "Event",
    "EventCircleScope",
    "EventMedia",
    "EventOfficeScope",
    "PageDEvenements",
]
