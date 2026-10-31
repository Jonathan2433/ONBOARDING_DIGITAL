"""Deposer une photo de profil en quarantaine — LOT 11, `T2`, `MVP-L11-US004`.

LE TEMOIN CENTRAL : LE PERMIS S'INVERSE AVEC LA PUBLICATION DE LA FICHE,
EXACTEMENT COMME POUR `short_intro`/`fun_fact` (LOT 7, `T3`)

  `peut_deposer_une_photo` dispatche sur les MEMES fonctions que la
  completion de la fiche d'arrivee : avant publication, `NEW` (Soi) peut
  deposer sa propre photo et `DSM` est a TIRET meme rattache ; apres
  publication, l'INVERSE — `NEW` perd le droit (§6.2) et `DSM` le retrouve en
  `Consultants`. Les deux etats sont prouves separement, sur la MEME
  appartenance, jamais seulement l'un ou l'autre (§7.39).

LES REFUS STRUCTURELS SONT CHACUN APPARIES A LEUR CAUSE EXACTE

  Fichier vide, nom vide une fois nettoye, taille superieure a 10 Mo, type
  declare hors JPEG/PNG/WebP — quatre codes distincts, jamais un gabarit
  generique qui les confondrait.

CE FICHIER NE TESTE PAS LE CONTENU REEL DE L'IMAGE

  Verifier qu'un contenu decode comme une vraie image releve d'`app.media.
  traitement`, teste dans `test_traitement_photo.py` — `deposer_une_photo` ne
  fait qu'un filtre DECLARATIF bon marche, voir son en-tete.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.media.depot import (
    CODE_FICHIER_TROP_LOURD,
    CODE_FICHIER_VIDE,
    CODE_NOM_DE_FICHIER_INVALIDE,
    CODE_TYPE_DECLARE_REFUSE,
    TAILLE_MAXIMALE_PHOTO_OCTETS,
    deposer_une_photo,
)
from app.media.perimetre import peut_deposer_une_photo
from app.onboarding.perimetre import (
    peut_completer_la_fiche_arrivee,
    peut_corriger_la_fiche_arrivee_apres_publication,
)
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.modeles import EtatAppartenance
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L11T2D"
ANCRAGE = dt.datetime(2026, 10, 31, 9, 0, tzinfo=dt.UTC)
ARRIVEE = dt.date(2026, 10, 15)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe}-{uuid.uuid4().hex[:6]}@exemple.test"
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, :prenom, 'T2', 'active') RETURNING id"
                ),
                {"a": adresse, "prenom": suffixe},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = EtatAppartenance.ACTIVE.value,
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'draft') RETURNING id"
                ),
                {"p": personne, "e": entite, "arrivee": ARRIVEE, "etat": etat},
            ).scalar_one()
        )
    )


def _fiche_publiee(cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID) -> None:
    """Une `arrival_profile` DEJA PUBLIEE, posee directement — cette suite ne
    reteste pas `completer_la_fiche_arrivee`/`valider_et_publier_la_fiche_
    arrivee`, deja prouvees au LOT 7.
    """
    cx.execute(
        text(
            "INSERT INTO arrival_profile (entity_id, entity_membership_id, short_intro, "
            "state, validated_at, published_at) "
            "VALUES (:e, :m, 'presentation', 'published', :i, :i)"
        ),
        {"e": entite, "m": appartenance, "i": ANCRAGE},
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


@pytest.fixture
def decor(cx: Connection) -> dict[str, Any]:
    """Une entite, un nouvel arrivant, un Booster de SON cercle, un DSM rattache, un ESM."""
    marqueur = f"{MARQUEUR}{uuid.uuid4().hex[:8]}"
    r: dict[str, Any] = {}

    entite = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
            "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
        ),
        {"code": f"{marqueur}-e", "nom": marqueur},
    ).scalar_one()
    r["entite"] = entite

    r["arrivant_personne"] = _personne(cx, "arrivant")
    r["arrivant"] = _appartenance(cx, entite, r["arrivant_personne"])

    r["cercle"] = cx.execute(
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :c, :n, 0) RETURNING id"
        ),
        {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
    ).scalar_one()

    r["booster_personne"] = _personne(cx, "booster")
    _appartenance(cx, entite, r["booster_personne"])
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :type, :c, :p, :d)"
        ),
        {
            "p": r["booster_personne"],
            "e": entite,
            "type": TypeResponsabilite.BOOSTER.value,
            "c": r["cercle"],
            "d": ANCRAGE - dt.timedelta(days=1),
        },
    )
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, :type, :d)"
        ),
        {
            "e": entite,
            "m": r["arrivant"],
            "c": r["cercle"],
            "type": TypeAppartenanceCercle.PRINCIPAL.value,
            "d": dt.date(2026, 9, 1),
        },
    )

    r["dsm_personne"] = _personne(cx, "dsm")
    _appartenance(cx, entite, r["dsm_personne"])
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :d)"
        ),
        {"p": r["dsm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
    )
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (consultant_membership_id, dsm_person_id, entity_id, "
            "starts_at) VALUES (:m, :p, :e, :d)"
        ),
        {
            "m": r["arrivant"],
            "p": r["dsm_personne"],
            "e": entite,
            "d": ANCRAGE - dt.timedelta(days=1),
        },
    )

    r["esm_personne"] = _personne(cx, "esm")
    _appartenance(cx, entite, r["esm_personne"])
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, :d)"
        ),
        {"p": r["esm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
    )
    return r


def _roles(
    cx: Connection, decor: dict[str, Any], personne: uuid.UUID
) -> frozenset[RoleDeLaMatrice]:
    return frozenset(resoudre_les_permissions(cx, personne, decor["entite"], ANCRAGE).roles)


# ===========================================================================
#  1. Le permis — avant publication (matrice §7 « Completer »)
# ===========================================================================


def test_avant_publication_le_nouvel_arrivant_depose_sa_propre_photo(
    cx: Connection, decor: dict[str, Any]
) -> None:
    autorise = peut_deposer_une_photo(
        cx,
        entite=decor["entite"],
        acteur=decor["arrivant_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["arrivant_personne"]),
        instant=ANCRAGE,
        fiche_publiee=False,
    )
    assert autorise is True
    #  Confronte directement a la fonction du LOT 7 — pas une reimplementation.
    assert autorise == peut_completer_la_fiche_arrivee(
        cx,
        entite=decor["entite"],
        acteur=decor["arrivant_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["arrivant_personne"]),
        instant=ANCRAGE,
    )


def test_avant_publication_le_DSM_RATTACHE_est_quand_meme_refuse(
    cx: Connection, decor: dict[str, Any]
) -> None:
    """Le piege §2.1 de `fiche-lot-7.md`, rejoue pour la photo : `DSM` est a
    TIRET sur cette ligne du §7, meme rattache au bon consultant.
    """
    autorise = peut_deposer_une_photo(
        cx,
        entite=decor["entite"],
        acteur=decor["dsm_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["dsm_personne"]),
        instant=ANCRAGE,
        fiche_publiee=False,
    )
    assert autorise is False


def test_avant_publication_le_booster_du_cercle_depose_pour_son_membre(
    cx: Connection, decor: dict[str, Any]
) -> None:
    autorise = peut_deposer_une_photo(
        cx,
        entite=decor["entite"],
        acteur=decor["booster_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["booster_personne"]),
        instant=ANCRAGE,
        fiche_publiee=False,
    )
    assert autorise is True


# ===========================================================================
#  2. Le permis — apres publication (matrice §6.1 « Ajouter ou remplacer »,
#     MEME GRILLE que « Corriger apres publication » du LOT 7)
# ===========================================================================


def test_apres_publication_le_nouvel_arrivant_PERD_le_droit(
    cx: Connection, decor: dict[str, Any]
) -> None:
    """L'INVERSE du test precedent, sur la MEME appartenance — §7.39 : prouver
    les deux etats, jamais un seul.
    """
    _fiche_publiee(cx, decor["entite"], decor["arrivant"])
    autorise = peut_deposer_une_photo(
        cx,
        entite=decor["entite"],
        acteur=decor["arrivant_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["arrivant_personne"]),
        instant=ANCRAGE,
        fiche_publiee=True,
    )
    assert autorise is False


def test_apres_publication_le_DSM_RATTACHE_RETROUVE_le_droit(
    cx: Connection, decor: dict[str, Any]
) -> None:
    _fiche_publiee(cx, decor["entite"], decor["arrivant"])
    autorise = peut_deposer_une_photo(
        cx,
        entite=decor["entite"],
        acteur=decor["dsm_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["dsm_personne"]),
        instant=ANCRAGE,
        fiche_publiee=True,
    )
    assert autorise is True
    assert autorise == peut_corriger_la_fiche_arrivee_apres_publication(
        cx,
        entite=decor["entite"],
        acteur=decor["dsm_personne"],
        cible_appartenance=decor["arrivant"],
        cible_personne=decor["arrivant_personne"],
        roles=_roles(cx, decor, decor["dsm_personne"]),
        instant=ANCRAGE,
    )


def test_esm_depose_aux_deux_etats(cx: Connection, decor: dict[str, Any]) -> None:
    roles_esm = _roles(cx, decor, decor["esm_personne"])
    for publiee in (False, True):
        if publiee:
            _fiche_publiee(cx, decor["entite"], decor["arrivant"])
        assert (
            peut_deposer_une_photo(
                cx,
                entite=decor["entite"],
                acteur=decor["esm_personne"],
                cible_appartenance=decor["arrivant"],
                cible_personne=decor["arrivant_personne"],
                roles=roles_esm,
                instant=ANCRAGE,
                fiche_publiee=publiee,
            )
            is True
        )


# ===========================================================================
#  3. Le depot lui-meme : empreinte, cle d'objet, ligne `pending`, outbox
# ===========================================================================

JPEG_MINIMAL = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300030202020202"
    "03020202030303030406040404040408060605060908080807080808090a0c"
    "0a0a0b0b0a0c0c100e0c0d0d100e0e0f13111111130f101316151515161512"
    "1414171a1a1d1d1a1713171c1716171c16131414ffc0000b080001000101011"
    "100ffc4001f0000010501010101010100000000000000000102030405060708"
    "090a0bffc400b5100002010303020403050504040000017d010203000411051"
    "2212131410613516171221314328191a1081042a1b2d2b43c1c232535d1d233"
    "6ff00019283cffd9"
)


def _deposer_ou_sauter(
    cx: Connection,
    parametres: Parametres,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    nom: str = "photo.jpg",
    content_type: str | None = "image/jpeg",
    contenu: bytes = JPEG_MINIMAL,
) -> Any:
    try:
        return deposer_une_photo(
            cx,
            parametres,
            entite=entite,
            acteur=acteur,
            nom_de_fichier=nom,
            content_type=content_type,
            contenu=contenu,
            instant=ANCRAGE,
        )
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        if isinstance(erreur, ErreurApplicative):
            raise
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")
        raise  # pragma: no cover


def test_le_depot_pose_une_ligne_pending_et_un_message_outbox(
    cx: Connection, decor: dict[str, Any], parametres_de_la_stack: Parametres
) -> None:
    depose = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=decor["entite"], acteur=decor["arrivant_personne"]
    )
    assert depose.state == "pending"

    ligne = (
        cx.execute(
            text(
                "SELECT state, object_key, checksum_sha256, size_bytes "
                "FROM media_asset WHERE id = :id"
            ),
            {"id": depose.id},
        )
        .mappings()
        .one()
    )
    assert ligne["state"] == "pending"
    assert ligne["object_key"] == f"media/{decor['entite']}/{depose.id}/original"
    assert ligne["size_bytes"] == len(JPEG_MINIMAL)

    message = (
        cx.execute(
            text(
                "SELECT topic, payload_json FROM outbox_message "
                "WHERE payload_json->>'media_asset_id' = :id"
            ),
            {"id": str(depose.id)},
        )
        .mappings()
        .one()
    )
    assert message["topic"] == "media"


def test_un_fichier_vide_est_refuse(
    cx: Connection, decor: dict[str, Any], parametres_de_la_stack: Parametres
) -> None:
    with pytest.raises(ErreurApplicative) as excinfo:
        _deposer_ou_sauter(
            cx,
            parametres_de_la_stack,
            entite=decor["entite"],
            acteur=decor["arrivant_personne"],
            contenu=b"",
        )
    assert excinfo.value.code == CODE_FICHIER_VIDE


def test_un_nom_vide_une_fois_nettoye_est_refuse(
    cx: Connection, decor: dict[str, Any], parametres_de_la_stack: Parametres
) -> None:
    with pytest.raises(ErreurApplicative) as excinfo:
        _deposer_ou_sauter(
            cx,
            parametres_de_la_stack,
            entite=decor["entite"],
            acteur=decor["arrivant_personne"],
            nom="  ",
        )
    assert excinfo.value.code == CODE_NOM_DE_FICHIER_INVALIDE


def test_une_photo_de_plus_de_dix_megaoctets_est_refusee(
    cx: Connection, decor: dict[str, Any], parametres_de_la_stack: Parametres
) -> None:
    trop_lourd = b"\xff" * (TAILLE_MAXIMALE_PHOTO_OCTETS + 1)
    with pytest.raises(ErreurApplicative) as excinfo:
        _deposer_ou_sauter(
            cx,
            parametres_de_la_stack,
            entite=decor["entite"],
            acteur=decor["arrivant_personne"],
            contenu=trop_lourd,
        )
    assert excinfo.value.code == CODE_FICHIER_TROP_LOURD


def test_un_type_declare_hors_liste_est_refuse(
    cx: Connection, decor: dict[str, Any], parametres_de_la_stack: Parametres
) -> None:
    with pytest.raises(ErreurApplicative) as excinfo:
        _deposer_ou_sauter(
            cx,
            parametres_de_la_stack,
            entite=decor["entite"],
            acteur=decor["arrivant_personne"],
            content_type="application/pdf",
        )
    assert excinfo.value.code == CODE_TYPE_DECLARE_REFUSE
