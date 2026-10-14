"""Creer manuellement un collaborateur — LOT 9, `T2`, `MVP-L09-US002` (1/2).

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. structure : aucune `professional_category` dans la demande (§6.2 de
     `app/people/creation.py`) ;
  2. la grille complete de `resoudre_l_autorisation_de_creation`, role par
     role — **chaque refus est apparie a son temoin positif** (§7.39) : un DSM
     qui designe un AUTRE DSM est refuse, le MEME DSM pour LUI-MEME reussit ;
     un Booster sur SON cercle reussit, sur un AUTRE cercle il echoue, et avec
     un DSM demande (meme vide de sens) il echoue aussi ;
  3. le service `creer_un_collaborateur`, sur une vraie connexion : les cinq
     ecritures relationnelles, `membership_state` derive de `arrival_date`, et
     la biconditionnelle statut/client refusee AVANT toute ecriture ;
  4. le declencheur `dsm_responsabilite_active`, traduit en `422` et non en
     `500`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.people.creation import (
    CODE_CLIENT_INCOHERENT,
    DemandeDAppartenance,
    DemandeDeCollaborateur,
    creer_un_collaborateur,
)
from app.people.modeles import EtatAppartenance, SituationProfessionnelle
from app.people.routes import DemandeDeCreationDeCollaborateur
from app.permissions.perimetre import PropositionDeCreation, resoudre_l_autorisation_de_creation
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T2"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
ARRIVEE = dt.date(2026, 1, 15)


def test_la_demande_ne_porte_aucune_categorie_professionnelle() -> None:
    """La categorie `dg` exige une action separee — voir l'en-tete du module."""
    assert "professional_category" not in DemandeDeCreationDeCollaborateur.model_fields
    assert "categorie" not in DemandeDeCreationDeCollaborateur.model_fields


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


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
    code = f"{MARQUEUR}-{suffixe}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Creation', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _metier(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label) "
            "VALUES (:e, :code, :libelle) RETURNING id"
        ),
        {"e": entite, "code": code, "libelle": code},
    ).scalar_one()


def _client(cx: Connection, entite: uuid.UUID, nom: str) -> uuid.UUID:
    client = cx.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affichage, 'active') RETURNING id"
        ),
        {"canonique": nom.lower(), "affichage": nom},
    ).scalar_one()
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    return client  # type: ignore[no-any-return]


def _responsabilite(
    cx: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_resp: str,
    cercle: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, assigned_by_person_id, "
            "starts_at) VALUES (:p, :e, :t, :c, :p, :d)"
        ),
        {"p": personne, "e": entite, "t": type_resp, "c": cercle, "d": debut},
    )


def _acteur(
    cx: Connection,
    entite: uuid.UUID,
    suffixe: str,
    *,
    responsabilite: str | None = None,
    cercle: uuid.UUID | None = None,
) -> uuid.UUID:
    personne = _personne(cx, suffixe)
    _appartenance(cx, entite, personne)
    if responsabilite is not None:
        _responsabilite(
            cx, entite=entite, personne=personne, type_resp=responsabilite, cercle=cercle
        )
    return personne


def _roles(
    cx: Connection, *, acteur: uuid.UUID, entite: uuid.UUID, instant: dt.datetime = DEMAIN
) -> frozenset[RoleDeLaMatrice]:
    return frozenset(resoudre_les_permissions(cx, acteur, entite, instant).roles)


def _demande(
    *,
    metier: uuid.UUID,
    cercle: uuid.UUID,
    statut: SituationProfessionnelle = SituationProfessionnelle.INTERCONTRACT,
    client: uuid.UUID | None = None,
    dsm: uuid.UUID | None = None,
    arrivee: dt.date = ARRIVEE,
) -> DemandeDeCollaborateur:
    return DemandeDeCollaborateur(
        email=f"{MARQUEUR.lower()}-{uuid.uuid4().hex[:10]}@exalt-company.com",
        first_name="Nouveau",
        last_name="Collaborateur",
        preferred_name=None,
        appartenance=DemandeDAppartenance(
            arrival_date=arrivee,
            job_catalog_id=metier,
            status=statut,
            client_id=client,
            dsm_person_id=dsm,
            circle_id=cercle,
        ),
    )


# ============================================================================
#  2. La grille de `resoudre_l_autorisation_de_creation`
# ============================================================================


@pytest.mark.integration
def test_TEMOIN_un_ESM_cree_sans_restriction(cx: Connection) -> None:
    entite = _entite(cx, "ESM1")
    acteur = _acteur(cx, entite, "ESM", responsabilite="ESM")
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=acteur,
        roles=_roles(cx, acteur=acteur, entite=entite),
        proposition=PropositionDeCreation(circle_id=uuid.uuid4(), dsm_person_id=uuid.uuid4()),
        instant=DEMAIN,
    )
    assert autorise is True


@pytest.mark.integration
def test_un_DSM_pour_LUI_MEME_est_autorise(cx: Connection) -> None:
    entite = _entite(cx, "DSM1")
    dsm = _acteur(cx, entite, "DSM", responsabilite="DSM")
    cercle = _cercle(cx, entite, "C1")
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=dsm,
        roles=_roles(cx, acteur=dsm, entite=entite),
        proposition=PropositionDeCreation(circle_id=cercle, dsm_person_id=dsm),
        instant=DEMAIN,
    )
    assert autorise is True


@pytest.mark.integration
def test_un_DSM_pour_UN_AUTRE_DSM_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "DSM2")
    dsm = _acteur(cx, entite, "DSMA", responsabilite="DSM")
    autre_dsm = _acteur(cx, entite, "DSMB", responsabilite="DSM")
    cercle = _cercle(cx, entite, "C1")
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=dsm,
        roles=_roles(cx, acteur=dsm, entite=entite),
        proposition=PropositionDeCreation(circle_id=cercle, dsm_person_id=autre_dsm),
        instant=DEMAIN,
    )
    assert autorise is False


@pytest.mark.integration
def test_un_BOOSTER_sur_SON_cercle_est_autorise(cx: Connection) -> None:
    entite = _entite(cx, "BO1")
    cercle = _cercle(cx, entite, "C1")
    booster = _acteur(cx, entite, "BOOST", responsabilite="BOOSTER", cercle=cercle)
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=booster,
        roles=_roles(cx, acteur=booster, entite=entite),
        proposition=PropositionDeCreation(circle_id=cercle, dsm_person_id=None),
        instant=DEMAIN,
    )
    assert autorise is True


@pytest.mark.integration
def test_un_BOOSTER_sur_un_AUTRE_cercle_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "BO2")
    son_cercle = _cercle(cx, entite, "C1")
    autre_cercle = _cercle(cx, entite, "C2")
    booster = _acteur(cx, entite, "BOOST", responsabilite="BOOSTER", cercle=son_cercle)
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=booster,
        roles=_roles(cx, acteur=booster, entite=entite),
        proposition=PropositionDeCreation(circle_id=autre_cercle, dsm_person_id=None),
        instant=DEMAIN,
    )
    assert autorise is False


@pytest.mark.integration
def test_un_BOOSTER_qui_demande_un_DSM_est_refuse(cx: Connection) -> None:
    """Meme exclusion que `CHAMPS_DU_BOOSTER` pour la modification : `hors changement de DSM`."""
    entite = _entite(cx, "BO3")
    cercle = _cercle(cx, entite, "C1")
    booster = _acteur(cx, entite, "BOOST", responsabilite="BOOSTER", cercle=cercle)
    un_dsm = _acteur(cx, entite, "DSM", responsabilite="DSM")
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=booster,
        roles=_roles(cx, acteur=booster, entite=entite),
        proposition=PropositionDeCreation(circle_id=cercle, dsm_person_id=un_dsm),
        instant=DEMAIN,
    )
    assert autorise is False


@pytest.mark.integration
def test_aucun_role_qualifiant_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "VIDE")
    acteur = _acteur(cx, entite, "EMP")
    roles = _roles(cx, acteur=acteur, entite=entite)
    assert not roles & {RoleDeLaMatrice.ESM, RoleDeLaMatrice.DSM, RoleDeLaMatrice.BOOSTER}
    autorise = resoudre_l_autorisation_de_creation(
        cx,
        entite=entite,
        acteur=acteur,
        roles=roles,
        proposition=PropositionDeCreation(circle_id=uuid.uuid4(), dsm_person_id=None),
        instant=DEMAIN,
    )
    assert autorise is False


# ============================================================================
#  3. Le service `creer_un_collaborateur`
# ============================================================================


@pytest.mark.integration
def test_TEMOIN_un_collaborateur_complet_est_cree(cx: Connection) -> None:
    entite = _entite(cx, "CREA1")
    acteur = _personne(cx, "ACTEUR")
    cercle = _cercle(cx, entite, "C1")
    metier = _metier(cx, entite, "DEV")
    client = _client(cx, entite, "Client A")
    dsm = _acteur(cx, entite, "DSM", responsabilite="DSM")

    resultat = creer_un_collaborateur(
        cx,
        entite=entite,
        acteur=acteur,
        demande=_demande(
            metier=metier,
            cercle=cercle,
            statut=SituationProfessionnelle.MISSION,
            client=client,
            dsm=dsm,
        ),
        instant=JANVIER,
    )
    assert resultat.version == 1

    ligne = (
        cx.execute(
            text(
                "SELECT membership_state, professional_category, profile_visibility "
                "FROM entity_membership WHERE id = :id"
            ),
            {"id": resultat.appartenance},
        )
        .mappings()
        .one()
    )
    #  `ARRIVEE` (15 janvier) est POSTERIEURE a `JANVIER` (1er janvier) : donc
    #  `future`, pas `active` — c'est precisement ce qui distingue les deux.
    assert ligne["membership_state"] == EtatAppartenance.FUTURE.value
    assert ligne["professional_category"] == "consultant"
    assert ligne["profile_visibility"] == "draft"

    for table in (
        "membership_job_assignment",
        "circle_membership",
        "professional_status_assignment",
        "dsm_assignment",
    ):
        colonne = (
            "consultant_membership_id" if table == "dsm_assignment" else "entity_membership_id"
        )
        total = cx.execute(
            text(f"SELECT count(*) FROM {table} WHERE {colonne} = :id"),  # noqa: S608
            {"id": resultat.appartenance},
        ).scalar_one()
        assert total == 1, table


@pytest.mark.integration
def test_une_arrivee_passee_rend_une_appartenance_ACTIVE(cx: Connection) -> None:
    entite = _entite(cx, "CREA2")
    acteur = _personne(cx, "ACTEUR")
    cercle = _cercle(cx, entite, "C1")
    metier = _metier(cx, entite, "DEV")

    resultat = creer_un_collaborateur(
        cx,
        entite=entite,
        acteur=acteur,
        demande=_demande(metier=metier, cercle=cercle, arrivee=dt.date(2025, 12, 1)),
        instant=JANVIER,
    )
    etat = cx.execute(
        text("SELECT membership_state FROM entity_membership WHERE id = :id"),
        {"id": resultat.appartenance},
    ).scalar_one()
    assert etat == EtatAppartenance.ACTIVE.value


@pytest.mark.integration
def test_une_mission_sans_client_est_refusee_AVANT_toute_ecriture(cx: Connection) -> None:
    entite = _entite(cx, "CREA3")
    acteur = _personne(cx, "ACTEUR")
    cercle = _cercle(cx, entite, "C1")
    metier = _metier(cx, entite, "DEV")

    avant = cx.execute(text("SELECT count(*) FROM person")).scalar_one()
    with pytest.raises(ErreurApplicative) as excinfo:
        creer_un_collaborateur(
            cx,
            entite=entite,
            acteur=acteur,
            demande=_demande(
                metier=metier, cercle=cercle, statut=SituationProfessionnelle.MISSION, client=None
            ),
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_CLIENT_INCOHERENT
    apres = cx.execute(text("SELECT count(*) FROM person")).scalar_one()
    assert apres == avant


@pytest.mark.integration
def test_un_intercontrat_AVEC_client_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "CREA4")
    acteur = _personne(cx, "ACTEUR")
    cercle = _cercle(cx, entite, "C1")
    metier = _metier(cx, entite, "DEV")
    client = _client(cx, entite, "Client B")

    with pytest.raises(ErreurApplicative) as excinfo:
        creer_un_collaborateur(
            cx,
            entite=entite,
            acteur=acteur,
            demande=_demande(
                metier=metier,
                cercle=cercle,
                statut=SituationProfessionnelle.INTERCONTRACT,
                client=client,
            ),
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_CLIENT_INCOHERENT


# ============================================================================
#  4. Le declencheur `dsm_responsabilite_active`, traduit et non 500
# ============================================================================


@pytest.mark.integration
def test_un_dsm_SANS_responsabilite_active_est_refuse_en_422(cx: Connection) -> None:
    entite = _entite(cx, "CREA5")
    acteur = _personne(cx, "ACTEUR")
    cercle = _cercle(cx, entite, "C1")
    metier = _metier(cx, entite, "DEV")
    #  Une personne RATTACHEE, mais JAMAIS designee DSM par aucune
    #  responsabilite Framework — le declencheur doit refuser.
    pas_un_dsm = _acteur(cx, entite, "PASDSM")

    with pytest.raises(ErreurApplicative) as excinfo:
        creer_un_collaborateur(
            cx,
            entite=entite,
            acteur=acteur,
            demande=_demande(metier=metier, cercle=cercle, dsm=pas_un_dsm),
            instant=JANVIER,
        )
    assert excinfo.value.statut == 422
