"""Le catalogue des taches de reference — LOT 7, `T4`.

`ferme ECART-013`, matrice §9.

UNE SEULE GRILLE, PAS UNE CIBLE

  Contrairement a la fiche d'arrivee (`T2`/`T3`), le permis ici ne depend
  d'AUCUNE personne visee — seulement de la responsabilite de l'ACTEUR dans
  l'entite consultee (matrice §9 : DSM, ESM, BOOST, ADM-E, SUPER — `OFFICE` a
  TIRET). Les tests le prouvent role par role, pas par cible.

SEUL `SUPER` ATTEINT `GLOBAL`

  `portee: "GLOBAL"` (`entity_id` NULL, modele §13.1) est reservee a `SUPER` —
  la SEULE colonne du §9 qui l'atteigne sur cette ligne. Le refus d'un ESM
  qui la demande n'est pas une absence generale de droit — il POSSEDE le
  droit `ENTITE` — c'est une asymetrie mesuree, comme `BOOST` sur « Valider
  et publier » en `T3`.

LE CATALOGUE EST UNE UNION : L'ENTITE, ET LE GLOBAL

  Modele §13.1 : un modele d'une entite peut reutiliser une tache PROPRE a
  cette entite ou une tache GLOBALE — jamais celle d'une AUTRE entite. Le
  temoin d'isolement le prouve dans les deux sens : une tache d'entite reste
  invisible ailleurs, une tache globale est visible partout.
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
CHEMIN_CATALOGUE = "/api/v1/entities/{code}/onboarding/task-references"

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
                    "account_state) VALUES (:a, :a, :prenom, 'T4', 'active') RETURNING id"
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


def _responsabilite_sans_perimetre(cx: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    """DSM et ESM — la contrainte du modele exige `circle_id`/`office_id` NULS."""
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :d)"
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


def _appeler_lecture(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


def _appeler_ecriture(
    parametres: Parametres, chemin: str, jeton: str | None, corps: dict[str, Any]
) -> Any:
    """POST protege par les deux barrieres CSRF — §7.4, `DEC-531`."""
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        return client.post(chemin, json=corps, headers=entetes)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite, une AUTRE (isolement), et un porteur par role du §9."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t4l7{uuid.uuid4().hex[:10]}"
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

        office = cx.execute(
            text(
                "INSERT INTO office (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-bureau", "n": f"{marqueur}-bureau"},
        ).scalar_one()

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(cx, entite, r["dsm_personne"])
        _responsabilite_sans_perimetre(cx, r["dsm_personne"], entite)

        r["esm_personne"] = _personne(cx, marqueur, "esm")
        _appartenance(cx, entite, r["esm_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'ESM', :p, :d)"
            ),
            {"p": r["esm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
        )

        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(cx, entite, r["booster_personne"])
        _responsabilite(
            cx, r["booster_personne"], entite, TypeResponsabilite.BOOSTER.value, cercle=cercle
        )

        r["office_personne"] = _personne(cx, marqueur, "office")
        _appartenance(cx, entite, r["office_personne"])
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

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
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


def _creer(
    parametres: Parametres,
    code_entite: str,
    jeton: str | None,
    *,
    code: str,
    portee: str = "ENTITE",
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_CATALOGUE.format(code=code_entite),
        jeton,
        {"code": code, "title": f"Titre {code}", "portee": portee},
    )


# ===========================================================================
#  Creer une tache de reference — matrice §9
# ===========================================================================


@pytest.mark.integration
def test_un_DSM_cree_une_tache_de_reference_dans_SON_entite(decor: dict[str, Any]) -> None:
    """`Consultants` se reduit a l'ENTITE ici — voir `perimetre.py`."""
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["dsm_personne"]),
        code=f"{decor['marqueur']}-dsm-tache",
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["entity_id"] == str(decor["entite"])
    assert corps["active"] is True


@pytest.mark.integration
def test_un_ESM_cree_une_tache_de_reference(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        code=f"{decor['marqueur']}-esm-tache",
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_un_BOOSTER_cree_une_tache_de_reference(decor: dict[str, Any]) -> None:
    """`Cercle` se reduit a l'ENTITE ici aussi : la table ne porte pas de cercle."""
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["booster_personne"]),
        code=f"{decor['marqueur']}-booster-tache",
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_un_ADM_E_cree_une_tache_de_reference(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["adm_e_personne"]),
        code=f"{decor['marqueur']}-adme-tache",
    )
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_un_SUPER_cree_une_tache_ENTITE_par_defaut(decor: dict[str, Any]) -> None:
    """`portee` omise -> `ENTITE`, meme pour SUPER."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        CHEMIN_CATALOGUE.format(code=decor["code"]),
        _session(parametres, decor["super_personne"]),
        {"code": f"{decor['marqueur']}-super-tache", "title": "Titre"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["entity_id"] == str(decor["entite"])


@pytest.mark.integration
def test_un_RESPONSABLE_DE_BUREAU_NE_cree_PAS(decor: dict[str, Any]) -> None:
    """`OFFICE` est a TIRET partout au §9 — troisieme occurrence de ce piege."""
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["office_personne"]),
        code=f"{decor['marqueur']}-office-tache",
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_EMPLOYE_NU_NE_cree_PAS(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["emp_personne"]),
        code=f"{decor['marqueur']}-emp-tache",
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_creer_avec_un_code_DEJA_UTILISE_dans_la_MEME_entite_est_refuse(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["esm_personne"])
    code = f"{decor['marqueur']}-doublon"
    premiere = _creer(parametres, decor["code"], jeton, code=code)
    assert premiere.status_code == 201, premiere.text

    seconde = _creer(parametres, decor["code"], jeton, code=code)
    assert seconde.status_code == 409, seconde.text
    assert seconde.json()["erreur"]["code"] == "code_de_tache_deja_utilise"


@pytest.mark.integration
def test_creer_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer(parametres, decor["code"], None, code=f"{decor['marqueur']}-anon")
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  Portee GLOBALE — seul SUPER l'atteint, matrice §9
# ===========================================================================


@pytest.mark.integration
def test_SEUL_SUPER_cree_une_tache_GLOBALE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["super_personne"]),
        code=f"{decor['marqueur']}-globale",
        portee="GLOBAL",
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["entity_id"] is None


@pytest.mark.integration
def test_un_ESM_NE_cree_PAS_de_tache_GLOBALE(decor: dict[str, Any]) -> None:
    """L'ESM POSSEDE le droit ENTITE (voir plus haut) — ce refus est une
    ASYMETRIE mesuree, pas une absence generale de droit."""
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        code=f"{decor['marqueur']}-esm-globale-refusee",
        portee="GLOBAL",
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_un_ADM_E_NE_cree_PAS_de_tache_GLOBALE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _creer(
        parametres,
        decor["code"],
        _session(parametres, decor["adm_e_personne"]),
        code=f"{decor['marqueur']}-adme-globale-refusee",
        portee="GLOBAL",
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


# ===========================================================================
#  Consulter le catalogue — union entite + global, isolement entre entites
# ===========================================================================


@pytest.mark.integration
def test_le_catalogue_est_VIDE_pour_une_entite_neuve(decor: dict[str, Any]) -> None:
    """§7.20 : `nombre_de_taches` est RAPPORTE, pas seulement une liste vide."""
    parametres = decor["parametres"]
    reponse = _appeler_lecture(
        parametres,
        CHEMIN_CATALOGUE.format(code=decor["autre_code"]),
        _session(parametres, decor["super_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["taches"] == []
    assert corps["nombre_de_taches"] == 0


@pytest.mark.integration
def test_le_catalogue_UNIT_les_taches_de_l_entite_ET_les_GLOBALES(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    super_jeton = _session(parametres, decor["super_personne"])
    esm_jeton = _session(parametres, decor["esm_personne"])

    code_local = f"{decor['marqueur']}-locale-union"
    code_globale = f"{decor['marqueur']}-globale-union"
    assert _creer(parametres, decor["code"], esm_jeton, code=code_local).status_code == 201
    assert (
        _creer(
            parametres, decor["code"], super_jeton, code=code_globale, portee="GLOBAL"
        ).status_code
        == 201
    )

    reponse = _appeler_lecture(parametres, CHEMIN_CATALOGUE.format(code=decor["code"]), esm_jeton)
    assert reponse.status_code == 200, reponse.text
    codes = {tache["code"] for tache in reponse.json()["taches"]}
    assert code_local in codes
    assert code_globale in codes


@pytest.mark.integration
def test_une_tache_D_ENTITE_reste_INVISIBLE_dans_une_AUTRE_entite(
    decor: dict[str, Any],
) -> None:
    """Isolement — modele §13.1 : une tache d'entite n'appartient qu'a la sienne."""
    parametres = decor["parametres"]
    super_jeton = _session(parametres, decor["super_personne"])
    code_local = f"{decor['marqueur']}-locale-isolee"
    code_globale = f"{decor['marqueur']}-globale-visible-partout"
    assert (
        _creer(
            parametres, decor["code"], _session(parametres, decor["esm_personne"]), code=code_local
        ).status_code
        == 201
    )
    assert (
        _creer(
            parametres, decor["code"], super_jeton, code=code_globale, portee="GLOBAL"
        ).status_code
        == 201
    )

    #  SUPER porte le droit global : sa session sert de temoin pour consulter
    #  une entite ou aucun autre acteur du decor n'a de responsabilite.
    reponse = _appeler_lecture(
        parametres, CHEMIN_CATALOGUE.format(code=decor["autre_code"]), super_jeton
    )
    assert reponse.status_code == 200, reponse.text
    codes = {tache["code"] for tache in reponse.json()["taches"]}
    assert code_globale in codes
    assert code_local not in codes


@pytest.mark.integration
def test_lister_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _appeler_lecture(parametres, CHEMIN_CATALOGUE.format(code=decor["code"]), None)
    assert reponse.status_code == 401, reponse.text
