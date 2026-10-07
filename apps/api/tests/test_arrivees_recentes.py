"""Les arrivees recentes de l'accueil — LOT 8, `T7`, `MVP-L08-US002`.

LE TEMOIN CENTRAL : LA FENETRE EST `[published_at, recent_until]`, PAS
`[arrival_date, recent_until]`

  §10.5 : « La fiche peut etre publiee […] y compris avant la date d'arrivee »
  et le backlog : « Une fiche validee apparait IMMEDIATEMENT ». Une fiche
  publiee pour un membre encore `future` (arrivee a venir) doit donc deja
  apparaitre — c'est pourquoi ce module filtre sur `ETATS_OCCUPANTS`
  (future ET active), jamais `ETAT_LISTE` (active seul) du trombinoscope.

LE SECOND TEMOIN CENTRAL : LA FRONTIERE `recent_until`, ANCRE CONTROLEE

  `recent_until` est une colonne DATE ecrite une fois a la publication (LOT 7,
  `T3`). `test_TEMOIN_la_frontiere_exacte_de_recent_until` pose DEUX fiches
  dont seule la date differe d'un jour et prouve que l'ancre — jamais une
  horloge mockee — les depart.

CE QUE LA REPONSE NE PORTE PAS, ET POURQUOI C'EST UN TEST ET NON UN
COMMENTAIRE

  Ni metier, ni statut, ni cercle, ni photo : la matrice §5 donne « Arrivees
  recentes » en Lecture aux HUIT roles, y compris DSM, qui est a TIRET sur
  « Consulter les informations preremplies ». Un test fige l'ABSENCE de ces
  champs (§7.32) : si un lot ulterieur veut les exposer, il devra casser ce
  test, donc le decider explicitement plutot que de les ajouter en silence.
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
from app.main import creer_application
from app.onboarding.arrivees_recentes import lister_les_arrivees_recentes
from app.onboarding.routes import ArriveeRecenteRendue
from app.shared.database import moteur
from app.shared.pagination import TAILLE_PAR_DEFAUT

ORIGINE_DE_TEST = "https://testserver"
CHEMIN = "/api/v1/entities/{code}/arrivees-recentes"
ANCRAGE = dt.datetime(2026, 10, 1, 12, 0, tzinfo=dt.UTC)
ARRIVEE_PASSEE = dt.date(2026, 9, 1)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================


def test_la_reponse_ne_porte_NI_metier_NI_statut_NI_cercle_NI_photo() -> None:
    """§6.5 : la matrice refuse DSM sur les informations preremplies ailleurs —
    les exposer ici serait une porte derobee vers un droit refuse."""
    assert set(ArriveeRecenteRendue.model_fields) == {
        "appartenance",
        "person_id",
        "first_name",
        "last_name",
        "preferred_name",
        "arrival_date",
        "short_intro",
        "fun_fact",
    }


def test_le_service_refuse_une_page_inferieure_a_un() -> None:
    with pytest.raises(ValueError, match="page"):
        lister_les_arrivees_recentes(
            None,  # type: ignore[arg-type]
            entite=uuid.uuid4(),
            page=0,
            taille=25,
            instant=ANCRAGE,
        )


def test_le_service_refuse_une_taille_hors_du_cahier_18_2() -> None:
    with pytest.raises(ValueError, match="taille"):
        lister_les_arrivees_recentes(
            None,  # type: ignore[arg-type]
            entite=uuid.uuid4(),
            page=1,
            taille=26,
            instant=ANCRAGE,
        )


# ============================================================================
#  2. Le service, sur une vraie connexion
# ============================================================================


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _entite(cx: Connection, suffixe: str) -> uuid.UUID:
    code = f"L8T7-{suffixe}-{uuid.uuid4().hex[:8]}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"l8t7-{suffixe}-{uuid.uuid4().hex[:8]}@exemple.test"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :a, 'Arrivee', :suffixe, 'active') RETURNING id"
        ),
        {"a": adresse, "suffixe": suffixe},
    ).scalar_one()


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    arrivee: dt.date,
    etat: str = "active",
    visibilite: str = "published",
) -> uuid.UUID:
    #  `departed` exige une `departure_date` — contrainte posee au LOT 2,
    #  `ck_entity_membership_depart_date_si_departed`.
    depart = arrivee + dt.timedelta(days=1) if etat == "departed" else None
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "departure_date, membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, :etat, 'consultant', :visibilite) RETURNING id"
        ),
        {
            "p": personne,
            "e": entite,
            "arrivee": arrivee,
            "depart": depart,
            "etat": etat,
            "visibilite": visibilite,
        },
    ).scalar_one()


def _fiche(
    cx: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    *,
    etat: str = "published",
    recent_until: dt.date,
    short_intro: str | None = "Bonjour a tous",
    fun_fact: str | None = "Aime le velo",
) -> None:
    cx.execute(
        text(
            "INSERT INTO arrival_profile (entity_id, entity_membership_id, state, "
            "short_intro, fun_fact, validated_at, published_at, recent_until) "
            "VALUES (:e, :m, :etat, :intro, :fun, :instant, :instant, :jusqua)"
        ),
        {
            "e": entite,
            "m": appartenance,
            "etat": etat,
            "intro": short_intro,
            "fun": fun_fact,
            "instant": ANCRAGE,
            "jusqua": recent_until,
        },
    )


def _arrivant(
    cx: Connection,
    entite: uuid.UUID,
    suffixe: str,
    *,
    arrivee: dt.date = ARRIVEE_PASSEE,
    membership_state: str = "active",
    profile_visibility: str = "published",
    fiche_state: str = "published",
    recent_until: dt.date,
) -> uuid.UUID:
    """Une personne, son appartenance et sa fiche d'arrivee, en un seul appel."""
    personne = _personne(cx, suffixe)
    appartenance = _appartenance(
        cx, entite, personne, arrivee=arrivee, etat=membership_state, visibilite=profile_visibility
    )
    _fiche(cx, entite, appartenance, etat=fiche_state, recent_until=recent_until)
    return appartenance


@pytest.mark.integration
def test_TEMOIN_une_fiche_publiee_AVANT_l_arrivee_apparait_immediatement(cx: Connection) -> None:
    """`future` — publiee par anticipation, et DEJA visible. §10.5, §7.1."""
    entite = _entite(cx, "FUTUR")
    arrivee = ANCRAGE.date() + dt.timedelta(days=10)
    _arrivant(
        cx,
        entite,
        "futur",
        arrivee=arrivee,
        membership_state="future",
        recent_until=arrivee + dt.timedelta(days=30),
    )
    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert [a.last_name for a in resultat.arrivees] == ["futur"]


@pytest.mark.integration
def test_TEMOIN_la_frontiere_exacte_de_recent_until(cx: Connection) -> None:
    """ANCRE CONTROLEE : la meme fiche, un jour de plus ou de moins sur
    `recent_until`, et rien d'autre — pas une horloge mockee."""
    entite = _entite(cx, "BORNE")
    _arrivant(cx, entite, "encore-visible", recent_until=ANCRAGE.date())
    _arrivant(cx, entite, "deja-parti", recent_until=ANCRAGE.date() - dt.timedelta(days=1))

    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert [a.last_name for a in resultat.arrivees] == ["encore-visible"]


@pytest.mark.integration
@pytest.mark.parametrize("etat", ["draft", "validated", "archived"])
def test_une_fiche_NON_PUBLIEE_n_apparait_pas(cx: Connection, etat: str) -> None:
    entite = _entite(cx, f"ETAT-{etat}")
    _arrivant(cx, entite, "x", fiche_state=etat, recent_until=ANCRAGE.date() + dt.timedelta(days=5))
    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert resultat.arrivees == []
    assert resultat.total == 0


@pytest.mark.integration
@pytest.mark.parametrize("visibilite", ["draft", "hidden"])
def test_un_profil_NON_LISTE_n_apparait_pas(cx: Connection, visibilite: str) -> None:
    """Meme discipline que le trombinoscope : `published` seul est public."""
    entite = _entite(cx, f"VIS-{visibilite}")
    _arrivant(
        cx,
        entite,
        "x",
        profile_visibility=visibilite,
        recent_until=ANCRAGE.date() + dt.timedelta(days=5),
    )
    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert resultat.arrivees == []


@pytest.mark.integration
@pytest.mark.parametrize("etat", ["departed", "archived"])
def test_une_appartenance_NON_OCCUPANTE_n_apparait_pas(cx: Connection, etat: str) -> None:
    entite = _entite(cx, f"MBR-{etat}")
    _arrivant(
        cx,
        entite,
        "x",
        membership_state=etat,
        recent_until=ANCRAGE.date() + dt.timedelta(days=5),
    )
    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert resultat.arrivees == []


@pytest.mark.integration
def test_une_entite_ne_recoit_jamais_l_arrivee_d_une_autre(cx: Connection) -> None:
    ici = _entite(cx, "ICI")
    ailleurs = _entite(cx, "AILLEURS")
    _arrivant(cx, ailleurs, "secret", recent_until=ANCRAGE.date() + dt.timedelta(days=5))
    resultat = lister_les_arrivees_recentes(cx, entite=ici, page=1, taille=25, instant=ANCRAGE)
    assert resultat.arrivees == []
    assert resultat.total == 0


@pytest.mark.integration
def test_l_ordre_est_la_date_d_arrivee_la_plus_RECENTE_d_abord(cx: Connection) -> None:
    entite = _entite(cx, "ORDRE")
    _arrivant(
        cx,
        entite,
        "ancien",
        arrivee=ANCRAGE.date() - dt.timedelta(days=20),
        recent_until=ANCRAGE.date() + dt.timedelta(days=5),
    )
    _arrivant(
        cx,
        entite,
        "recent",
        arrivee=ANCRAGE.date() - dt.timedelta(days=1),
        recent_until=ANCRAGE.date() + dt.timedelta(days=5),
    )
    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert [a.last_name for a in resultat.arrivees] == ["recent", "ancien"]


@pytest.mark.integration
def test_le_total_porte_la_POPULATION_et_pas_la_page(cx: Connection) -> None:
    entite = _entite(cx, "PAGE")
    for suffixe in ("a", "b", "c"):
        _arrivant(cx, entite, suffixe, recent_until=ANCRAGE.date() + dt.timedelta(days=5))
    resultat = lister_les_arrivees_recentes(cx, entite=entite, page=1, taille=25, instant=ANCRAGE)
    assert resultat.total == 3
    assert len(resultat.arrivees) == 3


# ============================================================================
#  3. La route HTTP, montage et refus
# ============================================================================


@pytest.fixture
def decor_http(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str]]:
    """Donnees commises, car l'API ouvre sa propre connexion PostgreSQL."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"l8t7{uuid.uuid4().hex[:10]}"
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
                "account_state) VALUES (:a, :a, 'Lecture', 'Arrivees', 'active') RETURNING id"
            ),
            {"a": adresse},
        ).scalar_one()
        appartenance = _appartenance(
            cx_http, entite, personne, arrivee=maintenant.date() - dt.timedelta(days=5)
        )
        _fiche(
            cx_http,
            entite,
            appartenance,
            recent_until=maintenant.date() + dt.timedelta(days=25),
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
                    "DELETE FROM arrival_profile WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(
                text(
                    "DELETE FROM entity_membership WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(text("DELETE FROM person WHERE email_normalized = :a"), {"a": adresse})
            menage.execute(text("DELETE FROM entity WHERE code = :c"), {"c": code})


def _appeler(parametres: Parametres, code: str, jeton: str | None, requete: str = "") -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN.format(code=code) + requete)


@pytest.mark.integration
def test_la_route_exige_une_session(decor_http: tuple[Parametres, str, str]) -> None:
    parametres, code, _ = decor_http
    assert _appeler(parametres, code, None).status_code == 401


@pytest.mark.integration
def test_TEMOIN_un_EMP_sans_appartenance_lit_une_autre_entite(
    decor_http: tuple[Parametres, str, str],
) -> None:
    """Matrice §5 : lecture pour les huit roles, y compris hors entite principale."""
    parametres, code, jeton = decor_http
    reponse = _appeler(parametres, code, jeton)
    assert reponse.status_code == 200, reponse.text
    charge = reponse.json()
    assert set(charge) == {"arrivees", "page", "taille", "total", "pages"}
    assert charge["page"] == 1
    assert charge["taille"] == TAILLE_PAR_DEFAUT
    assert charge["total"] == charge["pages"] == 1
    assert set(charge["arrivees"][0]) == {
        "appartenance",
        "person_id",
        "first_name",
        "last_name",
        "preferred_name",
        "arrival_date",
        "short_intro",
        "fun_fact",
    }


@pytest.mark.integration
@pytest.mark.parametrize("requete", ["?taille=26", "?page=0"])
def test_les_parametres_invalides_rendent_422(
    decor_http: tuple[Parametres, str, str], requete: str
) -> None:
    parametres, code, jeton = decor_http
    assert _appeler(parametres, code, jeton, requete).status_code == 422


@pytest.mark.integration
def test_entite_inconnue_rend_404(decor_http: tuple[Parametres, str, str]) -> None:
    parametres, _, jeton = decor_http
    assert _appeler(parametres, "inconnue-partout", jeton).status_code == 404
