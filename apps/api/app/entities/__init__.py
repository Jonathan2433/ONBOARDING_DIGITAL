"""Entites, parametres de plateforme et locaux, domaines e-mail autorises.

LOT 2, sous-etape `T2`, story `MVP-L02-US001`.
"""

from app.entities.modeles import (
    STATUTS_ENTITE,
    AllowedEmailDomain,
    Entity,
    EntitySetting,
    PlatformSetting,
    StatutEntite,
)

__all__ = [
    "STATUTS_ENTITE",
    "AllowedEmailDomain",
    "Entity",
    "EntitySetting",
    "PlatformSetting",
    "StatutEntite",
]
