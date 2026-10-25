"""Le cablage de l'audit generique sur l'onboarding — LOT 10, `T6`.

Stories `MVP-L10-US001`/`US002`, modele §21.1, `ARB-DATA-005`/`§30.20`.

CE QUE CE FICHIER PROUVE, ET DANS QUEL ORDRE

  1. chacune des TREIZE fonctions d'ecriture deja posees par le LOT 7 — le
     catalogue des taches, les modeles et leurs versions, le cycle de vie
     d'une version, l'affectation d'un parcours, les trois gestes sur une
     tache, l'archivage et la restauration manuels d'un parcours — ecrit
     AUSSI une ligne `audit_event`, dans la MEME transaction ;
  2. `action_code` REUTILISE `TypeEvenementTache` (§7.27) pour les quatre
     actions du journal propre §13.7 de ce domaine (affecter, terminer,
     annuler, reouvrir une tache) — meme lecture que `TypeEvenementAuth` a
     `T2` — et n'invente un littera que pour le reste, aucune enum
     n'existant pour les modeles/versions/parcours, a la difference des
     evenements (LOT 8) ;
  3. `definir_les_taches_de_la_version` et `affecter_un_parcours` ecrivent
     UN SEUL `audit_event` pour l'appel entier, meme quand ils posent
     PLUSIEURS lignes de plus bas niveau (taches, `onboarding_task_event`
     par tache) — meme principe que `modifier_un_evenement` (`T5`) ;
  4. `definir_les_taches_de_la_version` en ecrit un MEME quand la liste
     soumise est VIDE — A LA DIFFERENCE de `reordonner_les_liens` (`T4`),
     aucun retour anticipe n'existe avant l'ecriture — meme principe que
     `gerer_les_medias_d_un_evenement` (`T5`) ;
  5. l'archivage AUTOMATIQUE d'un parcours termine (declenche par la
     completion de la derniere tache obligatoire) N'ECRIT PAS son propre
     `audit_event` — c'est une CONSEQUENCE de « terminer une tache », deja
     auditee, jamais une decision distincte de l'acteur ;
  6. le correlation token courant est repris ici aussi ;
  7. l'atomicite n'est pas qu'une affirmation : un echec survenant APRES
     l'ecriture d'un `audit_event`, dans la MEME transaction, annule aussi
     cette ecriture.

CE QUE CE FICHIER NE REPROUVE PAS

  Les regles METIER de chaque site (portees de creation, priorite DSM >
  CIRCLE > ENTITY > GLOBAL, fenetre de cinq minutes, immutabilite d'une
  version publiee) sont deja prouvees par leurs propres suites —
  `test_catalogue_des_taches.py`, `test_modeles_onboarding.py`,
  `test_cycle_de_vie_des_modeles.py`, `test_instances_onboarding.py`,
  `test_taches_onboarding.py`, `test_reouverture_onboarding.py`,
  `test_archivage_onboarding.py`. Ce fichier ne porte que ce que `T6`
  ajoute : la ligne `audit_event` elle-meme.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator, Sequence

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping

from app.audit.services import DUREE_DE_RETENTION
from app.configuration.settings import Parametres
from app.onboarding.catalogue import creer_une_tache_de_reference
from app.onboarding.cycle_de_vie import (
    archiver_une_version,
    publier_une_version,
    restaurer_une_version,
)
from app.onboarding.gabarits import (
    Modele,
    NouvelleTacheDeVersion,
    creer_un_modele,
    creer_une_version,
    definir_les_taches_de_la_version,
)
from app.onboarding.instances import (
    Appartenance,
    affecter_un_parcours,
    archiver_un_parcours_termine,
    restaurer_un_parcours,
)
from app.onboarding.modeles import TypeEvenementTache
from app.onboarding.taches import annuler_la_completion, reouvrir_une_tache, terminer_une_tache
from app.shared.correlation import definir_correlation, effacer_correlation
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 10, 19, 9, 0, tzinfo=dt.UTC)
PLUS_TARD = INSTANT + dt.timedelta(days=1)
ARRIVEE = dt.date(2026, 9, 1)
MARQUEUR = "T6L10"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion en ROLLBACK : aucun test ne laisse de ligne derriere lui."""
    _exiger_postgresql(parametres_de_la_stack)
    connexion = moteur(parametres_de_la_stack).connect()
    transaction = connexion.begin()
    try:
        yield connexion
    finally:
        transaction.rollback()
        connexion.close()


# ---------------------------------------------------------------------------
#  Le decor. Local a ce fichier, comme ceux de `T2` a `T5` : aucun test du
#  depot n'importe le decor d'un autre.
# ---------------------------------------------------------------------------


def _entite(connexion: Connection, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO entity (code, display_name, city, country_code, status, "
                    "timezone, activated_at) "
                    "VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
                    "RETURNING id"
                ),
                {"code": code, "nom": code, "ville": code},
            ).scalar_one()
        )
    )


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO person "
                    "(email, email_normalized, first_name, last_name, account_state) "
                    "VALUES (:affichage, :normalise, 'Test', 'T6L10', 'active') RETURNING id"
                ),
                {"affichage": adresse, "normalise": adresse.lower()},
            ).scalar_one()
        )
    )


def _appartenance(connexion: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'published') "
                    "RETURNING id"
                ),
                {"p": personne, "e": entite, "arrivee": ARRIVEE},
            ).scalar_one()
        )
    )


def _statut(connexion: Connection, entite: uuid.UUID, appartenance: uuid.UUID, statut: str) -> None:
    connexion.execute(
        text(
            "INSERT INTO professional_status_assignment "
            "(entity_membership_id, entity_id, status, starts_at) "
            "VALUES (:a, :e, :s, :debut)"
        ),
        {"a": appartenance, "e": entite, "s": statut, "debut": INSTANT - dt.timedelta(days=60)},
    )


def _tache_de_reference(connexion: Connection, entite: uuid.UUID | None, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO onboarding_task_reference (entity_id, code, title) "
                    "VALUES (:e, :c, :t) RETURNING id"
                ),
                {"e": entite, "c": code, "t": f"Titre {code}"},
            ).scalar_one()
        )
    )


def _modele_publie(
    connexion: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    *,
    name: str,
    target_status: str,
    taches: Sequence[tuple[uuid.UUID, int]],
) -> Modele:
    """Un modele ENTITY publie pour `target_status` — les TROIS routes reelles
    du service (`T5`/`T6` du LOT 7), jamais une ecriture directe en base.
    `taches` : `(task_reference_id, due_offset_days)`, toutes obligatoires."""
    modele = creer_un_modele(
        connexion,
        entite=entite,
        name=name,
        target_status=target_status,
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )
    version = creer_une_version(
        connexion,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )
    definir_les_taches_de_la_version(
        connexion,
        modele=modele,
        version=version,
        taches=tuple(
            NouvelleTacheDeVersion(
                task_reference_id=reference,
                required=True,
                due_offset_days=decalage,
                title_override=None,
                description_override=None,
            )
            for reference, decalage in taches
        ),
        acteur=acteur,
        instant=INSTANT,
    )
    publier_une_version(
        connexion,
        version=version.id,
        entite_du_modele=modele.entity_id,
        acteur=acteur,
        instant=INSTANT,
    )
    return modele


def _audit_events(
    connexion: Connection, *, action_code: str, resource_reference: uuid.UUID | None = None
) -> Sequence[RowMapping]:
    requete = "SELECT * FROM audit_event WHERE action_code = :code"
    parametres: dict[str, object] = {"code": action_code}
    if resource_reference is not None:
        requete += " AND resource_reference = :reference"
        parametres["reference"] = resource_reference
    return connexion.execute(text(requete), parametres).mappings().all()


# ===========================================================================
#  LE CATALOGUE DES TACHES DE REFERENCE
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_une_tache_de_reference_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-CAT")
    acteur = _personne(cx, f"acteur-cat-{uuid.uuid4().hex[:8]}@exemple.test")

    creee = creer_une_tache_de_reference(
        cx,
        entite=entite,
        code=f"{MARQUEUR}-tache",
        title="Signer le contrat",
        description=None,
        category=None,
        acteur=acteur,
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="tache_de_reference_creee", resource_reference=creee.id)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "onboarding_task_reference"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == INSTANT
    assert ligne["retention_until"] == INSTANT + DUREE_DE_RETENTION
    assert ligne["correlation_token"]


@pytest.mark.integration
def test_la_creation_d_une_tache_GLOBALE_ecrit_un_audit_event_SANS_entite(
    cx: Connection,
) -> None:
    """`entity_id=None` — meme lecture que `creer_une_entite` (`T3`) : l'audit
    porte le PERIMETRE REEL de la ressource, jamais celui de l'appelant."""
    acteur = _personne(cx, f"acteur-catglobal-{uuid.uuid4().hex[:8]}@exemple.test")

    creee = creer_une_tache_de_reference(
        cx,
        entite=None,
        code=f"{MARQUEUR}-tache-globale",
        title="Tache commune",
        description=None,
        category=None,
        acteur=acteur,
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="tache_de_reference_creee", resource_reference=creee.id)
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] is None
    assert lignes[0]["actor_person_id"] == acteur


# ===========================================================================
#  LES MODELES ET LEURS VERSIONS
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_un_modele_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-MOD")
    acteur = _personne(cx, f"acteur-mod-{uuid.uuid4().hex[:8]}@exemple.test")

    cree = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours mission",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="modele_cree", resource_reference=cree.id)
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "onboarding_template"
    assert lignes[0]["entity_id"] == entite


@pytest.mark.integration
def test_la_creation_d_une_version_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-VERS")
    acteur = _personne(cx, f"acteur-vers-{uuid.uuid4().hex[:8]}@exemple.test")
    modele = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )

    creee = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary="Premiere version",
        acteur=acteur,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(cx, action_code="version_creee", resource_reference=creee.id)
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "onboarding_template_version"
    assert lignes[0]["entity_id"] == entite
    assert lignes[0]["occurred_at"] == PLUS_TARD


@pytest.mark.integration
def test_la_definition_des_taches_ecrit_un_SEUL_audit_event(cx: Connection) -> None:
    """UN evenement d'audit pour l'appel entier, meme avec plusieurs taches."""
    entite = _entite(cx, f"{MARQUEUR}-TACHES")
    acteur = _personne(cx, f"acteur-taches-{uuid.uuid4().hex[:8]}@exemple.test")
    modele = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )
    version = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )
    premiere = _tache_de_reference(cx, entite, f"{MARQUEUR}-t1")
    seconde = _tache_de_reference(cx, entite, f"{MARQUEUR}-t2")

    definir_les_taches_de_la_version(
        cx,
        modele=modele,
        version=version,
        taches=(
            NouvelleTacheDeVersion(
                task_reference_id=premiere,
                required=True,
                due_offset_days=3,
                title_override=None,
                description_override=None,
            ),
            NouvelleTacheDeVersion(
                task_reference_id=seconde,
                required=False,
                due_offset_days=7,
                title_override=None,
                description_override=None,
            ),
        ),
        acteur=acteur,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(
        cx, action_code="taches_de_version_definies", resource_reference=version.id
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["new_values"]["taches"] == [
        {"task_reference_id": str(premiere), "required": True, "due_offset_days": 3},
        {"task_reference_id": str(seconde), "required": False, "due_offset_days": 7},
    ]


@pytest.mark.integration
def test_la_definition_des_taches_a_vide_ecrit_QUAND_MEME_un_audit_event(
    cx: Connection,
) -> None:
    """A LA DIFFERENCE de `reordonner_les_liens` (`T4`) : pas de retour anticipe.

    Vider la liste des taches d'une version brouillon est une forme normale
    de ce geste — meme principe que `gerer_les_medias_d_un_evenement` (`T5`).
    """
    entite = _entite(cx, f"{MARQUEUR}-TACHESVIDE")
    acteur = _personne(cx, f"acteur-tachesvide-{uuid.uuid4().hex[:8]}@exemple.test")
    modele = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )
    version = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )

    definir_les_taches_de_la_version(
        cx, modele=modele, version=version, taches=(), acteur=acteur, instant=INSTANT
    )

    lignes = _audit_events(
        cx, action_code="taches_de_version_definies", resource_reference=version.id
    )
    assert len(lignes) == 1
    assert lignes[0]["new_values"] == {"taches": []}


@pytest.mark.integration
def test_la_publication_d_une_version_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-PUB")
    acteur = _personne(cx, f"acteur-pub-{uuid.uuid4().hex[:8]}@exemple.test")
    modele = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )
    version = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )

    publier_une_version(
        cx,
        version=version.id,
        entite_du_modele=modele.entity_id,
        acteur=acteur,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(cx, action_code="version_publiee", resource_reference=version.id)
    assert len(lignes) == 1
    assert lignes[0]["occurred_at"] == PLUS_TARD


@pytest.mark.integration
def test_larchivage_d_une_version_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-ARCHVERS")
    acteur = _personne(cx, f"acteur-archvers-{uuid.uuid4().hex[:8]}@exemple.test")
    modele = _modele_publie(
        cx, entite, acteur, name="Parcours", target_status="intercontract", taches=()
    )
    version = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )
    publier_une_version(
        cx, version=version.id, entite_du_modele=modele.entity_id, acteur=acteur, instant=INSTANT
    )

    archiver_une_version(
        cx,
        version=version.id,
        entite_du_modele=modele.entity_id,
        acteur=acteur,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(cx, action_code="version_archivee", resource_reference=version.id)
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] == entite


@pytest.mark.integration
def test_la_restauration_d_une_version_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-RESTVERS")
    acteur = _personne(cx, f"acteur-restvers-{uuid.uuid4().hex[:8]}@exemple.test")
    modele = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )
    version = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )
    publier_une_version(
        cx, version=version.id, entite_du_modele=modele.entity_id, acteur=acteur, instant=INSTANT
    )
    archiver_une_version(
        cx, version=version.id, entite_du_modele=modele.entity_id, acteur=acteur, instant=INSTANT
    )

    restaurer_une_version(
        cx,
        version=version.id,
        entite_du_modele=modele.entity_id,
        acteur=acteur,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(cx, action_code="version_restauree", resource_reference=version.id)
    assert len(lignes) == 1
    assert lignes[0]["occurred_at"] == PLUS_TARD


# ===========================================================================
#  LE PARCOURS D'UN COLLABORATEUR
# ===========================================================================


@pytest.mark.integration
def test_laffectation_d_un_parcours_ecrit_un_SEUL_audit_event_malgre_plusieurs_taches(
    cx: Connection,
) -> None:
    """UN evenement d'audit pour l'appel entier, meme avec DEUX taches
    snapshottees — chacune posant son PROPRE `onboarding_task_event` (§13.7),
    jamais son propre `audit_event`."""
    entite = _entite(cx, f"{MARQUEUR}-AFFECT")
    acteur = _personne(cx, f"acteur-affect-{uuid.uuid4().hex[:8]}@exemple.test")
    cible_personne = _personne(cx, f"cible-affect-{uuid.uuid4().hex[:8]}@exemple.test")
    appartenance = _appartenance(cx, entite, cible_personne)
    _statut(cx, entite, appartenance, "intercontract")
    premiere = _tache_de_reference(cx, entite, f"{MARQUEUR}-affect-t1")
    seconde = _tache_de_reference(cx, entite, f"{MARQUEUR}-affect-t2")
    _modele_publie(
        cx,
        entite,
        acteur,
        name="Parcours mission",
        target_status="intercontract",
        taches=((premiere, 3), (seconde, 7)),
    )

    parcours = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=appartenance,
        cible=Appartenance(person_id=cible_personne, arrival_date=ARRIVEE),
        acteur=acteur,
        instant=PLUS_TARD,
    )

    assert len(parcours.taches) == 2
    lignes = _audit_events(
        cx,
        action_code=TypeEvenementTache.ASSIGNED.value,
        resource_reference=parcours.instance.id,  # type: ignore[union-attr]
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "onboarding_instance"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == PLUS_TARD

    n_evenements_de_tache = cx.execute(
        text(
            "SELECT count(*) FROM onboarding_task_event WHERE onboarding_instance_task_id IN "
            "(SELECT id FROM onboarding_instance_task WHERE onboarding_instance_id = :i)"
        ),
        {"i": parcours.instance.id},  # type: ignore[union-attr]
    ).scalar_one()
    assert n_evenements_de_tache == 2, "le journal §13.7 reste PAR tache, lui"


# ===========================================================================
#  LES GESTES SUR UNE TACHE
# ===========================================================================


def _parcours_a_une_tache(
    cx: Connection, entite: uuid.UUID, acteur: uuid.UUID, marqueur: str
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Un collaborateur affecte a un parcours a UNE SEULE tache obligatoire.
    Rend `(appartenance, instance, tache)`."""
    cible_personne = _personne(cx, f"cible-{marqueur}-{uuid.uuid4().hex[:8]}@exemple.test")
    appartenance = _appartenance(cx, entite, cible_personne)
    _statut(cx, entite, appartenance, "intercontract")
    tache_ref = _tache_de_reference(cx, entite, f"{MARQUEUR}-{marqueur}-tache")
    _modele_publie(
        cx,
        entite,
        acteur,
        name=f"Parcours {marqueur}",
        target_status="intercontract",
        taches=((tache_ref, 3),),
    )
    parcours = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=appartenance,
        cible=Appartenance(person_id=cible_personne, arrival_date=ARRIVEE),
        acteur=acteur,
        instant=INSTANT,
    )
    assert parcours.instance is not None
    assert len(parcours.taches) == 1
    return appartenance, parcours.instance.id, parcours.taches[0].id


@pytest.mark.integration
def test_la_completion_d_une_tache_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-TERM")
    acteur = _personne(cx, f"acteur-term-{uuid.uuid4().hex[:8]}@exemple.test")
    _appartenance_inst, instance, tache = _parcours_a_une_tache(cx, entite, acteur, "term")

    terminer_une_tache(
        cx, entite=entite, instance=instance, tache=tache, acteur=acteur, instant=PLUS_TARD
    )

    lignes = _audit_events(
        cx, action_code=TypeEvenementTache.COMPLETED.value, resource_reference=tache
    )
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "onboarding_instance_task"
    assert lignes[0]["entity_id"] == entite
    assert lignes[0]["occurred_at"] == PLUS_TARD


@pytest.mark.integration
def test_terminer_la_derniere_tache_obligatoire_n_ecrit_QU_UN_SEUL_audit_event(
    cx: Connection,
) -> None:
    """L'archivage AUTOMATIQUE du parcours (LOT 7, `T11`), declenche par cette
    MEME completion, N'ECRIT PAS son propre `audit_event` — c'est une
    CONSEQUENCE, jamais une decision distincte de l'acteur."""
    entite = _entite(cx, f"{MARQUEUR}-AUTOARCH")
    acteur = _personne(cx, f"acteur-autoarch-{uuid.uuid4().hex[:8]}@exemple.test")
    _appartenance_inst, instance, tache = _parcours_a_une_tache(cx, entite, acteur, "autoarch")

    terminer_une_tache(
        cx, entite=entite, instance=instance, tache=tache, acteur=acteur, instant=INSTANT
    )

    etat = cx.execute(
        text("SELECT state FROM onboarding_instance WHERE id = :i"), {"i": instance}
    ).scalar_one()
    assert etat == "archived", (
        "l'automatique du LOT 7 doit avoir agi pour que ce test prouve quelque chose"
    )

    completions = _audit_events(cx, action_code=TypeEvenementTache.COMPLETED.value)
    archivages = _audit_events(cx, action_code="parcours_archive", resource_reference=instance)
    assert len(completions) == 1
    assert len(archivages) == 0


@pytest.mark.integration
def test_lannulation_de_la_completion_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-ANNUL")
    acteur = _personne(cx, f"acteur-annul-{uuid.uuid4().hex[:8]}@exemple.test")
    _appartenance_inst, instance, tache = _parcours_a_une_tache(cx, entite, acteur, "annul")
    terminer_une_tache(
        cx, entite=entite, instance=instance, tache=tache, acteur=acteur, instant=INSTANT
    )

    annuler_la_completion(
        cx, entite=entite, instance=instance, tache=tache, acteur=acteur, instant=INSTANT
    )

    lignes = _audit_events(
        cx, action_code=TypeEvenementTache.CANCELLED.value, resource_reference=tache
    )
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] == entite


@pytest.mark.integration
def test_la_reouverture_ecrit_un_audit_event_avec_son_motif(cx: Connection) -> None:
    """`motif` (deja obligatoire, §8.3) est porte dans `reason`, jamais dans
    `summary` — meme discipline que `annuler_un_evenement` (LOT 8, `T5`)."""
    entite = _entite(cx, f"{MARQUEUR}-REOUV")
    acteur = _personne(cx, f"acteur-reouv-{uuid.uuid4().hex[:8]}@exemple.test")
    _appartenance_inst, instance, tache = _parcours_a_une_tache(cx, entite, acteur, "reouv")
    #  Completee BIEN avant l'instant de reouverture, pour etre hors de la
    #  fenetre de cinq minutes — meme discipline que `test_reouverture_onboarding.py`.
    completee_a = INSTANT - dt.timedelta(minutes=10)
    terminer_une_tache(
        cx, entite=entite, instance=instance, tache=tache, acteur=acteur, instant=completee_a
    )

    reouvrir_une_tache(
        cx,
        entite=entite,
        instance=instance,
        tache=tache,
        acteur=acteur,
        motif="Tache terminee par erreur",
        instant=INSTANT,
    )

    lignes = _audit_events(
        cx, action_code=TypeEvenementTache.REOPENED.value, resource_reference=tache
    )
    assert len(lignes) == 1
    assert lignes[0]["reason"] == "Tache terminee par erreur"


# ===========================================================================
#  L'ARCHIVAGE ET LA RESTAURATION MANUELS D'UN PARCOURS
# ===========================================================================


@pytest.mark.integration
def test_larchivage_manuel_d_un_parcours_termine_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-ARCHMAN")
    acteur = _personne(cx, f"acteur-archman-{uuid.uuid4().hex[:8]}@exemple.test")
    cible_personne = _personne(cx, f"cible-archman-{uuid.uuid4().hex[:8]}@exemple.test")
    appartenance = _appartenance(cx, entite, cible_personne)
    _statut(cx, entite, appartenance, "intercontract")
    #  Une tache NON obligatoire seule : le parcours ne s'archive JAMAIS tout
    #  seul, ce qui rend le geste MANUEL necessaire pour ce test.
    tache_ref = _tache_de_reference(cx, entite, f"{MARQUEUR}-archman-tache")
    modele = creer_un_modele(
        cx,
        entite=entite,
        name="Parcours archman",
        target_status="intercontract",
        scope_type="ENTITY",
        scope_person_id=None,
        scope_circle_id=None,
        acteur=acteur,
        instant=INSTANT,
    )
    version = creer_une_version(
        cx,
        modele=modele.id,
        entite_du_modele=modele.entity_id,
        change_summary=None,
        acteur=acteur,
        instant=INSTANT,
    )
    definir_les_taches_de_la_version(
        cx,
        modele=modele,
        version=version,
        taches=(
            NouvelleTacheDeVersion(
                task_reference_id=tache_ref,
                required=False,
                due_offset_days=3,
                title_override=None,
                description_override=None,
            ),
        ),
        acteur=acteur,
        instant=INSTANT,
    )
    publier_une_version(
        cx, version=version.id, entite_du_modele=modele.entity_id, acteur=acteur, instant=INSTANT
    )
    parcours = affecter_un_parcours(
        cx,
        entite=entite,
        appartenance=appartenance,
        cible=Appartenance(person_id=cible_personne, arrival_date=ARRIVEE),
        acteur=acteur,
        instant=INSTANT,
    )
    assert parcours.instance is not None

    archivee = archiver_un_parcours_termine(
        cx,
        entite=entite,
        instance=parcours.instance.id,
        acteur=acteur,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(cx, action_code="parcours_archive", resource_reference=archivee.id)
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] == entite
    assert lignes[0]["occurred_at"] == PLUS_TARD


@pytest.mark.integration
def test_la_restauration_d_un_parcours_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-RESTPARC")
    acteur = _personne(cx, f"acteur-restparc-{uuid.uuid4().hex[:8]}@exemple.test")
    _appartenance_inst, instance, tache = _parcours_a_une_tache(cx, entite, acteur, "restparc")
    terminer_une_tache(
        cx, entite=entite, instance=instance, tache=tache, acteur=acteur, instant=INSTANT
    )
    etat = cx.execute(
        text("SELECT state FROM onboarding_instance WHERE id = :i"), {"i": instance}
    ).scalar_one()
    assert etat == "archived"

    restauree = restaurer_un_parcours(
        cx, entite=entite, instance=instance, acteur=acteur, instant=PLUS_TARD
    )

    lignes = _audit_events(cx, action_code="parcours_restaure", resource_reference=restauree.id)
    assert len(lignes) == 1
    assert lignes[0]["occurred_at"] == PLUS_TARD


# ===========================================================================
#  CORRELATION
# ===========================================================================


@pytest.mark.integration
def test_le_correlation_token_courant_est_REPRIS_pour_l_onboarding(cx: Connection) -> None:
    identifiant = definir_correlation("une-correlation-de-test-t6")
    try:
        entite = _entite(cx, f"{MARQUEUR}-CORR")
        acteur = _personne(cx, f"acteur-corr-{uuid.uuid4().hex[:8]}@exemple.test")
        cree = creer_un_modele(
            cx,
            entite=entite,
            name="Parcours",
            target_status="intercontract",
            scope_type="ENTITY",
            scope_person_id=None,
            scope_circle_id=None,
            acteur=acteur,
            instant=INSTANT,
        )
        lignes = _audit_events(cx, action_code="modele_cree", resource_reference=cree.id)
        assert lignes[0]["correlation_token"] == identifiant
    finally:
        effacer_correlation()


# ===========================================================================
#  ATOMICITE — ARB-DATA-005/§30.20 : un echec APRES l'ecriture annule TOUT
# ===========================================================================


@pytest.mark.integration
def test_un_echec_APRES_l_ecriture_annule_AUSSI_l_audit_event(
    parametres_de_la_stack: Parametres,
) -> None:
    _exiger_postgresql(parametres_de_la_stack)
    code = f"{MARQUEUR}-ATOMIQUE-{uuid.uuid4().hex[:8]}"
    with moteur(parametres_de_la_stack).begin() as decor:
        entite = _entite(decor, code)
        acteur = _personne(decor, f"atomique-{uuid.uuid4().hex[:8]}@exemple.test")
        modele = creer_un_modele(
            decor,
            entite=entite,
            name="Parcours atomicite",
            target_status="intercontract",
            scope_type="ENTITY",
            scope_person_id=None,
            scope_circle_id=None,
            acteur=acteur,
            instant=INSTANT,
        )
        version = creer_une_version(
            decor,
            modele=modele.id,
            entite_du_modele=modele.entity_id,
            change_summary=None,
            acteur=acteur,
            instant=INSTANT,
        )
        publier_une_version(
            decor,
            version=version.id,
            entite_du_modele=modele.entity_id,
            acteur=acteur,
            instant=INSTANT,
        )
    try:
        with (
            pytest.raises(RuntimeError, match="echec force apres l'audit"),
            moteur(parametres_de_la_stack).begin() as transaction,
        ):
            archiver_une_version(
                transaction,
                version=version.id,
                entite_du_modele=modele.entity_id,
                acteur=acteur,
                instant=PLUS_TARD,
            )
            #  A cet instant, `onboarding_template_version.state` ET
            #  `audit_event` portent deja la trace — mais la transaction N'A
            #  PAS COMMIT.
            raise RuntimeError("echec force apres l'audit, pour prouver l'atomicite")
        with moteur(parametres_de_la_stack).connect() as verification:
            #  Filtre sur `action_code` : le decor publie la version via le
            #  SERVICE `publier_une_version`, lui-meme cable (`T6`) — son
            #  PROPRE `audit_event` de publication a deja COMMIT, avec le
            #  MEME `resource_reference`. Sans ce filtre, cet evenement
            #  legitime masquerait l'absence de celui de l'archivage — meme
            #  confusion que `T4`/`T5` ont deja corrigee avant de l'ecrire ici.
            n_audit = verification.execute(
                text(
                    "SELECT count(*) FROM audit_event "
                    "WHERE resource_reference = :v AND action_code = :action"
                ),
                {"v": version.id, "action": "version_archivee"},
            ).scalar_one()
            etat = verification.execute(
                text("SELECT state FROM onboarding_template_version WHERE id = :v"),
                {"v": version.id},
            ).scalar_one()
            assert n_audit == 0, (
                "l'audit_event a SURVECU a l'echec : la transaction n'est pas atomique"
            )
            assert etat == "published", "la version a ete archivee malgre l'echec force"
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            menage.execute(
                text(
                    "DELETE FROM audit_event WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :code)"
                ),
                {"code": code},
            )
            menage.execute(
                text(
                    "DELETE FROM onboarding_template_version WHERE template_id IN "
                    "(SELECT id FROM onboarding_template WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :code))"
                ),
                {"code": code},
            )
            menage.execute(
                text(
                    "DELETE FROM onboarding_template WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :code)"
                ),
                {"code": code},
            )
            menage.execute(
                text(
                    "DELETE FROM audit_event WHERE actor_person_id IN "
                    "(SELECT id FROM person WHERE email_normalized LIKE :motif)"
                ),
                {"motif": "atomique-%"},
            )
            menage.execute(
                text("DELETE FROM person WHERE email_normalized LIKE :motif"),
                {"motif": "atomique-%"},
            )
            menage.execute(text("DELETE FROM entity WHERE code = :code"), {"code": code})
