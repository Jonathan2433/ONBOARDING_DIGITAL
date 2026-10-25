"""Consulter et traiter un signalement — matrice §17, cahier §9.6, `T12`.

LOT 10, sous-étape `T12`, story `MVP-L10-US006`.

CE QUE LE BACKLOG DEMANDE, ET CE QUE LE SCHÉMA PORTE DÉJÀ

  `US006` : « États nouveau, en analyse, corrigé et rejeté ; compteur
  back-office ; commentaires et historique. » Les quatre états existent
  depuis `T1` (`EtatSignalement`, `app.audit.modeles`) — rien à ajouter. Le
  « compteur back-office » est la pagination du §18.2 elle-même : une liste
  filtrée par état rend déjà son `total`, jamais une route séparée qui
  pourrait diverger du compte réel (§7.27).

  « Commentaires et historique » n'a PAS de table dédiée : `alert_comment`
  (modèle §21.3) est FK'ée à `operational_alert_id` SEULE — « commentaires
  d'acquittement et de résolution » d'une ALERTE, jamais d'un signalement.
  Construire une seconde table de commentaires pour `bug_report` inventerait
  une capacité que le §17 ne nomme nulle part comme une ligne séparée : à la
  différence des alertes, qui portent DEUX verbes distincts (« Acquitter » et
  « Résoudre ou commenter une alerte », `T13`), les signalements n'en portent
  qu'UN SEUL — « Modifier l'état d'un signalement ». Pas de ligne « commenter
  sans changer l'état ».

  **RÉUTILISÉ PLUTÔT QU'INVENTÉ** : chaque changement d'état écrit un
  `audit_event` via le service générique de `T2`
  (`app.audit.services.enregistrer_un_evenement`), avec le commentaire porté
  dans `reason` — même discipline que « le motif de réouverture porté dans
  `reason` » (`T6`) et « le motif d'annulation porté dans `reason` » (`T5`).
  « Historique » devient alors la SUITE de ces événements pour CE
  signalement, jamais une seconde table : un commentaire ET son horodatage
  voyagent ensemble, par construction.

POURQUOI L'HISTORIQUE N'EST PAS SERVI PAR `GET /entities/{code}/audit`

  `app.audit.lecture.FiltresDAudit` n'a pas d'axe `resource_reference` (un
  seul `resource_type`, jamais un identifiant précis) — et même s'il en avait
  un, la garde de cette route est `ROLES_DE_L_AUDIT` (matrice §16, six rôles,
  axes Consultants/Cercle/Bureau), un périmètre ENTIÈREMENT DIFFÉRENT de
  celui du support (`PerimetreDesSignalements`, §17). Un DSM a un périmètre
  `Consultants` sur l'audit mais seulement `Soi` sur les signalements : le
  servir par la route d'audit violerait le critère de sortie 3 du lot — « les
  rapports respectent les mêmes droits que les écrans source ». L'historique
  d'un signalement est donc une lecture DÉDIÉE, qui interroge `audit_event`
  directement (même table, même colonnes) mais vérifie le périmètre DU
  SUPPORT, jamais celui de l'audit.

`SUPER` ET LE MOTIF OBLIGATOIRE — `ECART-064` S'APPLIQUE, PAS RETROFITÉ

  `T7` a retrofité le motif obligatoire (`app.audit.motif`) sur la totalité
  des fonctions câblées par `T2` à `T6`, portée large explicitement validée
  par Jonathan — mais la règle qu'il ferme (`ECART-064`, cahier §18.1,
  `RIGHTS-017`) est désormais une règle PERMANENTE du projet : « un motif est
  obligatoire pour toute intervention du super-administrateur dans une
  entité », pas seulement pour les ~25 fonctions nommées à l'époque. «
  Modifier l'état d'un signalement » est la PREMIÈRE fonction de `T8` à `T16`
  qui porte une grille Entité/Global où `SUPER` agit DANS une entité
  particulière (lectures de `T8`/`T9`/`T10` exemptées, §18.1 bornant
  l'obligation aux écritures ; `T11` exemptée, aucune garde de rôle) — elle
  applique donc la même règle, avec le même mécanisme
  (`exiger_un_motif_si_necessaire`). Le champ `commentaire` du corps sert les
  DEUX : le commentaire métier du backlog, ET le motif du §18.1 quand `SUPER`
  autorise l'appel — un seul champ, jamais deux redondants.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any, Final

from fastapi import status
from sqlalchemy import text

from app.audit.services import enregistrer_un_evenement
from app.shared.errors import ErreurApplicative
from app.support.perimetre import PerimetreDesSignalements

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

CODE_SIGNALEMENT_INTROUVABLE: Final = "signalement_introuvable"
MESSAGE_SIGNALEMENT_INTROUVABLE: Final = (
    "Aucun signalement ne correspond a cet identifiant dans ce perimetre."
)

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "la version lue est perimee — cahier §18.4, aucun ecrasement silencieux"
)

#  Litteral : `bug_report` n'a aucune enum `ActionXxx` existante (a la
#  difference d'`ActionEditoriale`/`ActionEvenement`), meme situation que
#  `cercle_archive` au LOT 9 `T3`.
_ACTION_CODE_ETAT_MODIFIE: Final = "etat_de_signalement_modifie"
_RESOURCE_TYPE_BUG_REPORT: Final = "bug_report"


@dataclasses.dataclass(frozen=True, slots=True)
class LigneDeSignalement:
    """Une ligne de `bug_report` — modele §21.4.

    Les quatre champs techniques sont `None` pour qui n'a que la « Lecture
    fonctionnelle » (voir `app.support.perimetre.a_la_lecture_complete`) —
    jamais une absence de colonne, un masquage selon le perimetre resolu,
    meme discipline qu'`EvenementDAudit` (`T8`).
    """

    id: uuid.UUID
    state: str
    description: str
    reproduction_steps: str | None
    page_path: str
    entity_id: uuid.UUID
    reported_by_person_id: uuid.UUID
    created_at: dt.datetime
    version: int
    application_version: str | None
    environment: str | None
    browser_summary: str | None
    correlation_token: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class PageDeSignalements:
    """Une page de signalements, et le total de la population — le
    « compteur back-office » du backlog, jamais une route separee."""

    signalements: list[LigneDeSignalement]
    total: int


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementDHistoriqueDeSignalement:
    """Une ligne d'`audit_event` pour CE signalement — modele §21.1."""

    occurred_at: dt.datetime
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    reason: str | None
    actor_person_id: uuid.UUID | None


@dataclasses.dataclass(frozen=True, slots=True)
class SignalementModifie:
    """Ce que le changement d'etat a produit."""

    state: str
    version: int


_CLAUSE_SOI: Final[str] = "reported_by_person_id = :acteur"
_CLAUSE_ENTITE: Final[str] = "TRUE"

_CLAUSES_PAR_PERIMETRE: Final[dict[PerimetreDesSignalements, str]] = {
    PerimetreDesSignalements.GLOBAL: _CLAUSE_ENTITE,
    PerimetreDesSignalements.ENTITE_COMPLETE: _CLAUSE_ENTITE,
    PerimetreDesSignalements.ENTITE_FONCTIONNELLE: _CLAUSE_ENTITE,
    PerimetreDesSignalements.SOI: _CLAUSE_SOI,
}

_BASE_SOURCE: Final[str] = "FROM bug_report WHERE entity_id = :entite"


def lister_les_signalements(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDesSignalements,
    avec_lecture_complete: bool,
    filtre_etat: str | None,
    page: int,
    taille: int,
) -> PageDeSignalements:
    """La page demandee de signalements dans la portee resolue, et le total.

    `perimetre`/`avec_lecture_complete` sont DEJA resolus par l'appelant
    (`resoudre_le_perimetre_des_signalements`/`a_la_lecture_complete`) — ce
    module ne decide jamais qui voit quoi, meme discipline que `app.onboarding.suivi`.
    """
    clause = _CLAUSES_PAR_PERIMETRE[perimetre]
    source = f"{_BASE_SOURCE} AND ({clause})"
    parametres: dict[str, object] = {"entite": entite, "acteur": acteur}
    if filtre_etat is not None:
        source += " AND state = :etat"
        parametres["etat"] = filtre_etat

    total = int(connexion.execute(text(f"SELECT count(*) {source}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                "SELECT id, state, description, reproduction_steps, page_path, "
                "entity_id, reported_by_person_id, created_at, version, "
                "application_version, environment, browser_summary, correlation_token "
                f"{source} "
                "ORDER BY created_at DESC, id ASC "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )
    return PageDeSignalements(
        signalements=[
            _en_ligne(ligne, avec_lecture_complete=avec_lecture_complete) for ligne in lignes
        ],
        total=total,
    )


def _en_ligne(ligne: Any, *, avec_lecture_complete: bool) -> LigneDeSignalement:
    return LigneDeSignalement(
        id=ligne["id"],
        state=ligne["state"],
        description=ligne["description"],
        reproduction_steps=ligne["reproduction_steps"],
        page_path=ligne["page_path"],
        entity_id=ligne["entity_id"],
        reported_by_person_id=ligne["reported_by_person_id"],
        created_at=ligne["created_at"],
        version=ligne["version"],
        application_version=ligne["application_version"] if avec_lecture_complete else None,
        environment=ligne["environment"] if avec_lecture_complete else None,
        browser_summary=ligne["browser_summary"] if avec_lecture_complete else None,
        correlation_token=ligne["correlation_token"] if avec_lecture_complete else None,
    )


_SIGNALEMENT_VISIBLE: Final = text(
    "SELECT 1 FROM bug_report WHERE id = :signalement AND entity_id = :entite "
    "AND (CASE WHEN :soi_seul THEN reported_by_person_id = :acteur ELSE TRUE END)"
)


def signalement_visible(
    connexion: Connection,
    *,
    signalement: uuid.UUID,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDesSignalements,
) -> bool:
    """Ce signalement est-il dans la portee resolue de cet appelant ?

    Utilisee par l'historique ET par le changement d'etat, pour que les deux
    routes appliquent EXACTEMENT la meme regle de visibilite — jamais deux
    verifications qui pourraient diverger (§7.27).
    """
    ligne = connexion.execute(
        _SIGNALEMENT_VISIBLE,
        {
            "signalement": signalement,
            "entite": entite,
            "acteur": acteur,
            "soi_seul": perimetre is PerimetreDesSignalements.SOI,
        },
    ).first()
    return ligne is not None


_HISTORIQUE_D_UN_SIGNALEMENT: Final = text(
    "SELECT occurred_at, old_values, new_values, reason, actor_person_id "
    "FROM audit_event "
    "WHERE resource_type = :type_ressource AND resource_reference = :signalement "
    "ORDER BY occurred_at DESC, id ASC"
)


def lire_l_historique_d_un_signalement(
    connexion: Connection, *, signalement: uuid.UUID
) -> list[EvenementDHistoriqueDeSignalement]:
    """L'historique complet d'un signalement — la suite de ses `audit_event`.

    **AUCUNE VERIFICATION DE PERIMETRE ICI** : l'appelant doit avoir deja
    appele `signalement_visible` — meme separation que `lister_le_journal_d_
    audit`/`resoudre_le_perimetre_de_l_audit` (`T8`).
    """
    lignes = (
        connexion.execute(
            _HISTORIQUE_D_UN_SIGNALEMENT,
            {"type_ressource": _RESOURCE_TYPE_BUG_REPORT, "signalement": signalement},
        )
        .mappings()
        .all()
    )
    return [
        EvenementDHistoriqueDeSignalement(
            occurred_at=ligne["occurred_at"],
            old_values=ligne["old_values"],
            new_values=ligne["new_values"],
            reason=ligne["reason"],
            actor_person_id=ligne["actor_person_id"],
        )
        for ligne in lignes
    ]


_SIGNALEMENT_A_MODIFIER: Final = text(
    "SELECT state, version FROM bug_report "
    "WHERE id = :signalement AND entity_id = :entite FOR UPDATE"
)

_MODIFIER_L_ETAT: Final = text(
    "UPDATE bug_report "
    "SET state = :nouvel_etat, updated_at = :instant, updated_by_person_id = :acteur, "
    "    version = version + 1 "
    "WHERE id = :signalement AND entity_id = :entite "
    "RETURNING state, version"
)


def modifier_l_etat_d_un_signalement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    signalement: uuid.UUID,
    nouvel_etat: str,
    version_attendue: int,
    commentaire: str | None,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> SignalementModifie:
    """§17 « Modifier l'etat d'un signalement | Entite | Global ».

    Aucune transition n'est restreinte : le corpus ne porte aucun diagramme
    d'etat pour `bug_report` (a la difference de l'onboarding, §24.2) —
    inventer un graphe de transitions serait §6.5. Les quatre etats restent
    donc TOUS atteignables depuis n'importe lequel des quatre.

    `nouvel_etat` est deja valide par l'appelant (Pydantic, contre
    `ETATS_SIGNALEMENT`) avant d'atteindre ce service — jamais revalide ici,
    meme confiance qu'`archiver_un_cercle` envers son `action_code`.
    """
    ligne = connexion.execute(
        _SIGNALEMENT_A_MODIFIER, {"signalement": signalement, "entite": entite}
    ).one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_SIGNALEMENT_INTROUVABLE,
            message=MESSAGE_SIGNALEMENT_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    ancien_etat, version_actuelle = ligne
    if version_actuelle != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
            details={"version_actuelle": version_actuelle},
        )

    resultat = connexion.execute(
        _MODIFIER_L_ETAT,
        {
            "signalement": signalement,
            "entite": entite,
            "nouvel_etat": nouvel_etat,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_ETAT_MODIFIE,
        resource_type=_RESOURCE_TYPE_BUG_REPORT,
        resource_reference=signalement,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Changement d'etat d'un signalement",
        old_values={"state": ancien_etat},
        new_values={"state": resultat.state},
        reason=commentaire,
    )
    return SignalementModifie(state=resultat.state, version=resultat.version)
