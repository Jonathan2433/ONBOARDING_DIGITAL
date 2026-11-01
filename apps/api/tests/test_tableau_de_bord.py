"""Le tableau de bord administratif — LOT 9, `T5`, `MVP-L09-US001`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. les quatre compteurs propres à ce module (profils actifs, arrivées
     futures, onboardings actifs, profils incomplets) comptent juste dans la
     portée `ENTITE`, et la portée `CONSULTANTS`/`CERCLE` exclut bien ce qui
     n'entre pas dans le périmètre de l'acteur ;
  2. « profil incomplet » est EXACTEMENT ce que l'arbitrage du 09/10/2026
     dit — un profil `active` auquel il manque cercle principal, DSM ou
     statut, le client n'entrant jamais dans le calcul. **Le métier en est
     RETIRÉ depuis `DEC-675`** (LOT 11 `T5`, second arbitrage explicite) :
     le champ étant redevenu facultatif partout, son absence seule n'est
     plus comptée comme un manque ;
  3. « onboardings actifs » ne compte que les instances `active`, jamais
     `archived`/`replaced` ;
  4. « tâches en retard » est une RÉUTILISATION directe de
     `lister_les_taches_en_retard` (LOT 7, `T12`), jamais une seconde requête
     qui pourrait diverger ;
  5. « derniers imports en échec » filtre sur `failed` ou des lignes
     rejetées, jamais les imports réussis, et respecte la limite de cinq ;
  6. `resoudre_le_perimetre_du_tableau_de_bord` refuse `OFFICE` seul (aucune
     portée), contrairement aux quatre autres rôles du §15.1.

Ce fichier ne reteste PAS `exiger_un_role_dans_l_entite` ni
`resoudre_les_permissions` : des briques génériques, déjà prouvées ailleurs,
reprises sans modification par la route de `T5`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.administration.perimetre import (
    PerimetreDuTableauDeBord,
    resoudre_le_perimetre_du_tableau_de_bord,
)
from app.administration.tableau_de_bord import lire_le_tableau_de_bord
from app.configuration.settings import Parametres
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur

MARQUEUR = "L9T5"
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
            "VALUES (:email, :normalise, 'Tableau', :s, 'active') RETURNING id"
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


def _metier(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO job_catalog (entity_id, code, label) VALUES (:e, :c, :l) RETURNING id"),
        {"e": entite, "c": code, "l": code},
    ).scalar_one()


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


def _completer_le_profil(
    cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID, cercle: uuid.UUID
) -> None:
    """Pose les TROIS relations comptees qui rendent un profil ACTIF complet,
    plus un metier — pose par realisme, mais plus compte depuis `DEC-675`
    (LOT 11 `T5`) : voir `test_un_metier_absent_seul_ne_rend_PLUS_un_profil_incomplet`.
    """
    metier = _metier(cx, entite, f"M-{uuid.uuid4().hex[:6]}")
    debut = ANCRAGE - dt.timedelta(days=60)
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, 'principal', :d)"
        ),
        {"e": entite, "m": appartenance, "c": cercle, "d": debut},
    )
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_id, entity_membership_id, "
            "job_catalog_id, starts_at) VALUES (:e, :m, :j, :d)"
        ),
        {"e": entite, "m": appartenance, "j": metier, "d": debut},
    )
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, starts_at) VALUES (:e, :m, 'intercontract', :d)"
        ),
        {"e": entite, "m": appartenance, "d": debut},
    )
    dsm_personne = _personne(cx, f"DSM-{uuid.uuid4().hex[:6]}")
    _dsm_responsable(cx, dsm_personne, entite)
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at) VALUES (:e, :m, :d, :date)"
        ),
        {"e": entite, "m": appartenance, "d": dsm_personne, "date": debut},
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


def _booster(cx: Connection, personne: uuid.UUID, entite: uuid.UUID, cercle: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :p, :d)"
        ),
        {
            "p": personne,
            "e": entite,
            "t": TypeResponsabilite.BOOSTER.value,
            "c": cercle,
            "d": ANCRAGE - dt.timedelta(days=90),
        },
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
    cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID, version: uuid.UUID, *, etat: str
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_instance (entity_id, entity_membership_id, "
            "template_version_id, reference_date, state) "
            "VALUES (:e, :m, :v, :d, :etat) RETURNING id"
        ),
        {"e": entite, "m": appartenance, "v": version, "d": ANCRAGE.date(), "etat": etat},
    ).scalar_one()


def _tache_de_reference(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_task_reference (entity_id, code, title) "
            "VALUES (:e, :c, :t) RETURNING id"
        ),
        {"e": entite, "c": code, "t": f"Titre {code}"},
    ).scalar_one()


def _lot_d_import(
    cx: Connection, entite: uuid.UUID, *, etat: str, lignes_rejetees: int = 0
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO import_batch (entity_id, source_filename, source_checksum_sha256, "
            "state, total_rows, rejected_rows) "
            "VALUES (:e, :f, :h, :etat, 10, :rejetees) RETURNING id"
        ),
        {
            "e": entite,
            "f": f"{MARQUEUR}.csv",
            "h": uuid.uuid4().hex,
            "etat": etat,
            "rejetees": lignes_rejetees,
        },
    ).scalar_one()


@pytest.mark.integration
def test_TEMOIN_profils_actifs_et_arrivees_futures_comptent_juste_en_portee_ENTITE(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ENT1")
    acteur = _personne(cx, "ESM1")
    _appartenance(cx, entite, _personne(cx, "ACTIF1"), etat="active")
    _appartenance(cx, entite, _personne(cx, "ACTIF2"), etat="active")
    _appartenance(cx, entite, _personne(cx, "FUTUR1"), etat="future")

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
    )

    assert tableau.profils_actifs == 2
    assert tableau.arrivees_futures == 1


@pytest.mark.integration
def test_profils_incomplets_compte_un_profil_ACTIF_auquel_il_manque_une_relation(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ENT2")
    acteur = _personne(cx, "ESM2")
    cercle = _cercle(cx, entite, "C1")

    complet = _appartenance(cx, entite, _personne(cx, "COMPLET"), etat="active")
    _completer_le_profil(cx, entite, complet, cercle)

    #  Incomplet : AUCUNE des trois relations comptees n'est posee.
    _appartenance(cx, entite, _personne(cx, "NU"), etat="active")

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
    )

    assert tableau.profils_actifs == 2
    assert tableau.profils_incomplets == 1


@pytest.mark.integration
def test_un_metier_absent_seul_ne_rend_PLUS_un_profil_incomplet(cx: Connection) -> None:
    """`DEC-675` (LOT 11 `T5`) : le metier n'est plus l'une des relations comptees.

    Temoin POSITIF apparie au test precedent (negatif, §7.39) : un profil qui
    porte les TROIS relations restantes (cercle principal, DSM, statut) mais
    AUCUN metier n'est plus compte « incomplet » — avant ce retrait, il
    l'aurait ete.
    """
    entite = _entite(cx, "ENT2-SANSMETIER")
    acteur = _personne(cx, "ESM2-SANSMETIER")
    cercle = _cercle(cx, entite, "C1")
    debut = ANCRAGE - dt.timedelta(days=60)

    sans_metier = _appartenance(cx, entite, _personne(cx, "SANSMETIER"), etat="active")
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, 'principal', :d)"
        ),
        {"e": entite, "m": sans_metier, "c": cercle, "d": debut},
    )
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, starts_at) VALUES (:e, :m, 'intercontract', :d)"
        ),
        {"e": entite, "m": sans_metier, "d": debut},
    )
    dsm_personne = _personne(cx, "DSM2-SANSMETIER")
    _dsm_responsable(cx, dsm_personne, entite)
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at) VALUES (:e, :m, :d, :date)"
        ),
        {"e": entite, "m": sans_metier, "d": dsm_personne, "date": debut},
    )

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
    )

    assert tableau.profils_actifs == 1
    assert tableau.profils_incomplets == 0


@pytest.mark.integration
def test_onboardings_actifs_exclut_les_instances_non_ACTIVE(cx: Connection) -> None:
    entite = _entite(cx, "ENT3")
    acteur = _personne(cx, "ESM3")
    version = _modele_et_version(cx, entite)
    appartenance_active = _appartenance(cx, entite, _personne(cx, "ONB1"), etat="active")
    appartenance_archivee = _appartenance(cx, entite, _personne(cx, "ONB2"), etat="active")
    _instance(cx, entite, appartenance_active, version, etat="active")
    _instance(cx, entite, appartenance_archivee, version, etat="archived")

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
    )

    assert tableau.onboardings_actifs == 1


@pytest.mark.integration
def test_taches_en_retard_reutilise_le_service_du_suivi_sans_le_recopier(cx: Connection) -> None:
    entite = _entite(cx, "ENT4")
    acteur = _personne(cx, "ESM4")
    version = _modele_et_version(cx, entite)
    appartenance = _appartenance(cx, entite, _personne(cx, "RETARD"), etat="active")
    instance = _instance(cx, entite, appartenance, version, etat="active")
    reference = _tache_de_reference(cx, entite, f"TR-{uuid.uuid4().hex[:6]}")
    cx.execute(
        text(
            "INSERT INTO onboarding_instance_task (entity_id, onboarding_instance_id, "
            "task_reference_id, title_snapshot, required, state, due_at) "
            "VALUES (:e, :i, :r, 'Tache en retard', true, 'todo', :d)"
        ),
        {"e": entite, "i": instance, "r": reference, "d": ANCRAGE - dt.timedelta(days=1)},
    )

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
    )

    assert tableau.taches_en_retard == 1


@pytest.mark.integration
def test_derniers_imports_en_echec_filtre_et_exclut_les_reussis(cx: Connection) -> None:
    entite = _entite(cx, "ENT5")
    acteur = _personne(cx, "ESM5")
    _lot_d_import(cx, entite, etat="completed", lignes_rejetees=0)
    echoue = _lot_d_import(cx, entite, etat="failed")
    avec_rejets = _lot_d_import(cx, entite, etat="completed", lignes_rejetees=3)

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        perimetre=PerimetreDuTableauDeBord.ENTITE,
        instant=ANCRAGE,
    )

    identifiants = {i.id for i in tableau.derniers_imports_en_echec}
    assert identifiants == {echoue, avec_rejets}


@pytest.mark.integration
def test_derniers_imports_en_echec_est_VIDE_pour_un_DSM(cx: Connection) -> None:
    entite = _entite(cx, "ENT6")
    acteur = _personne(cx, "DSM6")
    _lot_d_import(cx, entite, etat="failed")

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.DSM}),
        perimetre=PerimetreDuTableauDeBord.CONSULTANTS,
        instant=ANCRAGE,
    )

    assert tableau.derniers_imports_en_echec == ()


@pytest.mark.integration
def test_perimetre_CONSULTANTS_ne_compte_que_les_profils_du_DSM(cx: Connection) -> None:
    entite = _entite(cx, "ENT7")
    dsm_personne = _personne(cx, "DSM7")
    _dsm_responsable(cx, dsm_personne, entite)

    son_consultant = _appartenance(cx, entite, _personne(cx, "SIEN"), etat="active")
    _dsm_de_ce_consultant(cx, entite, son_consultant, dsm_personne)
    #  Un AUTRE consultant, actif, mais sans lien DSM avec cet acteur.
    _appartenance(cx, entite, _personne(cx, "AUTRE"), etat="active")

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=dsm_personne,
        roles=frozenset({RoleDeLaMatrice.DSM}),
        perimetre=PerimetreDuTableauDeBord.CONSULTANTS,
        instant=ANCRAGE,
    )

    assert tableau.profils_actifs == 1


@pytest.mark.integration
def test_perimetre_CERCLE_ne_compte_que_les_profils_du_cercle_du_booster(cx: Connection) -> None:
    entite = _entite(cx, "ENT8")
    booster_personne = _personne(cx, "BOOST8")
    cercle_du_booster = _cercle(cx, entite, "CB")
    autre_cercle = _cercle(cx, entite, "CA")
    _booster(cx, booster_personne, entite, cercle_du_booster)

    dans_le_cercle = _appartenance(cx, entite, _personne(cx, "DANS"), etat="active")
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, 'principal', :d)"
        ),
        {"e": entite, "m": dans_le_cercle, "c": cercle_du_booster, "d": ANCRAGE},
    )
    hors_du_cercle = _appartenance(cx, entite, _personne(cx, "HORS"), etat="active")
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, 'principal', :d)"
        ),
        {"e": entite, "m": hors_du_cercle, "c": autre_cercle, "d": ANCRAGE},
    )

    tableau = lire_le_tableau_de_bord(
        cx,
        entite=entite,
        acteur=booster_personne,
        roles=frozenset({RoleDeLaMatrice.BOOSTER}),
        perimetre=PerimetreDuTableauDeBord.CERCLE,
        instant=ANCRAGE,
    )

    assert tableau.profils_actifs == 1


def test_OFFICE_seul_est_refuse_par_la_resolution_du_perimetre() -> None:
    assert (
        resoudre_le_perimetre_du_tableau_de_bord(
            roles=frozenset({RoleDeLaMatrice.RESPONSABLE_DE_BUREAU})
        )
        is None
    )


def test_les_cinq_roles_du_15_1_resolvent_une_portee() -> None:
    for role, attendue in (
        (RoleDeLaMatrice.ESM, PerimetreDuTableauDeBord.ENTITE),
        (RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE, PerimetreDuTableauDeBord.ENTITE),
        (RoleDeLaMatrice.SUPER_ADMINISTRATEUR, PerimetreDuTableauDeBord.ENTITE),
        (RoleDeLaMatrice.DSM, PerimetreDuTableauDeBord.CONSULTANTS),
        (RoleDeLaMatrice.BOOSTER, PerimetreDuTableauDeBord.CERCLE),
    ):
        assert resoudre_le_perimetre_du_tableau_de_bord(roles=frozenset({role})) == attendue
