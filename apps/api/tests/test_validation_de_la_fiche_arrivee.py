"""Completer, valider et publier la fiche d'arrivee — LOT 7, `T3`.

`MVP-L07-US001` (2/2), `MVP-L07-US002`.

LA VALIDATION PUBLIE DANS LE MEME APPEL, ET C'EST LE TEMOIN CENTRAL

  Matrice §7.1 : « publiee automatiquement […] ne necessite pas une
  approbation prealable ». `test_la_validation_PUBLIE_dans_le_MEME_appel`
  prouve qu'un SEUL appel HTTP fait passer `state` de `draft` a `published`,
  avec `validated_at == published_at` — un test qui exigerait deux appels
  serait faux ici (§7.39 du LOT 6).

L'ASYMETRIE `BOOST` EST LE SECOND TEMOIN CENTRAL

  `Support cercle` sur « Completer », TIRET sur « Valider et publier » — la
  SEULE des trois lignes du §7 ou `BOOST` differe. Le decor donne au Booster
  un membre reel de son cercle pour prouver qu'il peut completer SA fiche, et
  la MEME cible pour prouver qu'il ne peut PAS la valider.
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
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.modeles import EtatAppartenance
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_FICHE = "/api/v1/entities/{code}/people/{appartenance}/arrival-profile"
CHEMIN_VALIDATION = CHEMIN_FICHE + "/validation"

ANCRAGE = dt.datetime(2026, 9, 25, 9, 0, tzinfo=dt.UTC)
ARRIVEE = dt.date(2026, 10, 15)


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
                    "account_state) VALUES (:a, :a, :prenom, 'T3', 'active') RETURNING id"
                ),
                {"a": adresse, "prenom": suffixe},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = EtatAppartenance.ACTIVE.value,
    arrivee: dt.date = ARRIVEE,
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'draft') RETURNING id"
                ),
                {"p": personne, "e": entite, "arrivee": arrivee, "etat": etat},
            ).scalar_one()
        )
    )


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _appeler_lecture(parametres: Parametres, chemin: str, jeton: str) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


def _appeler_ecriture(
    parametres: Parametres, methode: str, chemin: str, jeton: str, corps: dict[str, Any]
) -> Any:
    """PATCH/POST proteges par les deux barrieres CSRF — §7.4, `DEC-531`.

    `PUBLIC_BASE_URL` est force a l'origine du `TestClient` : sans cela,
    l'en-tete `Origin` que ce client envoie serait etranger a la configuration
    par defaut et la premiere barriere refuserait avant meme la seconde.
    """
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    jeton_csrf = jeton_pour(empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY)
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
        appelable = getattr(client, methode)
        return appelable(
            chemin, json=corps, headers={"Origin": ORIGINE_DE_TEST, EN_TETE_JETON: jeton_csrf}
        )


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite, un nouvel arrivant, un ESM, un Booster de SON cercle, un DSM
    rattache, un employe nu — la meme famille de personas que `T2`.
    """
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t3l7{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres}

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

        r["arrivant_personne"] = _personne(cx, marqueur, "arrivant")
        r["arrivant"] = _appartenance(
            cx, entite, r["arrivant_personne"], etat=EtatAppartenance.FUTURE.value
        )

        r["cercle"] = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
        ).scalar_one()
        cx.execute(
            text(
                "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
                "membership_type, starts_at) VALUES (:e, :m, :c, :type, :d)"
            ),
            {
                "e": entite,
                "m": r["arrivant"],
                "c": r["cercle"],
                "type": TypeAppartenanceCercle.PRINCIPAL.value,
                "d": dt.date(2026, 9, 1),
            },
        )

        #  Le Booster du cercle ci-dessus — Support cercle sur « Completer »,
        #  TIRET sur « Valider et publier ». Sa PROPRE appartenance est requise
        #  — `resoudre_les_permissions` n'accorde un role de responsabilite que
        #  dans l'entite PRINCIPALE de l'acteur (§2.3 de `compte-rendu-t2-lot-7`).
        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(cx, entite, r["booster_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, :type, :c, :p, :d)"
            ),
            {
                "p": r["booster_personne"],
                "e": entite,
                "type": TypeResponsabilite.BOOSTER.value,
                "c": r["cercle"],
                "d": ANCRAGE - dt.timedelta(days=1),
            },
        )

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(cx, entite, r["dsm_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'DSM', :p, :d)"
            ),
            {"p": r["dsm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
        )
        cx.execute(
            text(
                "INSERT INTO dsm_assignment (consultant_membership_id, dsm_person_id, entity_id, "
                "starts_at) VALUES (:m, :p, :e, :d)"
            ),
            {
                "m": r["arrivant"],
                "p": r["dsm_personne"],
                "e": entite,
                "d": ANCRAGE - dt.timedelta(days=1),
            },
        )

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

        r["emp_personne"] = _personne(cx, marqueur, "emp")
        _appartenance(cx, entite, r["emp_personne"])

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM arrival_profile WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM dsm_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM person WHERE email LIKE :motif_personne",
            "DELETE FROM entity WHERE code LIKE :motif",
        ):
            menage.execute(
                text(requete), {"motif": f"{marqueur}%", "motif_personne": f"{marqueur}%"}
            )


# ===========================================================================
#  Completer — matrice §7, « Completer photo, presentation et fun fact »
# ===========================================================================


@pytest.mark.integration
def test_le_nouvel_arrivant_complete_SA_PROPRE_fiche_et_la_CREE(decor: dict[str, Any]) -> None:
    """`Soi` — la premiere completion CREE la ligne, `version` etait `None`."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["arrivant_personne"]),
        {
            "version": None,
            "short_intro": "Bonjour, je rejoins l'equipe.",
            "fun_fact": "Aime le velo",
        },
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["id"] is not None
    assert corps["version"] == 1
    assert corps["state"] == "draft"


@pytest.mark.integration
def test_completer_AVEC_une_version_NON_NULLE_alors_qu_AUCUNE_ligne_n_existe_est_refuse(
    decor: dict[str, Any],
) -> None:
    """Le meme code que l'inverse : une version presente suppose une ligne."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["arrivant_personne"]),
        {"version": 1, "short_intro": "Peu importe"},
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_completer_AVEC_une_version_NULLE_alors_qu_une_ligne_EXISTE_est_refuse(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    chemin = CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"])
    premiere = _appeler_ecriture(
        parametres, "patch", chemin, jeton, {"version": None, "short_intro": "Bonjour"}
    )
    assert premiere.status_code == 200, premiere.text

    seconde = _appeler_ecriture(
        parametres, "patch", chemin, jeton, {"version": None, "short_intro": "Autre"}
    )
    assert seconde.status_code == 409, seconde.text
    assert seconde.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_le_fun_fact_peut_etre_EFFACE_explicitement(decor: dict[str, Any]) -> None:
    """`model_fields_set` distingue `absent` de `envoye a null` — §7.25 du LOT 5."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    chemin = CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"])
    creation = _appeler_ecriture(
        parametres, "patch", chemin, jeton, {"version": None, "fun_fact": "Un fait amusant"}
    )
    assert creation.status_code == 200, creation.text
    version = creation.json()["version"]

    efface = _appeler_ecriture(
        parametres, "patch", chemin, jeton, {"version": version, "fun_fact": None}
    )
    assert efface.status_code == 200, efface.text
    assert efface.json()["version"] == version + 1

    lue = _appeler_lecture(parametres, chemin, jeton)
    assert lue.json()["fun_fact"] is None


@pytest.mark.integration
def test_un_ESM_complete_la_fiche_d_un_AUTRE(decor: dict[str, Any]) -> None:
    """`Support` — portee Entite, la meme que la lecture."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["esm_personne"]),
        {"version": None, "short_intro": "Redige par un ESM en support"},
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_BOOSTER_complete_la_fiche_d_un_membre_de_SON_cercle(decor: dict[str, Any]) -> None:
    """`Support cercle` — le Booster AIDE, matrice §7."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["booster_personne"]),
        {"version": None, "short_intro": "Redige par le Booster du cercle"},
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_DSM_MEME_RATTACHE_NE_COMPLETE_PAS(decor: dict[str, Any]) -> None:
    """Le meme piege que `T2` : `DSM` est a TIRET sur CETTE ligne aussi."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["dsm_personne"]),
        {"version": None, "short_intro": "Un DSM ne devrait pas ecrire ceci"},
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "fiche_arrivee_hors_perimetre"


@pytest.mark.integration
def test_un_EMPLOYE_NU_NE_COMPLETE_PAS_la_fiche_d_un_AUTRE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["emp_personne"]),
        {"version": None, "short_intro": "Refuse"},
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_completer_APRES_publication_est_refuse_pour_TOUS(decor: dict[str, Any]) -> None:
    """Borne au brouillon — §6.2, meme pour un role `Support`."""
    parametres = decor["parametres"]
    jeton_arrivant = _session(parametres, decor["arrivant_personne"])
    chemin = CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"])
    creation = _appeler_ecriture(
        parametres,
        "patch",
        chemin,
        jeton_arrivant,
        {"version": None, "short_intro": "Presentation"},
    )
    version = creation.json()["version"]
    validation = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton_arrivant,
        {"version": version},
    )
    assert validation.status_code == 200, validation.text
    version_publiee = validation.json()["version"]

    #  L'ESM, en Support, ne peut pas non plus completer une fiche publiee.
    apres = _appeler_ecriture(
        parametres,
        "patch",
        chemin,
        _session(parametres, decor["esm_personne"]),
        {"version": version_publiee, "short_intro": "Trop tard"},
    )
    assert apres.status_code == 409, apres.text
    assert apres.json()["erreur"]["code"] == "fiche_arrivee_etat_incompatible"


@pytest.mark.integration
def test_completer_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        reponse = client.patch(
            CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
            json={"version": None, "short_intro": "x"},
        )
    assert reponse.status_code == 401, reponse.text


# ===========================================================================
#  Valider et publier — matrice §7.1, §7.2, modele §12.1
# ===========================================================================


def _completer(parametres: Parametres, decor: dict[str, Any], jeton: str, presentation: str) -> int:
    reponse = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton,
        {"version": None, "short_intro": presentation},
    )
    assert reponse.status_code == 200, reponse.text
    return int(reponse.json()["version"])


@pytest.mark.integration
def test_la_validation_PUBLIE_dans_le_MEME_appel(decor: dict[str, Any]) -> None:
    """LE TEMOIN CENTRAL. Voir l'en-tete du module : un SEUL appel publie."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    version = _completer(parametres, decor, jeton, "Bonjour a tous")

    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton,
        {"version": version},
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "published"
    assert corps["validated_at"] == corps["published_at"]
    assert corps["validated_at"] is not None


@pytest.mark.integration
def test_recent_until_est_UN_MOIS_apres_l_arrivee(decor: dict[str, Any]) -> None:
    """Modele §12.1 — calcule par PostgreSQL, pas par une soustraction Python."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    version = _completer(parametres, decor, jeton, "Bonjour")

    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton,
        {"version": version},
    )
    assert reponse.status_code == 200, reponse.text
    #  ARRIVEE = 2026-10-15 -> un mois apres = 2026-11-15.
    assert reponse.json()["recent_until"] == "2026-11-15"


@pytest.mark.integration
def test_un_ESM_valide_la_fiche_d_un_AUTRE(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    version = _completer(
        parametres, decor, _session(parametres, decor["arrivant_personne"]), "Bonjour"
    )
    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["esm_personne"]),
        {"version": version},
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_BOOSTER_NE_VALIDE_PAS(decor: dict[str, Any]) -> None:
    """L'ASYMETRIE DU §7 : `Support cercle` pour completer, TIRET pour valider."""
    parametres = decor["parametres"]
    jeton_booster = _session(parametres, decor["booster_personne"])
    #  Temoin que le Booster PEUT completer — sans quoi son refus de valider ne
    #  prouverait rien de l'asymetrie, seulement une absence generale de droit.
    version = _completer(parametres, decor, jeton_booster, "Redige par le Booster")

    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton_booster,
        {"version": version},
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "fiche_arrivee_hors_perimetre"


@pytest.mark.integration
def test_un_DSM_MEME_RATTACHE_NE_VALIDE_PAS(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    version = _completer(
        parametres, decor, _session(parametres, decor["arrivant_personne"]), "Bonjour"
    )
    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["dsm_personne"]),
        {"version": version},
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_valider_SANS_presentation_est_refuse(decor: dict[str, Any]) -> None:
    """422 — modele §12.1, la presentation est obligatoire avant validation."""
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    #  Une completion qui ne touche QUE le fun fact : aucune presentation.
    creation = _appeler_ecriture(
        parametres,
        "patch",
        CHEMIN_FICHE.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton,
        {"version": None, "fun_fact": "Sans presentation"},
    )
    assert creation.status_code == 200, creation.text

    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton,
        {"version": creation.json()["version"]},
    )
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["code"] == "fiche_arrivee_presentation_manquante"


@pytest.mark.integration
def test_valider_une_fiche_INEXISTANTE_est_refuse(decor: dict[str, Any]) -> None:
    """Rien a completer, rien a valider : `409`, pas `404` (l'appartenance existe)."""
    parametres = decor["parametres"]
    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["arrivant_personne"]),
        {"version": 1},
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "fiche_arrivee_etat_incompatible"


@pytest.mark.integration
def test_valider_une_fiche_DEJA_PUBLIEE_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    version = _completer(parametres, decor, jeton, "Bonjour")
    chemin_validation = CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"])
    premiere = _appeler_ecriture(parametres, "post", chemin_validation, jeton, {"version": version})
    assert premiere.status_code == 200, premiere.text

    seconde = _appeler_ecriture(
        parametres, "post", chemin_validation, jeton, {"version": premiere.json()["version"]}
    )
    assert seconde.status_code == 409, seconde.text
    assert seconde.json()["erreur"]["code"] == "fiche_arrivee_etat_incompatible"


@pytest.mark.integration
def test_valider_avec_une_VERSION_OBSOLETE_est_refuse(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    jeton = _session(parametres, decor["arrivant_personne"])
    version = _completer(parametres, decor, jeton, "Bonjour")
    reponse = _appeler_ecriture(
        parametres,
        "post",
        CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
        jeton,
        {"version": version + 41},
    )
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_valider_sans_session_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        reponse = client.post(
            CHEMIN_VALIDATION.format(code=decor["code"], appartenance=decor["arrivant"]),
            json={"version": 1},
        )
    assert reponse.status_code == 401, reponse.text
