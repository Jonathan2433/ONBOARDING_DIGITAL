"""Une instance de parcours depuis la date d'arrivee — modele §13.5/§13.6, matrice §8.1, `T7`.

CE QUE `T7` LIVRE

  Deux gestes : affecter un parcours (matrice §8.1, « Affecter un parcours »)
  et le lire (« Consulter son parcours » / « ... d'un collaborateur »).
  Aucune nouvelle table : `onboarding_instance` et `onboarding_instance_task`
  existent depuis `T1`, jamais encore ecrites.

LE BON MODELE — ORDRE DE PRIORITE, ARBITRAGE DE JONATHAN DU 27/09/2026

  Un nouvel arrivant porte un statut cible (mission/intercontrat), un DSM et un
  cercle principal, tous VERROUILLES des sa fiche d'arrivee (matrice §6.2).
  Plusieurs modeles PUBLIES peuvent donc correspondre a son statut, a des
  niveaux differents : le sien propre (DSM), celui de son cercle (Booster),
  celui de son entite, ou le modele generique global. Le corpus ne tranche nulle
  part quel niveau prime — recherche dans la matrice, le modele et le cahier,
  rien ne le dit.

  **`DSM` > `CIRCLE` > `ENTITY` > `GLOBAL`.** Le plus specifique gagne, dans cet
  ordre : un modele DSM ou Cercle n'existe QUE pour remplacer le modele general
  pour un sous-ensemble precis de personnes — sans cette priorite, un DSM
  n'aurait jamais de raison d'en publier un (§9.1, matrice). Residuel nomme,
  non instruit ici faute d'occurrence connue : PLUSIEURS modeles publies au
  MEME niveau (deux modeles `ENTITY` pour `mission`, par exemple) departagent
  par la publication la plus RECENTE — aucune contrainte du corpus n'exclut ce
  cas, et rien n'impose non plus un ordre different.

`due_at` EST CALCULE EN BASE, JAMAIS EN PYTHON

  Meme discipline que `recent_until` (`T3`) : `reference_date + due_offset_days
  jours`, interprete a MINUIT UTC — le modele §13.4 ne donne aucune heure, et
  aucune section n'exige de fuseau local. Snapshot immediat : une fois pose,
  `due_at` ne bouge plus meme si `T6` republie une nouvelle version du modele.

UNE SEULE INSTANCE ACTIVE PAR APPARTENANCE — MODELE §13.5, UN INDEX PARTIEL

  `T1` a deja pose `uq_onboarding_instance_membership_active`. L'ecriture ici
  est un COMPARE-ET-POSE ATOMIQUE, `ON CONFLICT ... DO NOTHING RETURNING` —
  meme idiome que l'usage unique du magic link (LOT 3, `T4`) : aucune ligne
  rendue est un refus 409, sans lecture prealable qui laisserait une fenetre de
  course entre deux affectations concurrentes de la MEME appartenance.

LA PROGRESSION EST CALCULEE A CHAQUE LECTURE, JAMAIS STOCKEE

  Critere de sortie n°3 du lot (§1.2 de la fiche) : aucune colonne `progress`
  n'existe, et n'existera pas. `lire_le_parcours` compte les taches
  OBLIGATOIRES `completed` sur le total obligatoire, a chaque appel — un COUNT
  SQL, jamais une valeur ecrite. La « prochaine etape » est la tache non
  terminee dont `due_at` est le plus proche, obligatoire ou non : le modele
  §13.6 ne porte aucun `display_order` sur l'instance (contrairement au
  gabarit, §13.4), et `due_at` est la seule notion d'ordre qui lui survit.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Any, Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.shared.errors import ErreurApplicative

CODE_STATUT_INTROUVABLE: Final = "statut_professionnel_introuvable"
MESSAGE_STATUT_INTROUVABLE: Final = (
    "Aucune situation professionnelle active pour cette appartenance — modele §6.5."
)

CODE_AUCUN_MODELE_PUBLIE: Final = "aucun_modele_publie"
MESSAGE_AUCUN_MODELE_PUBLIE: Final = (
    "Aucun modele publie ne correspond a ce statut, pour cette entite, ce DSM ou ce cercle."
)

CODE_PARCOURS_DEJA_ACTIF: Final = "parcours_deja_actif"
MESSAGE_PARCOURS_DEJA_ACTIF: Final = (
    "Une instance active existe deja pour cette appartenance — modele §13.5."
)


@dataclasses.dataclass(frozen=True, slots=True)
class TacheDuParcours:
    """Une ligne de `onboarding_instance_task` — snapshot fige a l'affectation."""

    id: uuid.UUID
    task_reference_id: uuid.UUID
    title_snapshot: str
    description_snapshot: str | None
    required: bool
    due_at: dt.datetime
    state: str
    completed_at: dt.datetime | None
    reopened_at: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class Progression:
    """Comptee a chaque lecture — jamais stockee, critere de sortie n°3."""

    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


@dataclasses.dataclass(frozen=True, slots=True)
class Instance:
    """L'instance elle-meme — modele §13.5."""

    id: uuid.UUID
    template_version_id: uuid.UUID
    reference_date: dt.date
    state: str
    started_at: dt.datetime
    completed_at: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class Parcours:
    """Ce qu'une lecture (ou une affectation) rend — `None` si rien n'existe."""

    instance: Instance | None
    progression: Progression | None
    prochaine_tache: TacheDuParcours | None
    taches: tuple[TacheDuParcours, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Appartenance:
    """Ce que les routes doivent connaitre de la cible AVANT de resoudre un
    permis — `person_id` pour le raccourci `Soi`, `arrival_date` pour le
    calcul des echeances."""

    person_id: uuid.UUID
    arrival_date: dt.date


_AUCUN_PARCOURS: Final = Parcours(instance=None, progression=None, prochaine_tache=None, taches=())

_LIRE_L_APPARTENANCE: Final = """
SELECT person_id, arrival_date FROM entity_membership
WHERE id = :appartenance AND entity_id = :entite
"""

#  Meme predicat que `dsm_assignment(consultant_membership_id) UNIQUE WHERE
#  ends_at IS NULL` (modele §25.1), mais lu par PLAGE — `period @> :instant` —
#  pour la MEME raison que `_RATTACHE_A_CE_DSM` (`app/onboarding/perimetre.py`) :
#  une affectation future n'est pas encore active, ce qu'`ends_at IS NULL` seul
#  ne verifierait pas.
_DSM_ACTIF: Final = """
SELECT dsm_person_id FROM dsm_assignment
WHERE consultant_membership_id = :appartenance AND entity_id = :entite
  AND archived_at IS NULL AND period @> :instant
"""

_CERCLE_PRINCIPAL_ACTIF: Final = """
SELECT circle_id FROM circle_membership
WHERE entity_membership_id = :appartenance AND entity_id = :entite
  AND membership_type = 'principal' AND archived_at IS NULL AND period @> :instant
"""

_STATUT_ACTIF: Final = """
SELECT status FROM professional_status_assignment
WHERE entity_membership_id = :appartenance AND entity_id = :entite
  AND archived_at IS NULL AND period @> :instant
"""

#  L'ORDRE DE PRIORITE EST UN `CASE` SQL, PAS UNE BOUCLE PYTHON A QUATRE
#  REQUETES : une seule lecture rend directement LE candidat qui gagne, sans
#  fenetre entre plusieurs appels ou un modele pourrait etre archive
#  entre-temps. `:dsm`/`:cercle` a `NULL` neutralisent leurs branches
#  respectives sans garde explicite — `= NULL` n'est jamais vrai en SQL.
_VERSION_A_INSTANCIER: Final = """
SELECT v.id AS version_id, v.template_id
FROM onboarding_template AS t
JOIN onboarding_template_version AS v ON v.template_id = t.id AND v.state = 'published'
WHERE t.target_status = :statut
  AND (
        (t.scope_type = 'DSM' AND t.scope_person_id = :dsm)
     OR (t.scope_type = 'CIRCLE' AND t.scope_circle_id = :cercle)
     OR (t.scope_type = 'ENTITY' AND t.entity_id = :entite)
     OR (t.scope_type = 'GLOBAL')
  )
ORDER BY
  CASE t.scope_type
    WHEN 'DSM' THEN 4
    WHEN 'CIRCLE' THEN 3
    WHEN 'ENTITY' THEN 2
    WHEN 'GLOBAL' THEN 1
  END DESC,
  v.published_at DESC,
  v.version_number DESC
LIMIT 1
"""

_COLONNES_INSTANCE: Final = (
    "id, template_version_id, reference_date, state, started_at, completed_at"
)

#  Compare-et-pose atomique sur l'index partiel de `T1` — voir l'en-tete.
_INSERER_INSTANCE: Final = f"""
INSERT INTO onboarding_instance
    (entity_id, entity_membership_id, template_version_id, reference_date, started_at)
VALUES (:entite, :appartenance, :version, :reference_date, :instant)
ON CONFLICT (entity_membership_id) WHERE state = 'active' DO NOTHING
RETURNING {_COLONNES_INSTANCE}
"""  # noqa: S608

_LIRE_L_INSTANCE_LA_PLUS_RECENTE: Final = f"""
SELECT {_COLONNES_INSTANCE} FROM onboarding_instance
WHERE entity_membership_id = :appartenance AND entity_id = :entite
ORDER BY started_at DESC
LIMIT 1
"""  # noqa: S608

_TACHES_DE_LA_VERSION: Final = """
SELECT tt.task_reference_id, tt.required, tt.due_offset_days,
       COALESCE(tt.title_override, tr.title) AS title,
       COALESCE(tt.description_override, tr.description) AS description
FROM onboarding_template_task AS tt
JOIN onboarding_task_reference AS tr ON tr.id = tt.task_reference_id
WHERE tt.template_version_id = :version
ORDER BY tt.display_order
"""

_COLONNES_TACHE: Final = (
    "id, task_reference_id, title_snapshot, description_snapshot, required, "
    "due_at, state, completed_at, reopened_at"
)

_INSERER_TACHE_INSTANCE: Final = f"""
INSERT INTO onboarding_instance_task
    (entity_id, onboarding_instance_id, task_reference_id, title_snapshot,
     description_snapshot, required, due_at)
VALUES (
    :entite, :instance, :task_reference_id, :title, :description, :required,
    (CAST(:reference_date AS date) + (:due_offset_days || ' days')::interval) AT TIME ZONE 'UTC'
)
RETURNING {_COLONNES_TACHE}
"""  # noqa: S608

_LIRE_LES_TACHES_DE_L_INSTANCE: Final = f"""
SELECT {_COLONNES_TACHE} FROM onboarding_instance_task
WHERE onboarding_instance_id = :instance
ORDER BY due_at
"""  # noqa: S608


def _tache_depuis_la_ligne(ligne: Any) -> TacheDuParcours:
    return TacheDuParcours(
        id=uuid.UUID(str(ligne["id"])),
        task_reference_id=uuid.UUID(str(ligne["task_reference_id"])),
        title_snapshot=str(ligne["title_snapshot"]),
        description_snapshot=ligne["description_snapshot"],
        required=bool(ligne["required"]),
        due_at=ligne["due_at"],
        state=str(ligne["state"]),
        completed_at=ligne["completed_at"],
        reopened_at=ligne["reopened_at"],
    )


def _instance_depuis_la_ligne(ligne: Any) -> Instance:
    return Instance(
        id=uuid.UUID(str(ligne["id"])),
        template_version_id=uuid.UUID(str(ligne["template_version_id"])),
        reference_date=ligne["reference_date"],
        state=str(ligne["state"]),
        started_at=ligne["started_at"],
        completed_at=ligne["completed_at"],
    )


def _progression_depuis_les_taches(taches: tuple[TacheDuParcours, ...]) -> Progression:
    """Comptee sur ce qui vient d'etre LU, jamais reinterrogee — la MEME liste
    sert la progression et l'affichage, ce qui rend les deux impossibles a
    faire diverger par cette API."""
    obligatoires = [t for t in taches if t.required]
    return Progression(
        taches_obligatoires_totales=len(obligatoires),
        taches_obligatoires_terminees=sum(1 for t in obligatoires if t.state == "completed"),
    )


def _prochaine_tache(taches: tuple[TacheDuParcours, ...]) -> TacheDuParcours | None:
    """La premiere tache NI terminee ni annulee, dans l'ordre `due_at` deja
    trie par la requete — voir l'en-tete, aucun `display_order` ne survit sur
    l'instance."""
    for tache in taches:
        if tache.state not in ("completed", "cancelled"):
            return tache
    return None


def _dsm_actif(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instant: dt.datetime
) -> uuid.UUID | None:
    ligne = connexion.execute(
        text(_DSM_ACTIF), {"appartenance": appartenance, "entite": entite, "instant": instant}
    ).first()
    return None if ligne is None else uuid.UUID(str(ligne[0]))


def _cercle_principal_actif(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instant: dt.datetime
) -> uuid.UUID | None:
    ligne = connexion.execute(
        text(_CERCLE_PRINCIPAL_ACTIF),
        {"appartenance": appartenance, "entite": entite, "instant": instant},
    ).first()
    return None if ligne is None else uuid.UUID(str(ligne[0]))


def _statut_actif(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instant: dt.datetime
) -> str | None:
    ligne = connexion.execute(
        text(_STATUT_ACTIF), {"appartenance": appartenance, "entite": entite, "instant": instant}
    ).first()
    return None if ligne is None else str(ligne[0])


def lire_l_appartenance(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> Appartenance | None:
    """Sert la garde 404 unique des routes — jamais un chemin distinct pour
    « appartenance inconnue », meme discipline que `T2`/`T3` (voir l'en-tete
    de `routes.py`) — et le `person_id` dont le raccourci `Soi` a besoin."""
    ligne = (
        connexion.execute(
            text(_LIRE_L_APPARTENANCE), {"appartenance": appartenance, "entite": entite}
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        return None
    return Appartenance(
        person_id=uuid.UUID(str(ligne["person_id"])), arrival_date=ligne["arrival_date"]
    )


def _lire_les_taches(connexion: Connection, *, instance: uuid.UUID) -> tuple[TacheDuParcours, ...]:
    lignes = connexion.execute(
        text(_LIRE_LES_TACHES_DE_L_INSTANCE), {"instance": instance}
    ).mappings()
    return tuple(_tache_depuis_la_ligne(ligne) for ligne in lignes)


def lire_le_parcours(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> Parcours:
    """L'instance la plus recente de cette appartenance, ses taches et sa
    progression — `Parcours` vide si aucune instance n'existe encore, jamais
    une erreur : affecter un parcours est un geste SEPARE (§8.1)."""
    ligne = (
        connexion.execute(
            text(_LIRE_L_INSTANCE_LA_PLUS_RECENTE), {"appartenance": appartenance, "entite": entite}
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        return _AUCUN_PARCOURS
    instance = _instance_depuis_la_ligne(ligne)
    taches = _lire_les_taches(connexion, instance=instance.id)
    return Parcours(
        instance=instance,
        progression=_progression_depuis_les_taches(taches),
        prochaine_tache=_prochaine_tache(taches),
        taches=taches,
    )


def affecter_un_parcours(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    cible: Appartenance,
    instant: dt.datetime,
) -> Parcours:
    """Matrice §8.1 « Affecter un parcours » — modele §13.5/§13.4.

    `cible` est DEJA RESOLUE par l'appelant (`lire_l_appartenance`), meme
    discipline que `creer_une_version` recevant un `Modele` deja lu (`T5`) :
    le 404 « appartenance inconnue » est la garde de la ROUTE, jamais du
    service.

    Resout le statut actif, le DSM et le cercle de l'appartenance, PUIS le
    modele a instancier par la priorite DSM > CIRCLE > ENTITY > GLOBAL (voir
    l'en-tete), snapshotte ses taches, et refuse 409 sur une seconde instance
    active — l'index partiel de `T1` le garantit, cette fonction le traduit.
    """
    reference_date = cible.arrival_date

    statut = _statut_actif(connexion, entite=entite, appartenance=appartenance, instant=instant)
    if statut is None:
        raise ErreurApplicative(
            code=CODE_STATUT_INTROUVABLE,
            message=MESSAGE_STATUT_INTROUVABLE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    dsm = _dsm_actif(connexion, entite=entite, appartenance=appartenance, instant=instant)
    cercle = _cercle_principal_actif(
        connexion, entite=entite, appartenance=appartenance, instant=instant
    )

    candidate = connexion.execute(
        text(_VERSION_A_INSTANCIER),
        {"statut": statut, "dsm": dsm, "cercle": cercle, "entite": entite},
    ).first()
    if candidate is None:
        raise ErreurApplicative(
            code=CODE_AUCUN_MODELE_PUBLIE,
            message=MESSAGE_AUCUN_MODELE_PUBLIE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    version_id = uuid.UUID(str(candidate[0]))

    creee = (
        connexion.execute(
            text(_INSERER_INSTANCE),
            {
                "entite": entite,
                "appartenance": appartenance,
                "version": version_id,
                "reference_date": reference_date,
                "instant": instant,
            },
        )
        .mappings()
        .one_or_none()
    )
    if creee is None:
        raise ErreurApplicative(
            code=CODE_PARCOURS_DEJA_ACTIF,
            message=MESSAGE_PARCOURS_DEJA_ACTIF,
            statut=status.HTTP_409_CONFLICT,
        )
    instance = _instance_depuis_la_ligne(creee)

    lignes_taches = connexion.execute(
        text(_TACHES_DE_LA_VERSION), {"version": version_id}
    ).mappings()
    ecrites = []
    for ligne_tache in lignes_taches:
        ecrite = (
            connexion.execute(
                text(_INSERER_TACHE_INSTANCE),
                {
                    "entite": entite,
                    "instance": instance.id,
                    "task_reference_id": ligne_tache["task_reference_id"],
                    "title": ligne_tache["title"],
                    "description": ligne_tache["description"],
                    "required": ligne_tache["required"],
                    "reference_date": reference_date,
                    "due_offset_days": ligne_tache["due_offset_days"],
                },
            )
            .mappings()
            .one()
        )
        ecrites.append(_tache_depuis_la_ligne(ecrite))
    taches = tuple(ecrites)
    return Parcours(
        instance=instance,
        progression=_progression_depuis_les_taches(taches),
        prochaine_tache=_prochaine_tache(taches),
        taches=taches,
    )
