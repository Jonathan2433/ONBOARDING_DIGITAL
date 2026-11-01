"""Le reporting etendu — LOT 10, `T10`, `MVP-L10-US003`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. « onboardings termines » ne compte que `state = 'archived' AND
     completed_at IS NOT NULL` — jamais une instance encore `active`, ni une
     instance `archived` par un DEPART (`completed_at IS NULL`) ;
  2. « duree moyenne » vaut `completed_at - started_at`, sur la MEME
     population, et `None` (jamais `0`) quand cette population est vide ;
  3. « progression moyenne » somme le couple (totales, terminees) sur les
     instances ACTIVES SEULES de la portee, jamais les instances terminees ;
  4. « arrivees dans les 30 jours » est une fenetre BORNEE, distincte de
     « arrivees futures » (illimitee, LOT 9 `T5`) — une arrivee a 45 jours
     n'y entre pas ;
  5. les trois repartitions (cercle, client, DSM) groupent les PROFILS ACTIFS
     par relation courante, et une personne sans la relation concernee
     n'apparait dans AUCUN groupe ;
  6. le perimetre CONSULTANTS/CERCLE narrowe chaque requete EXACTEMENT comme
     `app.administration.tableau_de_bord` (meme clause, meme discipline) ;
  7. chaque axe de `FiltresDeReporting` (periode, DSM, cercle, client) narrowe
     la population SANS l'elargir au-dela du perimetre deja resolu — un
     temoin positif ET negatif par axe (§7.39) ;
  8. « detail onboarding » ne liste que les instances ACTIVES, avec leur
     progression PAR PERSONNE ;
  9. « profils incomplets » en detail rend EXACTEMENT la meme population que
     le compte de `T5` (LOT 9), avec les quatre booleens corrects.

Ce fichier ne reteste PAS `resoudre_le_perimetre_du_tableau_de_bord` ni
`ROLES_DU_TABLEAU_DE_BORD` : REUTILISES tels quels depuis `T5` (LOT 9), deja
prouves par `test_tableau_de_bord.py` — les retester ici dupliquerait une
preuve, jamais une regle (§7.27).
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.administration.perimetre import PerimetreDuTableauDeBord
from app.configuration.settings import Parametres
from app.reporting.lecture import (
    FiltresDeReporting,
    lire_les_indicateurs,
    lister_le_detail_onboarding,
    lister_les_profils_incomplets,
)
from app.shared.database import moteur

MARQUEUR = "L10T10"
ANCRAGE = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=10)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _entite(cx: Connection, suffixe: str) -> uuid.UUID:
    code = f"{MARQUEUR}-{suffixe}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Reporting', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _client(cx: Connection, entite: uuid.UUID, nom: str) -> uuid.UUID:
    #  DEUX PARAMETRES DISTINCTS, JAMAIS PARTAGES : `canonical_name` est
    #  `character varying(256)`, `display_name` est `text` — un seul `:n`
    #  reutilise sur les deux leve `AmbiguousParameter` (§7.25 de CLAUDE.md).
    unique = f"{nom.lower()}-{uuid.uuid4().hex[:6]}"
    client = cx.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affiche, 'active') RETURNING id"
        ),
        {"canonique": unique, "affiche": unique},
    ).scalar_one()
    #  `fn_mission_client_actif` (declencheur §7.6) exige un client ACTIVE
    #  POUR L'ENTITE avant toute mission — sans cette ligne, l'insertion
    #  d'une situation professionnelle en mission leve un `CheckViolation`.
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    return client  # type: ignore[no-any-return]


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = "active",
    arrivee: dt.date | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": arrivee or ANCRAGE.date(), "etat": etat},
    ).scalar_one()


def _cercle_principal(
    cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID, cercle: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, 'principal', :d)"
        ),
        {"e": entite, "m": appartenance, "c": cercle, "d": ANCRAGE - dt.timedelta(days=60)},
    )


def _situation_mission(
    cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID, client: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, client_id, starts_at) VALUES (:e, :m, 'mission', :c, :d)"
        ),
        {"e": entite, "m": appartenance, "c": client, "d": ANCRAGE - dt.timedelta(days=60)},
    )


def _dsm_responsable(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": ANCRAGE - dt.timedelta(days=90)},
    )


def _dsm_de_ce_consultant(
    cx: Connection, entite: uuid.UUID, consultant: uuid.UUID, dsm_personne: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at) VALUES (:e, :c, :d, :date)"
        ),
        {"e": entite, "c": consultant, "d": dsm_personne, "date": ANCRAGE - dt.timedelta(days=90)},
    )


def _modele_et_version(cx: Connection, entite: uuid.UUID) -> uuid.UUID:
    modele = cx.execute(
        text(
            "INSERT INTO onboarding_template (entity_id, name, target_status, scope_type, "
            "state) VALUES (:e, :n, 'intercontract', 'ENTITY', 'active') RETURNING id"
        ),
        {"e": entite, "n": f"{MARQUEUR}-modele-{uuid.uuid4().hex[:6]}"},
    ).scalar_one()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_template_version (template_id, version_number, state, "
            "published_at) VALUES (:t, 1, 'published', :d) RETURNING id"
        ),
        {"t": modele, "d": ANCRAGE - dt.timedelta(days=30)},
    ).scalar_one()


def _instance(
    cx: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    version: uuid.UUID,
    *,
    etat: str = "active",
    debutee: dt.datetime | None = None,
    terminee: dt.datetime | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_instance (entity_id, entity_membership_id, "
            "template_version_id, reference_date, state, started_at, completed_at) "
            "VALUES (:e, :m, :v, :d, :etat, :debutee, :terminee) RETURNING id"
        ),
        {
            "e": entite,
            "m": appartenance,
            "v": version,
            "d": (debutee or ANCRAGE).date(),
            "etat": etat,
            "debutee": debutee or ANCRAGE,
            "terminee": terminee,
        },
    ).scalar_one()


def _tache_de_reference(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_task_reference (entity_id, code, title) "
            "VALUES (:e, :c, :t) RETURNING id"
        ),
        {"e": entite, "c": code, "t": f"Titre {code}"},
    ).scalar_one()


def _tache_instance(
    cx: Connection,
    entite: uuid.UUID,
    instance: uuid.UUID,
    reference: uuid.UUID,
    *,
    required: bool,
    state: str,
) -> None:
    cx.execute(
        text(
            "INSERT INTO onboarding_instance_task (entity_id, onboarding_instance_id, "
            "task_reference_id, title_snapshot, required, state, due_at, completed_at) "
            "VALUES (:e, :i, :r, 'Tache', :req, :etat, :due, :completee)"
        ),
        {
            "e": entite,
            "i": instance,
            "r": reference,
            "req": required,
            "etat": state,
            "due": ANCRAGE + dt.timedelta(days=5),
            "completee": ANCRAGE if state == "completed" else None,
        },
    )


#  =========================================================================
#  onboardings termines / duree moyenne
#  =========================================================================


@pytest.mark.integration
def test_onboardings_termines_exclut_les_actifs_et_les_archives_par_depart(cx: Connection) -> None:
    entite = _entite(cx, "ENT1")
    acteur = _personne(cx, "ESM1")
    version = _modele_et_version(cx, entite)

    actif = _appartenance(cx, entite, _personne(cx, "ACTIF"))
    _instance(cx, entite, actif, version, etat="active")

    #  Archive par DEPART : `completed_at` reste NULL (voir
    #  `archiver_le_parcours_au_depart`), donc PAS « termine ».
    interrompu = _appartenance(cx, entite, _personne(cx, "INTERROMPU"))
    _instance(cx, entite, interrompu, version, etat="archived", terminee=None)

    #  Archive par COMPLETION : `completed_at` est pose.
    acheve = _appartenance(cx, entite, _personne(cx, "ACHEVE"))
    _instance(
        cx,
        entite,
        acheve,
        version,
        etat="archived",
        debutee=ANCRAGE - dt.timedelta(days=20),
        terminee=ANCRAGE - dt.timedelta(days=5),
    )

    indicateurs = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )

    assert indicateurs.onboardings_termines == 1


@pytest.mark.integration
def test_duree_moyenne_est_calculee_sur_les_termines_seuls(cx: Connection) -> None:
    entite = _entite(cx, "ENT2")
    acteur = _personne(cx, "ESM2")
    version = _modele_et_version(cx, entite)

    appartenance = _appartenance(cx, entite, _personne(cx, "ACHEVE"))
    debut = ANCRAGE - dt.timedelta(days=10)
    fin = ANCRAGE
    _instance(cx, entite, appartenance, version, etat="archived", debutee=debut, terminee=fin)

    indicateurs = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )

    assert indicateurs.duree_moyenne_jours is not None
    assert indicateurs.duree_moyenne_jours == pytest.approx(10.0, abs=0.01)


@pytest.mark.integration
def test_duree_moyenne_vaut_NONE_jamais_ZERO_sans_onboarding_termine(cx: Connection) -> None:
    entite = _entite(cx, "ENT3")
    acteur = _personne(cx, "ESM3")
    version = _modele_et_version(cx, entite)
    appartenance = _appartenance(cx, entite, _personne(cx, "ACTIF"))
    _instance(cx, entite, appartenance, version, etat="active")

    indicateurs = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )

    assert indicateurs.duree_moyenne_jours is None


#  =========================================================================
#  progression moyenne
#  =========================================================================


@pytest.mark.integration
def test_progression_moyenne_somme_les_taches_obligatoires_des_instances_actives(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ENT4")
    acteur = _personne(cx, "ESM4")
    version = _modele_et_version(cx, entite)

    actif = _appartenance(cx, entite, _personne(cx, "ACTIF"))
    instance_active = _instance(cx, entite, actif, version, etat="active")
    ref1 = _tache_de_reference(cx, entite, f"T1-{uuid.uuid4().hex[:6]}")
    ref2 = _tache_de_reference(cx, entite, f"T2-{uuid.uuid4().hex[:6]}")
    ref3 = _tache_de_reference(cx, entite, f"T3-{uuid.uuid4().hex[:6]}")
    _tache_instance(cx, entite, instance_active, ref1, required=True, state="completed")
    _tache_instance(cx, entite, instance_active, ref2, required=True, state="todo")
    #  Non obligatoire : ne doit PAS entrer dans le couple.
    _tache_instance(cx, entite, instance_active, ref3, required=False, state="completed")

    #  Une instance TERMINEE : sa progression n'entre JAMAIS dans la moyenne —
    #  elle serait a 100 % par definition et diluerait la mesure.
    termine = _appartenance(cx, entite, _personne(cx, "TERMINE"))
    instance_terminee = _instance(cx, entite, termine, version, etat="archived", terminee=ANCRAGE)
    ref4 = _tache_de_reference(cx, entite, f"T4-{uuid.uuid4().hex[:6]}")
    _tache_instance(cx, entite, instance_terminee, ref4, required=True, state="completed")

    indicateurs = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )

    assert indicateurs.progression_moyenne.taches_obligatoires_totales == 2
    assert indicateurs.progression_moyenne.taches_obligatoires_terminees == 1


#  =========================================================================
#  arrivees dans les 30 jours
#  =========================================================================


@pytest.mark.integration
def test_arrivees_30_jours_est_une_fenetre_BORNEE_distincte_des_arrivees_futures(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ENT5")
    acteur = _personne(cx, "ESM5")
    aujourd_hui = ANCRAGE.date()

    _appartenance(
        cx,
        entite,
        _personne(cx, "DANS15J"),
        etat="future",
        arrivee=aujourd_hui + dt.timedelta(days=15),
    )
    _appartenance(
        cx,
        entite,
        _personne(cx, "DANS45J"),
        etat="future",
        arrivee=aujourd_hui + dt.timedelta(days=45),
    )

    indicateurs = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )

    assert indicateurs.arrivees_30_jours == 1


#  =========================================================================
#  repartitions
#  =========================================================================


@pytest.mark.integration
def test_repartition_par_cercle_client_dsm(cx: Connection) -> None:
    entite = _entite(cx, "ENT6")
    acteur = _personne(cx, "ESM6")
    cercle = _cercle(cx, entite, "C1")
    client = _client(cx, entite, "Client6")
    dsm_personne = _personne(cx, "DSM6")
    _dsm_responsable(cx, dsm_personne, entite)

    rattache = _appartenance(cx, entite, _personne(cx, "RATTACHE"))
    _cercle_principal(cx, entite, rattache, cercle)
    _situation_mission(cx, entite, rattache, client)
    _dsm_de_ce_consultant(cx, entite, rattache, dsm_personne)

    #  Sans aucune des trois relations : n'apparait dans AUCUN groupe.
    _appartenance(cx, entite, _personne(cx, "SANS_RELATION"))

    indicateurs = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )

    assert len(indicateurs.repartition_par_cercle) == 1
    assert indicateurs.repartition_par_cercle[0].profils_actifs == 1
    assert len(indicateurs.repartition_par_client) == 1
    assert indicateurs.repartition_par_client[0].profils_actifs == 1
    assert len(indicateurs.repartition_par_dsm) == 1
    assert indicateurs.repartition_par_dsm[0].profils_actifs == 1


#  =========================================================================
#  perimetre CONSULTANTS / CERCLE (meme clause que le tableau de bord, T5)
#  =========================================================================


@pytest.mark.integration
def test_perimetre_CONSULTANTS_narrowe_les_indicateurs_au_DSM(cx: Connection) -> None:
    entite = _entite(cx, "ENT7")
    dsm_personne = _personne(cx, "DSM7")
    _dsm_responsable(cx, dsm_personne, entite)

    version = _modele_et_version(cx, entite)
    son_consultant = _appartenance(cx, entite, _personne(cx, "SIEN"))
    _dsm_de_ce_consultant(cx, entite, son_consultant, dsm_personne)
    _instance(
        cx,
        entite,
        son_consultant,
        version,
        etat="archived",
        debutee=ANCRAGE - dt.timedelta(days=5),
        terminee=ANCRAGE,
    )

    #  Un AUTRE consultant, termine aussi, mais sans lien DSM avec cet acteur.
    autre = _appartenance(cx, entite, _personne(cx, "AUTRE"))
    _instance(
        cx,
        entite,
        autre,
        version,
        etat="archived",
        debutee=ANCRAGE - dt.timedelta(days=5),
        terminee=ANCRAGE,
    )

    indicateurs = lire_les_indicateurs(
        cx,
        entite=entite,
        acteur=dsm_personne,
        perimetre=PerimetreDuTableauDeBord.CONSULTANTS,
        instant=ANCRAGE,
    )

    assert indicateurs.onboardings_termines == 1


@pytest.mark.integration
def test_perimetre_CERCLE_narrowe_la_repartition_par_client(cx: Connection) -> None:
    entite = _entite(cx, "ENT8")
    booster_personne = _personne(cx, "BOOST8")
    cercle_du_booster = _cercle(cx, entite, "CB")
    autre_cercle = _cercle(cx, entite, "CA")
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'BOOSTER', :c, :p, :d)"
        ),
        {
            "p": booster_personne,
            "e": entite,
            "c": cercle_du_booster,
            "d": ANCRAGE - dt.timedelta(days=90),
        },
    )
    client = _client(cx, entite, "Client8")

    dans_le_cercle = _appartenance(cx, entite, _personne(cx, "DANS"))
    _cercle_principal(cx, entite, dans_le_cercle, cercle_du_booster)
    _situation_mission(cx, entite, dans_le_cercle, client)

    hors_du_cercle = _appartenance(cx, entite, _personne(cx, "HORS"))
    _cercle_principal(cx, entite, hors_du_cercle, autre_cercle)
    _situation_mission(cx, entite, hors_du_cercle, client)

    indicateurs = lire_les_indicateurs(
        cx,
        entite=entite,
        acteur=booster_personne,
        perimetre=PerimetreDuTableauDeBord.CERCLE,
        instant=ANCRAGE,
    )

    assert len(indicateurs.repartition_par_client) == 1
    assert indicateurs.repartition_par_client[0].profils_actifs == 1


#  =========================================================================
#  filtres — periode, DSM, cercle, client
#  =========================================================================


@pytest.mark.integration
def test_filtre_periode_borne_arrival_date(cx: Connection) -> None:
    entite = _entite(cx, "ENT9")
    acteur = _personne(cx, "ESM9")
    cercle = _cercle(cx, entite, "C9")

    dedans = _appartenance(cx, entite, _personne(cx, "DEDANS"), arrivee=ANCRAGE.date())
    _cercle_principal(cx, entite, dedans, cercle)
    dehors = _appartenance(
        cx, entite, _personne(cx, "DEHORS"), arrivee=ANCRAGE.date() - dt.timedelta(days=100)
    )
    _cercle_principal(cx, entite, dehors, cercle)

    indicateurs = lire_les_indicateurs(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
        filtres=FiltresDeReporting(depuis=ANCRAGE.date() - dt.timedelta(days=10)),
    )

    assert indicateurs.repartition_par_cercle[0].profils_actifs == 1


@pytest.mark.integration
def test_filtre_cercle_narrowe_sans_elargir_le_perimetre(cx: Connection) -> None:
    entite = _entite(cx, "ENT10")
    acteur = _personne(cx, "ESM10")
    vise = _cercle(cx, entite, "VISE")
    autre = _cercle(cx, entite, "AUTRE")

    membre_vise = _appartenance(cx, entite, _personne(cx, "VISE1"))
    _cercle_principal(cx, entite, membre_vise, vise)
    membre_autre = _appartenance(cx, entite, _personne(cx, "AUTRE1"))
    _cercle_principal(cx, entite, membre_autre, autre)

    #  TEMOIN POSITIF : sans filtre, les deux cercles apparaissent.
    sans_filtre = lire_les_indicateurs(
        cx, entite=entite, acteur=acteur, perimetre=PerimetreDuTableauDeBord.ENTITE, instant=ANCRAGE
    )
    assert len(sans_filtre.repartition_par_cercle) == 2

    #  TEMOIN NEGATIF : avec le filtre, un seul cercle reste.
    avec_filtre = lire_les_indicateurs(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
        filtres=FiltresDeReporting(cercle=vise),
    )
    assert len(avec_filtre.repartition_par_cercle) == 1
    assert avec_filtre.repartition_par_cercle[0].id == vise


@pytest.mark.integration
def test_filtre_dsm_narrowe_la_population(cx: Connection) -> None:
    entite = _entite(cx, "ENT11")
    acteur = _personne(cx, "ESM11")
    dsm_vise = _personne(cx, "DSMVISE")
    _dsm_responsable(cx, dsm_vise, entite)
    dsm_autre = _personne(cx, "DSMAUTRE")
    _dsm_responsable(cx, dsm_autre, entite)
    client = _client(cx, entite, "Client11")

    son_consultant = _appartenance(cx, entite, _personne(cx, "SIEN"))
    _dsm_de_ce_consultant(cx, entite, son_consultant, dsm_vise)
    _situation_mission(cx, entite, son_consultant, client)

    autre_consultant = _appartenance(cx, entite, _personne(cx, "AUTRE"))
    _dsm_de_ce_consultant(cx, entite, autre_consultant, dsm_autre)
    _situation_mission(cx, entite, autre_consultant, client)

    indicateurs = lire_les_indicateurs(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
        filtres=FiltresDeReporting(dsm=dsm_vise),
    )

    assert len(indicateurs.repartition_par_client) == 1
    assert indicateurs.repartition_par_client[0].profils_actifs == 1


@pytest.mark.integration
def test_filtre_client_narrowe_la_population(cx: Connection) -> None:
    entite = _entite(cx, "ENT12")
    acteur = _personne(cx, "ESM12")
    cercle = _cercle(cx, entite, "C12")
    client_vise = _client(cx, entite, "Vise12")
    client_autre = _client(cx, entite, "Autre12")

    avec_vise = _appartenance(cx, entite, _personne(cx, "VISE1"))
    _cercle_principal(cx, entite, avec_vise, cercle)
    _situation_mission(cx, entite, avec_vise, client_vise)

    avec_autre = _appartenance(cx, entite, _personne(cx, "AUTRE1"))
    _cercle_principal(cx, entite, avec_autre, cercle)
    _situation_mission(cx, entite, avec_autre, client_autre)

    indicateurs = lire_les_indicateurs(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
        filtres=FiltresDeReporting(client=client_vise),
    )

    assert indicateurs.repartition_par_cercle[0].profils_actifs == 1


#  =========================================================================
#  detail onboarding — progression par personne
#  =========================================================================


@pytest.mark.integration
def test_detail_onboarding_ne_liste_que_les_instances_actives(cx: Connection) -> None:
    entite = _entite(cx, "ENT13")
    acteur = _personne(cx, "ESM13")
    version = _modele_et_version(cx, entite)

    actif = _appartenance(cx, entite, _personne(cx, "ACTIF"))
    instance_active = _instance(cx, entite, actif, version, etat="active")
    ref = _tache_de_reference(cx, entite, f"TR-{uuid.uuid4().hex[:6]}")
    _tache_instance(cx, entite, instance_active, ref, required=True, state="completed")

    termine = _appartenance(cx, entite, _personne(cx, "TERMINE"))
    _instance(cx, entite, termine, version, etat="archived", terminee=ANCRAGE)

    page = lister_le_detail_onboarding(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )

    assert page.total == 1
    assert page.elements[0].appartenance_id == actif
    assert page.elements[0].taches_obligatoires_totales == 1
    assert page.elements[0].taches_obligatoires_terminees == 1


@pytest.mark.integration
def test_detail_onboarding_sans_tache_rend_zero_zero(cx: Connection) -> None:
    """Une instance active sans AUCUNE tache ne doit pas faire echouer la
    jointure LATERAL — `coalesce` rend 0/0, jamais `NULL`/`NULL`."""
    entite = _entite(cx, "ENT14")
    acteur = _personne(cx, "ESM14")
    version = _modele_et_version(cx, entite)
    actif = _appartenance(cx, entite, _personne(cx, "SANSTACHE"))
    _instance(cx, entite, actif, version, etat="active")

    page = lister_le_detail_onboarding(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )

    assert page.total == 1
    assert page.elements[0].taches_obligatoires_totales == 0
    assert page.elements[0].taches_obligatoires_terminees == 0


#  =========================================================================
#  profils incomplets — en detail
#  =========================================================================


@pytest.mark.integration
def test_profils_incomplets_detail_rend_les_trois_booleens(cx: Connection) -> None:
    """Le metier n'est plus l'un des booleens depuis `DEC-675` (LOT 11 `T5`)."""
    entite = _entite(cx, "ENT15")
    acteur = _personne(cx, "ESM15")
    cercle = _cercle(cx, entite, "C15")

    #  Il ne manque QUE le cercle principal.
    partiel = _appartenance(cx, entite, _personne(cx, "PARTIEL"))
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, starts_at) VALUES (:e, :m, 'intercontract', :d)"
        ),
        {"e": entite, "m": partiel, "d": ANCRAGE - dt.timedelta(days=60)},
    )
    dsm_personne = _personne(cx, "DSM15")
    _dsm_responsable(cx, dsm_personne, entite)
    _dsm_de_ce_consultant(cx, entite, partiel, dsm_personne)

    #  Complet : n'apparait pas dans la liste.
    complet = _appartenance(cx, entite, _personne(cx, "COMPLET"))
    _cercle_principal(cx, entite, complet, cercle)
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, starts_at) VALUES (:e, :m, 'intercontract', :d)"
        ),
        {"e": entite, "m": complet, "d": ANCRAGE - dt.timedelta(days=60)},
    )
    _dsm_de_ce_consultant(cx, entite, complet, dsm_personne)

    page = lister_les_profils_incomplets(
        cx,
        entite=entite,
        acteur=acteur,
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )

    assert page.total == 1
    assert page.elements[0].appartenance_id == partiel
    assert page.elements[0].cercle_principal_manquant is True
    assert page.elements[0].dsm_manquant is False
    assert page.elements[0].statut_manquant is False
