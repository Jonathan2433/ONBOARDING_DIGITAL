"""Contenus editoriaux et liens internes — modele de donnees §15.

LOT 6, sous-etape `T1`. Trois tables, et aucune des trois n'existait : mesure du
13/09/2026 sur le schema reel, 29 tables `alembic_version` comprise.
"""

from app.content.modeles import (
    ETATS_DE_PAGE,
    TYPES_DE_BLOC,
    TYPES_DE_LIEN,
    TYPES_DE_PAGE,
    ContentBlock,
    ContentPage,
    EtatDePage,
    InternalLink,
    TypeDeBloc,
    TypeDeLien,
    TypeDePage,
)

__all__ = [
    "ETATS_DE_PAGE",
    "TYPES_DE_BLOC",
    "TYPES_DE_LIEN",
    "TYPES_DE_PAGE",
    "ContentBlock",
    "ContentPage",
    "EtatDePage",
    "InternalLink",
    "TypeDeBloc",
    "TypeDeLien",
    "TypeDePage",
]
