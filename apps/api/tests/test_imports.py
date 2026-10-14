"""Schema de l'import CSV — LOT 9, `T1`, modele §19.

Chaque chemin inter-entites a son refus et son temoin. Le fichier prouve aussi
l'arbitrage du 08/10/2026 : l'import reste SYNCHRONE, et aucune table
`async_job`/`outbox_message` n'existe — elles restent reservees au LOT 11.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.imports import ETATS_LIGNE_IMPORT, ETATS_LOT_IMPORT, TYPES_DE_DECISION_IMPORT
from app.modeles import metadonnees
from app.shared.database import moteur

MARQUEUR = "L9T1"


def test_les_huit_etats_du_19_1_sont_declares() -> None:
    assert set(ETATS_LOT_IMPORT) == {
        "uploaded",
        "analyzing",
        "preview_ready",
        "approved",
        "importing",
        "completed",
        "failed",
        "cancelled",
    }


def test_les_six_etats_du_19_2_sont_declares() -> None:
    assert set(ETATS_LIGNE_IMPORT) == {
        "valid",
        "warning",
        "needs_decision",
        "rejected",
        "imported",
        "updated",
    }


def test_les_cinq_types_de_decision_du_19_4_sont_declares() -> None:
    assert set(TYPES_DE_DECISION_IMPORT) == {
        "person_merge",
        "profile_reactivation",
        "client_alias_creation",
        "canonical_client_selection",
        "voluntary_rejection",
    }


def test_l_import_reste_synchrone_aucune_table_async_job_ni_outbox_message() -> None:
    """Arbitrage du 08/10/2026 : `async_job`/`outbox_message` restent au LOT 11."""

    assert "import_batch" in metadonnees.tables
    assert "async_job" not in metadonnees.tables
    assert "outbox_message" not in metadonnees.tables


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
            "VALUES (:email, :normalisee, 'Import', 'L9T1', 'active') RETURNING id"
        ),
        {"email": adresse, "normalisee": adresse},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, current_date, 'active', 'consultant', 'published') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _lot(cx: Connection, entite: uuid.UUID, *, etat: str | None = None) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO import_batch (entity_id, source_filename, source_checksum_sha256, "
            "state) VALUES (:entite, 'collaborateurs.csv', :empreinte, COALESCE(:etat, "
            "'uploaded')) RETURNING id"
        ),
        {"entite": entite, "empreinte": uuid.uuid4().hex * 2, "etat": etat},
    ).scalar_one()


def _ligne(
    cx: Connection,
    entite: uuid.UUID,
    lot: uuid.UUID,
    *,
    numero: int = 1,
    etat: str | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO import_row (entity_id, import_batch_id, row_number, raw_data, state) "
            "VALUES (:entite, :lot, :numero, :donnees, COALESCE(:etat, 'valid')) RETURNING id"
        ),
        {
            "entite": entite,
            "lot": lot,
            "numero": numero,
            "donnees": '{"email": "exemple@exalt-company.com"}',
            "etat": etat,
        },
    ).scalar_one()


@pytest.mark.integration
def test_TEMOIN_un_lot_une_ligne_un_probleme_et_une_decision_sont_acceptes(
    cx: Connection,
) -> None:
    entite = _entite(cx, "DEF")
    lot = _lot(cx, entite)
    ligne = _ligne(cx, entite, lot)
    cx.execute(
        text(
            "INSERT INTO import_row_issue (entity_id, import_row_id, code, message, level) "
            "VALUES (:entite, :ligne, 'email_absent', 'E-mail manquant', 'error')"
        ),
        {"entite": entite, "ligne": ligne},
    )
    cx.execute(
        text(
            "INSERT INTO import_decision (entity_id, import_row_id, decision_type) "
            "VALUES (:entite, :ligne, 'voluntary_rejection')"
        ),
        {"entite": entite, "ligne": ligne},
    )
    etat_lot = cx.execute(
        text("SELECT state FROM import_batch WHERE id = :id"), {"id": lot}
    ).scalar_one()
    assert etat_lot == "uploaded"


@pytest.mark.integration
def test_un_numero_de_ligne_negatif_ou_nul_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "NUM")
    lot = _lot(cx, entite)
    with pytest.raises(IntegrityError, match="ck_import_row_numero_de_ligne_positif"):
        _ligne(cx, entite, lot, numero=0)


@pytest.mark.integration
def test_un_etat_de_lot_invente_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "ETATLOT")
    with pytest.raises(IntegrityError, match="ck_import_batch_state_valide"):
        _lot(cx, entite, etat="en_cours")


@pytest.mark.integration
def test_un_etat_de_ligne_invente_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "ETATLIGNE")
    lot = _lot(cx, entite)
    with pytest.raises(IntegrityError, match="ck_import_row_state_valide"):
        _ligne(cx, entite, lot, etat="en_cours")


@pytest.mark.integration
def test_deux_lignes_du_meme_lot_portant_le_meme_numero_sont_refusees(cx: Connection) -> None:
    entite = _entite(cx, "DOUBLON")
    lot = _lot(cx, entite)
    _ligne(cx, entite, lot, numero=1)
    with pytest.raises(IntegrityError, match="uq_import_row_batch_numero"):
        _ligne(cx, entite, lot, numero=1)


@pytest.mark.integration
def test_une_ligne_ne_peut_pas_pointer_un_lot_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _entite(cx, "LE1"), _entite(cx, "LE2")
    lot = _lot(cx, ailleurs)
    with pytest.raises(IntegrityError, match="fk_import_row_import_batch"):
        _ligne(cx, ici, lot)


@pytest.mark.integration
def test_une_ligne_ne_peut_pas_pointer_une_appartenance_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "LM1"), _entite(cx, "LM2")
    lot = _lot(cx, ici)
    personne = _personne(cx, "LM")
    appartenance_ailleurs = _appartenance(cx, ailleurs, personne)
    with pytest.raises(IntegrityError, match="fk_import_row_entity_membership"):
        cx.execute(
            text(
                "INSERT INTO import_row (entity_id, import_batch_id, row_number, raw_data, "
                "target_membership_id) VALUES (:entite, :lot, 1, '{}', :appartenance)"
            ),
            {"entite": ici, "lot": lot, "appartenance": appartenance_ailleurs},
        )


@pytest.mark.integration
def test_un_probleme_ne_peut_pas_pointer_une_ligne_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _entite(cx, "PI1"), _entite(cx, "PI2")
    lot = _lot(cx, ailleurs)
    ligne = _ligne(cx, ailleurs, lot)
    with pytest.raises(IntegrityError, match="fk_import_row_issue_import_row"):
        cx.execute(
            text(
                "INSERT INTO import_row_issue (entity_id, import_row_id, code, message, level) "
                "VALUES (:entite, :ligne, 'code', 'message', 'error')"
            ),
            {"entite": ici, "ligne": ligne},
        )


@pytest.mark.integration
def test_une_decision_ne_peut_pas_pointer_une_ligne_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _entite(cx, "DI1"), _entite(cx, "DI2")
    lot = _lot(cx, ailleurs)
    ligne = _ligne(cx, ailleurs, lot)
    with pytest.raises(IntegrityError, match="fk_import_decision_import_row"):
        cx.execute(
            text(
                "INSERT INTO import_decision (entity_id, import_row_id, decision_type) "
                "VALUES (:entite, :ligne, 'voluntary_rejection')"
            ),
            {"entite": ici, "ligne": ligne},
        )
