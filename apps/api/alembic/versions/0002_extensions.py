"""Extensions PostgreSQL strictement necessaires.

LOT 2, sous-etape `T1`, story `MVP-L02-US008`.
Revision : 0002
Revision precedente : 0001

FONDEMENT — modele de donnees §28, point 1 : « extensions PostgreSQL
strictement necessaires ». Le mot qui commande est **strictement**.

QUESTION `QO-112`, CLOSE PAR CETTE MIGRATION. Aucun document du corpus ne
nommait une seule extension. La liste ci-dessous est donc DERIVEE d'un besoin
technique nomme, jamais d'un « on pourrait en avoir besoin » : une extension
posee par precaution est de la surface d'attaque et du code tiers que nous
n'auditons pas.

CE QUI EST INSTALLE, ET POURQUOI — UNE SEULE

  `btree_gist`  Une contrainte d'exclusion sur `(uuid WITH =, tstzrange WITH
                &&)` melange deux familles d'operateurs. GiST sait indexer les
                plages ; il ne sait pas indexer l'egalite d'un `uuid` sans cette
                extension. Elle est donc la condition technique du §25.2, dont
                Jonathan a arbitre le 18/08/2026 que les regles
                anti-chevauchement seraient portees par la BASE et pas seulement
                par le service.

CE QUI N'EST PAS INSTALLE, ET POURQUOI — LE PLUS INSTRUCTIF

  `pgcrypto`    Serait la pour `gen_random_uuid()`. MESURE du 18/08/2026 sur le
                serveur de ce projet : cette fonction est rattachee a « le
                NOYAU » et non a une extension -- PostgreSQL la fournit en
                interne depuis la version 13. L'installer n'apporterait rien.
  `uuid-ossp`   Meme motif, en plus ancien.
  `citext`      Le modele §6.1 prevoit une colonne `email_normalized` : la
                normalisation est APPLICATIVE et deja decidee. Un type
                insensible a la casse ferait un second mecanisme pour le meme
                besoin.
  `unaccent`    Necessaires a la « recherche tolerante » du §26.1, qui appartient
  `pg_trgm`     au LOT 5, avec le trombinoscope. Les installer ici serait
                anticiper un lot non ouvert.

Toutes ces extensions sont DISPONIBLES dans l'image -- mesure : 45 extensions
disponibles, dont les six ci-dessus. Ne pas les installer est un choix, pas une
impossibilite.

RETOUR ARRIERE. `DROP EXTENSION` sans `CASCADE` : si une contrainte d'exclusion
depend encore de `btree_gist`, la descente ECHOUE bruyamment au lieu de
supprimer silencieusement les contraintes qui protegent les donnees. Une
migration qui defait plus que ce qu'elle a fait est pire qu'une migration qui
refuse de descendre.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXTENSIONS: tuple[str, ...] = ("btree_gist",)


def upgrade() -> None:
    """Installer les extensions strictement necessaires."""
    for extension in EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')


def downgrade() -> None:
    """Retirer les extensions. Sans CASCADE : voir l'explication en tete de fichier."""
    for extension in reversed(EXTENSIONS):
        op.execute(f'DROP EXTENSION IF EXISTS "{extension}"')
