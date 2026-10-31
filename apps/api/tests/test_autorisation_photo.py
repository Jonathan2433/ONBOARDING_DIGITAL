"""Accorder et retirer l'autorisation d'affichage d'une photo — LOT 11, `T2`.

Modele §12.2, matrice §6.1, `MVP-L11-US005`.

LE RESIDU DU LOT 5 EST PROUVE ICI : DEUX AUTORISATIONS ACTIVES COEXISTENT

  `test_accorder_une_nouvelle_autorisation_NE_RETIRE_PAS_l_ancienne` est le
  temoin direct de la decision prise par `app.media.autorisation` (voir son
  en-tete) : apres un second octroi, LES DEUX lignes restent `withdrawn_at
  IS NULL` — rien n'a retire la premiere.

`DSM` EST A TIRET SUR CETTE LIGNE DU §6.1, A LA DIFFERENCE DU DEPOT

  Contrairement a `peut_deposer_une_photo` (ou `DSM` retrouve `Consultants`
  apres publication de la fiche), `peut_gerer_l_autorisation_photo` refuse
  TOUJOURS `DSM`, quel que soit l'etat — `test_le_DSM_est_refuse_par_http_
  sur_l_autorisation` le prouve.

LE DECOR EST COMMITTE, PAS ANNULE — MEME DISCIPLINE QUE `test_fiche_
arrivee.py`/`test_validation_de_la_fiche_arrivee.py` (LOT 7)

  Les quatre routes de cette sous-etape ouvrent leur PROPRE connexion ; une
  decor en transaction non committee leur serait invisible. Le nettoyage, en
  fin de fixture, supprime tout ce que le marqueur a cree — meme motif que
  `make residu-check` : aucune ligne ne doit survivre au fichier.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.csrf import EN_TETE_JETON, jeton_pour
from app.auth.sessions import empreinte_de_session, ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.media.autorisation import (
    CODE_MEDIA_INTROUVABLE,
    CODE_MEDIA_PAS_PRET,
    accorder_l_autorisation_photo,
    retirer_l_autorisation_photo,
)
from app.media.modeles import SourceAutorisationPhoto
from app.media.perimetre import peut_gerer_l_autorisation_photo
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.modeles import EtatAppartenance
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_PHOTO = "/api/v1/entities/{code}/people/{appartenance}/photo"
CHEMIN_DROITS = CHEMIN_PHOTO + "/droits"
CHEMIN_AUTORISATION = CHEMIN_PHOTO + "/autorisation"
CHEMIN_RETRAIT = CHEMIN_AUTORISATION + "/retrait"
CHEMIN_ETAT_MEDIA = "/api/v1/entities/{code}/media/{media}/etat"

ANCRAGE = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
ARRIVEE = dt.date(2026, 10, 15)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


def _personne(cx: Connection, marqueur: str, suffixe: str) -> uuid.UUID:
    adresse = f"{marqueur}-{suffixe}@exemple.test"
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


def _media(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, etat: str = "ready"
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, "
                    "media_type, original_filename, object_key, mime_declared, size_bytes, "
                    "checksum_sha256, created_at, updated_at) "
                    "VALUES (:e, :p, :etat, 'image', 'photo.jpg', :cle, 'image/jpeg', "
                    "1, :empreinte, :i, :i) RETURNING id"
                ),
                {
                    "e": entite,
                    "p": acteur,
                    "etat": etat,
                    "cle": f"test/{uuid.uuid4().hex}",
                    "empreinte": "b" * 64,
                    "i": ANCRAGE,
                },
            ).scalar_one()
        )
    )


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx,
            personne=personne,
            instant=dt.datetime.now(tz=dt.UTC),
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
    return jeton


def _get(parametres: Parametres, chemin: str, jeton: str) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


def _post(
    parametres: Parametres, chemin: str, jeton: str, corps: dict[str, Any] | None = None
) -> Any:
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    jeton_csrf = jeton_pour(empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY)
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
        return client.post(
            chemin,
            json=corps or {},
            headers={"Origin": ORIGINE_DE_TEST, EN_TETE_JETON: jeton_csrf},
        )


def _post_sans_csrf(parametres: Parametres, chemin: str, jeton: str, corps: dict[str, Any]) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.post(chemin, json=corps)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite, une cible, un Booster de SON cercle, un DSM rattache, un ESM — COMMITTE."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"l11t2a{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres}

    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-e", "nom": marqueur},
        ).scalar_one()
        r["entite"] = entite
        r["code"] = f"{marqueur}-e"

        r["cible_personne"] = _personne(cx, marqueur, "cible")
        r["cible"] = _appartenance(cx, entite, r["cible_personne"])

        r["cercle"] = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
        ).scalar_one()

        r["booster_personne"] = _personne(cx, marqueur, "booster")
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
                "d": ANCRAGE,
            },
        )
        cx.execute(
            text(
                "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
                "membership_type, starts_at) VALUES (:e, :m, :c, :type, :d)"
            ),
            {
                "e": entite,
                "m": r["cible"],
                "c": r["cercle"],
                "type": TypeAppartenanceCercle.PRINCIPAL.value,
                "d": dt.date(2026, 9, 1),
            },
        )

        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(cx, entite, r["dsm_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'DSM', :p, :d)"
            ),
            {"p": r["dsm_personne"], "e": entite, "d": ANCRAGE},
        )
        cx.execute(
            text(
                "INSERT INTO dsm_assignment (consultant_membership_id, dsm_person_id, "
                "entity_id, starts_at) VALUES (:m, :p, :e, :d)"
            ),
            {"m": r["cible"], "p": r["dsm_personne"], "e": entite, "d": ANCRAGE},
        )

        r["esm_personne"] = _personne(cx, marqueur, "esm")
        _appartenance(cx, entite, r["esm_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'ESM', :p, :d)"
            ),
            {"p": r["esm_personne"], "e": entite, "d": ANCRAGE},
        )

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM photo_authorization WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM media_asset WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM async_job WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM dsm_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM person WHERE email LIKE :motif_personne",
            "DELETE FROM entity WHERE code LIKE :motif",
        ):
            menage.execute(
                text(requete), {"motif": f"{marqueur}%", "motif_personne": f"{marqueur}%"}
            )


def _roles(
    parametres: Parametres, decor: dict[str, Any], personne: uuid.UUID
) -> frozenset[RoleDeLaMatrice]:
    with moteur(parametres).connect() as cx:
        return frozenset(resoudre_les_permissions(cx, personne, decor["entite"], ANCRAGE).roles)


# ===========================================================================
#  1. Le permis — `peut_gerer_l_autorisation_photo`
# ===========================================================================


def test_la_cible_gere_toujours_sa_propre_autorisation(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).connect() as cx:
        assert (
            peut_gerer_l_autorisation_photo(
                cx,
                entite=decor["entite"],
                acteur=decor["cible_personne"],
                cible_appartenance=decor["cible"],
                cible_personne=decor["cible_personne"],
                roles=_roles(parametres, decor, decor["cible_personne"]),
                instant=ANCRAGE,
            )
            is True
        )


def test_le_DSM_est_TOUJOURS_refuse(decor: dict[str, Any]) -> None:
    """A la difference du depot (`test_depot_photo.py`), `DSM` reste a tiret ICI, meme rattache."""
    parametres = decor["parametres"]
    with moteur(parametres).connect() as cx:
        assert (
            peut_gerer_l_autorisation_photo(
                cx,
                entite=decor["entite"],
                acteur=decor["dsm_personne"],
                cible_appartenance=decor["cible"],
                cible_personne=decor["cible_personne"],
                roles=_roles(parametres, decor, decor["dsm_personne"]),
                instant=ANCRAGE,
            )
            is False
        )


def test_le_booster_du_cercle_gere_en_soutien(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).connect() as cx:
        assert (
            peut_gerer_l_autorisation_photo(
                cx,
                entite=decor["entite"],
                acteur=decor["booster_personne"],
                cible_appartenance=decor["cible"],
                cible_personne=decor["cible_personne"],
                roles=_roles(parametres, decor, decor["booster_personne"]),
                instant=ANCRAGE,
            )
            is True
        )


# ===========================================================================
#  2. Le service — octroi, retrait, et le residu du LOT 5 tranche
# ===========================================================================


def test_accorder_exige_un_media_READY(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        media_pending = _media(
            cx, entite=decor["entite"], acteur=decor["cible_personne"], etat="pending"
        )
        with pytest.raises(ErreurApplicative) as excinfo:
            accorder_l_autorisation_photo(
                cx,
                entite=decor["entite"],
                person_id=decor["cible_personne"],
                media_asset_id=media_pending,
                source=SourceAutorisationPhoto.SELF_SERVICE.value,
                acteur=decor["cible_personne"],
                instant=ANCRAGE,
            )
        assert excinfo.value.code == CODE_MEDIA_PAS_PRET


def test_accorder_sur_un_media_d_une_autre_entite_est_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        #  Code PREFIXE PAR LE MEME MARQUEUR que le reste du decor : le
        #  nettoyage generique de la fixture (`code LIKE :motif`) l'emporte
        #  avec elle, media_asset compris — jamais un second geste de menage.
        autre_entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, "
                "timezone) VALUES (:code, 'autre', 'Lille', 'FR', 'active', "
                "'Europe/Paris') RETURNING id"
            ),
            {"code": f"{decor['code'][:-2]}-autre"},
        ).scalar_one()
        media_ailleurs = _media(cx, entite=autre_entite, acteur=decor["cible_personne"])
        with pytest.raises(ErreurApplicative) as excinfo:
            accorder_l_autorisation_photo(
                cx,
                entite=decor["entite"],
                person_id=decor["cible_personne"],
                media_asset_id=media_ailleurs,
                source=SourceAutorisationPhoto.SELF_SERVICE.value,
                acteur=decor["cible_personne"],
                instant=ANCRAGE,
            )
        assert excinfo.value.code == CODE_MEDIA_INTROUVABLE


def test_accorder_une_nouvelle_autorisation_NE_RETIRE_PAS_l_ancienne(decor: dict[str, Any]) -> None:
    """Le residu du LOT 5, tranche — voir l'en-tete d'`app.media.autorisation`."""
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        premier_media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])
        second_media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])

        premiere = accorder_l_autorisation_photo(
            cx,
            entite=decor["entite"],
            person_id=decor["cible_personne"],
            media_asset_id=premier_media,
            source=SourceAutorisationPhoto.SELF_SERVICE.value,
            acteur=decor["cible_personne"],
            instant=ANCRAGE,
        )
        accorder_l_autorisation_photo(
            cx,
            entite=decor["entite"],
            person_id=decor["cible_personne"],
            media_asset_id=second_media,
            source=SourceAutorisationPhoto.SELF_SERVICE.value,
            acteur=decor["cible_personne"],
            instant=ANCRAGE + dt.timedelta(minutes=1),
        )

        lignes = cx.execute(
            text(
                "SELECT withdrawn_at FROM photo_authorization "
                "WHERE person_id = :p ORDER BY granted_at"
            ),
            {"p": decor["cible_personne"]},
        ).all()
        assert len(lignes) == 2
        assert all(ligne.withdrawn_at is None for ligne in lignes)
        assert (
            cx.execute(
                text("SELECT withdrawn_at FROM photo_authorization WHERE id = :id"),
                {"id": premiere.id},
            ).scalar_one()
            is None
        )


def test_retirer_efface_toutes_les_lignes_actives(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        for _ in range(2):
            media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])
            accorder_l_autorisation_photo(
                cx,
                entite=decor["entite"],
                person_id=decor["cible_personne"],
                media_asset_id=media,
                source=SourceAutorisationPhoto.SELF_SERVICE.value,
                acteur=decor["cible_personne"],
                instant=ANCRAGE,
            )

        nombre = retirer_l_autorisation_photo(
            cx, person_id=decor["cible_personne"], acteur=decor["cible_personne"], instant=ANCRAGE
        )
        assert nombre == 2
        actives = cx.execute(
            text(
                "SELECT count(*) FROM photo_authorization "
                "WHERE person_id = :p AND withdrawn_at IS NULL"
            ),
            {"p": decor["cible_personne"]},
        ).scalar_one()
        assert actives == 0


def test_retirer_sans_rien_a_retirer_rend_zero_pas_une_erreur(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        nombre = retirer_l_autorisation_photo(
            cx, person_id=decor["cible_personne"], acteur=decor["cible_personne"], instant=ANCRAGE
        )
        assert nombre == 0


# ===========================================================================
#  3. Les quatre routes JSON, par HTTP reel — meme discipline que la fiche
#     d'arrivee (LOT 7)
# ===========================================================================


@pytest.mark.integration
def test_droits_dit_oui_pour_la_cible_elle_meme(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _get(
        parametres,
        CHEMIN_DROITS.format(code=decor["code"], appartenance=decor["cible"]),
        _session(parametres, decor["cible_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["peut_deposer"] is True
    assert corps["peut_gerer_autorisation"] is True


@pytest.mark.integration
def test_accorder_par_http_refuse_sans_csrf_puis_reussit(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])
    jeton = _session(parametres, decor["cible_personne"])

    #  Refus CSRF (negatif), apparie au succes (positif) qui suit — §7.39.
    refus = _post_sans_csrf(
        parametres,
        CHEMIN_AUTORISATION.format(code=decor["code"], appartenance=decor["cible"]),
        jeton,
        {"media_asset_id": str(media)},
    )
    assert refus.status_code == 403

    reponse = _post(
        parametres,
        CHEMIN_AUTORISATION.format(code=decor["code"], appartenance=decor["cible"]),
        jeton,
        {"media_asset_id": str(media)},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["granted_at"]


@pytest.mark.integration
def test_le_DSM_est_refuse_par_http_sur_l_autorisation(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])
    reponse = _post(
        parametres,
        CHEMIN_AUTORISATION.format(code=decor["code"], appartenance=decor["cible"]),
        _session(parametres, decor["dsm_personne"]),
        {"media_asset_id": str(media)},
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_retirer_par_http_est_idempotent(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])
    jeton = _session(parametres, decor["cible_personne"])
    _post(
        parametres,
        CHEMIN_AUTORISATION.format(code=decor["code"], appartenance=decor["cible"]),
        jeton,
        {"media_asset_id": str(media)},
    )

    chemin_retrait = CHEMIN_RETRAIT.format(code=decor["code"], appartenance=decor["cible"])
    premier = _post(parametres, chemin_retrait, jeton)
    assert premier.status_code == 200
    assert premier.json()["autorisations_retirees"] == 1

    second = _post(parametres, chemin_retrait, jeton)
    assert second.status_code == 200
    assert second.json()["autorisations_retirees"] == 0


@pytest.mark.integration
def test_l_etat_d_un_media_est_lisible_par_son_depositaire(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        media = _media(cx, entite=decor["entite"], acteur=decor["esm_personne"], etat="rejected")
        cx.execute(
            text("UPDATE media_asset SET rejection_code = 'contenu_illisible' WHERE id = :id"),
            {"id": media},
        )
    reponse = _get(
        parametres,
        CHEMIN_ETAT_MEDIA.format(code=decor["code"], media=media),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["state"] == "rejected"
    assert corps["rejection_code"] == "contenu_illisible"


@pytest.mark.integration
def test_l_etat_d_un_media_est_refuse_a_qui_ne_l_a_pas_depose_et_n_a_aucun_role_d_entite(
    decor: dict[str, Any],
) -> None:
    parametres = decor["parametres"]
    with moteur(parametres).begin() as cx:
        media = _media(cx, entite=decor["entite"], acteur=decor["cible_personne"])
    reponse = _get(
        parametres,
        CHEMIN_ETAT_MEDIA.format(code=decor["code"], media=media),
        _session(parametres, decor["dsm_personne"]),
    )
    assert reponse.status_code == 403
