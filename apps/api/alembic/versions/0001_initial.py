"""Migration initiale — volontairement vide.

Revision : 0001
Precedente : aucune

LOT 1, sous-etape T3, story MVP-L01-US003.

POURQUOI CETTE MIGRATION NE FAIT RIEN

La roadmap du LOT 1 demande littéralement qu'« une migration Alembic **vide ou
initiale** s'execute ». Le modele de donnees §28 place en premiere etape les
« extensions PostgreSQL strictement necessaires ».

Or **aucun document du corpus ne nomme une seule extension**. Verifie le
28/07/2026 : zero occurrence de `pg_trgm`, `unaccent`, `citext`, `pgcrypto` ou
`uuid-ossp` dans le cahier des charges comme dans le modele de donnees, avec
temoin positif du meme filtre — `SQLAlchemy` y remonte quatre fois.

Deux constats acheves de trancher la question :

  - le modele §3 impose des cles primaires UUID, mais `gen_random_uuid()` est
    integre a PostgreSQL depuis la version 13 : aucune extension n'est requise
    pour cela ;
  - le modele §26.1 indique que la recherche tolerante « pourra » utiliser une
    colonne denormalisee OU un index adapte. C'est explicitement ouvert, et ces
    index arrivent a la migration 16 de l'ordre recommande, pas a la premiere.

Choisir une liste ici aurait ete inventer une decision, et une extension
activee est plus penible a retirer qu'a ajouter. Arbitrage de Jonathan du
28/07/2026, `DEC-463` : la liste sera etablie au LOT 2, avec les tables et les
index de recherche. Question ouverte `QO-112`.

CE QUE CETTE MIGRATION PROUVE MALGRE TOUT

Elle prouve ce que le LOT 1 doit prouver : la chaine de migration fonctionne.
Elle s'applique sur une base vide, inscrit sa revision, se rejoue sans effet de
bord, et s'annule proprement. Aucune table metier n'est creee — ce serait une
anticipation du LOT 2, a refuser.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aucune operation. Voir l'explication en tete de fichier."""


def downgrade() -> None:
    """Aucune operation : il n'y a rien a defaire."""
