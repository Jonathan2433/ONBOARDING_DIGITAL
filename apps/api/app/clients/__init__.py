"""Clients globaux, activations locales et alias.

LOT 2, sous-etape `T6`, story `MVP-L02-US003`.
"""

from app.clients.modeles import (
    STATUTS_CLIENT,
    Client,
    ClientAlias,
    EntityClient,
    StatutClient,
    normaliser_nom_client,
)

__all__ = [
    "STATUTS_CLIENT",
    "Client",
    "ClientAlias",
    "EntityClient",
    "StatutClient",
    "normaliser_nom_client",
]
