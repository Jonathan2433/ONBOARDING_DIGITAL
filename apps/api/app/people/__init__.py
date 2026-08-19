"""Personnes et appartenance aux entites.

LOT 2, sous-etapes `T3` et `T4`, story `MVP-L02-US002`.
"""

from app.people.modeles import (
    CATEGORIES_PROFESSIONNELLES,
    ETATS_APPARTENANCE,
    ETATS_COMPTE,
    ETATS_OCCUPANTS,
    VISIBILITES_PROFIL,
    CategorieProfessionnelle,
    EntityMembership,
    EtatAppartenance,
    EtatCompte,
    Person,
    VisibiliteProfil,
    normaliser_email,
)

__all__ = [
    "CATEGORIES_PROFESSIONNELLES",
    "ETATS_APPARTENANCE",
    "ETATS_COMPTE",
    "ETATS_OCCUPANTS",
    "VISIBILITES_PROFIL",
    "CategorieProfessionnelle",
    "EntityMembership",
    "EtatAppartenance",
    "EtatCompte",
    "Person",
    "VisibiliteProfil",
    "normaliser_email",
]
