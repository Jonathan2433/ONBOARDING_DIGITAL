"""Creer un evenement, dans la portee resolue — matrice §11, LOT 8, `T3`, `US004` (1/3).

L'APPELANT A DEJA PROUVE `ROLES_DE_CREATION_EVENEMENT` : CE MODULE NE REJUGE
PAS LE ROLE COARSE, IL RESOUT LA PORTEE PRECISE

  La dependance de route exige l'un des six roles qui portent AU MOINS un droit
  de creation quelque part. Mais la matrice §11 donne a chacun EXACTEMENT une
  portee -- sauf au DSM, qui en a deux -- et la portee demandee n'arrive qu'avec
  le CORPS de la requete. C'est pourquoi `creer_un_evenement` revalide le couple
  (role, portee) via `peut_creer_un_evenement`, exactement comme
  `remplacer_le_contenu` revalide le couple (role, ressource) dans
  `app/content/ecriture.py`.

TROIS PORTEES, TROIS CHEMINS D'ECRITURE, ET UNE SEULE TRANSACTION

  `entite` (aucune ligne de portee), `cercle`/`bureau` (une ligne dans la table
  sœur correspondante) et `consultants` (une ligne dans `event_dsm_scope`,
  `ECART-067`, `DEC-622`) sont ECRITS DANS LA MEME TRANSACTION que l'evenement
  lui-meme : un evenement sans sa ligne de portee, ou l'inverse, serait un etat
  que rien dans ce module ne doit jamais produire.

CE QUE CE MODULE NE FAIT PAS ENCORE

  Il ne modifie, ne publie, n'annule, n'archive et ne rattache pas plusieurs
  cercles ou bureaux a la fois : la fiche du lot reserve ces gestes a `T4` et
  `T5`. Un evenement nait donc `draft` et seul, sans aucun media.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.events.perimetre import (
    PorteeDeCreation,
    peut_creer_un_evenement,
    verifier_le_rattachement_au_bureau,
    verifier_le_rattachement_au_cercle,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.errors import ErreurApplicative

#  **LE MEME GABARIT QUE PARTOUT AILLEURS DEPUIS `T9` DU LOT 4** (`CODE_ROLE_
#  REFUSE` de `app/permissions/dependances.py`) : un role absent de la portee
#  demandee et un Booster sur le cercle d'un autre rendent le MEME refus, pour
#  que le motif exact ne sorte jamais (§2.5 du cahier, « refus par defaut »).
CODE_ACCES_REFUSE: Final = "acces_refuse"
MESSAGE_ACCES_REFUSE: Final = (
    "Cet acces a ete refuse. Verifiez la portee demandee et vos responsabilites actives."
)

CODE_RATTACHEMENT_REQUIS: Final = "rattachement_requis"
MESSAGE_RATTACHEMENT_REQUIS: Final = (
    "La portee `cercle` exige un cercle ; la portee `bureau` exige un bureau."
)

#  Le meme code que `app/content/ecriture.py` : deux libelles pour la meme
#  cause (un code qui ne resout rien, dans cette entite) apprendraient a
#  distinguer deux mecanismes qui se comportent identiquement.
CODE_RESSOURCE_INTROUVABLE: Final = "ressource_introuvable"
MESSAGE_RESSOURCE_INTROUVABLE: Final = (
    "Le cercle ou le bureau nomme n'existe pas dans cette entite, ou il est archive."
)

CODE_CHRONOLOGIE_INVALIDE: Final = "chronologie_invalide"
MESSAGE_CHRONOLOGIE_INVALIDE: Final = (
    "`commence_le` doit etre strictement anterieur a `finit_le` (modele §17.1)."
)


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementCree:
    """Ce que la creation rend — assez pour que l'appelant retrouve son evenement."""

    identifiant: uuid.UUID
    title: str
    description: str | None
    starts_at: dt.datetime
    ends_at: dt.datetime
    location_text: str | None
    etat: str
    version: int
    portee: PorteeDeCreation


#  La ressource nommee existe-t-elle, NON ARCHIVEE, dans CETTE entite ? Le
#  couple `(id, entity_id)` porte l'isolation (§25.3) ; resoudre par le code
#  seul rattacherait un evenement au cercle d'une autre entite, ce que la cle
#  composite refuserait ensuite en 500. Memes requetes que
#  `app/content/ecriture.py`.
_CERCLE_PAR_CODE: Final = text(
    "SELECT id FROM circle WHERE entity_id = :entite AND code = :code AND archived_at IS NULL"
)
_BUREAU_PAR_CODE: Final = text(
    "SELECT id FROM office WHERE entity_id = :entite AND code = :code AND archived_at IS NULL"
)

#  Un parametre PAR COLONNE, jamais partage entre deux colonnes de types
#  differents — §7.25, `make parametres-check` le refuse depuis `DEC-580`.
_INSERER_L_EVENEMENT: Final = text(
    """
    INSERT INTO event
        (entity_id, title, description, starts_at, ends_at, location_text,
         created_by_person_id)
    VALUES
        (:entite, :titre, :description, :commence_le, :finit_le, :lieu, :acteur)
    RETURNING id, state, version
    """
)

_INSERER_LA_PORTEE_CERCLE: Final = text(
    "INSERT INTO event_circle_scope (entity_id, event_id, circle_id, created_by_person_id) "
    "VALUES (:entite, :evenement, :cercle, :acteur)"
)
_INSERER_LA_PORTEE_BUREAU: Final = text(
    "INSERT INTO event_office_scope (entity_id, event_id, office_id, created_by_person_id) "
    "VALUES (:entite, :evenement, :bureau, :acteur)"
)
#  `ECART-067`, `DEC-622` : le DSM EST la cle de sa propre portee, jamais une
#  liste de consultants figee a la creation — voir `EventDsmScope` au modele.
_INSERER_LA_PORTEE_CONSULTANTS: Final = text(
    "INSERT INTO event_dsm_scope (entity_id, event_id, dsm_person_id, created_by_person_id) "
    "VALUES (:entite, :evenement, :acteur, :acteur)"
)


def creer_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    title: str,
    description: str | None,
    starts_at: dt.datetime,
    ends_at: dt.datetime,
    location_text: str | None,
    portee: PorteeDeCreation,
    code_de_cercle: str | None,
    code_de_bureau: str | None,
    instant: dt.datetime,
) -> EvenementCree:
    """Creer un evenement en BROUILLON, dans la portee demandee — matrice §11.

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est **deja
    applique** : hors de son entite principale une personne n'a que `EMP`, et
    `EMP` ne porte aucune portee de creation.
    """
    if not peut_creer_un_evenement(roles, portee):
        raise ErreurApplicative(
            code=CODE_ACCES_REFUSE,
            message=MESSAGE_ACCES_REFUSE,
            statut=status.HTTP_403_FORBIDDEN,
        )

    #  **VALIDE ICI, PAS LAISSE A LA CONTRAINTE.** `ck_event_chronologie_valide`
    #  refuserait aussi, en `IntegrityError`, donc en 500 — et un 500 sur une
    #  faute de l'appelant l'accuserait d'un defaut du service. Meme motif que
    #  `type_de_page` dans `creer_une_page`.
    if not starts_at < ends_at:
        raise ErreurApplicative(
            code=CODE_CHRONOLOGIE_INVALIDE,
            message=MESSAGE_CHRONOLOGIE_INVALIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="finit_le",
        )

    cercle_id: uuid.UUID | None = None
    bureau_id: uuid.UUID | None = None

    if portee is PorteeDeCreation.CERCLE:
        if code_de_cercle is None:
            raise ErreurApplicative(
                code=CODE_RATTACHEMENT_REQUIS,
                message=MESSAGE_RATTACHEMENT_REQUIS,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="cercle",
            )
        cercle_id = connexion.execute(
            _CERCLE_PAR_CODE, {"entite": entite, "code": code_de_cercle}
        ).scalar_one_or_none()
        if cercle_id is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_RESSOURCE_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="cercle",
            )
        #  §11 : Booster cree pour « Cercle » — mais UNIQUEMENT le sien. Un
        #  Booster du cercle A qui nommerait le cercle B obtient le MEME refus
        #  qu'un role sans aucun droit de creation.
        if not verifier_le_rattachement_au_cercle(
            connexion, entite=entite, acteur=acteur, cercle=cercle_id, instant=instant
        ):
            raise ErreurApplicative(
                code=CODE_ACCES_REFUSE,
                message=MESSAGE_ACCES_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )

    elif portee is PorteeDeCreation.BUREAU:
        if code_de_bureau is None:
            raise ErreurApplicative(
                code=CODE_RATTACHEMENT_REQUIS,
                message=MESSAGE_RATTACHEMENT_REQUIS,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="bureau",
            )
        bureau_id = connexion.execute(
            _BUREAU_PAR_CODE, {"entite": entite, "code": code_de_bureau}
        ).scalar_one_or_none()
        if bureau_id is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_RESSOURCE_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="bureau",
            )
        if not verifier_le_rattachement_au_bureau(
            connexion, entite=entite, acteur=acteur, bureau=bureau_id, instant=instant
        ):
            raise ErreurApplicative(
                code=CODE_ACCES_REFUSE,
                message=MESSAGE_ACCES_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )

    #  `ENTITE` et `CONSULTANTS` n'exigent aucune ressource a resoudre : la
    #  premiere ne porte aucune ligne de portee, la seconde ne porte que
    #  l'acteur lui-meme (`ECART-067`).
    #
    #  **AUCUN `try`/`except` ICI, ET C'EST DELIBERE.** Les deux ressources
    #  citees viennent d'etre resolues DANS CETTE MEME TRANSACTION : aucune
    #  violation de cle etrangere ou d'unicite n'est attendue sur un chemin
    #  normal. Une `IntegrityError` qui survenait quand meme serait un defaut de
    #  CE module, pas une faute de l'appelant — un 500 bruyant vaut mieux qu'un
    #  422 qui l'accuserait a tort (§7.20).
    ligne = connexion.execute(
        _INSERER_L_EVENEMENT,
        {
            "entite": entite,
            "titre": title,
            "description": description,
            "commence_le": starts_at,
            "finit_le": ends_at,
            "lieu": location_text,
            "acteur": acteur,
        },
    ).one()
    evenement_id = ligne[0]

    if portee is PorteeDeCreation.CERCLE:
        connexion.execute(
            _INSERER_LA_PORTEE_CERCLE,
            {"entite": entite, "evenement": evenement_id, "cercle": cercle_id, "acteur": acteur},
        )
    elif portee is PorteeDeCreation.BUREAU:
        connexion.execute(
            _INSERER_LA_PORTEE_BUREAU,
            {"entite": entite, "evenement": evenement_id, "bureau": bureau_id, "acteur": acteur},
        )
    elif portee is PorteeDeCreation.CONSULTANTS:
        connexion.execute(
            _INSERER_LA_PORTEE_CONSULTANTS,
            {"entite": entite, "evenement": evenement_id, "acteur": acteur},
        )

    return EvenementCree(
        identifiant=evenement_id,
        title=title,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        location_text=location_text,
        etat=str(ligne[1]),
        version=int(ligne[2]),
        portee=portee,
    )
