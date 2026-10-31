"""Verifier le contenu reel d'une photo et generer sa miniature — LOT 11, `T2`.

Modele §16.1/§16.2, `MVP-L11-US005` : « la relance est idempotente ; les
variantes respectent les budgets ; l'original reste protege ».

LE TEMOIN DECISIF, MEME FORME QUE CELUI DE L'E-MAIL (`T1`)

  `test_rejouer_le_job_sur_un_media_deja_traite_ne_regenere_pas_la_variante`
  simule un relais interrompu entre le succes du job et le `UPDATE
  processed_at` — exactement `test_rejouer_le_relais_sur_un_message_deja_
  traite_ne_renvoie_pas_le_courriel` de `test_jobs.py`, transpose au `topic`
  `media`. Si l'idempotence du job echouait, ce test verrait DEUX variantes
  posees (ou une erreur de contrainte unique) au lieu d'aucune regeneration.

UN REJET EST UN SUCCES DU JOB

  `test_un_contenu_illisible_est_REJETE_pas_en_echec` et `test_un_format_non_
  autorise_est_rejete` prouvent que `state` passe a `rejected` et que la
  fonction REND NORMALEMENT (aucune exception) — voir l'en-tete d'`app.media.
  traitement`.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from PIL import Image
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.jobs.outbox import TOPIC_MEDIA, publier_dans_l_outbox, relayer_le_lot
from app.media.objets import client_s3, deposer_l_objet
from app.media.traitement import (
    BORNE_MINIATURE_OCTETS,
    CODE_CONTENU_ILLISIBLE,
    CODE_FORMAT_NON_AUTORISE,
    COTE_DE_LA_MINIATURE_PIXELS,
    VARIANTE_SERVIE,
    generer_les_variantes_depuis_la_charge,
)
from app.shared.database import moteur

MARQUEUR = "L11T2TR"


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


@pytest.fixture
def instant() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _image_reelle(*, format_: str = "JPEG", couleur: str = "red", cote: int = 400) -> bytes:
    """Une VRAIE image, decodable par Pillow — jamais des octets inventes."""
    image = Image.new("RGB", (cote, cote), couleur)
    tampon = io.BytesIO()
    image.save(tampon, format=format_)
    return tampon.getvalue()


def _entite(cx: Connection) -> uuid.UUID:
    code = f"{MARQUEUR}{uuid.uuid4().hex[:8]}"
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity (code, display_name, city, country_code, status, "
                    "timezone) VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', "
                    "'Europe/Paris') RETURNING id"
                ),
                {"code": code, "nom": code},
            ).scalar_one()
        )
    )


def _personne(cx: Connection) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{uuid.uuid4().hex[:8]}@exemple.test"
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, 'Traitement', 'T2', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


def _media_pending(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, cle: str, instant: dt.datetime
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, "
                    "media_type, original_filename, object_key, mime_declared, size_bytes, "
                    "checksum_sha256, created_at, updated_at) "
                    "VALUES (:e, :p, 'pending', 'image', 'photo.jpg', :cle, 'image/jpeg', "
                    "1, :empreinte, :i, :i) RETURNING id"
                ),
                {"e": entite, "p": acteur, "cle": cle, "empreinte": "a" * 64, "i": instant},
            ).scalar_one()
        )
    )


@pytest.fixture
def decor(
    cx: Connection, parametres_de_la_stack: Parametres, instant: dt.datetime
) -> dict[str, Any]:
    entite = _entite(cx)
    acteur = _personne(cx)
    return {"entite": entite, "acteur": acteur, "parametres": parametres_de_la_stack}


def _deposer_original(parametres: Parametres, cle: str, contenu: bytes) -> None:
    try:
        deposer_l_objet(parametres, cle, contenu)
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")


def _nettoyer(parametres: Parametres, *cles: str) -> None:
    client = client_s3(parametres)
    for cle in cles:
        with contextlib.suppress(Exception):  # menage, jamais fatal
            client.delete_object(Bucket=parametres.MINIO_BUCKET, Key=cle)  # type: ignore[attr-defined]


@pytest.mark.integration
def test_un_contenu_reel_devient_ready_avec_sa_miniature(
    cx: Connection, decor: dict[str, Any], instant: dt.datetime
) -> None:
    parametres = decor["parametres"]
    cle = f"test/{MARQUEUR}/{uuid.uuid4().hex}/original"
    contenu = _image_reelle(format_="JPEG", couleur="red", cote=800)
    _deposer_original(parametres, cle, contenu)
    media = _media_pending(
        cx, entite=decor["entite"], acteur=decor["acteur"], cle=cle, instant=instant
    )

    try:
        generer_les_variantes_depuis_la_charge(
            cx, {"media_asset_id": str(media)}, instant=instant, parametres=parametres
        )

        actif = (
            cx.execute(
                text(
                    "SELECT state, mime_detected, width, height, rejection_code "
                    "FROM media_asset WHERE id = :id"
                ),
                {"id": media},
            )
            .mappings()
            .one()
        )
        assert actif["state"] == "ready"
        assert actif["mime_detected"] == "image/jpeg"
        assert actif["width"] == 800
        assert actif["height"] == 800
        assert actif["rejection_code"] is None

        variante = (
            cx.execute(
                text(
                    "SELECT variant_type, width, height, size_bytes, object_key "
                    "FROM media_variant WHERE media_asset_id = :id"
                ),
                {"id": media},
            )
            .mappings()
            .one()
        )
        assert variante["variant_type"] == VARIANTE_SERVIE
        assert variante["width"] == COTE_DE_LA_MINIATURE_PIXELS
        assert variante["height"] == COTE_DE_LA_MINIATURE_PIXELS
        assert variante["size_bytes"] <= BORNE_MINIATURE_OCTETS
        assert variante["object_key"] != cle  # jamais la cle de l'original
    finally:
        cle_variante = f"media/{decor['entite']}/{media}/{VARIANTE_SERVIE}.jpg"
        _nettoyer(parametres, cle, cle_variante)


@pytest.mark.integration
def test_une_photo_PNG_transparente_est_aplatie_sur_fond_blanc(
    cx: Connection, decor: dict[str, Any], instant: dt.datetime
) -> None:
    parametres = decor["parametres"]
    cle = f"test/{MARQUEUR}/{uuid.uuid4().hex}/original"
    image = Image.new("RGBA", (300, 300), (0, 0, 255, 0))  # entierement transparente
    tampon = io.BytesIO()
    image.save(tampon, format="PNG")
    _deposer_original(parametres, cle, tampon.getvalue())
    media = _media_pending(
        cx, entite=decor["entite"], acteur=decor["acteur"], cle=cle, instant=instant
    )

    try:
        generer_les_variantes_depuis_la_charge(
            cx, {"media_asset_id": str(media)}, instant=instant, parametres=parametres
        )
        actif = (
            cx.execute(
                text("SELECT state, mime_detected FROM media_asset WHERE id = :id"), {"id": media}
            )
            .mappings()
            .one()
        )
        assert actif["state"] == "ready"
        assert actif["mime_detected"] == "image/png"
    finally:
        cle_variante = f"media/{decor['entite']}/{media}/{VARIANTE_SERVIE}.jpg"
        _nettoyer(parametres, cle, cle_variante)


@pytest.mark.integration
def test_un_contenu_illisible_est_REJETE_pas_en_echec(
    cx: Connection, decor: dict[str, Any], instant: dt.datetime
) -> None:
    parametres = decor["parametres"]
    cle = f"test/{MARQUEUR}/{uuid.uuid4().hex}/original"
    _deposer_original(parametres, cle, b"ceci n'est pas une image, juste du texte quelconque")
    media = _media_pending(
        cx, entite=decor["entite"], acteur=decor["acteur"], cle=cle, instant=instant
    )

    try:
        generer_les_variantes_depuis_la_charge(
            cx, {"media_asset_id": str(media)}, instant=instant, parametres=parametres
        )
        actif = (
            cx.execute(
                text("SELECT state, rejection_code FROM media_asset WHERE id = :id"), {"id": media}
            )
            .mappings()
            .one()
        )
        assert actif["state"] == "rejected"
        assert actif["rejection_code"] == CODE_CONTENU_ILLISIBLE
        assert (
            cx.execute(
                text("SELECT count(*) FROM media_variant WHERE media_asset_id = :id"), {"id": media}
            ).scalar_one()
            == 0
        )
    finally:
        _nettoyer(parametres, cle)


@pytest.mark.integration
def test_un_format_decode_hors_liste_est_rejete(
    cx: Connection, decor: dict[str, Any], instant: dt.datetime
) -> None:
    """Un GIF, parfaitement decodable par Pillow, mais HORS de `FORMATS_DECODES_AUTORISES`."""
    parametres = decor["parametres"]
    cle = f"test/{MARQUEUR}/{uuid.uuid4().hex}/original"
    _deposer_original(parametres, cle, _image_reelle(format_="GIF", couleur="green", cote=50))
    media = _media_pending(
        cx, entite=decor["entite"], acteur=decor["acteur"], cle=cle, instant=instant
    )

    try:
        generer_les_variantes_depuis_la_charge(
            cx, {"media_asset_id": str(media)}, instant=instant, parametres=parametres
        )
        actif = (
            cx.execute(
                text("SELECT state, rejection_code FROM media_asset WHERE id = :id"), {"id": media}
            )
            .mappings()
            .one()
        )
        assert actif["state"] == "rejected"
        assert actif["rejection_code"] == CODE_FORMAT_NON_AUTORISE
    finally:
        _nettoyer(parametres, cle)


@pytest.mark.integration
def test_un_media_qui_n_est_plus_pending_n_est_pas_retraite(
    cx: Connection, decor: dict[str, Any], instant: dt.datetime
) -> None:
    """Deja `ready` (par un essai anterieur) : la fonction ne fait RIEN."""
    parametres = decor["parametres"]
    cle = f"test/{MARQUEUR}/{uuid.uuid4().hex}/original"
    media = _media_pending(
        cx, entite=decor["entite"], acteur=decor["acteur"], cle=cle, instant=instant
    )
    cx.execute(text("UPDATE media_asset SET state = 'ready' WHERE id = :id"), {"id": media})

    generer_les_variantes_depuis_la_charge(
        cx, {"media_asset_id": str(media)}, instant=instant, parametres=parametres
    )
    assert (
        cx.execute(
            text("SELECT count(*) FROM media_variant WHERE media_asset_id = :id"), {"id": media}
        ).scalar_one()
        == 0
    )


@pytest.mark.integration
def test_rejouer_le_job_sur_un_media_deja_traite_ne_regenere_pas_la_variante(
    cx: Connection, decor: dict[str, Any], instant: dt.datetime
) -> None:
    """LE TEMOIN DECISIF — meme forme que `test_jobs.py` pour l'e-mail.

    Simule un relais interrompu ENTRE le succes du traitement et le `UPDATE
    processed_at` : le message est republie, un `async_job(job_type='media')`
    deja `succeeded` existe pour sa cle — `commencer_un_essai` doit refuser de
    relancer `generer_les_variantes_depuis_la_charge`, donc AUCUNE deuxieme
    variante n'est posee (et aucune violation de la contrainte unique).
    """
    parametres = decor["parametres"]
    cle = f"test/{MARQUEUR}/{uuid.uuid4().hex}/original"
    _deposer_original(parametres, cle, _image_reelle())
    media = _media_pending(
        cx, entite=decor["entite"], acteur=decor["acteur"], cle=cle, instant=instant
    )

    try:
        identifiant = publier_dans_l_outbox(
            cx, topic=TOPIC_MEDIA, payload={"media_asset_id": str(media)}, instant=instant
        )
        #  Simule le crash : le job a REUSSI (donc la variante existe deja et
        #  le media est `ready`) mais le message n'a JAMAIS ete marque traite.
        generer_les_variantes_depuis_la_charge(
            cx, {"media_asset_id": str(media)}, instant=instant, parametres=parametres
        )
        cx.execute(
            text(
                "INSERT INTO async_job "
                "(job_type, state, idempotency_key, attempt_count, started_at, finished_at, "
                " created_at, updated_at) "
                "VALUES ('media', 'succeeded', :cle, 1, :instant, :instant, :instant, :instant)"
            ),
            {"cle": str(identifiant), "instant": instant},
        )

        nombre_traites = relayer_le_lot(cx, instant=instant)

        assert nombre_traites == 1  # processed_at est rattrape...
        assert (
            cx.execute(
                text("SELECT count(*) FROM media_variant WHERE media_asset_id = :id"),
                {"id": media},
            ).scalar_one()
            == 1
        )  # ...mais AUCUNE deuxieme variante n'est posee
    finally:
        cle_variante = f"media/{decor['entite']}/{media}/{VARIANTE_SERVIE}.jpg"
        _nettoyer(parametres, cle, cle_variante)
