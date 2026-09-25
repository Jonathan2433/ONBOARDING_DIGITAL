"""La liste de protocoles du §15.3 devient STRUCTURELLE — LOT 6, `T8`.

Story `MVP-L06-US005`, decision `DEC-587`, question `QO-120` **close**.

CE QUE CETTE MIGRATION POSE, ET POURQUOI `T1` AVAIT RAISON DE NE PAS LA POSER

  Le modele §15.3 et le cahier §13 ecrivent tous deux « les URL sont validees
  selon une **liste de protocoles autorises** », et **aucun des deux ne la
  donne** -- zero occurrence, mesuree le 13/09/2026 puis le 22/09/2026. `T1` a
  donc borne la FORME -- `length(btrim(url)) > 0` -- et refuse le protocole, en
  ecrivant : « inventer la liste ici la figerait dans le schema ».

  **CE QUI A CHANGE N'EST PAS L'ARGUMENT, C'EST QUE LA LISTE N'EST PLUS UNE
  INVENTION.** `DEC-587` la tranche -- `https` seul -- et la figer coute
  desormais exactement ce que coute le `contrainte_enumeration` de `page_type` :
  une migration d'une ligne. C'est precisement le motif pour lequel ce depot
  prefere une contrainte de verification a un type `enum` natif.

POURQUOI UNE CONTRAINTE ALORS QUE LE SERVICE VALIDE DEJA

  **Parce qu'un service est un APPEL, et qu'une contrainte est une PROPRIETE.**
  §7.35 : quand une garantie ne tient qu'a ce qu'on n'oublie pas un appel, elle
  se perd en silence ; quand elle est structurelle, la perdre exige de casser le
  code. Trois ecrivains futurs sont deja nommes au corpus et n'appellent pas
  `app.content.liens` :

    - la reprise relue des textes et liens du prototype -- `MVP-L06-US007`,
      sous-etape `T11` de ce lot ;
    - le modele generique local -- §19, « modifier les modeles generiques
      locaux » ;
    - les imports du LOT 9, et le jeu de donnees engendre du LOT 2.

  **Aucun d'eux ne peut plus ecrire `javascript:` dans `internal_link`.** C'est
  ce que la contrainte apporte, et le service ne peut pas l'apporter.

CE QU'ELLE NE FAIT PAS, ET IL FAUT LE DIRE

  `LIKE 'https://%'` **ne sait pas exiger un hote**. Mesure du 22/09/2026 :
  `https:alert(1)` passe une liste blanche de protocoles, mais pas ce motif --
  il n'a pas les deux barres obliques. En revanche `https:///chemin` le passerait
  alors qu'il ne designe aucun serveur.

  C'est `valider_une_url` qui exige l'hote, et `url_sans_hote` qui le nomme. Les
  deux etages ne sont donc pas redondants : la contrainte est le PLANCHER que nul
  ne contourne, le service est le REFUS EXACT, plus fin et mieux libelle. Un test
  exige que les deux concordent -- sans quoi le service accepterait ce que la
  base refuse, en 500 au lieu de 422.

  **LA CASSE EST STRICTE, ET C'EST DELIBERE.** `HTTPS://x` est refuse par cette
  contrainte. Le service minuscule le segment de protocole avant d'ecrire --
  `urlsplit` le rend deja minuscule, mesure du 22/09/2026 -- si bien qu'aucune
  ecriture par l'API ne peut la heurter. Un `lower(url) LIKE ...` aurait accepte
  des adresses de casse melangee en base, donc deux ecritures d'une meme adresse
  qui ne se ressembleraient pas.

Revision ID: 0019
Revises: 0018
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#  **LE MOTIF EST ECRIT UNE FOIS.** Le module `app.content.liens` porte la meme
#  liste sous `PROTOCOLES_AUTORISES`, et un test confronte les deux : deux copies
#  d'une meme regle divergent au premier changement (`DEC-466`, `ECART-022`).
#  **LE NOM COMPLET, ET IL EST ECRIT TEL QUEL.** La convention de nommage de
#  `app.shared.modele` prefixe toute verification par `ck_<table>_` ; dans une
#  migration, `op.f()` dit a Alembic que le nom est DEJA final et qu'il ne doit
#  pas le prefixer une seconde fois. C'est l'idiome de la migration `0003`.
NOM = "ck_internal_link_url_https"
MOTIF = "https://%"


def upgrade() -> None:
    op.create_check_constraint(op.f(NOM), "internal_link", f"url LIKE '{MOTIF}'")


def downgrade() -> None:
    op.drop_constraint(op.f(NOM), "internal_link", type_="check")
