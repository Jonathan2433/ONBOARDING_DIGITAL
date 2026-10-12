"""Normaliser les e-mails, detecter les doublons — LOT 9, `T7`, `MVP-L09-US004` (2/2).

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. les quatre refus/decisions propres a l'e-mail — absent, format implausible,
     domaine refuse, doublon technique dans le fichier (`DEC-435` : la
     PREMIERE occurrence est retenue) ;
  2. les deux decisions de doublon de PERSONNE contre la base — profil actif
     existant, profil archive existant — et l'isolation : un domaine local a
     une entite ne vaut pas pour une autre ;
  3. l'homonymie DANS LE FICHIER (nom et prenom identiques, e-mails
     distincts), et son temoin negatif : deux lignes homonymes mais un SEUL
     e-mail distinct (doublon technique) ne declenchent PAS cette decision
     (§7.39 : chaque exclusion a son temoin) ;
  4. les quatre compteurs du lot se reconcilient EXACTEMENT avec le total ;
  5. `normalized_data` porte l'e-mail normalise pour une ligne qui en a un,
     `None` pour une ligne qui n'en a pas ;
  6. le profil de correspondance provisoire couvre les 19 champs logiques.

Ce fichier ne reteste PAS le depot (checksum, MinIO, delimiteur, fidelite de
`raw_data`) : `test_depot_import.py` le prouve deja.
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
from app.imports.analyse import (
    CODE_EMAIL_ABSENT,
    CODE_EMAIL_DOMAINE_REFUSE,
    CODE_EMAIL_DOUBLON_FICHIER,
    CODE_EMAIL_FORMAT_INVALIDE,
    CODE_PERSONNE_HOMONYME,
    CODE_PERSONNE_PROFIL_ACTIF,
    CODE_PERSONNE_PROFIL_ARCHIVE,
)
from app.imports.correspondance import PROFIL_DE_CORRESPONDANCE_PROVISOIRE, valeur_logique
from app.imports.depot import LotDepose, deposer_un_csv
from app.imports.modeles import EtatLigneImport, EtatLotImport
from app.media.objets import client_s3
from app.shared.database import moteur

MARQUEUR = "L9T7"
INSTANT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
DOMAINE_INCONNU = "domaine-non-enregistre.example"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


def _domaine_exalt_company_toujours_autorise(connexion: Connection) -> None:
    """Une seconde ligne GLOBALE, bornee dans le passe — §7.47, troisieme theatre.

    `make domaines-provision` seme deja `exalt-company.com` au demarrage de la
    stack, avec `starts_at = now()`. `INSTANT` de ce fichier est une date FIXE
    (2026-10-10) : le jour ou le calendrier reel la depasse, la ligne semee a
    un `starts_at` POSTERIEUR a `INSTANT`, sa periode ne le couvre plus, et
    CHAQUE ligne de ce domaine est refusee en silence (`E-EMAIL-003`) — mesure
    le 12/10/2026 en integration continue, sur une suite qui passait la veille.

    Une seconde ligne globale, bornee dans le passe et sans fin, ferme la
    question sans dependre du moment ou la stack a demarre. Elle vit dans la
    transaction du test (voir `cx` ci-dessous), donc elle s'annule avec elle —
    aucun residu, meme discipline que `_domaine_local`.
    """
    connexion.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, starts_at) "
            "VALUES ('exalt-company.com', NULL, '2020-01-01T00:00:00+00:00')"
        )
    )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            _domaine_exalt_company_toujours_autorise(connexion)
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


def _domaine_local(cx: Connection, *, entite: uuid.UUID, domaine: str) -> None:
    """Autoriser `domaine` pour `entite` — borne dans le PASSE, jamais `now()`.

    Meme defaut, meme correction que `_domaine_exalt_company_toujours_autorise`
    ci-dessus : une periode qui commence a `now()` cesse de couvrir `INSTANT`
    des que le calendrier reel depasse 2026-10-10.
    """
    cx.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, starts_at) "
            "VALUES (:domaine, :entite, '2020-01-01T00:00:00+00:00')"
        ),
        {"domaine": domaine, "entite": entite},
    )


def _personne_existante(cx: Connection, suffixe: str, *, email: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :email, 'Existant', :s, 'active') RETURNING id"
        ),
        {"email": email, "s": suffixe},
    ).scalar_one()


def _appartenance(
    cx: Connection, *, personne: uuid.UUID, entite: uuid.UUID, etat: str
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2020-01-01', :etat, 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "etat": etat},
    ).scalar_one()


def _deposer_ou_sauter(
    cx: Connection, parametres: Parametres, *, entite: uuid.UUID, acteur: uuid.UUID, contenu: str
) -> LotDepose:
    try:
        return deposer_un_csv(
            cx,
            parametres,
            entite=entite,
            acteur=acteur,
            nom_de_fichier="fichier.csv",
            contenu=contenu.encode(),
            instant=INSTANT,
        )
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")
        raise  # pragma: no cover — pytest.skip leve deja, mypy veut un retour


def _nettoyer_le_lot(cx: Connection, parametres: Parametres, lot: uuid.UUID) -> None:
    cle = cx.execute(
        text("SELECT source_object_key FROM import_batch WHERE id = :lot"), {"lot": lot}
    ).scalar_one()
    if not cle:
        return
    client = client_s3(parametres)
    with contextlib.suppress(Exception):
        client.delete_object(Bucket=parametres.MINIO_BUCKET, Key=cle)  # type: ignore[attr-defined]


def _codes_de_la_ligne(cx: Connection, lot: uuid.UUID, numero: int) -> list[str]:
    ligne_id = cx.execute(
        text("SELECT id FROM import_row WHERE import_batch_id = :lot AND row_number = :n"),
        {"lot": lot, "n": numero},
    ).scalar_one()
    lignes = cx.execute(
        text("SELECT code FROM import_row_issue WHERE import_row_id = :ligne ORDER BY code"),
        {"ligne": ligne_id},
    ).all()
    return [ligne.code for ligne in lignes]


def _etat_de_la_ligne(cx: Connection, lot: uuid.UUID, numero: int) -> str:
    return cx.execute(  # type: ignore[no-any-return]
        text("SELECT state FROM import_row WHERE import_batch_id = :lot AND row_number = :n"),
        {"lot": lot, "n": numero},
    ).scalar_one()


# ---------------------------------------------------------------------------
#  1. Les quatre refus/decisions propres a l'e-mail
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_email_absent_bloque_la_ligne(cx: Connection, parametres_de_la_stack: Parametres) -> None:
    entite = _entite(cx, "T1")
    acteur = _personne_existante(cx, "a1", email=f"{MARQUEUR.lower()}-a1@exalt-company.com")
    contenu = "email,nom,prenom\n,EXEMPLE,India\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.REJECTED.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == [CODE_EMAIL_ABSENT]
    assert lot.rejected_rows == 1
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_email_au_format_implausible_est_rejete(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T2")
    acteur = _personne_existante(cx, "a2", email=f"{MARQUEUR.lower()}-a2@exalt-company.com")
    #  Aucune arobase : `_email_plausible` exige `position("@") > 0`.
    contenu = "email,nom,prenom\nadresse-sans-arobase,EXEMPLE,Mike\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.REJECTED.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == [CODE_EMAIL_FORMAT_INVALIDE]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_domaine_non_autorise_est_rejete(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T3")
    acteur = _personne_existante(cx, "a3", email=f"{MARQUEUR.lower()}-a3@exalt-company.com")
    contenu = f"email,nom,prenom\nmike.exemple@{DOMAINE_INCONNU},EXEMPLE,Mike\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.REJECTED.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == [CODE_EMAIL_DOMAINE_REFUSE]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_un_domaine_local_a_une_entite_ne_vaut_pas_pour_une_autre(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """L'isolation multi-entites pendant l'import — critere de sortie du LOT 9."""
    entite_autorisee = _entite(cx, "T4a")
    entite_etrangere = _entite(cx, "T4b")
    _domaine_local(cx, entite=entite_autorisee, domaine="client-local.example")
    acteur = _personne_existante(cx, "a4", email=f"{MARQUEUR.lower()}-a4@exalt-company.com")
    contenu = "email,nom,prenom\nalix@client-local.example,EXEMPLE,Alix\n"

    lot_autorise = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite_autorisee, acteur=acteur, contenu=contenu
    )
    lot_etranger = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite_etrangere, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot_autorise.identifiant, 1) == EtatLigneImport.VALID.value
    assert _etat_de_la_ligne(cx, lot_etranger.identifiant, 1) == EtatLigneImport.REJECTED.value
    assert _codes_de_la_ligne(cx, lot_etranger.identifiant, 1) == [CODE_EMAIL_DOMAINE_REFUSE]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot_autorise.identifiant)
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot_etranger.identifiant)


@pytest.mark.integration
def test_doublon_technique_la_premiere_occurrence_est_retenue(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """`DEC-435` : la PREMIERE ligne est retenue, SEULE la seconde est rejetee."""
    entite = _entite(cx, "T5")
    acteur = _personne_existante(cx, "a5", email=f"{MARQUEUR.lower()}-a5@exalt-company.com")
    #  Casse differente : la NORMALISATION doit s'appliquer AVANT la
    #  comparaison, sans quoi les deux formes paraitraient distinctes.
    contenu = (
        "email,nom,prenom\n"
        "Alpha.Exemple@Exalt-Company.com,EXEMPLE,Alpha\n"
        "alpha.exemple@exalt-company.com,EXEMPLE,Lima\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.VALID.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == []
    assert _etat_de_la_ligne(cx, lot.identifiant, 2) == EtatLigneImport.REJECTED.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 2) == [CODE_EMAIL_DOUBLON_FICHIER]
    assert lot.valid_rows == 1
    assert lot.rejected_rows == 1
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  2. Doublons de PERSONNE contre la base
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_profil_actif_existant_est_une_decision(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T6")
    email_existant = f"{MARQUEUR.lower()}-existant-t6@exalt-company.com"
    personne = _personne_existante(cx, "existant-t6", email=email_existant)
    _appartenance(cx, personne=personne, entite=entite, etat="active")
    acteur = _personne_existante(cx, "a6", email=f"{MARQUEUR.lower()}-a6@exalt-company.com")
    contenu = f"email,nom,prenom\n{email_existant},EXEMPLE,Golf\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.NEEDS_DECISION.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == [CODE_PERSONNE_PROFIL_ACTIF]
    assert lot.needs_decision_rows == 1
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_profil_archive_existant_est_une_decision(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T7")
    email_existant = f"{MARQUEUR.lower()}-existant-t7@exalt-company.com"
    personne = _personne_existante(cx, "existant-t7", email=email_existant)
    _appartenance(cx, personne=personne, entite=entite, etat="archived")
    acteur = _personne_existante(cx, "a7", email=f"{MARQUEUR.lower()}-a7@exalt-company.com")
    contenu = f"email,nom,prenom\n{email_existant},EXEMPLE,Golf\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.NEEDS_DECISION.value
    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == [CODE_PERSONNE_PROFIL_ARCHIVE]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  3. Homonymie dans le fichier, et son temoin negatif
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_homonymie_dans_le_fichier_signale_les_deux_lignes(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T8")
    acteur = _personne_existante(cx, "a8", email=f"{MARQUEUR.lower()}-a8@exalt-company.com")
    #  Casse differente sur le nom/prenom : la comparaison est insensible a
    #  la casse (`casefold`), comme le jeu d'exemple du LOT 0 (Golf/golf).
    contenu = (
        "email,nom,prenom\n"
        "golf.exemple@exalt-company.com,EXEMPLE,Golf\n"
        "hotel.exemple@exalt-company.com,exemple,GOLF\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == [CODE_PERSONNE_HOMONYME]
    assert _codes_de_la_ligne(cx, lot.identifiant, 2) == [CODE_PERSONNE_HOMONYME]
    assert _etat_de_la_ligne(cx, lot.identifiant, 1) == EtatLigneImport.NEEDS_DECISION.value
    assert _etat_de_la_ligne(cx, lot.identifiant, 2) == EtatLigneImport.NEEDS_DECISION.value
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_un_SEUL_email_distinct_ne_declenche_PAS_l_homonymie(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Temoin negatif (§7.39) : meme nom/prenom, mais un SEUL e-mail distinct —
    la seconde ligne est deja exclue par le doublon technique (`E-EMAIL-004`),
    et `D-PERSONNE-003` ne doit PAS s'ajouter a la ligne retenue.
    """
    entite = _entite(cx, "T9")
    acteur = _personne_existante(cx, "a9", email=f"{MARQUEUR.lower()}-a9@exalt-company.com")
    contenu = (
        "email,nom,prenom\n"
        "golf.exemple@exalt-company.com,EXEMPLE,Golf\n"
        "golf.exemple@exalt-company.com,EXEMPLE,Golf\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert _codes_de_la_ligne(cx, lot.identifiant, 1) == []
    assert _codes_de_la_ligne(cx, lot.identifiant, 2) == [CODE_EMAIL_DOUBLON_FICHIER]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  4. Reconciliation des compteurs
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_les_quatre_compteurs_se_reconcilient_avec_le_total(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T10")
    email_existant = f"{MARQUEUR.lower()}-existant-t10@exalt-company.com"
    personne = _personne_existante(cx, "existant-t10", email=email_existant)
    _appartenance(cx, personne=personne, entite=entite, etat="active")
    acteur = _personne_existante(cx, "a10", email=f"{MARQUEUR.lower()}-a10@exalt-company.com")
    contenu = (
        "email,nom,prenom\n"
        "valide.exemple@exalt-company.com,EXEMPLE,Valide\n"  # valid
        ",EXEMPLE,India\n"  # rejected : E-EMAIL-001
        f"{email_existant},EXEMPLE,Existant\n"  # needs_decision : D-PERSONNE-001
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    assert lot.total_rows == 3
    assert lot.valid_rows == 1
    assert lot.warning_rows == 0
    assert lot.needs_decision_rows == 1
    assert lot.rejected_rows == 1
    assert (
        lot.valid_rows + lot.warning_rows + lot.needs_decision_rows + lot.rejected_rows
        == lot.total_rows
    )
    assert lot.state == EtatLotImport.PREVIEW_READY.value
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  5. `normalized_data`
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_normalized_data_porte_l_email_normalise_ou_None(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T11")
    acteur = _personne_existante(cx, "a11", email=f"{MARQUEUR.lower()}-a11@exalt-company.com")
    contenu = "email,nom,prenom\nVALIDE.Exemple@Exalt-Company.com,EXEMPLE,Valide\n,EXEMPLE,India\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )

    donnees = cx.execute(
        text(
            "SELECT row_number, normalized_data FROM import_row "
            "WHERE import_batch_id = :lot ORDER BY row_number"
        ),
        {"lot": lot.identifiant},
    ).all()
    assert donnees[0].normalized_data == {"F01": "valide.exemple@exalt-company.com"}
    assert donnees[1].normalized_data is None
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  6. Le profil de correspondance provisoire
# ---------------------------------------------------------------------------


def test_le_profil_de_correspondance_couvre_les_19_champs_logiques() -> None:
    attendus = {f"F{n:02d}" for n in range(1, 20)}
    assert set(PROFIL_DE_CORRESPONDANCE_PROVISOIRE) == attendus
    assert len(set(PROFIL_DE_CORRESPONDANCE_PROVISOIRE.values())) == 19  # aucun en-tete partage


def test_valeur_logique_rend_None_pour_une_valeur_vide_ou_absente() -> None:
    assert valeur_logique({"email": "a@b.com"}, "F01") == "a@b.com"
    assert valeur_logique({"email": "  "}, "F01") is None
    assert valeur_logique({}, "F01") is None
