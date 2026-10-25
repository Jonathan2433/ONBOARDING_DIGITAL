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

`T4` AJOUTE MODIFIER, PUBLIER ET LES RATTACHEMENTS MULTIPLES

  `modifier_un_evenement` ecrit les champs ET remplace, si elles sont fournies,
  les listes de cercles/bureaux de l'evenement — meme motif « la liste remplace
  la liste » que `remplacer_le_contenu` au LOT 6 : les lignes de portee
  retirees sont ARCHIVEES, jamais supprimees.

  **CHAQUE CODE AJOUTE EST REVALIDE INDIVIDUELLEMENT, INDEPENDAMMENT DU
  PERIMETRE GLOBAL DEJA VERIFIE PAR LA ROUTE.** Un acteur peut avoir le droit
  de MODIFIER cet evenement — par son propre cercle, par exemple — sans avoir
  le droit d'y ATTACHER le cercle d'un AUTRE Booster : les deux questions sont
  independantes, et §23.1 ne cumule que ce que chaque role accorde VRAIMENT.
  Un role de portee ENTITE (ESM/ADM-E/SUPER) n'a besoin d'aucune verification
  supplementaire : son perimetre couvre deja l'entite entiere.

  `publier_un_evenement` ne fait que la transition `draft -> published`, au
  meme verrou optimiste (§18.4) que `publier_une_page` du LOT 6 : aucune
  republication, ce qui ecraserait silencieusement une date que rien ne
  demande de reecrire.

`T5` AJOUTE ANNULER, ARCHIVER ET RESTAURER

  Les trois transitions, et ce qui les borne — meme discipline que
  `app/content/cycle_de_vie.py` au LOT 6 :

      published  --  annuler    -->  cancelled   cancelled_at, cancellation_reason
      draft|published|cancelled --  archiver  -->  archived    archived_at, archived_by
      archived   --  restaurer  -->  draft       archived_at et archived_by effaces

  **IL N'Y A PAS DE `draft --> cancelled`** : annuler un brouillon que
  personne n'a jamais vu contournerait la porte de publication que `PUBLIER`
  impose. **LA RESTAURATION REND TOUJOURS `draft`, JAMAIS L'ETAT ANTERIEUR A
  L'ARCHIVAGE** — meme raisonnement que `restaurer_une_page` : restaurer
  n'est pas publier, et `RIGHTS-001` refuse par defaut ce qui n'est pas
  explicitement redecide. `cancelled_at`/`cancellation_reason` ne sont PAS
  effaces par l'archivage ni par la restauration : l'evenement A ete annule
  ce jour-la, et c'est un fait, pas un residu — meme parti que `published_at`
  pour une page.

  **AUCUN MOTIF N'EST DEMANDE POUR ARCHIVER**, et le §18.1 en donne la
  raison : il enumere cinq cas ou un motif est obligatoire, et archiver un
  evenement n'y est pas. `archive_reason` existe depuis le LOT 2 et personne
  ne l'ecrit (`ECART-064`, toujours ouvert).

`T6` AJOUTE LE RATTACHEMENT DES MEDIAS

  `gerer_les_medias_d_un_evenement` sert « Ajouter une image ou vidéo » du
  §11 — meme discipline « la liste remplace la liste » que les cercles/
  bureaux de `T4` et les blocs de contenu du LOT 6 : les lignes de
  `event_media` retirees sont ARCHIVEES, jamais supprimees, et `display_order`
  vaut l'INDEX du tableau soumis — jamais un decalage calcule sur le nombre
  de lignes vivantes, piege deja mesure au LOT 6 (`T8-1`, non deterministe).

  **AUCUN TELEVERSEMENT, AUCUN TRAITEMENT** : ce module ne fait que RATTACHER
  un `media_asset` qui existe DEJA, dans la MEME entite. Televerser un
  fichier, generer ses variantes, c'est le LOT 11 — hors de ce depot pour le
  moment, et ce module ne l'anticipe pas.

  **SEUL UN MEDIA `ready` EST RATTACHABLE**, et ce n'est pas une regle
  inventee : c'est la reutilisation de `ETAT_AFFICHABLE` (`app/media/
  photo.py`, LOT 5), la definition DEJA DECIDEE de ce qu'est un media
  « affichable ». L'accueil (`T11`/`T12`) consommera cette meme liste, et un
  media encore `pending`/`processing`, ou `rejected`/`archived`/`deleted`,
  n'a rien a y faire.

CE QUE CE MODULE NE FAIT PAS ENCORE

  `T2` (lecture des evenements) ne rend aucun media : ce module n'etend pas
  sa reponse. Une lecture publique des medias attaches n'a pas encore de
  consommateur avant les ecrans (`T9` a `T12`).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.elements import TextClause

from app.audit.motif import exiger_un_motif_si_necessaire
from app.audit.services import enregistrer_un_evenement
from app.events.modeles import EtatEvenement
from app.events.perimetre import (
    ROLES_DE_PORTEE_ENTITE,
    ActionEvenement,
    PorteeDeCreation,
    peut_creer_un_evenement,
    verifier_le_rattachement_au_bureau,
    verifier_le_rattachement_au_cercle,
)
from app.media.photo import ETAT_AFFICHABLE
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

#  Meme gabarit que `CODE_VERSION_OBSOLETE` de `app/content/ecriture.py` —
#  cahier §18.4, « sans ecrasement silencieux ».
CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "L'evenement a change depuis votre lecture, ou n'est plus a l'etat attendu "
    "(cahier §18.4, « sans ecrasement silencieux »)."
)

CODE_DOUBLON_DANS_LA_LISTE: Final = "doublon_dans_la_liste"
MESSAGE_DOUBLON_DANS_LA_LISTE: Final = (
    "Un meme cercle ou bureau est nomme deux fois dans la meme liste."
)
MESSAGE_DOUBLON_DE_MEDIA: Final = "Un meme media est nomme deux fois dans la meme liste."

#  Le MEME code que ci-dessus, un message different : media_asset n'est ni
#  un cercle ni un bureau, mais la cause est identique (§2.5, refus par
#  defaut) — enseigner deux mecanismes qui se comportent identiquement
#  apprendrait a les distinguer pour rien.
MESSAGE_MEDIA_INTROUVABLE: Final = (
    "Le media nomme n'existe pas dans cette entite, ou il est archive."
)

CODE_MEDIA_NON_PRET: Final = "media_non_pret"
MESSAGE_MEDIA_NON_PRET: Final = (
    "Seul un media `ready` peut etre rattache a un evenement (app/media/photo.py, ETAT_AFFICHABLE)."
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
    motif: str | None = None,
) -> EvenementCree:
    """Creer un evenement en BROUILLON, dans la portee demandee — matrice §11.

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est **deja
    applique** : hors de son entite principale une personne n'a que `EMP`, et
    `EMP` ne porte aucune portee de creation.

    `motif` : le motif du §18.1 — obligatoire quand `SUPER` autorise l'appel
    (`app.audit.motif`, `ECART-064`, LOT 10 `T7`), verifie ICI puisque
    `roles` est deja un parametre.
    """
    if not peut_creer_un_evenement(roles, portee):
        raise ErreurApplicative(
            code=CODE_ACCES_REFUSE,
            message=MESSAGE_ACCES_REFUSE,
            statut=status.HTTP_403_FORBIDDEN,
        )
    exiger_un_motif_si_necessaire(roles, motif)

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

    #  LOT 10, `T5` : aucune valeur `ActionEvenement` ne nomme la creation —
    #  l'enumeration ne couvre que les six lignes du §11 ou un DROIT se joue,
    #  et « creer » releve de `PorteeDeCreation`, une structure distincte.
    #  Litteral, meme discipline que les liens internes au LOT 6 (`T8`,
    #  reutilisee par `T4` de ce lot).
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="creer",
        resource_type="event",
        resource_reference=evenement_id,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation de l'evenement « {title} »",
        reason=motif,
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


# ===========================================================================
#
#  MODIFIER ET PUBLIER — matrice §11, LOT 8, `T4`, `MVP-L08-US004` (2 sur 3)
#
# ===========================================================================


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementModifie:
    """Ce qu'une modification ou une publication rend."""

    identifiant: uuid.UUID
    title: str
    description: str | None
    starts_at: dt.datetime
    ends_at: dt.datetime
    location_text: str | None
    etat: str
    version: int


#  Le verrou optimiste du §18.4, pose par un `SELECT … FOR UPDATE` : aucune
#  ligne rendue signifie que l'evenement a quitte l'etat attendu (archive, ou
#  pas `draft` pour la publication) ; une version differente, qu'il a ete
#  ecrit entre-temps. Les deux causes rendent le MEME refus (§2.5).
_EVENEMENT_VERSION_POUR_MISE_A_JOUR: Final = text(
    "SELECT version FROM event WHERE id = :evenement AND entity_id = :entite "
    "AND archived_at IS NULL FOR UPDATE"
)
_EVENEMENT_VERSION_POUR_PUBLICATION: Final = text(
    "SELECT version FROM event WHERE id = :evenement AND entity_id = :entite "
    "AND archived_at IS NULL AND state = :etat_attendu FOR UPDATE"
)


def _exiger_la_version(
    connexion: Connection,
    requete: TextClause,
    parametres: dict[str, object],
    *,
    attendue: int,
) -> None:
    """Meme discipline que `_exiger_la_version` de `app/content/cycle_de_vie.py`."""
    ligne = connexion.execute(requete, parametres).one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
        )
    if int(ligne[0]) != attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
            details={"version_actuelle": int(ligne[0])},
        )


_METTRE_A_JOUR_L_EVENEMENT: Final = text(
    """
    UPDATE event
       SET title = :titre, description = :description,
           starts_at = :commence_le, ends_at = :finit_le, location_text = :lieu,
           updated_at = :instant, updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :evenement AND entity_id = :entite
    RETURNING version, state
    """
)

_ARCHIVER_LES_PORTEES_CERCLE: Final = text(
    "UPDATE event_circle_scope SET archived_at = :instant, archived_by_person_id = :acteur "
    "WHERE event_id = :evenement AND entity_id = :entite AND archived_at IS NULL"
)
_ARCHIVER_LES_PORTEES_BUREAU: Final = text(
    "UPDATE event_office_scope SET archived_at = :instant, archived_by_person_id = :acteur "
    "WHERE event_id = :evenement AND entity_id = :entite AND archived_at IS NULL"
)


def _verifier_l_absence_de_doublon(codes: list[str], *, champ: str) -> None:
    if len(set(codes)) != len(codes):
        raise ErreurApplicative(
            code=CODE_DOUBLON_DANS_LA_LISTE,
            message=MESSAGE_DOUBLON_DANS_LA_LISTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ=champ,
        )


def _resoudre_les_cercles(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    codes: list[str],
    instant: dt.datetime,
) -> list[uuid.UUID]:
    """Resoudre chaque code de cercle, et verifier le droit d'y ATTACHER l'evenement.

    **INDEPENDANT DU PERIMETRE GLOBAL DEJA VERIFIE PAR LA ROUTE.** Un role de
    portee ENTITE (ESM/ADM-E/SUPER) n'a besoin d'aucune verification de plus —
    son perimetre couvre deja l'entite entiere. Un Booster ne peut attacher QUE
    son propre cercle, meme s'il a par ailleurs le droit de MODIFIER cet
    evenement par une autre voie (§23.1 : l'union des droits porte sur les
    COUPLES role/ressource, pas sur les roles seuls).
    """
    _verifier_l_absence_de_doublon(codes, champ="cercles")
    portee_entite = bool(roles & ROLES_DE_PORTEE_ENTITE)
    identifiants: list[uuid.UUID] = []
    for code in codes:
        identifiant = connexion.execute(
            _CERCLE_PAR_CODE, {"entite": entite, "code": code}
        ).scalar_one_or_none()
        if identifiant is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_RESSOURCE_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="cercles",
            )
        if not portee_entite and not verifier_le_rattachement_au_cercle(
            connexion, entite=entite, acteur=acteur, cercle=identifiant, instant=instant
        ):
            raise ErreurApplicative(
                code=CODE_ACCES_REFUSE,
                message=MESSAGE_ACCES_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )
        identifiants.append(identifiant)
    return identifiants


def _resoudre_les_bureaux(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    codes: list[str],
    instant: dt.datetime,
) -> list[uuid.UUID]:
    """Symetrique de `_resoudre_les_cercles`, pour les bureaux."""
    _verifier_l_absence_de_doublon(codes, champ="bureaux")
    portee_entite = bool(roles & ROLES_DE_PORTEE_ENTITE)
    identifiants: list[uuid.UUID] = []
    for code in codes:
        identifiant = connexion.execute(
            _BUREAU_PAR_CODE, {"entite": entite, "code": code}
        ).scalar_one_or_none()
        if identifiant is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_RESSOURCE_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="bureaux",
            )
        if not portee_entite and not verifier_le_rattachement_au_bureau(
            connexion, entite=entite, acteur=acteur, bureau=identifiant, instant=instant
        ):
            raise ErreurApplicative(
                code=CODE_ACCES_REFUSE,
                message=MESSAGE_ACCES_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )
        identifiants.append(identifiant)
    return identifiants


def modifier_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    evenement: uuid.UUID,
    title: str,
    description: str | None,
    starts_at: dt.datetime,
    ends_at: dt.datetime,
    location_text: str | None,
    version_attendue: int,
    codes_de_cercle: list[str] | None,
    codes_de_bureau: list[str] | None,
    instant: dt.datetime,
    motif: str | None = None,
) -> EvenementModifie:
    """Remplacer les champs d'un evenement, et ses rattachements si fournis.

    L'appelant a deja prouve `ActionEvenement.MODIFIER` via
    `resoudre_le_perimetre_de_l_evenement` : ce module ne rejuge pas ce droit
    coarse. Il verifie en revanche, pour CHAQUE cercle ou bureau NOMME dans les
    listes, que l'acteur a le droit de l'y attacher — une question distincte,
    voir `_resoudre_et_verifier_les_codes`.

    `codes_de_cercle`/`codes_de_bureau` valant `None` signifie « ne pas toucher
    cette dimension » ; une liste vide la VIDE — meme distinction que
    `BlocSoumis` au LOT 6, ou la liste remplace la liste.

    `motif` : meme regle que `creer_un_evenement` — LOT 10 `T7`, `ECART-064`,
    verifie ICI puisque `roles` est deja un parametre.
    """
    exiger_un_motif_si_necessaire(roles, motif)
    if not starts_at < ends_at:
        raise ErreurApplicative(
            code=CODE_CHRONOLOGIE_INVALIDE,
            message=MESSAGE_CHRONOLOGIE_INVALIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="finit_le",
        )

    _exiger_la_version(
        connexion,
        _EVENEMENT_VERSION_POUR_MISE_A_JOUR,
        {"evenement": evenement, "entite": entite},
        attendue=version_attendue,
    )

    cercle_ids: list[uuid.UUID] | None = None
    if codes_de_cercle is not None:
        cercle_ids = _resoudre_les_cercles(
            connexion,
            entite=entite,
            acteur=acteur,
            roles=roles,
            codes=codes_de_cercle,
            instant=instant,
        )

    bureau_ids: list[uuid.UUID] | None = None
    if codes_de_bureau is not None:
        bureau_ids = _resoudre_les_bureaux(
            connexion,
            entite=entite,
            acteur=acteur,
            roles=roles,
            codes=codes_de_bureau,
            instant=instant,
        )

    if cercle_ids is not None:
        connexion.execute(
            _ARCHIVER_LES_PORTEES_CERCLE,
            {"evenement": evenement, "entite": entite, "acteur": acteur, "instant": instant},
        )
        for cercle_id in cercle_ids:
            connexion.execute(
                _INSERER_LA_PORTEE_CERCLE,
                {"entite": entite, "evenement": evenement, "cercle": cercle_id, "acteur": acteur},
            )

    if bureau_ids is not None:
        connexion.execute(
            _ARCHIVER_LES_PORTEES_BUREAU,
            {"evenement": evenement, "entite": entite, "acteur": acteur, "instant": instant},
        )
        for bureau_id in bureau_ids:
            connexion.execute(
                _INSERER_LA_PORTEE_BUREAU,
                {"entite": entite, "evenement": evenement, "bureau": bureau_id, "acteur": acteur},
            )

    ligne = connexion.execute(
        _METTRE_A_JOUR_L_EVENEMENT,
        {
            "evenement": evenement,
            "entite": entite,
            "titre": title,
            "description": description,
            "commence_le": starts_at,
            "finit_le": ends_at,
            "lieu": location_text,
            "acteur": acteur,
            "instant": instant,
        },
    ).one()

    #  LOT 10, `T5` : UN SEUL `audit_event` pour l'appel entier -- « modifier
    #  un evenement » est UNE action metier, meme quand elle remplace aussi
    #  les listes de cercles/bureaux. Aucune ancienne valeur n'est portee :
    #  cette fonction ne lit jamais l'etat anterieur des champs avant de les
    #  ecraser (a la difference de `remplacer_le_contenu` au LOT 6, qui avait
    #  deja l'ancien titre sous la main pour une autre raison).
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEvenement.MODIFIER.value,
        resource_type="event",
        resource_reference=evenement,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Modification de l'evenement",
        new_values={
            "title": title,
            "description": description,
            "starts_at": str(starts_at),
            "ends_at": str(ends_at),
            "location_text": location_text,
        },
        reason=motif,
    )

    return EvenementModifie(
        identifiant=evenement,
        title=title,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        location_text=location_text,
        etat=str(ligne[1]),
        version=int(ligne[0]),
    )


def publier_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    evenement: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> EvenementModifie:
    """§11 « Publier » — un BROUILLON devient `published`, immediatement.

    L'appelant a deja prouve `ActionEvenement.PUBLIER`, qui n'est jamais offert
    hors de l'etat `draft` (`resoudre_le_perimetre_de_l_evenement`). Le verrou
    de version re-exige NEANMOINS l'etat ici : les deux lectures sont deux
    instants distincts, et un evenement publie entre-temps par un autre
    porteur du meme droit ne doit pas l'etre une seconde fois.
    """
    _exiger_la_version(
        connexion,
        _EVENEMENT_VERSION_POUR_PUBLICATION,
        {"evenement": evenement, "entite": entite, "etat_attendu": EtatEvenement.DRAFT.value},
        attendue=version_attendue,
    )
    ligne = connexion.execute(
        text(
            """
            UPDATE event
               SET state = :etat, updated_at = :instant, updated_by_person_id = :acteur,
                   version = version + 1
             WHERE id = :evenement AND entity_id = :entite
            RETURNING id, title, description, starts_at, ends_at, location_text, version, state
            """
        ),
        {
            "evenement": evenement,
            "entite": entite,
            "etat": EtatEvenement.PUBLISHED.value,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()

    #  LOT 10, `T5` : `ActionEvenement.PUBLIER` est deja le vocabulaire du
    #  perimetre (§7.27), reutilise tel quel comme `action_code`.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEvenement.PUBLIER.value,
        resource_type="event",
        resource_reference=evenement,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Publication de l'evenement",
        reason=motif,
    )

    return EvenementModifie(
        identifiant=ligne[0],
        title=ligne[1],
        description=ligne[2],
        starts_at=ligne[3],
        ends_at=ligne[4],
        location_text=ligne[5],
        etat=str(ligne[7]),
        version=int(ligne[6]),
    )


# ===========================================================================
#
#  ANNULER, ARCHIVER ET RESTAURER — matrice §11, LOT 8, `T5`,
#  `MVP-L08-US004` (3 sur 3)
#
# ===========================================================================


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementAnnule:
    """Ce que l'annulation a produit — l'evenement reste visible, badge « Annule »."""

    version: int
    etat: str
    annule_le: dt.datetime
    motif_d_annulation: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementArchive:
    """Ce que l'archivage a produit — l'evenement quitte la consultation publique."""

    version: int
    etat: str
    archive_le: dt.datetime


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementRestaure:
    """Ce que la restauration a produit — l'evenement revient en BROUILLON."""

    version: int
    etat: str


#  `_EVENEMENT_VERSION_POUR_MISE_A_JOUR` sert deja l'archivage : aucune
#  precondition d'etat au-dela de « pas deja archive ». Annuler et restaurer
#  exigent chacun un etat precis, donc deux requetes de plus.
_EVENEMENT_VERSION_POUR_ANNULATION: Final = text(
    "SELECT version FROM event WHERE id = :evenement AND entity_id = :entite "
    "AND archived_at IS NULL AND state = :etat_attendu FOR UPDATE"
)
_EVENEMENT_VERSION_POUR_RESTAURATION: Final = text(
    "SELECT version FROM event WHERE id = :evenement AND entity_id = :entite "
    "AND archived_at IS NOT NULL FOR UPDATE"
)

_ANNULER: Final = text(
    """
    UPDATE event
       SET state = :etat, cancelled_at = :instant, cancellation_reason = :motif,
           updated_at = :instant, updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :evenement AND entity_id = :entite
    RETURNING version, state, cancelled_at, cancellation_reason
    """
)

#  `cancelled_at`/`cancellation_reason` ne sont PAS touches : un evenement
#  archive depuis `cancelled` garde le fait qu'il a ete annule, meme parti
#  que `published_at` conserve a l'archivage d'une page (LOT 6, `T7`).
_ARCHIVER: Final = text(
    """
    UPDATE event
       SET state = :etat, archived_at = :instant, archived_by_person_id = :acteur,
           updated_at = :instant, updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :evenement AND entity_id = :entite
    RETURNING version, state, archived_at
    """
)

#  La restauration rend TOUJOURS `draft`, jamais l'etat anterieur a
#  l'archivage : voir l'en-tete de ce module.
_RESTAURER: Final = text(
    """
    UPDATE event
       SET state = :etat, archived_at = NULL, archived_by_person_id = NULL,
           updated_at = :instant, updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :evenement AND entity_id = :entite
    RETURNING version, state
    """
)


def annuler_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    evenement: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    motif: str | None,
    instant: dt.datetime,
) -> EvenementAnnule:
    """§11 « Annuler » — un PUBLIE devient `cancelled`, et reste visible (badge).

    L'appelant a deja prouve `ActionEvenement.ANNULER`, qui n'est jamais
    offert hors de l'etat `published` (`resoudre_le_perimetre_de_l_evenement`).
    Le verrou de version re-exige NEANMOINS l'etat ici, deux instants
    distincts — meme discipline que `publier_un_evenement`.
    """
    _exiger_la_version(
        connexion,
        _EVENEMENT_VERSION_POUR_ANNULATION,
        {
            "evenement": evenement,
            "entite": entite,
            "etat_attendu": EtatEvenement.PUBLISHED.value,
        },
        attendue=version_attendue,
    )
    ligne = connexion.execute(
        _ANNULER,
        {
            "evenement": evenement,
            "entite": entite,
            "etat": EtatEvenement.CANCELLED.value,
            "motif": motif,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()

    #  LOT 10, `T5` : meme reutilisation de `ActionEvenement`. `motif` est le
    #  seul champ de ce module qui corresponde a un vrai motif humain -- porte
    #  dans `reason`, jamais dans `summary`, meme discipline que `raison` pour
    #  la revocation de session (LOT 3) ou `motif` pour la categorie DG (LOT 2).
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEvenement.ANNULER.value,
        resource_type="event",
        resource_reference=evenement,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Annulation de l'evenement",
        reason=motif,
    )

    return EvenementAnnule(
        version=int(ligne[0]),
        etat=str(ligne[1]),
        annule_le=ligne[2],
        motif_d_annulation=ligne[3],
    )


def archiver_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    evenement: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> EvenementArchive:
    """§11 « Archiver » — brouillon, publie ou annule devient `archived`.

    L'appelant a deja prouve `ActionEvenement.ARCHIVER`. Le §18.1 n'en fait
    pas un cas obligatoire pour cette ressource EN GENERAL — mais LOT 10
    `T7` (`ECART-064`) exige un motif quand l'acteur est `SUPER`, verifie a
    la ROUTE, qui connait deja les roles.
    """
    _exiger_la_version(
        connexion,
        _EVENEMENT_VERSION_POUR_MISE_A_JOUR,
        {"evenement": evenement, "entite": entite},
        attendue=version_attendue,
    )
    ligne = connexion.execute(
        _ARCHIVER,
        {
            "evenement": evenement,
            "entite": entite,
            "etat": EtatEvenement.ARCHIVED.value,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()

    #  LOT 10, `T5`/`T7` : meme reutilisation. `reason` ne porte que le motif
    #  de `SUPER` quand il est fourni — `ECART-064`.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEvenement.ARCHIVER.value,
        resource_type="event",
        resource_reference=evenement,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Archivage de l'evenement",
        reason=motif,
    )

    return EvenementArchive(version=int(ligne[0]), etat=str(ligne[1]), archive_le=ligne[2])


def restaurer_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    evenement: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> EvenementRestaure:
    """§11 « Restaurer » — un ARCHIVE revient en `draft`, jamais en `published`.

    L'appelant a deja prouve `ActionEvenement.RESTAURER`, offert aux seuls
    `ROLES_DE_PORTEE_ENTITE` (`ARB-DROIT-003`). DSM/BOOST/OFFICE n'atteignent
    jamais ce code : leur refus est pose par le perimetre, en 403, avant lui.
    """
    _exiger_la_version(
        connexion,
        _EVENEMENT_VERSION_POUR_RESTAURATION,
        {"evenement": evenement, "entite": entite},
        attendue=version_attendue,
    )
    ligne = connexion.execute(
        _RESTAURER,
        {
            "evenement": evenement,
            "entite": entite,
            "etat": EtatEvenement.DRAFT.value,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()

    #  LOT 10, `T5` : meme reutilisation, pour l'action symetrique.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEvenement.RESTAURER.value,
        resource_type="event",
        resource_reference=evenement,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Restauration de l'evenement",
        reason=motif,
    )

    return EvenementRestaure(version=int(ligne[0]), etat=str(ligne[1]))


# ===========================================================================
#
#  GERER LES MEDIAS — matrice §11 « Ajouter une image ou vidéo », LOT 8,
#  `T6`
#
# ===========================================================================


@dataclasses.dataclass(frozen=True, slots=True)
class MediaDEvenement:
    """Un media rattache, dans l'ordre d'affichage."""

    media_asset_id: uuid.UUID
    role: str
    ordre: int


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementMediasRemplaces:
    """Ce que le remplacement de la liste a produit."""

    version: int
    medias: list[MediaDEvenement]


#  Le media nomme existe-t-il, NON ARCHIVE, dans CETTE entite, et dans l'etat
#  `ready` ? Le couple `(id, entity_id)` porte l'isolation (§25.3) — resoudre
#  par l'identifiant seul rattacherait un media d'une AUTRE entite a cet
#  evenement, ce que la cle composite de `event_media` refuserait ensuite en
#  500 (§7.20 : un 422 ici, pas un 500 qui accuserait le service).
_MEDIA_PAR_ID: Final = text(
    "SELECT state FROM media_asset "
    "WHERE id = :media AND entity_id = :entite AND archived_at IS NULL"
)

_ARCHIVER_LES_MEDIAS: Final = text(
    "UPDATE event_media SET archived_at = :instant, archived_by_person_id = :acteur "
    "WHERE event_id = :evenement AND entity_id = :entite AND archived_at IS NULL"
)

_INSERER_UN_MEDIA: Final = text(
    "INSERT INTO event_media "
    "(entity_id, event_id, media_asset_id, display_order, display_role, "
    " created_by_person_id) "
    "VALUES (:entite, :evenement, :media, :ordre, :role, :acteur)"
)

#  Incremente la version de L'EVENEMENT pour un changement qui ne touche
#  aucun de ses champs propres — meme motif que `publier_un_evenement` : la
#  concurrence optimiste du §18.4 porte sur la ressource entiere, pas sur un
#  sous-ensemble de ses colonnes.
_INCREMENTER_LA_VERSION_DE_L_EVENEMENT: Final = text(
    "UPDATE event SET version = version + 1, updated_at = :instant, "
    "updated_by_person_id = :acteur WHERE id = :evenement AND entity_id = :entite "
    "RETURNING version"
)


def _resoudre_les_medias(
    connexion: Connection, *, entite: uuid.UUID, medias: list[uuid.UUID]
) -> None:
    """Verifier que CHAQUE media existe, est dans CETTE entite et `ready`.

    **AUCUN DOUBLON** : la DB ne l'interdirait pas — l'index unique porte sur
    `(event_id, display_order)`, jamais sur `media_asset_id` — mais soumettre
    deux fois le meme media dans la meme liste est une faute de l'appelant,
    meme discipline que `_verifier_l_absence_de_doublon` pour les cercles et
    bureaux.
    """
    if len({str(m) for m in medias}) != len(medias):
        raise ErreurApplicative(
            code=CODE_DOUBLON_DANS_LA_LISTE,
            message=MESSAGE_DOUBLON_DE_MEDIA,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="medias",
        )
    for media_id in medias:
        ligne = connexion.execute(
            _MEDIA_PAR_ID, {"media": media_id, "entite": entite}
        ).one_or_none()
        if ligne is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_MEDIA_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="medias",
            )
        if str(ligne[0]) != ETAT_AFFICHABLE:
            raise ErreurApplicative(
                code=CODE_MEDIA_NON_PRET,
                message=MESSAGE_MEDIA_NON_PRET,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="medias",
            )


def gerer_les_medias_d_un_evenement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    evenement: uuid.UUID,
    version_attendue: int,
    medias: list[tuple[uuid.UUID, str]],
    instant: dt.datetime,
    motif: str | None = None,
) -> EvenementMediasRemplaces:
    """Remplacer la liste COMPLETE des medias d'un evenement — §11.

    L'appelant a deja prouve `ActionEvenement.GERER_LES_MEDIAS`. `medias` est
    une liste de couples `(media_asset_id, role)` — jamais `None` pour cette
    route, qui n'a qu'une seule dimension, contrairement aux cercles/bureaux
    de `modifier_un_evenement` : une liste VIDE vide la galerie, c'est la
    seule forme de ce geste.

    `display_order` vaut l'INDEX du couple dans la liste soumise, jamais un
    decalage calcule sur le nombre de lignes vivantes — meme lecon que
    `T8-1` au LOT 6 : archiver TOUTES les lignes avant de reinserer rend les
    rangs `0..n-1` CONTIGUS par construction, sans jamais les calculer.
    """
    _exiger_la_version(
        connexion,
        _EVENEMENT_VERSION_POUR_MISE_A_JOUR,
        {"evenement": evenement, "entite": entite},
        attendue=version_attendue,
    )
    _resoudre_les_medias(connexion, entite=entite, medias=[m for m, _ in medias])

    connexion.execute(
        _ARCHIVER_LES_MEDIAS,
        {"evenement": evenement, "entite": entite, "acteur": acteur, "instant": instant},
    )
    for ordre, (media_id, role) in enumerate(medias):
        connexion.execute(
            _INSERER_UN_MEDIA,
            {
                "entite": entite,
                "evenement": evenement,
                "media": media_id,
                "ordre": ordre,
                "role": role,
                "acteur": acteur,
            },
        )

    version = connexion.execute(
        _INCREMENTER_LA_VERSION_DE_L_EVENEMENT,
        {"evenement": evenement, "entite": entite, "instant": instant, "acteur": acteur},
    ).scalar_one()

    #  LOT 10, `T5` : UN SEUL `audit_event` pour l'appel entier -- « remplacer
    #  la liste des medias » est UNE action metier, meme discipline que
    #  `reordonner_les_liens` au LOT 6 : jamais un evenement par media. Aucune
    #  liste vide ne court-circuite cette fonction avant l'ecriture (a la
    #  difference de `reordonner_les_liens`) : une galerie VIDEE est une forme
    #  normale de ce geste, donc un `audit_event` est ecrit meme sur `medias=[]`.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEvenement.GERER_LES_MEDIAS.value,
        resource_type="event",
        resource_reference=evenement,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Remplacement des medias de l'evenement ({len(medias)} media(s))",
        new_values={
            "medias": [{"media_asset_id": str(media_id), "role": role} for media_id, role in medias]
        },
        reason=motif,
    )

    return EvenementMediasRemplaces(
        version=int(version),
        medias=[
            MediaDEvenement(media_asset_id=media_id, role=role, ordre=ordre)
            for ordre, (media_id, role) in enumerate(medias)
        ],
    )
