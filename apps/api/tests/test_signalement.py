"""Le signalement d'un bug — LOT 10, `T11`, `MVP-L10-US005`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. aucune garde de role au-dela d'une session etablie — un simple
     consultant SANS aucune responsabilite Framework peut signaler, exactement
     comme un DSM (temoin positif pour les deux, §7.39) ;
  2. l'entite rattachee est TOUJOURS l'entite PRINCIPALE du rapporteur, jamais
     une valeur soumise par le client — le corps de la requete ne porte
     d'ailleurs aucun champ d'entite ;
  3. `application_version`/`environment` sont ceux du SERVEUR
     (`Parametres.APP_VERSION`/`APP_ENV`), jamais soumis par le client ;
  4. `browser_summary` vient de l'en-tete `User-Agent`, minimise, jamais du
     corps de la requete ;
  5. `correlation_token` est TOUJOURS rempli, meme nullable au schema — repris
     de l'en-tete de correlation s'il est present ;
  6. une description vide est refusee en 422, avant toute ecriture ;
  7. une personne SANS appartenance principale (aucune entite a rattacher)
     est refusee en 422, explicitement, jamais un 500.

Ce fichier ne reteste PAS `entite_principale` : reutilisee telle quelle depuis
le LOT 4, deja prouvee par `test_permissions.py` (§7.27).
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

from app.auth.csrf import EN_TETE_JETON, jeton_pour
from app.auth.sessions import empreinte_de_session, ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.correlation import EN_TETE_CORRELATION
from app.shared.database import moteur
from app.support.signalement import _resumer_le_navigateur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN = "/api/v1/bug-reports"
MARQUEUR = "L10T11"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


# ============================================================================
#  `_resumer_le_navigateur` — pure, aucune base requise
# ============================================================================


def test_resume_navigateur_rend_none_sur_absence() -> None:
    assert _resumer_le_navigateur(None) is None
    assert _resumer_le_navigateur("   ") is None


def test_resume_navigateur_est_tronque_et_strippe() -> None:
    brut = "Mozilla/5.0 " + ("x" * 500)
    resume = _resumer_le_navigateur(brut)
    assert resume is not None
    assert len(resume) == 200
    assert resume == brut.strip()[:200]


def test_resume_navigateur_court_est_inchange() -> None:
    assert _resumer_le_navigateur("  Mozilla/5.0 (Test)  ") == "Mozilla/5.0 (Test)"


# ============================================================================
#  La route HTTP
# ============================================================================


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"{MARQUEUR.lower()}{uuid.uuid4().hex[:10]}"
    code = f"{marqueur}-e"
    maintenant = dt.datetime.now(tz=dt.UTC)

    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, "
                "timezone, activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', "
                "'Europe/Paris', now()) RETURNING id"
            ),
            {"code": code, "nom": marqueur, "ville": marqueur},
        ).scalar_one()

        def _personne(suffixe: str) -> uuid.UUID:
            adresse = f"{marqueur}-{suffixe}@exemple.test"
            return cx.execute(  # type: ignore[no-any-return]
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, 'Signalement', :s, 'active') "
                    "RETURNING id"
                ),
                {"a": adresse, "s": suffixe},
            ).scalar_one()

        def _appartenance(personne: uuid.UUID) -> None:
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :d, 'active', 'consultant', 'draft')"
                ),
                {"p": personne, "e": entite, "d": maintenant.date()},
            )

        #  Un simple consultant, SANS aucune responsabilite Framework —
        #  le temoin central de ce module.
        consultant = _personne("consultant")
        _appartenance(consultant)

        #  Un DSM — temoin que les roles elargis fonctionnent AUSSI, pas
        #  seulement eux.
        dsm = _personne("dsm")
        _appartenance(dsm)
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'DSM', :p, :d)"
            ),
            {"p": dsm, "e": entite, "d": maintenant - dt.timedelta(days=1)},
        )

        #  Une personne SANS AUCUNE appartenance — le cas 422.
        sans_entite = _personne("sans-entite")

        def _jeton(personne: uuid.UUID) -> str:
            jeton, _ = ouvrir_une_session(
                cx,
                personne=personne,
                instant=maintenant,
                jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
            )
            return jeton

        donnees = {
            "parametres": parametres,
            "code": code,
            "entite": entite,
            "consultant": consultant,
            "jeton_consultant": _jeton(consultant),
            "jeton_dsm": _jeton(dsm),
            "jeton_sans_entite": _jeton(sans_entite),
            "marqueur": marqueur,
        }

    try:
        yield donnees
    finally:
        with moteur(parametres).begin() as menage:
            menage.execute(
                text(
                    "DELETE FROM user_session WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized LIKE :m)"
                ),
                {"m": f"{marqueur}-%"},
            )
            menage.execute(
                text(
                    "DELETE FROM bug_report WHERE reported_by_person_id IN "
                    "(SELECT id FROM person WHERE email_normalized LIKE :m)"
                ),
                {"m": f"{marqueur}-%"},
            )
            menage.execute(
                text(
                    "DELETE FROM framework_responsibility_assignment WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized LIKE :m)"
                ),
                {"m": f"{marqueur}-%"},
            )
            menage.execute(
                text(
                    "DELETE FROM entity_membership WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized LIKE :m)"
                ),
                {"m": f"{marqueur}-%"},
            )
            menage.execute(
                text("DELETE FROM person WHERE email_normalized LIKE :m"), {"m": f"{marqueur}-%"}
            )
            menage.execute(text("DELETE FROM entity WHERE code = :c"), {"c": code})


def _appeler(
    parametres: Parametres,
    jeton: str | None,
    corps: dict[str, Any],
    *,
    en_tetes: dict[str, str] | None = None,
    avec_csrf: bool = True,
) -> Any:
    """POST protege par les deux barrieres CSRF — §7.4, `DEC-531`.

    Memes motif et montage que `test_catalogue_des_taches.py` : `PUBLIC_BASE_URL`
    est aligne sur `ORIGINE_DE_TEST` pour que `origine_attendue` l'accepte.
    `avec_csrf=False` eprouve le refus — jamais recopie, voir
    `test_le_refus_csrf_sans_origine_ni_jeton`.
    """
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes = dict(en_tetes or {})
        if avec_csrf:
            entetes["Origin"] = ORIGINE_DE_TEST
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            if avec_csrf:
                entetes[EN_TETE_JETON] = jeton_pour(
                    empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
                )
        return client.post(CHEMIN, json=corps, headers=entetes)


def _ligne_du_signalement(parametres: Parametres, identifiant: str) -> Any:
    with moteur(parametres).connect() as cx:
        return (
            cx.execute(text("SELECT * FROM bug_report WHERE id = :i"), {"i": identifiant})
            .mappings()
            .one()
        )


@pytest.mark.integration
def test_la_route_exige_une_session(decor: dict[str, Any]) -> None:
    corps = {"description": "Le bouton ne repond pas.", "chemin_de_page": "/entites/x/framework"}
    assert _appeler(decor["parametres"], None, corps).status_code == 401


@pytest.mark.integration
def test_le_refus_csrf_sans_origine_ni_jeton(decor: dict[str, Any]) -> None:
    """Temoin NEGATIF — le positif est chaque autre test de ce fichier, qui
    passe tous par la meme barriere avec `avec_csrf=True` (§7.39)."""
    corps = {"description": "Tentative sans CSRF.", "chemin_de_page": "/entites/x"}
    reponse = _appeler(decor["parametres"], decor["jeton_consultant"], corps, avec_csrf=False)
    assert reponse.status_code == 403


@pytest.mark.integration
def test_un_simple_consultant_SANS_aucune_responsabilite_peut_signaler(
    decor: dict[str, Any],
) -> None:
    """LE TEMOIN CENTRAL — voir l'en-tete d'`app/support/routes.py`.

    La matrice §17 ne porte aucune colonne `EMP`, et aucune ligne de ce
    tableau ne nomme de tiret sur « Reporter un bug ». Si une garde de role
    refusait un simple consultant, ce test tomberait en 403.
    """
    corps = {
        "description": "La page d'accueil affiche un ecran blanc.",
        "chemin_de_page": "/entites/x/accueil",
    }
    reponse = _appeler(decor["parametres"], decor["jeton_consultant"], corps)
    assert reponse.status_code == 201, reponse.text
    corps_rendu = reponse.json()
    assert corps_rendu["etat"] == "new"
    uuid.UUID(corps_rendu["identifiant"])


@pytest.mark.integration
def test_un_role_elargi_peut_signaler_aussi(decor: dict[str, Any]) -> None:
    corps = {"description": "Le tableau de bord est faux.", "chemin_de_page": "/entites/x"}
    reponse = _appeler(decor["parametres"], decor["jeton_dsm"], corps)
    assert reponse.status_code == 201, reponse.text


@pytest.mark.integration
def test_la_description_vide_est_refusee(decor: dict[str, Any]) -> None:
    corps = {"description": "", "chemin_de_page": "/entites/x"}
    reponse = _appeler(decor["parametres"], decor["jeton_consultant"], corps)
    assert reponse.status_code == 422


@pytest.mark.integration
def test_aucune_entite_principale_rend_422_jamais_500(decor: dict[str, Any]) -> None:
    corps = {"description": "Un bug.", "chemin_de_page": "/entites/x"}
    reponse = _appeler(decor["parametres"], decor["jeton_sans_entite"], corps)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "aucune_entite_principale"


@pytest.mark.integration
def test_le_signalement_est_rattache_a_l_entite_principale_du_rapporteur(
    decor: dict[str, Any],
) -> None:
    """AUCUN CHAMP D'ENTITE DANS LE CORPS : rien a soumettre, rien a usurper."""
    corps = {"description": "Erreur sur la fiche profil.", "chemin_de_page": "/entites/x/profil"}
    reponse = _appeler(decor["parametres"], decor["jeton_consultant"], corps)
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_du_signalement(decor["parametres"], reponse.json()["identifiant"])
    assert ligne["entity_id"] == decor["entite"]
    assert ligne["reported_by_person_id"] == decor["consultant"]


@pytest.mark.integration
def test_contexte_technique_est_ajoute_automatiquement_jamais_soumis(
    decor: dict[str, Any],
) -> None:
    """`application_version`/`environment` viennent du SERVEUR, pas du client.

    Le corps de la requete ne porte meme pas ces champs — le client ne peut
    donc structurellement pas les usurper.
    """
    corps = {"description": "Erreur de version.", "chemin_de_page": "/entites/x"}
    reponse = _appeler(
        decor["parametres"],
        decor["jeton_consultant"],
        corps,
        en_tetes={"User-Agent": "NavigateurDeTest/1.0"},
    )
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_du_signalement(decor["parametres"], reponse.json()["identifiant"])
    assert ligne["application_version"] == decor["parametres"].APP_VERSION
    assert ligne["environment"] == decor["parametres"].APP_ENV
    assert ligne["browser_summary"] == "NavigateurDeTest/1.0"


@pytest.mark.integration
def test_correlation_token_est_toujours_rempli_et_repris_de_l_en_tete(
    decor: dict[str, Any],
) -> None:
    corps = {"description": "Erreur de correlation.", "chemin_de_page": "/entites/x"}
    reponse = _appeler(
        decor["parametres"],
        decor["jeton_consultant"],
        corps,
        en_tetes={EN_TETE_CORRELATION: "corr-l10t11-temoin"},
    )
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_du_signalement(decor["parametres"], reponse.json()["identifiant"])
    assert ligne["correlation_token"] == "corr-l10t11-temoin"


@pytest.mark.integration
def test_les_etapes_de_reproduction_sont_facultatives(decor: dict[str, Any]) -> None:
    corps = {"description": "Sans etapes.", "chemin_de_page": "/entites/x"}
    reponse = _appeler(decor["parametres"], decor["jeton_consultant"], corps)
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_du_signalement(decor["parametres"], reponse.json()["identifiant"])
    assert ligne["reproduction_steps"] is None
