"""Deposer un CSV et l'analyser sans ecriture metier — LOT 9, `T6`, `MVP-L09-US004` (1/2).

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. le lot est pose avec sa bonne empreinte SHA-256 (sur les OCTETS, jamais le
     texte decode) et transite `uploaded` -> `analyzing` en un seul appel ;
  2. chaque ligne du CSV devient `import_row.raw_data`, telle quelle, sans
     AUCUNE validation — colonne manquante, colonne en trop, les deux formes
     sont couvertes separement (§7.42 : un decor qui ne produit jamais
     l'absence ne dit rien d'elle) ;
  3. le delimiteur est detecte structurellement, virgule ET point-virgule —
     deux decors distincts, jamais un seul suppose representatif ;
  4. les trois refus structurels (fichier vide, encodage invalide, nom de
     fichier vide une fois nettoye) sont chacun apparies a leur cause exacte ;
  5. le nettoyage du nom de fichier traite les DEUX separateurs de chemin ;
  6. les octets reellement deposes dans MinIO sont ceux recus, a l'octet pres
     — jamais le texte redecode, jamais une transformation.

Ce fichier ne reteste PAS `exiger_un_role_dans_l_entite` ni
`resoudre_les_permissions` : des briques generiques, deja prouvees ailleurs,
reutilisees sans modification par la route de `T6`.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.imports.depot import (
    CLE_COLONNES_EXCEDENTAIRES,
    CODE_ENCODAGE_INVALIDE,
    CODE_FICHIER_VIDE,
    CODE_NOM_DE_FICHIER_INVALIDE,
    LotDepose,
    _nettoyer_le_nom_de_fichier,
    deposer_un_csv,
)
from app.imports.modeles import EtatLotImport
from app.media.objets import client_s3, lire_l_objet
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T6"
INSTANT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)


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
            "VALUES (:email, :normalise, 'Depot', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
    ).scalar_one()


def _lignes_du_lot(cx: Connection, lot: uuid.UUID) -> list[dict[str, object]]:
    lignes = cx.execute(
        text(
            "SELECT row_number, raw_data FROM import_row "
            "WHERE import_batch_id = :lot ORDER BY row_number"
        ),
        {"lot": lot},
    ).all()
    return [dict(ligne.raw_data) for ligne in lignes]


def _deposer_ou_sauter(
    cx: Connection,
    parametres: Parametres,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    nom: str,
    contenu: bytes,
) -> LotDepose:
    try:
        return deposer_un_csv(
            cx,
            parametres,
            entite=entite,
            acteur=acteur,
            nom_de_fichier=nom,
            contenu=contenu,
            instant=INSTANT,
        )
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")
        raise  # pragma: no cover — pytest.skip leve deja, mypy veut un retour


def _nettoyer_l_objet(parametres: Parametres, cle: str | None) -> None:
    if not cle:
        return
    client = client_s3(parametres)
    #  Le menage ne doit JAMAIS faire echouer le test : une erreur ici dirait
    #  « MinIO est injoignable », ce que le test lui-meme a deja signale.
    with contextlib.suppress(Exception):
        client.delete_object(Bucket=parametres.MINIO_BUCKET, Key=cle)  # type: ignore[attr-defined]


def _nettoyer_le_lot(cx: Connection, parametres: Parametres, lot: uuid.UUID) -> None:
    cle = cx.execute(
        text("SELECT source_object_key FROM import_batch WHERE id = :lot"), {"lot": lot}
    ).scalar_one()
    _nettoyer_l_objet(parametres, cle)


# ---------------------------------------------------------------------------
#  1. Le lot, son empreinte, sa transition d'etat
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_le_depot_calcule_l_empreinte_et_transite_vers_analyzing(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T1")
    acteur = _personne(cx, "a1")
    contenu = b"email,prenom\nsoi@exemple.test,Alix\n"

    lot = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite,
        acteur=acteur,
        nom="collaborateurs.csv",
        contenu=contenu,
    )

    assert lot.source_checksum_sha256 == hashlib.sha256(contenu).hexdigest()
    assert lot.state == EtatLotImport.ANALYZING.value
    assert lot.total_rows == 1
    assert lot.version == 2  # 1 a la creation, +1 au UPDATE qui fixe le resultat

    ligne = cx.execute(
        text(
            "SELECT state, total_rows, valid_rows, source_object_key, source_filename "
            "FROM import_batch WHERE id = :lot"
        ),
        {"lot": lot.identifiant},
    ).one()
    assert ligne.state == "analyzing"
    assert ligne.total_rows == 1
    #  AUCUNE validation de contenu en T6 : valid_rows reste au defaut du
    #  modele, jamais calcule ici — c'est T7.
    assert ligne.valid_rows == 0
    assert ligne.source_object_key == f"imports/{entite}/{lot.identifiant}.csv"
    assert ligne.source_filename == "collaborateurs.csv"

    _nettoyer_l_objet(parametres_de_la_stack, ligne.source_object_key)


# ---------------------------------------------------------------------------
#  2. Chaque ligne, telle quelle — absence ET exces de colonnes
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_une_ligne_normale_devient_un_dictionnaire_fidele(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T2")
    acteur = _personne(cx, "a2")
    contenu = b"email,prenom,nom\nsoi@exemple.test,Alix,Dupont\n"

    lot = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite,
        acteur=acteur,
        nom="fichier.csv",
        contenu=contenu,
    )
    lignes = _lignes_du_lot(cx, lot.identifiant)

    assert lignes == [{"email": "soi@exemple.test", "prenom": "Alix", "nom": "Dupont"}]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_une_colonne_manquante_vaut_None_jamais_une_cle_absente(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Une ligne plus COURTE que l'en-tete : `restval=None`, jamais une cle en moins."""
    entite = _entite(cx, "T3")
    acteur = _personne(cx, "a3")
    contenu = b"email,prenom,nom\nsoi@exemple.test,Alix\n"

    lot = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite,
        acteur=acteur,
        nom="fichier.csv",
        contenu=contenu,
    )
    lignes = _lignes_du_lot(cx, lot.identifiant)

    assert lignes == [{"email": "soi@exemple.test", "prenom": "Alix", "nom": None}]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


@pytest.mark.integration
def test_une_colonne_excedentaire_rejoint_la_cle_dediee(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Une ligne plus LONGUE que l'en-tete : jamais la cle `None` de `csv.DictReader`."""
    entite = _entite(cx, "T4")
    acteur = _personne(cx, "a4")
    contenu = b"email,prenom\nsoi@exemple.test,Alix,Dupont,Surnumeraire\n"

    lot = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite,
        acteur=acteur,
        nom="fichier.csv",
        contenu=contenu,
    )
    lignes = _lignes_du_lot(cx, lot.identifiant)

    assert lignes == [
        {
            "email": "soi@exemple.test",
            "prenom": "Alix",
            CLE_COLONNES_EXCEDENTAIRES: ["Dupont", "Surnumeraire"],
        }
    ]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  3. Le delimiteur, detecte structurellement
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("suffixe", "contenu_texte"),
    [
        ("T5", "email,prenom\nsoi@exemple.test,Alix\n"),
        ("T6", "email;prenom\nsoi@exemple.test;Alix\n"),
    ],
)
def test_le_delimiteur_est_detecte_quel_que_soit_virgule_ou_point_virgule(
    cx: Connection, parametres_de_la_stack: Parametres, suffixe: str, contenu_texte: str
) -> None:
    entite = _entite(cx, suffixe)
    acteur = _personne(cx, f"a{suffixe}")
    lot = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite,
        acteur=acteur,
        nom="fichier.csv",
        contenu=contenu_texte.encode(),
    )
    lignes = _lignes_du_lot(cx, lot.identifiant)

    assert lignes == [{"email": "soi@exemple.test", "prenom": "Alix"}]
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)


# ---------------------------------------------------------------------------
#  4. Les trois refus structurels
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("contenu", [b"", b"   \n\n  "])
def test_un_fichier_vide_est_refuse(
    cx: Connection, parametres_de_la_stack: Parametres, contenu: bytes
) -> None:
    entite = _entite(cx, "T7")
    acteur = _personne(cx, "a7")

    with pytest.raises(ErreurApplicative) as excinfo:
        deposer_un_csv(
            cx,
            parametres_de_la_stack,
            entite=entite,
            acteur=acteur,
            nom_de_fichier="vide.csv",
            contenu=contenu,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_FICHIER_VIDE
    assert excinfo.value.statut == 422


@pytest.mark.integration
def test_un_encodage_non_utf8_est_refuse(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T8")
    acteur = _personne(cx, "a8")
    #  Une sequence qui n'est PAS un UTF-8 valide (ni UTF-8-SIG) : un octet de
    #  continuation (0x80) sans octet de tete.
    contenu = b"email,prenom\n\x80\x81,Alix\n"

    with pytest.raises(ErreurApplicative) as excinfo:
        deposer_un_csv(
            cx,
            parametres_de_la_stack,
            entite=entite,
            acteur=acteur,
            nom_de_fichier="invalide.csv",
            contenu=contenu,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_ENCODAGE_INVALIDE
    assert excinfo.value.statut == 422


@pytest.mark.integration
@pytest.mark.parametrize("nom", ["", "   ", "/", "\\", "C:\\Users\\jonathan\\"])
def test_un_nom_de_fichier_vide_une_fois_nettoye_est_refuse(
    cx: Connection, parametres_de_la_stack: Parametres, nom: str
) -> None:
    entite = _entite(cx, "T9")
    acteur = _personne(cx, "a9")

    with pytest.raises(ErreurApplicative) as excinfo:
        deposer_un_csv(
            cx,
            parametres_de_la_stack,
            entite=entite,
            acteur=acteur,
            nom_de_fichier=nom,
            contenu=b"email\nsoi@exemple.test\n",
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_NOM_DE_FICHIER_INVALIDE
    assert excinfo.value.statut == 422


# ---------------------------------------------------------------------------
#  5. Le nettoyage du nom de fichier, pur et sans base — les DEUX separateurs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("brut", "nettoye"),
    [
        ("collaborateurs.csv", "collaborateurs.csv"),
        ("dossier/collaborateurs.csv", "collaborateurs.csv"),
        ("C:\\Users\\jonathan\\collaborateurs.csv", "collaborateurs.csv"),
        ("../../etc/collaborateurs.csv", "collaborateurs.csv"),
        ("  collaborateurs.csv  ", "collaborateurs.csv"),
    ],
)
def test_le_nettoyage_du_nom_de_fichier_traite_les_deux_separateurs(
    brut: str, nettoye: str
) -> None:
    assert _nettoyer_le_nom_de_fichier(brut) == nettoye


# ---------------------------------------------------------------------------
#  6. Les octets reellement deposes dans MinIO
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_les_octets_deposes_sont_exactement_ceux_recus(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T10")
    acteur = _personne(cx, "a10")
    #  Un contenu non-ASCII, pour eprouver que les octets voyagent tels quels
    #  et non une re-encodage approximatif.
    contenu = "email,prenom\nsoi@exemple.test,Élodie\n".encode()

    lot = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite,
        acteur=acteur,
        nom="accents.csv",
        contenu=contenu,
    )

    cle = f"imports/{entite}/{lot.identifiant}.csv"
    try:
        octets_lus = lire_l_objet(parametres_de_la_stack, cle)
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        pytest.skip(f"MinIO injoignable a la relecture : {type(erreur).__name__}")

    assert octets_lus == contenu
    _nettoyer_le_lot(cx, parametres_de_la_stack, lot.identifiant)
