"""Lecture a venir/passee des evenements — LOT 8, `T2`, `MVP-L08-US003`.

Le temoin central pose trois evenements dont un finit exactement a l'ancre :
``ends_at <= instant`` est passe, ``ends_at > instant`` est a venir. Brouillons
et archives sont absents ; l'annule reste visible et porte son etat.
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

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.events.lecture import ClassementEvenement, lister_les_evenements
from app.main import creer_application
from app.shared.database import moteur
from app.shared.pagination import TAILLE_PAR_DEFAUT

ORIGINE_DE_TEST = "https://testserver"
CHEMIN = "/api/v1/entities/{code}/events"
ANCRAGE = dt.datetime(2026, 10, 1, 12, 0, tzinfo=dt.UTC)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


def test_les_deux_classements_sont_des_valeurs_de_requete_pas_des_etats() -> None:
    assert {membre.value for membre in ClassementEvenement} == {"a_venir", "passes"}


def test_le_service_refuse_une_page_inferieure_a_un() -> None:
    with pytest.raises(ValueError, match="page"):
        lister_les_evenements(
            None,  # type: ignore[arg-type]
            entite=uuid.uuid4(),
            classement=ClassementEvenement.A_VENIR,
            page=0,
            taille=25,
            instant=ANCRAGE,
        )


def test_le_service_refuse_une_taille_hors_du_cahier_18_2() -> None:
    with pytest.raises(ValueError, match="taille"):
        lister_les_evenements(
            None,  # type: ignore[arg-type]
            entite=uuid.uuid4(),
            classement=ClassementEvenement.PASSES,
            page=1,
            taille=26,
            instant=ANCRAGE,
        )


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
    code = f"L8T2-{suffixe}-{uuid.uuid4().hex[:8]}"
    identifiant = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()
    return identifiant, code


def _evenement(
    cx: Connection,
    entite: uuid.UUID,
    titre: str,
    *,
    debut: dt.datetime,
    fin: dt.datetime,
    etat: str = "published",
    archive_le: dt.datetime | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO event (entity_id, title, description, starts_at, ends_at, "
            "location_text, state, cancelled_at, cancellation_reason, archived_at) "
            "VALUES (:entite, :titre, :description, :debut, :fin, :lieu, :etat, "
            ":annule_le, :motif_d_annulation, :archive) "
            "RETURNING id"
        ),
        {
            "entite": entite,
            "titre": titre,
            "description": f"Description {titre}",
            "debut": debut,
            "fin": fin,
            "lieu": "Bordeaux",
            "etat": etat,
            "annule_le": debut if etat == "cancelled" else None,
            "motif_d_annulation": "Indisponibilite" if etat == "cancelled" else None,
            "archive": archive_le,
        },
    ).scalar_one()


@pytest.mark.integration
def test_TEMOIN_la_frontiere_exacte_classe_une_fin_egale_dans_les_passes(
    cx: Connection,
) -> None:
    entite, _ = _entite(cx, "BORNE")
    _evenement(
        cx,
        entite,
        "Fini avant",
        debut=ANCRAGE - dt.timedelta(hours=2),
        fin=ANCRAGE - dt.timedelta(seconds=1),
    )
    _evenement(
        cx,
        entite,
        "Fini a la borne",
        debut=ANCRAGE - dt.timedelta(hours=1),
        fin=ANCRAGE,
    )
    _evenement(
        cx,
        entite,
        "En cours",
        debut=ANCRAGE - dt.timedelta(minutes=30),
        fin=ANCRAGE + dt.timedelta(minutes=30),
    )

    passes = lister_les_evenements(
        cx,
        entite=entite,
        classement=ClassementEvenement.PASSES,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )
    a_venir = lister_les_evenements(
        cx,
        entite=entite,
        classement=ClassementEvenement.A_VENIR,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )

    assert [e.title for e in passes.evenements] == ["Fini a la borne", "Fini avant"]
    assert [e.title for e in a_venir.evenements] == ["En cours"]
    assert passes.total + a_venir.total == 3


@pytest.mark.integration
def test_un_evenement_annule_reste_visible_avec_son_motif(cx: Connection) -> None:
    entite, _ = _entite(cx, "ANNULE")
    _evenement(
        cx,
        entite,
        "Annule",
        debut=ANCRAGE + dt.timedelta(days=1),
        fin=ANCRAGE + dt.timedelta(days=1, hours=1),
        etat="cancelled",
    )
    resultat = lister_les_evenements(
        cx,
        entite=entite,
        classement=ClassementEvenement.A_VENIR,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )
    assert [(e.title, e.state, e.cancellation_reason) for e in resultat.evenements] == [
        ("Annule", "cancelled", "Indisponibilite")
    ]


@pytest.mark.integration
def test_brouillon_et_archive_sont_absents_de_la_lecture_generale(cx: Connection) -> None:
    entite, _ = _entite(cx, "ETATS")
    for titre, etat, archive_le in (
        ("Publie", "published", None),
        ("Brouillon", "draft", None),
        ("Archive par etat", "archived", ANCRAGE),
        ("Archive par colonne", "published", ANCRAGE),
    ):
        _evenement(
            cx,
            entite,
            titre,
            debut=ANCRAGE + dt.timedelta(days=1),
            fin=ANCRAGE + dt.timedelta(days=1, hours=1),
            etat=etat,
            archive_le=archive_le,
        )
    resultat = lister_les_evenements(
        cx,
        entite=entite,
        classement=ClassementEvenement.A_VENIR,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )
    assert [e.title for e in resultat.evenements] == ["Publie"]


@pytest.mark.integration
def test_une_entite_ne_recoit_jamais_l_evenement_d_une_autre(cx: Connection) -> None:
    ici, _ = _entite(cx, "ICI")
    ailleurs, _ = _entite(cx, "AILLEURS")
    _evenement(
        cx,
        ailleurs,
        "Secret d ailleurs",
        debut=ANCRAGE + dt.timedelta(days=1),
        fin=ANCRAGE + dt.timedelta(days=1, hours=1),
    )
    resultat = lister_les_evenements(
        cx,
        entite=ici,
        classement=ClassementEvenement.A_VENIR,
        page=1,
        taille=25,
        instant=ANCRAGE,
    )
    assert resultat.evenements == []
    assert resultat.total == 0


@pytest.fixture
def decor_http(
    parametres_de_la_stack: Parametres,
) -> Iterator[tuple[Parametres, str, str]]:
    """Donnees commises, car l'API ouvre sa propre connexion PostgreSQL."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"l8t2{uuid.uuid4().hex[:10]}"
    code = f"{marqueur}-e"
    maintenant = dt.datetime.now(tz=dt.UTC)
    adresse = f"{marqueur}@exemple.test"

    with moteur(parametres).begin() as cx_http:
        entite = cx_http.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
                "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', "
                "now()) RETURNING id"
            ),
            {"code": code, "nom": marqueur, "ville": marqueur},
        ).scalar_one()
        personne = cx_http.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "account_state) VALUES (:a, :a, 'Lecture', 'Evenements', 'active') RETURNING id"
            ),
            {"a": adresse},
        ).scalar_one()
        _evenement(
            cx_http,
            entite,
            "A venir via HTTP",
            debut=maintenant + dt.timedelta(days=1),
            fin=maintenant + dt.timedelta(days=1, hours=1),
        )
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
                    "DELETE FROM event WHERE entity_id IN (SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(text("DELETE FROM person WHERE email_normalized = :a"), {"a": adresse})
            menage.execute(text("DELETE FROM entity WHERE code = :c"), {"c": code})


def _appeler(
    parametres: Parametres,
    code: str,
    jeton: str | None,
    requete: str,
) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN.format(code=code) + requete)


@pytest.mark.integration
def test_la_route_exige_une_session(decor_http: tuple[Parametres, str, str]) -> None:
    parametres, code, _ = decor_http
    assert _appeler(parametres, code, None, "?classement=a_venir").status_code == 401


@pytest.mark.integration
def test_TEMOIN_un_EMP_sans_appartenance_lit_une_autre_entite(
    decor_http: tuple[Parametres, str, str],
) -> None:
    """Matrice §5/§11 : lecture pour EMP, y compris hors entite principale."""
    parametres, code, jeton = decor_http
    reponse = _appeler(parametres, code, jeton, "?classement=a_venir&taille=25")
    assert reponse.status_code == 200, reponse.text
    charge = reponse.json()
    assert set(charge) == {"classement", "evenements", "page", "taille", "total", "pages"}
    assert charge["classement"] == "a_venir"
    assert charge["page"] == 1
    assert charge["taille"] == TAILLE_PAR_DEFAUT
    assert charge["total"] == charge["pages"] == 1
    assert set(charge["evenements"][0]) == {
        "identifiant",
        "titre",
        "description",
        "commence_le",
        "finit_le",
        "lieu",
        "etat",
        "annule_le",
        "motif_d_annulation",
    }


@pytest.mark.integration
@pytest.mark.parametrize("requete", ["", "?classement=invente", "?classement=passes&taille=26"])
def test_les_parametres_invalides_rendent_422(
    decor_http: tuple[Parametres, str, str], requete: str
) -> None:
    parametres, code, jeton = decor_http
    assert _appeler(parametres, code, jeton, requete).status_code == 422
