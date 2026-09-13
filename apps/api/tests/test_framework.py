"""La page Framework en lecture — LOT 6, `T2`, story `MVP-L06-US001`.

CE QUE CE FICHIER PROUVE

  Les TROIS familles du cahier §10.3, l'exclusion de ce qui n'est pas actif, et
  le couple de jeton de couleur du §7.42.

CHAQUE EXCLUSION A SON TEMOIN, ET LE PLUS UTILE EST CELUI DE L'INSTANT

  Cinq raisons peuvent faire qu'une responsabilite ne nomme personne : archivee,
  close, future, cercle archive, autre entite. **Elles donnent toutes la meme
  observation** -- un titulaire absent. Un `WHERE` trop large les passerait
  toutes en paraissant correct.

  Chaque exclusion est donc appariee a un temoin qui ne differe que par LA valeur
  en cause, et le plus discriminant est celui ou **seul l'instant avance** : meme
  ligne, meme personne, meme cercle, et la responsabilite devient active.
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
from app.organization.framework import (
    RESPONSABILITES_A_PAGE_PROPRE,
    RESPONSABILITES_FRAMEWORK,
    PageFramework,
    lire_la_page_framework,
)
from app.shared.database import moteur

MARQUEUR = "L6T2"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)


# ============================================================================
#  1. Ce que le corpus ECRIT, verifie sans base
# ============================================================================
def test_les_QUATRE_responsabilites_du_6_2_sont_declarees() -> None:
    """Cahier §6.2 : « DSM ; ESM ; Booster ; responsable de bureau »."""
    assert RESPONSABILITES_FRAMEWORK == ("DSM", "ESM", "BOOSTER", "OFFICE_MANAGER")


def test_DEUX_responsabilites_sur_quatre_ont_une_page_propre() -> None:
    """L'annexe A §10.1 donne « Modifier la page DSM » et « Modifier la page ESM ».

    Elle n'en donne AUCUNE a `BOOSTER` ni a `OFFICE_MANAGER`, qui se rejoignent
    PAR les cercles et les bureaux. Promettre une page qui n'existe pour personne
    serait inventer ce que le document ne dit pas.
    """
    assert set(RESPONSABILITES_A_PAGE_PROPRE) == {"DSM", "ESM"}


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
        #  Un parametre PAR COLONNE : `code` est varchar, `display_name` et `city`
        #  sont text, et un parametre partage rend « inconsistent types deduced
        #  for parameter $1 » sans nommer la colonne. §7.25, defaut `T1-2`.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()
    return identifiant, code


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, 'Prenom', 'Nom', 'active') RETURNING id"
        ),
        #  `email_normalized` doit etre EN MINUSCULES — contrainte
        #  `ck_person_email_normalise_en_minuscules` du LOT 2. Le marqueur de ce
        #  fichier est en majuscules : la normalisation n'est pas decorative.
        {"a": adresse, "b": adresse.lower()},
    ).scalar_one()


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


def _bureau(cx: Connection, entite: uuid.UUID, code: str, *, rang: int = 1) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, :rang) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code, "rang": rang},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_de_responsabilite: str,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, office_id, assigned_by_person_id, "
            "starts_at, ends_at) VALUES (:p, :e, :t, :c, :b, :p, :d, :f)"
        ),
        {
            "p": personne,
            "e": entite,
            "t": type_de_responsabilite,
            "c": cercle,
            "b": bureau,
            "d": debut,
            "f": fin,
        },
    )


def _lire(
    cx: Connection, entite: uuid.UUID, code: str, instant: dt.datetime = JUIN
) -> PageFramework:
    return lire_la_page_framework(cx, entite=entite, code_entite=code, instant=instant)


# ---- les trois familles ----------------------------------------------------
@pytest.mark.integration
def test_les_trois_familles_sont_TOUJOURS_presentes_meme_vides(cx: Connection) -> None:
    """Une famille absente et une famille vide ne disent pas la meme chose."""
    entite, code = _entite(cx, "VIDE")
    page = _lire(cx, entite, code)
    #  Les quatre responsabilites sont rendues meme sans titulaire : la carte
    #  d'une categorie existe independamment de qui la porte.
    assert len(page.responsabilites) == 4
    assert page.cercles == ()
    assert page.bureaux == ()


@pytest.mark.integration
def test_l_ordre_des_responsabilites_vient_de_l_ENUMERATION(cx: Connection) -> None:
    """§7.35 : une propriete qu'aucun test unique ne peut observer est tenue par
    la structure. L'ordre d'iteration d'un ensemble ne varie qu'entre PROCESSUS."""
    entite, code = _entite(cx, "ORDRE")
    rendus = tuple(c.type_de_responsabilite for c in _lire(cx, entite, code).responsabilites)
    assert rendus == RESPONSABILITES_FRAMEWORK
    #  Et ce n'est PAS l'ordre alphabetique, sans quoi le test ne discriminerait rien.
    assert rendus != tuple(sorted(RESPONSABILITES_FRAMEWORK))


# ---- le couple du §7.42 ----------------------------------------------------
@pytest.mark.integration
def test_un_cercle_SANS_jeton_rend_None_et_non_la_chaine_None(cx: Connection) -> None:
    """**LE CAS QUI A COUTE `T10-8`**, servi sur 100 % des cercles pendant deux lots.

    Le couple est dans le decor : un cercle AVEC jeton et un SANS. Ni moitie ne
    suffit — sans le temoin, un code qui ne rendrait jamais de jeton passerait ;
    sans le cas, `str(None)` reste invisible.
    """
    entite, code = _entite(cx, "JETON")
    _cercle(cx, entite, "AVEC", jeton="bleu", rang=1)
    _cercle(cx, entite, "SANS", jeton=None, rang=2)
    cercles = {c.code: c for c in _lire(cx, entite, code).cercles}
    assert cercles["AVEC"].jeton_de_couleur == "bleu"
    assert cercles["SANS"].jeton_de_couleur is None
    assert cercles["SANS"].jeton_de_couleur != "None"


@pytest.mark.integration
def test_un_cercle_sans_couleur_porte_TOUJOURS_son_nom(cx: Connection) -> None:
    """Critere de sortie n°4 : la couleur n'est jamais l'unique information."""
    entite, code = _entite(cx, "NOM")
    _cercle(cx, entite, "SANS", jeton=None)
    cercle = _lire(cx, entite, code).cercles[0]
    assert cercle.jeton_de_couleur is None
    assert cercle.nom and cercle.code


# ---- l'instant, et c'est le temoin decisif ---------------------------------
@pytest.mark.integration
def test_TEMOIN_une_responsabilite_ACTIVE_nomme_son_titulaire(cx: Connection) -> None:
    entite, code = _entite(cx, "ACT")
    personne = _personne(cx, f"{MARQUEUR}act@exalt.test")
    _responsabilite(cx, entite, personne, "ESM", debut=JANVIER, fin=None)
    esm = next(
        c for c in _lire(cx, entite, code).responsabilites if c.type_de_responsabilite == "ESM"
    )
    assert len(esm.titulaires) == 1


@pytest.mark.integration
def test_une_responsabilite_FUTURE_ne_nomme_personne_et_SEUL_L_INSTANT_CHANGE(
    cx: Connection,
) -> None:
    """**LE TEMOIN LE PLUS DISCRIMINANT DU FICHIER.**

    Meme ligne, meme personne, meme type. Seul l'instant de lecture avance, et la
    responsabilite devient active. Sans lui, une absence de titulaire pourrait
    venir de n'importe quel filtre trop large.
    """
    entite, code = _entite(cx, "FUT")
    personne = _personne(cx, f"{MARQUEUR}fut@exalt.test")
    _responsabilite(cx, entite, personne, "ESM", debut=DECEMBRE, fin=None)

    avant = next(
        c
        for c in _lire(cx, entite, code, instant=JUIN).responsabilites
        if c.type_de_responsabilite == "ESM"
    )
    apres = next(
        c
        for c in _lire(cx, entite, code, instant=DECEMBRE + dt.timedelta(days=1)).responsabilites
        if c.type_de_responsabilite == "ESM"
    )
    assert avant.titulaires == ()
    assert len(apres.titulaires) == 1


@pytest.mark.integration
def test_une_responsabilite_CLOSE_ne_nomme_plus_personne(cx: Connection) -> None:
    entite, code = _entite(cx, "CLOS")
    personne = _personne(cx, f"{MARQUEUR}clos@exalt.test")
    _responsabilite(cx, entite, personne, "ESM", debut=JANVIER, fin=JUIN - dt.timedelta(days=1))
    esm = next(
        c for c in _lire(cx, entite, code).responsabilites if c.type_de_responsabilite == "ESM"
    )
    assert esm.titulaires == ()


# ---- les cercles et les bureaux --------------------------------------------
@pytest.mark.integration
def test_le_Booster_ACTIF_est_nomme_sur_son_cercle(cx: Connection) -> None:
    entite, code = _entite(cx, "BOOST")
    personne = _personne(cx, f"{MARQUEUR}boost@exalt.test")
    cercle = _cercle(cx, entite, "DATA", jeton="bleu")
    _responsabilite(cx, entite, personne, "BOOSTER", cercle=cercle)
    rendu = _lire(cx, entite, code).cercles[0]
    assert rendu.booster is not None
    assert rendu.booster.identifiant == personne


@pytest.mark.integration
def test_TEMOIN_un_cercle_SANS_Booster_rend_None(cx: Connection) -> None:
    """Sans ce temoin, une jointure qui ne joint jamais donnerait la meme
    observation qu'une jointure correcte sur un cercle sans Booster."""
    entite, code = _entite(cx, "NOBOOST")
    _cercle(cx, entite, "DATA", jeton="bleu")
    assert _lire(cx, entite, code).cercles[0].booster is None


@pytest.mark.integration
def test_un_cercle_ARCHIVE_est_exclu_et_son_temoin_ne_l_est_pas(cx: Connection) -> None:
    entite, code = _entite(cx, "ARCH")
    _cercle(cx, entite, "VIVANT", rang=1)
    archive = _cercle(cx, entite, "MORT", rang=2)
    cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": archive})
    codes = {c.code for c in _lire(cx, entite, code).cercles}
    assert codes == {"VIVANT"}


@pytest.mark.integration
def test_un_cercle_d_une_AUTRE_entite_n_apparait_pas(cx: Connection) -> None:
    """Le service filtre sur `entity_id` ; ce test le prouve plutot que de le croire."""
    ici, code_ici = _entite(cx, "ICI")
    ailleurs, _ = _entite(cx, "AILL")
    _cercle(cx, ici, "MIEN")
    _cercle(cx, ailleurs, "SIEN")
    assert {c.code for c in _lire(cx, ici, code_ici).cercles} == {"MIEN"}


@pytest.mark.integration
@pytest.mark.parametrize("combien", [0, 1, 3])
def test_un_bureau_rend_ses_responsables_ACTIFS_de_zero_a_trois(
    cx: Connection, combien: int
) -> None:
    """Le §8.4 en veut « entre un et trois **lorsqu'il est publie** ».

    **CETTE ROUTE N'EXIGE RIEN** : elle rend ce qui est, zero compris. `DEC-576`
    dit a partir de quand la borne mord — quand la page de contenu du bureau est
    publiee — et c'est `T4` qui posera le declencheur.
    """
    entite, code = _entite(cx, f"BUR{combien}")
    bureau = _bureau(cx, entite, "BDS")
    for rang in range(combien):
        personne = _personne(cx, f"{MARQUEUR}bur{combien}-{rang}@exalt.test")
        _responsabilite(cx, entite, personne, "OFFICE_MANAGER", bureau=bureau)
    assert len(_lire(cx, entite, code).bureaux[0].responsables) == combien


# ---- les chemins des pages detaillees --------------------------------------
@pytest.mark.integration
def test_chaque_carte_MENE_a_sa_page_detaillee(cx: Connection) -> None:
    """Critere d'acceptation : « les cartes menent aux pages detaillees »."""
    entite, code = _entite(cx, "CHEM")
    _cercle(cx, entite, "DATA")
    _bureau(cx, entite, "BDS")
    page = _lire(cx, entite, code)
    assert page.cercles[0].chemin_detaille.endswith("/framework/cercles/DATA")
    assert page.bureaux[0].chemin_detaille.endswith("/framework/bureaux/BDS")
    par_type = {c.type_de_responsabilite: c.chemin_detaille for c in page.responsabilites}
    assert par_type["DSM"] is not None and par_type["DSM"].endswith("/responsabilites/dsm")
    assert par_type["ESM"] is not None
    #  **`null`, ET NON UNE CHAINE VIDE.** Vide dirait « la page existe, son
    #  adresse est inconnue » ; `null` dit « il n'y en a pas ».
    assert par_type["BOOSTER"] is None
    assert par_type["OFFICE_MANAGER"] is None
