"""La pagination du cahier §18.2 — une seule declaration pour tout le projet.

**POURQUOI ELLE VIT ICI ET NON DANS UN MODULE METIER**, et le motif est un import
CIRCULAIRE mesure le 14/09/2026, a l'ouverture de `T3` du LOT 6.

  Ces trois tailles ont ete declarees en `T2` du LOT 5, dans
  `app/people/trombinoscope.py`, parce que le trombinoscope etait la seule liste
  paginee du projet. `T3` du LOT 6 en ajoute une seconde -- les membres d'un
  cercle -- et le §18.2 s'applique a elle aussi : il s'intitule « Pagination »,
  vit dans le chapitre **API** du cahier, et ne nomme aucune ressource.

  **Mais `app/organization` ne peut pas importer `app/people`** : `people`
  importe DEJA `app.organization.modeles` -- `TypeAppartenanceCercle`, dans
  `trombinoscope.py` et dans `ecriture.py`. L'import inverse fermerait le cycle,
  et `app/organization/__init__.py` serait lu a moitie.

  **Les deux issues etaient de dupliquer ou de deplacer.** Dupliquer donnerait
  deux declarations d'une meme regle du cahier, dont la premiere sous-etape qui
  en changerait une oublierait l'autre -- §7.27, et pire qu'une liste recopiee
  puisqu'il s'agit d'un TYPE. Deplacer est ce que ce projet a deja fait pour
  `ETAT_LISTE` et `VISIBILITE_LISTEE`, qu'un import circulaire entre le
  trombinoscope et `media/photo.py` avait designees comme n'appartenant a aucun
  des deux.

  **Un fait du CAHIER se declare donc dans `shared`, pas dans le premier module
  qui en a eu besoin.**
"""

from __future__ import annotations

import enum
from typing import Final


#  Cahier §18.2, a la lettre : « options 25, 50 et 100 ; maximum 100 ».
#
#  **LE TYPE EST LA SOURCE, ET LE TUPLE EN EST DERIVE.** La route a besoin d'un
#  type qui fasse produire a FastAPI un 422 nommant les valeurs admises et qui
#  les documente dans OpenAPI ; le service a besoin d'un tuple pour verifier.
#  Ecrire les deux cote a cote donnerait DEUX listes a maintenir, et la premiere
#  sous-etape qui en changerait une oublierait l'autre (§7.27).
#
#  **ET CE TYPE EST UN `IntEnum`, PAS UN `Literal` — LE DEFAUT `T2-3` L'A PROUVE.**
#  Un parametre d'URL arrive TOUJOURS en chaine. Mesure du 25/08/2026 :
#
#      TypeAdapter(Literal[25, 50, 100]).validate_python("25")  ->  REFUSE
#      TypeAdapter(IntEnum(...)).validate_python("25")          ->  25
#
#  Avec un `Literal`, la route refusait donc **les trois tailles valides** des
#  qu'elles etaient ecrites dans l'URL, et n'acceptait plus que le defaut
#  implicite. **Mes huit tests de refus passaient tous** : ils demandaient un
#  refus, et ils l'obtenaient -- pour la mauvaise raison. Seul le TEMOIN, celui
#  qui exige que 25, 50 et 100 SOIENT servies, discrimine les deux situations.
#  C'est la troisieme proposition du §7.0 : un controle dont l'echec produit la
#  meme observation que le succes ne prouve rien.
#
#  La borne de 100 est le `max` du tuple, jamais une troisieme constante.
class TailleDePage(enum.IntEnum):
    """Les trois tailles de page du cahier §18.2, et elles seules."""

    VINGT_CINQ = 25
    CINQUANTE = 50
    CENT = 100


TAILLES_DE_PAGE: Final[tuple[int, ...]] = tuple(membre.value for membre in TailleDePage)
TAILLE_PAR_DEFAUT: Final[TailleDePage] = TailleDePage.VINGT_CINQ
TAILLE_MAXIMALE: Final[int] = max(TAILLES_DE_PAGE)
