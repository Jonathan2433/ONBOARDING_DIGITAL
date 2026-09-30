"""Terminer une tache, l'annuler dans les cinq minutes — LOT 7, `T8`.

matrice §8.1 : « Marquer une tache comme terminee », « Annuler la completion
dans les 5 minutes ». LES DEUX LIGNES SONT IDENTIQUES — `Soi` uniquement,
tiret partout ailleurs, y compris `DSM`/`BOOST` qui portent pourtant un droit
sur la LECTURE du parcours (piege n°1, `fiche-lot-7.md` §2.1). Le temoin qui
compte n'est donc PAS un role sans aucun rattachement : c'est le `DSM`
RATTACHE a ce consultant precis, qui LIT pleinement son parcours (`T7`) et
doit pourtant etre REFUSE ici.

`annuler_la_completion` NE PRODUIT JAMAIS L'ETAT `cancelled` — UN TEMOIN LE
PROUVE DIRECTEMENT en re-terminant la meme tache apres l'avoir annulee : une
transition VERS `cancelled` (terminale) l'interdirait.

LA FENETRE DE CINQ MINUTES EST ANCREE A `completed_at`, JAMAIS A UNE HORLOGE
MOCKEE (fiche-lot-7.md §3) : le temoin « hors delai » recule `completed_at`
directement par SQL, jamais un `sleep()` ni une horloge figee.
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
CHEMIN_ANNULATION = CHEMIN_PARCOURS + "/taches/{tache}/annulation"

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
                    "account_state) VALUES (:a, :a, :prenom, 'T8', 'active') RETURNING id"
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
    marqueur = f"t8l7{uuid.uuid4().hex[:10]}"
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
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'ESM', :p, :d)"
            ),
            {"p": r["esm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=90)},
        )

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(
            cx, entite, r["dsm_personne"], arrivee=ANCRAGE.date() - dt.timedelta(days=400)
        )
        _dsm(cx, r["dsm_personne"], entite)

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
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
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
    directe en base."""
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
    """Affecte un parcours (par l'ESM) et rend l'identifiant de son unique
    tache — le decor commun a la quasi-totalite des temoins de ce fichier."""
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


def _annuler(
    parametres: Parametres, code: str, appartenance: uuid.UUID, tache: str, jeton: str | None
) -> Any:
    return _appeler_ecriture(
        parametres,
        CHEMIN_ANNULATION.format(code=code, appartenance=appartenance, tache=tache),
        jeton,
    )


def _decor_avec_parcours(decor: dict[str, Any], suffixe: str) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Cree un consultant, son parcours (modele GLOBAL) et rend
    `(consultant_personne, appartenance, tache)`."""
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
    tache = _affecter_et_lire_la_tache(parametres, decor["code"], consultant, esm_jeton)
    return consultant_personne, consultant, tache


# ===========================================================================
#  Marquer une tache comme terminee — `Soi` uniquement
# ===========================================================================


@pytest.mark.integration
def test_terminer_sa_propre_tache_la_marque_terminee(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "termine")

    reponse = _terminer(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "completed"
    assert corps["completed_at"] is not None


@pytest.mark.integration
def test_terminer_une_tache_deja_terminee_est_refusee_409(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "double")
    jeton = _session(parametres, consultant_personne)

    premiere = _terminer(parametres, decor["code"], consultant, tache, jeton)
    assert premiere.status_code == 200, premiere.text
    seconde = _terminer(parametres, decor["code"], consultant, tache, jeton)
    assert seconde.status_code == 409, seconde.text
    assert seconde.json()["erreur"]["code"] == "transition_de_tache_invalide"


@pytest.mark.integration
def test_un_DSM_RATTACHE_NE_termine_PAS_la_tache_de_SON_consultant(decor: dict[str, Any]) -> None:
    """Piege n°1 (fiche-lot-7.md §2.1) : ce DSM LIT pleinement ce parcours
    (`T7`), et doit pourtant etre REFUSE d'agir sur sa tache."""
    parametres = decor["parametres"]
    _, consultant, tache = _decor_avec_parcours(decor, "dsm-refuse")

    reponse = _terminer(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_terminer_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, tache = _decor_avec_parcours(decor, "anon-termine")

    reponse = _terminer(parametres, decor["code"], consultant, tache, None)
    assert reponse.status_code == 401, reponse.text


@pytest.mark.integration
def test_terminer_une_tache_inconnue_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, _tache = _decor_avec_parcours(decor, "tache-inconnue")

    reponse = _terminer(
        parametres,
        decor["code"],
        consultant,
        str(uuid.uuid4()),
        _session(parametres, consultant_personne),
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "tache_introuvable"


@pytest.mark.integration
def test_terminer_sans_parcours_actif_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    marqueur = decor["marqueur"]
    with moteur(parametres).begin() as cx:
        personne = _personne(cx, marqueur, "sans-parcours")
        appartenance = _appartenance(cx, decor["entite"], personne, arrivee=ANCRAGE.date())

    reponse = _terminer(
        parametres, decor["code"], appartenance, str(uuid.uuid4()), _session(parametres, personne)
    )
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["erreur"]["code"] == "aucun_parcours_actif"


@pytest.mark.integration
def test_terminer_sur_une_AUTRE_entite_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "autre-entite")

    reponse = _terminer(
        parametres,
        decor["autre_code"],
        consultant,
        tache,
        _session(parametres, consultant_personne),
    )
    assert reponse.status_code == 404, reponse.text


# ===========================================================================
#  Annuler la completion dans les cinq minutes — `Soi` uniquement
# ===========================================================================


@pytest.mark.integration
def test_annuler_dans_la_fenetre_rend_la_tache_a_todo(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "annule-a-temps")
    jeton = _session(parametres, consultant_personne)
    assert _terminer(parametres, decor["code"], consultant, tache, jeton).status_code == 200

    reponse = _annuler(parametres, decor["code"], consultant, tache, jeton)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "todo"
    assert corps["completed_at"] is None


@pytest.mark.integration
def test_annuler_une_tache_jamais_terminee_est_refusee_avec_transition_invalide(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "jamais-terminee")

    reponse = _annuler(
        parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "transition_de_tache_invalide"


@pytest.mark.integration
def test_annuler_hors_fenetre_est_refusee_avec_le_delai_depasse(decor: dict[str, Any]) -> None:
    """La fenetre est ancree a `completed_at`, JAMAIS a une horloge mockee —
    ce test RECULE `completed_at` par SQL, jamais un `sleep()`."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "hors-delai")
    jeton = _session(parametres, consultant_personne)
    assert _terminer(parametres, decor["code"], consultant, tache, jeton).status_code == 200

    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "UPDATE onboarding_instance_task SET completed_at = :six_minutes WHERE id = :tache"
            ),
            {"six_minutes": dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=6), "tache": tache},
        )

    reponse = _annuler(parametres, decor["code"], consultant, tache, jeton)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "delai_d_annulation_depasse"


@pytest.mark.integration
def test_un_DSM_RATTACHE_NE_annule_PAS_la_completion_de_SON_consultant(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "dsm-annule-refuse")
    assert (
        _terminer(
            parametres, decor["code"], consultant, tache, _session(parametres, consultant_personne)
        ).status_code
        == 200
    )

    reponse = _annuler(
        parametres, decor["code"], consultant, tache, _session(parametres, decor["dsm_personne"])
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_annuler_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    _, consultant, tache = _decor_avec_parcours(decor, "anon-annule")

    reponse = _annuler(parametres, decor["code"], consultant, tache, None)
    assert reponse.status_code == 401, reponse.text


@pytest.mark.integration
def test_re_terminer_apres_annulation_reussit_letat_nest_jamais_cancelled(
    decor: dict[str, Any],
) -> None:
    """`annuler_la_completion` rend `todo`, JAMAIS `cancelled` (terminal) —
    voir `app/onboarding/taches.py`. Ce temoin le prouve DIRECTEMENT : une
    transition vers `cancelled` interdirait cette seconde completion."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "re-termine")
    jeton = _session(parametres, consultant_personne)
    assert _terminer(parametres, decor["code"], consultant, tache, jeton).status_code == 200
    assert _annuler(parametres, decor["code"], consultant, tache, jeton).status_code == 200

    reponse = _terminer(parametres, decor["code"], consultant, tache, jeton)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["state"] == "completed"


# ===========================================================================
#  Criteres de sortie du lot — evenements historises, progression exacte
# ===========================================================================


@pytest.mark.integration
def test_les_evenements_ASSIGNED_COMPLETED_CANCELLED_sont_journalises(
    decor: dict[str, Any],
) -> None:
    """Critere de sortie n°4 (fiche §1.2) : `onboarding_task_event`, ecrit a
    `T7`-`T10`. `T7` posait la table sans y ecrire — correctif de `T8` (voir
    l'en-tete d'`app/onboarding/instances.py`) : `ASSIGNED` est desormais posee
    par l'affectation elle-meme, `COMPLETED`/`CANCELLED` par ce module."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "evenements")
    jeton = _session(parametres, consultant_personne)
    assert _terminer(parametres, decor["code"], consultant, tache, jeton).status_code == 200
    assert _annuler(parametres, decor["code"], consultant, tache, jeton).status_code == 200

    with moteur(parametres).begin() as cx:
        lignes = cx.execute(
            text(
                "SELECT event_type, actor_person_id FROM onboarding_task_event "
                "WHERE onboarding_instance_task_id = :tache ORDER BY occurred_at"
            ),
            {"tache": tache},
        ).all()
    types = [str(ligne[0]) for ligne in lignes]
    assert types == ["ASSIGNED", "COMPLETED", "CANCELLED"], types
    for ligne in lignes:
        assert ligne[1] is not None, "un acteur humain doit etre trace pour chaque evenement"


@pytest.mark.integration
def test_la_progression_change_quand_une_tache_est_completee(decor: dict[str, Any]) -> None:
    """Critere de sortie n°3, temoin POSITIF (§7.39 du LOT 6) : la progression
    est COMPTEE, pas seulement absente de colonne — elle doit varier quand
    l'etat d'une tache change, sans qu'aucune ecriture ne touche une colonne
    de progression."""
    parametres = decor["parametres"]
    consultant_personne, consultant, tache = _decor_avec_parcours(decor, "progression")
    jeton = _session(parametres, consultant_personne)

    avant = _appeler_lecture(
        parametres, CHEMIN_PARCOURS.format(code=decor["code"], appartenance=consultant), jeton
    ).json()
    assert avant["progression"] == {
        "taches_obligatoires_totales": 1,
        "taches_obligatoires_terminees": 0,
    }

    assert _terminer(parametres, decor["code"], consultant, tache, jeton).status_code == 200

    apres = _appeler_lecture(
        parametres, CHEMIN_PARCOURS.format(code=decor["code"], appartenance=consultant), jeton
    ).json()
    assert apres["progression"] == {
        "taches_obligatoires_totales": 1,
        "taches_obligatoires_terminees": 1,
    }
