"""Reouvrir une tache apres le delai de cinq minutes — LOT 7, `T9`.

matrice §8.1/§8.3 : « Reouvrir apres le delai de 5 minutes ». CINQUIEME
grille du module, et l'INVERSE de la quatrieme (`T8`) : `ESM`, administrateur
d'entite (`ADM-E`) ou super-administrateur SEULEMENT — `Soi`, `DSM` et
`BOOST` EXCLUS EN BLOC, meme rattaches. Le §8.3 l'ecrit en toutes lettres :
« Le DSM et le Booster ne peuvent pas effectuer cette correction ». Les
temoins qui comptent sont donc un DSM et un Booster RATTACHES a ce
consultant/ce cercle precis — qui LISENT et AFFECTENT pleinement ce parcours
(`T7`) — et doivent pourtant etre REFUSES ici.

CORRECTIF `T9` A `terminer_une_tache` (`T8`) : LE DIAGRAMME §24.2 EXIGE
`Reopened -> Completed`. Un temoin re-termine une tache apres sa reouverture
administrative — sans ce correctif, une tache reouverte restait dans une
impasse permanente.

LA FENETRE EST L'INVERSE STRICT DE CELLE DE `T8`, ANCREE A LA MEME COLONNE
`completed_at` — jamais un second mecanisme, jamais une horloge mockee : le
temoin « trop tot » ne recule rien, le temoin « apres le delai » recule
`completed_at` par SQL, exactement comme `T8`.
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
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_MODELES = "/api/v1/entities/{code}/onboarding/templates"
CHEMIN_VERSIONS = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions"
CHEMIN_TACHES = "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/tasks"
CHEMIN_PUBLICATION = (
    "/api/v1/entities/{code}/onboarding/templates/{modele}/versions/{version}/publication"
)
CHEMIN_PARCOURS = "/api/v1/entities/{code}/people/{appartenance}/onboarding-parcours"
CHEMIN_COMPLETION = CHEMIN_PARCOURS + "/taches/{tache}/completion"
CHEMIN_REOUVERTURE = CHEMIN_PARCOURS + "/taches/{tache}/reouverture"

#  DERIVEE DE `now()`, JAMAIS FIGEE — §7.47 du LOT 6.
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
                    "account_state) VALUES (:a, :a, :prenom, 'T9', 'active') RETURNING id"
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


def _booster_de_ce_cercle(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID, cercle: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'BOOSTER', :c, :p, :d)"
        ),
        {"p": personne, "e": entite, "c": cercle, "d": ANCRAGE - dt.timedelta(days=90)},
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


def _appeler_ecriture(
    parametres: Parametres, chemin: str, jeton: str | None, corps: dict[str, Any] | None = None
) -> Any:
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = {"Origin": ORIGINE_DE_TEST}
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            entetes[EN_TETE_JETON] = jeton_pour(
                empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
            )
        return client.post(chemin, json=corps if corps is not None else {}, headers=entetes)


def _appeler_lecture(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t9l7{uuid.uuid4().hex[:10]}"
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

        r["esm_personne"] = _personne(cx, marqueur, "esm")
        _appartenance(
            cx, entite, r["esm_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _esm(cx, r["esm_personne"], entite)

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(
            cx, entite, r["dsm_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _dsm(cx, r["dsm_personne"], entite)

        r["adme_personne"] = _personne(cx, marqueur, "adme")
        _appartenance(
            cx, entite, r["adme_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _role_technique(cx, r["adme_personne"], entite, "ENTITY_ADMIN")

        r["super_personne"] = _personne(cx, marqueur, "super")
        _appartenance(
            cx, entite, r["super_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _role_technique(cx, r["super_personne"], None, "SUPER_ADMIN")

        cercle = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 1) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
        ).scalar_one()
        r["cercle"] = cercle

        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(
            cx, entite, r["booster_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _booster_de_ce_cercle(cx, r["booster_personne"], entite, cercle)

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
            #  AVANT `circle` : `framework_responsibility_assignment` (le
            #  Booster) reference `circle_id` — meme ordre que `T7`.
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
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
    parametres: Parametres, code_entite: str, jeton: str | None, *, name: str, tache: uuid.UUID
) -> None:
    """Cree un modele ENTITY (l'ESM le gere pleinement), une version, une
    tache, puis PUBLIE — les quatre routes reelles, jamais une ecriture
    directe en base. Meme defaut evite qu'en `T8` (`T8-1`/`T7-5`) : PORTEE
    ENTITY, jamais GLOBAL, que seul `SUPER` gere."""
    corps: dict[str, Any] = {"name": name, "target_status": "intercontract", "portee": "ENTITY"}
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
        reponse_taches = client.put(
            CHEMIN_TACHES.format(code=code_entite, modele=modele, version=version),
            json={"taches": [{"task_reference_id": str(tache), "due_offset_days": 3}]},
            headers=entetes,
        )
        assert reponse_taches.status_code == 200, reponse_taches.text
        publiee = client.post(
            CHEMIN_PUBLICATION.format(code=code_entite, modele=modele, version=version),
            json={},
            headers=entetes,
        )
        assert publiee.status_code == 200, publiee.text


def _affecter_et_lire_la_tache(
    parametres: Parametres, code: str, appartenance: uuid.UUID, jeton: str | None
) -> str:
    reponse = _appeler_ecriture(
        parametres, CHEMIN_PARCOURS.format(code=code, appartenance=appartenance), jeton
    )
    assert reponse.status_code == 201, reponse.text
    taches = reponse.json()["taches"]
    assert len(taches) == 1
    return str(taches[0]["id"])


def _terminer(
    parametres: Parametres, code: str, appartenance: uuid.UUID, tache: str, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_COMPLETION.format(code=code, appartenance=appartenance, tache=tache),
        jeton,
    )


def _reouvrir(
    parametres: Parametres,
    code: str,
    appartenance: uuid.UUID,
    tache: str,
    jeton: str | None,
    *,
    motif: str | None = "Correction technique auditee — erreur de saisie du responsable.",
) -> Any:
    corps = {} if motif is None else {"motif": motif}
    return _appeler_ecriture(
        parametres,
        CHEMIN_REOUVERTURE.format(code=code, appartenance=appartenance, tache=tache),
        jeton,
        corps,
    )


def _decor_avec_parcours(decor: dict[str, Any], suffixe: str) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Cree un consultant, son parcours (modele ENTITY) et rend
    `(consultant_personne, appartenance, tache)` — rattache au DSM et au
    cercle du decor, pour que les deux temoins de refus soient de VRAIS
    rattachements, pas des absences triviales."""
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    esm_jeton = _session(parametres, decor["esm_personne"])
    _creer_modele_publie(
        parametres,
        decor["code"],
        esm_jeton,
        name=f"{marqueur}-modele-{suffixe}",
        tache=decor["tache_globale"],
    )
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, f"consultant-{suffixe}")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
        _dsm_de_ce_consultant(cx, decor["entite"], consultant, decor["dsm_personne"])
        _cercle_principal(cx, decor["entite"], consultant, decor["cercle"])
    tache = _affecter_et_lire_la_tache(parametres, decor["code"], consultant, esm_jeton)
    return consultant_personne, consultant, tache


def _terminer_puis_reculer_de_six_minutes(
    parametres: Parametres, code: str, consultant: uuid.UUID, tache: str, jeton: str | None
) -> None:
    assert _terminer(parametres, code, consultant, tache, jeton).status_code == 200
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "UPDATE onboarding_instance_task SET completed_at = :six_minutes WHERE id = :tache"
            ),
            {"six_minutes": dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=6), "tache": tache},
        )


# ===========================================================================
#  Reouvrir apres le delai — ESM, ADM-E, SUPER SEULEMENT
# ===========================================================================


@pytest.mark.integration
def test_reouvrir_apres_le_delai_par_l_ESM_rend_reopened(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "esm-reouvre")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "reopened"
    assert corps["reopened_at"] is not None
    assert corps["completed_at"] is not None, "la completion ORIGINALE est conservee, pas effacee"


@pytest.mark.integration
def test_reouvrir_par_l_ADM_E_reussit(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "adme-reouvre")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["adme_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "reopened"


@pytest.mark.integration
def test_reouvrir_par_le_SUPER_reussit(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "super-reouvre")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["super_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "reopened"


@pytest.mark.integration
def test_un_DSM_RATTACHE_NE_reouvre_PAS_la_tache_de_SON_consultant(decor: dict[str, Any]) -> None:
    """§8.3, a la lettre : « Le DSM […] ne peu[t] pas effectuer cette
    correction ». Ce DSM LIT et AFFECTE pleinement ce parcours (`T7`), et
    doit pourtant etre REFUSE ici — piege n°1 inverse."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "dsm-refuse")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_un_BOOSTER_RATTACHE_NE_reouvre_PAS_la_tache_d_un_membre_de_SON_cercle(
    decor: dict[str, Any],
) -> None:
    """§8.3 : « […] Booster ne peu[t] pas effectuer cette correction », meme
    Booster du cercle PRINCIPAL de ce consultant precis."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "booster-refuse")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres,
        decor["code"],
        consultant,
        tache,
        _session(parametres, decor["booster_personne"]),
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_reouvrir_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, tache = _decor_avec_parcours(decor, "anon-reouvre")

    reponse = _reouvrir(parametres, decor["code"], consultant, tache, None)
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  La fenetre — inverse stricte de celle de `T8`, ancree a `completed_at`
# ===========================================================================


@pytest.mark.integration
def test_reouvrir_dans_la_fenetre_est_refusee_avec_reouverture_prematuree(
    decor: dict[str, Any],
) -> None:
    """Moins de cinq minutes depuis la completion : le nouvel arrivant peut
    encore annuler LUI-MEME (`T8`) — la reouverture administrative n'a pas
    encore lieu d'etre."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "trop-tot")
    assert (
        _terminer(
            parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
        ).status_code
        == 200
    )

    reponse = _reouvrir(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "reouverture_prematuree"


@pytest.mark.integration
def test_reouvrir_une_tache_jamais_terminee_est_refusee_avec_transition_invalide(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    _, consultant, tache = _decor_avec_parcours(decor, "jamais-terminee")

    reponse = _reouvrir(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_tache_invalide"


# ===========================================================================
#  Le motif — obligatoire au corps ET a la base
# ===========================================================================


@pytest.mark.integration
def test_reouvrir_sans_motif_est_422(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "sans-motif")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres,
        decor["code"],
        consultant,
        tache,
        _session(parametres, decor["esm_personne"]),
        motif=None,
    )
    assert reponse.status_code == 422, reponse.text


@pytest.mark.integration
def test_reouvrir_avec_un_motif_vide_est_422(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "motif-vide")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres,
        decor["code"],
        consultant,
        tache,
        _session(parametres, decor["esm_personne"]),
        motif="",
    )
    assert reponse.status_code == 422, reponse.text


@pytest.mark.integration
def test_le_motif_et_l_acteur_sont_ecrits_en_base(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "motif-ecrit")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )
    motif = "Correction auditee : le collaborateur a valide la mauvaise tache par erreur."

    reponse = _reouvrir(
        parametres,
        decor["code"],
        consultant,
        tache,
        _session(parametres, decor["esm_personne"]),
        motif=motif,
    )
    assert reponse.status_code == 200, reponse.text

    with moteur(parametres).begin() as cx:
        ligne = cx.execute(
            text(
                "SELECT reopen_reason, reopened_by_person_id, completed_by_person_id "
                "FROM onboarding_instance_task WHERE id = :tache"
            ),
            {"tache": tache},
        ).one()
    assert ligne[0] == motif
    assert ligne[1] == decor["esm_personne"]
    assert ligne[2] == consultant_personne, "la completion ORIGINALE reste tracee"


# ===========================================================================
#  Resolution de l'appartenance et de l'instance active
# ===========================================================================


@pytest.mark.integration
def test_reouvrir_une_tache_inconnue_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, _tache = _decor_avec_parcours(decor, "tache-inconnue")

    reponse = _reouvrir(
        parametres,
        decor["code"],
        consultant,
        str(uuid.uuid4()),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "tache_introuvable"


@pytest.mark.integration
def test_reouvrir_sans_parcours_actif_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        personne = _personne(cx, marqueur, "sans-parcours")
        appartenance = _appartenance(cx, decor["entite"], personne, arrivee=ANCRAGE.date())

    reponse = _reouvrir(
        parametres,
        decor["code"],
        appartenance,
        str(uuid.uuid4()),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "aucun_parcours_actif"


@pytest.mark.integration
def test_reouvrir_sur_une_AUTRE_entite_est_404(decor: dict[str, Any]) -> None:
    """Le `SUPER` porte son role PARTOUT (§5.1) : la seule raison d'un 404
    ici est que cette appartenance n'existe pas dans CETTE entite-la — la
    resolution reste bornee a l'entite du chemin."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "autre-entite")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )

    reponse = _reouvrir(
        parametres,
        decor["autre_code"],
        consultant,
        tache,
        _session(parametres, decor["super_personne"]),
    )
    assert reponse.status_code == 404, reponse.text


# ===========================================================================
#  Correctif `T9` a `terminer_une_tache` (`T8`) — diagramme §24.2
# ===========================================================================


@pytest.mark.integration
def test_terminer_a_nouveau_apres_reouverture_reussit_correctif_du_diagramme_24_2(
    decor: dict[str, Any],
) -> None:
    """`Reopened -> Completed` — sans le correctif de `T9` a `_TERMINER_LA_
    TACHE` (`T8` n'acceptait que `todo`), cette tache resterait dans une
    impasse permanente apres une reouverture administrative."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "re-termine")
    jeton_consultant = _session(parametres, consultant_personne)
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, jeton_consultant
    )
    assert (
        _reouvrir(
            parametres,
            decor["code"],
            consultant,
            tache,
            _session(parametres, decor["esm_personne"]),
        ).status_code
        == 200
    )

    reponse = _terminer(parametres, decor["code"], consultant, tache, jeton_consultant)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "completed"


@pytest.mark.integration
def test_la_progression_redevient_incomplete_apres_reouverture(decor: dict[str, Any]) -> None:
    """Une tache `reopened` n'est PLUS comptee parmi les obligatoires
    terminees — meme mecanique que `todo`, sans aucune ecriture sur une
    colonne de progression (critere de sortie n°3, comptee a la lecture)."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "progression-reouverte")
    jeton_consultant = _session(parametres, consultant_personne)
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, jeton_consultant
    )

    avant = _appeler_lecture(
        parametres,
        CHEMIN_PARCOURS.format(code=decor["code"], appartenance=consultant),
        jeton_consultant,
    ).json()
    assert avant["progression"]["taches_obligatoires_terminees"] == 1

    assert (
        _reouvrir(
            parametres,
            decor["code"],
            consultant,
            tache,
            _session(parametres, decor["esm_personne"]),
        ).status_code
        == 200
    )

    apres = _appeler_lecture(
        parametres,
        CHEMIN_PARCOURS.format(code=decor["code"], appartenance=consultant),
        jeton_consultant,
    ).json()
    assert apres["progression"]["taches_obligatoires_terminees"] == 0


@pytest.mark.integration
def test_l_evenement_REOPENED_est_journalise_avec_son_motif(decor: dict[str, Any]) -> None:
    """Critere de sortie n°4 : `onboarding_task_event` — `REOPENED` avec son
    acteur ET son motif, a cote d'`ASSIGNED`/`COMPLETED`."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "evenement-reopened")
    _terminer_puis_reculer_de_six_minutes(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )
    motif = "Motif de reouverture pour ce temoin."
    assert (
        _reouvrir(
            parametres,
            decor["code"],
            consultant,
            tache,
            _session(parametres, decor["esm_personne"]),
            motif=motif,
        ).status_code
        == 200
    )

    with moteur(parametres).begin() as cx:
        lignes = cx.execute(
            text(
                "SELECT event_type, actor_person_id, reason FROM onboarding_task_event "
                "WHERE onboarding_instance_task_id = :tache ORDER BY occurred_at"
            ),
            {"tache": tache},
        ).all()
    types = [str(ligne[0]) for ligne in lignes]
    assert types == ["ASSIGNED", "COMPLETED", "REOPENED"], types
    evenement_reopened = lignes[-1]
    assert evenement_reopened[1] == decor["esm_personne"]
    assert evenement_reopened[2] == motif
