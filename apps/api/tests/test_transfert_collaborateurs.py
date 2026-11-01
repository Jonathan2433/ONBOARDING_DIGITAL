"""Changer un collaborateur d'entite — LOT 9, `T3`, `MVP-L09-US002` (2/2).

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. le service `changer_d_entite`, sur une vraie connexion : l'ancienne
     appartenance va jusqu'a `archived` (`active` passe par `departed`,
     `future` y va directement), la nouvelle existe dans l'entite de
     destination, et les relations de l'ancienne sont reellement CLOSES
     (pas seulement rapportees) ;
  2. la grille d'etat : une cible deja `departed` ou `archived` est refusee
     en `409`, meme qu'une version obsolete ;
  3. la biconditionnelle statut/client est verifiee AVANT toute ecriture,
     sur la demande de la NOUVELLE appartenance ;
  4. le declencheur `dsm_responsabilite_active` dans l'entite de
     DESTINATION, traduit en `422`.

Ce fichier ne reteste PAS la mecanique de revocation elle-meme (sessions,
liens magiques) : `enregistrer_un_depart`/`archiver_une_appartenance` sont
reutilisees sans modification, deja prouvees au LOT 3 `T9` et au LOT 5 `T8`.
Il ne reteste pas non plus `archiver_le_parcours_au_depart` (LOT 7 `T11`) :
aucun parcours n'existe dans ces fixtures, et `parcours_onboarding_archive`
vaut donc `None` partout ci-dessous — une preuve de cablage, pas de la
fonction elle-meme.
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
from app.people.creation import CODE_CLIENT_INCOHERENT, DemandeDAppartenance
from app.people.ecriture import CODE_ETAT_INCOMPATIBLE, CODE_VERSION_OBSOLETE
from app.people.modeles import SituationProfessionnelle
from app.people.transfert import changer_d_entite
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T3"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
ARRIVEE_ANCIENNE = dt.date(2025, 6, 1)
ARRIVEE_NOUVELLE = dt.date(2026, 2, 1)


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
            "VALUES (:email, :normalise, 'Transfert', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
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


def _collaborateur_occupant(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str,
    arrivee: dt.date,
    depart: dt.date | None = None,
) -> uuid.UUID:
    """Une appartenance OCCUPANTE complete : metier, cercle, statut poses.

    Les trois relations existent pour que `relations_closes` ait quelque
    chose a rapporter — une appartenance nue prouverait moins. `depart` sert
    UNIQUEMENT au cas `departed` : `ck_entity_membership_depart_date_si_
    departed` l'exige, sans quoi l'insertion de decor elle-meme echoue.
    """
    appartenance = cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "departure_date, membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, :etat, 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": arrivee, "depart": depart, "etat": etat},
    ).scalar_one()
    cercle = _cercle(cx, entite, f"C-{uuid.uuid4().hex[:6]}")
    metier = _metier(cx, entite, f"M-{uuid.uuid4().hex[:6]}")
    debut = dt.datetime(arrivee.year, arrivee.month, arrivee.day, tzinfo=dt.UTC)
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_membership_id, entity_id, circle_id, "
            "membership_type, starts_at) VALUES (:a, :e, :c, 'principal', :d)"
        ),
        {"a": appartenance, "e": entite, "c": cercle, "d": debut},
    )
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_membership_id, entity_id, "
            "job_catalog_id, starts_at) VALUES (:a, :e, :m, :d)"
        ),
        {"a": appartenance, "e": entite, "m": metier, "d": debut},
    )
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_membership_id, entity_id, "
            "status, starts_at) VALUES (:a, :e, 'intercontract', :d)"
        ),
        {"a": appartenance, "e": entite, "d": debut},
    )
    return appartenance  # type: ignore[no-any-return]


def _demande_destination(*, metier: uuid.UUID | None, cercle: uuid.UUID) -> DemandeDAppartenance:
    return DemandeDAppartenance(
        arrival_date=ARRIVEE_NOUVELLE,
        job_catalog_id=metier,
        status=SituationProfessionnelle.INTERCONTRACT,
        client_id=None,
        dsm_person_id=None,
        circle_id=cercle,
    )


@pytest.mark.integration
def test_TEMOIN_un_collaborateur_ACTIF_est_transfere(cx: Connection) -> None:
    source, destination = _entite(cx, "SRC1"), _entite(cx, "DST1")
    personne = _personne(cx, "ACTIF")
    ancienne = _collaborateur_occupant(
        cx, source, personne, etat="active", arrivee=ARRIVEE_ANCIENNE
    )
    cercle_dst = _cercle(cx, destination, "C1")
    metier_dst = _metier(cx, destination, "M1")

    transfert = changer_d_entite(
        cx,
        entite_source=source,
        entite_destination=destination,
        cible=ancienne,
        acteur=personne,
        version_attendue=1,
        demande=_demande_destination(metier=metier_dst, cercle=cercle_dst),
        instant=JANVIER,
    )

    assert transfert.etat_precedent == "active"
    assert transfert.version == 1
    assert transfert.nouvelle_appartenance != ancienne

    #  L'ANCIENNE va jusqu'a `archived`, jamais `departed` seul.
    etat_ancienne = cx.execute(
        text("SELECT membership_state, entity_id FROM entity_membership WHERE id = :id"),
        {"id": ancienne},
    ).one()
    assert etat_ancienne[0] == "archived"
    assert etat_ancienne[1] == source

    #  La NOUVELLE existe dans la DESTINATION, avec le metier/cercle demandes.
    nouvelle = cx.execute(
        text(
            "SELECT entity_id, membership_state, professional_category FROM entity_membership "
            "WHERE id = :id"
        ),
        {"id": transfert.nouvelle_appartenance},
    ).one()
    assert nouvelle[0] == destination
    #  `ARRIVEE_NOUVELLE` (1er fevrier) est posterieure a `JANVIER` : `future`.
    assert nouvelle[1] == "future"
    assert nouvelle[2] == "consultant"

    #  Les TROIS relations de l'ancienne sont reellement CLOSES (`ends_at` pose).
    for table, lien in (
        ("circle_membership", "entity_membership_id"),
        ("membership_job_assignment", "entity_membership_id"),
        ("professional_status_assignment", "entity_membership_id"),
    ):
        ouvertes = cx.execute(
            text(f"SELECT count(*) FROM {table} WHERE {lien} = :a AND ends_at IS NULL"),  # noqa: S608
            {"a": ancienne},
        ).scalar_one()
        assert ouvertes == 0, table

    assert sum(transfert.relations_closes.values()) >= 3


@pytest.mark.integration
def test_un_collaborateur_SANS_metier_est_transfere(cx: Connection) -> None:
    """`DEC-675` (LOT 11 `T5`) : `metier=None` dans la destination ne cree
    aucune ligne `membership_job_assignment` — meme comportement que la
    creation, `creer_l_appartenance` etant partagee par les deux (§7.27).
    """
    source, destination = _entite(cx, "SRC-SANSMET"), _entite(cx, "DST-SANSMET")
    personne = _personne(cx, "SANSMETIER")
    ancienne = _collaborateur_occupant(
        cx, source, personne, etat="active", arrivee=ARRIVEE_ANCIENNE
    )
    cercle_dst = _cercle(cx, destination, "C1")

    transfert = changer_d_entite(
        cx,
        entite_source=source,
        entite_destination=destination,
        cible=ancienne,
        acteur=personne,
        version_attendue=1,
        demande=_demande_destination(metier=None, cercle=cercle_dst),
        instant=JANVIER,
    )

    total = cx.execute(
        text("SELECT count(*) FROM membership_job_assignment WHERE entity_membership_id = :id"),
        {"id": transfert.nouvelle_appartenance},
    ).scalar_one()
    assert total == 0


@pytest.mark.integration
def test_un_collaborateur_FUTURE_va_directement_a_archived(cx: Connection) -> None:
    source, destination = _entite(cx, "SRC2"), _entite(cx, "DST2")
    personne = _personne(cx, "FUTUR")
    #  Une arrivee dans le futur : `membership_state = 'future'`.
    arrivee_annulee = dt.date(2026, 6, 1)
    ancienne = _collaborateur_occupant(cx, source, personne, etat="future", arrivee=arrivee_annulee)
    cercle_dst = _cercle(cx, destination, "C1")
    metier_dst = _metier(cx, destination, "M1")
    #  UNE DATE QUI RECOUVRIRAIT L'ANCIENNE PERIODE NON BORNEE, SANS LA
    #  LIBERATION DU §7 DE L'EN-TETE DU MODULE : `creer_l_appartenance`
    #  echouerait sur `ex_entity_membership_sans_chevauchement`, meme avec
    #  une date de destination ANTERIEURE a l'arrivee annulee — les deux
    #  plages sont non bornees, donc toujours en chevauchement.
    arrivee_destination = arrivee_annulee - dt.timedelta(days=30)

    transfert = changer_d_entite(
        cx,
        entite_source=source,
        entite_destination=destination,
        cible=ancienne,
        acteur=personne,
        version_attendue=1,
        demande=DemandeDAppartenance(
            arrival_date=arrivee_destination,
            job_catalog_id=metier_dst,
            status=SituationProfessionnelle.INTERCONTRACT,
            client_id=None,
            dsm_person_id=None,
            circle_id=cercle_dst,
        ),
        instant=JANVIER,
    )

    assert transfert.etat_precedent == "future"
    #  Une seule revocation : `archiver_une_appartenance` seule, jamais de depart.
    assert len(transfert.revocations) == 1
    etat_ancienne, depart_ancienne = cx.execute(
        text("SELECT membership_state, departure_date FROM entity_membership WHERE id = :id"),
        {"id": ancienne},
    ).one()
    assert etat_ancienne == "archived"
    #  LA PERIODE EST VIDEE (`departure_date = arrival_date`), PAS `NULL` :
    #  c'est precisement ce qui a libere la date pour la nouvelle appartenance.
    assert depart_ancienne == arrivee_annulee


@pytest.mark.integration
def test_une_version_obsolete_est_refusee_en_409(cx: Connection) -> None:
    source, destination = _entite(cx, "SRC3"), _entite(cx, "DST3")
    personne = _personne(cx, "VERSION")
    ancienne = _collaborateur_occupant(
        cx, source, personne, etat="active", arrivee=ARRIVEE_ANCIENNE
    )
    cercle_dst = _cercle(cx, destination, "C1")
    metier_dst = _metier(cx, destination, "M1")

    with pytest.raises(ErreurApplicative) as excinfo:
        changer_d_entite(
            cx,
            entite_source=source,
            entite_destination=destination,
            cible=ancienne,
            acteur=personne,
            version_attendue=99,
            demande=_demande_destination(metier=metier_dst, cercle=cercle_dst),
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_VERSION_OBSOLETE
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_une_cible_DEJA_PARTIE_est_refusee_en_409(cx: Connection) -> None:
    source, destination = _entite(cx, "SRC4"), _entite(cx, "DST4")
    personne = _personne(cx, "PARTI")
    ancienne = _collaborateur_occupant(
        cx,
        source,
        personne,
        etat="departed",
        arrivee=ARRIVEE_ANCIENNE,
        depart=ARRIVEE_ANCIENNE + dt.timedelta(days=90),
    )
    cercle_dst = _cercle(cx, destination, "C1")
    metier_dst = _metier(cx, destination, "M1")

    with pytest.raises(ErreurApplicative) as excinfo:
        changer_d_entite(
            cx,
            entite_source=source,
            entite_destination=destination,
            cible=ancienne,
            acteur=personne,
            version_attendue=1,
            demande=_demande_destination(metier=metier_dst, cercle=cercle_dst),
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_ETAT_INCOMPATIBLE
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_la_biconditionnelle_est_verifiee_AVANT_toute_ecriture(cx: Connection) -> None:
    source, destination = _entite(cx, "SRC5"), _entite(cx, "DST5")
    personne = _personne(cx, "BICOND")
    ancienne = _collaborateur_occupant(
        cx, source, personne, etat="active", arrivee=ARRIVEE_ANCIENNE
    )
    cercle_dst = _cercle(cx, destination, "C1")
    metier_dst = _metier(cx, destination, "M1")
    demande_incoherente = DemandeDAppartenance(
        arrival_date=ARRIVEE_NOUVELLE,
        job_catalog_id=metier_dst,
        status=SituationProfessionnelle.MISSION,
        client_id=None,
        dsm_person_id=None,
        circle_id=cercle_dst,
    )

    avant = cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one()
    with pytest.raises(ErreurApplicative) as excinfo:
        changer_d_entite(
            cx,
            entite_source=source,
            entite_destination=destination,
            cible=ancienne,
            acteur=personne,
            version_attendue=1,
            demande=demande_incoherente,
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_CLIENT_INCOHERENT
    apres = cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one()
    assert apres == avant
    #  L'ANCIENNE n'a pas bouge : refusee avant tout depart/archivage.
    etat_ancienne = cx.execute(
        text("SELECT membership_state FROM entity_membership WHERE id = :id"), {"id": ancienne}
    ).scalar_one()
    assert etat_ancienne == "active"


@pytest.mark.integration
def test_un_dsm_SANS_responsabilite_active_DANS_LA_DESTINATION_est_refuse(
    cx: Connection,
) -> None:
    source, destination = _entite(cx, "SRC6"), _entite(cx, "DST6")
    personne = _personne(cx, "DSMDST")
    ancienne = _collaborateur_occupant(
        cx, source, personne, etat="active", arrivee=ARRIVEE_ANCIENNE
    )
    cercle_dst = _cercle(cx, destination, "C1")
    metier_dst = _metier(cx, destination, "M1")
    #  Une personne RATTACHEE a la destination, mais jamais designee DSM la-bas.
    pas_un_dsm = _personne(cx, "PASDSM")
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft')"
        ),
        {"p": pas_un_dsm, "e": destination},
    )
    demande = DemandeDAppartenance(
        arrival_date=ARRIVEE_NOUVELLE,
        job_catalog_id=metier_dst,
        status=SituationProfessionnelle.INTERCONTRACT,
        client_id=None,
        dsm_person_id=pas_un_dsm,
        circle_id=cercle_dst,
    )

    #  Traduit par `traduire_un_refus_de_la_base` (meme chemin que `T2`,
    #  `test_un_dsm_SANS_responsabilite_active_est_refuse_en_422`) : le
    #  declencheur leve une `CheckViolation`, jamais un `500`.
    with pytest.raises(ErreurApplicative) as excinfo:
        changer_d_entite(
            cx,
            entite_source=source,
            entite_destination=destination,
            cible=ancienne,
            acteur=personne,
            version_attendue=1,
            demande=demande,
            instant=JANVIER,
        )
    assert excinfo.value.statut == 422
