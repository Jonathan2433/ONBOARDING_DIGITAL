"""Identifiant de correlation — reexport du paquet partage.

LOT 1, sous-etape T4, story MVP-L01-US004.

L'implementation vivait ici a `T3`. Elle a demenage dans
`packages/observabilite` en `T4`, parce que le critere de la sous-etape exige
que « chaque requete ET chaque job » portent un identifiant : le worker en a
besoin autant que l'API, et deux implementations auraient fini par diverger.

Ce module ne fait plus que reexporter, pour que les imports existants de l'API
restent valides. Il ne contient AUCUNE logique : la source unique est
`observabilite.correlation`.
"""

from __future__ import annotations

from observabilite.correlation import (
    EN_TETE_CORRELATION,
    correlation_courante,
    definir_correlation,
    effacer_correlation,
    engendrer,
)

__all__ = [
    "EN_TETE_CORRELATION",
    "correlation_courante",
    "definir_correlation",
    "effacer_correlation",
    "engendrer",
]
