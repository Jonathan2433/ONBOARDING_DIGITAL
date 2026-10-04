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

import dataclasses
import datetime as dt
import enum
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.events.modeles import EtatEvenement
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

#  Les roles dont la portee est l'ENTITE entiere sur les evenements : le §11
#  ecrit « Entite » pour `ESM`/`ADM-E`, « Global » pour `SUPER`. La route etant
#  bornee a une entite par son chemin, les trois se resolvent identiquement --
#  meme parti que `ROLES_DE_PORTEE_ENTITE` de `app/content/perimetre.py`.
ROLES_DE_PORTEE_ENTITE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
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


# ===========================================================================
#
#  MODIFIER ET PUBLIER — matrice §11, LOT 8, `T4`, `MVP-L08-US004` (2 sur 3)
#
#    **DEUX LIGNES VOISINES, DEUX GRILLES QUI NE DIFFERENT QUE SUR UNE
#    CELLULE.** Le §11 donne, pour ESM/ADM-E/SUPER/BOOST/OFFICE, EXACTEMENT la
#    meme portee a « Modifier » et a « Publier » -- Entite, Entite, Global,
#    Cercle, Bureau. Seul le DSM diverge :
#
#        Modifier   « Evenements crees OU rattaches a son perimetre »
#        Publier    « Perimetre »
#
#    **ET « PERIMETRE », LU PAR LE §3, NE DENOTE PAS LE MEME ENSEMBLE SELON LE
#    ROLE** -- la lecon du §7.45 de la passation, deja payee au LOT 6. Pour
#    l'ESM, le §3 donne « Perimetre principal : ensemble de son entite », donc
#    `Perimetre` et `Entite` coincident. **Pour le DSM, le §3 donne « ses
#    CONSULTANTS dans son entite »** -- un ensemble de PERSONNES, exactement ce
#    que `EventDsmScope` porte. Publier un evenement cree par un DSM mais reste
#    de portee ENTITE ne lui est donc PAS ouvert : seul un evenement OU IL EST
#    LE DSM NOMME (`event_dsm_scope.dsm_person_id = acteur`) l'est. Modifier,
#    lui, accepte aussi « cree par lui », quelle que soit la portee choisie a la
#    creation.
#
# ===========================================================================


class ActionEvenement(enum.StrEnum):
    """Les deux lignes du §11 que `T4` sert — `T5` ajoutera annuler/archiver/restaurer."""

    MODIFIER = "modifier"
    PUBLIER = "publier"


@dataclasses.dataclass(frozen=True, slots=True)
class PerimetreEvenement:
    """Les actions que l'acteur peut mener SUR CET EVENEMENT.

    **UN ENSEMBLE VIDE EST LE REFUS**, meme discipline que `PerimetreDEcriture`
    et `PerimetreEditorial` de ce depot : pas de booleen derivable, pas de motif
    qui sortirait (§2.5, refus par defaut).
    """

    actions: frozenset[ActionEvenement]


#  L'evenement cible : qui l'a cree, dans quel etat, est-il archive ? Le couple
#  `(id, entity_id)` porte l'isolation (§25.3).
_EVENEMENT_CIBLE: Final[str] = """
SELECT created_by_person_id, state, archived_at
  FROM event
 WHERE id = :evenement AND entity_id = :entite
"""

#  `acteur` est-il Booster ACTIF d'au moins UN des cercles auxquels CET
#  evenement est rattache ? `period @> :instant`, jamais `ends_at IS NULL`
#  (`ECART-056`). La portee de l'evenement n'est pas relue a part : c'est la
#  JOINTURE qui la porte, donc aucune liste de cercles ne peut diverger entre
#  les deux cotes de la verification.
_ACTEUR_BOOSTER_DE_LA_PORTEE: Final[str] = """
SELECT 1
  FROM event_circle_scope ecs
  JOIN framework_responsibility_assignment fra
    ON fra.circle_id = ecs.circle_id AND fra.entity_id = ecs.entity_id
 WHERE ecs.event_id = :evenement AND ecs.entity_id = :entite
   AND ecs.archived_at IS NULL
   AND fra.person_id = :acteur
   AND fra.responsibility_type = :type_booster
   AND fra.archived_at IS NULL AND fra.period @> :instant
 LIMIT 1
"""

#  Symetrique pour un responsable de bureau.
_ACTEUR_OFFICE_DE_LA_PORTEE: Final[str] = """
SELECT 1
  FROM event_office_scope eos
  JOIN framework_responsibility_assignment fra
    ON fra.office_id = eos.office_id AND fra.entity_id = eos.entity_id
 WHERE eos.event_id = :evenement AND eos.entity_id = :entite
   AND eos.archived_at IS NULL
   AND fra.person_id = :acteur
   AND fra.responsibility_type = :type_office
   AND fra.archived_at IS NULL AND fra.period @> :instant
 LIMIT 1
"""

#  `ECART-067` : l'acteur EST-il le DSM nomme par la portee « consultants » de
#  CET evenement ? Aucune jointure vers `dsm_assignment` -- la table porte
#  directement le DSM, pas ses consultants.
_ACTEUR_EST_LE_DSM_DE_LA_PORTEE: Final[str] = """
SELECT 1 FROM event_dsm_scope
 WHERE event_id = :evenement AND entity_id = :entite
   AND archived_at IS NULL AND dsm_person_id = :acteur
 LIMIT 1
"""


def resoudre_le_perimetre_de_l_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    evenement: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> PerimetreEvenement:
    """Les actions du §11 que `acteur` peut mener sur `evenement`, dans `entite`.

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est **deja
    applique**. Un evenement ARCHIVE n'offre plus rien ici : `T5` porte sa
    propre grille de cycle de vie, et un `UPDATE` sur une ligne qui n'existe
    plus rendrait un succes vide sans cette garde (§7.0, quatrieme proposition).
    """
    ligne = connexion.execute(
        text(_EVENEMENT_CIBLE), {"evenement": evenement, "entite": entite}
    ).one_or_none()
    if ligne is None or ligne[2] is not None:
        return PerimetreEvenement(actions=frozenset())

    createur, etat = ligne[0], str(ligne[1])
    actions: set[ActionEvenement] = set()

    if roles & ROLES_DE_PORTEE_ENTITE:
        actions |= {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}

    if (
        RoleDeLaMatrice.BOOSTER in roles
        and connexion.execute(
            text(_ACTEUR_BOOSTER_DE_LA_PORTEE),
            {
                "evenement": evenement,
                "entite": entite,
                "acteur": acteur,
                "type_booster": TypeResponsabilite.BOOSTER.value,
                "instant": instant,
            },
        ).first()
    ):
        actions |= {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}

    if (
        RoleDeLaMatrice.RESPONSABLE_DE_BUREAU in roles
        and connexion.execute(
            text(_ACTEUR_OFFICE_DE_LA_PORTEE),
            {
                "evenement": evenement,
                "entite": entite,
                "acteur": acteur,
                "type_office": TypeResponsabilite.OFFICE_MANAGER.value,
                "instant": instant,
            },
        ).first()
    ):
        actions |= {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}

    if RoleDeLaMatrice.DSM in roles:
        #  « Perimetre » seul publie ; « cree OU rattache » modifie -- deux
        #  grilles distinctes pour le MEME role, et c'est le §11 qui les separe.
        est_le_dsm_nomme = connexion.execute(
            text(_ACTEUR_EST_LE_DSM_DE_LA_PORTEE),
            {"evenement": evenement, "entite": entite, "acteur": acteur},
        ).first()
        if est_le_dsm_nomme:
            actions |= {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}
        elif createur == acteur:
            actions.add(ActionEvenement.MODIFIER)

    #  `PUBLIER` n'est offert qu'a un BROUILLON -- meme discipline que
    #  `publier_une_page` au LOT 6 : pas de republication, qui ecraserait
    #  silencieusement une date que rien ne demande de reecrire.
    if etat != EtatEvenement.DRAFT.value:
        actions.discard(ActionEvenement.PUBLIER)

    return PerimetreEvenement(actions=frozenset(actions))
