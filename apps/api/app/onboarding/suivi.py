"""Le suivi par perimetre — matrice §8.1 « Consulter les taches en retard », `T12`.

CE QUE `T12` LIVRE, ET CE QU'IL NE LIVRE PAS

  Une seule ligne du §8.1 restait sans consommateur apres `T11` : « Consulter
  les taches en retard » (`NEW` Soi, `DSM` Consultants, `ESM` Entite, `BOOST`
  Cercle, `OFFICE` —, `ADM-E` Entite, `SUPER` Global). Les DEUX autres lignes
  de consultation sont deja servies : « Consulter le parcours d'un
  collaborateur » par `lire_le_parcours` (`T7`), qui rend l'instance la PLUS
  RECENTE quel que soit son etat — `active`, `archived` ou `replaced` — sans
  qu'aucun filtre de `T12` n'ait besoin d'y toucher ; « Archiver »/
  « Restaurer » par `T11`. C'est ainsi que le critere `MVP-L07-US008`,
  « les onboardings termines sont archives et consultables selon droits »,
  est deja tenu avant que ce module n'existe — `T12` n'ajoute PAS une
  deuxieme route de consultation, il ajoute le REPORTING, litteralement la
  seule chose que le §8.1 nommait encore sans reponse.

  **« REPORTING DE BASE » SEULEMENT (cahier, Inclus) : AUCUN GRAPHIQUE, AUCUN
  EXPORT** — ce serait le LOT 10 (matrice §8.1, « Exporter le suivi », `V1`
  pour tous les roles). Cette liste rend donc des TACHES, paginees comme le
  cahier §18.2 l'exige partout ailleurs, jamais un agregat ni une moyenne.

CE QUE « EN RETARD » VEUT DIRE, ET CE QUI N'A PAS ETE INVENTE

  Une tache dont l'echeance est PASSEE et qui n'est ni terminee ni annulee —
  `state IN ('todo', 'reopened')` et `due_at < instant`. Le filtre porte sur
  TOUTE tache, obligatoire ou non : le §8.1 ne restreint pas cette ligne aux
  taches obligatoires, a la difference de « Archiver un parcours termine »
  (`T11`), qui lui ne regarde que celles-la.

  **SEULES LES INSTANCES `active` SONT COMPTEES.** Une instance `archived` a
  DEJA vu toutes ses taches obligatoires terminees (`T11`) ; une tache non
  obligatoire encore `todo` sur une instance archivee est un residu, pas un
  suivi actionnable — rien dans le corpus ne demande de le signaler, et
  l'omettre est la lecture qui n'invente rien (§6.5). Une instance `replaced`
  est un parcours qu'un changement de statut a rendu inerte (`T10`) : ses
  taches ne sont plus l'affaire de personne. Voir `compte-rendu-t12-lot-7.md`
  §2.1 pour le temoin qui le prouve.

QUI VOIT QUOI : LA RESOLUTION EST DANS `perimetre.py`, PAS ICI

  `resoudre_le_perimetre_du_suivi` (perimetre.py) transforme un ensemble de
  roles en UNE portee parmi quatre. Ce module ne fait QUE traduire cette
  portee en clause SQL — jamais l'inverse, et jamais de logique de role ici :
  la separation deja etablie entre "qui peut" (perimetre.py) et "comment on
  lit" (instances.py, taches.py) est reconduite a l'identique.

DEUX REQUETES, PAGINATION IDENTIQUE AU TROMBINOSCOPE (LOT 5, `T2`)

  Meme discipline que `lister_le_trombinoscope` : le total ET la page dans la
  MEME transaction, aucune boucle par ligne, un ordre TOTAL (`due_at` puis
  `id`, cle primaire en dernier recours). Les trois tailles du cahier §18.2
  sont REUTILISEES depuis `app.shared.pagination`, jamais redeclarees —
  premiere consommation de ce module par l'onboarding.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.onboarding.perimetre import PerimetreDuSuivi
from app.shared.pagination import TAILLES_DE_PAGE

#  §8.4 : meme litterale que `perimetre.py::_TYPE_BOOSTER` — recopiee et non
#  importee, motif SQL partage entre deux modules (§7.27, voir l'en-tete de
#  `perimetre.py`).
_TYPE_BOOSTER: Final[str] = "BOOSTER"


@dataclasses.dataclass(frozen=True, slots=True)
class TacheEnRetard:
    """Une ligne de `onboarding_instance_task`, en retard, et la personne
    qu'elle concerne — matrice §8.1 « Consulter les taches en retard »."""

    id: uuid.UUID
    title_snapshot: str
    due_at: dt.datetime
    state: str
    instance_id: uuid.UUID
    appartenance_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str


@dataclasses.dataclass(frozen=True, slots=True)
class PageDeSuivi:
    """Une page du suivi, et le total de la population — pas de la page,
    meme discipline que `PageDuTrombinoscope` (LOT 5, `T2`)."""

    taches: list[TacheEnRetard]
    total: int


#  Une clause par portee, correlee a `em` (alias de `entity_membership` dans
#  `_SOURCE`). `ENTITE` n'a besoin d'aucune restriction supplementaire : le
#  filtre `entite = :entite` de `_SOURCE` suffit deja, donc sa clause est
#  triviale — jamais un chemin de code distinct, voir la fonction.
_CLAUSE_CONSULTANTS: Final[str] = """
EXISTS (
    SELECT 1 FROM dsm_assignment da
    WHERE da.consultant_membership_id = em.id AND da.dsm_person_id = :acteur
      AND da.entity_id = :entite AND da.archived_at IS NULL AND da.period @> :instant
)
"""

_CLAUSE_CERCLE: Final[str] = """
EXISTS (
    SELECT 1 FROM circle_membership cm
    JOIN framework_responsibility_assignment fra
      ON fra.circle_id = cm.circle_id AND fra.entity_id = cm.entity_id
    WHERE cm.entity_membership_id = em.id AND cm.archived_at IS NULL AND cm.period @> :instant
      AND fra.person_id = :acteur AND fra.entity_id = :entite
      AND fra.responsibility_type = :type_booster
      AND fra.archived_at IS NULL AND fra.period @> :instant
)
"""

_CLAUSE_SOI: Final[str] = "em.person_id = :acteur"

_CLAUSES_PAR_PERIMETRE: Final[Mapping[PerimetreDuSuivi, str]] = {
    PerimetreDuSuivi.ENTITE: "TRUE",
    PerimetreDuSuivi.CONSULTANTS: _CLAUSE_CONSULTANTS,
    PerimetreDuSuivi.CERCLE: _CLAUSE_CERCLE,
    PerimetreDuSuivi.SOI: _CLAUSE_SOI,
}

#  Instance `active` SEULE (voir l'en-tete), taches `todo`/`reopened` en
#  retard. `oit.entity_id` (colonne propre, `ChampsCommuns`) evite de
#  joindre `onboarding_instance` pour la seule isolation d'entite ; la
#  jointure reste necessaire pour `state` et `entity_membership_id`.
_BASE_SOURCE: Final[str] = """
FROM onboarding_instance_task oit
JOIN onboarding_instance oi
  ON oi.id = oit.onboarding_instance_id AND oi.entity_id = oit.entity_id
JOIN entity_membership em ON em.id = oi.entity_membership_id
JOIN person p ON p.id = em.person_id
WHERE oit.entity_id = :entite
  AND oi.state = 'active'
  AND oit.state IN ('todo', 'reopened')
  AND oit.due_at < :instant
"""


def lister_les_taches_en_retard(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    perimetre: PerimetreDuSuivi,
    page: int,
    taille: int,
    instant: dt.datetime,
) -> PageDeSuivi:
    """La page demandee des taches en retard dans la portee resolue, et le total.

    `perimetre` est DEJA RESOLU par l'appelant (`resoudre_le_perimetre_du_
    suivi`), meme discipline que `cible` deja resolue dans `affecter_un_
    parcours` (`T7`) : ce module ne decide jamais QUI voit quoi, il traduit
    une decision deja prise.

    `instant` EST INJECTE, jamais `now()` dans la requete : le temoin « hors
    delai » de `T12` avance cette valeur, comme tous les temoins temporels du
    lot depuis `T8` (§9.2 point 13 de `CLAUDE.md`).
    """
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    clause = _CLAUSES_PAR_PERIMETRE[perimetre]
    source = f"{_BASE_SOURCE} AND ({clause})"
    parametres: dict[str, object] = {
        "entite": entite,
        "instant": instant,
        "acteur": acteur,
        "type_booster": _TYPE_BOOSTER,
    }

    total = int(connexion.execute(text(f"SELECT count(*) {source}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                "SELECT oit.id, oit.title_snapshot, oit.due_at, oit.state, "
                "oi.id AS instance_id, em.id AS appartenance_id, "
                "p.id AS person_id, p.first_name, p.last_name "
                f"{source} "
                "ORDER BY oit.due_at ASC, oit.id ASC "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )

    return PageDeSuivi(taches=[_en_tache(ligne) for ligne in lignes], total=total)


def _en_tache(ligne: Any) -> TacheEnRetard:
    return TacheEnRetard(
        id=ligne["id"],
        title_snapshot=ligne["title_snapshot"],
        due_at=ligne["due_at"],
        state=ligne["state"],
        instance_id=ligne["instance_id"],
        appartenance_id=ligne["appartenance_id"],
        person_id=ligne["person_id"],
        first_name=ligne["first_name"],
        last_name=ligne["last_name"],
    )
