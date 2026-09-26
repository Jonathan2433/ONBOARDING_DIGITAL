"""Le cycle de vie d'une version de modele d'onboarding — LOT 7, `T6`.

matrice §9 : « Publier une version », « Archiver une version », « Restaurer
une version ».

`ECART-066` RESOLU : L'ESM RESTAURE DESORMAIS COMME `ADM-E`, DANS SON ENTITE

  Publier et archiver reutilisent la MEME grille que la creation (`T5`) : DSM
  et Booster agissent sur LEUR PROPRE modele, ESM/ADM-E sur toute l'entite,
  SUPER sur le global. **Restaurer est la SEULE ligne du §9 ou DSM/Booster
  sont EXCLUS EN BLOC** — jamais un sous-cas de leur propre modele, a la
  difference des deux autres gestes. Les temoins d'asymetrie le prouvent :
  un DSM (ou un Booster) publie et archive SON PROPRE modele sans probleme,
  puis est refuse sur SA PROPRE restauration — pendant qu'un ESM restaure ce
  meme modele sans difficulte.

LE TEMOIN LE PLUS IMPORTANT DE CETTE SOUS-ETAPE : LA RESTAURATION NE ROUVRE
PAS L'EDITION

  Contrairement a `restaurer_une_page` (LOT 6), qui ramene une page en
  BROUILLON, restaurer une version de modele la ramene en `published` —
  jamais en `draft`. Le temoin decisif n'est pas la valeur de `state` seule :
  c'est qu'APRES restauration, `PUT .../tasks` refuse TOUJOURS d'ecrire,
  exactement comme sur une version fraichement publiee (`T5`). Si la
  restauration rendait `draft`, ce meme appel reussirait — et c'est
  precisement ce que ce module refuse.
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
CHEMIN_ARCHIVAGE = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/archivage"
)
CHEMIN_RESTAURATION = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/restauration"
)

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
                    "account_state) VALUES (:a, :a, :prenom, 'T6', 'active') RETURNING id"
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


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _appeler_ecriture(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    """Ecriture protegee par les deux barrieres CSRF — §7.4, `DEC-531`. Corps
    vide : aucune des trois transitions de ce module n'en attend."""
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        return client.post(chemin, json={}, headers=entetes)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite, une AUTRE (isolement), un cercle, un porteur par role."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t6l7{uuid.uuid4().hex[:10]}"
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

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(cx, entite, r["dsm_personne"])
        _dsm(cx, r["dsm_personne"], entite)

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

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM onboarding_template_task WHERE template_version_id IN "
            "(SELECT id FROM onboarding_template_version WHERE template_id IN "
            "(SELECT id FROM onboarding_template WHERE name LIKE :motif))",
            "DELETE FROM onboarding_template_version WHERE template_id IN "
            "(SELECT id FROM onboarding_template WHERE name LIKE :motif)",
            "DELETE FROM onboarding_template WHERE name LIKE :motif",
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
                {"motif": f"{marqueur}%", "motif_personne": f"{marqueur}%"},
            )


def _creer_modele_et_version(
    parametres: Parametres,
    code_entite: str,
    jeton: str | None,
    *,
    name: str,
    portee: str,
    scope_person_id: uuid.UUID | None = None,
    scope_circle_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Cree un modele puis sa premiere version brouillon — reutilise les deux
    routes de `T5`, jamais une ecriture directe en base."""
    corps: dict[str, Any] = {"name": name, "target_status": "mission", "portee": portee}
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
            CHEMIN_VERSIONS.format(code=code_entite, modele=modele), json={}, headers=entetes
        ).json()["id"]
    return uuid.UUID(modele), uuid.UUID(version)


def _publier(
    parametres: Parametres, code: str, modele: uuid.UUID, version: uuid.UUID, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres, CHEMIN_PUBLICATION.format(code=code, modele=modele, version=version), jeton
    )


def _archiver(
    parametres: Parametres, code: str, modele: uuid.UUID, version: uuid.UUID, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres, CHEMIN_ARCHIVAGE.format(code=code, modele=modele, version=version), jeton
    )


def _restaurer(
    parametres: Parametres, code: str, modele: uuid.UUID, version: uuid.UUID, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres, CHEMIN_RESTAURATION.format(code=code, modele=modele, version=version), jeton
    )


def _definir_une_tache(
    parametres: Parametres, code: str, modele: uuid.UUID, version: uuid.UUID, jeton: str | None
) -> Any:
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        return client.put(
            CHEMIN_TACHES.format(code=code, modele=modele, version=version),
            json={"taches": []},
            headers=entetes,
        )


# ===========================================================================
#  Publier une version — draft -> published
# ===========================================================================


@pytest.mark.integration
def test_publier_une_version_BROUILLON_reussit(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-publier", portee="ENTITY"
    )

    reponse = _publier(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "published"
    assert corps["published_at"] is not None
    assert corps["published_by_person_id"] == str(decor["esm_personne"])


@pytest.mark.integration
def test_publier_une_version_DEJA_PUBLIEE_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-republier", portee="ENTITY"
    )
    _publier(parametres, decor["code"], modele, version, jeton)

    reponse = _publier(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_version_invalide"


@pytest.mark.integration
def test_publier_une_version_INCONNUE_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, _ = _creer_modele_et_version(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-publier-404", portee="ENTITY"
    )
    reponse = _publier(parametres, decor["code"], modele, uuid.uuid4(), jeton)
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_de_modele_introuvable"


@pytest.mark.integration
def test_publier_une_version_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-publier-anon", portee="ENTITY"
    )
    reponse = _publier(parametres, decor["code"], modele, version, None)
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  Archiver une version — published -> retired
# ===========================================================================


@pytest.mark.integration
def test_archiver_une_version_PUBLIEE_reussit(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-archiver", portee="ENTITY"
    )
    _publier(parametres, decor["code"], modele, version, jeton)

    reponse = _archiver(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "retired"


@pytest.mark.integration
def test_archiver_une_version_encore_BROUILLON_est_refuse(decor: dict[str, Any]) -> None:
    """Aucune transition directe `draft --> retired` — le §9 n'en nomme aucune."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-archiver-brouillon",
        portee="ENTITY",
    )
    reponse = _archiver(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_version_invalide"


@pytest.mark.integration
def test_archiver_une_version_DEJA_RETIREE_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-archiver-deux-fois",
        portee="ENTITY",
    )
    _publier(parametres, decor["code"], modele, version, jeton)
    _archiver(parametres, decor["code"], modele, version, jeton)

    reponse = _archiver(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_version_invalide"


# ===========================================================================
#  Restaurer une version — retired -> published, ECART-066 resolu
# ===========================================================================


@pytest.mark.integration
def test_restaurer_une_version_RETIREE_redevient_PUBLIEE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], jeton, name=f"{decor['marqueur']}-restaurer", portee="ENTITY"
    )
    publiee = _publier(parametres, decor["code"], modele, version, jeton).json()
    _archiver(parametres, decor["code"], modele, version, jeton)

    reponse = _restaurer(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "published"
    #  `published_at`/`published_by_person_id` D'ORIGINE, CONSERVES — restaurer
    #  n'est pas republier.
    assert corps["published_at"] == publiee["published_at"]
    assert corps["published_by_person_id"] == publiee["published_by_person_id"]


@pytest.mark.integration
def test_restaurer_une_version_NE_ROUVRE_PAS_l_edition_des_taches(decor: dict[str, Any]) -> None:
    """Le temoin decisif de cette sous-etape : la restauration rend `published`,
    jamais `draft` — `PUT .../tasks` refuse TOUJOURS apres restauration."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-restaurer-immuable",
        portee="ENTITY",
    )
    _publier(parametres, decor["code"], modele, version, jeton)
    _archiver(parametres, decor["code"], modele, version, jeton)
    _restaurer(parametres, decor["code"], modele, version, jeton)

    reponse = _definir_une_tache(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_de_modele_immuable"


@pytest.mark.integration
def test_restaurer_une_version_encore_PUBLIEE_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-restaurer-publiee",
        portee="ENTITY",
    )
    _publier(parametres, decor["code"], modele, version, jeton)

    reponse = _restaurer(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_version_invalide"


@pytest.mark.integration
def test_restaurer_une_version_encore_BROUILLON_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-restaurer-brouillon",
        portee="ENTITY",
    )
    reponse = _restaurer(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_version_invalide"


@pytest.mark.integration
def test_un_DSM_publie_et_archive_SON_PROPRE_modele_mais_ne_le_RESTAURE_PAS(
    decor: dict[str, Any],
) -> None:
    """`ECART-066` — asymetrie : DSM agit sur les deux premiers gestes, jamais
    le troisieme, MEME sur son propre modele."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["dsm_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-dsm-cycle",
        portee="DSM",
        scope_person_id=decor["dsm_personne"],
    )
    assert _publier(parametres, decor["code"], modele, version, jeton).status_code == 200
    assert _archiver(parametres, decor["code"], modele, version, jeton).status_code == 200

    reponse = _restaurer(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"

    #  ET UN ESM RESTAURE CE MEME MODELE — `ECART-066` resolu.
    esm_jeton = _session(parametres, decor["esm_personne"])
    reponse_esm = _restaurer(parametres, decor["code"], modele, version, esm_jeton)
    assert reponse_esm.status_code == 200, reponse_esm.text


@pytest.mark.integration
def test_un_BOOSTER_publie_et_archive_SON_cercle_mais_ne_le_RESTAURE_PAS(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["booster_personne"])
    modele, version = _creer_modele_et_version(
        parametres,
        decor["code"],
        jeton,
        name=f"{decor['marqueur']}-booster-cycle",
        portee="CIRCLE",
        scope_circle_id=decor["cercle"],
    )
    assert _publier(parametres, decor["code"], modele, version, jeton).status_code == 200
    assert _archiver(parametres, decor["code"], modele, version, jeton).status_code == 200

    reponse = _restaurer(parametres, decor["code"], modele, version, jeton)
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_ADM_E_restaure_une_version_de_son_entite(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], esm_jeton, name=f"{decor['marqueur']}-adme", portee="ENTITY"
    )
    _publier(parametres, decor["code"], modele, version, esm_jeton)
    _archiver(parametres, decor["code"], modele, version, esm_jeton)

    reponse = _restaurer(
        parametres, decor["code"], modele, version, _session(parametres, decor["adm_e_personne"])
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_SEUL_SUPER_restaure_une_version_GLOBALE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    super_jeton = _session(parametres, decor["super_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], super_jeton, name=f"{decor['marqueur']}-global", portee="GLOBAL"
    )
    _publier(parametres, decor["code"], modele, version, super_jeton)
    _archiver(parametres, decor["code"], modele, version, super_jeton)

    refus = _restaurer(
        parametres, decor["code"], modele, version, _session(parametres, decor["esm_personne"])
    )
    assert refus.status_code == 403, refus.text
    assert refus.json()["erreur"]["code"] == "acces_refuse"

    reussite = _restaurer(parametres, decor["code"], modele, version, super_jeton)
    assert reussite.status_code == 200, reussite.text


@pytest.mark.integration
def test_un_RESPONSABLE_DE_BUREAU_NE_restaure_AUCUNE_version(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], esm_jeton, name=f"{decor['marqueur']}-office", portee="ENTITY"
    )
    _publier(parametres, decor["code"], modele, version, esm_jeton)
    _archiver(parametres, decor["code"], modele, version, esm_jeton)

    reponse = _restaurer(
        parametres, decor["code"], modele, version, _session(parametres, decor["office_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_restaurer_une_version_d_une_AUTRE_entite_est_404(decor: dict[str, Any]) -> None:
    """Isolement — meme discipline que `T5`."""
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], esm_jeton, name=f"{decor['marqueur']}-isolee", portee="ENTITY"
    )
    _publier(parametres, decor["code"], modele, version, esm_jeton)
    _archiver(parametres, decor["code"], modele, version, esm_jeton)

    reponse = _restaurer(
        parametres,
        decor["autre_code"],
        modele,
        version,
        _session(parametres, decor["super_personne"]),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "modele_introuvable"


@pytest.mark.integration
def test_restaurer_une_version_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    modele, version = _creer_modele_et_version(
        parametres, decor["code"], esm_jeton, name=f"{decor['marqueur']}-anon", portee="ENTITY"
    )
    _publier(parametres, decor["code"], modele, version, esm_jeton)
    _archiver(parametres, decor["code"], modele, version, esm_jeton)

    reponse = _restaurer(parametres, decor["code"], modele, version, None)
    assert reponse.status_code == 401, reponse.text
