"""Recherche normalisee du trombinoscope — LOT 5, sous-etape `T3`.

Story `MVP-L05-US002`. Modele §26.1 : « normalisation et index de recherche sur
prenom et nom ».

POURQUOI UNE FONCTION, ET POURQUOI ELLE DOIT ETRE `IMMUTABLE`

  La normalisation doit s'appliquer **des deux cotes** -- a la colonne et au terme
  cherche -- sinon ils ne se rencontrent pas. Une seule fonction SQL le garantit ;
  deux normalisations, l'une en Python et l'autre en SQL, divergeraient au premier
  caractere oublie et la recherche rendrait silencieusement moins de resultats.

  Et **PostgreSQL n'indexe une expression que si elle est `IMMUTABLE`** : elle doit
  rendre toujours la meme valeur pour la meme entree, sans quoi l'index pourrait
  designer des lignes qui ne correspondent plus.

POURQUOI `translate` ET NON L'EXTENSION `unaccent`

  `unaccent()` est declaree **`STABLE`**, pas `IMMUTABLE` : son resultat depend
  d'un dictionnaire que l'administrateur peut remplacer. L'usage repandu consiste
  a l'envelopper dans une fonction que l'on declare `IMMUTABLE` **en le sachant
  faux** -- et un index construit sur un mensonge se corrompt le jour ou le
  dictionnaire change.

  `translate()` est **reellement** `IMMUTABLE` : sa table de correspondance est
  ecrite ici, dans la migration, et ne peut pas changer sous l'index. Elle
  n'exige en outre **aucune extension**, ce qui evite de rouvrir `QO-112`.

  Le prix est nomme : la table est une **liste**, donc elle vieillit si une lettre
  manque. Elle est **eprouvee caractere par caractere** par un test, et le §26.1
  autorise explicitement « une colonne de recherche denormalisee ou un index
  PostgreSQL adapte ».

`translate` NE SAIT PAS DEPLIER UNE LIGATURE, ET C'EST POURQUOI IL Y A UN `replace`

  `translate` fait une correspondance **caractere a caractere**. « oe » fait deux
  caracteres pour un : `œ` doit donc passer par `replace`, avant le `translate`.
  Les quatre ligatures du francais sont traitees ainsi.

L'INDEX N'EST PAS EXIGE PAR LE CRITERE, IL EST EXIGE PAR LE §26.1

  Le critere de sortie est une **duree** -- « recherche sous 800 ms au P95 »,
  cahier §25.2. Sur 5 000 lignes un parcours sequentiel la tient largement, et un
  test qui exigerait l'usage de l'index exigerait le contraire de la performance
  (lecon de `T12` du LOT 2, §7.20).

  L'index est pose parce que le §26.1 le **recommande** et parce que le §25.1
  annonce « augmentation possible sans refonte » : il sert le jour ou le volume
  depasse ce que la recette mesure. Sa presence est verifiee ; son **usage** ne
  l'est pas.

Revision ID: 0015
Revises: 0014
"""

from __future__ import annotations

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | None = None
depends_on: str | None = None


#  Les lettres accentuees du francais et de ses emprunts courants, en une seule
#  source. Ordre : la source, puis la cible, caractere par caractere.
#
#  **LE MAJUSCULE EST TRAITE AUSSI**, bien que `lower()` s'applique ensuite : la
#  fonction reste ainsi juste quel que soit l'ordre des deux operations, et un
#  lecteur n'a pas a deduire que l'un protege l'autre.
_ACCENTS = "àáâãäåÀÁÂÃÄÅèéêëÈÉÊËìíîïÌÍÎÏòóôõöÒÓÔÕÖùúûüÙÚÛÜçÇñÑÿýŸÝ"
_SANS = "aaaaaaAAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcCnNyyYY"


def upgrade() -> None:
    """Poser la fonction de normalisation et l'index de recherche."""
    #  La cible du `translate` doit avoir EXACTEMENT la longueur de la source :
    #  un caractere de trop ou de moins decalerait TOUTE la correspondance, en
    #  silence. La verification est ici, au moment ou la migration s'applique.
    if len(_ACCENTS) != len(_SANS):
        message = (
            f"table de correspondance desequilibree : {len(_ACCENTS)} accents "
            f"pour {len(_SANS)} remplacements — le decalage serait silencieux"
        )
        raise RuntimeError(message)

    op.execute(f"""
        CREATE FUNCTION fn_normaliser_pour_recherche(valeur text) RETURNS text
        LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
            SELECT lower(
                translate(
                    replace(replace(replace(replace(
                        valeur, 'œ', 'oe'), 'Œ', 'OE'), 'æ', 'ae'), 'Æ', 'AE'),
                    '{_ACCENTS}',
                    '{_SANS}'
                )
            );
        $$;
    """)

    op.execute("""
        COMMENT ON FUNCTION fn_normaliser_pour_recherche(text) IS
        'Modele §26.1 : normalisation de recherche sur prenom et nom. IMMUTABLE '
        'par construction — la table de correspondance est ecrite dans la '
        'migration 0015, contrairement a unaccent() qui est STABLE.';
    """)

    #  L'expression indexee est EXACTEMENT celle que le service emploie. Si les
    #  deux divergeaient, l'index existerait sans jamais servir -- un livrable
    #  qui parait bon et ne fait rien.
    op.execute("""
        CREATE INDEX ix_person_recherche_nom
        ON person (fn_normaliser_pour_recherche(first_name || ' ' || last_name));
    """)


def downgrade() -> None:
    """Retirer l'index puis la fonction — l'index en depend."""
    op.execute("DROP INDEX IF EXISTS ix_person_recherche_nom")
    op.execute("DROP FUNCTION IF EXISTS fn_normaliser_pour_recherche(text)")
