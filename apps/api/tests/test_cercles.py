"""La page detaillee d'un cercle — LOT 6, `T3`, story `MVP-L06-US002`.

CHAQUE EXCLUSION A SON TEMOIN, ET ELLES DONNENT TOUTES LA MEME OBSERVATION

  Sept raisons peuvent faire qu'une personne n'apparaisse pas dans les membres :
  appartenance au cercle archivee, close, future ; profil `draft` ; appartenance
  a l'entite non `active` ; appartenance archivee ; autre cercle. **Un `WHERE`
  trop large les passerait toutes en paraissant correct**, exactement comme les
  huit refus du defaut `T2-3`.

  Chaque exclusion est donc appariee a un temoin qui ne differe que par LA valeur
  en cause — et la plus discriminante est celle ou **seul l'instant avance**.

LA COULEUR N'EST JAMAIS SEULE, ET C'EST LE MODELE QUI L'EXIGE

  Le §8.1 le porte parmi les contraintes de `circle`. Le decor porte donc un
  COUPLE : un cercle avec jeton, un cercle sans — et la chaine « None » est
  cherchee, parce que `str(None)` l'a servie sur 100 % des cercles pendant deux
  lots (defaut `T10-8`).
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
from app.media.modeles import EtatMedia, SourceAutorisationPhoto, TypeMedia, TypeVarianteMedia
from app.organization.cercles import CercleDetaille, lire_le_cercle
from app.organization.modeles import TypeAppartenanceCercle
from app.people.modeles import ETAT_LISTE, VISIBILITE_LISTEE
from app.shared.database import moteur
from app.shared.pagination import TAILLES_DE_PAGE

MARQUEUR = "L6T3"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)


# ============================================================================
#  1. Ce que le corpus ECRIT, verifie sans base
# ============================================================================
def test_les_DEUX_natures_d_appartenance_du_8_2_sont_declarees() -> None:
    """§8.2 : « `membership_type` | `principal` ou `secondary` »."""
    assert {m.value for m in TypeAppartenanceCercle} == {"principal", "secondary"}


def test_la_visibilite_est_celle_du_trombinoscope_et_non_une_copie() -> None:
    """§7.27 : deux copies d'une meme regle divergent au premier ajout.

    Ce test ne verifie pas une VALEUR, il verifie une PROVENANCE : si un jour
    quelqu'un ecrit `'active'` en dur dans `cercles.py`, ce test continuera de
    passer — et c'est pourquoi le module importe les constantes plutot que de les
    recopier. Ce que le test tient, c'est que les deux noms existent et sont bien
    ceux que le trombinoscope emploie.
    """
    assert ETAT_LISTE == "active"
    assert VISIBILITE_LISTEE == "published"


# ============================================================================
#  2. Integration
# ============================================================================
def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _entite(cx: Connection, suffixe: str) -> tuple[uuid.UUID, str]:
    code = f"{MARQUEUR}{suffixe}"
    identifiant = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        #  Un parametre PAR COLONNE — §7.25, defaut `T1-2`. `make parametres-check`
        #  le refuserait desormais.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()
    return identifiant, code


def _cercle(
    cx: Connection, entite: uuid.UUID, code: str, *, jeton: str | None = None, rang: int = 1
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, color_token, display_order) "
            "VALUES (:e, :code, :nom, :jeton, :rang) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code, "jeton": jeton, "rang": rang},
    ).scalar_one()


def _membre(
    cx: Connection,
    entite: uuid.UUID,
    cercle: uuid.UUID,
    *,
    nom: str,
    prenom: str = "Prenom",
    nature: str = "principal",
    etat: str = ETAT_LISTE,
    visibilite: str = VISIBILITE_LISTEE,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
) -> uuid.UUID:
    """Une personne, son appartenance a l'entite, et son appartenance au cercle."""
    adresse = f"{MARQUEUR}-{nom}-{uuid.uuid4().hex[:6]}@exalt.test".lower()
    personne = cx.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, :prenom, :nom, 'active') RETURNING id"
        ),
        #  `email_normalized` EN MINUSCULES — contrainte du LOT 2, defaut `T2-1`.
        {"a": adresse, "b": adresse, "prenom": prenom, "nom": nom},
    ).scalar_one()
    #  **`departed` EXIGE UNE DATE DE DEPART.** La contrainte
    #  `ck_entity_membership_depart_date_si_departed` le refuse sinon, et elle a
    #  raison : un partant sans date de depart n'existe pas. Defaut `T3-1`.
    depart = JUIN.date() if etat == "departed" else None
    appartenance = cx.execute(
        text(
            "INSERT INTO entity_membership (entity_id, person_id, arrival_date, "
            "departure_date, membership_state, professional_category, profile_visibility) "
            "VALUES (:e, :p, :arrivee, :depart, :etat, 'consultant', :visibilite) "
            "RETURNING id"
        ),
        {
            "e": entite,
            "p": personne,
            "arrivee": JANVIER.date(),
            "depart": depart,
            "etat": etat,
            "visibilite": visibilite,
        },
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at, ends_at) VALUES (:e, :a, :c, :t, :d, :f)"
        ),
        {"e": entite, "a": appartenance, "c": cercle, "t": nature, "d": debut, "f": fin},
    )
    return appartenance  # type: ignore[no-any-return]


def _photo_servable(
    cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID, *, maintenant: dt.datetime
) -> None:
    """Autorise et sert une photo pour l'appartenance donnee.

    Chantier front hors lot, `S12` (`DEC-673`). Reprend exactement la recette de
    `test_photo_de_profil.py` (media_asset `READY`, variante
    `MINIATURE_TROMBINOSCOPE`, autorisation active) : une seconde regle
    divergerait au premier ajout (§7.27).
    """
    personne = cx.execute(
        text("SELECT person_id FROM entity_membership WHERE id = :a"), {"a": appartenance}
    ).scalar_one()
    actif = cx.execute(
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256, "
            "ready_at) VALUES (:e, :p, :etat, :type_m, 'photo.jpg', :cle, 'image/jpeg', "
            "2000000, :emp, :pret) RETURNING id"
        ),
        {
            "e": entite,
            "p": personne,
            "etat": EtatMedia.READY.value,
            "type_m": TypeMedia.IMAGE.value,
            "cle": f"originaux-s12/{uuid.uuid4().hex}",
            "emp": "a" * 64,
            "pret": maintenant - dt.timedelta(days=1),
        },
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO media_variant (entity_id, media_asset_id, variant_type, width, "
            "height, variant_format, size_bytes, checksum_sha256, object_key) "
            "VALUES (:e, :a, :t, 200, 200, 'jpeg', 4096, :emp, :cle)"
        ),
        {
            "e": entite,
            "a": actif,
            "t": TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value,
            "emp": "a" * 64,
            "cle": f"miniatures-s12/{uuid.uuid4().hex}",
        },
    )
    cx.execute(
        text(
            "INSERT INTO photo_authorization (person_id, media_asset_id, granted_at, source) "
            "VALUES (:p, :m, :octroi, :src)"
        ),
        {
            "p": personne,
            "m": actif,
            "octroi": maintenant - dt.timedelta(days=1),
            "src": SourceAutorisationPhoto.SELF_SERVICE.value,
        },
    )


def _lire(
    cx: Connection, entite: uuid.UUID, code_entite: str, code_cercle: str, **kwargs: object
) -> CercleDetaille | None:
    return lire_le_cercle(
        cx,
        entite=entite,
        code_entite=code_entite,
        code_cercle=code_cercle,
        instant=kwargs.pop("instant", JUIN),  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


# ---- le couple du §7.42 ----------------------------------------------------
@pytest.mark.integration
def test_un_cercle_SANS_jeton_rend_None_et_non_la_chaine_None(cx: Connection) -> None:
    """**LE CAS QUI A COUTE `T10-8`**, servi sur 100 % des cercles pendant deux lots."""
    entite, code = _entite(cx, "JET")
    _cercle(cx, entite, "AVEC", jeton="bleu", rang=1)
    _cercle(cx, entite, "SANS", jeton=None, rang=2)
    avec = _lire(cx, entite, code, "AVEC")
    sans = _lire(cx, entite, code, "SANS")
    assert avec is not None and sans is not None
    assert avec.jeton_de_couleur == "bleu"
    assert sans.jeton_de_couleur is None
    assert sans.jeton_de_couleur != "None"


@pytest.mark.integration
def test_un_cercle_sans_couleur_porte_TOUJOURS_son_code_et_son_nom(cx: Connection) -> None:
    """§8.1 du MODELE : « la couleur ne constitue jamais la seule information visuelle »."""
    entite, code = _entite(cx, "NOM")
    _cercle(cx, entite, "SANS", jeton=None)
    cercle = _lire(cx, entite, code, "SANS")
    assert cercle is not None
    assert cercle.jeton_de_couleur is None
    assert cercle.code and cercle.nom


# ---- les trois causes de `None` --------------------------------------------
@pytest.mark.integration
def test_un_code_de_cercle_inconnu_rend_None(cx: Connection) -> None:
    entite, code = _entite(cx, "INC")
    assert _lire(cx, entite, code, "N-EXISTE-PAS") is None


@pytest.mark.integration
def test_un_cercle_d_une_AUTRE_entite_rend_None(cx: Connection) -> None:
    ici, code_ici = _entite(cx, "ICI")
    ailleurs, _ = _entite(cx, "AILL")
    _cercle(cx, ailleurs, "SIEN")
    assert _lire(cx, ici, code_ici, "SIEN") is None


@pytest.mark.integration
def test_un_cercle_ARCHIVE_rend_None_et_son_temoin_est_rendu(cx: Connection) -> None:
    """Le §10.2 porte « Restaurer un cercle », donc une lecture d'archive viendra —
    et elle aura sa PROPRE route, comme `fiche-archivee` au LOT 5 `T8` (§7.41)."""
    entite, code = _entite(cx, "ARCH")
    _cercle(cx, entite, "VIVANT", rang=1)
    archive = _cercle(cx, entite, "MORT", rang=2)
    cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": archive})
    assert _lire(cx, entite, code, "MORT") is None
    assert _lire(cx, entite, code, "VIVANT") is not None


# ---- le Booster ------------------------------------------------------------
@pytest.mark.integration
def test_le_Booster_ACTIF_est_nomme_et_son_absence_rend_None(cx: Connection) -> None:
    """Sans le second cas, une jointure qui ne joint jamais donnerait la meme
    observation qu'une jointure correcte sur un cercle sans Booster."""
    entite, code = _entite(cx, "BOOST")
    avec = _cercle(cx, entite, "AVEC", rang=1)
    _cercle(cx, entite, "SANS", rang=2)
    personne = cx.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :a, 'Lea', 'Martin', 'active') RETURNING id"
        ),
        {"a": f"{MARQUEUR}boost@exalt.test".lower()},
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'BOOSTER', :c, :p, :d)"
        ),
        {"p": personne, "e": entite, "c": avec, "d": JANVIER},
    )
    rendu_avec = _lire(cx, entite, code, "AVEC")
    rendu_sans = _lire(cx, entite, code, "SANS")
    assert rendu_avec is not None and rendu_avec.booster is not None
    assert rendu_avec.booster.nom == "Martin"
    #  Chantier front S12 (DEC-673) : ce Booster n'a AUCUNE appartenance dans
    #  cette entite -- `appartenance` reste None et `a_une_photo` reste faux,
    #  plutot que de lever sur une jointure qui ne trouve rien.
    assert rendu_avec.booster.appartenance is None
    assert rendu_avec.booster.a_une_photo is False
    assert rendu_sans is not None and rendu_sans.booster is None


# ---- la photo, chantier front hors lot S12 (DEC-673) -----------------------
@pytest.mark.integration
def test_le_Booster_AVEC_une_appartenance_et_une_photo_autorisee_la_sert(cx: Connection) -> None:
    """Contrairement au Booster sans appartenance ci-dessus : ici une
    appartenance active et listee existe, et une photo lui est autorisee."""
    entite, code = _entite(cx, "BPHO")
    cercle = _cercle(cx, entite, "DATA")
    appartenance = _membre(cx, entite, cercle, nom="Booster")
    personne = cx.execute(
        text("SELECT person_id FROM entity_membership WHERE id = :a"), {"a": appartenance}
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'BOOSTER', :c, :p, :d)"
        ),
        {"p": personne, "e": entite, "c": cercle, "d": JANVIER},
    )
    _photo_servable(cx, entite, appartenance, maintenant=JUIN)
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None and rendu.booster is not None
    assert rendu.booster.appartenance == appartenance
    assert rendu.booster.a_une_photo is True


@pytest.mark.integration
def test_TEMOIN_un_membre_AVEC_photo_la_sert_un_membre_SANS_ne_la_sert_pas(
    cx: Connection,
) -> None:
    """**LE TEMOIN QUI DISCRIMINE.** Deux membres, MEME cercle, MEME instant —
    seule la presence d'une autorisation differe. Sans ce couple, un `EXISTS`
    qui ne rend jamais rien donnerait la meme observation qu'un `EXISTS` exact,
    exactement le piege du defaut `T2-3` (huit refus restaient verts)."""
    entite, code = _entite(cx, "MPHO")
    cercle = _cercle(cx, entite, "DATA")
    avec = _membre(cx, entite, cercle, nom="Avec")
    sans = _membre(cx, entite, cercle, nom="Sans")
    _photo_servable(cx, entite, avec, maintenant=JUIN)
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None
    par_appartenance = {m.appartenance: m for m in rendu.membres}
    assert par_appartenance[avec].a_une_photo is True
    assert par_appartenance[sans].a_une_photo is False


# ---- les membres, et leurs sept exclusions ---------------------------------
@pytest.mark.integration
def test_TEMOIN_un_membre_actif_et_publie_est_liste(cx: Connection) -> None:
    entite, code = _entite(cx, "MEM")
    cercle = _cercle(cx, entite, "DATA")
    _membre(cx, entite, cercle, nom="Durand")
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None
    assert rendu.total_des_membres == 1
    assert rendu.membres[0].nom == "Durand"
    assert rendu.membres[0].type_d_appartenance == "principal"


@pytest.mark.integration
def test_les_DEUX_natures_d_appartenance_sont_rendues(cx: Connection) -> None:
    """§8.2 autorise « plusieurs cercles secondaires actifs » : les deux natures
    coexistent, et `ARB-DROIT-004` les distingue en droits."""
    entite, code = _entite(cx, "NAT")
    cercle = _cercle(cx, entite, "DATA")
    _membre(cx, entite, cercle, nom="Aprincipal", nature="principal")
    _membre(cx, entite, cercle, nom="Bsecondaire", nature="secondary")
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None
    assert {m.type_d_appartenance for m in rendu.membres} == {"principal", "secondary"}


@pytest.mark.integration
def test_une_appartenance_au_cercle_FUTURE_n_est_pas_listee_SEUL_L_INSTANT_CHANGE(
    cx: Connection,
) -> None:
    """**LE TEMOIN LE PLUS DISCRIMINANT.** Meme ligne, meme personne, meme cercle.
    Seul l'instant de lecture avance, et l'appartenance devient active."""
    entite, code = _entite(cx, "FUT")
    cercle = _cercle(cx, entite, "DATA")
    _membre(cx, entite, cercle, nom="Futur", debut=DECEMBRE)
    avant = _lire(cx, entite, code, "DATA", instant=JUIN)
    apres = _lire(cx, entite, code, "DATA", instant=DECEMBRE + dt.timedelta(days=1))
    assert avant is not None and avant.total_des_membres == 0
    assert apres is not None and apres.total_des_membres == 1


@pytest.mark.integration
def test_une_appartenance_au_cercle_CLOSE_n_est_plus_listee(cx: Connection) -> None:
    entite, code = _entite(cx, "CLOS")
    cercle = _cercle(cx, entite, "DATA")
    _membre(cx, entite, cercle, nom="Parti", fin=JUIN - dt.timedelta(days=1))
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None and rendu.total_des_membres == 0


@pytest.mark.integration
@pytest.mark.parametrize("etat", ["future", "departed", "archived"])
def test_une_appartenance_a_l_entite_non_ACTIVE_n_est_pas_listee(cx: Connection, etat: str) -> None:
    """`ETAT_LISTE`, reutilise du trombinoscope. Le §22.5 etape 5 n'etant
    implemente nulle part, un partant reste `published` : ce filtre est necessaire."""
    entite, code = _entite(cx, f"ET{etat[:3]}")
    cercle = _cercle(cx, entite, "DATA")
    _membre(cx, entite, cercle, nom="Exclu", etat=etat)
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None and rendu.total_des_membres == 0


@pytest.mark.integration
def test_un_profil_DRAFT_n_est_pas_liste(cx: Connection) -> None:
    """`VISIBILITE_LISTEE`. Un nouvel arrivant est `active` des son arrivee avec un
    profil `draft` : ce second filtre est necessaire, et il n'est pas redondant."""
    entite, code = _entite(cx, "DRA")
    cercle = _cercle(cx, entite, "DATA")
    _membre(cx, entite, cercle, nom="Brouillon", visibilite="draft")
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None and rendu.total_des_membres == 0


@pytest.mark.integration
def test_un_membre_d_un_AUTRE_cercle_n_est_pas_liste(cx: Connection) -> None:
    entite, code = _entite(cx, "AUT")
    ici = _cercle(cx, entite, "ICI", rang=1)
    ailleurs = _cercle(cx, entite, "AILLEURS", rang=2)
    _membre(cx, entite, ici, nom="Mien")
    _membre(cx, entite, ailleurs, nom="Sien")
    rendu = _lire(cx, entite, code, "ICI")
    assert rendu is not None
    assert [m.nom for m in rendu.membres] == ["Mien"]


# ---- la pagination du §18.2 ------------------------------------------------
@pytest.mark.integration
@pytest.mark.parametrize("taille", TAILLES_DE_PAGE)
def test_TEMOIN_les_TROIS_tailles_du_18_2_sont_acceptees(cx: Connection, taille: int) -> None:
    """**LE TEMOIN QUI A TROUVE `T2-3`.** Huit refus par valeur hors liste
    passaient tous, pour la mauvaise raison ; seul ce temoin discrimine."""
    entite, code = _entite(cx, f"TA{taille}")
    _cercle(cx, entite, "DATA")
    rendu = _lire(cx, entite, code, "DATA", taille=taille)
    assert rendu is not None and rendu.taille == taille


@pytest.mark.integration
@pytest.mark.parametrize("taille", [0, 1, 24, 26, 99, 101, 1000])
def test_une_taille_hors_du_18_2_est_refusee(cx: Connection, taille: int) -> None:
    entite, code = _entite(cx, "TAX")
    _cercle(cx, entite, "DATA")
    with pytest.raises(ValueError, match="taille doit etre"):
        _lire(cx, entite, code, "DATA", taille=taille)


@pytest.mark.integration
def test_une_page_inferieure_a_1_est_refusee(cx: Connection) -> None:
    entite, code = _entite(cx, "PG0")
    _cercle(cx, entite, "DATA")
    with pytest.raises(ValueError, match="page doit valoir"):
        _lire(cx, entite, code, "DATA", page=0)


@pytest.mark.integration
def test_les_pages_se_recomposent_SANS_doublon_ni_manquant(cx: Connection) -> None:
    """**L'ORDRE DOIT ETRE TOTAL, ET C'EST CE QUE CE TEST PROUVE.** Sans la cle
    primaire en dernier terme, deux homonymes rendraient un ordre non
    deterministe : une ligne pourrait paraitre deux fois ou jamais. Le decor porte
    donc DEUX homonymes exacts."""
    entite, code = _entite(cx, "REC")
    cercle = _cercle(cx, entite, "DATA")
    attendus = set()
    for rang in range(30):
        #  Deux homonymes EXACTS parmi les trente : c'est ce qui rend le test
        #  capable d'echouer si l'ordre n'est pas total.
        nom = "Homonyme" if rang < 2 else f"Nom{rang:02d}"
        attendus.add(_membre(cx, entite, cercle, nom=nom, prenom="Meme"))

    vus: list[uuid.UUID] = []
    for page in (1, 2):
        rendu = _lire(cx, entite, code, "DATA", page=page, taille=25)
        assert rendu is not None
        vus.extend(m.appartenance for m in rendu.membres)

    assert len(vus) == 30
    assert len(set(vus)) == 30, "une appartenance parait DEUX fois : l'ordre n'est pas total"
    assert set(vus) == attendus


@pytest.mark.integration
def test_pages_vaut_AU_MOINS_1_meme_sans_membre(cx: Connection) -> None:
    """`0` ne distinguerait pas « aucun membre » de « chargement »."""
    entite, code = _entite(cx, "P1")
    _cercle(cx, entite, "DATA")
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None
    assert rendu.total_des_membres == 0
    assert rendu.pages == 1


@pytest.mark.integration
def test_le_chemin_detaille_mene_a_la_page_du_cercle(cx: Connection) -> None:
    entite, code = _entite(cx, "CHE")
    _cercle(cx, entite, "DATA")
    rendu = _lire(cx, entite, code, "DATA")
    assert rendu is not None
    assert rendu.chemin_detaille.endswith("/framework/cercles/DATA")
