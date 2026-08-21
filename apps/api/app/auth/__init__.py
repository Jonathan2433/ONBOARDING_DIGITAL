"""Authentification, sessions et securite applicative.

LOT 3, sous-etape `T2`, modele de donnees §10.
"""

from app.auth.modeles import (
    ETATS_COMPTE,
    ETATS_COMPTE_DE_SERVICE,
    JOURS_MAXIMUM_DE_SESSION,
    LONGUEUR_EMPREINTE_SHA256,
    MINUTES_DE_VALIDITE_DU_MAGIC_LINK,
    TYPES_COMPTE,
    TYPES_EVENEMENT_AUTH,
    AdminPasswordCredential,
    AuthEvent,
    EtatCompte,
    EtatCompteDeService,
    MagicLinkRequest,
    ServiceAccount,
    ServiceToken,
    TypeCompte,
    TypeEvenementAuth,
    UserAccount,
    UserSession,
)

__all__ = [
    "ETATS_COMPTE",
    "ETATS_COMPTE_DE_SERVICE",
    "JOURS_MAXIMUM_DE_SESSION",
    "LONGUEUR_EMPREINTE_SHA256",
    "MINUTES_DE_VALIDITE_DU_MAGIC_LINK",
    "TYPES_COMPTE",
    "TYPES_EVENEMENT_AUTH",
    "AdminPasswordCredential",
    "AuthEvent",
    "EtatCompte",
    "EtatCompteDeService",
    "MagicLinkRequest",
    "ServiceAccount",
    "ServiceToken",
    "TypeCompte",
    "TypeEvenementAuth",
    "UserAccount",
    "UserSession",
]
