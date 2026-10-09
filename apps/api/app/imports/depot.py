"""Deposer un CSV, calculer son empreinte, l'analyser SANS ecriture metier.

LOT 9, sous-etape `T6`, story `MVP-L09-US004` (1/2).

CE QUE CETTE SOUS-ETAPE SERT, ET DANS QUEL ORDRE — cahier §9.5, points 1 et 2

  1. chargement du fichier : les octets sont deposes dans MinIO (§19.1,
     « usage restreint »), sous une cle qui n'est JAMAIS celle que le client
     fournit — meme discipline que les medias (§16.1) ;
  2. analyse complete SANS ecriture : le CSV est lu structurellement, ligne
     par ligne, dans `import_row.raw_data` — aucune colonne n'est interpretee
     contre le schema F01-F19 (`DEC-434`), aucune ligne n'est validee, AUCUNE
     table metier (`person`, `client`, `entity_membership`...) n'est touchee.

  La normalisation des e-mails, la detection des doublons, le blocage des
  lignes sans e-mail et la previsualisation complete sont `T7`, `US004` (2/2) —
  deborder ici serait empieter sur une sous-etape qui n'est pas encore faite
  (§2, regle n°1).

LA PREMIERE ECRITURE MinIO DU PROJET

  Mesure avant d'ecrire une ligne : zero occurrence de `put_object` hors des
  tests, dans tout le depot. Chaque photo du jeu de donnees ou des decors de
  test est posee DIRECTEMENT par `boto3`, jamais par une route de l'API. `T6`
  ajoute donc `app.media.objets.deposer_l_objet`, reutilisant la construction
  du client deja faite pour la lecture (meme raison d'etre que ce module).

L'ETAT DU LOT A LA FIN DE CETTE SOUS-ETAPE, ET POURQUOI

  Le diagramme §24.4 donne `Uploaded --> Analyzing --> PreviewReady`. Cette
  sous-etape sert les DEUX premieres transitions dans le MEME appel — l'import
  est SYNCHRONE (`DEC-462`) — et s'arrete a `analyzing` : `PreviewReady`
  suppose la normalisation et la detection de doublons de `T7`, qui n'existent
  pas encore. Le nom de la sous-etape, « zone d'analyse sans ecriture
  metier », EST litteralement l'etat `analyzing`.

POURQUOI LE LOT EST CREE AVANT LE DEPOT MinIO, ET NON L'INVERSE

  Si l'upload MinIO echouait apres l'insertion du lot, la transaction
  ouvrante (`with moteur(parametres).begin()`, pose par la route) annule
  l'insertion : aucun lot orphelin ne survit a un depot rate. L'inverse —
  deposer d'abord, inserer ensuite — laisserait des octets dans MinIO sans
  aucune ligne pour les reclamer si l'insertion echouait, un residu qu'aucune
  duree de conservation ne saurait expliquer.

  Le decodage et l'analyse structurelle du CSV se font ENCORE PLUS TOT, avant
  toute ecriture, y compris celle du lot : un fichier illisible ne doit
  produire NI ligne `import_batch` NI octet depose — §9.5 point 2 dit
  « analyse complete SANS ECRITURE », et un fichier qui ne s'analyse meme pas
  ne justifie aucune des deux.

LE SCHEMA REEL DES COLONNES RESTE OUVERT, ET CE MODULE NE L'INVENTE PAS

  `QO-096`/`QO-110` (delimiteur, en-tetes, nomenclature) sont ouvertes et NE
  BLOQUENT PAS la construction du pipeline (fiche §2.1). Le delimiteur est
  donc DETECTE structurellement (`csv.Sniffer`, parmi virgule/point-virgule/
  tabulation — les trois formes qu'un tableur produit reellement), jamais
  suppose fixe : une heuristique MECANIQUE, pas une regle metier. Si la
  detection echoue (une seule colonne, par exemple), le repli est la virgule
  — un choix REVERSIBLE qui ne grave rien au schema.

  Chaque ligne devient un dictionnaire {en-tete: valeur}, SANS aucune
  validation de contenu : une valeur manquante vaut `None`, une colonne en
  trop rejoint `_colonnes_excedentaires` plutot que de se perdre en silence
  ou de produire une cle JSON invalide (`None`, que `csv.DictReader` emploie
  par defaut pour `restkey`).
"""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import hashlib
import io
import json
import uuid
from typing import TYPE_CHECKING, Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.imports.modeles import EtatLotImport
from app.media.objets import deposer_l_objet
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

CODE_FICHIER_VIDE: Final = "fichier_vide"
MESSAGE_FICHIER_VIDE: Final = "Le fichier depose est vide — aucune ligne a analyser."

CODE_ENCODAGE_INVALIDE: Final = "encodage_invalide"
MESSAGE_ENCODAGE_INVALIDE: Final = "Le fichier n'est pas un texte UTF-8 valide."

CODE_NOM_DE_FICHIER_INVALIDE: Final = "nom_de_fichier_invalide"
MESSAGE_NOM_DE_FICHIER_INVALIDE: Final = "Le nom du fichier depose est vide une fois nettoye."

#  Les valeurs qui excedent le nombre de colonnes de l'en-tete rejoignent
#  cette cle, en LISTE — jamais la cle `None` que `csv.DictReader` emploierait
#  par defaut pour `restkey`, qui n'est pas une cle JSON valide.
CLE_COLONNES_EXCEDENTAIRES: Final = "_colonnes_excedentaires"

#  Delimiteurs CANDIDATS pour la detection structurelle — §9.5, "QO-096 ne
#  bloque pas le pipeline". Trois formes qu'un tableur produit reellement,
#  jamais une liste complete inventee.
_DELIMITEURS_CANDIDATS: Final = ",;\t"


@dataclasses.dataclass(frozen=True, slots=True)
class LotDepose:
    """Ce que le depot d'un CSV a produit — modele §19.1."""

    identifiant: uuid.UUID
    source_filename: str
    source_checksum_sha256: str
    state: str
    total_rows: int
    version: int


_INSERER_LE_LOT: Final = text(
    """
    INSERT INTO import_batch
      (entity_id, source_filename, source_checksum_sha256, state,
       created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :nom_de_fichier, :empreinte, :etat_initial,
       :acteur, :acteur, :instant, :instant)
    RETURNING id
    """
)

_INSERER_UNE_LIGNE: Final = text(
    """
    INSERT INTO import_row (entity_id, import_batch_id, row_number, raw_data)
    VALUES (:entite, :lot, :numero, CAST(:donnees AS jsonb))
    """
)

#  **TROIS COLONNES DANS LE MEME `UPDATE`** — la cle d'objet, l'etat et le
#  total de lignes — pour qu'elles ne puissent jamais diverger par cette API
#  (§7.35, meme discipline que `app.organization.cycle_de_vie`).
_FIXER_LE_RESULTAT_DE_L_ANALYSE: Final = text(
    """
    UPDATE import_batch
       SET source_object_key = :cle,
           state = :etat_final,
           total_rows = :total,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :lot AND entity_id = :entite
    RETURNING version
    """
)


def _nettoyer_le_nom_de_fichier(nom: str) -> str:
    """Le « nom nettoye » du §19.1 — aucun chemin, les deux separateurs geres.

    Un navigateur n'envoie normalement que le nom seul, mais rien ne
    l'empeche de porter un chemin (§7.34 : un motif ecrit contre UN exemple ne
    couvre pas la classe) — les DEUX separateurs sont donc traites, jamais un
    seul.
    """
    return nom.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()


def _detecter_le_dialecte(texte: str) -> type[csv.Dialect] | csv.Dialect:
    """Detecter le delimiteur STRUCTURELLEMENT — jamais une regle metier.

    Le repli est la virgule, un choix REVERSIBLE : `QO-096`/`QO-110` restent
    ouvertes, et rien ici ne grave un format au schema.
    """
    try:
        return csv.Sniffer().sniff(texte[:8192], delimiters=_DELIMITEURS_CANDIDATS)
    except csv.Error:
        return csv.excel


def _analyser_les_lignes(texte: str) -> list[dict[str, object]]:
    """Les lignes du CSV, SANS AUCUNE validation de contenu — §9.5 point 2.

    `csv.DictReader` gere deja la variete que la colonne a trop ou en moins
    produit : `restval=None` pour une valeur manquante, `restkey=` (jamais
    `None`) pour les valeurs excedentaires, en liste.
    """
    dialecte = _detecter_le_dialecte(texte)
    lecteur = csv.DictReader(
        io.StringIO(texte),
        dialect=dialecte,
        restkey=CLE_COLONNES_EXCEDENTAIRES,
        restval=None,
    )
    return [dict(ligne) for ligne in lecteur]


def deposer_un_csv(
    connexion: Connection,
    parametres: Parametres,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    nom_de_fichier: str,
    contenu: bytes,
    instant: dt.datetime,
) -> LotDepose:
    """Deposer un CSV, l'analyser structurellement — cahier §9.5 (1 et 2), §19.1.

    **AUCUNE ECRITURE METIER** : les seules tables touchees sont `import_batch`
    et `import_row`, jamais `person`, `client`, `entity_membership` ou une
    autre table du domaine (§19.2 : « le contenu ne doit jamais etre recopie
    dans les logs » — et il n'entre pas davantage ailleurs qu'ici).
    """
    nom_nettoye = _nettoyer_le_nom_de_fichier(nom_de_fichier)
    if not nom_nettoye:
        raise ErreurApplicative(
            code=CODE_NOM_DE_FICHIER_INVALIDE,
            message=MESSAGE_NOM_DE_FICHIER_INVALIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="nom_de_fichier",
        )

    if not contenu:
        raise ErreurApplicative(
            code=CODE_FICHIER_VIDE,
            message=MESSAGE_FICHIER_VIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    try:
        texte = contenu.decode("utf-8-sig")
    except UnicodeDecodeError as erreur:
        raise ErreurApplicative(
            code=CODE_ENCODAGE_INVALIDE,
            message=MESSAGE_ENCODAGE_INVALIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        ) from erreur

    if not texte.strip():
        raise ErreurApplicative(
            code=CODE_FICHIER_VIDE,
            message=MESSAGE_FICHIER_VIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    lignes = _analyser_les_lignes(texte)
    empreinte = hashlib.sha256(contenu).hexdigest()

    lot = connexion.execute(
        _INSERER_LE_LOT,
        {
            "entite": entite,
            "nom_de_fichier": nom_nettoye,
            "empreinte": empreinte,
            "etat_initial": EtatLotImport.UPLOADED.value,
            "acteur": acteur,
            "instant": instant,
        },
    ).scalar_one()

    #  **LE DEPOT MinIO SUIT L'INSERTION, JAMAIS L'INVERSE** — voir l'en-tete
    #  du module : un echec ici annule l'insertion du lot via la transaction
    #  ouvrante, plutot que de laisser des octets orphelins dans le bucket.
    cle = f"imports/{entite}/{lot}.csv"
    deposer_l_objet(parametres, cle, contenu)

    for numero, ligne in enumerate(lignes, start=1):
        connexion.execute(
            _INSERER_UNE_LIGNE,
            {
                "entite": entite,
                "lot": lot,
                "numero": numero,
                "donnees": json.dumps(ligne),
            },
        )

    version = connexion.execute(
        _FIXER_LE_RESULTAT_DE_L_ANALYSE,
        {
            "cle": cle,
            "etat_final": EtatLotImport.ANALYZING.value,
            "total": len(lignes),
            "instant": instant,
            "acteur": acteur,
            "lot": lot,
            "entite": entite,
        },
    ).scalar_one()

    return LotDepose(
        identifiant=lot,
        source_filename=nom_nettoye,
        source_checksum_sha256=empreinte,
        state=EtatLotImport.ANALYZING.value,
        total_rows=len(lignes),
        version=version,
    )
