"""Transferts en masse — LOT 9, `T11`, `MVP-L09-US003`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  Ce fichier ne reteste PAS `changer_d_entite` lui-meme : ses transitions
  d'etat, ses revocations et sa biconditionnelle sont deja prouvees par
  `test_transfert_collaborateurs.py` (`T3`). Ce qui est NEUF a `T11`, et donc
  ce que cette suite prouve :

  1. plusieurs elements VALIDES reussissent dans le MEME appel ;
  2. l'apercu rend le MEME impact que l'execution, mais n'ECRIT rien ;
  3. un echec au MILIEU du lot n'annule PAS les elements qui l'entourent —
     chacun dans son propre savepoint ;
  4. rejouer le MEME lot est SANS DANGER (§18.6) : chaque element deja
     transfere est refuse explicitement, jamais rejoue ;
  5. une destination introuvable est rapportee SUR SON element, les autres
     continuent ;
  6. un acteur SANS role dans UNE destination est refuse SUR CET element,
     sans arreter le lot — la permission est resolue PAR element, puisque
     deux elements du meme lot peuvent viser des destinations differentes.
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
from app.people.creation import DemandeDAppartenance
from app.people.ecriture import CODE_ETAT_INCOMPATIBLE, CODE_VERSION_OBSOLETE
from app.people.modeles import SituationProfessionnelle
from app.people.transfert_masse import ElementDuTransfertEnMasse, executer_le_transfert_en_masse
from app.shared.database import moteur

MARQUEUR = "L9T11"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEBUT_RESPONSABILITE = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
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
            "VALUES (:email, :normalise, 'Masse', :s, 'active') RETURNING id"
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


def _esm(cx: Connection, entite: uuid.UUID, suffixe: str) -> uuid.UUID:
    """Une personne tenant SEULE la responsabilite ESM dans `entite`.

    `framework_responsibility_assignment`, meme table que `DSM`/`BOOSTER` —
    `resoudre_les_permissions` (LOT 2 `T8`) l'y lit, pas dans
    `technical_role_assignment` (reserve a `ADM-E`/`SUPER`).
    """
    personne = _personne(cx, suffixe)
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2024-01-01', 'active', 'consultant', 'draft')"
        ),
        {"p": personne, "e": entite},
    )
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": DEBUT_RESPONSABILITE},
    )
    return personne


def _collaborateur_occupant(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = "active",
    arrivee: dt.date = ARRIVEE_ANCIENNE,
) -> uuid.UUID:
    """Une appartenance OCCUPANTE minimale, cible d'un transfert."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": arrivee, "etat": etat},
    ).scalar_one()


def _element(
    *,
    appartenance: uuid.UUID,
    destination_code: str,
    version: int = 1,
    metier: uuid.UUID,
    cercle: uuid.UUID,
) -> ElementDuTransfertEnMasse:
    return ElementDuTransfertEnMasse(
        appartenance=appartenance,
        entite_destination_code=destination_code,
        version_attendue=version,
        circle_id=cercle,
        dsm_person_id=None,
        demande=DemandeDAppartenance(
            arrival_date=ARRIVEE_NOUVELLE,
            job_catalog_id=metier,
            status=SituationProfessionnelle.INTERCONTRACT,
            client_id=None,
            dsm_person_id=None,
            circle_id=cercle,
        ),
    )


def _code(entite_id: uuid.UUID, cx: Connection) -> str:
    return cx.execute(  # type: ignore[no-any-return]
        text("SELECT code FROM entity WHERE id = :e"), {"e": entite_id}
    ).scalar_one()


@pytest.mark.integration
def test_TEMOIN_deux_transferts_valides_reussissent_dans_le_meme_lot(cx: Connection) -> None:
    source = _entite(cx, "SRC1")
    destination = _entite(cx, "DST1")
    esm = _esm(cx, destination, "ESM1")
    personne_a, personne_b = _personne(cx, "A1"), _personne(cx, "B1")
    cible_a = _collaborateur_occupant(cx, source, personne_a)
    cible_b = _collaborateur_occupant(cx, source, personne_b)
    cercle_dst, metier_dst = _cercle(cx, destination, "C1"), _metier(cx, destination, "M1")
    code_destination = _code(destination, cx)

    resultats = executer_le_transfert_en_masse(
        cx,
        entite_source=source,
        acteur=esm,
        elements=[
            _element(
                appartenance=cible_a,
                destination_code=code_destination,
                metier=metier_dst,
                cercle=cercle_dst,
            ),
            _element(
                appartenance=cible_b,
                destination_code=code_destination,
                metier=metier_dst,
                cercle=cercle_dst,
            ),
        ],
        instant=JANVIER,
        mode="execution",
    )

    assert [r.succes for r in resultats] == [True, True]
    assert all(r.transfert is not None for r in resultats)
    for ancienne in (cible_a, cible_b):
        etat = cx.execute(
            text("SELECT membership_state FROM entity_membership WHERE id = :id"),
            {"id": ancienne},
        ).scalar_one()
        assert etat == "archived"


@pytest.mark.integration
def test_l_apercu_rend_le_meme_impact_mais_n_ecrit_rien(cx: Connection) -> None:
    source = _entite(cx, "SRC2")
    destination = _entite(cx, "DST2")
    esm = _esm(cx, destination, "ESM2")
    personne = _personne(cx, "A2")
    cible = _collaborateur_occupant(cx, source, personne)
    cercle_dst, metier_dst = _cercle(cx, destination, "C1"), _metier(cx, destination, "M1")
    avant = cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one()

    resultats = executer_le_transfert_en_masse(
        cx,
        entite_source=source,
        acteur=esm,
        elements=[
            _element(
                appartenance=cible,
                destination_code=_code(destination, cx),
                metier=metier_dst,
                cercle=cercle_dst,
            )
        ],
        instant=JANVIER,
        mode="apercu",
    )

    assert resultats[0].succes is True
    assert resultats[0].transfert is not None
    #  **L'IMPACT EST REEL** (pas une estimation) : la meme chose qu'un
    #  transfert execute aurait revoquee.
    assert resultats[0].transfert.etat_precedent == "active"

    #  **ET POURTANT RIEN N'EST ECRIT** : l'ancienne appartenance est
    #  TOUJOURS active, et aucune ligne de plus n'existe.
    etat = cx.execute(
        text("SELECT membership_state FROM entity_membership WHERE id = :id"), {"id": cible}
    ).scalar_one()
    assert etat == "active"
    apres = cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one()
    assert apres == avant


@pytest.mark.integration
def test_un_echec_au_milieu_n_annule_pas_les_elements_voisins(cx: Connection) -> None:
    source = _entite(cx, "SRC3")
    destination = _entite(cx, "DST3")
    esm = _esm(cx, destination, "ESM3")
    personne_a, personne_b, personne_c = (
        _personne(cx, "A3"),
        _personne(cx, "B3"),
        _personne(cx, "C3"),
    )
    cible_a = _collaborateur_occupant(cx, source, personne_a)
    cible_b = _collaborateur_occupant(cx, source, personne_b)
    cible_c = _collaborateur_occupant(cx, source, personne_c)
    cercle_dst, metier_dst = _cercle(cx, destination, "C1"), _metier(cx, destination, "M1")
    code_destination = _code(destination, cx)

    element_b_invalide = _element(
        appartenance=cible_b,
        destination_code=code_destination,
        version=99,  # version obsolete — refuse par `changer_d_entite`
        metier=metier_dst,
        cercle=cercle_dst,
    )
    resultats = executer_le_transfert_en_masse(
        cx,
        entite_source=source,
        acteur=esm,
        elements=[
            _element(
                appartenance=cible_a,
                destination_code=code_destination,
                metier=metier_dst,
                cercle=cercle_dst,
            ),
            element_b_invalide,
            _element(
                appartenance=cible_c,
                destination_code=code_destination,
                metier=metier_dst,
                cercle=cercle_dst,
            ),
        ],
        instant=JANVIER,
        mode="execution",
    )

    assert [r.succes for r in resultats] == [True, False, True]
    assert resultats[1].code_erreur == CODE_VERSION_OBSOLETE

    #  A ET C sont bien ARCHIVES — l'echec de B ne les a PAS annules.
    for ancienne in (cible_a, cible_c):
        etat = cx.execute(
            text("SELECT membership_state FROM entity_membership WHERE id = :id"),
            {"id": ancienne},
        ).scalar_one()
        assert etat == "archived"
    #  B, lui, n'a pas bouge.
    etat_b = cx.execute(
        text("SELECT membership_state FROM entity_membership WHERE id = :id"), {"id": cible_b}
    ).scalar_one()
    assert etat_b == "active"


@pytest.mark.integration
def test_rejouer_le_meme_lot_est_sans_danger(cx: Connection) -> None:
    source = _entite(cx, "SRC4")
    destination = _entite(cx, "DST4")
    esm = _esm(cx, destination, "ESM4")
    personne = _personne(cx, "A4")
    cible = _collaborateur_occupant(cx, source, personne)
    cercle_dst, metier_dst = _cercle(cx, destination, "C1"), _metier(cx, destination, "M1")
    element = _element(
        appartenance=cible,
        destination_code=_code(destination, cx),
        metier=metier_dst,
        cercle=cercle_dst,
    )

    premier = executer_le_transfert_en_masse(
        cx, entite_source=source, acteur=esm, elements=[element], instant=JANVIER, mode="execution"
    )
    assert premier[0].succes is True
    avant_rejeu = cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one()

    #  **LE MEME LOT, REJOUE TEL QUEL** (meme `version_attendue=1`, deja
    #  perimee puisque l'element est maintenant `archived`).
    second = executer_le_transfert_en_masse(
        cx, entite_source=source, acteur=esm, elements=[element], instant=JANVIER, mode="execution"
    )
    assert second[0].succes is False
    assert second[0].code_erreur == CODE_ETAT_INCOMPATIBLE

    #  **AUCUNE DEUXIEME ECRITURE** : rejouer n'a rien ajoute.
    apres_rejeu = cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one()
    assert apres_rejeu == avant_rejeu


@pytest.mark.integration
def test_une_destination_introuvable_est_rapportee_sur_son_element_seul(cx: Connection) -> None:
    source = _entite(cx, "SRC5")
    destination = _entite(cx, "DST5")
    esm = _esm(cx, destination, "ESM5")
    personne_a, personne_b = _personne(cx, "A5"), _personne(cx, "B5")
    cible_a = _collaborateur_occupant(cx, source, personne_a)
    cible_b = _collaborateur_occupant(cx, source, personne_b)
    cercle_dst, metier_dst = _cercle(cx, destination, "C1"), _metier(cx, destination, "M1")

    element_introuvable = _element(
        appartenance=cible_a,
        destination_code=f"{MARQUEUR}-INCONNU",
        metier=metier_dst,
        cercle=cercle_dst,
    )
    element_valide = _element(
        appartenance=cible_b,
        destination_code=_code(destination, cx),
        metier=metier_dst,
        cercle=cercle_dst,
    )
    resultats = executer_le_transfert_en_masse(
        cx,
        entite_source=source,
        acteur=esm,
        elements=[element_introuvable, element_valide],
        instant=JANVIER,
        mode="execution",
    )

    assert resultats[0].succes is False
    assert resultats[0].code_erreur == "entite_introuvable"
    assert resultats[1].succes is True


@pytest.mark.integration
def test_un_acteur_sans_role_dans_une_destination_est_refuse_sans_arreter_le_lot(
    cx: Connection,
) -> None:
    source = _entite(cx, "SRC6")
    destination_refusee = _entite(cx, "DSTR6")
    destination_autorisee = _entite(cx, "DSTA6")
    #  L'ACTEUR EST ESM DANS `destination_autorisee` SEULEMENT.
    esm = _esm(cx, destination_autorisee, "ESM6")
    personne_a, personne_b = _personne(cx, "A6"), _personne(cx, "B6")
    cible_a = _collaborateur_occupant(cx, source, personne_a)
    cible_b = _collaborateur_occupant(cx, source, personne_b)
    cercle_refuse, metier_refuse = (
        _cercle(cx, destination_refusee, "C1"),
        _metier(cx, destination_refusee, "M1"),
    )
    cercle_ok, metier_ok = (
        _cercle(cx, destination_autorisee, "C1"),
        _metier(cx, destination_autorisee, "M1"),
    )

    element_refuse = _element(
        appartenance=cible_a,
        destination_code=_code(destination_refusee, cx),
        metier=metier_refuse,
        cercle=cercle_refuse,
    )
    element_autorise = _element(
        appartenance=cible_b,
        destination_code=_code(destination_autorisee, cx),
        metier=metier_ok,
        cercle=cercle_ok,
    )
    resultats = executer_le_transfert_en_masse(
        cx,
        entite_source=source,
        acteur=esm,
        elements=[element_refuse, element_autorise],
        instant=JANVIER,
        mode="execution",
    )

    assert resultats[0].succes is False
    assert resultats[0].code_erreur == "acces_refuse"
    assert resultats[1].succes is True
