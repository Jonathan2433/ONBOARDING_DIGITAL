"""Les modeles d'onboarding et leurs versions — LOT 7, `T5`.

matrice §9 : « Creer un modele », « Creer une nouvelle version », « Ajouter ou
reordonner des taches ».

ICI, CONTRAIREMENT AU CATALOGUE DE `T4`, `Consultants` ET `Cercle` NE SE
REDUISENT PAS A L'ENTITE

  `onboarding_template` porte de vraies colonnes de portee — `scope_person_id`,
  `scope_circle_id`. Un DSM ne peut donc gerer QUE ses propres modeles
  (`scope_person_id == lui-meme`), un Booster QUE ceux de SON cercle. Les
  temoins d'asymetrie le prouvent : un DSM refuse sur le modele d'un AUTRE
  DSM, un Booster refuse sur le cercle d'un AUTRE Booster — alors qu'un ESM/
  ADM-E/SUPER gere l'un comme l'autre (portee ENTITE, meme parti que
  `ROLES_DE_PORTEE_ENTITE` du LOT 6).

LE TEMOIN DE CETTE SOUS-ETAPE : L'IMMUABILITE D'UNE VERSION PUBLIEE

  Aucune route de `T5` ne publie — `T6`. Le decor force donc `state =
  'published'` DIRECTEMENT en base, exactement comme les decors precedents
  ecrivent des etats qu'aucune route ne sait encore produire.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
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
from app.onboarding.perimetre import (
    ROLES_DE_GESTION_DES_MODELES,
    ROLES_DE_RESTAURATION_DES_MODELES,
)
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur

#  Ancre sur `__file__`, jamais sur le repertoire de travail — §7.28, l'ecart
#  qui a fait diverger un compte de tests selon d'ou `pytest` est lance.
MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_MODELES = "/api/v1/entities/{code}/onboarding/templates"
CHEMIN_VERSIONS = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions"
CHEMIN_TACHES = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/tasks"

ANCRAGE = dt.datetime(2026, 9, 26, 9, 0, tzinfo=dt.UTC)


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
                    "account_state) VALUES (:a, :a, :prenom, 'T5', 'active') RETURNING id"
                ),
                {"a": adresse, "prenom": suffixe},
            ).scalar_one()
        )
    )


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'draft') RETURNING id"
                ),
                {"p": personne, "e": entite, "arrivee": (ANCRAGE - dt.timedelta(days=30)).date()},
            ).scalar_one()
        )
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
            "d": ANCRAGE - dt.timedelta(days=1),
        },
    )


def _dsm(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    """DSM — la contrainte du modele exige `circle_id`/`office_id` NULS."""
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
    )


def _esm(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
    )


def _role_technique(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID | None, role: str
) -> None:
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, :r, :d)"
        ),
        {"p": personne, "e": entite, "r": role, "d": ANCRAGE - dt.timedelta(days=1)},
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


def _appeler_lecture(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


def _appeler_ecriture(
    parametres: Parametres,
    chemin: str,
    jeton: str | None,
    corps: dict[str, Any],
    *,
    methode: str = "POST",
) -> Any:
    """Ecriture protegee par les deux barrieres CSRF — §7.4, `DEC-531`."""
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        if methode == "PUT":
            return client.put(chemin, json=corps, headers=entetes)
        return client.post(chemin, json=corps, headers=entetes)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite, une AUTRE (isolement), deux cercles, deux DSM, un porteur par role."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t5l7{uuid.uuid4().hex[:10]}"
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

        autre_entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Nantes', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-autre", "nom": f"{marqueur}-autre"},
        ).scalar_one()
        r["autre_entite"] = autre_entite
        r["autre_code"] = f"{marqueur}-autre"

        cercle = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
        ).scalar_one()
        r["cercle"] = cercle

        #  Un SECOND cercle de la MEME entite, dont le Booster du decor n'est
        #  PAS responsable — le temoin d'asymetrie.
        autre_cercle = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 1) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-autre-cercle", "n": f"{marqueur}-autre-cercle"},
        ).scalar_one()
        r["autre_cercle"] = autre_cercle

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(cx, entite, r["dsm_personne"])
        _dsm(cx, r["dsm_personne"], entite)

        #  Un SECOND DSM, actif lui aussi — le temoin d'asymetrie du DSM.
        r["autre_dsm_personne"] = _personne(cx, marqueur, "autre-dsm")
        _appartenance(cx, entite, r["autre_dsm_personne"])
        _dsm(cx, r["autre_dsm_personne"], entite)

        r["esm_personne"] = _personne(cx, marqueur, "esm")
        _appartenance(cx, entite, r["esm_personne"])
        _esm(cx, r["esm_personne"], entite)

        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(cx, entite, r["booster_personne"])
        _responsabilite(
            cx, r["booster_personne"], entite, TypeResponsabilite.BOOSTER.value, cercle=cercle
        )

        r["office_personne"] = _personne(cx, marqueur, "office")
        _appartenance(cx, entite, r["office_personne"])
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
                "d": ANCRAGE - dt.timedelta(days=1),
            },
        )

        r["adm_e_personne"] = _personne(cx, marqueur, "adme")
        _appartenance(cx, entite, r["adm_e_personne"])
        _role_technique(cx, r["adm_e_personne"], entite, TypeRoleTechnique.ENTITY_ADMIN.value)

        r["super_personne"] = _personne(cx, marqueur, "super")
        _role_technique(cx, r["super_personne"], None, TypeRoleTechnique.SUPER_ADMIN.value)

        r["emp_personne"] = _personne(cx, marqueur, "emp")
        _appartenance(cx, entite, r["emp_personne"])

        r["tache_entite"] = _tache_de_reference(cx, entite, f"{marqueur}-tache-entite")
        r["tache_globale"] = _tache_de_reference(cx, None, f"{marqueur}-tache-globale")
        r["tache_autre_entite"] = _tache_de_reference(
            cx, autre_entite, f"{marqueur}-tache-autre-entite"
        )

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM onboarding_template_task WHERE template_version_id IN "
            "(SELECT id FROM onboarding_template_version WHERE template_id IN "
            "(SELECT id FROM onboarding_template WHERE name LIKE :motif))",
            "DELETE FROM onboarding_template_version WHERE template_id IN "
            "(SELECT id FROM onboarding_template WHERE name LIKE :motif)",
            "DELETE FROM onboarding_template WHERE name LIKE :motif",
            "DELETE FROM onboarding_task_reference WHERE code LIKE :motif_code",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
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


def _creer_modele(
    parametres: Parametres,
    code_entite: str,
    jeton: str | None,
    *,
    name: str,
    portee: str,
    target_status: str = "mission",
    scope_person_id: uuid.UUID | None = None,
    scope_circle_id: uuid.UUID | None = None,
) -> Any:
    corps: dict[str, Any] = {"name": name, "target_status": target_status, "portee": portee}
    if scope_person_id is not None:
        corps["scope_person_id"] = str(scope_person_id)
    if scope_circle_id is not None:
        corps["scope_circle_id"] = str(scope_circle_id)
    return _appeler_ecriture(parametres, CHEMIN_MODELES.format(code=code_entite), jeton, corps)


def _lister_les_modeles(parametres: Parametres, code_entite: str, jeton: str | None) -> Any:
    return _appeler_lecture(parametres, CHEMIN_MODELES.format(code=code_entite), jeton)


def _creer_version(
    parametres: Parametres, code_entite: str, modele: uuid.UUID, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres, CHEMIN_VERSIONS.format(code=code_entite, modele=modele), jeton, {}
    )


def _definir_les_taches(
    parametres: Parametres,
    code_entite: str,
    modele: uuid.UUID,
    version: uuid.UUID,
    jeton: str | None,
    taches: list[dict[str, Any]],
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_TACHES.format(code=code_entite, modele=modele, version=version),
        jeton,
        {"taches": taches},
        methode="PUT",
    )


def _forcer_l_etat_de_la_version(parametres: Parametres, version: uuid.UUID, etat: str) -> None:
    """Ecriture DIRECTE — aucune route de `T5` ne publie encore, c'est `T6`."""
    with moteur(parametres).begin() as cx:
        cx.execute(
            text("UPDATE onboarding_template_version SET state = :s WHERE id = :v"),
            {"s": etat, "v": version},
        )


# ===========================================================================
#  Creer un modele — matrice §9, quatre portees
# ===========================================================================


@pytest.mark.integration
def test_un_DSM_cree_un_modele_pour_LUI_MEME(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["dsm_personne"]),
        name=f"{decor['marqueur']}-modele-dsm",
        portee="DSM",
        scope_person_id=decor["dsm_personne"],
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["scope_type"] == "DSM"
    assert corps["scope_person_id"] == str(decor["dsm_personne"])
    assert corps["entity_id"] == str(decor["entite"])


@pytest.mark.integration
def test_un_DSM_NE_cree_PAS_de_modele_pour_un_AUTRE_DSM(decor: dict[str, Any]) -> None:
    """§9.1 : « destine a SES consultants » — jamais a un autre DSM, meme actif."""
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["dsm_personne"]),
        name=f"{decor['marqueur']}-modele-dsm-refuse",
        portee="DSM",
        scope_person_id=decor["autre_dsm_personne"],
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_ESM_cree_un_modele_ENTITY(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-esm",
        portee="ENTITY",
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["entity_id"] == str(decor["entite"])


@pytest.mark.integration
def test_un_ESM_cree_un_modele_DSM_pour_N_IMPORTE_QUEL_DSM_ACTIF(decor: dict[str, Any]) -> None:
    """Portee ENTITE : un ESM gere aussi ce qu'un role LOCAL gererait — LOT 6."""
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-esm-pour-dsm",
        portee="DSM",
        scope_person_id=decor["autre_dsm_personne"],
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_un_ESM_cree_un_modele_CIRCLE_pour_N_IMPORTE_QUEL_CERCLE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-esm-pour-cercle",
        portee="CIRCLE",
        scope_circle_id=decor["autre_cercle"],
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_un_BOOSTER_cree_un_modele_pour_SON_cercle(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["booster_personne"]),
        name=f"{decor['marqueur']}-modele-booster",
        portee="CIRCLE",
        scope_circle_id=decor["cercle"],
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["scope_circle_id"] == str(decor["cercle"])


@pytest.mark.integration
def test_un_BOOSTER_NE_cree_PAS_pour_un_AUTRE_cercle(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["booster_personne"]),
        name=f"{decor['marqueur']}-modele-booster-refuse",
        portee="CIRCLE",
        scope_circle_id=decor["autre_cercle"],
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_ADM_E_cree_un_modele_ENTITY(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["adm_e_personne"]),
        name=f"{decor['marqueur']}-modele-adme",
        portee="ENTITY",
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_SEUL_SUPER_cree_un_modele_GLOBAL(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        name=f"{decor['marqueur']}-modele-global",
        portee="GLOBAL",
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["entity_id"] is None


@pytest.mark.integration
def test_un_ESM_NE_cree_PAS_de_modele_GLOBAL(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-esm-global-refuse",
        portee="GLOBAL",
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_RESPONSABLE_DE_BUREAU_NE_cree_AUCUN_modele(decor: dict[str, Any]) -> None:
    """`OFFICE` est a TIRET partout au §9 — quatrieme occurrence de ce piege."""
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["office_personne"]),
        name=f"{decor['marqueur']}-modele-office-refuse",
        portee="ENTITY",
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_EMPLOYE_NU_NE_cree_AUCUN_modele(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["emp_personne"]),
        name=f"{decor['marqueur']}-modele-emp-refuse",
        portee="ENTITY",
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_creer_un_modele_DSM_sans_scope_person_id_est_422(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["dsm_personne"]),
        name=f"{decor['marqueur']}-modele-dsm-incoherent",
        portee="DSM",
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["code"] == "portee_de_modele_incoherente"


@pytest.mark.integration
def test_creer_un_modele_ENTITY_avec_un_scope_circle_id_est_422(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-entity-incoherent",
        portee="ENTITY",
        scope_circle_id=decor["cercle"],
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["code"] == "portee_de_modele_incoherente"


@pytest.mark.integration
def test_creer_un_modele_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_modele(
        parametres, decor["code"], None, name=f"{decor['marqueur']}-anon", portee="ENTITY"
    )
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  Creer une nouvelle version — modele §13.3
# ===========================================================================


@pytest.mark.integration
def test_creer_une_version_incremente_le_numero(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-versions",
        portee="ENTITY",
    ).json()["id"]

    premiere = _creer_version(parametres, decor["code"], modele, jeton)
    assert premiere.status_code == 201, premiere.text
    assert premiere.json()["version_number"] == 1
    assert premiere.json()["state"] == "draft"

    seconde = _creer_version(parametres, decor["code"], modele, jeton)
    assert seconde.status_code == 201, seconde.text
    assert seconde.json()["version_number"] == 2


@pytest.mark.integration
def test_un_DSM_NE_cree_PAS_de_version_sur_le_modele_d_un_AUTRE_DSM(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{decor['marqueur']}-modele-autre-dsm",
        portee="DSM",
        scope_person_id=decor["autre_dsm_personne"],
    ).json()["id"]

    reponse = _creer_version(
        parametres, decor["code"], modele, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_creer_une_version_sur_un_modele_INCONNU_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer_version(
        parametres, decor["code"], uuid.uuid4(), _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "modele_introuvable"


@pytest.mark.integration
def test_creer_une_version_sur_un_modele_d_une_AUTRE_entite_est_404(
    decor: dict[str, Any],
) -> None:
    """Isolement — meme discipline que le catalogue de `T4`."""
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{decor['marqueur']}-modele-isole",
        portee="ENTITY",
    ).json()["id"]

    reponse = _creer_version(
        parametres,
        decor["autre_code"],
        modele,
        _session(parametres, decor["super_personne"]),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "modele_introuvable"


@pytest.mark.integration
def test_un_modele_GLOBAL_reste_gerable_depuis_N_IMPORTE_QUELLE_entite(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    super_jeton = _session(parametres, decor["super_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        super_jeton,
        name=f"{decor['marqueur']}-modele-global-atteint",
        portee="GLOBAL",
    ).json()["id"]

    reponse = _creer_version(parametres, decor["autre_code"], modele, super_jeton)
    assert reponse.status_code == 201, reponse.text


# ===========================================================================
#  Poser/reordonner les taches d'une version — modele §13.4
# ===========================================================================


@pytest.mark.integration
def test_definir_les_taches_pose_l_ORDRE_selon_la_liste_recue(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-modele-taches", portee="ENTITY"
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]

    reponse = _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [
            {"task_reference_id": str(decor["tache_entite"]), "due_offset_days": 1},
            {"task_reference_id": str(decor["tache_globale"]), "due_offset_days": 2},
        ],
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["nombre_de_taches"] == 2
    assert len(corps["taches"]) == 2
    ordre = [(t["task_reference_id"], t["display_order"]) for t in corps["taches"]]
    assert ordre == [
        (str(decor["tache_entite"]), 0),
        (str(decor["tache_globale"]), 1),
    ]


@pytest.mark.integration
def test_redefinir_les_taches_REORDONNE_au_lieu_d_empiler(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-reordre",
        portee="ENTITY",
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]

    _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [
            {"task_reference_id": str(decor["tache_entite"]), "due_offset_days": 1},
            {"task_reference_id": str(decor["tache_globale"]), "due_offset_days": 2},
        ],
    )
    reponse = _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [
            {"task_reference_id": str(decor["tache_globale"]), "due_offset_days": 2},
            {"task_reference_id": str(decor["tache_entite"]), "due_offset_days": 1},
        ],
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    #  REORDONNE, jamais empile : deux lignes, pas quatre.
    assert corps["nombre_de_taches"] == 2
    ordre = [(t["task_reference_id"], t["display_order"]) for t in corps["taches"]]
    assert ordre == [
        (str(decor["tache_globale"]), 0),
        (str(decor["tache_entite"]), 1),
    ]


@pytest.mark.integration
def test_une_tache_GLOBALE_est_utilisable_dans_TOUT_modele(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["super_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-avec-globale",
        portee="GLOBAL",
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]

    reponse = _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [{"task_reference_id": str(decor["tache_globale"]), "due_offset_days": 0}],
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_une_tache_D_UNE_AUTRE_entite_est_hors_perimetre(decor: dict[str, Any]) -> None:
    """Residuel nomme par `T1`, instruit ici : jamais la tache d'une AUTRE entite."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-hors-perimetre",
        portee="ENTITY",
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]

    reponse = _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [{"task_reference_id": str(decor["tache_autre_entite"]), "due_offset_days": 0}],
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["code"] == "tache_hors_perimetre_du_modele"


@pytest.mark.integration
def test_definir_les_taches_sur_une_version_PUBLIEE_est_refuse(decor: dict[str, Any]) -> None:
    """Le temoin de cette sous-etape — modele §13.3 : une version publiee est immuable."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-immuable",
        portee="ENTITY",
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]
    _forcer_l_etat_de_la_version(parametres, version, "published")

    reponse = _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [{"task_reference_id": str(decor["tache_entite"]), "due_offset_days": 0}],
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_de_modele_immuable"


@pytest.mark.integration
def test_definir_les_taches_sur_une_version_RETIREE_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-retiree",
        portee="ENTITY",
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]
    _forcer_l_etat_de_la_version(parametres, version, "retired")

    reponse = _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [{"task_reference_id": str(decor["tache_entite"]), "due_offset_days": 0}],
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_de_modele_immuable"


@pytest.mark.integration
def test_definir_les_taches_sur_une_version_INCONNUE_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-version-inconnue",
        portee="ENTITY",
    ).json()["id"]

    reponse = _definir_les_taches(parametres, decor["code"], modele, uuid.uuid4(), jeton, [])
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_de_modele_introuvable"


@pytest.mark.integration
def test_definir_les_taches_avec_une_liste_VIDE_efface_la_precedente(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-modele-vidage", portee="ENTITY"
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]
    _definir_les_taches(
        parametres,
        decor["code"],
        modele,
        version,
        jeton,
        [{"task_reference_id": str(decor["tache_entite"]), "due_offset_days": 0}],
    )

    reponse = _definir_les_taches(parametres, decor["code"], modele, version, jeton, [])
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["nombre_de_taches"] == 0
    assert reponse.json()["taches"] == []


@pytest.mark.integration
def test_definir_les_taches_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-modele-anon", portee="ENTITY"
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()["id"]

    reponse = _definir_les_taches(parametres, decor["code"], modele, version, None, [])
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  Lister les modeles — T14, l'ecran d'administration. Trouve en construisant
#  l'ecran : sans cette route, « gerer les modeles » ne pouvait agir que sur
#  ce qui vient d'etre cree DANS LA MEME SESSION.
# ===========================================================================


@pytest.mark.integration
def test_un_DSM_NE_VOIT_QUE_SES_PROPRES_modeles(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton_dsm = _session(parametres, decor["dsm_personne"])
    jeton_esm = _session(parametres, decor["esm_personne"])
    _creer_modele(
        parametres,
        decor["code"],
        jeton_dsm,
        name=f"{decor['marqueur']}-modele-dsm-liste",
        portee="DSM",
        scope_person_id=decor["dsm_personne"],
    )
    _creer_modele(
        parametres,
        decor["code"],
        jeton_esm,
        name=f"{decor['marqueur']}-modele-autre-dsm-liste",
        portee="DSM",
        scope_person_id=decor["autre_dsm_personne"],
    )

    reponse = _lister_les_modeles(parametres, decor["code"], jeton_dsm)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    noms = {modele["name"] for modele in corps["modeles"]}
    assert f"{decor['marqueur']}-modele-dsm-liste" in noms
    assert f"{decor['marqueur']}-modele-autre-dsm-liste" not in noms
    assert corps["nombre_de_modeles"] == len(corps["modeles"])


@pytest.mark.integration
def test_un_ESM_voit_TOUS_les_modeles_de_l_entite(decor: dict[str, Any]) -> None:
    """Portee ENTITE : un ESM gere aussi ce qu'un role LOCAL gererait — LOT 6,
    meme parti que la creation (`test_un_ESM_cree_un_modele_DSM_pour_...`)."""
    parametres = decor["parametres"]
    jeton_dsm = _session(parametres, decor["dsm_personne"])
    jeton_booster = _session(parametres, decor["booster_personne"])
    jeton_esm = _session(parametres, decor["esm_personne"])
    _creer_modele(
        parametres,
        decor["code"],
        jeton_dsm,
        name=f"{decor['marqueur']}-modele-esm-voit-dsm",
        portee="DSM",
        scope_person_id=decor["dsm_personne"],
    )
    _creer_modele(
        parametres,
        decor["code"],
        jeton_booster,
        name=f"{decor['marqueur']}-modele-esm-voit-cercle",
        portee="CIRCLE",
        scope_circle_id=decor["cercle"],
    )

    reponse = _lister_les_modeles(parametres, decor["code"], jeton_esm)
    assert reponse.status_code == 200, reponse.text
    noms = {modele["name"] for modele in reponse.json()["modeles"]}
    assert f"{decor['marqueur']}-modele-esm-voit-dsm" in noms
    assert f"{decor['marqueur']}-modele-esm-voit-cercle" in noms


@pytest.mark.integration
def test_SEUL_SUPER_voit_les_modeles_GLOBAUX_dans_la_liste(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton_super = _session(parametres, decor["super_personne"])
    jeton_esm = _session(parametres, decor["esm_personne"])
    _creer_modele(
        parametres,
        decor["code"],
        jeton_super,
        name=f"{decor['marqueur']}-modele-global-liste",
        portee="GLOBAL",
    )

    vu_par_super = _lister_les_modeles(parametres, decor["code"], jeton_super)
    vu_par_esm = _lister_les_modeles(parametres, decor["code"], jeton_esm)
    assert f"{decor['marqueur']}-modele-global-liste" in {
        modele["name"] for modele in vu_par_super.json()["modeles"]
    }
    assert f"{decor['marqueur']}-modele-global-liste" not in {
        modele["name"] for modele in vu_par_esm.json()["modeles"]
    }


@pytest.mark.integration
def test_lister_les_modeles_INCLUT_leurs_versions(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele = _creer_modele(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-modele-avec-version",
        portee="ENTITY",
    ).json()["id"]
    version = _creer_version(parametres, decor["code"], modele, jeton).json()

    reponse = _lister_les_modeles(parametres, decor["code"], jeton)
    assert reponse.status_code == 200, reponse.text
    trouve = next(m for m in reponse.json()["modeles"] if m["id"] == modele)
    assert [v["id"] for v in trouve["versions"]] == [version["id"]]
    assert trouve["versions"][0]["state"] == "draft"


@pytest.mark.integration
def test_un_RESPONSABLE_DE_BUREAU_NE_liste_AUCUN_modele(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _lister_les_modeles(
        parametres, decor["code"], _session(parametres, decor["office_personne"])
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_lister_les_modeles_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _lister_les_modeles(parametres, decor["code"], None)
    assert reponse.status_code == 401, reponse.text


def test_le_MANIFESTE_declare_UNE_SECONDE_grille_pour_la_MEME_rubrique() -> None:
    """T14 — le menu « Administration » doit aussi s'ouvrir a un DSM/Booster qui
    gere ses propres modeles, decision de Jonathan (voir le manifeste).

    **`rolesAdministrationOnboarding` N'EST PAS UNE COINCIDENCE AVEC
    `rolesAdministration`, ET LES DEUX RESTENT DEUX DECLARATIONS SEPAREES** —
    meme discipline que `rolesCycleDeVie`/`rolesRestaurationDUnContenu`
    (LOT 5/6) : les fusionner ferait suivre l'une quand l'autre change, en
    silence (§7.27). Celle-ci EST une authentique derivation du §9, confrontee
    ici a `ROLES_DE_GESTION_DES_MODELES` (`perimetre.py`) dans les deux sens.
    """
    chemin = pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    codes = manifeste["rolesAdministrationOnboarding"]
    assert codes, "le manifeste ne declare aucun role d'administration onboarding"
    declares = {RoleDeLaMatrice(code) for code in codes}
    assert declares == ROLES_DE_GESTION_DES_MODELES

    #  **ET LES DEUX GRILLES RESTENT DEUX DECLARATIONS.** Fusionner les cles
    #  ferait echouer ici, exactement comme pour `rolesCycleDeVie` (LOT 5).
    assert "rolesAdministration" in manifeste
    assert "rolesAdministrationOnboarding" in manifeste


def test_le_MANIFESTE_declare_SEPAREMENT_les_roles_qui_RESTAURENT_un_modele() -> None:
    """T14 — DSM et BOOSTER sont exclus EN BLOC de la restauration (§9), a la
    difference des autres gestes de `rolesAdministrationOnboarding`. Proposer
    le bouton « Restaurer » a un DSM/Booster serait l'avertissement faux du
    §7.21 : cette liste, plus etroite, sert a ne pas le faire."""
    chemin = pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    codes = manifeste["rolesRestaurationDesModelesOnboarding"]
    assert codes, "le manifeste ne declare aucun role de restauration de modele"
    declares = {RoleDeLaMatrice(code) for code in codes}
    assert declares == ROLES_DE_RESTAURATION_DES_MODELES
    assert RoleDeLaMatrice.DSM not in declares
    assert RoleDeLaMatrice.BOOSTER not in declares
