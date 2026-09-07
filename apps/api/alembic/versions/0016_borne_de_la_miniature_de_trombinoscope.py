"""Borne de la miniature de trombinoscope — LOT 5, sous-etape `T5`.

Story `MVP-L05-US005`. Cahier §25.3 : « miniature de trombinoscope **inferieure
a 100 Ko** ».

POURQUOI EN BASE, ET NON DANS LE SERVICE

  **Ce n'est PAS le LOT 5 qui fabrique les miniatures.** Le cahier place la
  generation en `MVP-L11-US005` -- « Generer miniatures et variantes sans
  doublon » -- et aucune bibliotheque de traitement d'image n'est installee :
  mesure du 06/09/2026, zero occurrence de `pillow` ou `vips`.

  Une borne posee dans le service du LOT 5 ne contraindrait donc **rien** : le
  producteur arrivera au LOT 11, et il n'appellera pas ce service. Posee en base,
  elle attend le producteur et le refuse s'il deborde -- c'est le §7.32, « n'ecris
  pas de defense contre un etat que la base peut interdire ».

  Le critere de sortie du LOT 5 « les miniatures sont inferieures a la cible de
  100 Ko » devient ainsi verifiable **avant** qu'une seule miniature n'existe.

CENT KILO-OCTETS FONT CENT MILLE OCTETS, ET C'EST LA LECTURE STRICTE

  Le cahier ecrit « Ko », kilo-octet, qui vaut **1 000** octets dans le systeme
  international -- le multiple binaire s'ecrit « Kio ». La borne est donc
  **100 000** octets et non 102 400.

  Les deux lectures se defendent dans l'usage courant ; celle-ci est la **plus
  stricte** des deux, ce qui la rend sure : une miniature qui la respecte
  respecte aussi l'autre. L'inverse serait faux, et un budget qu'on relache sans
  le dire n'est plus un budget.

  **ELLE NE PORTE QUE SUR `thumbnail`.** Les quatre autres variantes du §16.2 --
  carte, pleine largeur, apercu video, format optimise -- n'ont **aucune** borne
  ecrite dans le corpus, et en inventer une serait le §6.5. Le §25.3 ne parle
  que de la miniature de trombinoscope.

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | None = None
depends_on: str | None = None

#  Cahier §25.3, en octets. Ecrit ici une seule fois : le service et les tests le
#  lisent depuis le modele, jamais en litteral (§7.27).
BORNE_MINIATURE_OCTETS = 100_000

CONTRAINTE = "ck_media_variant_miniature_sous_cent_ko"


def upgrade() -> None:
    """Refuser une miniature de trombinoscope de 100 000 octets ou plus."""
    #  La forme « type <> 'thumbnail' OR taille < borne » et non une contrainte
    #  partielle : un `CHECK` ne se restreint pas par `WHERE`, et l'implication
    #  dit exactement la regle -- les autres variantes ne sont pas contraintes.
    op.execute(f"""
        ALTER TABLE media_variant ADD CONSTRAINT {CONTRAINTE}
        CHECK (variant_type <> 'thumbnail' OR size_bytes < {BORNE_MINIATURE_OCTETS});
    """)
    op.execute(f"""
        COMMENT ON CONSTRAINT {CONTRAINTE} ON media_variant IS
        'Cahier §25.3 : miniature de trombinoscope inferieure a 100 Ko, soit '
        '{BORNE_MINIATURE_OCTETS} octets (Ko = 1000, lecture stricte). La '
        'generation appartient au LOT 11 : cette borne l''attend.';
    """)


def downgrade() -> None:
    """Retirer la borne."""
    op.execute(f"ALTER TABLE media_variant DROP CONSTRAINT IF EXISTS {CONTRAINTE}")
