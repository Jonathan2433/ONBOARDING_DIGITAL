"""Le catalogue des taches reutilisables — modele §13.1, matrice §9, `T4`.

CE QUE CETTE SOUS-ETAPE FERME, STRUCTURELLEMENT — `ECART-013`

  Les cinq taches communes du prototype portaient un identifiant DIFFERENT
  par parcours (`ic_a1` contre `m_a1`, `ic_m1_1` contre `m_m1_5`...). Le
  remede n'est pas de transposer cette numerotation — le modele §13.1
  l'interdit explicitement, « ne pas reprendre la numerotation du prototype
  telle quelle » — c'est de poser UN SEUL identifiant fonctionnel STABLE par
  tache commune, partage par construction : `onboarding_template_task.
  task_reference_id` (posee des `T1`) pointe TOUJOURS vers la MEME ligne
  d'`onboarding_task_reference`, quel que soit le modele — mission ou
  intercontrat — qui la reutilise.

  Cette sous-etape pose donc le SERVICE qui cree et liste ces lignes ; `T10`
  (`US007`, changement automatique mission <-> intercontrat) est l'epreuve
  REELLE de la conservation par reference stable, pas celle-ci.

CE QUE LA MATRICE §9 DONNE ICI, ET CE QU'ELLE NE PEUT PAS DONNER

  Voir `perimetre.py` pour le detail : cinq des sept lignes du §9 partagent
  une seule grille (Consultants/Entite/Cercle/—/Entite/Global), et
  `onboarding_task_reference` n'a pas de colonne pour distinguer Consultants
  ou Cercle d'Entite — seul `entity_id`, nullable pour le global. DSM et
  BOOSTER recoivent donc la portee ENTITE, comme ESM et ADM-E ; seul SUPER
  atteint GLOBAL (`entity_id NULL`).

CE QUE CETTE SOUS-ETAPE NE FAIT PAS

  Ni modification, ni desactivation, ni archivage d'une tache de reference :
  aucune ligne du §9 ne les nomme. `active` et `archived_at` restent des
  colonnes du modele SANS ecrivain — un residuel nomme plutot qu'un oubli
  (§6.5 : ne jamais inventer un geste que le corpus ne decrit pas). Si un lot
  ulterieur en a besoin, c'est a lui de le decider et de l'ecrire.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Any, Final

from fastapi import status
from psycopg import errors as erreurs_psycopg
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.audit.services import enregistrer_un_evenement
from app.shared.errors import ErreurApplicative

CODE_TACHE_DEJA_UTILISEE: Final = "code_de_tache_deja_utilise"
MESSAGE_TACHE_DEJA_UTILISEE: Final = (
    "Ce code de tache est deja utilise dans ce perimetre (cette entite, ou le catalogue global)."
)


@dataclasses.dataclass(frozen=True, slots=True)
class TacheDeReference:
    """Une ligne du catalogue — modele §13.1. `entity_id=None` : tache GLOBALE."""

    id: uuid.UUID
    entity_id: uuid.UUID | None
    code: str
    title: str
    description: str | None
    category: str | None
    active: bool


#  Seul un LITTERAL FIXE de ce module — jamais une valeur de l'appelant — est
#  concatene dans les deux requetes ci-dessous : `_COLONNES` est une liste de
#  noms de colonnes constante, pas parametrable en SQL. `noqa: S608` sur
#  chacune, comme `ecriture.py` le fait pour le meme motif exact.
_COLONNES: Final = "id, entity_id, code, title, description, category, active"

_INSERER: Final = f"""
INSERT INTO onboarding_task_reference (entity_id, code, title, description, category)
VALUES (:entite, :code, :title, :description, :category)
RETURNING {_COLONNES}
"""  # noqa: S608

#  `entity_id = :entite OR entity_id IS NULL` : un modele de CETTE entite peut
#  reutiliser une tache qui lui est propre AUSSI BIEN qu'une tache globale —
#  modele §13.1, rien ne les separe pour la consultation. Les deux doivent
#  apparaitre dans le MEME catalogue pour que `T5` puisse composer une version.
_LISTER: Final = f"""
SELECT {_COLONNES}
FROM onboarding_task_reference
WHERE archived_at IS NULL
  AND (entity_id = :entite OR entity_id IS NULL)
ORDER BY category NULLS LAST, title
"""  # noqa: S608


def _depuis_la_ligne(ligne: Any) -> TacheDeReference:
    entity_id = ligne["entity_id"]
    return TacheDeReference(
        id=uuid.UUID(str(ligne["id"])),
        entity_id=None if entity_id is None else uuid.UUID(str(entity_id)),
        code=str(ligne["code"]),
        title=str(ligne["title"]),
        description=ligne["description"],
        category=ligne["category"],
        active=bool(ligne["active"]),
    )


def lire_le_catalogue_de_taches(
    connexion: Connection, *, entite: uuid.UUID
) -> tuple[TacheDeReference, ...]:
    """Les taches REUTILISABLES dans `entite` — les siennes, et les globales."""
    lignes = connexion.execute(text(_LISTER), {"entite": entite}).mappings().all()
    return tuple(_depuis_la_ligne(ligne) for ligne in lignes)


def creer_une_tache_de_reference(
    connexion: Connection,
    *,
    entite: uuid.UUID | None,
    code: str,
    title: str,
    description: str | None,
    category: str | None,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> TacheDeReference:
    """Ajouter une tache au catalogue — `entite=None` pour une tache GLOBALE.

    L'unicite du `code` est tenue par les DEUX index partiels poses en `T1`
    (`app/onboarding/modeles.py`) — un par perimetre, entite ou global —
    jamais recalculee ici : la CONTRAINTE decide, cette fonction la traduit.

    `acteur`/`instant` : LOT 10, `T6`. Ce module ne les employait pour AUCUNE
    colonne avant ce cablage — ni `created_by_person_id` ni `created_at` ne
    sont ecrits ici, `ChampsCommuns` laissant ses defauts serveur jouer. Les
    deux ne servent QUE l'ecriture d'audit ci-dessous.
    """
    try:
        ligne = (
            connexion.execute(
                text(_INSERER),
                {
                    "entite": entite,
                    "code": code,
                    "title": title,
                    "description": description,
                    "category": category,
                },
            )
            .mappings()
            .one()
        )
    except IntegrityError as erreur:
        #  Discriminant sur le TYPE d'exception psycopg, jamais sur le message
        #  — §7.25/§7.37, un message est localise et change de version en version.
        if isinstance(erreur.orig, erreurs_psycopg.UniqueViolation):
            raise ErreurApplicative(
                code=CODE_TACHE_DEJA_UTILISEE,
                message=MESSAGE_TACHE_DEJA_UTILISEE,
                statut=status.HTTP_409_CONFLICT,
            ) from erreur
        raise
    creee = _depuis_la_ligne(ligne)

    #  LOT 10, `T6` : litteral, meme discipline que la creation d'un modele ou
    #  d'une version (`gabarits.py`) — la matrice §9 ne porte aucune enum
    #  d'actions, a la difference des evenements du LOT 8.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="tache_de_reference_creee",
        resource_type="onboarding_task_reference",
        resource_reference=creee.id,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation de la tache de reference « {title} »",
    )
    return creee
