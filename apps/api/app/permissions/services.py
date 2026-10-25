"""Quels droits une personne a-t-elle DANS l'entite qu'elle consulte ?

LOT 4, sous-etape `T8`, story `MVP-L04-US002`.

LA REGLE N'EST PAS INVENTEE : LA MATRICE §5.1 LA DONNE ENTIERE

  Le cahier §23.3 et la matrice §23.3 posent les memes cinq regles du changement
  d'entite, dont la troisieme -- « recharge les permissions ». Ni l'un ni l'autre
  ne dit CE QUE deviennent les permissions. **La matrice §5.1 le dit**, et c'est
  la section dediee que le §7.29 apprend a chercher :

    « Lorsqu'une personne consulte une entite differente de son entite
      principale : elle possede uniquement les droits `EMP` ; ses
      responsabilites DSM, ESM, Booster, responsable de bureau ou
      administrateur d'entite ne s'appliquent pas ; aucune action de creation,
      modification, publication, archivage, restauration ou export n'est
      proposee ; les controles cote API utilisent l'entite de la ressource, et
      non uniquement l'entite selectionnee dans le frontend.
      Le super-administrateur constitue la seule exception globale. »

  La resolution tient donc en trois branches, toutes ecrites :

    entite consultee == entite principale   ->  union des responsabilites (§23.1)
    entite consultee != entite principale   ->  `EMP` SEULEMENT (§5.1)
    role technique `SUPER_ADMIN`            ->  exception globale (§5.1)

  **Aucune quatrieme branche n'a ete ajoutee.** Le §23.2 -- « restriction la plus
  forte » -- porte sur des interdictions liees a **la ressource ou a l'etat**, pas
  sur la resolution des roles ; il s'appliquera route par route, la ou une
  ressource existe. Ce lot est en lecture seule et n'en expose aucune.

TROIS GARANTIES SONT DEJA STRUCTURELLES, ET MESUREES

  Le §5.1 aurait pu demander du code defensif. Le socle du LOT 2 le rend inutile,
  et le §7.32 dit quoi faire dans ce cas : ne pas ecrire la defense, EXIGER que
  la base continue d'interdire. Mesures du 24/08/2026 sur le schema reel :

    `ck_technical_role_assignment_portee_selon_le_role`
        CHECK ((role_type = 'ENTITY_ADMIN' AND entity_id IS NOT NULL)
            OR (role_type = 'SUPER_ADMIN'  AND entity_id IS NULL))
        -> « le super-administrateur constitue la SEULE exception globale » est
           une contrainte de base, pas une convention.

    `framework_responsibility_assignment.entity_id` NOT NULL
        -> une responsabilite est TOUJOURS rattachee a une entite. « Aucune
           permission locale n'est transferee » n'est pas une precaution de
           notre code : une responsabilite sans entite ne peut pas exister.

    `uq_entity_membership_person_id_occupante`
        UNIQUE (person_id) WHERE membership_state IN ('future','active')
        -> une personne a AU PLUS UNE appartenance occupante. L'entite
           principale est donc unique par construction, et il n'y a pas de cas
           « plusieurs entites principales » a arbitrer.

  Les trois sont eprouvees par des tests qui exigent le NOM de la contrainte
  violee : si un lot ulterieur les relachait, celui qui le fait saurait qu'il
  doit relire ce fichier.

LE TEMPS EST INJECTE, ET `ends_at IS NULL` NE SUFFIRAIT PAS

  Le controle §24.12 du cahier exige qu'« un role cloture ne continue pas a
  accorder des permissions ». Une affectation FUTURE, dont `starts_at` est a
  venir, a elle aussi `ends_at` nul : c'est la colonne generee `period` et
  l'operateur `@>` qui repondent a la vraie question, « ce droit est-il actif A
  CET INSTANT ». Meme idiome que `organization/services.py`.

  L'instant est un ARGUMENT. Un test qui doit prouver qu'un role clos n'accorde
  rien ne peut pas attendre la cloture : il l'injecte.

DEUX VOCABULAIRES POUR LES MEMES CHOSES, ET LA CORRESPONDANCE EST DECLAREE

  La matrice §3 nomme les roles `EMP`, `DSM`, `ESM`, `BOOST`, `OFFICE`, `ADM-E`,
  `SUPER`. Le modele §8.4 et §8.6 stockent `DSM`, `ESM`, `BOOSTER`,
  `OFFICE_MANAGER`, `ENTITY_ADMIN`, `SUPER_ADMIN`. Deux documents valides, deux
  vocabulaires -- et la reponse d'une route de PERMISSIONS parle celui de la
  matrice.

  La correspondance n'est pas devinee : chaque paire est appariee par les
  DESCRIPTIONS concordantes des deux documents -- « Booster, responsable d'un
  cercle » face a un `BOOSTER` dont le §8.4 exige `circle_id` ; « administrateur
  d'entite » face a un `ENTITY_ADMIN` dont la base exige `entity_id NOT NULL` ;
  « super-administrateur, toutes les entites » face au `SUPER_ADMIN` dont la base
  exige `entity_id IS NULL`.

  Elle reste une INTERPRETATION que ni l'un ni l'autre ne porte seul. Elle est
  donc **declaree** et non derivee, et un test **exige qu'elle couvre les deux
  enumerations en entier** -- c'est ce que le §7.27 prescrit pour une liste dont
  rien ne porte l'equivalent, et c'est ce qui l'empeche de vieillir au premier
  type ajoute.

DEUX ROLES DE LA MATRICE NE SONT PAS RESOLUS ICI, ET LE DIRE VAUT MIEUX

  `NEW` -- « employe disposant d'une fiche d'arrivee ou d'un onboarding actif ».
  Ni fiche d'arrivee ni onboarding n'existent dans le schema : ils appartiennent
  aux LOTS 7 et 8. Le deduire d'autre chose serait une invention (§6.5).

  `SERVICE` -- un compte de service n'a pas de session de personne, il porte un
  jeton et passe par `exiger_un_scope`. Une route qui exige une session ne peut
  pas en rendre un.

  `ANON` n'est pas un cas : sans session, la route rend 401.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.people.modeles import ETATS_OCCUPANTS

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

    from sqlalchemy.engine import Connection


class RoleDeLaMatrice(enum.StrEnum):
    """Les codes du §3 de la matrice, a la lettre.

    Les dix types y sont enumeres ; les sept ci-dessous sont ceux qu'une session
    de personne peut porter. `NEW` et `SERVICE` sont nommes au docstring du
    module avec le motif de leur absence, et `ANON` est l'absence de session.
    """

    EMPLOYE = "EMP"
    DSM = "DSM"
    ESM = "ESM"
    BOOSTER = "BOOST"
    RESPONSABLE_DE_BUREAU = "OFFICE"
    ADMINISTRATEUR_D_ENTITE = "ADM-E"
    SUPER_ADMINISTRATEUR = "SUPER"


#  Modele §8.4 -> matrice §3. Declaree, jamais derivee : voir le docstring.
CORRESPONDANCE_RESPONSABILITES: Final[Mapping[str, RoleDeLaMatrice]] = {
    TypeResponsabilite.DSM.value: RoleDeLaMatrice.DSM,
    TypeResponsabilite.ESM.value: RoleDeLaMatrice.ESM,
    TypeResponsabilite.BOOSTER.value: RoleDeLaMatrice.BOOSTER,
    TypeResponsabilite.OFFICE_MANAGER.value: RoleDeLaMatrice.RESPONSABLE_DE_BUREAU,
}

#  Modele §8.6 -> matrice §3.
CORRESPONDANCE_ROLES_TECHNIQUES: Final[Mapping[str, RoleDeLaMatrice]] = {
    TypeRoleTechnique.ENTITY_ADMIN.value: RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
    TypeRoleTechnique.SUPER_ADMIN.value: RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
}

#  **PAS DE SECONDE LISTE.** Les etats qui font d'une personne un « collaborateur
#  actif present dans la base » (matrice §3) sont ceux qui occupent la place
#  unique du §25.1, et `app/people/modeles.py` les declare DEJA sous le nom
#  `ETATS_OCCUPANTS`. En reecrire une copie ici serait le §7.27 dans mon propre
#  code : deux listes de meme sens divergent au premier etat ajoute, et
#  l'index unique partiel de la base suivrait l'une des deux.
#
#  La premiere version de ce fichier portait cette copie. Elle a ete retiree
#  apres avoir mesure que la constante existait -- pas avant.


@dataclasses.dataclass(frozen=True, slots=True)
class PermissionsDeLEntite:
    """Ce qu'une personne peut, DANS l'entite qu'elle consulte.

    `roles` suit **l'ordre de declaration de `RoleDeLaMatrice`**, qui est celui
    du tableau du §3 de la matrice.

    **CE N'ETAIT PAS LE PREMIER CHOIX, ET LA MESURE A TRANCHE.** La premiere
    version rendait `tuple(sorted(ensemble))`. Le tri retire, les quinze
    controles de `make permissions-check` passaient **trois fois sur trois** :
    l'iteration d'un `set` est stable au sein d'un meme processus, et les deux
    appels du controle tombent sur le meme worker. L'echec produisait donc la
    meme observation que le succes -- §7.0, quatrieme proposition, dans mon
    propre code.

    Renforcer le controle n'y pouvait rien : deux ensembles egaux s'iterent
    identiquement en CPython quel que soit l'ordre d'insertion, et le seul
    endroit ou l'ordre varierait vraiment est **d'un processus a l'autre**, que
    ni un controle de stack ni un test unitaire n'observent en une execution.

    **L'ordre est donc rendu STRUCTUREL au lieu d'etre teste.** Il vient de
    l'iteration de l'enumeration, pas d'un appel qu'on peut retirer sans que
    rien ne le dise : le perdre exigerait de supprimer la boucle elle-meme.
    C'est le §7.32 transpose -- ne pas tester ce qu'on peut rendre impossible.
    """

    entite: uuid.UUID
    est_entite_principale: bool
    roles: tuple[RoleDeLaMatrice, ...]
    #  `None` hors de l'entite principale, ou sans appartenance occupante —
    #  LOT 7, `T13`. Voir `_appartenance_occupante` : l'index unique du LOT 2
    #  garantit qu'il n'y en a jamais deux, dans CETTE entite ni ailleurs.
    appartenance: uuid.UUID | None


def entite_principale(connexion: Connection, personne: uuid.UUID) -> uuid.UUID | None:
    """L'entite de l'appartenance OCCUPANTE, ou `None` s'il n'y en a pas.

    `scalar_one_or_none` et non `scalar_one` : une personne peut n'avoir aucune
    appartenance occupante -- un ancien collaborateur archive, par exemple -- et
    l'index unique garantit qu'elle n'en a jamais deux. Le `or_none` porte donc
    un cas reel, pas une precaution.
    """
    return connexion.execute(
        text(
            "SELECT entity_id FROM entity_membership "
            "WHERE person_id = :personne "
            "  AND membership_state = ANY(:etats_occupants) "
            "  AND archived_at IS NULL"
        ),
        {"personne": personne, "etats_occupants": list(ETATS_OCCUPANTS)},
    ).scalar_one_or_none()


def _appartenance_occupante(connexion: Connection, personne: uuid.UUID) -> uuid.UUID | None:
    """L'identifiant de l'appartenance OCCUPANTE elle-meme — LOT 7, `T13`.

    **POURQUOI CETTE FONCTION EXISTE, ET POURQUOI ELLE N'EST APPELEE QUE DANS
    L'ENTITE PRINCIPALE.** Aucune route de l'onboarding (fiche d'arrivee,
    parcours, taches) n'accepte de cible implicite : chacune exige un
    `entity_membership_id` explicite dans son chemin (§7 et §8.1 de la
    matrice), exactement comme le reste de l'API depuis `T2` du LOT 7. Sans ce
    champ, l'ecran du nouvel arrivant n'aurait AUCUN moyen de savoir quelle
    URL appeler pour SES propres fiche et parcours.

    `uq_entity_membership_person_id_occupante` (LOT 2, `T?`) est UNIQUE sur
    `person_id` seul, pas sur `(person_id, entity_id)` : une personne a au
    plus UNE appartenance occupante, tous azimuts. Elle vit donc forcement
    dans l'entite PRINCIPALE — `resoudre_les_permissions` ne l'appelle que la,
    jamais hors de l'entite principale, ou elle rendrait `None` de toute
    facon.
    """
    return connexion.execute(
        text(
            "SELECT id FROM entity_membership "
            "WHERE person_id = :personne "
            "  AND membership_state = ANY(:etats_occupants) "
            "  AND archived_at IS NULL"
        ),
        {"personne": personne, "etats_occupants": list(ETATS_OCCUPANTS)},
    ).scalar_one_or_none()


def est_super_administrateur(
    connexion: Connection, personne: uuid.UUID, instant: dt.datetime
) -> bool:
    """`personne` tient-elle le role technique GLOBAL `SUPER_ADMIN`, a `instant`.

    Extraite de la branche 1 de `resoudre_les_permissions` (LOT 9, `T12`) :
    cette branche ne depend d'AUCUNE entite — `entity_id IS NULL` est exige
    par le §8.6 pour ce role precisement — et une garde qui n'a encore aucune
    entite a consulter (« creer une entite ») en a besoin seule, sans les deux
    autres branches qui, elles, exigent une entite deja existante.
    """
    return bool(
        connexion.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM technical_role_assignment "
                "  WHERE person_id = :personne_super AND role_type = :type_super "
                "    AND entity_id IS NULL AND archived_at IS NULL "
                "    AND period @> :instant_super"
                ")"
            ),
            #  Des noms DISTINCTS par emploi : un meme parametre lie a deux
            #  colonnes rend « inconsistent types deduced for parameter », et
            #  le message ne nomme ni la table ni la colonne. §7.25.
            {
                "personne_super": personne,
                "type_super": TypeRoleTechnique.SUPER_ADMIN.value,
                "instant_super": instant,
            },
        ).scalar_one()
    )


def est_administrateur_d_entite_quelque_part(
    connexion: Connection, personne: uuid.UUID, instant: dt.datetime
) -> bool:
    """`personne` tient-elle `ENTITY_ADMIN`, DANS N'IMPORTE QUELLE entite, a `instant`.

    Meme requete qu'`est_super_administrateur`, SANS le filtre
    `entity_id IS NULL` qui est propre a `SUPER_ADMIN` — extension du meme
    patron pour une ressource GLOBALE ou la grille Entite/Global de la
    matrice ne peut pas se lire comme un filtrage par entite, faute d'entite
    a filtrer sur la ressource elle-meme.

    **PROMUE ICI DEPUIS `app.support.perimetre_alertes` (LOT 10, `T13`)**,
    son premier appelant : `T14` (demandes RGPD) en est le second, et une
    fonction recopiee deux fois est exactement ce que le §7.27 de la
    passation apprend a partager plutot qu'a dupliquer — a la difference
    d'`_est_esm_quelque_part`, qui reste propre aux alertes faute d'un
    second appelant.
    """
    return bool(
        connexion.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM technical_role_assignment "
                "  WHERE person_id = :personne_adm AND role_type = :type_adm "
                "    AND archived_at IS NULL AND period @> :instant_adm"
                ")"
            ),
            {
                "personne_adm": personne,
                "type_adm": TypeRoleTechnique.ENTITY_ADMIN.value,
                "instant_adm": instant,
            },
        ).scalar_one()
    )


def resoudre_les_permissions(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    instant: dt.datetime,
) -> PermissionsDeLEntite:
    """Les roles de `personne` DANS `entite`, a `instant`.

    LES TROIS BRANCHES SONT CELLES DE LA MATRICE, DANS SON ORDRE

      1. `SUPER_ADMIN` actif -> l'exception globale du §5.1. Elle est ajoutee
         SANS condition sur l'entite consultee, parce que sa portee est la
         plateforme et que la base l'impose : `entity_id IS NULL`.
      2. l'entite consultee est l'entite principale -> union des responsabilites
         du §23.1, plus `ADM-E` s'il y a un role technique local.
      3. sinon -> `EMP` seulement, et rien d'autre.

    `EMP` EST ACCORDE PAR L'APPARTENANCE, PAS PAR L'ENTITE CONSULTEE

      Le §3 le definit comme « collaborateur actif present dans la base », et son
      perimetre principal est « lecture de toutes les entites ». C'est donc
      l'existence d'une appartenance occupante -- n'importe ou -- qui l'accorde,
      et le §5.1 le confirme : hors de son entite principale, la personne
      « possede UNIQUEMENT les droits `EMP` ». Une personne sans appartenance
      occupante ne recoit pas `EMP`, et peut donc ressortir avec un ensemble
      VIDE. Ce n'est pas une erreur : c'est ce que le corpus decrit, et le
      §7.32 interdit d'inventer une defense contre un etat que rien n'interdit.
    """
    roles: set[RoleDeLaMatrice] = set()

    principale = entite_principale(connexion, personne)
    est_principale = principale is not None and principale == entite

    if principale is not None:
        roles.add(RoleDeLaMatrice.EMPLOYE)

    #  Branche 1 -- l'exception globale, EXTRAITE en `est_super_administrateur`
    #  (LOT 9, `T12`) pour etre reutilisee par la garde GLOBALE de creation
    #  d'entite, qui n'a encore aucune entite a consulter (§7.27).
    if est_super_administrateur(connexion, personne, instant):
        roles.add(RoleDeLaMatrice.SUPER_ADMINISTRATEUR)

    if est_principale:
        #  Branche 2 -- l'union du §23.1. Les DEUX requetes sont bornees a
        #  `entity_id = :entite` : c'est ce qui rend « aucune permission locale
        #  n'est transferee » vrai par la requete, et non par une verification
        #  posterieure qu'on pourrait oublier.
        for (type_responsabilite,) in connexion.execute(
            text(
                "SELECT DISTINCT responsibility_type "
                "FROM framework_responsibility_assignment "
                "WHERE person_id = :personne_resp AND entity_id = :entite_resp "
                "  AND archived_at IS NULL AND period @> :instant_resp"
            ),
            {
                "personne_resp": personne,
                "entite_resp": entite,
                "instant_resp": instant,
            },
        ):
            role = CORRESPONDANCE_RESPONSABILITES.get(type_responsabilite)
            #  Un type inconnu est IGNORE, et c'est delibere : la contrainte
            #  `ck_..._responsibility_type_valide` interdit d'en ecrire un, et
            #  lever ici rendrait la route 500 sur une ligne que la base ne peut
            #  pas contenir. Le test d'exhaustivite de la correspondance est ce
            #  qui garantit qu'aucun type VALIDE ne tombe dans ce cas.
            if role is not None:
                roles.add(role)

        for (type_role,) in connexion.execute(
            text(
                "SELECT DISTINCT role_type FROM technical_role_assignment "
                "WHERE person_id = :personne_tech AND entity_id = :entite_tech "
                "  AND archived_at IS NULL AND period @> :instant_tech"
            ),
            {
                "personne_tech": personne,
                "entite_tech": entite,
                "instant_tech": instant,
            },
        ):
            role = CORRESPONDANCE_ROLES_TECHNIQUES.get(type_role)
            if role is not None:
                roles.add(role)

    return PermissionsDeLEntite(
        entite=entite,
        est_entite_principale=est_principale,
        #  L'ordre vient de l'ENUMERATION, jamais d'un tri. Voir le docstring
        #  de `PermissionsDeLEntite` : le tri etait invisible a tout controle.
        roles=tuple(membre for membre in RoleDeLaMatrice if membre in roles),
        appartenance=_appartenance_occupante(connexion, personne) if est_principale else None,
    )
