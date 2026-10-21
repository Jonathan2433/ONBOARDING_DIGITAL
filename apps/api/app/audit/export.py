"""L'export CSV du journal d'audit — matrice §16 « Exporter en CSV », `T9`, `US004`.

CE QUE LE BACKLOG EXIGE (`MVP-L10-US004`), ET COMMENT CHAQUE MOT EST TENU

  « Seuls les administrateurs autorises peuvent exporter » : `ROLES_D_EXPORT_
  DE_L_AUDIT` (`app/audit/perimetre.py`), verifie a la route avant tout code
  de ce module.

  « Le perimetre est respecte » : `lister_tout_le_journal_d_audit` (`app/audit/
  lecture.py`) REUTILISE la MEME resolution de perimetre et la MEME
  construction SQL que la lecture paginee de `T8` — jamais une seconde requete
  qui pourrait diverger. Comme `ADM-E`/`SUPER` sont EXACTEMENT les deux roles
  de `ROLES_DES_DETAILS_TECHNIQUES`, l'export ne masque jamais `resource_
  reference`/`correlation_token` — mais ce module ne le suppose pas, il
  transmet le booleen deja resolu par l'appelant, comme `T8`.

  « L'export est journalise » : cahier §10.11 liste « exports » parmi ce qui
  est audite. `ecrire_la_demande_d_export` pose une ligne `export_request`
  (modele §21.5, demandeur/perimetre normalise) ; l'appelant (la route) ecrit
  EN PLUS un `audit_event` via le service generique de `T2`, exactement comme
  toute autre action sensible deja cablee — ce module ne l'ecrit pas lui-meme,
  jamais une deuxieme voie d'ecriture d'audit (voir l'en-tete d'`app/audit/
  services.py`).

  « Limite » : lu comme « limite au perimetre deja resolu », rien de plus —
  aucun document ne nomme une borne de lignes ou de periode pour CET export,
  et en inventer une serait §6.5 de la passation. Le filtre `depuis`/`jusqua`
  deja servi par `T8` reste le seul moyen de borner une periode, a la demande
  de l'appelant.

POURQUOI `export_request.generated_media_id`/`.expires_at` RESTENT `NULL` ICI

  Le modele les declare (§21.5 : « media ou objet genere ; date d'expiration »)
  et `ExportRequest` (`app/audit/modeles.py`, `T1`) le dit DANS SON PROPRE
  DOCSTRING : « `T9` sert cet export de maniere SYNCHRONE ». Le couple
  mediatheque + expiration + telechargement securise est EXPLICITEMENT la V1
  asynchrone (`V1-L04-US002` : « le WORKER genere le fichier ; expiration et
  telechargement securise ») — une dependance, `async_job`, qui n'existe pas
  dans ce lot (§2 de la fiche). `T9` rend donc le CSV DIRECTEMENT dans la
  reponse HTTP, sans le deposer dans MinIO : les deux colonnes restent reservees
  a cette V1 future, jamais ecrites avant qu'elle n'existe.

LE FORMAT CSV LUI-MEME N'EST CONTRAINT PAR AUCUN DOCUMENT

  `DEC-432` fixe le separateur du CSV COLLABORATEURS, en ENTREE — un besoin
  different (des noms et presentations qui portent des virgules). Aucun
  document ne contraint le format de CET export, en SORTIE : virgule, guillemets
  RFC 4180 via le module `csv` standard, encodage UTF-8 — un choix par defaut
  documente ici, jamais une regle metier.

POURQUOI UNE VALEUR `None` DEVIENT UNE CELLULE VIDE, JAMAIS LE MOT `None`

  `str(None)` rend la chaine `"None"`, un texte qui RESSEMBLE a une donnee —
  exactement le defaut `T10-8` du LOT 6 (§7.42 de la passation) : une colonne
  NULLABLE (`reason`, `resource_reference`, `correlation_token`, `old_values`,
  `new_values`, `actor_*`) qui rend une chaine plausible plutot que rien.
  `_cellule` le dit explicitement.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import uuid
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import text

from app.audit.lecture import EvenementDAudit
from app.audit.perimetre import PerimetreDAudit

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  Vocabulaire OUVERT (`export_request.export_type`, voir `app/audit/
#  modeles.py`) : une seule valeur a ce jour, jamais une enumeration fermee sur
#  un ensemble V1 non decide.
TYPE_EXPORT_AUDIT_CSV: Final[str] = "audit_csv"

#  `action_code`/`resource_type` de l'evenement d'audit qui JOURNALISE
#  l'export lui-meme — litteraux, aucune enum existante ne nommant ce geste
#  (meme regime que `creer` au LOT 8 `T5`, `app/audit/lecture.py` n'en declare
#  aucune pour « export »).
ACTION_CODE_AUDIT_EXPORTE: Final[str] = "audit_exporte_en_csv"
RESOURCE_TYPE_EXPORT_REQUEST: Final[str] = "export_request"

_EN_TETE_CSV: Final[tuple[str, ...]] = (
    "id",
    "occurred_at",
    "action_code",
    "resource_type",
    "resource_reference",
    "summary",
    "old_values",
    "new_values",
    "reason",
    "actor_person_id",
    "actor_service_account_id",
    "correlation_token",
    "retention_until",
)


def _cellule(valeur: object) -> str:
    """Une valeur de `EvenementDAudit` en texte de cellule CSV — voir l'en-tete."""
    if valeur is None:
        return ""
    if isinstance(valeur, dict):
        return json.dumps(valeur, ensure_ascii=False, sort_keys=True)
    if isinstance(valeur, dt.datetime):
        return valeur.isoformat()
    return str(valeur)


def generer_le_csv(evenements: list[EvenementDAudit]) -> str:
    """Le contenu CSV complet — un en-tete, puis une ligne par evenement, dans
    l'ordre DEJA RESOLU par `lister_tout_le_journal_d_audit` (le plus recent
    d'abord). Jamais trie une seconde fois ici."""
    tampon = io.StringIO()
    redacteur = csv.writer(tampon)
    redacteur.writerow(_EN_TETE_CSV)
    for evenement in evenements:
        redacteur.writerow(
            [
                _cellule(evenement.id),
                _cellule(evenement.occurred_at),
                _cellule(evenement.action_code),
                _cellule(evenement.resource_type),
                _cellule(evenement.resource_reference),
                _cellule(evenement.summary),
                _cellule(evenement.old_values),
                _cellule(evenement.new_values),
                _cellule(evenement.reason),
                _cellule(evenement.actor_person_id),
                _cellule(evenement.actor_service_account_id),
                _cellule(evenement.correlation_token),
                _cellule(evenement.retention_until),
            ]
        )
    return tampon.getvalue()


def normaliser_la_portee(
    *, perimetre: PerimetreDAudit, entite: uuid.UUID, filtres: dict[str, Any]
) -> dict[str, Any]:
    """Le « filtre et perimetre normalises » du modele §21.5 — un `jsonb`
    JSON-serialisable, jamais un objet Python brut (UUID, `datetime`)."""
    return {
        "perimetre": perimetre.value,
        "entite": str(entite),
        "filtres": {
            cle: (valeur.isoformat() if isinstance(valeur, dt.datetime) else str(valeur))
            for cle, valeur in filtres.items()
            if valeur is not None
        },
    }


def ecrire_la_demande_d_export(
    connexion: Connection,
    *,
    requested_by_person_id: uuid.UUID,
    normalized_scope: dict[str, Any],
) -> uuid.UUID:
    """Poser la ligne `export_request` — modele §21.5. `generated_media_id`/
    `expires_at` restent `NULL` : voir l'en-tete du module."""
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO export_request (export_type, requested_by_person_id, normalized_scope) "
            "VALUES (:export_type, :demandeur, CAST(:portee AS jsonb)) RETURNING id"
        ),
        {
            "export_type": TYPE_EXPORT_AUDIT_CSV,
            "demandeur": requested_by_person_id,
            "portee": json.dumps(normalized_scope),
        },
    ).scalar_one()
