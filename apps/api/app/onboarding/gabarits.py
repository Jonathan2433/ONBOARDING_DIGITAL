"""Les modeles d'onboarding et leurs versions — modele §13.2 a §13.4, matrice §9, `T5`.

POURQUOI CE MODULE S'APPELLE `gabarits` ET NON `modeles`

  `app/onboarding/modeles.py` porte deja ce nom pour les classes SQLAlchemy du
  lot entier (§7 de `CLAUDE.md`, convention constante du projet : un domaine,
  un fichier `modeles.py` pour son ORM). « Gabarit » traduit le meme mot que
  le corpus emploie en francais courant — le cahier et la fiche disent tous
  deux « modele » — sans entrer en collision avec ce nom deja pris.

CE QUE `T5` LIVRE, ET CE QU'IL NE LIVRE PAS

  Trois gestes, dans l'ordre du §9 : creer un modele (le conteneur, `onboarding_
  template`), creer une nouvelle version (brouillon, `onboarding_template_
  version`), composer la liste de ses taches (`onboarding_template_task`).
  **`T6` (« Cycle de vie d'un modele », `app/onboarding/cycle_de_vie.py`) livre
  depuis la publication, l'archivage et la restauration d'une version** —
  matrice §9, lignes « Publier une version », « Archiver une version »,
  « Restaurer une version ». Aucune duplication distincte n'existe : arbitrage
  de Jonathan du 26/09/2026, ce mot du decoupage (`DEC-598`) designe la
  creation de version deja livree ici, pas une quatrieme route. Aucune lecture
  non plus : ni « Consulter les modeles publies » (grille plus large), ni
  « Previsualiser » — les deux arrivent avec les ecrans (`T13`/`T14`).

CE QUE `T14` AJOUTE, ET POURQUOI CE N'ETAIT PAS DECIDE A `T5`

  `lister_les_modeles`/`lister_les_versions` : trouve en construisant l'ecran
  d'administration — sans elles, « gerer les modeles » ne pourrait agir que
  sur ce qui vient d'etre cree DANS LA MEME SESSION, jamais revenir sur un
  modele existant. Ni `T5` ni `T6` n'avaient besoin de lire PLUSIEURS modeles
  a la fois, donc rien n'existait avant qu'un ecran ne le demande — meme
  motif que l'extension de `/permissions` a `T13`. Le filtrage par role
  (§9) reste celui de `perimetre.py`, applique par l'appelant sur la liste
  brute que ce module rend : aucune seconde regle de portee ici. « Consulter
  les modeles publies » (§9, grille plus large qu'`OFFICE` atteint aussi) et
  « Previsualiser » restent SANS route : aucun critere actuel ne les
  reclame, et `T14` ne les invente pas.

L'IMMUABILITE D'UNE VERSION PUBLIEE — modele §13.3, LE TEMOIN DE CETTE SOUS-ETAPE

  « Chaque publication cree une version immuable. » `T5` ne publie rien lui-
  meme, mais DOIT refuser d'ecrire des taches sur une version qui l'est deja
  — sans cette garde, la publication de `T6` ne protegerait rien : un modele
  reste modifiable APRES publication par la seule route de `T5`. Le decor de
  test ecrit directement `state = 'published'` en base (aucune route ne le
  fait encore, `T6`), exactement comme les tests de `T4` ecrivaient des
  appartenances sans passer par une route qui ne les cree pas non plus.

DEUX RESIDUS NOMMES PAR `T1`, INSTRUITS ICI — PAR LE SERVICE, PAS PAR LA BASE

  `app/onboarding/modeles.py` documente pourquoi `onboarding_template.
  scope_circle_id` et `onboarding_template_task.task_reference_id` portent
  des cles ETRANGERES SIMPLES plutot que composites : `make isolation-check`
  exige `entity_id NOT NULL` a la SOURCE pour toute cle composite, sans
  condition, et les deux tables visees ont un `entity_id` NULLABLE (le cercle
  n'est pas en cause ici, mais `onboarding_task_reference` l'est). La
  coherence d'entite N'EST DONC PAS GARANTIE EN BASE :

    - un modele `CIRCLE` doit viser un cercle de la MEME entite — verifie par
      `peut_gerer_un_modele_de_cette_portee` (`perimetre.py`), AVANT creation ;
    - une tache de reference ajoutee a une version doit etre GLOBALE ou de la
      MEME entite que le modele — jamais celle d'une AUTRE entite. Verifie
      ici par `_tache_dans_le_perimetre_du_modele`, la MEME regle que `T4`
      documente deja (compte-rendu `T4`, §2.4) : « un modele d'une entite peut
      reutiliser une tache PROPRE a cette entite ou une tache GLOBALE ».

LA LISTE DES TACHES EST REECRITE EN BLOC, JAMAIS FUSIONNEE

  Matrice §9 : « Ajouter ou reordonner des taches » est UNE SEULE ligne, pas
  deux verbes distincts a deux routes — meme lecture que `content_block`
  (LOT 6, `T6`) : `display_order` vaut l'INDEX du tableau recu, et poser la
  liste ENTIERE remplace la precedente. Aucune archive n'est ecrite sur les
  lignes retirees : rien ne les REFERENCE encore — aucune instance n'existe
  avant `T7` — et le §2.4 du modele reserve l'archivage aux ressources deja
  EXPOSEES, ce qu'un brouillon non publie n'est pas.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any, Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit.services import enregistrer_un_evenement
from app.shared.errors import ErreurApplicative

CODE_MODELE_INTROUVABLE: Final = "modele_introuvable"
MESSAGE_MODELE_INTROUVABLE: Final = (
    "Ce modele n'existe pas, ou n'est pas accessible depuis cette entite."
)

CODE_VERSION_INTROUVABLE: Final = "version_de_modele_introuvable"
MESSAGE_VERSION_INTROUVABLE: Final = "Cette version n'existe pas pour ce modele."

CODE_PORTEE_INCOHERENTE: Final = "portee_de_modele_incoherente"
MESSAGE_PORTEE_INCOHERENTE: Final = (
    "`scope_person_id` est requis (et lui seul) pour la portee DSM, "
    "`scope_circle_id` est requis (et lui seul) pour la portee CIRCLE — "
    "modele §13.2."
)

CODE_VERSION_IMMUABLE: Final = "version_de_modele_immuable"
MESSAGE_VERSION_IMMUABLE: Final = (
    "Cette version est publiee ou retiree : elle est immuable — modele §13.3."
)

CODE_TACHE_HORS_PERIMETRE: Final = "tache_hors_perimetre_du_modele"
MESSAGE_TACHE_HORS_PERIMETRE: Final = (
    "Une tache de reference doit etre GLOBALE ou propre a l'entite de ce modele — "
    "jamais celle d'une autre entite."
)


@dataclasses.dataclass(frozen=True, slots=True)
class Modele:
    """Le conteneur — modele §13.2. `entity_id=None` : modele GLOBAL."""

    id: uuid.UUID
    entity_id: uuid.UUID | None
    name: str
    target_status: str
    scope_type: str
    scope_person_id: uuid.UUID | None
    scope_circle_id: uuid.UUID | None
    state: str


@dataclasses.dataclass(frozen=True, slots=True)
class VersionDeModele:
    """Une publication du modele — modele §13.3."""

    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    state: str
    change_summary: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class NouvelleTacheDeVersion:
    """Une ligne demandee pour composer une version — modele §13.4."""

    task_reference_id: uuid.UUID
    required: bool
    due_offset_days: int
    title_override: str | None
    description_override: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class TacheDeVersion:
    """Une ligne telle qu'ecrite — modele §13.4, `display_order` = index."""

    id: uuid.UUID
    template_version_id: uuid.UUID
    task_reference_id: uuid.UUID
    display_order: int
    required: bool
    due_offset_days: int
    title_override: str | None
    description_override: str | None


_COLONNES_MODELE: Final = (
    "id, entity_id, name, target_status, scope_type, scope_person_id, scope_circle_id, state"
)

#  Seul un litteral FIXE de ce module est concatene ci-dessous — jamais une
#  valeur de l'appelant — meme discipline que `catalogue.py` (noqa: S608).
_INSERER_MODELE: Final = f"""
INSERT INTO onboarding_template
    (entity_id, name, target_status, scope_type, scope_person_id, scope_circle_id)
VALUES (:entite, :name, :target_status, :scope_type, :scope_person_id, :scope_circle_id)
RETURNING {_COLONNES_MODELE}
"""  # noqa: S608

#  **PAS filtre sur `entity_id = :entite`** : un modele GLOBAL (`entity_id
#  IS NULL`) doit rester atteignable depuis N'IMPORTE QUELLE entite du
#  chemin — meme lecture que le catalogue de `T4`. La coherence d'entite d'un
#  modele NON global est verifiee par l'appelant (`_dans_le_perimetre_de_l_
#  entite`), pas par cette requete.
_LIRE_MODELE: Final = f"""
SELECT {_COLONNES_MODELE} FROM onboarding_template WHERE id = :modele
"""  # noqa: S608

#  T14 : meme lecture que `_LIRE_MODELE` -- un modele GLOBAL (`entity_id IS
#  NULL`) est SERVI depuis toute entite, le filtrage par role (§9) est fait
#  par l'appelant via `peut_gerer_un_modele_de_cette_portee`, jamais ici.
_LISTER_MODELES: Final = f"""
SELECT {_COLONNES_MODELE} FROM onboarding_template
WHERE entity_id = :entite OR entity_id IS NULL
ORDER BY name
"""  # noqa: S608

_COLONNES_VERSION: Final = "id, template_id, version_number, state, change_summary"

_INSERER_VERSION: Final = f"""
INSERT INTO onboarding_template_version (template_id, version_number, change_summary)
VALUES (:template, COALESCE(
    (SELECT MAX(version_number) FROM onboarding_template_version WHERE template_id = :template), 0
) + 1, :change_summary)
RETURNING {_COLONNES_VERSION}
"""  # noqa: S608

_LIRE_VERSION: Final = f"""
SELECT {_COLONNES_VERSION} FROM onboarding_template_version
WHERE id = :version AND template_id = :template
"""  # noqa: S608

#  T14 : les versions de PLUSIEURS modeles en une seule requete, plutot que
#  N+1 -- `ANY(:modeles)` sur un tableau, jamais une boucle Python d'appels.
_LISTER_VERSIONS_DE_PLUSIEURS_MODELES: Final = f"""
SELECT {_COLONNES_VERSION} FROM onboarding_template_version
WHERE template_id = ANY(:modeles)
ORDER BY version_number
"""  # noqa: S608

_COLONNES_TACHE_DE_VERSION: Final = (
    "id, template_version_id, task_reference_id, display_order, required, "
    "due_offset_days, title_override, description_override"
)

_SUPPRIMER_TACHES_DE_LA_VERSION: Final = """
DELETE FROM onboarding_template_task WHERE template_version_id = :version
"""

_INSERER_TACHE_DE_VERSION: Final = f"""
INSERT INTO onboarding_template_task
    (template_version_id, task_reference_id, display_order, required,
     due_offset_days, title_override, description_override)
VALUES (:version, :task_reference_id, :display_order, :required,
        :due_offset_days, :title_override, :description_override)
RETURNING {_COLONNES_TACHE_DE_VERSION}
"""  # noqa: S608

#  `entity_id` seul : GLOBAL (NULL) ou de la MEME entite que le modele — c'est
#  l'appelant (`_tache_dans_le_perimetre_du_modele`) qui compare, en lisant
#  cette seule colonne. Pas de jointure : une tache inexistante rend `None`,
#  distinguee du refus de perimetre par le meme code (§2.5, un seul gabarit).
_ENTITE_DE_LA_TACHE: Final = """
SELECT entity_id FROM onboarding_task_reference WHERE id = :tache AND archived_at IS NULL
"""


def _modele_depuis_la_ligne(ligne: Any) -> Modele:
    entity_id = ligne["entity_id"]
    scope_person_id = ligne["scope_person_id"]
    scope_circle_id = ligne["scope_circle_id"]
    return Modele(
        id=uuid.UUID(str(ligne["id"])),
        entity_id=None if entity_id is None else uuid.UUID(str(entity_id)),
        name=str(ligne["name"]),
        target_status=str(ligne["target_status"]),
        scope_type=str(ligne["scope_type"]),
        scope_person_id=None if scope_person_id is None else uuid.UUID(str(scope_person_id)),
        scope_circle_id=None if scope_circle_id is None else uuid.UUID(str(scope_circle_id)),
        state=str(ligne["state"]),
    )


def _version_depuis_la_ligne(ligne: Any) -> VersionDeModele:
    return VersionDeModele(
        id=uuid.UUID(str(ligne["id"])),
        template_id=uuid.UUID(str(ligne["template_id"])),
        version_number=int(ligne["version_number"]),
        state=str(ligne["state"]),
        change_summary=ligne["change_summary"],
    )


def _tache_depuis_la_ligne(ligne: Any) -> TacheDeVersion:
    return TacheDeVersion(
        id=uuid.UUID(str(ligne["id"])),
        template_version_id=uuid.UUID(str(ligne["template_version_id"])),
        task_reference_id=uuid.UUID(str(ligne["task_reference_id"])),
        display_order=int(ligne["display_order"]),
        required=bool(ligne["required"]),
        due_offset_days=int(ligne["due_offset_days"]),
        title_override=ligne["title_override"],
        description_override=ligne["description_override"],
    )


def creer_un_modele(
    connexion: Connection,
    *,
    entite: uuid.UUID | None,
    name: str,
    target_status: str,
    scope_type: str,
    scope_person_id: uuid.UUID | None,
    scope_circle_id: uuid.UUID | None,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> Modele:
    """Creer le conteneur d'un modele — modele §13.2. `entite=None` : GLOBAL.

    `acteur`/`instant` (LOT 10, `T6`) ne servent qu'a l'ecriture d'audit : le
    modele §13.2 ne declare ni `created_by_person_id` ni aucune date propre a
    ce geste.
    """
    ligne = (
        connexion.execute(
            text(_INSERER_MODELE),
            {
                "entite": entite,
                "name": name,
                "target_status": target_status,
                "scope_type": scope_type,
                "scope_person_id": scope_person_id,
                "scope_circle_id": scope_circle_id,
            },
        )
        .mappings()
        .one()
    )
    cree = _modele_depuis_la_ligne(ligne)

    #  LOT 10, `T6` : `entity_id=entite` — None pour un modele GLOBAL, meme
    #  lecture que `creer_une_entite` (`T3`) ou `entity_id` est la ressource
    #  elle-meme. Litteral : la matrice §9 ne porte aucune enum d'action.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="modele_cree",
        resource_type="onboarding_template",
        resource_reference=cree.id,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation du modele d'onboarding « {name} »",
    )
    return cree


def lire_un_modele(connexion: Connection, *, entite: uuid.UUID, modele: uuid.UUID) -> Modele | None:
    """Le modele, s'il existe et est accessible depuis `entite`.

    **ACCESSIBLE** veut dire : GLOBAL (visible depuis toute entite), ou propre
    a CETTE entite precisement — jamais celle d'une autre, meme isolation que
    le catalogue de `T4`.
    """
    ligne = connexion.execute(text(_LIRE_MODELE), {"modele": modele}).mappings().one_or_none()
    if ligne is None:
        return None
    trouve = _modele_depuis_la_ligne(ligne)
    if trouve.entity_id is not None and trouve.entity_id != entite:
        return None
    return trouve


def lister_les_modeles(connexion: Connection, *, entite: uuid.UUID) -> tuple[Modele, ...]:
    """Les modeles ATTEIGNABLES depuis cette entite — les siens, et les GLOBAUX.

    **AUCUN FILTRE DE ROLE ICI** : ni `T5` ni `T6` n'ont jamais lu plusieurs
    modeles a la fois, donc rien n'existait avant `T14` (l'ecran
    d'administration) pour ce besoin. Le filtrage fin — un DSM ne voit que
    SES modeles, un Booster que ceux de SON cercle — est celui de
    `peut_gerer_un_modele_de_cette_portee` (`perimetre.py`), applique par
    l'appelant SUR CETTE LISTE, jamais redit ici en SQL : une seconde
    derivation de la meme regle divergerait au premier changement (§7.27).
    """
    lignes = connexion.execute(text(_LISTER_MODELES), {"entite": entite}).mappings().all()
    return tuple(_modele_depuis_la_ligne(ligne) for ligne in lignes)


def lister_les_versions(
    connexion: Connection, *, modeles: Sequence[uuid.UUID]
) -> tuple[VersionDeModele, ...]:
    """Les versions de plusieurs modeles a la fois — T14, l'ecran qui montre
    l'etat de cycle de vie de chacune sans un aller-retour par modele."""
    if not modeles:
        return ()
    lignes = (
        connexion.execute(text(_LISTER_VERSIONS_DE_PLUSIEURS_MODELES), {"modeles": list(modeles)})
        .mappings()
        .all()
    )
    return tuple(_version_depuis_la_ligne(ligne) for ligne in lignes)


def creer_une_version(
    connexion: Connection,
    *,
    modele: uuid.UUID,
    entite_du_modele: uuid.UUID | None,
    change_summary: str | None,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> VersionDeModele:
    """Creer une nouvelle version brouillon — modele §13.3.

    `version_number` est calcule EN SQL, dans la MEME requete que l'insertion
    — jamais lu puis recalcule en Python, ce qui laisserait une fenetre a une
    course entre deux creations concurrentes de la meme version.

    `entite_du_modele`/`acteur`/`instant` (LOT 10, `T6`) : la version n'a pas
    d'`entity_id` propre (elle herite celui du modele, voir l'en-tete de
    classe) — l'appelant le transmet pour que l'audit porte le MEME perimetre
    que le modele, jamais une colonne ecrite sur `onboarding_template_version`.
    """
    ligne = (
        connexion.execute(
            text(_INSERER_VERSION), {"template": modele, "change_summary": change_summary}
        )
        .mappings()
        .one()
    )
    creee = _version_depuis_la_ligne(ligne)

    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="version_creee",
        resource_type="onboarding_template_version",
        resource_reference=creee.id,
        entity_id=entite_du_modele,
        actor_person_id=acteur,
        summary=f"Creation de la version {creee.version_number} du modele",
    )
    return creee


def lire_une_version(
    connexion: Connection, *, modele: uuid.UUID, version: uuid.UUID
) -> VersionDeModele | None:
    """La version, si elle existe et appartient bien a `modele`."""
    ligne = (
        connexion.execute(text(_LIRE_VERSION), {"version": version, "template": modele})
        .mappings()
        .one_or_none()
    )
    return None if ligne is None else _version_depuis_la_ligne(ligne)


def _tache_dans_le_perimetre_du_modele(
    connexion: Connection, *, entite_du_modele: uuid.UUID | None, tache: uuid.UUID
) -> bool:
    """Modele §13.1, confirme par `T4` (compte-rendu §2.4) : une tache GLOBALE
    est reutilisable par tout modele ; une tache D'ENTITE ne l'est que dans SA
    propre entite. Une tache introuvable (ou archivee) est refusee de la meme
    facon — §2.5, un seul gabarit."""
    ligne = connexion.execute(text(_ENTITE_DE_LA_TACHE), {"tache": tache}).one_or_none()
    if ligne is None:
        return False
    entite_de_la_tache = ligne[0]
    if entite_de_la_tache is None:
        return True
    return uuid.UUID(str(entite_de_la_tache)) == entite_du_modele


def definir_les_taches_de_la_version(
    connexion: Connection,
    *,
    modele: Modele,
    version: VersionDeModele,
    taches: Sequence[NouvelleTacheDeVersion],
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> tuple[TacheDeVersion, ...]:
    """Poser (ou reordonner) la liste ENTIERE des taches d'une version brouillon.

    **REFUSE SUR UNE VERSION PUBLIEE OU RETIREE** — modele §13.3, le temoin de
    cette sous-etape. **REFUSE SUR UNE TACHE HORS PERIMETRE** — voir l'en-tete
    du module. Les deux refus sont verifies AVANT toute ecriture : la liste
    precedente reste intacte si l'un des deux mord.

    LOT 10, `T6` : UN SEUL `audit_event` pour l'appel entier — « poser la
    liste » est UNE action metier, meme discipline que `reordonner_les_liens`
    (LOT 6) et `gerer_les_medias_d_un_evenement` (LOT 8). **Mais, comme ce
    dernier et a la difference de `reordonner_les_liens`, AUCUN retour
    anticipe n'existe sur une liste vide** : `_SUPPRIMER_TACHES_DE_LA_VERSION`
    s'execute INCONDITIONNELLEMENT ci-dessous, et vider la liste des taches
    d'une version brouillon est une forme normale de ce geste. Un `audit_event`
    est donc ecrit MEME quand `taches=()`.
    """
    if version.state != "draft":
        raise ErreurApplicative(
            code=CODE_VERSION_IMMUABLE,
            message=MESSAGE_VERSION_IMMUABLE,
            statut=status.HTTP_409_CONFLICT,
        )
    for demandee in taches:
        if not _tache_dans_le_perimetre_du_modele(
            connexion, entite_du_modele=modele.entity_id, tache=demandee.task_reference_id
        ):
            raise ErreurApplicative(
                code=CODE_TACHE_HORS_PERIMETRE,
                message=MESSAGE_TACHE_HORS_PERIMETRE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

    connexion.execute(text(_SUPPRIMER_TACHES_DE_LA_VERSION), {"version": version.id})
    ecrites = []
    for rang, demandee in enumerate(taches):
        ligne = (
            connexion.execute(
                text(_INSERER_TACHE_DE_VERSION),
                {
                    "version": version.id,
                    "task_reference_id": demandee.task_reference_id,
                    "display_order": rang,
                    "required": demandee.required,
                    "due_offset_days": demandee.due_offset_days,
                    "title_override": demandee.title_override,
                    "description_override": demandee.description_override,
                },
            )
            .mappings()
            .one()
        )
        ecrites.append(_tache_depuis_la_ligne(ligne))
    resultat = tuple(ecrites)

    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="taches_de_version_definies",
        resource_type="onboarding_template_version",
        resource_reference=version.id,
        entity_id=modele.entity_id,
        actor_person_id=acteur,
        summary=(
            f"Composition des taches de la version {version.version_number} "
            f"({len(resultat)} tache(s))"
        ),
        new_values={
            "taches": [
                {
                    "task_reference_id": str(t.task_reference_id),
                    "required": t.required,
                    "due_offset_days": t.due_offset_days,
                }
                for t in resultat
            ]
        },
    )
    return resultat
