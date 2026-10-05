"""L'agrégat de l'accueil d'une entité — LOT 8, `T8`, `MVP-L08-US001` (1/2),
`MVP-L08-US006` (1/2).

LE TÉMOIN CENTRAL : CINQ SECTIONS COMPOSÉES, AUCUNE RÈGLE RECOPIÉE

  `test_TEMOIN_les_cinq_sections_sont_composees` pose un décor complet — une
  page de présentation, un cercle, un bureau, un événement à venir, une
  arrivée récente, deux liens internes — et vérifie que chaque section de
  l'agrégat porte EXACTEMENT ce que son propre service rendrait seul. Ce
  n'est pas un test des RÈGLES de chaque section (déjà prouvées par
  `test_framework.py`, `test_lecture_evenements.py`, `test_arrivees_recentes.py`,
  `test_liens_internes.py`, `test_rendu_des_blocs.py`) : c'est un test du
  CÂBLAGE — que `lire_l_accueil` transmet la bonne entité et le bon instant
  aux cinq services, sans en réécrire un seul filtre.

LA PRÉSENTATION ABSENTE EST UN ÉTAT VALIDE

  `test_la_presentation_ABSENTE_rend_None` prouve que l'absence de page
  `HOME`/`presentation` ne fait pas échouer l'agrégat : les quatre autres
  sections restent composées normalement.

L'ISOLATION ENTRE ENTITÉS

  `test_une_entite_ne_recoit_jamais_les_donnees_d_une_autre` pose deux
  entités avec des données distinctes et vérifie qu'aucune ne fuit dans
  l'accueil de l'autre — le même risque que n'importe quelle des cinq
  sources, mais ici à travers les CINQ en même temps.
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

from app.accueil.lecture import lire_l_accueil
from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN = "/api/v1/entities/{code}/accueil"
ANCRAGE = dt.datetime(2026, 10, 1, 12, 0, tzinfo=dt.UTC)
MARQUEUR = "L8T8"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _entite(cx: Connection, suffixe: str) -> tuple[uuid.UUID, str]:
    code = f"{MARQUEUR}-{suffixe}-{uuid.uuid4().hex[:8]}"
    identifiant = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()
    return identifiant, code


def _page_de_presentation(cx: Connection, entite: uuid.UUID, titre: str) -> None:
    page = cx.execute(
        text(
            "INSERT INTO content_page (entity_id, page_type, title, slug, state, "
            "published_at) VALUES (:e, 'HOME', :titre, 'presentation', 'published', now()) "
            "RETURNING id"
        ),
        {"e": entite, "titre": titre},
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO content_block (entity_id, content_page_id, block_type, "
            "display_order, payload_json) VALUES (:e, :p, 'TITLE', 0, "
            "CAST(:charge AS jsonb))"
        ),
        {"e": entite, "p": page, "charge": '{"texte": "Bienvenue"}'},
    )


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 0) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 0) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _evenement(cx: Connection, entite: uuid.UUID, titre: str, *, debut: dt.datetime) -> None:
    cx.execute(
        text(
            "INSERT INTO event (entity_id, title, starts_at, ends_at, state) "
            "VALUES (:e, :titre, :debut, :fin, 'published')"
        ),
        {"e": entite, "titre": titre, "debut": debut, "fin": debut + dt.timedelta(hours=1)},
    )


def _arrivee_recente(cx: Connection, entite: uuid.UUID, suffixe: str) -> None:
    personne = cx.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, "
            "account_state) VALUES (:a, :a, 'Arrivee', :s, 'active') RETURNING id"
        ),
        {"a": f"{MARQUEUR.lower()}-{suffixe}-{uuid.uuid4().hex[:8]}@exemple.test", "s": suffixe},
    ).scalar_one()
    appartenance = cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'published') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": ANCRAGE.date() - dt.timedelta(days=5)},
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO arrival_profile (entity_id, entity_membership_id, state, "
            "short_intro, published_at, recent_until) "
            "VALUES (:e, :m, 'published', 'Bonjour', now(), :jusqua)"
        ),
        {"e": entite, "m": appartenance, "jusqua": ANCRAGE.date() + dt.timedelta(days=25)},
    )


def _lien(cx: Connection, entite: uuid.UUID, libelle: str, url: str, rang: int) -> None:
    cx.execute(
        text(
            "INSERT INTO internal_link (entity_id, label, url, link_type, display_order) "
            "VALUES (:e, :libelle, :url, 'OTHER', :rang)"
        ),
        {"e": entite, "libelle": libelle, "url": url, "rang": rang},
    )


@pytest.mark.integration
def test_TEMOIN_les_cinq_sections_sont_composees(cx: Connection) -> None:
    entite, code = _entite(cx, "COMPLET")
    _page_de_presentation(cx, entite, "Bordeaux")
    _cercle(cx, entite, "cercle-a")
    _bureau(cx, entite, "bureau-a")
    _evenement(cx, entite, "Soiree", debut=ANCRAGE + dt.timedelta(days=1))
    _arrivee_recente(cx, entite, "nouvel")
    _lien(cx, entite, "Hub", "https://hub.exemple.test/", 0)
    _lien(cx, entite, "Academy", "https://academy.exemple.test/", 1)

    accueil = lire_l_accueil(cx, entite=entite, code_entite=code, instant=ANCRAGE)

    assert accueil.presentation is not None
    assert accueil.presentation.titre == "Bordeaux"
    assert accueil.presentation.nombre_de_blocs == 1

    assert [c.code for c in accueil.framework.cercles] == ["cercle-a"]
    assert [b.code for b in accueil.framework.bureaux] == ["bureau-a"]

    assert [e.title for e in accueil.evenements_a_venir.evenements] == ["Soiree"]
    assert accueil.evenements_a_venir.total == 1

    assert [a.last_name for a in accueil.arrivees_recentes.arrivees] == ["nouvel"]
    assert accueil.arrivees_recentes.total == 1

    assert [lien.libelle for lien in accueil.liens_internes] == ["Hub", "Academy"]


@pytest.mark.integration
def test_la_presentation_ABSENTE_rend_None(cx: Connection) -> None:
    entite, code = _entite(cx, "SANSPAGE")
    accueil = lire_l_accueil(cx, entite=entite, code_entite=code, instant=ANCRAGE)
    assert accueil.presentation is None
    #  Les quatre autres sections restent composees, meme vides.
    assert accueil.framework.cercles == ()
    assert accueil.evenements_a_venir.evenements == []
    assert accueil.arrivees_recentes.arrivees == []
    assert accueil.liens_internes == ()


@pytest.mark.integration
def test_une_entite_ne_recoit_jamais_les_donnees_d_une_autre(cx: Connection) -> None:
    ici, code_ici = _entite(cx, "ICI")
    ailleurs, _ = _entite(cx, "AILLEURS")
    _page_de_presentation(cx, ailleurs, "Etranger")
    _cercle(cx, ailleurs, "cercle-etranger")
    _evenement(cx, ailleurs, "Etranger", debut=ANCRAGE + dt.timedelta(days=1))
    _arrivee_recente(cx, ailleurs, "etranger")
    _lien(cx, ailleurs, "Etranger", "https://etranger.exemple.test/", 0)

    accueil = lire_l_accueil(cx, entite=ici, code_entite=code_ici, instant=ANCRAGE)

    assert accueil.presentation is None
    assert accueil.framework.cercles == ()
    assert accueil.evenements_a_venir.evenements == []
    assert accueil.arrivees_recentes.arrivees == []
    assert accueil.liens_internes == ()


# ============================================================================
#  La route HTTP
# ============================================================================


@pytest.fixture
def decor_http(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"l8t8{uuid.uuid4().hex[:10]}"
    code = f"{marqueur}-e"
    maintenant = dt.datetime.now(tz=dt.UTC)
    adresse = f"{marqueur}@exemple.test"

    with moteur(parametres).begin() as cx_http:
        entite = cx_http.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, "
                "timezone, activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', "
                "'Europe/Paris', now()) RETURNING id"
            ),
            {"code": code, "nom": marqueur, "ville": marqueur},
        ).scalar_one()
        personne = cx_http.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "account_state) VALUES (:a, :a, 'Lecture', 'Accueil', 'active') RETURNING id"
            ),
            {"a": adresse},
        ).scalar_one()
        _page_de_presentation(cx_http, entite, code)
        _lien(cx_http, entite, "Hub", "https://hub.exemple.test/", 0)
        jeton, _ = ouvrir_une_session(
            cx_http,
            personne=personne,
            instant=maintenant,
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )

    try:
        yield parametres, code, jeton
    finally:
        with moteur(parametres).begin() as menage:
            menage.execute(
                text(
                    "DELETE FROM user_session WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized = :a)"
                ),
                {"a": adresse},
            )
            menage.execute(
                text(
                    "DELETE FROM content_block WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(
                text(
                    "DELETE FROM content_page WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(
                text(
                    "DELETE FROM internal_link WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(text("DELETE FROM person WHERE email_normalized = :a"), {"a": adresse})
            menage.execute(text("DELETE FROM entity WHERE code = :c"), {"c": code})


def _appeler(parametres: Parametres, code: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN.format(code=code))


@pytest.mark.integration
def test_la_route_exige_une_session(decor_http: tuple[Parametres, str, str]) -> None:
    parametres, code, _ = decor_http
    assert _appeler(parametres, code, None).status_code == 401


@pytest.mark.integration
def test_entite_inconnue_rend_404(decor_http: tuple[Parametres, str, str]) -> None:
    parametres, _, jeton = decor_http
    assert _appeler(parametres, "inconnue-partout", jeton).status_code == 404


@pytest.mark.integration
def test_TEMOIN_les_cinq_cles_sont_servies_par_HTTP(
    decor_http: tuple[Parametres, str, str],
) -> None:
    parametres, code, jeton = decor_http
    reponse = _appeler(parametres, code, jeton)
    assert reponse.status_code == 200, reponse.text
    charge = reponse.json()
    assert set(charge) == {
        "presentation",
        "framework",
        "arrivees_recentes",
        "evenements_a_venir",
        "liens_internes",
    }
    assert charge["presentation"]["titre"] == code
    assert charge["liens_internes"]["nombre_de_liens"] == 1
    assert charge["liens_internes"]["liens"][0]["libelle"] == "Hub"
    assert set(charge["framework"]) == {"responsabilites", "cercles", "bureaux"}
    assert set(charge["arrivees_recentes"]) == {"arrivees", "page", "taille", "total", "pages"}
    assert set(charge["evenements_a_venir"]) == {
        "classement",
        "evenements",
        "page",
        "taille",
        "total",
        "pages",
    }
