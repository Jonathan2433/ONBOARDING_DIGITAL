"""Ouvrir, acquitter, commenter et résoudre une alerte opérationnelle — `T13`.

LOT 10, sous-étape `T13`, story `MVP-L10-US007`.

LE CYCLE DU §27.5, ET CE QUE LE MODÈLE EN RETIENT RÉELLEMENT

  Le cahier §27.5 décrit le cycle en prose : « ouverte ; acquittée ;
  commentée ; résolue ; rouverte automatiquement en cas de récidive. » Mais
  `operational_alert.state` (modèle §21.2, `T1`) ne ferme que TROIS valeurs —
  `open`, `acknowledged`, `resolved` — jamais un quatrième état « commentée » :
  commenter n'est donc PAS une transition d'état, c'est une action
  INDÉPENDANTE, superposable à n'importe lequel des trois états réels. C'est
  cette lecture, et non le prose du §27.5 pris à la lettre, qui gouverne ce
  module.

  **Deux transitions sont restreintes, une ne l'est pas** :

    - « Acquitter » n'est offert que depuis `open` — acquitter une alerte
      déjà résolue ou déjà acquittée n'a pas de sens opérationnel, et le
      §27.5 nomme l'acquittement comme précédant la résolution, jamais
      l'inverse ;
    - « Résoudre » est offert depuis `open` OU `acknowledged` — rien n'exige
      l'acquittement préalable (aucun diagramme d'état n'existe pour cette
      table, inventer une restriction au-delà de ce que les noms d'état
      portent eux-mêmes serait §6.5) ; seule une alerte déjà résolue refuse ;
    - « Commenter » n'a AUCUNE précondition d'état : une note d'investigation
      est utile à tout moment du cycle, y compris après résolution (suivi
      a posteriori).

  Ni l'une ni l'autre restriction n'est un diagramme inventé : elles tiennent
  au SENS des trois noms d'état eux-mêmes (`T12` a laissé `bug_report`
  totalement libre parce qu'aucun de ses quatre états ne porte un sens
  temporel aussi contraint que « acquittée avant résolue »).

« COMMENTAIRES » A UNE VRAIE TABLE — JAMAIS `audit_event.reason`

  À la différence du signalement (`T12`, qui réutilise `audit_event.reason`
  faute de table dédiée), `alert_comment` (modèle §21.3) EXISTE et est FK'ée à
  `operational_alert_id` : le §17 porte ici DEUX verbes distincts
  (« Acquitter » et « Résoudre ou commenter »), jamais un seul comme pour les
  signalements. Chaque commentaire vit UNE SEULE FOIS, dans `alert_comment`
  — jamais dupliqué dans `audit_event.reason`, ce qui créerait deux sources
  pour la même donnée, divergentes au premier correctif (§7.27). `audit_event`
  reste le journal des TRANSITIONS D'ÉTAT (qui, quand, quel changement),
  `alert_comment` le journal des NOTES (qui, quand, quel texte) — deux
  natures, jamais mélangées.

`lever_une_alerte` N'A AUCUNE ROUTE HTTP, ET C'EST DÉLIBÉRÉ

  Le §17 ne nomme AUCUNE ligne « Ouvrir une alerte » : l'ouverture (et sa
  réouverture automatique en cas de récidive) vient du système de
  supervision (Uptime Kuma, LOT 13) ou du code applicatif qui détecte une
  condition (disque, sauvegarde, e-mail) — jamais d'un geste humain via
  l'API. Construire une route que la matrice ne nomme pas inventerait un
  droit que personne n'a demandé. `lever_une_alerte` est donc une fonction de
  SERVICE pure, exercée directement par les tests et réservée au câblage
  futur — même nature que les fonctions internes non câblées à une route
  propre du LOT 9 (`_accorder_les_responsabilites`, etc., `T7`).

  **Réouverture = la MÊME ligne repasse à `open`, jamais une seconde** (le
  modèle l'exige par son index unique sur `fingerprint`, voir
  `app/audit/modeles.py`). Les horodatages `acknowledged_at`/`resolved_at`
  du cycle PRÉCÉDENT sont remis à `NULL` : ils décrivaient un cycle
  désormais clos, les garder laisserait croire qu'ils décrivent le cycle
  courant. L'historique complet n'est pas perdu : `audit_event` porte
  l'ancien état avant chaque transition, réouverture comprise.

`assigned_to_person_id` EST UN PARAMÈTRE, JAMAIS UNE VALEUR CÂBLÉE EN DUR

  Le backlog dit « Jonathan est affecté par défaut en local » — un fait
  d'EXPLOITATION (qui reçoit les alertes dans CET environnement), pas une
  règle de ce service générique. Câbler un e-mail ou un identifiant en dur
  dans une fonction de domaine mélangerait une identité d'environnement avec
  une logique métier réutilisable — l'assignation par défaut reste une
  décision du CÂBLAGE futur (LOT 13), qui connaîtra la configuration réelle.

AUCUN MOTIF OBLIGATOIRE, AUCUNE GARDE DE RÔLE ICI

  Les deux sont déjà résolues par l'appelant : `app/support/perimetre_
  alertes.py` explique pourquoi `ECART-064` ne s'applique jamais à une
  ressource globale, et les routes (`app/support/routes.py`) portent la garde
  de rôle AVANT d'appeler ce module — même séparation que `app.support.
  traitement`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any, Final

from fastapi import status
from sqlalchemy import text

from app.audit.modeles import EtatAlerte
from app.audit.services import enregistrer_un_evenement
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

CODE_ALERTE_INTROUVABLE: Final = "alerte_introuvable"
MESSAGE_ALERTE_INTROUVABLE: Final = "Aucune alerte ne correspond a cet identifiant."

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "la version lue est perimee — cahier §18.4, aucun ecrasement silencieux"
)

CODE_TRANSITION_INVALIDE: Final = "transition_invalide"
MESSAGE_TRANSITION_INVALIDE: Final = (
    "Cette alerte ne peut pas recevoir cette action dans son etat actuel."
)

_ACTION_CODE_ALERTE_LEVEE: Final = "alerte_levee"
_ACTION_CODE_ALERTE_ROUVERTE: Final = "alerte_rouverte"
_ACTION_CODE_ALERTE_ACQUITTEE: Final = "alerte_acquittee"
_ACTION_CODE_ALERTE_COMMENTEE: Final = "alerte_commentee"
_ACTION_CODE_ALERTE_RESOLUE: Final = "alerte_resolue"
_RESOURCE_TYPE_ALERTE: Final = "operational_alert"


@dataclasses.dataclass(frozen=True, slots=True)
class LigneDAlerte:
    """Une ligne d'`operational_alert` — modèle §21.2.

    `source`/`fingerprint` sont `None` pour qui n'a que le périmètre `LIMITE`
    (l'`ESM`) — voir `app.support.perimetre_alertes.a_la_lecture_complete`.
    """

    id: uuid.UUID
    severity: str
    source: str | None
    state: str
    assigned_to_person_id: uuid.UUID | None
    opened_at: dt.datetime
    acknowledged_at: dt.datetime | None
    resolved_at: dt.datetime | None
    fingerprint: str | None
    version: int


@dataclasses.dataclass(frozen=True, slots=True)
class PageDAlertes:
    """Une page d'alertes, et le total de la population."""

    alertes: list[LigneDAlerte]
    total: int


@dataclasses.dataclass(frozen=True, slots=True)
class CommentaireDAlerte:
    """Une ligne d'`alert_comment` — modèle §21.3."""

    id: uuid.UUID
    content: str
    created_at: dt.datetime
    created_by_person_id: uuid.UUID | None


@dataclasses.dataclass(frozen=True, slots=True)
class AlerteLevee:
    """Ce que `lever_une_alerte` a produit."""

    id: uuid.UUID
    state: str
    version: int
    reouverture: bool


@dataclasses.dataclass(frozen=True, slots=True)
class AlerteModifiee:
    """Ce qu'une transition d'etat a produit."""

    state: str
    version: int


_BASE_SOURCE: Final[str] = "FROM operational_alert"


def lister_les_alertes(
    connexion: Connection,
    *,
    avec_lecture_complete: bool,
    filtre_etat: str | None,
    page: int,
    taille: int,
) -> PageDAlertes:
    """La page demandee d'alertes, et le total — ressource GLOBALE, aucun
    filtre d'entite (voir `app/support/perimetre_alertes.py`)."""
    source = _BASE_SOURCE
    parametres: dict[str, object] = {}
    if filtre_etat is not None:
        source += " WHERE state = :etat"
        parametres["etat"] = filtre_etat

    total = int(connexion.execute(text(f"SELECT count(*) {source}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                "SELECT id, severity, source, state, assigned_to_person_id, "
                "opened_at, acknowledged_at, resolved_at, fingerprint, version "
                f"{source} "
                "ORDER BY opened_at DESC, id ASC "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )
    return PageDAlertes(
        alertes=[_en_ligne(ligne, avec_lecture_complete=avec_lecture_complete) for ligne in lignes],
        total=total,
    )


def _en_ligne(ligne: Any, *, avec_lecture_complete: bool) -> LigneDAlerte:
    return LigneDAlerte(
        id=ligne["id"],
        severity=ligne["severity"],
        source=ligne["source"] if avec_lecture_complete else None,
        state=ligne["state"],
        assigned_to_person_id=ligne["assigned_to_person_id"],
        opened_at=ligne["opened_at"],
        acknowledged_at=ligne["acknowledged_at"],
        resolved_at=ligne["resolved_at"],
        fingerprint=ligne["fingerprint"] if avec_lecture_complete else None,
        version=ligne["version"],
    )


_ALERTE_PAR_ID: Final = text(
    "SELECT id, severity, source, state, assigned_to_person_id, "
    "opened_at, acknowledged_at, resolved_at, fingerprint, version "
    "FROM operational_alert WHERE id = :alerte"
)


def lire_une_alerte(
    connexion: Connection, *, alerte: uuid.UUID, avec_lecture_complete: bool
) -> LigneDAlerte:
    """Une alerte precise — 404 si elle n'existe pas."""
    ligne = connexion.execute(_ALERTE_PAR_ID, {"alerte": alerte}).mappings().one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_ALERTE_INTROUVABLE,
            message=MESSAGE_ALERTE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    return _en_ligne(ligne, avec_lecture_complete=avec_lecture_complete)


_ALERTE_EXISTE: Final = text("SELECT 1 FROM operational_alert WHERE id = :alerte")

_COMMENTAIRES_DUNE_ALERTE: Final = text(
    "SELECT id, content, created_at, created_by_person_id FROM alert_comment "
    "WHERE operational_alert_id = :alerte ORDER BY created_at DESC, id ASC"
)


def lister_les_commentaires(
    connexion: Connection, *, alerte: uuid.UUID
) -> list[CommentaireDAlerte]:
    """Les commentaires d'une alerte, le plus recent d'abord — 404 si l'alerte n'existe pas."""
    if connexion.execute(_ALERTE_EXISTE, {"alerte": alerte}).first() is None:
        raise ErreurApplicative(
            code=CODE_ALERTE_INTROUVABLE,
            message=MESSAGE_ALERTE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    lignes = connexion.execute(_COMMENTAIRES_DUNE_ALERTE, {"alerte": alerte}).mappings().all()
    return [
        CommentaireDAlerte(
            id=ligne["id"],
            content=ligne["content"],
            created_at=ligne["created_at"],
            created_by_person_id=ligne["created_by_person_id"],
        )
        for ligne in lignes
    ]


_ALERTE_PAR_EMPREINTE: Final = text(
    "SELECT id, state, version FROM operational_alert WHERE fingerprint = :empreinte FOR UPDATE"
)

_INSERER_UNE_ALERTE: Final = text(
    "INSERT INTO operational_alert "
    "(severity, source, state, assigned_to_person_id, opened_at, fingerprint, "
    " created_at, created_by_person_id, updated_at, updated_by_person_id) "
    "VALUES (:severity, :source, 'open', :assigne, :instant, :empreinte, "
    " :instant, :acteur, :instant, :acteur) "
    "RETURNING id, version"
)

_ROUVRIR_UNE_ALERTE: Final = text(
    "UPDATE operational_alert "
    "SET state = 'open', severity = :severity, source = :source, "
    "    opened_at = :instant, acknowledged_at = NULL, resolved_at = NULL, "
    "    updated_at = :instant, updated_by_person_id = :acteur, version = version + 1 "
    "WHERE id = :alerte "
    "RETURNING version"
)


def lever_une_alerte(
    connexion: Connection,
    *,
    severity: str,
    source: str,
    fingerprint: str,
    instant: dt.datetime,
    assigned_to_person_id: uuid.UUID | None = None,
    acteur: uuid.UUID | None = None,
) -> AlerteLevee:
    """Ouvrir une alerte, ou la ROUVRIR si son empreinte existe deja — modele §21.2.

    Voir l'en-tete du module : aucune route HTTP n'appelle cette fonction.

    Si l'empreinte existe deja et que l'alerte est encore `open`, l'appel est
    un NO-OP (meme occurrence en cours, pas une recidive) : aucune ecriture.
    Si elle existe et n'est plus `open`, c'est une RECIDIVE : reouverture.
    """
    existante = connexion.execute(_ALERTE_PAR_EMPREINTE, {"empreinte": fingerprint}).one_or_none()
    if existante is None:
        resultat = connexion.execute(
            _INSERER_UNE_ALERTE,
            {
                "severity": severity,
                "source": source,
                "assigne": assigned_to_person_id,
                "instant": instant,
                "empreinte": fingerprint,
                "acteur": acteur,
            },
        ).one()
        enregistrer_un_evenement(
            connexion,
            instant=instant,
            action_code=_ACTION_CODE_ALERTE_LEVEE,
            resource_type=_RESOURCE_TYPE_ALERTE,
            resource_reference=resultat.id,
            actor_person_id=acteur,
            summary="Ouverture d'une alerte operationnelle",
            new_values={"state": EtatAlerte.OPEN.value, "severity": severity, "source": source},
        )
        return AlerteLevee(
            id=resultat.id, state=EtatAlerte.OPEN.value, version=resultat.version, reouverture=False
        )

    alerte_id, etat_actuel, version_actuelle = existante
    if etat_actuel == EtatAlerte.OPEN.value:
        return AlerteLevee(
            id=alerte_id, state=etat_actuel, version=version_actuelle, reouverture=False
        )

    resultat = connexion.execute(
        _ROUVRIR_UNE_ALERTE,
        {
            "alerte": alerte_id,
            "severity": severity,
            "source": source,
            "instant": instant,
            "acteur": acteur,
        },
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_ALERTE_ROUVERTE,
        resource_type=_RESOURCE_TYPE_ALERTE,
        resource_reference=alerte_id,
        actor_person_id=acteur,
        summary="Reouverture automatique d'une alerte recurrente",
        old_values={"state": etat_actuel},
        new_values={"state": EtatAlerte.OPEN.value},
    )
    return AlerteLevee(
        id=alerte_id, state=EtatAlerte.OPEN.value, version=resultat.version, reouverture=True
    )


_ALERTE_POUR_TRANSITION: Final = text(
    "SELECT state, version FROM operational_alert WHERE id = :alerte FOR UPDATE"
)

_ACQUITTER: Final = text(
    "UPDATE operational_alert "
    "SET state = 'acknowledged', acknowledged_at = :instant, "
    "    updated_at = :instant, updated_by_person_id = :acteur, version = version + 1 "
    "WHERE id = :alerte "
    "RETURNING state, version"
)

_RESOUDRE: Final = text(
    "UPDATE operational_alert "
    "SET state = 'resolved', resolved_at = :instant, "
    "    updated_at = :instant, updated_by_person_id = :acteur, version = version + 1 "
    "WHERE id = :alerte "
    "RETURNING state, version"
)

_INSERER_UN_COMMENTAIRE: Final = text(
    "INSERT INTO alert_comment "
    "(operational_alert_id, content, created_at, created_by_person_id, "
    " updated_at, updated_by_person_id) "
    "VALUES (:alerte, :contenu, :instant, :acteur, :instant, :acteur) "
    "RETURNING id, created_at"
)


def _lire_pour_transition(
    connexion: Connection, *, alerte: uuid.UUID, version_attendue: int
) -> str:
    ligne = connexion.execute(_ALERTE_POUR_TRANSITION, {"alerte": alerte}).one_or_none()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_ALERTE_INTROUVABLE,
            message=MESSAGE_ALERTE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    etat_actuel, version_actuelle = ligne
    if version_actuelle != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            champ="version",
            details={"version_actuelle": version_actuelle},
        )
    return str(etat_actuel)


def acquitter_une_alerte(
    connexion: Connection,
    *,
    alerte: uuid.UUID,
    version_attendue: int,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> AlerteModifiee:
    """§17 « Acquitter une alerte | Entite | Global ».

    Valide SEULEMENT depuis `open` — voir l'en-tete du module.
    """
    etat_actuel = _lire_pour_transition(connexion, alerte=alerte, version_attendue=version_attendue)
    if etat_actuel != EtatAlerte.OPEN.value:
        raise ErreurApplicative(
            code=CODE_TRANSITION_INVALIDE,
            message=MESSAGE_TRANSITION_INVALIDE,
            statut=status.HTTP_409_CONFLICT,
            champ="etat",
        )
    resultat = connexion.execute(
        _ACQUITTER, {"alerte": alerte, "instant": instant, "acteur": acteur}
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_ALERTE_ACQUITTEE,
        resource_type=_RESOURCE_TYPE_ALERTE,
        resource_reference=alerte,
        actor_person_id=acteur,
        summary="Acquittement d'une alerte",
        old_values={"state": etat_actuel},
        new_values={"state": resultat.state},
    )
    return AlerteModifiee(state=resultat.state, version=resultat.version)


def resoudre_une_alerte(
    connexion: Connection,
    *,
    alerte: uuid.UUID,
    version_attendue: int,
    commentaire: str | None,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> AlerteModifiee:
    """§17 « Resoudre ou commenter une alerte | Entite | Global ».

    Valide depuis `open` OU `acknowledged` — voir l'en-tete du module.
    `commentaire`, s'il est fourni, cree AUSSI une ligne `alert_comment` :
    le §17 FUSIONNE « Resoudre » et « commenter » dans un seul verbe, jamais
    duplique dans `audit_event.reason` (voir l'en-tete du module).
    """
    etat_actuel = _lire_pour_transition(connexion, alerte=alerte, version_attendue=version_attendue)
    if etat_actuel == EtatAlerte.RESOLVED.value:
        raise ErreurApplicative(
            code=CODE_TRANSITION_INVALIDE,
            message=MESSAGE_TRANSITION_INVALIDE,
            statut=status.HTTP_409_CONFLICT,
            champ="etat",
        )
    resultat = connexion.execute(
        _RESOUDRE, {"alerte": alerte, "instant": instant, "acteur": acteur}
    ).one()
    if commentaire:
        connexion.execute(
            _INSERER_UN_COMMENTAIRE,
            {"alerte": alerte, "contenu": commentaire, "instant": instant, "acteur": acteur},
        )
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_ALERTE_RESOLUE,
        resource_type=_RESOURCE_TYPE_ALERTE,
        resource_reference=alerte,
        actor_person_id=acteur,
        summary="Resolution d'une alerte",
        old_values={"state": etat_actuel},
        new_values={"state": resultat.state},
    )
    return AlerteModifiee(state=resultat.state, version=resultat.version)


def ajouter_un_commentaire(
    connexion: Connection,
    *,
    alerte: uuid.UUID,
    contenu: str,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> CommentaireDAlerte:
    """§17 « Resoudre ou commenter une alerte » — commenter SEUL, sans changer l'etat.

    Aucun verrou optimiste : un INSERT pur dans `alert_comment`, jamais une
    ecriture concurrente sur `operational_alert` (voir l'en-tete du module).
    """
    if connexion.execute(_ALERTE_EXISTE, {"alerte": alerte}).first() is None:
        raise ErreurApplicative(
            code=CODE_ALERTE_INTROUVABLE,
            message=MESSAGE_ALERTE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    resultat = connexion.execute(
        _INSERER_UN_COMMENTAIRE,
        {"alerte": alerte, "contenu": contenu, "instant": instant, "acteur": acteur},
    ).one()
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=_ACTION_CODE_ALERTE_COMMENTEE,
        resource_type=_RESOURCE_TYPE_ALERTE,
        resource_reference=alerte,
        actor_person_id=acteur,
        summary="Commentaire ajoute a une alerte",
    )
    return CommentaireDAlerte(
        id=resultat.id, content=contenu, created_at=resultat.created_at, created_by_person_id=acteur
    )
