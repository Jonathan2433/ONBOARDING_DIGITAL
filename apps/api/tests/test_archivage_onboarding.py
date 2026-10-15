"""Archiver et restaurer un parcours d'onboarding — LOT 7, `T11`, ferme `§30.13`.

matrice §8.1 : « Archiver un parcours termine » (`NEW` = Automatique,
`ESM`/`ADM-E`/`SUPER` = Entite/Entite/Global) et « Restaurer un parcours
archive » (`ECART-066`, volet parcours, RESOLU le 28/09/2026 : l'ESM restaure
librement dans son entite, meme regime que la restauration d'une version de
modele, `T6`/`DEC-605`).

DEUX DECLENCHEURS AUTOMATIQUES, TESTES SANS AUCUNE NOUVELLE GARDE DE PERMISSION

  « Marquer une tache comme terminee » (`T8`, garde `Soi`) et « Archiver un
  profil » (LOT 5 `T8`, sa propre garde) sont deja pleinement testes ailleurs.
  Les tests de cette section appellent donc leurs routes HTTP EXISTANTES et
  observent le SEUL fait nouveau : l'instance d'onboarding passe a `archived`.

DEUX GESTES MANUELS, AVEC LA MEME GRILLE QUE LA REOUVERTURE (`T9`)

  `ESM`/`ADM-E`/`SUPER` seulement, `DSM`/`BOOST` EXCLUS EN BLOC — meme un DSM
  RATTACHE a ce consultant precis (qui LIT et AFFECTE pleinement son parcours,
  `T7`) doit etre REFUSE ici, piege n°1 de `fiche-lot-7.md` §2.1 rejoue une
  quatrieme fois.

LE FILET MANUEL NE TROUVE NORMALEMENT RIEN A FAIRE

  Pour l'archivage MANUEL, l'automatique ayant deja agi des la derniere
  completion, le temoin positif construit deliberement le cas RESIDUEL —
  toutes les taches obligatoires `completed` SANS passer par `terminer_une_
  tache` (donc sans que l'automatique ait eu l'occasion de s'exercer) — pour
  prouver que le filet fonctionne vraiment, pas seulement qu'il ne casse rien.
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
CHEMIN_ARCHIVAGE_PARCOURS = CHEMIN_PARCOURS + "/archivage"
CHEMIN_RESTAURATION_PARCOURS = CHEMIN_PARCOURS + "/{instance}/restauration"
CHEMIN_ARCHIVAGE_PROFIL = "/api/v1/entities/{code}/people/{appartenance}/archivage"

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
                    "account_state) VALUES (:a, :a, :prenom, 'T11', 'active') RETURNING id"
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


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t11l7{uuid.uuid4().hex[:10]}"
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
            #  AVANT `person` : `framework_responsibility_assignment` (DSM,
            #  ESM) reference `assigned_by_person_id` — meme ordre que `T9`.
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            #  LOT 10, `T3` : l'archivage d'un profil (route HTTP de ce
            #  fichier) ecrit desormais `audit_event` aussi —
            #  `actor_person_id` ET `entity_id` y referencent `person`/
            #  `entity`, meme classe que `T2` pour `auth_event` (§7.30).
            "DELETE FROM audit_event WHERE actor_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM audit_event WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
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
    parametres: Parametres,
    code_entite: str,
    jeton: str | None,
    *,
    name: str,
    taches: list[uuid.UUID],
) -> None:
    """Cree un modele ENTITY (l'ESM le gere pleinement), une version, ses
    taches — toutes OBLIGATOIRES par defaut du service — puis PUBLIE."""
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


def _affecter_et_lire_les_taches(
    parametres: Parametres, code: str, appartenance: uuid.UUID, jeton: str | None
) -> list[str]:
    reponse = _appeler_ecriture(
        parametres, CHEMIN_PARCOURS.format(code=code, appartenance=appartenance), jeton
    )
    assert reponse.status_code == 201, reponse.text
    return [str(t["id"]) for t in reponse.json()["taches"]]


def _affecter(decor: dict[str, Any], appartenance: uuid.UUID) -> list[str]:
    """« Affecter un parcours » N'A PAS DE `Soi` (`perimetre.py`, en-tete) :
    contrairement a la lecture ou la completion, l'ESM affecte — jamais le
    consultant lui-meme."""
    parametres = decor["parametres"]
    return _affecter_et_lire_les_taches(
        parametres, decor["code"], appartenance, _session(parametres, decor["esm_personne"])
    )


def _terminer(
    parametres: Parametres, code: str, appartenance: uuid.UUID, tache: str, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_COMPLETION.format(code=code, appartenance=appartenance, tache=tache),
        jeton,
    )


def _archiver_le_parcours(
    parametres: Parametres, code: str, appartenance: uuid.UUID, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres, CHEMIN_ARCHIVAGE_PARCOURS.format(code=code, appartenance=appartenance), jeton
    )


def _restaurer_le_parcours(
    parametres: Parametres, code: str, appartenance: uuid.UUID, instance: str, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_RESTAURATION_PARCOURS.format(
            code=code, appartenance=appartenance, instance=instance
        ),
        jeton,
    )


def _archiver_le_profil(
    parametres: Parametres,
    code: str,
    appartenance: uuid.UUID,
    jeton: str | None,
    *,
    version: int = 1,
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_ARCHIVAGE_PROFIL.format(code=code, appartenance=appartenance),
        jeton,
        {"version": version},
    )


def _consultant_avec_appartenance(
    decor: dict[str, Any], suffixe: str, *, dsm_rattache: bool = False
) -> tuple[uuid.UUID, uuid.UUID]:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        consultant_personne = _personne(cx, marqueur, f"consultant-{suffixe}")
        consultant = _appartenance(cx, decor["entite"], consultant_personne, arrivee=ANCRAGE.date())
        _statut_intercontrat(cx, decor["entite"], consultant)
        if dsm_rattache:
            _dsm_de_ce_consultant(cx, decor["entite"], consultant, decor["dsm_personne"])
    return consultant_personne, consultant


def _etat_de_l_instance(parametres: Parametres, instance: str) -> tuple[str, Any]:
    with moteur(parametres).begin() as cx:
        ligne = cx.execute(
            text("SELECT state, completed_at FROM onboarding_instance WHERE id = :i"),
            {"i": instance},
        ).one()
    return str(ligne[0]), ligne[1]


def _marquer_termine_sans_passer_par_la_route(parametres: Parametres, tache: str) -> None:
    """Simule le seul cas ou le geste MANUEL trouve quelque chose a faire :
    une tache obligatoire `completed` SANS que `terminer_une_tache` n'ait
    jamais tourne, donc sans que l'automatique (`archiver_le_parcours_si_
    termine`) n'ait eu l'occasion de s'exercer."""
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "UPDATE onboarding_instance_task SET state = 'completed', "
                "completed_at = :instant WHERE id = :tache"
            ),
            {"instant": ANCRAGE, "tache": tache},
        )


# ===========================================================================
#  Les deux declencheurs AUTOMATIQUES — aucune nouvelle garde a tester
# ===========================================================================


@pytest.mark.integration
def test_terminer_la_derniere_tache_obligatoire_archive_automatiquement(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-auto",
        taches=[decor["tache_globale"]],
    )
    consultant_personne, consultant = _consultant_avec_appartenance(decor, "auto")
    jeton_consultant = _session(parametres, consultant_personne)
    (tache,) = _affecter(decor, consultant)

    reponse = _terminer(parametres, decor["code"], consultant, tache, jeton_consultant)
    assert reponse.status_code == 200, reponse.text

    with moteur(parametres).begin() as cx:
        instance = str(
            cx.execute(
                text("SELECT onboarding_instance_id FROM onboarding_instance_task WHERE id = :t"),
                {"t": tache},
            ).scalar_one()
        )
    etat, complete_le = _etat_de_l_instance(parametres, instance)
    assert etat == "archived"
    assert complete_le is not None, "un parcours ACHEVE porte `completed_at`"


@pytest.mark.integration
def test_terminer_une_tache_non_derniere_n_archive_pas(decor: dict[str, Any]) -> None:
    """Deux taches obligatoires : en terminer UNE seule laisse l'instance
    `active` — le geste automatique ne prouve rien s'il archive TOUJOURS."""
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        seconde_tache = _tache_de_reference(cx, None, f"{decor['marqueur']}-tache-deux")
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-deux-taches",
        taches=[decor["tache_globale"], seconde_tache],
    )
    consultant_personne, consultant = _consultant_avec_appartenance(decor, "pas-derniere")
    jeton_consultant = _session(parametres, consultant_personne)
    taches = _affecter(decor, consultant)
    assert len(taches) == 2

    reponse = _terminer(parametres, decor["code"], consultant, taches[0], jeton_consultant)
    assert reponse.status_code == 200, reponse.text

    with moteur(parametres).begin() as cx:
        instance = str(
            cx.execute(
                text("SELECT onboarding_instance_id FROM onboarding_instance_task WHERE id = :t"),
                {"t": taches[0]},
            ).scalar_one()
        )
    etat, complete_le = _etat_de_l_instance(parametres, instance)
    assert etat == "active"
    assert complete_le is None


@pytest.mark.integration
def test_le_depart_archive_automatiquement_le_parcours_actif(decor: dict[str, Any]) -> None:
    """Matrice §8.2 : « le depart d'un collaborateur archive le parcours ».
    `T11` s'accroche a `archiver_un_profil` (LOT 5 `T8`) sans dupliquer la
    revocation, deja pleinement testee ailleurs (`test_archivage.py`)."""
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-depart",
        taches=[decor["tache_globale"]],
    )
    _, consultant = _consultant_avec_appartenance(decor, "depart")
    (tache,) = _affecter(decor, consultant)
    with moteur(parametres).begin() as cx:
        instance = str(
            cx.execute(
                text("SELECT onboarding_instance_id FROM onboarding_instance_task WHERE id = :t"),
                {"t": tache},
            ).scalar_one()
        )

    reponse = _archiver_le_profil(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["parcours_onboarding_archive"] == instance

    etat, complete_le = _etat_de_l_instance(parametres, instance)
    assert etat == "archived"
    assert complete_le is None, "un parcours INTERROMPU par le depart ne porte pas `completed_at`"


@pytest.mark.integration
def test_le_depart_sans_parcours_actif_ne_fait_rien(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant = _consultant_avec_appartenance(decor, "sans-parcours")

    reponse = _archiver_le_profil(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["parcours_onboarding_archive"] is None


# ===========================================================================
#  Le geste MANUEL — meme grille que la reouverture (T9)
# ===========================================================================


@pytest.mark.integration
def test_esm_archive_manuellement_un_parcours_termine_que_l_automatique_n_a_pas_couvert(
    decor: dict[str, Any],
) -> None:
    """Le CAS RESIDUEL : toutes les taches obligatoires `completed` sans
    passer par `terminer_une_tache`, donc sans que l'automatique n'ait agi —
    le geste manuel doit trouver quelque chose a faire, et le faire."""
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-manuel",
        taches=[decor["tache_globale"]],
    )
    _, consultant = _consultant_avec_appartenance(decor, "manuel-esm")
    (tache,) = _affecter(decor, consultant)
    _marquer_termine_sans_passer_par_la_route(parametres, tache)

    reponse = _archiver_le_parcours(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "archived"
    assert reponse.json()["completed_at"] is not None


@pytest.mark.integration
def test_un_DSM_RATTACHE_NE_archive_PAS_manuellement(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-dsm-refuse",
        taches=[decor["tache_globale"]],
    )
    _, consultant = _consultant_avec_appartenance(decor, "dsm-refuse-archivage", dsm_rattache=True)
    (tache,) = _affecter(decor, consultant)
    _marquer_termine_sans_passer_par_la_route(parametres, tache)

    reponse = _archiver_le_parcours(
        parametres, decor["code"], consultant, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_archiver_un_parcours_non_termine_est_409(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-non-termine",
        taches=[decor["tache_globale"]],
    )
    _, consultant = _consultant_avec_appartenance(decor, "non-termine")
    _affecter(decor, consultant)

    reponse = _archiver_le_parcours(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "parcours_non_termine"


@pytest.mark.integration
def test_archiver_sans_parcours_actif_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant = _consultant_avec_appartenance(decor, "aucun-parcours")

    reponse = _archiver_le_parcours(
        parametres, decor["code"], consultant, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "aucun_parcours_actif"


# ===========================================================================
#  La restauration — ECART-066 (volet parcours) resolu
# ===========================================================================


def _parcours_archive(decor: dict[str, Any], suffixe: str) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Cree un consultant, son parcours, le TERMINE et l'archive
    AUTOMATIQUEMENT — l'etat de depart de tous les temoins de restauration."""
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-{suffixe}",
        taches=[decor["tache_globale"]],
    )
    consultant_personne, consultant = _consultant_avec_appartenance(decor, suffixe)
    jeton_consultant = _session(parametres, consultant_personne)
    (tache,) = _affecter(decor, consultant)
    assert (
        _terminer(parametres, decor["code"], consultant, tache, jeton_consultant).status_code == 200
    )
    with moteur(parametres).begin() as cx:
        instance = str(
            cx.execute(
                text("SELECT onboarding_instance_id FROM onboarding_instance_task WHERE id = :t"),
                {"t": tache},
            ).scalar_one()
        )
    etat, _ = _etat_de_l_instance(parametres, instance)
    assert etat == "archived"
    return consultant_personne, consultant, instance


@pytest.mark.integration
def test_esm_restaure_un_parcours_archive(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, instance = _parcours_archive(decor, "restaure-esm")

    reponse = _restaurer_le_parcours(
        parametres, decor["code"], consultant, instance, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "active"
    assert corps["completed_at"] is None, "l'archivage passe est desappose a la restauration"


@pytest.mark.integration
def test_le_super_administrateur_restaure(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, instance = _parcours_archive(decor, "restaure-super")

    reponse = _restaurer_le_parcours(
        parametres,
        decor["code"],
        consultant,
        instance,
        _session(parametres, decor["super_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "active"


@pytest.mark.integration
def test_un_DSM_RATTACHE_NE_restaure_PAS(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, instance = _parcours_archive(decor, "restaure-dsm-refuse")
    with moteur(parametres).begin() as cx:
        _dsm_de_ce_consultant(cx, decor["entite"], consultant, decor["dsm_personne"])

    reponse = _restaurer_le_parcours(
        parametres, decor["code"], consultant, instance, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_restaurer_une_instance_qui_n_est_pas_archivee_est_409(decor: dict[str, Any]) -> None:
    """L'instance existe bien pour cette appartenance, mais elle est
    `active` — pas `archived` : refus PROPRE, jamais une `IntegrityError`
    brute (§7.32)."""
    parametres = decor["parametres"]
    _creer_modele_publie(
        parametres,
        decor["code"],
        _session(parametres, decor["esm_personne"]),
        name=f"{decor['marqueur']}-modele-encore-active",
        taches=[decor["tache_globale"]],
    )
    _, consultant = _consultant_avec_appartenance(decor, "encore-active")
    (tache,) = _affecter(decor, consultant)
    with moteur(parametres).begin() as cx:
        instance = str(
            cx.execute(
                text("SELECT onboarding_instance_id FROM onboarding_instance_task WHERE id = :t"),
                {"t": tache},
            ).scalar_one()
        )

    reponse = _restaurer_le_parcours(
        parametres, decor["code"], consultant, instance, _session(parametres, decor["esm_personne"])
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "parcours_non_archivable"


@pytest.mark.integration
def test_restaurer_quand_une_autre_instance_est_deja_active_est_409(
    decor: dict[str, Any],
) -> None:
    """Le meme refus proprement lisible que l'index partiel de `T1`
    imposerait de toute facon — mesure ici plutot qu'une `IntegrityError`."""
    parametres = decor["parametres"]
    _, consultant, ancienne_instance = _parcours_archive(decor, "conflit-restauration")
    #  Une SECONDE affectation apres l'archivage automatique : l'index partiel
    #  de `T1` l'autorise, puisque l'ancienne n'est plus `active`.
    _affecter(decor, consultant)

    reponse = _restaurer_le_parcours(
        parametres,
        decor["code"],
        consultant,
        ancienne_instance,
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "parcours_non_archivable"


@pytest.mark.integration
def test_restaurer_une_instance_inconnue_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, _instance = _parcours_archive(decor, "instance-inconnue")

    reponse = _restaurer_le_parcours(
        parametres,
        decor["code"],
        consultant,
        str(uuid.uuid4()),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "instance_introuvable"


@pytest.mark.integration
def test_restaurer_ne_rouvre_aucune_tache(decor: dict[str, Any]) -> None:
    """« Restaurer un parcours n'est pas restaurer une personne » — la tache
    `completed` reste `completed`, jamais reouverte a `todo`."""
    parametres = decor["parametres"]
    _, consultant, instance = _parcours_archive(decor, "aucune-reouverture")

    assert (
        _restaurer_le_parcours(
            parametres,
            decor["code"],
            consultant,
            instance,
            _session(parametres, decor["esm_personne"]),
        ).status_code
        == 200
    )

    with moteur(parametres).begin() as cx:
        etats = [
            str(ligne[0])
            for ligne in cx.execute(
                text(
                    "SELECT state FROM onboarding_instance_task WHERE onboarding_instance_id = :i"
                ),
                {"i": instance},
            ).all()
        ]
    assert etats == ["completed"]


@pytest.mark.integration
def test_archiver_et_restaurer_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, instance = _parcours_archive(decor, "anon")

    assert _archiver_le_parcours(parametres, decor["code"], consultant, None).status_code == 401
    assert (
        _restaurer_le_parcours(parametres, decor["code"], consultant, instance, None).status_code
        == 401
    )
