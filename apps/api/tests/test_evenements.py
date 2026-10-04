"""Schema evenementiel — LOT 8, `T1`, modele §17.

Chaque chemin inter-entites a son refus et son temoin. Le fichier prouve aussi
les deux exigences negatives de la sous-etape : aucun pseudo-etat « passe » et
aucune donnee de recurrence ou de participant ne sont stockes.
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
from app.events import ETATS_EVENEMENT, EtatEvenement
from app.modeles import metadonnees
from app.shared.database import moteur

MARQUEUR = "L8T1"
DEBUT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 10, 10, 10, 0, tzinfo=dt.UTC)


def test_les_quatre_etats_du_17_1_sont_declares_sans_pseudo_etat_passe() -> None:
    assert set(ETATS_EVENEMENT) == {"draft", "published", "cancelled", "archived"}
    assert "past" not in ETATS_EVENEMENT


def test_les_cinq_tables_ne_portent_ni_recurrence_ni_participant() -> None:
    """Critere de sortie n°1 : l'absence est verifiee sur toute la structure.

    `T3` etend ce temoin a la cinquieme table, `event_dsm_scope` (`ECART-067`,
    `DEC-622`), et aux modeles de requete — voir
    `test_creation_evenements.py::test_aucun_champ_de_la_DEMANDE_n_est_de_nature_participant`.
    Le manifeste est verifie par `test_contrat.py`, generique a toutes les routes.
    """

    noms = {
        "event",
        "event_circle_scope",
        "event_office_scope",
        "event_dsm_scope",
        "event_media",
    }
    interdits = {
        "participant",
        "registration",
        "attendance",
        "notification",
        "recurrence",
        "occurrence",
    }
    assert noms <= set(metadonnees.tables)
    assert not any(interdit in nom for nom in metadonnees.tables for interdit in interdits)
    for nom in noms:
        colonnes = {colonne.name for colonne in metadonnees.tables[nom].columns}
        assert not any(interdit in colonne for colonne in colonnes for interdit in interdits)


def test_l_etat_passe_est_derive_et_n_est_pas_stocke() -> None:
    colonnes = {colonne.name for colonne in metadonnees.tables["event"].columns}
    assert {"starts_at", "ends_at", "state"} <= colonnes
    assert not ({"past", "is_past", "passed_at"} & colonnes)


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


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:entite, :code, :nom, 1) RETURNING id"
        ),
        {"entite": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:entite, :code, :nom, 1) RETURNING id"
        ),
        {"entite": entite, "code": code, "nom": code},
    ).scalar_one()


def _evenement(
    cx: Connection,
    entite: uuid.UUID,
    *,
    debut: dt.datetime = DEBUT,
    fin: dt.datetime = FIN,
    etat: str | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO event (entity_id, title, starts_at, ends_at, state) "
            "VALUES (:entite, 'Petit-dejeuner', :debut, :fin, "
            "COALESCE(:etat, 'draft')) RETURNING id"
        ),
        {"entite": entite, "debut": debut, "fin": fin, "etat": etat},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalisee, 'Evenement', 'L8T1', 'active') RETURNING id"
        ),
        {"email": adresse, "normalisee": adresse},
    ).scalar_one()


def _media(cx: Connection, entite: uuid.UUID, suffixe: str) -> uuid.UUID:
    personne = _personne(cx, suffixe)
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256) "
            "VALUES (:entite, :personne, 'pending', 'image', 'event.jpg', :cle, "
            "'image/jpeg', 1024, :empreinte) RETURNING id"
        ),
        {
            "entite": entite,
            "personne": personne,
            "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            "empreinte": uuid.uuid4().hex * 2,
        },
    ).scalar_one()


@pytest.mark.integration
def test_TEMOIN_un_evenement_valide_est_accepte_et_brouillon_par_defaut(cx: Connection) -> None:
    entite = _entite(cx, "DEF")
    evenement = _evenement(cx, entite)
    etat = cx.execute(
        text("SELECT state FROM event WHERE id = :id"), {"id": evenement}
    ).scalar_one()
    assert etat == EtatEvenement.DRAFT


@pytest.mark.integration
def test_un_evenement_doit_finir_apres_son_debut(cx: Connection) -> None:
    entite = _entite(cx, "TEMPS")
    with pytest.raises(IntegrityError, match="ck_event_chronologie_valide"):
        _evenement(cx, entite, fin=DEBUT)


@pytest.mark.integration
def test_un_etat_d_evenement_invente_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "ETAT")
    with pytest.raises(IntegrityError, match="ck_event_state_valide"):
        _evenement(cx, entite, etat="past")


@pytest.mark.integration
def test_TEMOIN_les_portees_cercle_et_bureau_de_la_meme_entite_sont_acceptees(
    cx: Connection,
) -> None:
    entite = _entite(cx, "PORT")
    evenement = _evenement(cx, entite)
    cercle = _cercle(cx, entite, "DATA")
    bureau = _bureau(cx, entite, "BDS")
    cx.execute(
        text(
            "INSERT INTO event_circle_scope (entity_id, event_id, circle_id) "
            "VALUES (:entite, :evenement, :cercle)"
        ),
        {"entite": entite, "evenement": evenement, "cercle": cercle},
    )
    cx.execute(
        text(
            "INSERT INTO event_office_scope (entity_id, event_id, office_id) "
            "VALUES (:entite, :evenement, :bureau)"
        ),
        {"entite": entite, "evenement": evenement, "bureau": bureau},
    )


@pytest.mark.integration
def test_une_portee_cercle_ne_peut_pas_pointer_un_evenement_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "CE1"), _entite(cx, "CE2")
    evenement = _evenement(cx, ailleurs)
    cercle = _cercle(cx, ici, "DATA")
    with pytest.raises(IntegrityError, match="fk_event_circle_scope_event"):
        cx.execute(
            text(
                "INSERT INTO event_circle_scope (entity_id, event_id, circle_id) "
                "VALUES (:entite, :evenement, :cercle)"
            ),
            {"entite": ici, "evenement": evenement, "cercle": cercle},
        )


@pytest.mark.integration
def test_une_portee_cercle_ne_peut_pas_pointer_un_cercle_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "CC1"), _entite(cx, "CC2")
    evenement = _evenement(cx, ici)
    cercle = _cercle(cx, ailleurs, "DATA")
    with pytest.raises(IntegrityError, match="fk_event_circle_scope_circle"):
        cx.execute(
            text(
                "INSERT INTO event_circle_scope (entity_id, event_id, circle_id) "
                "VALUES (:entite, :evenement, :cercle)"
            ),
            {"entite": ici, "evenement": evenement, "cercle": cercle},
        )


@pytest.mark.integration
def test_une_portee_bureau_ne_peut_pas_pointer_un_evenement_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "BE1"), _entite(cx, "BE2")
    evenement = _evenement(cx, ailleurs)
    bureau = _bureau(cx, ici, "BDS")
    with pytest.raises(IntegrityError, match="fk_event_office_scope_event"):
        cx.execute(
            text(
                "INSERT INTO event_office_scope (entity_id, event_id, office_id) "
                "VALUES (:entite, :evenement, :bureau)"
            ),
            {"entite": ici, "evenement": evenement, "bureau": bureau},
        )


@pytest.mark.integration
def test_une_portee_bureau_ne_peut_pas_pointer_un_bureau_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "BB1"), _entite(cx, "BB2")
    evenement = _evenement(cx, ici)
    bureau = _bureau(cx, ailleurs, "BDS")
    with pytest.raises(IntegrityError, match="fk_event_office_scope_office"):
        cx.execute(
            text(
                "INSERT INTO event_office_scope (entity_id, event_id, office_id) "
                "VALUES (:entite, :evenement, :bureau)"
            ),
            {"entite": ici, "evenement": evenement, "bureau": bureau},
        )


@pytest.mark.integration
def test_TEMOIN_une_portee_dsm_est_acceptee(cx: Connection) -> None:
    """`ECART-067`, `DEC-622` — la cinquieme table, posee par `T3`."""
    entite = _entite(cx, "DSM")
    evenement = _evenement(cx, entite)
    dsm = _personne(cx, "dsm-port")
    identifiant = cx.execute(
        text(
            "INSERT INTO event_dsm_scope (entity_id, event_id, dsm_person_id) "
            "VALUES (:entite, :evenement, :dsm) RETURNING id"
        ),
        {"entite": entite, "evenement": evenement, "dsm": dsm},
    ).scalar_one()
    assert identifiant is not None


@pytest.mark.integration
def test_une_portee_dsm_ne_peut_pas_pointer_un_evenement_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "DE1"), _entite(cx, "DE2")
    evenement = _evenement(cx, ailleurs)
    dsm = _personne(cx, "dsm-isol")
    with pytest.raises(IntegrityError, match="fk_event_dsm_scope_event"):
        cx.execute(
            text(
                "INSERT INTO event_dsm_scope (entity_id, event_id, dsm_person_id) "
                "VALUES (:entite, :evenement, :dsm)"
            ),
            {"entite": ici, "evenement": evenement, "dsm": dsm},
        )


@pytest.mark.integration
def test_deux_portees_dsm_sur_le_MEME_evenement_sont_refusees(cx: Connection) -> None:
    """A la difference de cercle/bureau, la matrice §11 ecrit « Entite OU
    consultants » — une disjonction, jamais une liste : un evenement ne porte
    donc jamais deux lignes `event_dsm_scope` actives, meme pour DEUX DSM
    differents. L'index unique porte sur `event_id` SEUL, pas sur le couple
    `(event_id, dsm_person_id)` comme les deux tables sœurs.
    """
    entite = _entite(cx, "DD1")
    evenement = _evenement(cx, entite)
    premier, second = _personne(cx, "dsm-un"), _personne(cx, "dsm-deux")
    requete = text(
        "INSERT INTO event_dsm_scope (entity_id, event_id, dsm_person_id) "
        "VALUES (:entite, :evenement, :dsm)"
    )
    cx.execute(requete, {"entite": entite, "evenement": evenement, "dsm": premier})
    with pytest.raises(IntegrityError, match="uq_event_dsm_scope_event_non_archive"):
        cx.execute(requete, {"entite": entite, "evenement": evenement, "dsm": second})


@pytest.mark.integration
def test_TEMOIN_un_media_de_la_meme_entite_est_accepte(cx: Connection) -> None:
    entite = _entite(cx, "MED")
    evenement = _evenement(cx, entite)
    media = _media(cx, entite, "med")
    identifiant = cx.execute(
        text(
            "INSERT INTO event_media (entity_id, event_id, media_asset_id, display_order, "
            "display_role) VALUES (:entite, :evenement, :media, 0, 'cover') RETURNING id"
        ),
        {"entite": entite, "evenement": evenement, "media": media},
    ).scalar_one()
    assert identifiant is not None


@pytest.mark.integration
def test_un_media_ne_peut_pas_pointer_un_evenement_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _entite(cx, "ME1"), _entite(cx, "ME2")
    evenement = _evenement(cx, ailleurs)
    media = _media(cx, ici, "me")
    with pytest.raises(IntegrityError, match="fk_event_media_event"):
        cx.execute(
            text(
                "INSERT INTO event_media (entity_id, event_id, media_asset_id, display_order, "
                "display_role) VALUES (:entite, :evenement, :media, 0, 'cover')"
            ),
            {"entite": ici, "evenement": evenement, "media": media},
        )


@pytest.mark.integration
def test_un_evenement_ne_peut_pas_pointer_un_media_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _entite(cx, "MM1"), _entite(cx, "MM2")
    evenement = _evenement(cx, ici)
    media = _media(cx, ailleurs, "mm")
    with pytest.raises(IntegrityError, match="fk_event_media_media_asset"):
        cx.execute(
            text(
                "INSERT INTO event_media (entity_id, event_id, media_asset_id, display_order, "
                "display_role) VALUES (:entite, :evenement, :media, 0, 'cover')"
            ),
            {"entite": ici, "evenement": evenement, "media": media},
        )


@pytest.mark.integration
def test_deux_medias_de_meme_rang_sur_un_evenement_sont_refuses(cx: Connection) -> None:
    entite = _entite(cx, "ORD")
    evenement = _evenement(cx, entite)
    premier = _media(cx, entite, "ord1")
    second = _media(cx, entite, "ord2")
    requete = text(
        "INSERT INTO event_media (entity_id, event_id, media_asset_id, display_order, "
        "display_role) VALUES (:entite, :evenement, :media, 0, 'cover')"
    )
    cx.execute(requete, {"entite": entite, "evenement": evenement, "media": premier})
    with pytest.raises(IntegrityError, match="uq_event_media_event_ordre_non_archive"):
        cx.execute(requete, {"entite": entite, "evenement": evenement, "media": second})


@pytest.mark.integration
def test_un_role_d_affichage_vide_est_refuse_sans_enumeration_inventee(cx: Connection) -> None:
    entite = _entite(cx, "ROLE")
    evenement = _evenement(cx, entite)
    media = _media(cx, entite, "role")
    with pytest.raises(IntegrityError, match="ck_event_media_role_affichage_non_vide"):
        cx.execute(
            text(
                "INSERT INTO event_media (entity_id, event_id, media_asset_id, display_order, "
                "display_role) VALUES (:entite, :evenement, :media, 0, '   ')"
            ),
            {"entite": entite, "evenement": evenement, "media": media},
        )
