"""Le suivi par perimetre — LOT 7, `T12`, `US008`.

matrice §8.1 « Consulter les taches en retard » : `NEW` Soi, `DSM` Consultants,
`ESM` Entite, `BOOST` Cercle, `OFFICE` —, `ADM-E` Entite, `SUPER` Global —
QUATRE portees, jamais un refus (`resoudre_le_perimetre_du_suivi`, en-tete).

UN TEMOIN PAR PERIMETRE, CRITERE DE SORTIE N°2 DU LOT

  Quatre consultants, quatre parcours, une seule tache en retard chacun :
  ESM/ADM-E/SUPER voient les QUATRE (Entite), le DSM rattache n'en voit
  qu'UN (Consultants), le Booster de son cercle n'en voit qu'UN (Cercle), et
  un consultant sans aucun role ne voit que LE SIEN (Soi) — jamais celui
  d'un autre, meme dans la meme entite.

DEUX FILTRES D'ETAT, CHACUN AVEC SON TEMOIN NEGATIF

  Une tache `completed` n'est jamais « en retard », meme avec une echeance
  passee — filtre sur `oit.state`. Une tache NON obligatoire encore `todo`
  sur une instance `archived` (l'automatique de `T11` a deja archive des que
  la derniere OBLIGATOIRE a ete terminee) n'apparait pas non plus — filtre
  sur `oi.state = 'active'`, delibere et non un oubli (voir l'en-tete de
  `app/onboarding/suivi.py`, §2.1 du compte rendu).
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
from app.organization.modeles import TypeResponsabilite
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
CHEMIN_SUIVI = "/api/v1/entities/{code}/onboarding-suivi/taches-en-retard"

#  DERIVEE DE `now()`, JAMAIS FIGEE — §7.47 du LOT 6.
ANCRAGE = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=10)
HIER = ANCRAGE - dt.timedelta(days=1)
DEMAIN = ANCRAGE + dt.timedelta(days=1)


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
                    "account_state) VALUES (:a, :a, :prenom, 'T12', 'active') RETURNING id"
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


def _suivre(parametres: Parametres, code: str, jeton: str | None, **params: object) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN_SUIVI.format(code=code), params=params)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t12l7{uuid.uuid4().hex[:10]}"
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

        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(
            cx, entite, r["booster_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _booster(cx, r["booster_personne"], entite, cercle)

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
            #  AVANT `person` : `framework_responsibility_assignment` (DSM,
            #  ESM, BOOSTER) reference `assigned_by_person_id` — meme ordre
            #  que `T9`/`T11`.
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
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
    parametres: Parametres,
    code_entite: str,
    jeton: str | None,
    *,
    name: str,
    taches: list[uuid.UUID],
) -> None:
    """Cree un modele ENTITY, une version, ses taches (OBLIGATOIRES par
    defaut du service), puis PUBLIE — identique a `T7`/`T11`."""
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
            json={
                "taches": [
                    {"task_reference_id": str(tache), "due_offset_days": 3} for tache in taches
                ]
            },
            headers=entetes,
        )
        assert reponse_taches.status_code == 200, reponse_taches.text
        publiee = client.post(
            CHEMIN_PUBLICATION.format(code=code_entite, modele=modele, version=version),
            json={},
            headers=entetes,
        )
        assert publiee.status_code == 200, publiee.text


def _affecter(decor: dict[str, Any], appartenance: uuid.UUID) -> list[str]:
    """« Affecter un parcours » N'A PAS DE `Soi` : l'ESM affecte toujours."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        CHEMIN_PARCOURS.format(code=decor["code"], appartenance=appartenance),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 201, reponse.text
    return [str(t["id"]) for t in reponse.json()["taches"]]


def _consultant(
    decor: dict[str, Any],
    suffixe: str,
    *,
    dsm_rattache: bool = False,
    cercle: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        personne = _personne(cx, marqueur, f"consultant-{suffixe}")
        appartenance = _appartenance(cx, decor["entite"], personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], appartenance)
        if dsm_rattache:
            _dsm_de_ce_consultant(cx, decor["entite"], appartenance, decor["dsm_personne"])
        if cercle is not None:
            _cercle_principal(cx, decor["entite"], appartenance, cercle)
    return personne, appartenance


def _forcer_echeance(parametres: Parametres, tache: str, quand: dt.datetime) -> None:
    with moteur(parametres).begin() as cx:
        cx.execute(
            text("UPDATE onboarding_instance_task SET due_at = :d WHERE id = :t"),
            {"d": quand, "t": tache},
        )


def _rendre_optionnelle(parametres: Parametres, tache: str) -> None:
    with moteur(parametres).begin() as cx:
        cx.execute(
            text("UPDATE onboarding_instance_task SET required = false WHERE id = :t"),
            {"t": tache},
        )


def _terminer_directement(parametres: Parametres, tache: str) -> None:
    """Complete SANS passer par la route — isole le filtre `state` de celui
    de `oi.state` (l'archivage automatique de `T11`), meme discipline que
    `_marquer_termine_sans_passer_par_la_route` (`compte-rendu-t11-lot-7.md`)."""
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "UPDATE onboarding_instance_task SET state = 'completed', completed_at = :i "
                "WHERE id = :t"
            ),
            {"i": ANCRAGE, "t": tache},
        )


def _un_parcours_en_retard(decor: dict[str, Any], suffixe: str, **kwargs: Any) -> tuple[str, str]:
    """Un consultant, un modele publie a une tache, affecte, echeance forcee
    HIER. Rend `(appartenance, tache)`."""
    _, appartenance = _consultant(decor, suffixe, **kwargs)
    _creer_modele_publie(
        decor["parametres"],
        decor["code"],
        _session(decor["parametres"], decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-{suffixe}",
        taches=[decor["tache_globale"]],
    )
    (tache,) = _affecter(decor, appartenance)
    _forcer_echeance(decor["parametres"], tache, HIER)
    return str(appartenance), tache


@pytest.mark.integration
def test_esm_voit_les_taches_en_retard_de_toute_l_entite(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, t1 = _un_parcours_en_retard(decor, "sans-role")
    _, t2 = _un_parcours_en_retard(decor, "dsm-rattache", dsm_rattache=True)
    _, t3 = _un_parcours_en_retard(decor, "cercle", cercle=decor["cercle"])
    _, t4 = _un_parcours_en_retard(decor, "autre-cercle", cercle=decor["autre_cercle"])

    reponse = _suivre(parametres, decor["code"], _session(parametres, decor["esm_personne"]))
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 4
    assert {t["id"] for t in corps["taches"]} == {t1, t2, t3, t4}


@pytest.mark.integration
def test_adm_e_et_super_voient_aussi_toute_l_entite(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _un_parcours_en_retard(decor, "un")
    _un_parcours_en_retard(decor, "deux")

    for personne in ("adme_personne", "super_personne"):
        reponse = _suivre(parametres, decor["code"], _session(parametres, decor[personne]))
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["total"] == 2, personne


@pytest.mark.integration
def test_dsm_ne_voit_que_son_consultant_rattache(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, t_rattache = _un_parcours_en_retard(decor, "dsm-rattache", dsm_rattache=True)
    _un_parcours_en_retard(decor, "sans-dsm")

    reponse = _suivre(parametres, decor["code"], _session(parametres, decor["dsm_personne"]))
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 1
    assert corps["taches"][0]["id"] == t_rattache


@pytest.mark.integration
def test_booster_ne_voit_que_son_cercle(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, t_cercle = _un_parcours_en_retard(decor, "cercle", cercle=decor["cercle"])
    _un_parcours_en_retard(decor, "autre-cercle", cercle=decor["autre_cercle"])

    reponse = _suivre(parametres, decor["code"], _session(parametres, decor["booster_personne"]))
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 1
    assert corps["taches"][0]["id"] == t_cercle


@pytest.mark.integration
def test_personne_sans_role_ne_voit_que_ses_propres_taches(decor: dict[str, Any]) -> None:
    """`SOI` : le plancher universel, jamais une consequence du role — voir
    `resoudre_le_perimetre_du_suivi`, en-tete."""
    parametres = decor["parametres"]
    personne_a, appartenance_a = _consultant(decor, "soi-a")
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-soi",
        taches=[decor["tache_globale"]],
    )
    (tache_a,) = _affecter(decor, appartenance_a)
    _forcer_echeance(parametres, tache_a, HIER)
    _un_parcours_en_retard(decor, "soi-b")

    reponse = _suivre(parametres, decor["code"], _session(parametres, personne_a))
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 1
    assert corps["taches"][0]["id"] == tache_a


@pytest.mark.integration
def test_tache_pas_encore_en_retard_est_exclue_puis_apparait(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, tache = _un_parcours_en_retard(decor, "temporel")
    _forcer_echeance(parametres, tache, DEMAIN)

    avant = _suivre(parametres, decor["code"], _session(parametres, decor["esm_personne"]))
    assert avant.json()["total"] == 0

    _forcer_echeance(parametres, tache, HIER)
    apres = _suivre(parametres, decor["code"], _session(parametres, decor["esm_personne"]))
    assert apres.json()["total"] == 1
    assert apres.json()["taches"][0]["id"] == tache


@pytest.mark.integration
def test_tache_terminee_est_exclue(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, tache = _un_parcours_en_retard(decor, "terminee")
    _terminer_directement(parametres, tache)

    reponse = _suivre(parametres, decor["code"], _session(parametres, decor["esm_personne"]))
    assert reponse.json()["total"] == 0


@pytest.mark.integration
def test_tache_optionnelle_sur_instance_archivee_est_exclue(decor: dict[str, Any]) -> None:
    """L'automatique de `T11` archive des que la DERNIERE tache OBLIGATOIRE
    est terminee. Une tache NON obligatoire, encore `todo`, en retard,
    laissee sur une instance desormais `archived` : le §8.1 ne demande pas
    de la signaler, et `oi.state = 'active'` l'exclut deliberement."""
    parametres = decor["parametres"]
    personne, appartenance = _consultant(decor, "residuelle")
    with moteur(parametres).begin() as cx:
        deuxieme_reference = _tache_de_reference(cx, None, f"{decor['marqueur']}-residuelle-bis")
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-residuel",
        taches=[decor["tache_globale"], deuxieme_reference],
    )
    tache_obligatoire, tache_optionnelle = _affecter(decor, appartenance)
    _rendre_optionnelle(parametres, tache_optionnelle)
    _forcer_echeance(parametres, tache_optionnelle, HIER)

    achevement = _appeler_ecriture(
        parametres,
        CHEMIN_COMPLETION.format(
            code=decor["code"], appartenance=appartenance, tache=tache_obligatoire
        ),
        _session(parametres, personne),
    )
    assert achevement.status_code == 200, achevement.text

    with moteur(parametres).begin() as cx:
        etat = cx.execute(
            text(
                "SELECT state FROM onboarding_instance "
                "WHERE entity_membership_id = :a ORDER BY started_at DESC LIMIT 1"
            ),
            {"a": appartenance},
        ).scalar_one()
    assert etat == "archived"

    reponse = _suivre(parametres, decor["code"], _session(parametres, decor["esm_personne"]))
    assert reponse.json()["total"] == 0


@pytest.mark.integration
def test_ordre_et_total(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, t_recent = _un_parcours_en_retard(decor, "recent")
    _forcer_echeance(parametres, t_recent, ANCRAGE - dt.timedelta(hours=1))
    _, t_ancien = _un_parcours_en_retard(decor, "ancien")
    _forcer_echeance(parametres, t_ancien, ANCRAGE - dt.timedelta(days=10))

    reponse = _suivre(parametres, decor["code"], _session(parametres, decor["esm_personne"]))
    corps = reponse.json()
    assert corps["total"] == 2
    assert corps["pages"] == 1
    assert [t["id"] for t in corps["taches"]] == [t_ancien, t_recent]


@pytest.mark.integration
def test_401_sans_session(decor: dict[str, Any]) -> None:
    reponse = _suivre(decor["parametres"], decor["code"], None)
    assert reponse.status_code == 401


@pytest.mark.integration
def test_422_taille_invalide(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _suivre(
        parametres, decor["code"], _session(parametres, decor["esm_personne"]), taille=10
    )
    assert reponse.status_code == 422
