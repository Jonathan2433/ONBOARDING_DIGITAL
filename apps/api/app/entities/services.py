"""Lister les entites du portail national — story `MVP-L04-US001`.

LOT 4, sous-etape `T1`.

« ACTIVE » N'EST PAS UNE INTERPRETATION DU BACKLOG : C'EST LE CAHIER

  Le backlog `US001` dit « seules les entites actives sont proposees ». On
  pourrait le lire comme un raccourci de redaction ; le cahier §8.3 tranche en
  toutes lettres, et c'est lui qui prevaut : la page nationale presente « une
  liste accessible des entites », « une carte de France » et **« un acces a
  chaque entite ACTIVE »**.

  Deux sources concordantes, donc aucune invention.

LE FILTRE PORTE SUR TROIS ETATS, PAS SUR LES DEUX QUE LA FICHE NOMME

  `StatutEntite` en declare **quatre** : `draft`, `active`, `suspended`,
  `archived`. Le critere de sortie de `T1` ecrit dans la fiche ne nomme que
  « `suspended` ou `archived` » -- ce sont deux **exemples**, pas la classe.
  `draft` est le troisieme etat non actif, et une entite en brouillon rendue par
  cette route serait exactement le defaut que le critere veut empecher.

  **C'est le §7.34 de la passation, ecrit la veille** : un motif ecrit contre un
  exemple ne couvre que cet exemple. Le filtre est donc ecrit en `= active` et
  non en `NOT IN (suspended, archived)`, et les temoins couvrent **les trois**
  etats non actifs.

  Et la valeur comparee est **derivee de l'enumeration**, `StatutEntite.ACTIVE`,
  jamais la chaine litterale : une liste recopiee vieillit au premier ajout, et
  c'est §7.27.

QUATRE COLONNES SUR SEPT, ET LE MOTIF DE CHACUNE DES TROIS ABSENCES

  `entity` porte `code`, `display_name`, `city`, `country_code`, `status`,
  `timezone` et `activated_at`. Le §8.3 demande une liste et un acces ; il ne
  demande rien d'autre. Sont donc exposees `id`, `code`, `display_name` et
  `city`, et pas les trois autres :

    `status`       toute ligne rendue est active par construction. Le champ ne
                   porterait **aucune information**, et un champ constant apprend
                   a ne pas le lire -- c'est le §7.21 sur les avertissements
                   faux, dans un autre costume ;
    `timezone`     aucun ecran du LOT 4 n'affiche d'heure locale. L'exposer
                   maintenant serait livrer une donnee sans consommateur, ce que
                   `T10` du LOT 1 et `T11` de ce lot refusent tous deux ;
    `country_code` le §5.1 dit « `FR` dans le MVP ». Une carte **de France** n'a
                   pas besoin de distinguer les pays, et l'ajouter le jour ou une
                   entite etrangere existera sera une ligne.

  `city` EST EXPOSEE ET LA CARTE N'EN VIT PAS. C'est la seule colonne
  geographique de la table -- ni latitude ni longitude, mesure sur le schema
  reel -- et c'est ce qui rend le format de la carte un point ouvert de `T7`.
  Elle est exposee pour la **liste**, que le §8.3 exige, non pour la carte.

L'ORDRE EST TOTAL, ET C'EST UNE NECESSITE, PAS UN GOUT

  `ORDER BY display_name` seul ne suffit pas : rien n'impose l'unicite du nom
  d'affichage, et PostgreSQL est libre de rendre deux homonymes dans un ordre
  different d'un appel a l'autre. Le tri porte donc aussi sur `code`, qui est
  **UNIQUE** par `code_unique` : l'ordre devient total, donc reproductible, donc
  testable.
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.entities.modeles import StatutEntite

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  Les colonnes exposees, en une seule source. Le controle de `T1` compare la
#  reponse servie a cette liste : une colonne ajoutee a la requete sans etre
#  ajoutee ici -- ou l'inverse -- fait echouer le test.
COLONNES_EXPOSEES: Final[tuple[str, ...]] = ("id", "code", "display_name", "city")


@dataclasses.dataclass(frozen=True, slots=True)
class EntiteListee:
    """Une entite telle que la page nationale la voit."""

    id: uuid.UUID
    code: str
    display_name: str
    city: str


def lister_les_entites_actives(connexion: Connection) -> list[EntiteListee]:
    """Les entites `active`, triees par nom d'affichage puis par code.

    Aucun filtre d'appelant : la matrice §5 donne la page nationale aux **huit**
    roles authentifies, sans distinction. Le seul controle est l'existence d'une
    session, et il est porte par `exiger_une_session`.
    """
    lignes = connexion.execute(
        text(
            "SELECT id, code, display_name, city FROM entity "
            "WHERE status = :statut_actif "
            "ORDER BY display_name, code"
        ),
        {"statut_actif": StatutEntite.ACTIVE.value},
    ).fetchall()
    return [
        EntiteListee(
            id=uuid.UUID(str(ligne[0])),
            code=str(ligne[1]),
            display_name=str(ligne[2]),
            city=str(ligne[3]),
        )
        for ligne in lignes
    ]
