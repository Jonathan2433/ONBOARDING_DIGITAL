"""Une instance de parcours depuis la date d'arrivee — LOT 7, `T7`.

matrice §8.1 : « Affecter un parcours », « Consulter son parcours », «
Consulter le parcours d'un collaborateur ».

L'ORDRE DE PRIORITE DU MODELE — ARBITRAGE DE JONATHAN DU 27/09/2026

  `DSM` > `CIRCLE` > `ENTITY` > `GLOBAL` : le plus specifique gagne. Quatre
  temoins postent les QUATRE modeles publies en meme temps sur le MEME
  statut, et retirent le niveau gagnant un par un pour prouver que chaque
  echelon cede sa place au suivant — jamais un seul modele a la fois, ce qui
  ne prouverait qu'une absence de refus, pas un ORDRE.

`DSM` A ICI « CONSULTANTS » PLEIN — CONTRAIREMENT A LA FICHE D'ARRIVEE (T2)

  Piege n°1 de `fiche-lot-7.md` §2.1 : DSM/BOOST consultent le parcours d'un
  collaborateur, ils n'agissent pas sur SES taches. Deux temoins le prouvent
  dans les deux sens : DSM/BOOST LISENT le parcours d'un consultant rattache,
  ce que `T2` leur refusait sur la fiche.

« AFFECTER » N'A PAS DE `Soi` — LA SEULE ASYMETRIE ENTRE LES DEUX GESTES

  `NEW` ne peut jamais s'affecter lui-meme un parcours : un temoin le prouve
  explicitement, la ou la lecture l'accepterait.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.csrf import EN_TETE_JETON, jeton_pour
from app.auth.sessions import empreinte_de_session, ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_MODELES = "/api/v1/entities/{code}/onboarding/templates"
CHEMIN_VERSIONS = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions"
CHEMIN_TACHES = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/tasks"
CHEMIN_PUBLICATION = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/publication"
)
CHEMIN_PARCOURS = "/api/v1/entities/{code}/people/{appartenance}/onboarding-parcours"

#  DERIVEE DE `now()`, JAMAIS FIGEE — §7.47 du LOT 6 : une ancre absolue est
#  une bombe a retardement datee (ou, ici, un futur qui n'est pas encore
#  arrive). Les sessions ouvertes avec cette ancre doivent rester dans le
#  PASSE au moment ou la route relit `now()` pour son verrou d'activite.
ANCRAGE = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=10)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


def _personne(cx: Connection, marqueur: str, suffixe: str) -> uuid.UUID:
    adresse = f"{marqueur}-{suffixe}@exemple.test"
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, :prenom, 'T7', 'active') RETURNING id"
                ),
                {"a": adresse, "prenom": suffixe},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection, entite: uuid.UUID, personne: uuid.UUID, *, arrivee: dt.date
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'draft') RETURNING id"
                ),
                {"p": personne, "e": entite, "arrivee": arrivee},
            ).scalar_one()
        )
    )


def _statut_intercontrat(cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment "
            "(entity_id, entity_membership_id, status, starts_at) "
            "VALUES (:e, :m, 'intercontract', :d)"
        ),
        {"e": entite, "m": appartenance, "d": ANCRAGE - dt.timedelta(days=60)},
    )


def _dsm_de_ce_consultant(
    cx: Connection, entite: uuid.UUID, consultant: uuid.UUID, dsm_personne: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, "
            "dsm_person_id, starts_at) VALUES (:e, :c, :d, :date)"
        ),
        {"e": entite, "c": consultant, "d": dsm_personne, "date": ANCRAGE - dt.timedelta(days=60)},
    )


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


def _responsabilite(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID, type_resp: str, *, cercle: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :p, :d)"
        ),
        {
            "p": personne,
            "e": entite,
            "t": type_resp,
            "c": cercle,
            "d": ANCRAGE - dt.timedelta(days=90),
        },
    )


def _dsm(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": ANCRAGE - dt.timedelta(days=90)},
    )


def _esm(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": ANCRAGE - dt.timedelta(days=90)},
    )


def _role_technique(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID | None, role: str
) -> None:
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, :r, :d)"
        ),
        {"p": personne, "e": entite, "r": role, "d": ANCRAGE - dt.timedelta(days=90)},
    )


def _tache_de_reference(cx: Connection, entite: uuid.UUID | None, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO onboarding_task_reference (entity_id, code, title) "
                    "VALUES (:e, :c, :t) RETURNING id"
                ),
                {"e": entite, "c": code, "t": f"Titre {code}"},
            ).scalar_one()
        )
    )


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _appeler_ecriture(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        return client.post(chemin, json={}, headers=entetes)


def _appeler_lecture(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t7l7{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres, "marqueur": marqueur}

    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-e", "nom": marqueur},
        ).scalar_one()
        r["entite"] = entite
        r["code"] = f"{marqueur}-e"

        cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Nantes', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-autre", "nom": f"{marqueur}-autre"},
        )
        r["autre_code"] = f"{marqueur}-autre"

        cercle = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
        ).scalar_one()
        r["cercle"] = cercle

        autre_cercle = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 1) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-autre-cercle", "n": f"{marqueur}-autre-cercle"},
        ).scalar_one()
        r["autre_cercle"] = autre_cercle

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(
            cx, entite, r["dsm_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _dsm(cx, r["dsm_personne"], entite)

        r["esm_personne"] = _personne(cx, marqueur, "esm")
        _appartenance(
            cx, entite, r["esm_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _esm(cx, r["esm_personne"], entite)

        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(
            cx, entite, r["booster_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _responsabilite(
            cx, r["booster_personne"], entite, TypeResponsabilite.BOOSTER.value, cercle=cercle
        )

        r["office_personne"] = _personne(cx, marqueur, "office")
        _appartenance(
            cx, entite, r["office_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        office = cx.execute(
            text(
                "INSERT INTO office (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-bureau", "n": f"{marqueur}-bureau"},
        ).scalar_one()
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, office_id, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'OFFICE_MANAGER', :o, :p, :d)"
            ),
            {
                "p": r["office_personne"],
                "e": entite,
                "o": office,
                "d": ANCRAGE - dt.timedelta(days=90),
            },
        )

        r["adm_e_personne"] = _personne(cx, marqueur, "adme")
        _appartenance(
            cx, entite, r["adm_e_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _role_technique(cx, r["adm_e_personne"], entite, TypeRoleTechnique.ENTITY_ADMIN.value)

        r["super_personne"] = _personne(cx, marqueur, "super")
        _role_technique(cx, r["super_personne"], None, TypeRoleTechnique.SUPER_ADMIN.value)

        r["emp_personne"] = _personne(cx, marqueur, "emp")
        _appartenance(
            cx, entite, r["emp_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )

        r["tache_globale"] = _tache_de_reference(cx, None, f"{marqueur}-tache-globale")

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM onboarding_task_event WHERE onboarding_instance_task_id IN "
            "(SELECT id FROM onboarding_instance_task WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif))",
            "DELETE FROM onboarding_instance_task WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM onboarding_instance WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM onboarding_template_task WHERE template_version_id IN "
            "(SELECT id FROM onboarding_template_version WHERE template_id IN "
            "(SELECT id FROM onboarding_template WHERE name LIKE :motif))",
            "DELETE FROM onboarding_template_version WHERE template_id IN "
            "(SELECT id FROM onboarding_template WHERE name LIKE :motif)",
            "DELETE FROM onboarding_template WHERE name LIKE :motif",
            "DELETE FROM onboarding_task_reference WHERE code LIKE :motif_code",
            "DELETE FROM professional_status_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM dsm_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            #  LOT 10, `T6` : affecter un parcours (route HTTP de ce fichier)
            #  ecrit desormais `audit_event` aussi — meme classe que `T2`/`T3`
            #  (§7.30).
            "DELETE FROM audit_event WHERE actor_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM audit_event WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM office WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM person WHERE email LIKE :motif_personne",
            "DELETE FROM entity WHERE code LIKE :motif",
        ):
            menage.execute(
                text(requete),
                {
                    "motif": f"{marqueur}%",
                    "motif_personne": f"{marqueur}%",
                    "motif_code": f"{marqueur}%",
                },
            )


def _creer_modele_publie(
    parametres: Parametres,
    code_entite: str,
    jeton: str | None,
    *,
    name: str,
    portee: str,
    scope_person_id: uuid.UUID | None = None,
    scope_circle_id: uuid.UUID | None = None,
    tache: uuid.UUID,
) -> uuid.UUID:
    """Cree un modele, une version, une tache, puis PUBLIE — les quatre routes
    reelles, jamais une ecriture directe en base."""
    corps: dict[str, Any] = {
        "name": name,
        "target_status": "intercontract",
        "portee": portee,
        "motif": "Decor de test",
    }
    if scope_person_id is not None:
        corps["scope_person_id"] = str(scope_person_id)
    if scope_circle_id is not None:
        corps["scope_circle_id"] = str(scope_circle_id)
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        modele = client.post(
            CHEMIN_MODELES.format(code=code_entite), json=corps, headers=entetes
        ).json()["id"]
        version = client.post(
            CHEMIN_VERSIONS.format(code=code_entite, modele=modele),
            json={"motif": "Decor de test"},
            headers=entetes,
        ).json()["id"]
        reponse_taches = client.put(
            CHEMIN_TACHES.format(code=code_entite, modele=modele, version=version),
            json={
                "taches": [{"task_reference_id": str(tache), "due_offset_days": 3}],
                "motif": "Decor de test",
            },
            headers=entetes,
        )
        assert reponse_taches.status_code == 200, reponse_taches.text
        publiee = client.post(
            CHEMIN_PUBLICATION.format(code=code_entite, modele=modele, version=version),
            json={"motif": "Decor de test"},
            headers=entetes,
        )
        assert publiee.status_code == 200, publiee.text
    return uuid.UUID(str(version))


def _affecter(parametres: Parametres, code: str, appartenance: uuid.UUID, jeton: str | None) -> Any:
    return _appeler_ecriture(
        parametres, CHEMIN_PARCOURS.format(code=code, appartenance=appartenance), jeton
    )


def _lire(parametres: Parametres, code: str, appartenance: uuid.UUID, jeton: str | None) -> Any:
    return _appeler_lecture(
        parametres, CHEMIN_PARCOURS.format(code=code, appartenance=appartenance), jeton
    )


# ===========================================================================
#  Affecter un parcours — l'ordre de priorite DSM > CIRCLE > ENTITY > GLOBAL
# ===========================================================================


@pytest.mark.integration
def test_priorite_dsm_gagne_sur_cercle_entite_et_global(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]

    version_dsm = _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-dsm",
        portee="DSM",
        scope_person_id=decor["dsm_personne"],
        tache=decor["tache_globale"],
    )
    _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-cercle",
        portee="CIRCLE",
        scope_circle_id=decor["cercle"],
        tache=decor["tache_globale"],
    )
    _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-entite",
        portee="ENTITY",
        tache=decor["tache_globale"],
    )
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-global",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )

    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-dsm-gagne")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
        _dsm_de_ce_consultant(cx, decor["entite"], consultant, decor["dsm_personne"])
        _cercle_principal(cx, decor["entite"], consultant, decor["cercle"])

    reponse = _affecter(parametres, decor["code"], consultant, esm_jeton)
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["instance"]["template_version_id"] == str(version_dsm)


@pytest.mark.integration
def test_priorite_cercle_gagne_si_pas_de_dsm(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]

    version_cercle = _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-cercle-2",
        portee="CIRCLE",
        scope_circle_id=decor["cercle"],
        tache=decor["tache_globale"],
    )
    _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-entite-2",
        portee="ENTITY",
        tache=decor["tache_globale"],
    )
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-global-2",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )

    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-cercle-gagne")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
        _cercle_principal(cx, decor["entite"], consultant, decor["cercle"])

    reponse = _affecter(parametres, decor["code"], consultant, esm_jeton)
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["instance"]["template_version_id"] == str(version_cercle)


@pytest.mark.integration
def test_priorite_entite_gagne_si_pas_de_dsm_ni_cercle(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]

    version_entite = _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-entite-3",
        portee="ENTITY",
        tache=decor["tache_globale"],
    )
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-global-3",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )

    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-entite-gagne")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(parametres, decor["code"], consultant, esm_jeton)
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["instance"]["template_version_id"] == str(version_entite)


@pytest.mark.integration
def test_seul_le_global_est_utilise_en_dernier_recours(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    super_jeton = _session(parametres, decor["super_personne"])
    marqueur = decor["marqueur"]

    version_globale = _creer_modele_publie(
        parametres,
        decor["code"],
        super_jeton,
        name=f"{marqueur}-modele-global-4",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )

    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-global-gagne")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["instance"]["template_version_id"] == str(version_globale)


@pytest.mark.integration
def test_aucun_modele_publie_est_refuse_422(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-sans-modele")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["code"] == "aucun_modele_publie"


@pytest.mark.integration
def test_sans_statut_professionnel_actif_est_refuse_422(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-sans-statut")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["code"] == "statut_professionnel_introuvable"


# ===========================================================================
#  Une seule instance active par appartenance — modele §13.5, a l'unite ET au volume
# ===========================================================================


@pytest.mark.integration
def test_une_seconde_affectation_est_refusee_409(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-double",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-double")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    premiere = _affecter(parametres, decor["code"], consultant, esm_jeton)
    assert premiere.status_code == 201, premiere.text
    seconde = _affecter(parametres, decor["code"], consultant, esm_jeton)
    assert seconde.status_code == 409, seconde.text
    assert seconde.json()["erreur"]["code"] == "parcours_deja_actif"


@pytest.mark.integration
def test_affecter_a_volume_ne_collisionne_jamais(decor: dict[str, Any]) -> None:
    """§7.26 du LOT 6 : une contrainte d'unicite s'eprouve au VOLUME."""
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-volume",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )
    volume = 40
    with moteur(parametres).begin() as cx:
        consultants = []
        for i in range(volume):
            personne = _personne(cx, marqueur, f"volume-{i}")
            appartenance = _appartenance(cx, decor["entite"], personne, arrivee=ANCRAGE.date())
            _statut_intercontrat(cx, decor["entite"], appartenance)
            consultants.append(appartenance)

    instances = set()
    for consultant in consultants:
        reponse = _affecter(parametres, decor["code"], consultant, esm_jeton)
        assert reponse.status_code == 201, reponse.text
        instances.add(reponse.json()["instance"]["id"])
    assert len(instances) == volume


# ===========================================================================
#  Snapshot des taches — echeances calculees, overrides copies
# ===========================================================================


@pytest.mark.integration
def test_affecter_calcule_les_echeances_depuis_larrivee(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-echeance",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )
    arrivee = ANCRAGE.date() - dt.timedelta(days=5)
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-echeance")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=arrivee)
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(parametres, decor["code"], consultant, esm_jeton)
    assert reponse.status_code == 201, reponse.text
    taches = reponse.json()["taches"]
    assert len(taches) == 1
    attendue = dt.datetime.combine(arrivee, dt.time.min, tzinfo=dt.UTC) + dt.timedelta(days=3)
    obtenue = dt.datetime.fromisoformat(taches[0]["due_at"].replace("Z", "+00:00"))
    assert obtenue == attendue


# ===========================================================================
#  Permissions — affecter (pas de Soi, DSM/Booster rattaches uniquement)
# ===========================================================================


@pytest.mark.integration
def test_un_DSM_affecte_le_parcours_de_SON_consultant(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-dsm-affecte",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-de-dsm")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
        _dsm_de_ce_consultant(cx, decor["entite"], consultant, decor["dsm_personne"])

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_un_DSM_NON_rattache_NE_affecte_PAS(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-sans-dsm")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_BOOSTER_NE_affecte_PAS_hors_de_SON_cercle(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-autre-cercle")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
        _cercle_principal(cx, decor["entite"], consultant, decor["autre_cercle"])

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["booster_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_un_RESPONSABLE_DE_BUREAU_NE_affecte_AUCUN_parcours(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-office")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, decor["office_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_le_NOUVEL_ARRIVANT_NE_S_affecte_PAS_lui_meme(decor: dict[str, Any]) -> None:
    """« Affecter » n'a PAS de `Soi` — la seule asymetrie avec la lecture."""
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-soi")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)

    reponse = _affecter(
        parametres, decor["code"], consultant, _session(parametres, consultant_personne)
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_affecter_un_parcours_sur_une_appartenance_d_une_AUTRE_entite_est_404(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-isole")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())

    reponse = _affecter(
        parametres, decor["autre_code"], consultant, _session(parametres, decor["super_personne"])
    )
    assert reponse.status_code == 404, reponse.text


@pytest.mark.integration
def test_affecter_un_parcours_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-anon")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())

    reponse = _affecter(parametres, decor["code"], consultant, None)
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  Lecture du parcours — Soi, DSM/Booster rattaches EN LECTURE (asymetrie T2)
# ===========================================================================


@pytest.mark.integration
def test_lire_son_propre_parcours_avant_toute_affectation_rend_des_nuls(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        personne = _personne(cx, marqueur, "lecture-vide")
        appartenance = _appartenance(cx, decor["entite"], personne, arrivee=ANCRAGE.date())

    reponse = _lire(parametres, decor["code"], appartenance, _session(parametres, personne))
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["instance"] is None
    assert corps["progression"] is None
    assert corps["prochaine_tache"] is None
    assert corps["taches"] == []


@pytest.mark.integration
def test_un_DSM_LIT_le_parcours_de_SON_consultant(decor: dict[str, Any]) -> None:
    """Contrairement a `T2` (fiche non publiee), DSM lit PLEINEMENT ici."""
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-lu-par-dsm")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _dsm_de_ce_consultant(cx, decor["entite"], consultant, decor["dsm_personne"])

    reponse = _lire(
        parametres, decor["code"], consultant, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_DSM_NON_rattache_NE_lit_PAS(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-non-lu")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())

    reponse = _lire(
        parametres, decor["code"], consultant, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_BOOSTER_lit_le_parcours_d_un_membre_de_SON_cercle(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-du-cercle")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _cercle_principal(cx, decor["entite"], consultant, decor["cercle"])

    reponse = _lire(
        parametres, decor["code"], consultant, _session(parametres, decor["booster_personne"])
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_EMPLOYE_NU_NE_lit_PAS_le_parcours_d_un_AUTRE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-prive")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())

    reponse = _lire(
        parametres, decor["code"], consultant, _session(parametres, decor["emp_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_lire_le_parcours_apres_affectation_rend_taches_et_progression(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    marqueur = decor["marqueur"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{marqueur}-modele-lecture",
        portee="GLOBAL",
        tache=decor["tache_globale"],
    )
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, "consultant-relu")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
    _affecter(parametres, decor["code"], consultant, esm_jeton)

    reponse = _lire(parametres, decor["code"], consultant, esm_jeton)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["instance"] is not None
    assert corps["progression"] == {
        "taches_obligatoires_totales": 1,
        "taches_obligatoires_terminees": 0,
    }
    assert corps["prochaine_tache"]["state"] == "todo"
    assert len(corps["taches"]) == 1


@pytest.mark.integration
def test_lire_un_parcours_sur_une_appartenance_INCONNUE_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _lire(
        parametres, decor["code"], uuid.uuid4(), _session(parametres, decor["super_personne"])
    )
    assert reponse.status_code == 404, reponse.text


@pytest.mark.integration
def test_lire_un_parcours_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        personne = _personne(cx, marqueur, "lecture-anon")
        appartenance = _appartenance(cx, decor["entite"], personne, arrivee=ANCRAGE.date())

    reponse = _lire(parametres, decor["code"], appartenance, None)
    assert reponse.status_code == 401, reponse.text
