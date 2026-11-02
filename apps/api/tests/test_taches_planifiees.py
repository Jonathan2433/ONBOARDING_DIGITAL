"""Les six taches planifiees et leur verrou — LOT 11, `T4`, `MVP-L11-US006`/`US007`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. le verrou de `scheduled_task_run` (`app.scheduling.execution`) : une
     execution deja `running` refuse une seconde execution CONCURRENTE de la
     MEME tache (§20.3 : « une seule execution logique ») ;
  2. chaque tache, un paire negatif/positif (§7.39) : ce qui doit etre touche
     l'est, ce qui ne doit pas l'etre ne l'est pas ;
  3. l'idempotence de `anonymiser_apres_depart` : rejouee, elle ne retouche
     jamais une personne deja anonymisee ;
  4. `executer_le_cycle` (l'orchestrateur) : six lignes `scheduled_task_run`
     par cycle, et une tache DEJA `running` (verrouillee par un autre worker)
     est sautee sans affecter les cinq autres.

Ancre DERIVEE de `now()`, jamais une date figee — §7.47 de la passation : une
date absolue comparee a `now()` dans une meme requete devient une bombe a
retardement datee.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.media.objets import ObjetIntrouvable, client_s3, deposer_l_objet, lire_l_objet
from app.scheduling.execution import (
    TacheDejaEnCours,
    commencer_l_execution,
    terminer_avec_succes,
    terminer_en_echec,
)
from app.scheduling.orchestrateur import executer_le_cycle
from app.scheduling.taches import (
    anonymiser_apres_depart,
    confirmer_les_evenements_passes,
    detecter_les_jobs_bloques,
    expirer_les_liens_et_sessions,
    nettoyer_les_medias,
    purger_l_audit,
)
from app.shared.database import moteur

pytestmark = pytest.mark.integration

MARQUEUR = "L11T4"
#  Derivee de `now()`, bornee dans le passe proche pour que toute arithmetique
#  de jours/mois reste coherente quel que soit le jour d'execution.
ANCRAGE = dt.datetime.now(dt.UTC).replace(microsecond=0) - dt.timedelta(hours=1)
JOUR = dt.timedelta(days=1)


def _exiger_la_stack(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_la_stack(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


# ---------------------------------------------------------------------------
#  Decor partage
# ---------------------------------------------------------------------------


def _entite(cx: Connection, suffixe: str) -> uuid.UUID:
    code = f"{MARQUEUR}{suffixe}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :a, 'Prenom', 'Nom', 'active') RETURNING id"
        ),
        {"a": adresse},
    ).scalar_one()


def _appartenance(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    *,
    etat: str = "active",
    arrivee: dt.date,
    depart: dt.date | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, :etat, 'consultant', 'published') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": arrivee, "depart": depart, "etat": etat},
    ).scalar_one()


def _fiche(
    cx: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    *,
    short_intro: str | None = "Bonjour",
    fun_fact: str | None = "Aime le velo",
    photo_media_id: uuid.UUID | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO arrival_profile (entity_id, entity_membership_id, state, short_intro, "
            "fun_fact, photo_media_id) VALUES (:e, :m, 'validated', :intro, :fun, :photo)"
        ),
        {
            "e": entite,
            "m": appartenance,
            "intro": short_intro,
            "fun": fun_fact,
            "photo": photo_media_id,
        },
    )


def _media(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cle: str,
    etat: str = "pending",
    cree_le: dt.datetime | None = None,
    archive_le: dt.datetime | None = None,
) -> uuid.UUID:
    media: uuid.UUID = cx.execute(
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256, "
            "ready_at, created_at, updated_at) "
            "VALUES (:e, :p, :etat, 'image', 'photo.jpg', :cle, 'image/jpeg', 1, :empreinte, "
            ":pret, :cree, :cree) RETURNING id"
        ),
        {
            "e": entite,
            "p": acteur,
            "etat": etat,
            "cle": cle,
            "empreinte": "a" * 64,
            "pret": cree_le if etat in ("ready", "archived", "deleted") else None,
            "cree": cree_le or ANCRAGE,
        },
    ).scalar_one()
    if archive_le is not None:
        cx.execute(
            text("UPDATE media_asset SET archived_at = :a, archive_reason = 'test' WHERE id = :m"),
            {"a": archive_le, "m": media},
        )
    return media


def _autorisation_photo(
    cx: Connection, *, personne: uuid.UUID, media: uuid.UUID, retiree: bool = False
) -> None:
    cx.execute(
        text(
            "INSERT INTO photo_authorization (person_id, media_asset_id, granted_at, "
            "withdrawn_at, source) VALUES (:p, :m, :octroi, :retrait, 'self_service')"
        ),
        {"p": personne, "m": media, "octroi": ANCRAGE, "retrait": ANCRAGE if retiree else None},
    )


def _job(
    cx: Connection,
    *,
    etat: str,
    cree_le: dt.datetime,
    dernier_battement: dt.datetime | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO async_job (job_type, state, idempotency_key, attempt_count, "
            "created_at, updated_at, last_heartbeat_at, started_at) "
            "VALUES ('maintenance', :etat, :cle, 1, :cree, :cree, :battement, :cree) RETURNING id"
        ),
        {
            "etat": etat,
            "cle": uuid.uuid4().hex,
            "cree": cree_le,
            "battement": dernier_battement,
        },
    ).scalar_one()


def _audit_event(cx: Connection, *, retention_until: dt.datetime) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO audit_event (action_code, resource_type, summary, correlation_token, "
            "occurred_at, retention_until) "
            "VALUES ('test_action', 'test_resource', 'resume de test', :corr, :occ, :retenu) "
            "RETURNING id"
        ),
        {
            "corr": f"corr-{uuid.uuid4().hex[:12]}",
            "occ": ANCRAGE,
            "retenu": retention_until,
        },
    ).scalar_one()


def _lien_magique(cx: Connection, personne: uuid.UUID, *, demande: dt.datetime) -> uuid.UUID:
    """`expires_at` est TOUJOURS `demande + 15 minutes` (contrainte en base,

    `ck_magic_link_request_expiration_a_quinze_minutes`) : le seul levier pour
    simuler un lien expire est l'instant de la DEMANDE, jamais la duree.
    """
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO magic_link_request (person_id, token_hash, requested_at, expires_at) "
            "VALUES (:p, :h, :demande, :demande + interval '15 minutes') RETURNING id"
        ),
        {
            "p": personne,
            "h": uuid.uuid4().hex + uuid.uuid4().hex[:24],
            "demande": demande,
        },
    ).scalar_one()


def _session(cx: Connection, personne: uuid.UUID, *, creee_depuis_jours: float = 0) -> uuid.UUID:
    """Une session dont l'activite s'arrete a sa creation.

    `created_at` et `last_activity_at` portent la MEME valeur, reculee de
    `creee_depuis_jours` par rapport a `ANCRAGE` : c'est ce qui simule une
    inactivite de cette duree, sans jamais violer
    `ck_user_session_activite_apres_creation` (`last_activity_at >=
    created_at`). `absolute_expires_at` est posee au PLAFOND du modele
    (30 jours depuis cette creation reculee, `ck_user_session_expiration_
    apres_creation`) : assez loin pour ne jamais interferer avec le test
    d'inactivite, dont les durees testees restent bien en-deca.
    """
    debut = ANCRAGE - dt.timedelta(days=creee_depuis_jours)
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO user_session (session_token_hash, person_id, created_at, "
            "last_activity_at, absolute_expires_at) "
            "VALUES (:h, :p, :debut, :debut, :debut + interval '30 days') RETURNING id"
        ),
        {
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "p": personne,
            "debut": debut,
        },
    ).scalar_one()


# ---------------------------------------------------------------------------
#  1. Le verrou — `app.scheduling.execution`
# ---------------------------------------------------------------------------


def test_une_execution_deja_running_refuse_une_seconde_execution(cx: Connection) -> None:
    commencer_l_execution(cx, task_name="purge_audit", instant=ANCRAGE)
    with pytest.raises(TacheDejaEnCours):
        commencer_l_execution(cx, task_name="purge_audit", instant=ANCRAGE)


def test_une_execution_terminee_libere_le_verrou_pour_la_suivante(cx: Connection) -> None:
    ligne = commencer_l_execution(cx, task_name="purge_audit", instant=ANCRAGE)
    terminer_avec_succes(cx, ligne.id, instant=ANCRAGE, items_processed=0)
    #  Plus aucune ligne `running` : un second cycle peut demarrer la MEME tache.
    seconde = commencer_l_execution(cx, task_name="purge_audit", instant=ANCRAGE)
    assert seconde.id != ligne.id


def test_un_echec_est_consigne_et_libere_aussi_le_verrou(cx: Connection) -> None:
    ligne = commencer_l_execution(cx, task_name="nettoyage_medias", instant=ANCRAGE)
    finale = terminer_en_echec(cx, ligne.id, instant=ANCRAGE, error_message="defaut de test")
    assert finale.state == "failed"
    assert finale.error_message == "defaut de test"
    commencer_l_execution(cx, task_name="nettoyage_medias", instant=ANCRAGE)  # ne leve pas


# ---------------------------------------------------------------------------
#  2. Expiration des liens et des sessions
# ---------------------------------------------------------------------------


def test_un_lien_expire_non_consomme_est_invalide(cx: Connection) -> None:
    personne = _personne(cx, f"{MARQUEUR.lower()}-lien-expire@exemple.test")
    lien = _lien_magique(cx, personne, demande=ANCRAGE - dt.timedelta(minutes=30))
    expirer_les_liens_et_sessions(cx, instant=ANCRAGE, parametres=None)  # type: ignore[arg-type]
    etat = cx.execute(
        text("SELECT invalidated_at FROM magic_link_request WHERE id = :l"), {"l": lien}
    ).scalar_one()
    assert etat is not None


def test_un_lien_encore_valide_n_est_pas_touche(cx: Connection) -> None:
    personne = _personne(cx, f"{MARQUEUR.lower()}-lien-valide@exemple.test")
    lien = _lien_magique(cx, personne, demande=ANCRAGE)
    expirer_les_liens_et_sessions(cx, instant=ANCRAGE, parametres=None)  # type: ignore[arg-type]
    etat = cx.execute(
        text("SELECT invalidated_at FROM magic_link_request WHERE id = :l"), {"l": lien}
    ).scalar_one()
    assert etat is None


def test_une_session_inactive_depuis_plus_de_sept_jours_est_revoquee(cx: Connection) -> None:
    personne = _personne(cx, f"{MARQUEUR.lower()}-session-inactive@exemple.test")
    session = _session(cx, personne, creee_depuis_jours=8)
    expirer_les_liens_et_sessions(cx, instant=ANCRAGE, parametres=None)  # type: ignore[arg-type]
    revoquee = cx.execute(
        text("SELECT revoked_at FROM user_session WHERE id = :s"), {"s": session}
    ).scalar_one()
    assert revoquee is not None


def test_une_session_active_recemment_n_est_pas_revoquee(cx: Connection) -> None:
    personne = _personne(cx, f"{MARQUEUR.lower()}-session-active@exemple.test")
    session = _session(cx, personne)
    expirer_les_liens_et_sessions(cx, instant=ANCRAGE, parametres=None)  # type: ignore[arg-type]
    revoquee = cx.execute(
        text("SELECT revoked_at FROM user_session WHERE id = :s"), {"s": session}
    ).scalar_one()
    assert revoquee is None


# ---------------------------------------------------------------------------
#  3. Evenements passes — rien a ecrire
# ---------------------------------------------------------------------------


def test_confirmer_les_evenements_passes_ne_touche_a_rien(cx: Connection) -> None:
    assert confirmer_les_evenements_passes(cx, instant=ANCRAGE, parametres=None) == 0  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
#  4. Anonymisation apres depart
# ---------------------------------------------------------------------------


class _ParametresDeTest:
    DEPARTURE_ARCHIVE_MONTHS = 3


def test_une_personne_partie_depuis_plus_de_trois_mois_est_anonymisee(cx: Connection) -> None:
    entite = _entite(cx, "ANO1")
    personne = _personne(cx, f"{MARQUEUR.lower()}-anonymise@exemple.test")
    appartenance = _appartenance(
        cx,
        personne,
        entite,
        etat="archived",
        arrivee=(ANCRAGE - 200 * JOUR).date(),
        depart=(ANCRAGE - 100 * JOUR).date(),
    )
    _fiche(cx, entite, appartenance)
    media = _media(cx, entite=entite, acteur=personne, cle=f"{MARQUEUR}/photo.jpg", etat="ready")
    _autorisation_photo(cx, personne=personne, media=media)

    nombre = anonymiser_apres_depart(cx, instant=ANCRAGE, parametres=_ParametresDeTest())  # type: ignore[arg-type]
    assert nombre == 1

    ligne = cx.execute(
        text(
            "SELECT first_name, last_name, email, email_normalized, account_state, "
            "anonymized_at FROM person WHERE id = :p"
        ),
        {"p": personne},
    ).one()
    assert ligne.first_name == "Anonymisé"
    assert ligne.last_name == "Anonymisé"
    assert ligne.email == ligne.email_normalized
    assert "@anonymise.invalid" in ligne.email
    assert ligne.account_state == "anonymized"
    assert ligne.anonymized_at is not None

    fiche = cx.execute(
        text(
            "SELECT short_intro, fun_fact, photo_media_id FROM arrival_profile "
            "WHERE entity_membership_id = :m"
        ),
        {"m": appartenance},
    ).one()
    assert fiche.short_intro == "Anonymisé"
    assert fiche.fun_fact is None
    assert fiche.photo_media_id is None

    autorisation_active = cx.execute(
        text(
            "SELECT count(*) FROM photo_authorization WHERE person_id = :p AND withdrawn_at IS NULL"
        ),
        {"p": personne},
    ).scalar_one()
    assert autorisation_active == 0


def test_une_personne_toujours_active_n_est_pas_anonymisee(cx: Connection) -> None:
    entite = _entite(cx, "ANO2")
    personne = _personne(cx, f"{MARQUEUR.lower()}-active@exemple.test")
    _appartenance(cx, personne, entite, etat="active", arrivee=(ANCRAGE - 200 * JOUR).date())

    anonymiser_apres_depart(cx, instant=ANCRAGE, parametres=_ParametresDeTest())  # type: ignore[arg-type]

    etat = cx.execute(
        text("SELECT account_state FROM person WHERE id = :p"), {"p": personne}
    ).scalar_one()
    assert etat == "active"


def test_une_personne_partie_depuis_moins_de_trois_mois_n_est_pas_anonymisee(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ANO3")
    personne = _personne(cx, f"{MARQUEUR.lower()}-depart-recent@exemple.test")
    _appartenance(
        cx,
        personne,
        entite,
        etat="archived",
        arrivee=(ANCRAGE - 200 * JOUR).date(),
        depart=(ANCRAGE - 10 * JOUR).date(),
    )

    anonymiser_apres_depart(cx, instant=ANCRAGE, parametres=_ParametresDeTest())  # type: ignore[arg-type]

    etat = cx.execute(
        text("SELECT account_state FROM person WHERE id = :p"), {"p": personne}
    ).scalar_one()
    assert etat == "active"


def test_rejouer_l_anonymisation_ne_retouche_jamais_une_personne_deja_anonymisee(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ANO4")
    personne = _personne(cx, f"{MARQUEUR.lower()}-idempotence@exemple.test")
    _appartenance(
        cx,
        personne,
        entite,
        etat="archived",
        arrivee=(ANCRAGE - 200 * JOUR).date(),
        depart=(ANCRAGE - 100 * JOUR).date(),
    )

    premier_passage = anonymiser_apres_depart(cx, instant=ANCRAGE, parametres=_ParametresDeTest())  # type: ignore[arg-type]
    assert premier_passage == 1
    horodatage_initial = cx.execute(
        text("SELECT anonymized_at FROM person WHERE id = :p"), {"p": personne}
    ).scalar_one()

    second_passage = anonymiser_apres_depart(cx, instant=ANCRAGE, parametres=_ParametresDeTest())  # type: ignore[arg-type]
    assert second_passage == 0
    horodatage_final = cx.execute(
        text("SELECT anonymized_at FROM person WHERE id = :p"), {"p": personne}
    ).scalar_one()
    assert horodatage_final == horodatage_initial


# ---------------------------------------------------------------------------
#  5. Purge de l'audit
# ---------------------------------------------------------------------------


def test_une_ligne_d_audit_echue_est_purgee(cx: Connection) -> None:
    echue = _audit_event(cx, retention_until=ANCRAGE - JOUR)
    purger_l_audit(cx, instant=ANCRAGE, parametres=None)  # type: ignore[arg-type]
    reste = cx.execute(
        text("SELECT count(*) FROM audit_event WHERE id = :e"), {"e": echue}
    ).scalar_one()
    assert reste == 0


def test_une_ligne_d_audit_encore_valide_n_est_pas_purgee(cx: Connection) -> None:
    valide = _audit_event(cx, retention_until=ANCRAGE + 10 * JOUR)
    purger_l_audit(cx, instant=ANCRAGE, parametres=None)  # type: ignore[arg-type]
    reste = cx.execute(
        text("SELECT count(*) FROM audit_event WHERE id = :e"), {"e": valide}
    ).scalar_one()
    assert reste == 1


# ---------------------------------------------------------------------------
#  6. Detection des jobs bloques
# ---------------------------------------------------------------------------


class _ParametresAlertes:
    WORKER_ABSENT_ALERT_MINUTES = 10
    JOB_STALLED_ALERT_MINUTES = 30


def _alerte_ouverte(cx: Connection, empreinte: str) -> int:
    return cx.execute(  # type: ignore[no-any-return]
        text("SELECT count(*) FROM operational_alert WHERE fingerprint = :f AND state = 'open'"),
        {"f": empreinte},
    ).scalar_one()


def test_un_job_sans_worker_depuis_dix_minutes_leve_une_alerte(cx: Connection) -> None:
    job = _job(cx, etat="queued", cree_le=ANCRAGE - dt.timedelta(minutes=20))
    detecter_les_jobs_bloques(cx, instant=ANCRAGE, parametres=_ParametresAlertes())  # type: ignore[arg-type]
    assert _alerte_ouverte(cx, f"job-sans-worker:{job}") == 1


def test_un_job_recemment_mis_en_file_ne_leve_aucune_alerte(cx: Connection) -> None:
    job = _job(cx, etat="queued", cree_le=ANCRAGE - dt.timedelta(minutes=1))
    detecter_les_jobs_bloques(cx, instant=ANCRAGE, parametres=_ParametresAlertes())  # type: ignore[arg-type]
    assert _alerte_ouverte(cx, f"job-sans-worker:{job}") == 0


def test_un_job_sans_progression_depuis_trente_minutes_leve_une_alerte(cx: Connection) -> None:
    job = _job(
        cx,
        etat="running",
        cree_le=ANCRAGE - dt.timedelta(hours=2),
        dernier_battement=ANCRAGE - dt.timedelta(minutes=45),
    )
    detecter_les_jobs_bloques(cx, instant=ANCRAGE, parametres=_ParametresAlertes())  # type: ignore[arg-type]
    assert _alerte_ouverte(cx, f"job-bloque:{job}") == 1


def test_un_job_en_cours_avec_un_battement_recent_ne_leve_aucune_alerte(cx: Connection) -> None:
    job = _job(
        cx,
        etat="running",
        cree_le=ANCRAGE - dt.timedelta(hours=2),
        dernier_battement=ANCRAGE - dt.timedelta(minutes=2),
    )
    detecter_les_jobs_bloques(cx, instant=ANCRAGE, parametres=_ParametresAlertes())  # type: ignore[arg-type]
    assert _alerte_ouverte(cx, f"job-bloque:{job}") == 0


# ---------------------------------------------------------------------------
#  7. Nettoyage des medias — delai de 7 jours, meme regle pour les 3 categories
# ---------------------------------------------------------------------------


@pytest.fixture
def parametres_minio(parametres_de_la_stack: Parametres) -> Parametres:
    return parametres_de_la_stack


def _deposer(parametres: Parametres, cle: str, contenu: bytes = b"contenu-de-test") -> None:
    try:
        deposer_l_objet(parametres, cle, contenu)
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")


def _nettoyer_minio(parametres: Parametres, *cles: str) -> None:
    client = client_s3(parametres)
    for cle in cles:
        with contextlib.suppress(Exception):
            client.delete_object(Bucket=parametres.MINIO_BUCKET, Key=cle)  # type: ignore[attr-defined]


def test_un_media_jamais_pret_depuis_plus_de_sept_jours_est_supprime(
    cx: Connection, parametres_minio: Parametres
) -> None:
    cle = f"{MARQUEUR}/jamais-pret-expire-{uuid.uuid4().hex}.jpg"
    _deposer(parametres_minio, cle)
    entite = _entite(cx, "MED1")
    personne = _personne(cx, f"{MARQUEUR.lower()}-mediarejete@exemple.test")
    media = _media(
        cx, entite=entite, acteur=personne, cle=cle, etat="rejected", cree_le=ANCRAGE - 8 * JOUR
    )
    try:
        nombre = nettoyer_les_medias(cx, instant=ANCRAGE, parametres=parametres_minio)
        assert nombre == 1
        etat = cx.execute(
            text("SELECT state FROM media_asset WHERE id = :m"), {"m": media}
        ).scalar_one()
        assert etat == "deleted"
        with pytest.raises(ObjetIntrouvable):
            lire_l_objet(parametres_minio, cle)
    finally:
        _nettoyer_minio(parametres_minio, cle)


def test_un_media_jamais_pret_recent_n_est_pas_supprime(
    cx: Connection, parametres_minio: Parametres
) -> None:
    cle = f"{MARQUEUR}/jamais-pret-recent-{uuid.uuid4().hex}.jpg"
    _deposer(parametres_minio, cle)
    entite = _entite(cx, "MED2")
    personne = _personne(cx, f"{MARQUEUR.lower()}-mediarecent@exemple.test")
    media = _media(cx, entite=entite, acteur=personne, cle=cle, etat="pending", cree_le=ANCRAGE)
    try:
        nettoyer_les_medias(cx, instant=ANCRAGE, parametres=parametres_minio)
        etat = cx.execute(
            text("SELECT state FROM media_asset WHERE id = :m"), {"m": media}
        ).scalar_one()
        assert etat == "pending"
    finally:
        _nettoyer_minio(parametres_minio, cle)


def test_un_media_pret_sans_reference_est_archive_comme_orphelin(
    cx: Connection, parametres_minio: Parametres
) -> None:
    cle = f"{MARQUEUR}/orphelin-detecte-{uuid.uuid4().hex}.jpg"
    entite = _entite(cx, "MED3")
    personne = _personne(cx, f"{MARQUEUR.lower()}-orphelin@exemple.test")
    media = _media(cx, entite=entite, acteur=personne, cle=cle, etat="ready", cree_le=ANCRAGE)
    nettoyer_les_medias(cx, instant=ANCRAGE, parametres=parametres_minio)
    archive = cx.execute(
        text("SELECT archived_at FROM media_asset WHERE id = :m"), {"m": media}
    ).scalar_one()
    assert archive is not None


def test_un_media_pret_avec_une_autorisation_active_n_est_jamais_archive(
    cx: Connection, parametres_minio: Parametres
) -> None:
    cle = f"{MARQUEUR}/reference-active-{uuid.uuid4().hex}.jpg"
    entite = _entite(cx, "MED4")
    personne = _personne(cx, f"{MARQUEUR.lower()}-reference@exemple.test")
    media = _media(cx, entite=entite, acteur=personne, cle=cle, etat="ready", cree_le=ANCRAGE)
    _autorisation_photo(cx, personne=personne, media=media)
    nettoyer_les_medias(cx, instant=ANCRAGE, parametres=parametres_minio)
    archive = cx.execute(
        text("SELECT archived_at FROM media_asset WHERE id = :m"), {"m": media}
    ).scalar_one()
    assert archive is None


def test_un_media_orphelin_depuis_plus_de_sept_jours_est_supprime_definitivement(
    cx: Connection, parametres_minio: Parametres
) -> None:
    cle = f"{MARQUEUR}/orphelin-expire-{uuid.uuid4().hex}.jpg"
    _deposer(parametres_minio, cle)
    entite = _entite(cx, "MED5")
    personne = _personne(cx, f"{MARQUEUR.lower()}-orphelinexpire@exemple.test")
    media = _media(
        cx,
        entite=entite,
        acteur=personne,
        cle=cle,
        etat="ready",
        cree_le=ANCRAGE - 30 * JOUR,
        archive_le=ANCRAGE - 8 * JOUR,
    )
    try:
        nombre = nettoyer_les_medias(cx, instant=ANCRAGE, parametres=parametres_minio)
        assert nombre == 1
        etat = cx.execute(
            text("SELECT state FROM media_asset WHERE id = :m"), {"m": media}
        ).scalar_one()
        assert etat == "deleted"
        with pytest.raises(ObjetIntrouvable):
            lire_l_objet(parametres_minio, cle)
    finally:
        _nettoyer_minio(parametres_minio, cle)


def test_un_media_orphelin_depuis_moins_de_sept_jours_n_est_pas_encore_supprime(
    cx: Connection, parametres_minio: Parametres
) -> None:
    cle = f"{MARQUEUR}/orphelin-recent-{uuid.uuid4().hex}.jpg"
    entite = _entite(cx, "MED6")
    personne = _personne(cx, f"{MARQUEUR.lower()}-orphelinrecent@exemple.test")
    media = _media(
        cx,
        entite=entite,
        acteur=personne,
        cle=cle,
        etat="ready",
        cree_le=ANCRAGE - 30 * JOUR,
        archive_le=ANCRAGE - 2 * JOUR,
    )
    nettoyer_les_medias(cx, instant=ANCRAGE, parametres=parametres_minio)
    etat = cx.execute(
        text("SELECT state FROM media_asset WHERE id = :m"), {"m": media}
    ).scalar_one()
    assert etat == "ready"


# ---------------------------------------------------------------------------
#  8. L'orchestrateur — un cycle complet, et le verrou vu depuis le cycle
# ---------------------------------------------------------------------------


def test_un_cycle_complet_cree_les_six_lignes_en_succes(
    cx: Connection, parametres_minio: Parametres
) -> None:
    resultat = executer_le_cycle(cx, instant=ANCRAGE, parametres=parametres_minio)
    assert len(resultat.taches) == 6
    assert resultat.nombre_d_echecs == 0
    noms = {t.task_name for t in resultat.taches}
    assert noms == {
        "expiration_liens_sessions",
        "evenements_passes",
        "anonymisation_apres_depart",
        "purge_audit",
        "detection_jobs_bloques",
        "nettoyage_medias",
    }


def test_une_tache_deja_verrouillee_est_sautee_sans_affecter_les_autres(
    cx: Connection, parametres_minio: Parametres
) -> None:
    #  Une AUTRE execution (un autre worker) tient deja le verrou de cette tache.
    commencer_l_execution(cx, task_name="purge_audit", instant=ANCRAGE)
    resultat = executer_le_cycle(cx, instant=ANCRAGE, parametres=parametres_minio)
    sautee = next(t for t in resultat.taches if t.task_name == "purge_audit")
    assert sautee.etat is None
    #  Les cinq autres ont bien tourne.
    assert sum(1 for t in resultat.taches if t.etat == "succeeded") == 5
