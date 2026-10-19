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
  lignes sans e-mail et la previsualisation complete sont `T7`, `US004` (2/2),
  et vivent dans `app.imports.analyse` — ce module les APPELLE, dans la MEME
  transaction, mais n'en porte aucune regle (§7.27).

LA PREMIERE ECRITURE MinIO DU PROJET

  Mesure avant d'ecrire une ligne : zero occurrence de `put_object` hors des
  tests, dans tout le depot. Chaque photo du jeu de donnees ou des decors de
  test est posee DIRECTEMENT par `boto3`, jamais par une route de l'API. `T6`
  ajoute donc `app.media.objets.deposer_l_objet`, reutilisant la construction
  du client deja faite pour la lecture (meme raison d'etre que ce module).

L'ETAT DU LOT A LA FIN DE CET APPEL, ET CE QUI A CHANGE DEPUIS `T6`

  Le diagramme §24.4 donne `Uploaded --> Analyzing --> PreviewReady`. `T6`
  servait les deux PREMIERES transitions et s'arretait a `analyzing` — ce
  module le fait encore, structurellement : il pose le lot, depose le CSV,
  insere les lignes brutes. **`T7` AJOUTE LA TROISIEME TRANSITION DANS LE
  MEME APPEL** : `deposer_un_csv` appelle desormais
  `app.imports.analyse.analyser_le_lot`, qui normalise, detecte les
  doublons, et fait passer le lot `analyzing -> preview_ready` — toujours
  dans la MEME transaction (import synchrone, `DEC-462`). Les tests de `T6`
  qui lisaient `state == "analyzing"` en sortie ont ete mis a jour en
  consequence : ce n'est pas une sous-etape qui en casse une autre, c'est la
  MEME fonction qui complete le pipeline qu'elle avait commence.

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

LE SEPARATEUR N'EST PAS DEVINE : `DEC-432` LE TRANCHE DEJA, ET `T6` NE L'AVAIT
PAS LU

  `QO-096`/`QO-110` (schema definitif, nomenclature des en-tetes) restent
  ouvertes et ne bloquent pas la construction du pipeline (fiche §2.1) — mais
  le SEPARATEUR DE CHAMPS, lui, est deja decide : `DEC-432`
  (`docs/architecture/donnees/schema-csv-collaborateurs.md` §2) dit
  « point-virgule OBLIGATOIRE ; la virgule est acceptee SI ELLE EST DETECTEE
  DE FACON NON AMBIGUE ». Motif explicite du document : « les noms et les
  presentations courtes contiennent des virgules, pas des points-virgules »
  — exactement le cas du jeu d'exemple du LOT 0, dont une ligne porte une
  presentation libre contenant une virgule NON ECHAPPEE.

  **DEFAUT TROUVE EN CONSTRUISANT `T7`, CORRIGE ICI AVANT TOUT CODE DE `T7`** :
  la premiere version de ce module (commit de `T6`) employait `csv.Sniffer`
  sur virgule/point-virgule/tabulation avec repli sur la virgule — une
  heuristique de FREQUENCE, jamais la regle EXPLICITE de `DEC-432`. Elle
  n'avait encore produit aucun defaut observable (le point-virgule reste
  largement majoritaire dans tout decor de test ecrit jusqu'ici), mais rien
  ne le garantissait structurellement. `_detecter_le_delimiteur` applique
  desormais la regle a la lettre : point-virgule par defaut, virgule
  SEULEMENT si aucun point-virgule n'apparait dans l'echantillon — et la
  tabulation, jamais nommee par `DEC-432`, est retiree des candidats.

  Le separateur RETENU est desormais persiste dans `import_batch.delimiter`
  (migration `0026`, `T10`) — `criteres-qualite-import.md` §4 l'exige « aux
  cotes de l'empreinte SHA-256 » dans LE RAPPORT D'IMPORT. Ce module le
  consigne a l'instant du depot ; `app.imports.rapport` le relit tel quel.

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

from app.audit.services import enregistrer_un_evenement
from app.imports.analyse import analyser_le_lot
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

#  `DEC-432` : le separateur OBLIGATOIRE. Voir l'en-tete du module.
_DELIMITEUR_PAR_DEFAUT: Final = ";"
#  `DEC-432` : « la virgule est acceptee si elle est detectee de facon non
#  ambigue » — jamais la tabulation, que la decision ne nomme pas.
_DELIMITEUR_TOLERE: Final = ","


@dataclasses.dataclass(frozen=True, slots=True)
class LotDepose:
    """Ce que le depot ET l'analyse d'un CSV ont produit — modele §19.1.

    **`state` VAUT DESORMAIS `preview_ready`**, pas `analyzing` : voir
    l'en-tete du module, `T7` complete le pipeline dans le MEME appel.
    """

    identifiant: uuid.UUID
    source_filename: str
    source_checksum_sha256: str
    state: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    needs_decision_rows: int
    rejected_rows: int
    version: int


_INSERER_LE_LOT: Final = text(
    """
    INSERT INTO import_batch
      (entity_id, source_filename, source_checksum_sha256, delimiter, state,
       created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :nom_de_fichier, :empreinte, :delimiteur, :etat_initial,
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


def _detecter_le_delimiteur(texte: str) -> str:
    """Le separateur du fichier — `DEC-432`, PAS une heuristique de frequence.

    Point-virgule par defaut ; virgule UNIQUEMENT si aucun point-virgule
    n'apparait dans l'echantillon (« detectee de facon non ambigue »). Voir
    l'en-tete du module : la premiere version de `T6` confiait ce choix a
    `csv.Sniffer`, qui ne porte pas cette regle.
    """
    echantillon = texte[:8192]
    if _DELIMITEUR_PAR_DEFAUT in echantillon:
        return _DELIMITEUR_PAR_DEFAUT
    if _DELIMITEUR_TOLERE in echantillon:
        return _DELIMITEUR_TOLERE
    return _DELIMITEUR_PAR_DEFAUT


def _analyser_les_lignes(texte: str) -> tuple[list[dict[str, object]], str]:
    """Les lignes du CSV, SANS AUCUNE validation de contenu — §9.5 point 2.

    `csv.DictReader` gere deja la variete que la colonne a trop ou en moins
    produit : `restval=None` pour une valeur manquante, `restkey=` (jamais
    `None`) pour les valeurs excedentaires, en liste.

    Rend aussi le delimiteur RETENU — `T10` le consigne desormais dans
    `import_batch.delimiter`, residu nomme par `T6` (voir l'en-tete du module).
    """
    delimiteur = _detecter_le_delimiteur(texte)
    lecteur = csv.DictReader(
        io.StringIO(texte),
        delimiter=delimiteur,
        restkey=CLE_COLONNES_EXCEDENTAIRES,
        restval=None,
    )
    return [dict(ligne) for ligne in lecteur], delimiteur


def deposer_un_csv(
    connexion: Connection,
    parametres: Parametres,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    nom_de_fichier: str,
    contenu: bytes,
    motif: str | None = None,
    instant: dt.datetime,
) -> LotDepose:
    """Deposer un CSV, l'analyser structurellement — cahier §9.5 (1 et 2), §19.1.

    **AUCUNE ECRITURE METIER** : les seules tables touchees sont `import_batch`
    et `import_row`, jamais `person`, `client`, `entity_membership` ou une
    autre table du domaine (§19.2 : « le contenu ne doit jamais etre recopie
    dans les logs » — et il n'entre pas davantage ailleurs qu'ici).

    `motif` : le motif du §18.1, obligatoire cote ROUTE quand `SUPER` autorise
    l'appel (`app.audit.motif`, `ECART-064`) — jamais verifie ici, ce module
    ne connait aucun role.
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

    lignes, delimiteur = _analyser_les_lignes(texte)
    empreinte = hashlib.sha256(contenu).hexdigest()

    lot = connexion.execute(
        _INSERER_LE_LOT,
        {
            "entite": entite,
            "nom_de_fichier": nom_nettoye,
            "empreinte": empreinte,
            "delimiteur": delimiteur,
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

    connexion.execute(
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
    )

    #  **`T7` DANS LA MEME TRANSACTION** : normalisation, doublons,
    #  `analyzing -> preview_ready` — voir l'en-tete du module.
    previsualisation = analyser_le_lot(
        connexion, entite=entite, lot=lot, acteur=acteur, instant=instant
    )

    #  LOT 10, `T7` : UN SEUL `audit_event` pour l'appel entier — depot ET
    #  previsualisation sont la MEME action metier, dans la MEME transaction.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="import_lot_depose",
        resource_type="import_batch",
        resource_reference=lot,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Depot du CSV « {nom_nettoye} » ({len(lignes)} ligne(s))",
        reason=motif,
    )

    return LotDepose(
        identifiant=lot,
        source_filename=nom_nettoye,
        source_checksum_sha256=empreinte,
        state=previsualisation.state,
        total_rows=previsualisation.total_rows,
        valid_rows=previsualisation.valid_rows,
        warning_rows=previsualisation.warning_rows,
        needs_decision_rows=previsualisation.needs_decision_rows,
        rejected_rows=previsualisation.rejected_rows,
        version=previsualisation.version,
    )
