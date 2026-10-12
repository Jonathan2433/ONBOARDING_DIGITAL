"""Consulter le rapport d'un lot d'import — LOT 9, `T10`, `MVP-L09-US006` (2/2).

QUI CONSULTE, ET CE QUE CETTE SOUS-ETAPE NE SERT PAS ENCORE

  Matrice §14 « Consulter le rapport » : `ESM`/`ADM-E` Entite, `SUPER` Global,
  `DSM` Consultants, `BOOST` Cercle limite, `OFFICE` a tiret. **CE MODULE NE
  SERT QUE LES TROIS PREMIERS** — `ROLES_DE_DEPOT_DE_L_IMPORT`, MEME grille
  que « Charger un CSV » et « Lancer l'import » (§7.27).

  Posé à Jonathan avant tout code : rien dans le corpus ne dit COMMENT filtrer
  un rapport d'import par DSM ou par cercle, et une ligne rejetee n'a souvent
  pas encore de collaborateur rattache pour savoir a quel perimetre la
  rattacher — inventer ce filtrage aurait ete exactement le §6.5. Arbitrage :
  construire le rapport complet pour les trois roles qui chargent et lancent
  deja l'import, et OUVRIR UNE QUESTION pour le volet DSM/Booster plutot que
  de deviner — meme discipline que `QO-121` pour les blocs de contenu.

LA RECONCILIATION EST UNE LECTURE FRAICHE DE `import_row.state`, JAMAIS UN CACHE

  `criteres-qualite-import.md` §4 : « total_lignes = creations + mises_a_jour
  + rejets + en_attente_de_decision », avec les etats de `import_row` APRES
  import. `RapportDeLancement` (T9) ne compte que ce qu'UN appel de
  `lancer_l_import` a fait — les lignes deja `rejected` depuis la
  PREVISUALISATION (T7) y sont explicitement SKIPPEES, jamais recomptees. Ce
  module relit `import_row.state` DIRECTEMENT, par un `GROUP BY` : le compte
  reste exact apres un `rejeu` (T10), sans aucun compteur a synchroniser.

LE SEPARATEUR, L'ENCODAGE ET LE PROFIL DE CORRESPONDANCE

  Le separateur vient de `import_batch.delimiter`, consigne par T6/T10
  (migration `0026`, voir l'en-tete d'`app.imports.depot`). L'encodage est
  TOUJOURS `utf-8` — `app.imports.depot.deposer_un_csv` refuse tout le reste
  en 422 — une CONSTANTE, jamais une colonne pour une valeur qui ne varie
  pas. Le profil de correspondance est le profil PROVISOIRE unique
  (`DEC-434`, `QO-110` ouverte, `app.imports.correspondance`) : il n'existe
  qu'UNE version en usage aujourd'hui, donc rien a versionner par lot.

AUCUNE LIGNE REJETEE N'EST MASQUEE — CRITERE DE SORTIE DU LOT 9

  Chaque ligne de la page est rendue avec son `state` ET ses problemes
  (`import_row_issue`, code/champ/message/niveau) quand elle en porte — pas
  seulement les lignes rejetees : une ligne `warning` ou `needs_decision`
  porte aussi un probleme que le rapport ne doit pas taire.
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.imports.execution import CODE_LOT_INTROUVABLE, MESSAGE_LOT_INTROUVABLE
from app.imports.modeles import EtatLigneImport
from app.shared.errors import ErreurApplicative

#  Constante, jamais une colonne — voir l'en-tete : `deposer_un_csv` refuse
#  tout ce qui n'est pas de l'UTF-8 valide, en 422, avant toute ecriture.
ENCODAGE_RETENU: Final = "utf-8"

#  Une seule version en usage aujourd'hui (`QO-110` ouverte) — voir l'en-tete.
PROFIL_DE_CORRESPONDANCE: Final = "provisoire (DEC-434, QO-110 ouverte)"

_LOT: Final = text(
    """
    SELECT source_filename, source_checksum_sha256, delimiter, state,
           total_rows, valid_rows, warning_rows, needs_decision_rows, rejected_rows,
           created_by_person_id, approved_by_person_id
      FROM import_batch
     WHERE id = :lot AND entity_id = :entite
    """
)

_RECONCILIATION: Final = text(
    "SELECT state, count(*) AS total FROM import_row WHERE import_batch_id = :lot GROUP BY state"
)

_TOTAL_DES_LIGNES: Final = text("SELECT count(*) FROM import_row WHERE import_batch_id = :lot")

_PAGE_DES_LIGNES: Final = text(
    """
    SELECT id, row_number, state, error_codes
      FROM import_row
     WHERE import_batch_id = :lot
     ORDER BY row_number
     LIMIT :taille OFFSET :decalage
    """
)

_PROBLEMES_DES_LIGNES: Final = text(
    """
    SELECT import_row_id, code, field, message, level
      FROM import_row_issue
     WHERE import_row_id = ANY(:lignes)
     ORDER BY created_at
    """
)


@dataclasses.dataclass(frozen=True, slots=True)
class ProblemeDeLigne:
    code: str
    champ: str | None
    message: str
    niveau: str


@dataclasses.dataclass(frozen=True, slots=True)
class LigneDuRapport:
    identifiant: uuid.UUID
    numero: int
    etat: str
    codes_derreur: tuple[str, ...]
    problemes: tuple[ProblemeDeLigne, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Reconciliation:
    """`criteres-qualite-import.md` §4 — les quatre termes APRES import.

    `en_cours` (`valid`/`warning` non encore traites) n'appartient PAS a la
    formule du critere 8 : elle n'est non nulle qu'AVANT `lancer_l_import`,
    et reste rapportee pour la transparence d'un lot encore en previsualisation.
    """

    total_lignes: int
    creations: int
    mises_a_jour: int
    rejets: int
    en_attente_de_decision: int
    en_cours: int


@dataclasses.dataclass(frozen=True, slots=True)
class RapportDImport:
    etat_du_lot: str
    nom_de_fichier: str
    empreinte_sha256: str
    delimiteur: str | None
    encodage: str
    profil_de_correspondance: str
    depose_par: uuid.UUID
    approuve_par: uuid.UUID | None
    compteurs_de_previsualisation: dict[str, int]
    reconciliation: Reconciliation
    lignes: tuple[LigneDuRapport, ...]
    total_des_lignes: int
    page: int
    taille: int
    pages: int


def consulter_le_rapport(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lot: uuid.UUID,
    page: int,
    taille: int,
) -> RapportDImport:
    """Le rapport d'un lot — matrice §14, `criteres-qualite-import.md` §4."""
    ligne_lot = connexion.execute(_LOT, {"lot": lot, "entite": entite}).one_or_none()
    if ligne_lot is None:
        raise ErreurApplicative(
            code=CODE_LOT_INTROUVABLE,
            message=MESSAGE_LOT_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )

    comptes = {
        row.state: int(row.total) for row in connexion.execute(_RECONCILIATION, {"lot": lot})
    }
    reconciliation = Reconciliation(
        total_lignes=sum(comptes.values()),
        creations=comptes.get(EtatLigneImport.IMPORTED.value, 0),
        mises_a_jour=comptes.get(EtatLigneImport.UPDATED.value, 0),
        rejets=comptes.get(EtatLigneImport.REJECTED.value, 0),
        en_attente_de_decision=comptes.get(EtatLigneImport.NEEDS_DECISION.value, 0),
        en_cours=comptes.get(EtatLigneImport.VALID.value, 0)
        + comptes.get(EtatLigneImport.WARNING.value, 0),
    )

    total_des_lignes = int(connexion.execute(_TOTAL_DES_LIGNES, {"lot": lot}).scalar_one())
    pages = -(-total_des_lignes // taille) if total_des_lignes else 0

    lignes_brutes = connexion.execute(
        _PAGE_DES_LIGNES, {"lot": lot, "taille": taille, "decalage": (page - 1) * taille}
    ).fetchall()

    #  **AUCUNE REQUETE SUPPLEMENTAIRE SUR UNE PAGE VIDE** — meme discipline
    #  que `app.people.trombinoscope` : un `= ANY('{}')` ne rend rien et
    #  coute un aller-retour pour aucune information.
    identifiants = [row.id for row in lignes_brutes]
    problemes_par_ligne: dict[uuid.UUID, list[ProblemeDeLigne]] = {}
    if identifiants:
        for row in connexion.execute(_PROBLEMES_DES_LIGNES, {"lignes": identifiants}):
            problemes_par_ligne.setdefault(row.import_row_id, []).append(
                ProblemeDeLigne(
                    code=row.code, champ=row.field, message=row.message, niveau=row.level
                )
            )

    lignes = tuple(
        LigneDuRapport(
            identifiant=row.id,
            numero=row.row_number,
            etat=row.state,
            codes_derreur=tuple(row.error_codes or []),
            problemes=tuple(problemes_par_ligne.get(row.id, ())),
        )
        for row in lignes_brutes
    )

    return RapportDImport(
        etat_du_lot=ligne_lot.state,
        nom_de_fichier=ligne_lot.source_filename,
        empreinte_sha256=ligne_lot.source_checksum_sha256,
        delimiteur=ligne_lot.delimiter,
        encodage=ENCODAGE_RETENU,
        profil_de_correspondance=PROFIL_DE_CORRESPONDANCE,
        depose_par=ligne_lot.created_by_person_id,
        approuve_par=ligne_lot.approved_by_person_id,
        compteurs_de_previsualisation={
            "total_rows": ligne_lot.total_rows,
            "valid_rows": ligne_lot.valid_rows,
            "warning_rows": ligne_lot.warning_rows,
            "needs_decision_rows": ligne_lot.needs_decision_rows,
            "rejected_rows": ligne_lot.rejected_rows,
        },
        reconciliation=reconciliation,
        lignes=lignes,
        total_des_lignes=total_des_lignes,
        page=page,
        taille=taille,
        pages=pages,
    )
