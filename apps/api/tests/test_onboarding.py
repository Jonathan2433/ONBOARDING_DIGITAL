"""Les huit tables du lot — LOT 7, `T1`, modele §12.1 et §13.1 a §13.7.

CE QUE CE FICHIER PROUVE, ET CE QU'IL NE PEUT PAS PROUVER

  Il prouve ce que la BASE refuse : les six enumerations, les six chemins de
  fuite fermes par une cle composite (voir `test_isolation.py`, dont
  `test_les_cles_composites_sont_toutes_couvertes` exige que chacun soit
  couvert ICI), les deux clefs simples legitimement nullables et la structure
  du §13.2. Il ne pose ni service ni route : T1 est le socle.

CHAQUE REFUS A SON TEMOIN, ET CHAQUE CLE COMPOSITE A SON COUPLE

  Un test qui n'exigerait que l'echec serait satisfait par une table
  ininsertable. Chaque refus est donc double d'une insertion qui REUSSIT et ne
  differe que par LA valeur en cause.
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
from app.onboarding import (
    ETATS_DU_MODELE,
    ETATS_FICHE_ARRIVEE,
    ETATS_INSTANCE,
    ETATS_TACHE_INSTANCE,
    PORTEES_DU_MODELE,
    TYPES_EVENEMENT_TACHE,
)
from app.shared.database import moteur

MARQUEUR = "L7T1"
EMPREINTE = "b" * 64


# ============================================================================
#  1. Ce que le corpus ECRIT, verifie sans base
# ============================================================================
def test_les_quatre_etats_de_fiche_d_arrivee_du_12_1_sont_declares() -> None:
    assert set(ETATS_FICHE_ARRIVEE) == {"draft", "validated", "published", "archived"}


def test_les_quatre_portees_du_13_2_sont_declarees() -> None:
    assert set(PORTEES_DU_MODELE) == {"GLOBAL", "ENTITY", "DSM", "CIRCLE"}


def test_les_trois_etats_de_modele_du_13_2_sont_declares() -> None:
    assert set(ETATS_DU_MODELE) == {"draft", "active", "archived"}


def test_les_quatre_etats_d_instance_du_13_5_sont_declares() -> None:
    assert set(ETATS_INSTANCE) == {"active", "completed", "archived", "replaced"}


def test_les_quatre_etats_de_tache_d_instance_du_13_6_sont_declares() -> None:
    assert set(ETATS_TACHE_INSTANCE) == {"todo", "completed", "reopened", "cancelled"}


def test_les_six_evenements_du_13_7_sont_declares() -> None:
    """§13.7, en prose : affectation, completion, annulation, reouverture,

    conservation lors d'un remplacement, annulation lors d'un changement de
    parcours — six, jamais enumeres en colonnes, voir le module.
    """
    assert set(TYPES_EVENEMENT_TACHE) == {
        "ASSIGNED",
        "COMPLETED",
        "CANCELLED",
        "REOPENED",
        "RETAINED_ON_REPLACEMENT",
        "CANCELLED_ON_REPLACEMENT",
    }


# ============================================================================
#  2. Fixtures et fabriques
# ============================================================================
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
            "VALUES (:a, :a, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"a": adresse},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, membership_state, "
            "professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": _personne(cx, adresse), "e": entite},
    ).scalar_one()


def _media(cx: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    personne = _personne(cx, adresse)
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256) "
            "VALUES (:e, :p, 'pending', 'image', 'photo.jpg', :cle, 'image/jpeg', 1024, "
            ":empreinte) RETURNING id"
        ),
        {
            "e": entite,
            "p": personne,
            "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            "empreinte": EMPREINTE,
        },
    ).scalar_one()


def _fiche_arrivee(
    cx: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    *,
    photo: uuid.UUID | None = None,
    state: str = "draft",
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO arrival_profile (entity_id, entity_membership_id, photo_media_id, state, "
            "short_intro) VALUES (:e, :m, :photo, :state, :intro) RETURNING id"
        ),
        {
            "e": entite,
            "m": appartenance,
            "photo": photo,
            "state": state,
            "intro": None if state == "draft" else "Presentation courte",
        },
    ).scalar_one()


def _tache_reference(cx: Connection, entite: uuid.UUID | None, code: str) -> uuid.UUID:
    #  DEUX parametres distincts, jamais un seul reutilise : `code` est
    #  `character varying(64)`, `title` est `text` — §7.25, rejoue une
    #  cinquieme fois si les deux colonnes partagent `:c`.
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_task_reference (entity_id, code, title) "
            "VALUES (:e, :c, :t) RETURNING id"
        ),
        {"e": entite, "c": code, "t": code},
    ).scalar_one()


def _modele(
    cx: Connection,
    *,
    entite: uuid.UUID | None,
    scope_type: str,
    target_status: str = "mission",
    scope_person: uuid.UUID | None = None,
    scope_circle: uuid.UUID | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_template (entity_id, name, target_status, scope_type, "
            "scope_person_id, scope_circle_id) "
            "VALUES (:e, 'Modele', :ts, :st, :sp, :sc) RETURNING id"
        ),
        {
            "e": entite,
            "ts": target_status,
            "st": scope_type,
            "sp": scope_person,
            "sc": scope_circle,
        },
    ).scalar_one()


def _version(
    cx: Connection, modele: uuid.UUID, *, numero: int = 1, state: str = "active"
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_template_version (template_id, version_number, state) "
            "VALUES (:t, :n, :s) RETURNING id"
        ),
        {"t": modele, "n": numero, "s": state},
    ).scalar_one()


def _instance(
    cx: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    version: uuid.UUID,
    *,
    state: str = "active",
    replaced_by: uuid.UUID | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_instance (entity_id, entity_membership_id, "
            "template_version_id, reference_date, state, replaced_by_instance_id) "
            "VALUES (:e, :m, :v, '2026-01-01', :s, :r) RETURNING id"
        ),
        {"e": entite, "m": appartenance, "v": version, "s": state, "r": replaced_by},
    ).scalar_one()


def _tache_instance(
    cx: Connection,
    entite: uuid.UUID,
    instance: uuid.UUID,
    tache_reference: uuid.UUID,
    *,
    state: str = "todo",
    reopened_at: dt.datetime | None = None,
    reopen_reason: str | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_instance_task (entity_id, onboarding_instance_id, "
            "task_reference_id, title_snapshot, required, due_at, state, reopened_at, "
            "reopen_reason) "
            "VALUES (:e, :i, :t, 'Tache', true, now(), :s, :ra, :rr) RETURNING id"
        ),
        {
            "e": entite,
            "i": instance,
            "t": tache_reference,
            "s": state,
            "ra": reopened_at,
            "rr": reopen_reason,
        },
    ).scalar_one()


def _deux_entites(cx: Connection) -> tuple[uuid.UUID, uuid.UUID]:
    return _entite(cx, "ICI"), _entite(cx, "AIL")


# ============================================================================
#  3. Les six chemins de fuite fermes par une cle composite — voir
#     `test_isolation.py::test_les_cles_composites_sont_toutes_couvertes`
# ============================================================================
@pytest.mark.integration
def test_une_fiche_ne_peut_pas_pointer_une_appartenance_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _deux_entites(cx)
    appartenance_etrangere = _appartenance(cx, ailleurs, "f1@x.test")
    with pytest.raises(IntegrityError, match="fk_arrival_profile_entity_membership"):
        _fiche_arrivee(cx, ici, appartenance_etrangere)


@pytest.mark.integration
def test_TEMOIN_une_fiche_pointe_une_appartenance_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "TF1")
    appartenance = _appartenance(cx, entite, "f2@x.test")
    assert _fiche_arrivee(cx, entite, appartenance) is not None


@pytest.mark.integration
def test_une_fiche_ne_peut_pas_pointer_une_photo_d_une_AUTRE_entite(cx: Connection) -> None:
    ici, ailleurs = _deux_entites(cx)
    appartenance = _appartenance(cx, ici, "f3@x.test")
    photo_etrangere = _media(cx, ailleurs, "f4@x.test")
    with pytest.raises(IntegrityError, match="fk_arrival_profile_media_asset"):
        _fiche_arrivee(cx, ici, appartenance, photo=photo_etrangere)


@pytest.mark.integration
def test_TEMOIN_une_fiche_pointe_une_photo_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "TF2")
    appartenance = _appartenance(cx, entite, "f5@x.test")
    photo = _media(cx, entite, "f6@x.test")
    assert _fiche_arrivee(cx, entite, appartenance, photo=photo) is not None


@pytest.mark.integration
def test_une_instance_ne_peut_pas_pointer_une_appartenance_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _deux_entites(cx)
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance_etrangere = _appartenance(cx, ailleurs, "i1@x.test")
    with pytest.raises(IntegrityError, match="fk_onboarding_instance_entity_membership"):
        _instance(cx, ici, appartenance_etrangere, version)


@pytest.mark.integration
def test_TEMOIN_une_instance_pointe_une_appartenance_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "TI1")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "i2@x.test")
    assert _instance(cx, entite, appartenance, version) is not None


@pytest.mark.integration
def test_une_instance_ne_peut_pas_etre_remplacee_par_une_instance_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _deux_entites(cx)
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance_etrangere = _appartenance(cx, ailleurs, "i3@x.test")
    remplacante_etrangere = _instance(cx, ailleurs, appartenance_etrangere, version)
    appartenance = _appartenance(cx, ici, "i4@x.test")
    with pytest.raises(
        IntegrityError, match="fk_onboarding_instance_onboarding_instance_replacement"
    ):
        _instance(
            cx, ici, appartenance, version, state="replaced", replaced_by=remplacante_etrangere
        )


@pytest.mark.integration
def test_TEMOIN_une_instance_est_remplacee_par_une_instance_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "TI2")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "i5@x.test")
    remplacante = _instance(cx, entite, appartenance, version)
    assert (
        _instance(cx, entite, appartenance, version, state="replaced", replaced_by=remplacante)
        is not None
    )


@pytest.mark.integration
def test_une_tache_d_instance_ne_peut_pas_pointer_une_instance_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _deux_entites(cx)
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance_etrangere = _appartenance(cx, ailleurs, "t1@x.test")
    instance_etrangere = _instance(cx, ailleurs, appartenance_etrangere, version)
    tache = _tache_reference(cx, None, "T1")
    with pytest.raises(IntegrityError, match="fk_onboarding_instance_task_onboarding_instance"):
        _tache_instance(cx, ici, instance_etrangere, tache)


@pytest.mark.integration
def test_TEMOIN_une_tache_d_instance_pointe_une_instance_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "TT1")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "t2@x.test")
    instance = _instance(cx, entite, appartenance, version)
    tache = _tache_reference(cx, None, "T2")
    assert _tache_instance(cx, entite, instance, tache) is not None


@pytest.mark.integration
def test_un_evenement_ne_peut_pas_pointer_une_tache_d_instance_d_une_AUTRE_entite(
    cx: Connection,
) -> None:
    ici, ailleurs = _deux_entites(cx)
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance_etrangere = _appartenance(cx, ailleurs, "e1@x.test")
    instance_etrangere = _instance(cx, ailleurs, appartenance_etrangere, version)
    tache = _tache_reference(cx, None, "T3")
    tache_instance_etrangere = _tache_instance(cx, ailleurs, instance_etrangere, tache)
    with pytest.raises(IntegrityError, match="fk_onboarding_task_event_onboarding_instance_task"):
        cx.execute(
            text(
                "INSERT INTO onboarding_task_event (entity_id, onboarding_instance_task_id, "
                "event_type) VALUES (:e, :t, 'ASSIGNED')"
            ),
            {"e": ici, "t": tache_instance_etrangere},
        )


@pytest.mark.integration
def test_TEMOIN_un_evenement_pointe_une_tache_d_instance_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "TE1")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "e2@x.test")
    instance = _instance(cx, entite, appartenance, version)
    tache = _tache_reference(cx, None, "T4")
    tache_instance = _tache_instance(cx, entite, instance, tache)
    resultat = cx.execute(
        text(
            "INSERT INTO onboarding_task_event (entity_id, onboarding_instance_task_id, "
            "event_type) VALUES (:e, :t, 'ASSIGNED') RETURNING id"
        ),
        {"e": entite, "t": tache_instance},
    ).scalar_one()
    assert resultat is not None


# ============================================================================
#  4. Deux cles SIMPLES legitimement nullables, et un temoin qu'elles marchent
#     quand meme — voir `verifier-isolation.py`, "simples legitimes"
# ============================================================================
@pytest.mark.integration
def test_une_tache_d_instance_PEUT_reutiliser_une_tache_de_reference_GLOBALE(
    cx: Connection,
) -> None:
    entite = _entite(cx, "GL1")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "g1@x.test")
    instance = _instance(cx, entite, appartenance, version)
    tache_globale = _tache_reference(cx, None, "GLOB1")
    assert _tache_instance(cx, entite, instance, tache_globale) is not None


@pytest.mark.integration
def test_un_modele_CIRCLE_PEUT_pointer_un_cercle_de_SON_entite(cx: Connection) -> None:
    entite = _entite(cx, "CI1")
    cercle = cx.execute(
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, 'C', 'C', 1) RETURNING id"
        ),
        {"e": entite},
    ).scalar_one()
    assert _modele(cx, entite=entite, scope_type="CIRCLE", scope_circle=cercle) is not None


# ============================================================================
#  5. La structure du §13.2 — une implication par portee
# ============================================================================
@pytest.mark.integration
@pytest.mark.parametrize("scope_type", ["ENTITY", "DSM", "CIRCLE"])
def test_un_modele_NON_global_SANS_entite_est_refuse(cx: Connection, scope_type: str) -> None:
    with pytest.raises(IntegrityError, match="colonnes_de_portee_selon_scope_type"):
        _modele(cx, entite=None, scope_type=scope_type)


@pytest.mark.integration
def test_un_modele_GLOBAL_AVEC_une_entite_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "GX1")
    with pytest.raises(IntegrityError, match="colonnes_de_portee_selon_scope_type"):
        _modele(cx, entite=entite, scope_type="GLOBAL")


@pytest.mark.integration
def test_TEMOIN_un_modele_GLOBAL_se_cree(cx: Connection) -> None:
    assert _modele(cx, entite=None, scope_type="GLOBAL") is not None


# ============================================================================
#  6. Deux autres implications, ecrites en toutes lettres dans le corpus
# ============================================================================
@pytest.mark.integration
def test_une_fiche_HORS_BROUILLON_SANS_presentation_est_refusee(cx: Connection) -> None:
    """§12.1 : « `short_intro` | Obligatoire avant validation »."""
    entite = _entite(cx, "SI1")
    appartenance = _appartenance(cx, entite, "s1@x.test")
    with pytest.raises(IntegrityError, match="short_intro_requis_hors_brouillon"):
        cx.execute(
            text(
                "INSERT INTO arrival_profile (entity_id, entity_membership_id, state) "
                "VALUES (:e, :m, 'validated')"
            ),
            {"e": entite, "m": appartenance},
        )


@pytest.mark.integration
def test_une_reouverture_SANS_motif_est_refusee(cx: Connection) -> None:
    """Matrice §8.3, a la lettre : « La reouverture EXIGE un motif »."""
    entite = _entite(cx, "RM1")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "r1@x.test")
    instance = _instance(cx, entite, appartenance, version)
    tache = _tache_reference(cx, None, "RM1")
    with pytest.raises(IntegrityError, match="motif_requis_a_la_reouverture"):
        _tache_instance(
            cx, entite, instance, tache, state="reopened", reopened_at=dt.datetime.now(dt.UTC)
        )


@pytest.mark.integration
def test_TEMOIN_une_reouverture_AVEC_motif_reussit(cx: Connection) -> None:
    entite = _entite(cx, "RM2")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "r2@x.test")
    instance = _instance(cx, entite, appartenance, version)
    tache = _tache_reference(cx, None, "RM2")
    assert (
        _tache_instance(
            cx,
            entite,
            instance,
            tache,
            state="reopened",
            reopened_at=dt.datetime.now(dt.UTC),
            reopen_reason="Erreur de saisie",
        )
        is not None
    )


# ============================================================================
#  7. Les deux unicites du catalogue de taches — §13.1, « unique DANS SON
#     PERIMETRE ». Deux index partiels, un par perimetre.
# ============================================================================
@pytest.mark.integration
def test_deux_taches_GLOBALES_de_meme_code_sont_refusees(cx: Connection) -> None:
    _tache_reference(cx, None, "DOUBLON")
    with pytest.raises(
        IntegrityError, match="uq_onboarding_task_reference_code_globale_non_archive"
    ):
        _tache_reference(cx, None, "DOUBLON")


@pytest.mark.integration
def test_deux_taches_de_MEME_entite_et_meme_code_sont_refusees(cx: Connection) -> None:
    entite = _entite(cx, "DB1")
    _tache_reference(cx, entite, "DOUBLON")
    with pytest.raises(
        IntegrityError, match="uq_onboarding_task_reference_entity_code_non_archive"
    ):
        _tache_reference(cx, entite, "DOUBLON")


@pytest.mark.integration
def test_TEMOIN_le_MEME_code_est_accepte_dans_DEUX_entites_differentes(cx: Connection) -> None:
    """Le perimetre discrimine : « unique » ne veut pas dire « unique au monde »."""
    ici, ailleurs = _deux_entites(cx)
    assert _tache_reference(cx, ici, "PARTAGE") is not None
    assert _tache_reference(cx, ailleurs, "PARTAGE") is not None


@pytest.mark.integration
def test_TEMOIN_une_tache_GLOBALE_et_une_tache_D_ENTITE_peuvent_partager_un_code(
    cx: Connection,
) -> None:
    entite = _entite(cx, "PG1")
    assert _tache_reference(cx, None, "MIXTE") is not None
    assert _tache_reference(cx, entite, "MIXTE") is not None


# ============================================================================
#  8. « Une seule instance active par appartenance » — §13.5
# ============================================================================
@pytest.mark.integration
def test_une_SECONDE_instance_active_pour_la_MEME_appartenance_est_refusee(cx: Connection) -> None:
    entite = _entite(cx, "SA1")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "sa1@x.test")
    _instance(cx, entite, appartenance, version)
    with pytest.raises(IntegrityError, match="uq_onboarding_instance_membership_active"):
        _instance(cx, entite, appartenance, version)


@pytest.mark.integration
def test_TEMOIN_une_instance_ARCHIVEE_n_empeche_pas_une_nouvelle_instance_active(
    cx: Connection,
) -> None:
    entite = _entite(cx, "SA2")
    modele = _modele(cx, entite=None, scope_type="GLOBAL")
    version = _version(cx, modele)
    appartenance = _appartenance(cx, entite, "sa2@x.test")
    _instance(cx, entite, appartenance, version, state="archived")
    assert _instance(cx, entite, appartenance, version) is not None
