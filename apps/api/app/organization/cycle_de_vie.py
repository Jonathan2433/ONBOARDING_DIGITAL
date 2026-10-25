"""Archiver et restaurer un cercle ou un bureau — matrice §10.2, §10.3, §18.

LOT 9, sous-etape `T4`, story `MVP-L09-US008` — « Les restaurations simples
suivent la matrice ; les restaurations techniques ou massives restent
reservees aux roles prevus. »

CE QUE CE MODULE FERME, ET DEPUIS QUAND C'ETAIT PROMIS

  `T3` du LOT 6 ecrivait deja, en lisant la matrice §10.2 : « Le §10.2 porte
  bien une ligne « Restaurer un cercle », donc une lecture d'archive viendra --
  et elle aura sa PROPRE route avec sa propre grille de roles, comme
  `fiche-archivee` au LOT 5. » Treize sous-etapes et trois lots plus tard,
  aucune n'avait pose cette route : `circle` et `office` portent `archived_at`
  depuis le LOT 2 (`T7`), les deux index partiels §25.1 l'EXCLUENT deja de
  toute lecture, mais rien ne l'ECRIT ni ne l'EFFACE. Mesure avant d'ecrire une
  ligne : zero occurrence de `archiver_un_cercle`, `restaurer_un_cercle`,
  `archiver_un_bureau` ou `restaurer_un_bureau` dans tout le depot.

  Ce trou n'est PAS celui de `T2`/`T3` du LOT 9 -- la restauration d'un
  COLLABORATEUR (`entity_membership`) est, elle, entierement servie depuis le
  `T8` du LOT 5 (`app.people.archivage.restaurer_un_profil`) et n'a RIEN a
  recevoir ici. `ARB-DROIT-003` nomme CINQ ressources -- profil, contenu,
  evenement, cercle, bureau -- et les trois premieres sont deja closes. Ce
  module ferme les deux dernieres.

LE MEME GABARIT QUE LE CONTENU EDITORIAL, EN PLUS SIMPLE

  `app.content.cycle_de_vie` est le patron direct : verrou optimiste du §18.4,
  deux colonnes ecrites dans le MEME `UPDATE` pour qu'elles ne puissent pas
  diverger (§7.35), traduction des refus de la base au format du §18.3. La
  difference est que `circle`/`office` n'ont PAS d'enumeration d'etat : juste
  `archived_at`/`archived_by_person_id`, nuls ou non. Deux etats, pas quatre --
  aucun `PerimetreDuCycleDeVie` n'est donc necessaire ici, a la difference du
  profil : la precondition d'etat vit entierement dans le `WHERE` de chaque
  requete.

  **AUCUN MOTIF N'EST DEMANDE**, et le §18.1 en donne la raison deja tenue par
  `T7` du LOT 6 : il enumere cinq cas ou un motif est obligatoire, et archiver
  un cercle ou un bureau n'y est pas. `archive_reason` reste NULL, comme pour
  CHAQUE route de ce depot -- `ECART-064`, LOT 10.

L'ARCHIVAGE D'UN CERCLE REFUSE S'IL A ENCORE UN MEMBRE ACTIF, ET CE N'EST PAS
UN ROLE

  Le §10.2, seul des deux, porte une condition : « Archiver un cercle | Entite,
  **si aucun membre actif** ». Elle vaut pour `ESM`, `ADM-E` ET `SUPER` sans
  distinction -- une interdiction liee a la ressource prevaut sur le cumul des
  roles (§23.2), exactement comme le 409 qui refuse d'archiver un profil deja
  archive (`T8` du LOT 5). Elle est donc verifiee ICI, dans la MEME transaction
  que le verrou optimiste, avant toute ecriture -- jamais en PostgreSQL : aucune
  des contraintes du §25 ne la porte, et l'ecrire en declencheur pour une seule
  regle non partagee serait un outil de plus pour un seul appelant. Le §10.3 ne
  porte AUCUNE condition equivalente pour un bureau -- elle n'est donc PAS
  inventee ici (§6.5).

CE QUE LA RESTAURATION PEUT REFUSER, ET POURQUOI C'EST ATTENDU

  Les deux index partiels du §25.1 -- `uq_circle_entity_id_code_non_archive`,
  `uq_office_entity_id_code_non_archive` -- liberent le CODE a l'archivage,
  exactement comme le slug d'une page (`T7` du LOT 6). Si un cercle ou un
  bureau neuf a repris ce code entre-temps, la restauration le reprendrait en
  double : la base refuse, et le 409 nomme la cause plutot que de laisser
  `IntegrityError` remonter brute.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.sql.elements import TextClause

from app.audit.services import enregistrer_un_evenement
from app.shared.errors import ErreurApplicative

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "la version lue est perimee — cahier §18.4, aucun ecrasement silencieux"
)

CODE_MEMBRES_ACTIFS: Final = "membres_actifs"
MESSAGE_MEMBRES_ACTIFS: Final = (
    "un cercle avec au moins un membre actif ne peut pas etre archive — modele §8.2"
)

CODE_CODE_DEJA_PRIS: Final = "code_deja_pris"
MESSAGE_CODE_DEJA_PRIS: Final = (
    "un autre cercle ou bureau de cette entite porte deja ce code — modele §25.1"
)


@dataclasses.dataclass(frozen=True, slots=True)
class CercleArchive:
    """Ce que l'archivage d'un cercle a produit."""

    version: int
    archive_le: dt.datetime


@dataclasses.dataclass(frozen=True, slots=True)
class CercleRestaure:
    """Ce que la restauration d'un cercle a produit — `archived_at` redevient NULL."""

    version: int


@dataclasses.dataclass(frozen=True, slots=True)
class BureauArchive:
    """Ce que l'archivage d'un bureau a produit."""

    version: int
    archive_le: dt.datetime


@dataclasses.dataclass(frozen=True, slots=True)
class BureauRestaure:
    """Ce que la restauration d'un bureau a produit — `archived_at` redevient NULL."""

    version: int


#  **`FOR UPDATE` VERROUILLE LA LIGNE JUSQU'A LA FIN DE LA TRANSACTION**, meme
#  idiome que `content.cycle_de_vie` : deux archivages simultanes se
#  serialisent, le second relit la version incrementee par le premier.
_CERCLE_A_ARCHIVER: Final = text(
    """
    SELECT version,
           EXISTS (
               SELECT 1 FROM circle_membership
                WHERE circle_id = :cercle AND ends_at IS NULL
           ) AS a_des_membres_actifs
      FROM circle
     WHERE id = :cercle AND entity_id = :entite AND archived_at IS NULL
       FOR UPDATE
    """
)

_CERCLE_A_RESTAURER: Final = text(
    """
    SELECT version FROM circle
     WHERE id = :cercle AND entity_id = :entite AND archived_at IS NOT NULL
       FOR UPDATE
    """
)

#  Les deux colonnes dans le MEME `UPDATE` : elles ne peuvent pas diverger par
#  cette API (§7.35).
_ARCHIVER_CERCLE: Final = text(
    """
    UPDATE circle
       SET archived_at = :instant,
           archived_by_person_id = :acteur,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :cercle AND entity_id = :entite
    RETURNING version, archived_at
    """
)

_RESTAURER_CERCLE: Final = text(
    """
    UPDATE circle
       SET archived_at = NULL,
           archived_by_person_id = NULL,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :cercle AND entity_id = :entite
    RETURNING version
    """
)

_BUREAU_A_ARCHIVER: Final = text(
    """
    SELECT version FROM office
     WHERE id = :bureau AND entity_id = :entite AND archived_at IS NULL
       FOR UPDATE
    """
)

_BUREAU_A_RESTAURER: Final = text(
    """
    SELECT version FROM office
     WHERE id = :bureau AND entity_id = :entite AND archived_at IS NOT NULL
       FOR UPDATE
    """
)

_ARCHIVER_BUREAU: Final = text(
    """
    UPDATE office
       SET archived_at = :instant,
           archived_by_person_id = :acteur,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :bureau AND entity_id = :entite
    RETURNING version, archived_at
    """
)

_RESTAURER_BUREAU: Final = text(
    """
    UPDATE office
       SET archived_at = NULL,
           archived_by_person_id = NULL,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :bureau AND entity_id = :entite
    RETURNING version
    """
)


def _refuser_version_obsolete(version_actuelle: int | None) -> ErreurApplicative:
    """Le meme refus pour deux causes — aucune ligne, ou une version differente.

    **DEUX CAUSES, UN SEUL CODE, ET C'EST EXACT** (meme motif que
    `content.cycle_de_vie._exiger_la_version`) : aucune ligne rendue signifie
    que la ressource a quitte l'etat attendu (deja archivee, deja active,
    inconnue, ou d'une autre entite) ; une version differente, qu'elle a ete
    ecrite entre-temps. Les distinguer apprendrait l'etat courant d'une
    ressource a qui n'a peut-etre pas le droit de la voir (§2.5).
    """
    details = None if version_actuelle is None else {"version_actuelle": version_actuelle}
    return ErreurApplicative(
        code=CODE_VERSION_OBSOLETE,
        message=MESSAGE_VERSION_OBSOLETE,
        statut=status.HTTP_409_CONFLICT,
        champ="version",
        details=details,
    )


def _traduire_un_refus_de_la_base(
    erreur: IntegrityError | DataError, *, contrainte_code: str
) -> ErreurApplicative:
    """Traduire un refus du schema au format du §18.3.

    **LE NOM DE LA CONTRAINTE EST LE DISCRIMINANT**, jamais le texte du message
    -- `diag.constraint_name`, une donnee structuree du protocole PostgreSQL,
    meme parti que `content._traduire_un_refus_de_la_base`.

    **CE QUI N'EST PAS RECONNU REMONTE.** Un 500 bruyant vaut mieux qu'un 409
    qui accuserait l'appelant d'une faute qu'il n'a pas commise (§7.20).
    """
    cause = erreur.orig
    diagnostic = getattr(cause, "diag", None)
    contrainte = str(getattr(diagnostic, "constraint_name", "") or "")
    if contrainte == contrainte_code:
        return ErreurApplicative(
            code=CODE_CODE_DEJA_PRIS,
            message=MESSAGE_CODE_DEJA_PRIS,
            statut=status.HTTP_409_CONFLICT,
            champ="code",
        )
    raise erreur


def archiver_un_cercle(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cercle: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> CercleArchive:
    """§10.2 « Archiver un cercle | Entite, si aucun membre actif » et §18.

    **LA CONDITION DE RESSOURCE EST VERIFIEE AVANT TOUTE ECRITURE** : un cercle
    avec un membre actif (principal ou secondaire, peu importe) ne peut etre
    archive par AUCUN role, pas meme `SUPER`.
    """
    ligne = connexion.execute(
        _CERCLE_A_ARCHIVER, {"cercle": cercle, "entite": entite}
    ).one_or_none()
    if ligne is None:
        raise _refuser_version_obsolete(None)
    version_actuelle, a_des_membres_actifs = ligne
    if version_actuelle != version_attendue:
        raise _refuser_version_obsolete(version_actuelle)
    if a_des_membres_actifs:
        raise ErreurApplicative(
            code=CODE_MEMBRES_ACTIFS,
            message=MESSAGE_MEMBRES_ACTIFS,
            statut=status.HTTP_409_CONFLICT,
        )
    resultat = connexion.execute(
        _ARCHIVER_CERCLE,
        {"cercle": cercle, "entite": entite, "instant": instant, "acteur": acteur},
    ).one()
    #  LOT 10, `T3` : aucune enum Python ne nomme cette transition (`circle`
    #  n'a pas de machine a etats, juste `archived_at`/`archived_by_person_id`
    #  — voir l'en-tete du module) — `action_code` est donc un litteral.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="cercle_archive",
        resource_type="circle",
        resource_reference=cercle,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Archivage d'un cercle",
        reason=motif,
    )
    return CercleArchive(version=resultat[0], archive_le=resultat[1])


def restaurer_un_cercle(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    cercle: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> CercleRestaure:
    """§18 « Restaurer un cercle ou bureau | Entite, restauration fonctionnelle »."""
    _exiger_la_version(
        _CERCLE_A_RESTAURER, {"cercle": cercle, "entite": entite}, connexion, version_attendue
    )
    try:
        resultat = connexion.execute(
            _RESTAURER_CERCLE,
            {"cercle": cercle, "entite": entite, "instant": instant, "acteur": acteur},
        ).one()
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(
            erreur, contrainte_code="uq_circle_entity_id_code_non_archive"
        ) from erreur
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="cercle_restaure",
        resource_type="circle",
        resource_reference=cercle,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Restauration d'un cercle",
        reason=motif,
    )
    return CercleRestaure(version=resultat[0])


def archiver_un_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    bureau: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> BureauArchive:
    """§10.3 « Archiver un bureau | Entite » — AUCUNE condition de ressource.

    A la difference d'un cercle, le §10.3 ne porte aucune ligne « si aucun
    responsable actif » : la borne du §25.4 (un a trois responsables actifs
    LORSQU'IL EST PUBLIE) vit sur la PAGE de contenu du bureau, jamais sur le
    bureau lui-meme, et un bureau archive n'a pas besoin de zero responsable
    pour l'etre.
    """
    _exiger_la_version(
        _BUREAU_A_ARCHIVER, {"bureau": bureau, "entite": entite}, connexion, version_attendue
    )
    resultat = connexion.execute(
        _ARCHIVER_BUREAU,
        {"bureau": bureau, "entite": entite, "instant": instant, "acteur": acteur},
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="bureau_archive",
        resource_type="office",
        resource_reference=bureau,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Archivage d'un bureau",
        reason=motif,
    )
    return BureauArchive(version=resultat[0], archive_le=resultat[1])


def restaurer_un_bureau(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    bureau: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    instant: dt.datetime,
    motif: str | None = None,
) -> BureauRestaure:
    """§18 « Restaurer un cercle ou bureau | Entite, restauration fonctionnelle »."""
    _exiger_la_version(
        _BUREAU_A_RESTAURER, {"bureau": bureau, "entite": entite}, connexion, version_attendue
    )
    try:
        resultat = connexion.execute(
            _RESTAURER_BUREAU,
            {"bureau": bureau, "entite": entite, "instant": instant, "acteur": acteur},
        ).one()
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(
            erreur, contrainte_code="uq_office_entity_id_code_non_archive"
        ) from erreur
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="bureau_restaure",
        resource_type="office",
        resource_reference=bureau,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Restauration d'un bureau",
        reason=motif,
    )
    return BureauRestaure(version=resultat[0])


def _exiger_la_version(
    requete: TextClause, parametres: dict[str, object], connexion: Connection, attendue: int
) -> None:
    """Le verrou optimiste du §18.4, pour les transitions SANS condition de ressource."""
    ligne = connexion.execute(requete, parametres).one_or_none()
    if ligne is None:
        raise _refuser_version_obsolete(None)
    if ligne[0] != attendue:
        raise _refuser_version_obsolete(ligne[0])
