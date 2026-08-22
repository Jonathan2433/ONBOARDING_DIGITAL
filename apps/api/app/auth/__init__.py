"""Authentification, sessions et securite applicative.

LOT 3 — `T2` a pose les sept tables du modele §10, `T3` la demande de magic link.
"""

from app.auth.jetons import (
    MOTIF_JETON_MAGIC_LINK,
    PREFIXE_MAGIC_LINK,
    empreinte_d_origine,
    empreinte_de_jeton,
    engendrer_jeton_magic_link,
    ressemble_a_un_jeton_magic_link,
)
from app.auth.modeles import (
    ETATS_COMPTE,
    ETATS_COMPTE_DE_SERVICE,
    JOURS_D_INACTIVITE_DE_SESSION,
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
    "JOURS_D_INACTIVITE_DE_SESSION",
    "JOURS_MAXIMUM_DE_SESSION",
    "LONGUEUR_EMPREINTE_SHA256",
    "MINUTES_DE_VALIDITE_DU_MAGIC_LINK",
    "MOTIF_JETON_MAGIC_LINK",
    "PREFIXE_MAGIC_LINK",
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
    "empreinte_d_origine",
    "empreinte_de_jeton",
    "engendrer_jeton_magic_link",
    "ressemble_a_un_jeton_magic_link",
]
