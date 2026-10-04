"""Qui peut CREER un evenement, et dans quelle portee — matrice §11, LOT 8, `T3`.

LA MATRICE N'A QU'UNE LIGNE DE CREATION, ET CHAQUE ROLE Y PORTE EXACTEMENT UNE
PORTEE -- SAUF LE DSM, QUI EN PORTE DEUX

    EMP     —                     (aucune creation)
    DSM     Entite OU consultants
    ESM     Entite
    BOOST   Cercle
    OFFICE  Bureau
    ADM-E   Entite
    SUPER   Global

  A la difference du §13 des contenus, ou une seule ligne de creation est
  reservee a trois roles de portee ENTITE et ou Booster/responsable de bureau ne
  CREENT rien -- ils MODIFIENT le contenu d'une ressource deja creee --, ici
  Booster et responsable de bureau CREENT directement un evenement, borne a LEUR
  cercle ou LEUR bureau. Une seule grille ne suffirait donc pas : il faut savoir
  QUELLE portee est demandee pour savoir QUEL role l'autorise.

`ECART-067` : « CONSULTANTS » N'EST PAS UNE RESSOURCE A RATTACHER, C'EST LE RÔLE
LUI-MEME

  Un cercle et un bureau sont des unites organisationnelles stables : un DSM
  n'en a aucune. Sa portee « consultants » ne reclame donc AUCUNE ressource a
  resoudre par un code -- contrairement a `CERCLE` et `BUREAU` -- et aucune
  verification supplementaire au-dela du role : c'est `EventDsmScope.
  dsm_person_id = acteur` qui porte tout le sens de cette portee, en lecture
  comme a l'ecriture. Voir le modele dans `app/events/modeles.py`.

CE QUE CE MODULE NE FAIT PAS

  Il ne resout ni n'insere rien : `peut_creer_un_evenement` repond a « ce role a
  cette portee a-t-il le droit de principe ? », et les deux fonctions de
  rattachement repondent a « ce Booster/ce responsable de bureau gere-t-il
  PRECISEMENT cette ressource ? ». La resolution du code en identifiant et
  l'ecriture vivent dans `app/events/ecriture.py`, exactement comme
  `app/content/perimetre.py` ne resout pas lui-meme les codes de cercle/bureau.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice


class PorteeDeCreation(enum.StrEnum):
    """Les quatre portees que la matrice §11 permet d'exprimer a la creation."""

    ENTITE = "entite"
    CERCLE = "cercle"
    BUREAU = "bureau"
    CONSULTANTS = "consultants"


#  Le garde-fou de ROLE de la route : au moins un droit de creation quelque
#  part. La portee exacte est resolue ensuite par `peut_creer_un_evenement`, qui
#  seule connait la portee demandee -- la ROUTE ne la lit pas avant le corps.
ROLES_DE_CREATION_EVENEMENT: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.RESPONSABLE_DE_BUREAU,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  §11, colonne par colonne. **LA ROUTE ETANT DEJA BORNEE A UNE ENTITE PAR SON
#  CHEMIN**, `ESM`, `ADM-E` ("Entite") et `SUPER` ("Global") se resolvent
#  identiquement -- meme parti que `ROLES_DE_PORTEE_ENTITE` de
#  `app/content/perimetre.py`, et le dire vaut mieux que de laisser croire que
#  `SUPER` est traite a part.
_PORTEES_AUTORISEES_PAR_ROLE: Final[dict[RoleDeLaMatrice, frozenset[PorteeDeCreation]]] = {
    RoleDeLaMatrice.DSM: frozenset({PorteeDeCreation.ENTITE, PorteeDeCreation.CONSULTANTS}),
    RoleDeLaMatrice.ESM: frozenset({PorteeDeCreation.ENTITE}),
    RoleDeLaMatrice.BOOSTER: frozenset({PorteeDeCreation.CERCLE}),
    RoleDeLaMatrice.RESPONSABLE_DE_BUREAU: frozenset({PorteeDeCreation.BUREAU}),
    RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE: frozenset({PorteeDeCreation.ENTITE}),
    RoleDeLaMatrice.SUPER_ADMINISTRATEUR: frozenset({PorteeDeCreation.ENTITE}),
}


def peut_creer_un_evenement(roles: frozenset[RoleDeLaMatrice], portee: PorteeDeCreation) -> bool:
    """§11 « Creer » : l'un des `roles` porte-t-il CETTE `portee` ?

    **AUCUNE CONNEXION, AUCUNE CIBLE, AUCUN INSTANT.** La creation ne porte sur
    aucune ressource existante : seuls le role et la portee demandee sont en
    jeu, exactement le motif de `peut_creer_une_page` dans
    `app/content/perimetre.py`. Un acces au cercle ou au bureau PRECIS se
    verifie ensuite, par `verifier_le_rattachement_au_cercle` ou
    `verifier_le_rattachement_au_bureau`.
    """
    return any(portee in _PORTEES_AUTORISEES_PAR_ROLE.get(role, frozenset()) for role in roles)


#  §11 : Booster cree pour « Cercle », responsable de bureau pour « Bureau ».
#  **`person_id = :acteur` ET `{colonne} = :ressource` SONT TOUS DEUX
#  NECESSAIRES** : sans le premier, la responsabilite de n'importe qui sur ce
#  cercle accorderait le droit ; sans le second, n'importe quelle responsabilite
#  de CET acteur l'accorderait, meme sur un autre cercle. Meme motif que
#  `_RESPONSABILITE_SUR_LA_RESSOURCE` de `app/content/perimetre.py`.
#
#  `period @> :instant`, JAMAIS `ends_at IS NULL` -- une affectation FUTURE a
#  elle aussi un `ends_at` nul, et la compter comme active accorderait un droit
#  qui n'existe pas encore (`ECART-056`).
_RESPONSABILITE_SUR_LA_RESSOURCE: Final[str] = """
SELECT 1 FROM framework_responsibility_assignment
 WHERE person_id = :acteur AND entity_id = :entite
   AND responsibility_type = :type_de_responsabilite
   AND {colonne} = :ressource
   AND archived_at IS NULL AND period @> :instant
 LIMIT 1
"""


def verifier_le_rattachement_au_cercle(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cercle: uuid.UUID,
    instant: dt.datetime,
) -> bool:
    """`acteur` est-il Booster ACTIF de CE cercle, dans cette entite ?"""
    requete = _RESPONSABILITE_SUR_LA_RESSOURCE.format(colonne="circle_id")
    ligne = connexion.execute(
        text(requete),
        {
            "acteur": acteur,
            "entite": entite,
            "type_de_responsabilite": TypeResponsabilite.BOOSTER.value,
            "ressource": cercle,
            "instant": instant,
        },
    ).first()
    return ligne is not None


def verifier_le_rattachement_au_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    bureau: uuid.UUID,
    instant: dt.datetime,
) -> bool:
    """`acteur` est-il responsable ACTIF de CE bureau, dans cette entite ?"""
    requete = _RESPONSABILITE_SUR_LA_RESSOURCE.format(colonne="office_id")
    ligne = connexion.execute(
        text(requete),
        {
            "acteur": acteur,
            "entite": entite,
            "type_de_responsabilite": TypeResponsabilite.OFFICE_MANAGER.value,
            "ressource": bureau,
            "instant": instant,
        },
    ).first()
    return ligne is not None
