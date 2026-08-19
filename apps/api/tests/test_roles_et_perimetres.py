"""Contraintes de roles et de perimetres — modele §6.5, §8.2, §8.4, §25.4.

LOT 2, sous-etape `T10`, story `MVP-L02-US005`.

DEUX DES TROIS CRITERES DE `US005` ETAIENT DEJA ACQUIS, et le verifier avant de
refaire etait la premiere chose a faire :

  « un seul Booster actif par cercle »            `T8`, index partiel du §25.1
  « aucune responsabilite active dans plusieurs   `T8`, declencheur
    entites »                                     `booster_une_seule_entite`
  « DG implique DSM local »                       ici

ET UN TEST PORTE SUR UNE NON-ACTION, comme en `T6` pour les alias : « le Booster
d'un cercle secondaire ne modifie pas le cercle principal, le DSM, le client ou le
statut » (§8.2). Une regle de non-effet ne se prouve qu'en montrant que RIEN n'a
change.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.shared.database import moteur

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
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


def _entite(connexion: Connection, code: str = "BORDEAUX") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"a": adresse, "b": adresse},
    ).scalar_one()


def _responsabilite(
    connexion: Connection, entite: uuid.UUID, personne: uuid.UUID, type_: str = "DSM"
) -> None:
    connexion.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :p, :debut)"
        ),
        {"p": personne, "e": entite, "t": type_, "debut": JANVIER},
    )


def _appartenance(
    connexion: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    categorie: str = "consultant",
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', :cat, 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "cat": categorie},
    ).scalar_one()


# ----------------------------------------------------------------------------
#  « DG implique DSM local » — l'IMPLICATION, appliquee defensivement
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_une_categorie_dg_SANS_responsabilite_DSM_est_refusee(cx: Connection) -> None:
    """Critere de `US005` : « DG implique DSM local ».

    **LE MODELE DECRIT UNE ACTION, LE BACKLOG UNE IMPLICATION**, et seule la
    seconde est applicable par la base. Le §8.4 ecrit « un DG recoit
    AUTOMATIQUEMENT une responsabilite DSM dans la meme transaction » -- or
    `assigned_by_person_id` est `NOT NULL` et un declencheur ne sait pas QUI
    attribue. Inventer un attributeur fabriquerait une trace d'audit fausse, ce
    qui est pire qu'une trace absente.

    L'implication, elle, se verifie. La creation automatique reste au service, en
    `T11` ou au LOT 3, et elle satisfera cet invariant plutot que de s'y
    substituer.
    """
    entite = _entite(cx)
    with pytest.raises(IntegrityError) as echec:
        _appartenance(cx, entite, _personne(cx, "dg@exalt.com"), categorie="dg")
    assert "une categorie dg exige une responsabilite DSM active" in str(echec.value)


@pytest.mark.integration
def test_une_categorie_dg_AVEC_responsabilite_DSM_est_acceptee(cx: Connection) -> None:
    """Temoin du precedent."""
    entite = _entite(cx)
    personne = _personne(cx, "dg@exalt.com")
    _responsabilite(cx, entite, personne, "DSM")
    _appartenance(cx, entite, personne, categorie="dg")
    categorie = cx.execute(text("SELECT professional_category FROM entity_membership")).scalar_one()
    assert categorie == "dg"


@pytest.mark.integration
def test_une_responsabilite_DSM_dans_une_AUTRE_entite_ne_suffit_PAS(cx: Connection) -> None:
    """« DSM **LOCAL** » : le mot local n'est pas decoratif."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    personne = _personne(cx, "dg@exalt.com")
    _responsabilite(cx, lille, personne, "DSM")
    with pytest.raises(IntegrityError) as echec:
        _appartenance(cx, bordeaux, personne, categorie="dg")
    assert "une categorie dg exige une responsabilite DSM active" in str(echec.value)


@pytest.mark.integration
def test_une_categorie_consultant_n_exige_AUCUNE_responsabilite(cx: Connection) -> None:
    """Second temoin : le declencheur ne s'applique qu'a `dg`."""
    entite = _entite(cx)
    _appartenance(cx, entite, _personne(cx, "consultant@exalt.com"), categorie="consultant")
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 1


@pytest.mark.integration
def test_un_ESM_ne_suffit_PAS_a_justifier_un_dg(cx: Connection) -> None:
    """Troisieme temoin : c'est bien la responsabilite `DSM` qui est exigee.

    Sans lui, un declencheur qui se contenterait de « une responsabilite
    quelconque » passerait.
    """
    entite = _entite(cx)
    personne = _personne(cx, "dg@exalt.com")
    _responsabilite(cx, entite, personne, "ESM")
    with pytest.raises(IntegrityError) as echec:
        _appartenance(cx, entite, personne, categorie="dg")
    assert "une categorie dg exige une responsabilite DSM active" in str(echec.value)


# ----------------------------------------------------------------------------
#  §6.5 : « `mission` exige un client ACTIF POUR L'ENTITE »
# ----------------------------------------------------------------------------


def _client(connexion: Connection, nom: str | None = None) -> uuid.UUID:
    canonique = nom or f"client {uuid.uuid4().hex[:8]}"
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:nom, :affiche, 'active') RETURNING id"
        ),
        {"nom": canonique, "affiche": canonique.title()},
    ).scalar_one()


def _situation_mission(
    connexion: Connection, entite: uuid.UUID, appartenance: uuid.UUID, client: uuid.UUID
) -> None:
    connexion.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, client_id, starts_at) VALUES (:e, :a, 'mission', :c, :debut)"
        ),
        {"e": entite, "a": appartenance, "c": client, "debut": JANVIER},
    )


@pytest.mark.integration
def test_une_mission_avec_un_client_NON_ACTIVE_est_refusee(cx: Connection) -> None:
    """§6.5, notee en `T5` puis `T6`, appliquee ici.

    Le client existe GLOBALEMENT mais n'est pas active dans l'entite : aucune
    ligne de `entity_client`. C'est precisement ce que « actif POUR L'ENTITE »
    exige.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, _personne(cx, "c@exalt.com"))
    with pytest.raises(IntegrityError) as echec:
        _situation_mission(cx, entite, appartenance, _client(cx))
    assert "une mission exige un client active dans cette entite" in str(echec.value)


@pytest.mark.integration
def test_une_mission_avec_un_client_ACTIVE_est_acceptee(cx: Connection) -> None:
    """Temoin du precedent."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, _personne(cx, "c@exalt.com"))
    client = _client(cx)
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    _situation_mission(cx, entite, appartenance, client)
    assert cx.execute(text("SELECT count(*) FROM professional_status_assignment")).scalar_one() == 1


@pytest.mark.integration
def test_une_activation_ARCHIVEE_localement_ne_suffit_PAS(cx: Connection) -> None:
    """§7.2 : « archiver LOCALEMENT une relation ». Une activation archivee n'est plus active.

    C'est le cas qui distingue « le client est connu de l'entite » de « le client
    est ACTIF pour l'entite ».
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, _personne(cx, "c@exalt.com"))
    client = _client(cx)
    cx.execute(
        text(
            "INSERT INTO entity_client (entity_id, client_id, archived_at) VALUES (:e, :c, now())"
        ),
        {"e": entite, "c": client},
    )
    with pytest.raises(IntegrityError) as echec:
        _situation_mission(cx, entite, appartenance, client)
    assert "une mission exige un client active dans cette entite" in str(echec.value)


@pytest.mark.integration
def test_une_activation_dans_une_AUTRE_entite_ne_suffit_PAS(cx: Connection) -> None:
    """« POUR L'ENTITE » : le client doit etre active dans CELLE de l'appartenance."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance = _appartenance(cx, bordeaux, _personne(cx, "c@exalt.com"))
    client = _client(cx)
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": lille, "c": client},
    )
    with pytest.raises(IntegrityError) as echec:
        _situation_mission(cx, bordeaux, appartenance, client)
    assert "une mission exige un client active dans cette entite" in str(echec.value)


@pytest.mark.integration
def test_un_intercontract_reste_accepte_sans_client(cx: Connection) -> None:
    """Le pendant du §6.5 etait deja acquis en `T5`.

    « `intercontract` interdit un client actif » : la contrainte
    `client_selon_le_statut` impose `client_id IS NULL`, et une absence de client
    est a fortiori une absence de client actif. Le declencheur ne se reveille pas.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, _personne(cx, "c@exalt.com"))
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, starts_at) VALUES (:e, :a, 'intercontract', :debut)"
        ),
        {"e": entite, "a": appartenance, "debut": JANVIER},
    )
    assert cx.execute(text("SELECT count(*) FROM professional_status_assignment")).scalar_one() == 1


# ----------------------------------------------------------------------------
#  §8.2 : une regle de NON-EFFET
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_cercle_SECONDAIRE_ne_modifie_RIEN_d_autre(cx: Connection) -> None:
    """§8.2 : « le Booster d'un cercle secondaire ne modifie pas le cercle principal,
    le DSM, le client ou le statut de la personne ».

    UNE REGLE DE NON-EFFET, ET ELLE SE PROUVE EN MONTRANT QUE RIEN N'A CHANGE --
    comme en `T6` pour les alias clients. Le test releve l'etat complet des quatre
    relations citees, ajoute un cercle secondaire ET une responsabilite de Booster
    sur ce cercle, puis compare.

    **Aucune contrainte ne l'exprime, et c'est normal** : il n'y a rien a refuser.
    Ce qui pourrait la violer est un SERVICE trop zele, et le seul garde-fou
    possible est un test qui constate l'absence d'effet.
    """
    entite = _entite(cx)
    personne = _personne(cx, "consultant@exalt.com")
    appartenance = _appartenance(cx, entite, personne)

    #  L'etat de depart : un cercle principal, un DSM, une mission avec client.
    principal = cx.execute(
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, 'TECH', 'Tech') RETURNING id"),
        {"e": entite},
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :a, :c, 'principal', :debut)"
        ),
        {"e": entite, "a": appartenance, "c": principal, "debut": JANVIER},
    )
    dsm = _personne(cx, "dsm@exalt.com")
    _responsabilite(cx, entite, dsm, "DSM")
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at) VALUES (:e, :a, :d, :debut)"
        ),
        {"e": entite, "a": appartenance, "d": dsm, "debut": JANVIER},
    )
    client = _client(cx)
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    _situation_mission(cx, entite, appartenance, client)

    def etat() -> tuple[object, ...]:
        principal_actif = cx.execute(
            text(
                "SELECT circle_id FROM circle_membership WHERE entity_membership_id = :a "
                "AND membership_type = 'principal' AND ends_at IS NULL"
            ),
            {"a": appartenance},
        ).scalar_one()
        dsm_actif = cx.execute(
            text(
                "SELECT dsm_person_id FROM dsm_assignment WHERE consultant_membership_id = :a "
                "AND ends_at IS NULL"
            ),
            {"a": appartenance},
        ).scalar_one()
        statut, client_actif = cx.execute(
            text(
                "SELECT status, client_id FROM professional_status_assignment "
                "WHERE entity_membership_id = :a AND ends_at IS NULL"
            ),
            {"a": appartenance},
        ).one()
        return (principal_actif, dsm_actif, statut, client_actif)

    avant = etat()

    #  L'action : un cercle SECONDAIRE, et le Booster de ce cercle.
    secondaire = cx.execute(
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, 'DATA', 'Data') RETURNING id"),
        {"e": entite},
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :a, :c, 'secondary', :debut)"
        ),
        {"e": entite, "a": appartenance, "c": secondaire, "debut": JANVIER},
    )
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'BOOSTER', :c, :p, :debut)"
        ),
        {"p": personne, "e": entite, "c": secondaire, "debut": JANVIER},
    )

    assert etat() == avant, (
        "un cercle secondaire, meme avec sa responsabilite de Booster, ne doit modifier "
        "NI le cercle principal, NI le DSM, NI le client, NI le statut (§8.2)"
    )
