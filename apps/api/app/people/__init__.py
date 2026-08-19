"""Personnes et appartenance aux entites.

LOT 2, sous-etape `T3`, story `MVP-L02-US002`.
"""

from app.people.modeles import ETATS_COMPTE, EtatCompte, Person, normaliser_email

__all__ = ["ETATS_COMPTE", "EtatCompte", "Person", "normaliser_email"]
