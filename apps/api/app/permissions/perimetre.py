"""Qui peut ecrire QUOI sur QUI — matrice §6.1, §6.2 et §5.1, LOT 5 `T7`.

`resoudre_les_permissions` repond « quels ROLES cette personne porte dans cette
entite ». C'est ce dont la LECTURE avait besoin, et c'est tout ce que le LOT 4
avait a produire : la matrice §5 ne distingue aucun role en lecture.

**L'ECRITURE POSE UNE AUTRE QUESTION, ET AUCUN CODE N'Y REPONDAIT :** « cet
acteur peut-il modifier CETTE personne, et quels champs ». Le §6.2 la rend
inevitable :

    DSM     « ne peut modifier que les consultants ayant un rattachement DSM
              ACTIF vers lui »
    BOOST   « ne peut modifier que les membres ACTIFS de son cercle. Pour un
              membre SECONDAIRE, ses actions doivent rester limitees aux donnees
              du cercle et ne pas permettre de modifier un autre cercle principal
              sans autorisation superieure »
    OFFICE  « n'obtient AUCUN droit general sur les profils du seul fait de sa
              responsabilite de bureau »

Un controle par role seul rendrait donc « autorise » a un DSM sur le consultant
d'un autre DSM.

L'UNION DES DROITS PORTE SUR LES COUPLES (ROLE, PORTEE), PAS SUR LES ROLES

  Le §23.1 cumule, et son exemple le dit lui-meme : Booster du cercle Data ET
  responsable du BDE, « elle peut gerer le contenu du cercle Data, elle peut
  gerer le contenu du BDE, elle ne peut pas gerer le cercle Forge ni le BDG ».
  Le cumul est donc **borne par la portee de chaque role**. Chaque role
  contribue ici son ensemble de champs **pour cette cible seulement**, et
  l'union est prise ensuite.

  Consequence a connaitre : une personne a la fois `BOOST` et `ESM` PEUT changer
  le DSM, alors que `BOOST` seul ne peut pas. Ce n'est pas un trou, c'est le
  §23.1 -- et « hors changement de DSM » est une restriction de ROLE, non de
  ressource, donc le §23.2 ne la fait pas survivre au cumul.

LA GRILLE D'ETAT PREVAUT SUR LE CUMUL, ET ELLE S'APPLIQUE AUSSI A `SUPER`

  §23.2 : « une interdiction liee a la ressource ou a l'etat prevaut sur le cumul
  des roles ». La modification porte sur un profil VIVANT : le §6.1 traite
  separement « consulter un profil archive » et « reactiver un profil archive »,
  tous deux restreints, et l'archivage est `T8`. La cible doit donc etre dans un
  etat OCCUPANT -- `future` ou `active` -- et `ETATS_OCCUPANTS` porte deja ce
  regroupement dans `app/people/modeles.py`. En reecrire une copie ici serait le
  §7.27.

LE TEMPS EST INJECTE

  Toutes les periodes sont lues en `period @> :instant`, jamais en
  `ends_at IS NULL` : une affectation FUTURE a elle aussi un `ends_at` nul, et
  la compter comme active accorderait un droit qui n'existe pas encore. C'est le
  piege que `responsabilite_dsm_active` portait encore, `ECART-056`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.modeles import (
    ETATS_OCCUPANTS,
    TRANSITIONS_DU_CYCLE_DE_VIE,
    EtatAppartenance,
)
from app.permissions.services import RoleDeLaMatrice


class ChampOrganisationnel(enum.StrEnum):
    """Les SIX champs que le cahier §10.2 nomme « donnees organisationnelles ».

    « Pour un nouvel arrivant, les donnees organisationnelles sont preremplies et
    verrouillees : date d'arrivee ; metier ; statut ; DSM ; client ; cercle
    principal. » La liste est donc **ecrite dans le corpus**, pas choisie ici.

    `presentation courte`, `fun fact` et `cercles secondaires` sont des lignes
    DISTINCTES du §6.1, avec leurs propres portees -- `NEW` peut modifier son fun
    fact avant validation, ce qui n'est vrai d'aucun champ ci-dessous. Elles sont
    **hors du perimetre de `T7`**, nommees comme telles, et non oubliees.
    """

    DATE_D_ARRIVEE = "date_d_arrivee"
    METIER = "metier"
    STATUT = "statut"
    CLIENT = "client"
    DSM = "dsm"
    CERCLE_PRINCIPAL = "cercle_principal"


#  L'ordre vient de l'iteration de l'enumeration, donc du §10.2. Le meme parti
#  que `PermissionsDeLEntite.roles` : structurel plutot que teste (§7.35).
TOUS_LES_CHAMPS: Final[frozenset[ChampOrganisationnel]] = frozenset(ChampOrganisationnel)

#  **`BOOST` EST LE SEUL ROLE AVEC UNE EXCLUSION DE CHAMP, ET ELLE EST ECRITE.**
#  §6.1, ligne « Modifier metier, statut, DSM, client ou cercle principal » :
#  la colonne `BOOST` porte « Cercle, **hors changement de DSM** ».
CHAMPS_DU_BOOSTER: Final[frozenset[ChampOrganisationnel]] = TOUS_LES_CHAMPS - {
    ChampOrganisationnel.DSM
}

#  Les roles qui portent AU MOINS un droit de modification quelque part. Sert au
#  garde-fou de role de la route ; le perimetre par cible est resolu ensuite.
#
#  **`EMP`, `NEW` et `OFFICE` en sont ABSENTS, et chacun pour son motif ecrit :**
#  la colonne `OFFICE` du §6.1 est **entierement a tiret** et le §6.2 le redit en
#  clair ; `EMP` ne modifie plus rien apres validation (§6.2, et `RIGHTS-012`) ;
#  `NEW` ne modifie que photo, presentation et fun fact -- aucun des six champs
#  ci-dessus -- et le §6.2 les declare « preremplis et **verrouilles** » pour lui.
ROLES_D_ECRITURE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class PerimetreDEcriture:
    """Les champs que l'acteur peut ecrire SUR CETTE CIBLE, et rien d'autre.

    **UN ENSEMBLE VIDE EST LE REFUS**, et il n'y a pas de second champ pour le
    dire. Un booleen `autorise` derivable de `champs` serait un etat que rien
    n'empeche de contredire ; et un champ `motif` que la reponse ne peut pas
    porter -- le §2.5 « refus par defaut » interdit de reveler pourquoi -- serait
    un champ que personne ne lit jamais, ce que le §7.32 nomme un defaut.
    """

    champs: frozenset[ChampOrganisationnel]


#  La cible est-elle une appartenance OCCUPANTE de cette entite ? Le couple
#  `(id, entity_id)` est ce qui porte l'isolation (§25.3), et non un `WHERE`
#  sur l'entite seule -- deux appartenances d'entites differentes ne peuvent
#  pas se confondre.
_CIBLE_MODIFIABLE: Final[str] = """
SELECT 1 FROM entity_membership
WHERE id = :cible AND entity_id = :entite
  AND membership_state = ANY(:etats_occupants)
  AND archived_at IS NULL
"""

#  §6.2 : « un DSM ne peut modifier que les consultants ayant un rattachement DSM
#  ACTIF vers lui ». La cible est l'appartenance, l'acteur est une PERSONNE :
#  `dsm_assignment` porte `consultant_membership_id` et `dsm_person_id`.
_RATTACHE_A_CE_DSM: Final[str] = """
SELECT 1 FROM dsm_assignment
WHERE consultant_membership_id = :cible AND dsm_person_id = :acteur
  AND entity_id = :entite AND archived_at IS NULL
  AND period @> :instant
"""

#  §6.2 : « un Booster ne peut modifier que les membres ACTIFS de son cercle ».
#  Rend le TYPE d'appartenance au cercle du Booster -- `principal` ou
#  `secondary` -- parce que le §6.2 les traite differemment.
_TYPE_DANS_LE_CERCLE_DU_BOOSTER: Final[str] = """
SELECT cm.membership_type
FROM framework_responsibility_assignment fra
JOIN circle_membership cm
  ON cm.circle_id = fra.circle_id AND cm.entity_id = fra.entity_id
WHERE fra.person_id = :acteur AND fra.entity_id = :entite
  AND fra.responsibility_type = :type_booster
  AND fra.archived_at IS NULL AND fra.period @> :instant_fra
  AND cm.entity_membership_id = :cible
  AND cm.archived_at IS NULL AND cm.period @> :instant_cm
LIMIT 1
"""


def resoudre_le_perimetre(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> PerimetreDEcriture:
    """Les champs organisationnels que `acteur` peut ecrire sur `cible`.

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est **deja
    applique** : hors de son entite principale une personne n'a que `EMP`, et
    `EMP` n'est pas dans `ROLES_D_ECRITURE`. Il n'y a rien a redire ici, et le
    redire donnerait deux regles pour une seule (`DEC-466`).
    """
    #  **LA GRILLE D'ETAT D'ABORD, ET POUR TOUS LES ROLES.** §23.2 : une
    #  interdiction liee a l'etat prevaut sur le cumul. Un `SUPER` ne modifie pas
    #  davantage un profil archive qu'un DSM : cela releve de `T8`.
    modifiable = connexion.execute(
        text(_CIBLE_MODIFIABLE),
        {"cible": cible, "entite": entite, "etats_occupants": list(ETATS_OCCUPANTS)},
    ).first()
    if modifiable is None:
        return PerimetreDEcriture(champs=frozenset())

    champs: set[ChampOrganisationnel] = set()

    #  Portee ENTITE : le §6.1 ecrit « Entite » pour ESM et ADM-E, « Global » pour
    #  SUPER. La route etant deja bornee a une entite par son chemin, les trois
    #  se resolvent identiquement ici -- et le dire vaut mieux que de laisser
    #  croire que `SUPER` est traite a part.
    if roles & {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }:
        champs |= TOUS_LES_CHAMPS

    if RoleDeLaMatrice.DSM in roles:
        rattache = connexion.execute(
            text(_RATTACHE_A_CE_DSM),
            {"cible": cible, "acteur": acteur, "entite": entite, "instant": instant},
        ).first()
        if rattache is not None:
            champs |= TOUS_LES_CHAMPS

    if RoleDeLaMatrice.BOOSTER in roles:
        ligne = connexion.execute(
            text(_TYPE_DANS_LE_CERCLE_DU_BOOSTER),
            {
                "acteur": acteur,
                "entite": entite,
                "cible": cible,
                "type_booster": TypeResponsabilite.BOOSTER.value,
                "instant_fra": instant,
                "instant_cm": instant,
            },
        ).first()
        if ligne is not None and ligne[0] == TypeAppartenanceCercle.PRINCIPAL.value:
            champs |= CHAMPS_DU_BOOSTER
        #  **UN MEMBRE SECONDAIRE N'OUVRE AUCUN DES SIX CHAMPS, ET C'EST DERIVE
        #  DE DEUX SOURCES CONCORDANTES.** §6.2 : « pour un membre SECONDAIRE,
        #  ses actions doivent rester limitees aux donnees du cercle et ne pas
        #  permettre de modifier un autre cercle principal ». Or aucun des six
        #  champs n'est une donnee du cercle -- sauf `cercle_principal`, que la
        #  phrase exclut precisement. Et la roadmap le confirme en nommant le cas
        #  dans sa demonstration attendue : « ajout d'un membre secondaire par un
        #  Booster » puis « IMPOSSIBILITE pour le Booster de modifier son cercle
        #  principal ou son client ».
        #
        #  Gerer l'appartenance SECONDAIRE elle-meme est une autre ligne du §6.1,
        #  « Gerer les cercles secondaires », hors perimetre de `T7`.

    return PerimetreDEcriture(champs=frozenset(champs))


# ===========================================================================
#
#  LE CYCLE DE VIE — ARCHIVER, RESTAURER, CONSULTER UN ARCHIVE (LOT 5, `T8`)
#
#    **TROIS LIGNES DU §6.1, ET UNE SEULE GRILLE DE ROLES.** La matrice donne
#    exactement les memes trois roles aux trois actions :
#
#        Archiver un profil            —  —  —  Entite  —  —  Entite  Global
#        Reactiver un profil archive   —  —  —  Condit. —  —  Entite  Global
#        Consulter un profil archive   —  —  —  Entite* —  —  Entite  Global
#
#    `DSM` et `BOOST` sont A TIRET sur les trois, alors qu'ils portent tous deux
#    un droit de MODIFICATION. **Reutiliser `ROLES_D_ECRITURE` accorderait donc
#    l'archivage a deux roles que la matrice en exclut**, et le §6.2 le redit en
#    mots : « l'archivage d'un collaborateur est reserve a l'ESM, a
#    l'administrateur d'entite et au super-administrateur ». Deux grilles, parce
#    que le document en porte deux.
#
#    **« CONDITIONNEL » N'EST PAS UNE DECISION A PRENDRE (§7.29).** Le mot y
#    ressemble ; la condition est ecrite ailleurs, en deux endroits concordants :
#    le §18 precise « Entite, **restauration fonctionnelle** », et
#    `ARB-DROIT-003` tranche -- « l'ESM peut restaurer dans son entite un profil
#    […] ; les restaurations **techniques, massives ou liees aux imports**
#    restent reservees a l'administrateur d'entite et au super-administrateur ».
#    Un profil a l'unite par une route dediee EST une restauration
#    fonctionnelle : l'ESM est autorise.
#
#    **ET IL EXISTE UNE SECONDE LIGNE « REACTIVER UN PROFIL ARCHIVE », QUI N'EST
#    PAS CELLE-CI.** Le §14 -- imports CSV -- la reprend en exigeant
#    « Confirmation explicite » de l'ESM et de l'ADM-E. C'est le LOT 9, et
#    l'appliquer ici ajouterait une exigence que le §6.1 ne porte pas.
#
#    **LA GRILLE D'ETAT EST DERIVEE DU §24.1, PAS ECRITE.** `T7` avait un seul
#    etat admissible -- occupant -- et pouvait le lire dans `ETATS_OCCUPANTS`.
#    Ici chaque action a le sien, et la source est le diagramme : une action est
#    possible si et seulement si une transition part de l'etat courant.
#
# ===========================================================================


class ActionDeCycleDeVie(enum.StrEnum):
    """Les trois lignes du §6.1 qui portent sur un profil archive ou a archiver."""

    ARCHIVER = "archiver"
    RESTAURER = "restaurer"
    CONSULTER_UN_ARCHIVE = "consulter_un_archive"


ROLES_DU_CYCLE_DE_VIE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  Les etats depuis lesquels une transition MENE hors de l'occupation : c'est la
#  definition meme d'« archivable ». `active` y passe par `departed`, le §24.1
#  n'ayant aucune transition `Active --> Archived` directe.
ETATS_ARCHIVABLES: Final[frozenset[str]] = frozenset(
    depuis for depuis, vers in TRANSITIONS_DU_CYCLE_DE_VIE if vers not in ETATS_OCCUPANTS
)

#  Et ceux depuis lesquels une transition RAMENE dans l'occupation. Le §24.1 n'en
#  donne qu'un, `archived`, et le deriver ainsi fait suivre un §24.1 qui
#  en ajouterait un autre.
ETATS_RESTAURABLES: Final[frozenset[str]] = frozenset(
    depuis for depuis, vers in TRANSITIONS_DU_CYCLE_DE_VIE if vers in ETATS_OCCUPANTS
)


@dataclasses.dataclass(frozen=True, slots=True)
class PerimetreDuCycleDeVie:
    """Les actions de cycle de vie que l'acteur peut mener SUR CETTE CIBLE.

    **UN ENSEMBLE VIDE EST LE REFUS**, exactement comme `PerimetreDEcriture` :
    meme discipline, meme motif, et aucun champ derivable en plus.
    """

    actions: frozenset[ActionDeCycleDeVie]


#  L'etat courant de la cible. Le couple `(id, entity_id)` porte l'isolation
#  (§25.3) ; un `WHERE` sur l'entite seule confondrait deux appartenances.
_ETAT_DE_LA_CIBLE: Final[str] = """
SELECT membership_state FROM entity_membership
WHERE id = :cible AND entity_id = :entite AND archived_at IS NULL
"""


def resoudre_le_cycle_de_vie(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cible: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
) -> PerimetreDuCycleDeVie:
    """Quelles actions de cycle de vie `roles` autorise sur `cible`, dans `entite`.

    **AUCUN `acteur` EN PARAMETRE, ET C'EST UNE DIFFERENCE REELLE AVEC
    `resoudre_le_perimetre`.** Les trois roles du §6.1 ont une portee d'ENTITE ou
    globale : aucun ne depend d'un lien entre l'acteur et la cible, la ou un DSM
    dependait de `dsm_assignment` et un Booster de son cercle. Passer un acteur
    inutilise laisserait croire qu'il est examine.

    **AUCUN `instant` NON PLUS.** Rien ici n'est temporel : les roles arrivent
    deja resolus a l'instant de l'appelant par `resoudre_les_permissions`, et
    l'etat d'une appartenance n'est pas une periode. En demander un serait un
    parametre que personne ne lit -- §7.32.
    """
    if not roles & ROLES_DU_CYCLE_DE_VIE:
        return PerimetreDuCycleDeVie(actions=frozenset())

    ligne = connexion.execute(text(_ETAT_DE_LA_CIBLE), {"cible": cible, "entite": entite}).first()
    if ligne is None:
        return PerimetreDuCycleDeVie(actions=frozenset())

    etat = str(ligne[0])
    actions: set[ActionDeCycleDeVie] = set()
    if etat in ETATS_ARCHIVABLES:
        actions.add(ActionDeCycleDeVie.ARCHIVER)
    if etat in ETATS_RESTAURABLES:
        actions.add(ActionDeCycleDeVie.RESTAURER)
    if etat == EtatAppartenance.ARCHIVED.value:
        actions.add(ActionDeCycleDeVie.CONSULTER_UN_ARCHIVE)
    return PerimetreDuCycleDeVie(actions=frozenset(actions))
