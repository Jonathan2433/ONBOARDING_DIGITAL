"""Une instance de parcours depuis la date d'arrivee — modele §13.5/§13.6, matrice §8.1, `T7`.

CE QUE `T7` LIVRE, ET CE QUE `T10` Y AJOUTE

  Deux gestes : affecter un parcours (matrice §8.1, « Affecter un parcours »)
  et le lire (« Consulter son parcours » / « ... d'un collaborateur »).
  Aucune nouvelle table : `onboarding_instance` et `onboarding_instance_task`
  existent depuis `T1`, jamais encore ecrites.

  `T10` ajoute un TROISIEME geste, `remplacer_le_parcours_apres_changement_de_
  statut` — matrice §8.1 « Remplacer le parcours apres changement de statut »,
  §8.2 « en cas de changement de situation, le parcours est remplace par le
  nouveau modele », modele §6.5 « un changement de STATUT declenche
  l'evaluation du parcours d'onboarding », §14.1 (diagramme de sequence).

  **AUCUNE ROUTE PROPRE, ET CE N'EST PAS UN OUBLI.** Le diagramme §14.1 ne
  nomme que « Service metier » et « PostgreSQL » — aucun acteur HTTP. La
  grille matrice de cette ligne (`DSM` Consultants, `ESM` Entite, `BOOST`
  Cercle, `ADM-E` Entite, `SUPER` Global) est EXACTEMENT celle de « Affecter
  un parcours » (`T7`, `_dans_le_perimetre_du_parcours`) ET celle du champ
  `STATUT` de `resoudre_le_perimetre` (LOT 5, `app/permissions/perimetre.py`)
  sur ses trois roles a portee entiere (`ESM`/`ADM-E`/`SUPER` -> tous les
  champs) et son DSM rattache (meme requete `_RATTACHE_A_CE_DSM`, recopiee
  dans les deux modules — §7.27). Seule la ligne `BOOST` differe en toutes
  lettres : LOT 5 restreint au membre PRINCIPAL du cercle, l'onboarding
  n'importe pas lequel — mais quiconque reussit a ECRIRE le champ `STATUT`
  (donc a passe la grille LOT 5, la plus stricte des deux) est *a fortiori*
  dans la grille, plus large, de cette ligne-ci. Poser une SECONDE garde ici
  serait une regle pour un ensemble d'acteurs deja inclus dans le premier —
  §7.27 encore. `remplacer_le_parcours_apres_changement_de_statut` est donc
  appelee PAR `app.people.ecriture._ecrire_le_statut`, dans la MEME
  transaction, apres que ce module a deja verifie le droit d'ecrire `STATUT`.

  **LE DIAGRAMME §24.2 GOUVERNE ENCORE, POUR SA MOITIE RESTANTE.** `Todo ->
  Cancelled` (« remplacement de parcours ») et `Completed -> Preserved`
  (« tache commune conservee ») sont les DEUX transitions que `T7`/`T8`/`T9`
  n'exercaient pas. Le modele ne declare que QUATRE etats sur
  `onboarding_instance_task` (§13.6 : `todo`, `completed`, `reopened`,
  `cancelled`) — pas de cinquieme valeur `preserved`. « Preserved » n'est donc
  PAS un etat ecrit : une tache RETENUE reste `completed`, dans une instance
  qui n'est plus `active` — `lire_l_instance_active` ne la trouvera plus
  jamais, et aucune route (`T8`/`T9`) n'agit sur une instance non active. La
  preservation est donc GRATUITE, une consequence du garde-fou deja pose,
  jamais une colonne a ajouter. `todo` ET `reopened` (une tache pas encore
  refaite) rejoignent tous deux `cancelled` — le diagramme ne nomme que
  `Todo`, mais `reopened` est le MEME etat « pas termine » sous un autre nom,
  et le laisser trainer sur une instance devenue `replaced` serait une
  troisieme forme de tache orpheline que ni le diagramme ni le modele ne
  decrivent.

  **`ECART-013` EST MIS A L'EPREUVE POUR DE VRAI, ICI.** Le catalogue
  (`onboarding_task_reference`, `T4`) porte un identifiant STABLE partage par
  les DEUX modeles (mission et intercontrat) : une tache commune aux deux se
  reconnait par ce SEUL identifiant, jamais par une correspondance de titre.
  Les taches `completed` de l'ANCIENNE instance sont donc lues par
  `task_reference_id`, et toute tache de la NOUVELLE version qui porte le
  MEME identifiant recoit une ligne `completed` d'emblee — `completed_at`/
  `completed_by_person_id` COPIES tels quels (meme discipline que `T9` sur la
  reouverture : preserver la trace, jamais l'inventer), `title_snapshot`/
  `description_snapshot`/`required`/`due_at` recalcules depuis la NOUVELLE
  version (une instance est toujours un instantane DE SA VERSION, `T7`).
  L'evenement pose est `RETAINED_ON_REPLACEMENT`, jamais `ASSIGNED` : cette
  tache n'a pas ete affectee, elle a ete RETENUE.

  **LA FENETRE DE `reference_date` N'EST PAS `arrival_date`, ET C'EST
  DELIBERE.** `affecter_un_parcours` ancre les echeances sur la date
  d'ARRIVEE — la seule date que `T7` connaisse. Un remplacement a lieu des
  MOIS plus tard : ancrer sur `arrival_date` daterait les echeances de la
  NOUVELLE version dans le passe (un `due_offset_days=3` tomberait trois
  jours apres l'embauche, pas apres le remplacement). `reference_date` du
  nouveau parcours est donc l'INSTANT du changement de statut lui-meme —
  litteralement `starts_at` de la nouvelle ligne `professional_status_
  assignment` que `_ecrire_le_statut` vient de poser, la seule date que ce
  remplacement connaisse et qui ait un sens pour SES propres echeances.

  **AUCUN `outbox_message` NI `async_job` N'EST ECRIT ICI, ET CE N'EST PAS UN
  OUBLI.** Le diagramme §14.1 termine par « Job disponible via outbox » /
  « Worker recalcule progression et echeances secondaires ». Mesure avant
  d'ecrire : AUCUNE ligne du depot n'ecrit encore `outbox_message` ni
  `async_job` — `app/auth/idempotence.py` (LOT 3 `T7`) nomme deja ces deux
  tables comme un mecanisme qui « restera porte … au LOT 11 ». Et la
  progression, critere de sortie n°3 du lot, n'est **JAMAIS STOCKEE** —
  aucune colonne n'existe pour qu'un worker la « recalcule ». Inventer ici un
  message pour un consommateur qui n'existe nulle part serait §6.5. Residuel
  nomme, non bloquant : voir le compte rendu.


LE BON MODELE — ORDRE DE PRIORITE, ARBITRAGE DE JONATHAN DU 27/09/2026

  Un nouvel arrivant porte un statut cible (mission/intercontrat), un DSM et un
  cercle principal, tous VERROUILLES des sa fiche d'arrivee (matrice §6.2).
  Plusieurs modeles PUBLIES peuvent donc correspondre a son statut, a des
  niveaux differents : le sien propre (DSM), celui de son cercle (Booster),
  celui de son entite, ou le modele generique global. Le corpus ne tranche nulle
  part quel niveau prime — recherche dans la matrice, le modele et le cahier,
  rien ne le dit.

  **`DSM` > `CIRCLE` > `ENTITY` > `GLOBAL`.** Le plus specifique gagne, dans cet
  ordre : un modele DSM ou Cercle n'existe QUE pour remplacer le modele general
  pour un sous-ensemble precis de personnes — sans cette priorite, un DSM
  n'aurait jamais de raison d'en publier un (§9.1, matrice). Residuel nomme,
  non instruit ici faute d'occurrence connue : PLUSIEURS modeles publies au
  MEME niveau (deux modeles `ENTITY` pour `mission`, par exemple) departagent
  par la publication la plus RECENTE — aucune contrainte du corpus n'exclut ce
  cas, et rien n'impose non plus un ordre different.

`due_at` EST CALCULE EN BASE, JAMAIS EN PYTHON

  Meme discipline que `recent_until` (`T3`) : `reference_date + due_offset_days
  jours`, interprete a MINUIT UTC — le modele §13.4 ne donne aucune heure, et
  aucune section n'exige de fuseau local. Snapshot immediat : une fois pose,
  `due_at` ne bouge plus meme si `T6` republie une nouvelle version du modele.

UNE SEULE INSTANCE ACTIVE PAR APPARTENANCE — MODELE §13.5, UN INDEX PARTIEL

  `T1` a deja pose `uq_onboarding_instance_membership_active`. L'ecriture ici
  est un COMPARE-ET-POSE ATOMIQUE, `ON CONFLICT ... DO NOTHING RETURNING` —
  meme idiome que l'usage unique du magic link (LOT 3, `T4`) : aucune ligne
  rendue est un refus 409, sans lecture prealable qui laisserait une fenetre de
  course entre deux affectations concurrentes de la MEME appartenance.

LA PROGRESSION EST CALCULEE A CHAQUE LECTURE, JAMAIS STOCKEE

  Critere de sortie n°3 du lot (§1.2 de la fiche) : aucune colonne `progress`
  n'existe, et n'existera pas. `lire_le_parcours` compte les taches
  OBLIGATOIRES `completed` sur le total obligatoire, a chaque appel — un COUNT
  SQL, jamais une valeur ecrite. La « prochaine etape » est la tache non
  terminee dont `due_at` est le plus proche, obligatoire ou non : le modele
  §13.6 ne porte aucun `display_order` sur l'instance (contrairement au
  gabarit, §13.4), et `due_at` est la seule notion d'ordre qui lui survit.

CORRECTIF TROUVE EN ECRIVANT `T8` : L'EVENEMENT `ASSIGNED` MANQUAIT

  Critere de sortie n°4 de la fiche (§1.2) : « les evenements de tache sont
  historises […] `onboarding_task_event`, ecrit a `T7`-`T10` ». `T7` livrait
  la table et l'affectation, mais n'ecrivait AUCUN evenement — un residu non
  nomme dans son propre compte rendu, trouve en relisant ce critere avant
  d'ecrire `T8`. `affecter_un_parcours` recoit desormais `acteur` et pose un
  evenement `ASSIGNED` par tache snapshottee, via `enregistrer_un_evenement_
  de_tache` — la MEME fonction que `T8` emploie pour `COMPLETED`/`CANCELLED`,
  §7.27 : une seule ecriture d'evenement, jamais une par sous-etape.

CE QUE `T11` AJOUTE : DEUX DECLENCHEURS AUTOMATIQUES, DEUX GESTES MANUELS

  Matrice §8.1, ligne « Archiver un parcours termine » : `NEW` = Automatique,
  `ESM`/`ADM-E`/`SUPER` = Entite/Entite/Global, tous les autres a tiret.
  §8.2 (regle metier) : « le parcours est termine lorsque toutes les taches
  obligatoires sont terminees » ET « le depart d'un collaborateur archive le
  parcours et revoque les sessions » — DEUX evenements distincts, DEUX
  fonctions distinctes :

    - `archiver_le_parcours_si_termine`, appelee automatiquement par
      `taches.terminer_une_tache` apres CHAQUE completion — transition directe
      `active -> archived`, `completed_at` POSE (ce parcours a ete acheve) ;
    - `archiver_le_parcours_au_depart`, appelee automatiquement par
      `app.people.archivage.archiver_un_profil` AU DEPART (jamais a
      l'archivage fonctionnel ulterieur de l'appartenance) — meme transition,
      `completed_at` JAMAIS pose (ce parcours a ete INTERROMPU, pas acheve).

  **AUCUNE DES DEUX N'A DE ROUTE PROPRE** — meme motif qu'au `T10` : la
  premiere est un sous-effet de « Marquer une tache comme terminee » (`T8`,
  deja gardee par `Soi`), la seconde un sous-effet du depart (LOT 3 `T9`, deja
  gardee par la route d'archivage d'un profil, LOT 5 `T8`). Poser une garde
  ici serait une regle pour un acteur deja verifie ailleurs (§7.27).

  **DEUX GESTES MANUELS ONT NEANMOINS LEUR PROPRE ROUTE**, parce que la
  matrice leur accorde un droit qui n'est le sous-effet d'AUCUNE autre action
  deja gardee : « Archiver un parcours termine » (le filet manuel de
  `ESM`/`ADM-E`/`SUPER` sur un parcours que l'automatique n'aurait pas
  archive) et « Restaurer un parcours archive » (`ECART-066`, volet parcours,
  RESOLU le 28/09/2026 — l'ESM restaure librement dans son entite, meme
  regime que la restauration d'une version de modele, `T6`/`DEC-605`).
  `perimetre.ROLES_D_ARCHIVAGE_ET_RESTAURATION_DU_PARCOURS` gouverne les
  deux : memes trois roles que la reouverture (`T9`), DSM/BOOST EXCLUS EN
  BLOC — aucune de ces deux lignes n'admet de sous-cas « son propre ».

`COLONNES_TACHE` ET `tache_depuis_la_ligne` SONT PUBLICS, PAS UN OUBLI

  `T8` (`app/onboarding/taches.py`) ecrit `onboarding_instance_task` a son
  tour et rend le MEME `TacheDuParcours` : partager la projection colonnes ->
  dataclasse evite une deuxieme liste qui divergerait de celle-ci au premier
  ajout de champ (§7.27). Seule cette paire quitte le prefixe prive ; le reste
  du module — `_instance_depuis_la_ligne`, les requetes de resolution du
  modele — ne sert qu'ici et le reste.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Any, Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit.services import enregistrer_un_evenement
from app.onboarding.modeles import TypeEvenementTache
from app.shared.errors import ErreurApplicative

CODE_STATUT_INTROUVABLE: Final = "statut_professionnel_introuvable"
MESSAGE_STATUT_INTROUVABLE: Final = (
    "Aucune situation professionnelle active pour cette appartenance — modele §6.5."
)

CODE_AUCUN_MODELE_PUBLIE: Final = "aucun_modele_publie"
MESSAGE_AUCUN_MODELE_PUBLIE: Final = (
    "Aucun modele publie ne correspond a ce statut, pour cette entite, ce DSM ou ce cercle."
)

CODE_PARCOURS_DEJA_ACTIF: Final = "parcours_deja_actif"
MESSAGE_PARCOURS_DEJA_ACTIF: Final = (
    "Une instance active existe deja pour cette appartenance — modele §13.5."
)

CODE_AUCUN_PARCOURS_ACTIF: Final = "aucun_parcours_actif"
MESSAGE_AUCUN_PARCOURS_ACTIF: Final = (
    "Aucune instance active n'existe pour cette appartenance — modele §13.5."
)

CODE_PARCOURS_NON_TERMINE: Final = "parcours_non_termine"
MESSAGE_PARCOURS_NON_TERMINE: Final = (
    "Toutes les taches obligatoires ne sont pas encore completees — matrice §8.1, "
    "« Archiver un parcours termine »."
)

CODE_PARCOURS_NON_ARCHIVE: Final = "parcours_non_archivable"
MESSAGE_PARCOURS_NON_ARCHIVE: Final = (
    "Ce parcours n'est pas archive, ou une autre instance est deja active pour "
    "cette appartenance — matrice §8.1, « Restaurer un parcours archive »."
)

CODE_INSTANCE_INTROUVABLE: Final = "instance_introuvable"
MESSAGE_INSTANCE_INTROUVABLE: Final = (
    "Aucune instance de ce parcours ne correspond a cet identifiant, pour cette appartenance."
)


@dataclasses.dataclass(frozen=True, slots=True)
class TacheDuParcours:
    """Une ligne de `onboarding_instance_task` — snapshot fige a l'affectation."""

    id: uuid.UUID
    task_reference_id: uuid.UUID
    title_snapshot: str
    description_snapshot: str | None
    required: bool
    due_at: dt.datetime
    state: str
    completed_at: dt.datetime | None
    reopened_at: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class Progression:
    """Comptee a chaque lecture — jamais stockee, critere de sortie n°3."""

    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


@dataclasses.dataclass(frozen=True, slots=True)
class Instance:
    """L'instance elle-meme — modele §13.5."""

    id: uuid.UUID
    template_version_id: uuid.UUID
    reference_date: dt.date
    state: str
    started_at: dt.datetime
    completed_at: dt.datetime | None


@dataclasses.dataclass(frozen=True, slots=True)
class Parcours:
    """Ce qu'une lecture (ou une affectation) rend — `None` si rien n'existe."""

    instance: Instance | None
    progression: Progression | None
    prochaine_tache: TacheDuParcours | None
    taches: tuple[TacheDuParcours, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Appartenance:
    """Ce que les routes doivent connaitre de la cible AVANT de resoudre un
    permis — `person_id` pour le raccourci `Soi`, `arrival_date` pour le
    calcul des echeances."""

    person_id: uuid.UUID
    arrival_date: dt.date


_AUCUN_PARCOURS: Final = Parcours(instance=None, progression=None, prochaine_tache=None, taches=())

_LIRE_L_APPARTENANCE: Final = """
SELECT person_id, arrival_date FROM entity_membership
WHERE id = :appartenance AND entity_id = :entite
"""

#  Meme predicat que `dsm_assignment(consultant_membership_id) UNIQUE WHERE
#  ends_at IS NULL` (modele §25.1), mais lu par PLAGE — `period @> :instant` —
#  pour la MEME raison que `_RATTACHE_A_CE_DSM` (`app/onboarding/perimetre.py`) :
#  une affectation future n'est pas encore active, ce qu'`ends_at IS NULL` seul
#  ne verifierait pas.
_DSM_ACTIF: Final = """
SELECT dsm_person_id FROM dsm_assignment
WHERE consultant_membership_id = :appartenance AND entity_id = :entite
  AND archived_at IS NULL AND period @> :instant
"""

_CERCLE_PRINCIPAL_ACTIF: Final = """
SELECT circle_id FROM circle_membership
WHERE entity_membership_id = :appartenance AND entity_id = :entite
  AND membership_type = 'principal' AND archived_at IS NULL AND period @> :instant
"""

_STATUT_ACTIF: Final = """
SELECT status FROM professional_status_assignment
WHERE entity_membership_id = :appartenance AND entity_id = :entite
  AND archived_at IS NULL AND period @> :instant
"""

#  L'ORDRE DE PRIORITE EST UN `CASE` SQL, PAS UNE BOUCLE PYTHON A QUATRE
#  REQUETES : une seule lecture rend directement LE candidat qui gagne, sans
#  fenetre entre plusieurs appels ou un modele pourrait etre archive
#  entre-temps. `:dsm`/`:cercle` a `NULL` neutralisent leurs branches
#  respectives sans garde explicite — `= NULL` n'est jamais vrai en SQL.
_VERSION_A_INSTANCIER: Final = """
SELECT v.id AS version_id, v.template_id
FROM onboarding_template AS t
JOIN onboarding_template_version AS v ON v.template_id = t.id AND v.state = 'published'
WHERE t.target_status = :statut
  AND (
        (t.scope_type = 'DSM' AND t.scope_person_id = :dsm)
     OR (t.scope_type = 'CIRCLE' AND t.scope_circle_id = :cercle)
     OR (t.scope_type = 'ENTITY' AND t.entity_id = :entite)
     OR (t.scope_type = 'GLOBAL')
  )
ORDER BY
  CASE t.scope_type
    WHEN 'DSM' THEN 4
    WHEN 'CIRCLE' THEN 3
    WHEN 'ENTITY' THEN 2
    WHEN 'GLOBAL' THEN 1
  END DESC,
  v.published_at DESC,
  v.version_number DESC
LIMIT 1
"""

_COLONNES_INSTANCE: Final = (
    "id, template_version_id, reference_date, state, started_at, completed_at"
)

#  Compare-et-pose atomique sur l'index partiel de `T1` — voir l'en-tete.
_INSERER_INSTANCE: Final = f"""
INSERT INTO onboarding_instance
    (entity_id, entity_membership_id, template_version_id, reference_date, started_at)
VALUES (:entite, :appartenance, :version, :reference_date, :instant)
ON CONFLICT (entity_membership_id) WHERE state = 'active' DO NOTHING
RETURNING {_COLONNES_INSTANCE}
"""  # noqa: S608

_LIRE_L_INSTANCE_LA_PLUS_RECENTE: Final = f"""
SELECT {_COLONNES_INSTANCE} FROM onboarding_instance
WHERE entity_membership_id = :appartenance AND entity_id = :entite
ORDER BY started_at DESC
LIMIT 1
"""  # noqa: S608

#  `T11`, garde 404 de la restauration : PLUSIEURS instances archivees ou
#  remplacees peuvent exister historiquement pour la MEME appartenance (un
#  changement de statut en cree une nouvelle a chaque fois, `T10`) — jamais
#  « la plus recente », contrairement a `lire_le_parcours`. Seul l'appelant
#  sait LAQUELLE restaurer, d'ou l'identifiant explicite dans le chemin.
_LIRE_UNE_INSTANCE: Final = f"""
SELECT {_COLONNES_INSTANCE} FROM onboarding_instance
WHERE id = :instance AND entity_membership_id = :appartenance AND entity_id = :entite
"""  # noqa: S608

_TACHES_DE_LA_VERSION: Final = """
SELECT tt.task_reference_id, tt.required, tt.due_offset_days,
       COALESCE(tt.title_override, tr.title) AS title,
       COALESCE(tt.description_override, tr.description) AS description
FROM onboarding_template_task AS tt
JOIN onboarding_task_reference AS tr ON tr.id = tt.task_reference_id
WHERE tt.template_version_id = :version
ORDER BY tt.display_order
"""

#  PUBLIQUE : partagee avec `app/onboarding/taches.py` (`T8`) — voir l'en-tete.
COLONNES_TACHE: Final = (
    "id, task_reference_id, title_snapshot, description_snapshot, required, "
    "due_at, state, completed_at, reopened_at"
)

_INSERER_TACHE_INSTANCE: Final = f"""
INSERT INTO onboarding_instance_task
    (entity_id, onboarding_instance_id, task_reference_id, title_snapshot,
     description_snapshot, required, due_at)
VALUES (
    :entite, :instance, :task_reference_id, :title, :description, :required,
    (CAST(:reference_date AS date) + (:due_offset_days || ' days')::interval) AT TIME ZONE 'UTC'
)
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

_LIRE_LES_TACHES_DE_L_INSTANCE: Final = f"""
SELECT {COLONNES_TACHE} FROM onboarding_instance_task
WHERE onboarding_instance_id = :instance
ORDER BY due_at
"""  # noqa: S608

#  L'index partiel de `T1` garantit AU PLUS UNE ligne `state = 'active'` par
#  appartenance — `T8` s'appuie dessus pour resoudre SANS ambiguite l'instance
#  dont les taches sont actionnables, plutot que « la plus recente » (qui
#  pourrait etre `replaced`/`archived` une fois `T10`/`T11` ecrites).
_LIRE_L_INSTANCE_ACTIVE: Final = f"""
SELECT {_COLONNES_INSTANCE} FROM onboarding_instance
WHERE entity_membership_id = :appartenance AND entity_id = :entite AND state = 'active'
"""  # noqa: S608

#  `T11` — voir `lire_l_instance_actionnable` : `active` OU `archived`
#  (l'archivage AUTOMATIQUE ne doit pas fermer la fenetre de cinq minutes de
#  `T8`/`T9`), JAMAIS `replaced` (`T10`, une instance supplantee ne recoit
#  plus AUCUNE action). La plus RECENTE des deux, comme `lire_le_parcours`.
_LIRE_L_INSTANCE_ACTIONNABLE: Final = f"""
SELECT {_COLONNES_INSTANCE} FROM onboarding_instance
WHERE entity_membership_id = :appartenance AND entity_id = :entite
  AND state IN ('active', 'archived')
ORDER BY started_at DESC
LIMIT 1
"""  # noqa: S608

_INSERER_EVENEMENT_TACHE: Final = """
INSERT INTO onboarding_task_event
    (entity_id, onboarding_instance_task_id, event_type, occurred_at, actor_person_id, reason)
VALUES (:entite, :tache, :type_evenement, :instant, :acteur, :motif)
"""

#  `T10`. Precondition dans le `WHERE`, meme discipline que `taches.py` : ne
#  clore que l'instance encore `active` — voir l'en-tete, aucune deuxieme
#  cause d'echec n'est distinguee ici, contrairement a `taches.py`, faute
#  d'appelant externe pouvant se tromper de cible (cette fonction n'est jamais
#  exposee par une route, voir l'en-tete).
_CLORE_L_INSTANCE_REMPLACEE: Final = """
UPDATE onboarding_instance SET state = 'replaced'
 WHERE id = :instance AND entity_id = :entite AND state = 'active'
"""

_LIER_LE_REMPLACEMENT: Final = """
UPDATE onboarding_instance SET replaced_by_instance_id = :nouvelle
 WHERE id = :ancienne AND entity_id = :entite
"""

#  `Todo -> Cancelled` ET `Reopened -> Cancelled` — voir l'en-tete du module,
#  les deux sont « pas encore termine » au sens du diagramme §24.2.
_ANNULER_LES_TACHES_EN_COURS: Final = f"""
UPDATE onboarding_instance_task
   SET state = 'cancelled'
 WHERE onboarding_instance_id = :instance AND entity_id = :entite
   AND state IN ('todo', 'reopened')
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

#  `Completed -> Preserved` — voir l'en-tete : LU ici par `task_reference_id`,
#  l'identifiant stable d'`ECART-013`, jamais par titre.
_TACHES_COMPLETEES_DE_L_INSTANCE: Final = """
SELECT task_reference_id, completed_at, completed_by_person_id
FROM onboarding_instance_task
WHERE onboarding_instance_id = :instance AND entity_id = :entite AND state = 'completed'
"""

#  Une tache RETENUE : `completed` DES LA CREATION, `completed_at`/
#  `completed_by_person_id` COPIES de l'ancienne ligne — voir l'en-tete,
#  jamais effaces ni recalcules. `due_at` est neanmoins recalcule depuis LA
#  NOUVELLE version : une instance est toujours un instantane de SA version.
_INSERER_TACHE_PRESERVEE: Final = f"""
INSERT INTO onboarding_instance_task
    (entity_id, onboarding_instance_id, task_reference_id, title_snapshot,
     description_snapshot, required, due_at, state, completed_at, completed_by_person_id)
VALUES (
    :entite, :instance, :task_reference_id, :title, :description, :required,
    (CAST(:reference_date AS date) + (:due_offset_days || ' days')::interval) AT TIME ZONE 'UTC',
    'completed', :completed_at, :completed_by
)
RETURNING {COLONNES_TACHE}
"""  # noqa: S608


def remplacer_le_parcours_apres_changement_de_statut(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    statut_precedent: str,
    nouveau_statut: str,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> None:
    """Matrice §8.1 « Remplacer le parcours apres changement de statut » /
    §8.2, modele §6.5/§14.1 — voir l'en-tete du module pour le motif complet.

    Appelee UNIQUEMENT par `app.people.ecriture._ecrire_le_statut`, apres
    l'ecriture de la nouvelle ligne `professional_status_assignment`, et
    SEULEMENT quand `statut_precedent != nouveau_statut` — un changement de
    CLIENT seul (meme statut) n'evalue rien ici, voir l'en-tete de
    `_ecrire_le_statut`. Aucune verification de permission propre : voir
    l'en-tete de ce module, la garde deja franchie par l'appelant EST la
    garde de cette ligne.

    Ne fait RIEN si aucune instance `active` n'existe — un collaborateur
    jamais affecte a un parcours n'a rien a remplacer, ce sera le geste
    (humain, matrice §8.1) d'« Affecter un parcours ».

    LOT 10, `T6` : AUCUN `audit_event` separe ici — cette fonction n'a aucun
    appelant HTTP propre, elle est une CONSEQUENCE automatique d'un changement
    de `STATUT`, deja audite PAR CHAMP par `modifier_les_donnees_
    organisationnelles` (`T3` de ce lot, `action_code` reutilisant
    `ChampOrganisationnel`). Le remplacement du parcours est l'IMPLICATION
    metier de ce champ, pas une decision distincte de l'acteur — meme
    discipline que `T3` pour l'import CSV et le transfert en masse.
    """
    active = lire_l_instance_active(connexion, entite=entite, appartenance=appartenance)
    if active is None:
        return

    dsm = _dsm_actif(connexion, entite=entite, appartenance=appartenance, instant=instant)
    cercle = _cercle_principal_actif(
        connexion, entite=entite, appartenance=appartenance, instant=instant
    )
    candidate = connexion.execute(
        text(_VERSION_A_INSTANCIER),
        {"statut": nouveau_statut, "dsm": dsm, "cercle": cercle, "entite": entite},
    ).first()
    if candidate is None:
        raise ErreurApplicative(
            code=CODE_AUCUN_MODELE_PUBLIE,
            message=MESSAGE_AUCUN_MODELE_PUBLIE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    version_id = uuid.UUID(str(candidate[0]))

    #  Lu AVANT toute ecriture sur l'ancienne instance : ni la cloture ni
    #  l'annulation des taches en cours ne touchent les lignes `completed`.
    completees = {
        uuid.UUID(str(ligne["task_reference_id"])): (
            ligne["completed_at"],
            ligne["completed_by_person_id"],
        )
        for ligne in connexion.execute(
            text(_TACHES_COMPLETEES_DE_L_INSTANCE), {"instance": active.id, "entite": entite}
        ).mappings()
    }

    annulees = connexion.execute(
        text(_ANNULER_LES_TACHES_EN_COURS), {"instance": active.id, "entite": entite}
    ).mappings()
    for ligne in annulees:
        enregistrer_un_evenement_de_tache(
            connexion,
            entite=entite,
            tache=ligne["id"],
            type_evenement=TypeEvenementTache.CANCELLED_ON_REPLACEMENT.value,
            instant=instant,
            acteur=acteur,
        )

    #  CLORE PUIS OUVRIR (meme parti que `app.people.ecriture`) : l'ancienne
    #  instance doit avoir quitte `active` AVANT l'insertion de la nouvelle,
    #  sans quoi l'index unique partiel de `T1` refuserait une seconde ligne
    #  `active` pour la meme appartenance.
    connexion.execute(text(_CLORE_L_INSTANCE_REMPLACEE), {"instance": active.id, "entite": entite})

    reference_date = instant.date()
    nouvelle_ligne = (
        connexion.execute(
            text(_INSERER_INSTANCE),
            {
                "entite": entite,
                "appartenance": appartenance,
                "version": version_id,
                "reference_date": reference_date,
                "instant": instant,
            },
        )
        .mappings()
        .one()
    )
    nouvelle_instance = _instance_depuis_la_ligne(nouvelle_ligne)

    connexion.execute(
        text(_LIER_LE_REMPLACEMENT),
        {"ancienne": active.id, "nouvelle": nouvelle_instance.id, "entite": entite},
    )

    lignes_taches = connexion.execute(
        text(_TACHES_DE_LA_VERSION), {"version": version_id}
    ).mappings()
    for ligne_tache in lignes_taches:
        reference = uuid.UUID(str(ligne_tache["task_reference_id"]))
        conservee = completees.get(reference)
        if conservee is not None:
            completed_at, completed_by = conservee
            ecrite = (
                connexion.execute(
                    text(_INSERER_TACHE_PRESERVEE),
                    {
                        "entite": entite,
                        "instance": nouvelle_instance.id,
                        "task_reference_id": ligne_tache["task_reference_id"],
                        "title": ligne_tache["title"],
                        "description": ligne_tache["description"],
                        "required": ligne_tache["required"],
                        "reference_date": reference_date,
                        "due_offset_days": ligne_tache["due_offset_days"],
                        "completed_at": completed_at,
                        "completed_by": completed_by,
                    },
                )
                .mappings()
                .one()
            )
            type_evenement = TypeEvenementTache.RETAINED_ON_REPLACEMENT.value
        else:
            ecrite = (
                connexion.execute(
                    text(_INSERER_TACHE_INSTANCE),
                    {
                        "entite": entite,
                        "instance": nouvelle_instance.id,
                        "task_reference_id": ligne_tache["task_reference_id"],
                        "title": ligne_tache["title"],
                        "description": ligne_tache["description"],
                        "required": ligne_tache["required"],
                        "reference_date": reference_date,
                        "due_offset_days": ligne_tache["due_offset_days"],
                    },
                )
                .mappings()
                .one()
            )
            type_evenement = TypeEvenementTache.ASSIGNED.value
        enregistrer_un_evenement_de_tache(
            connexion,
            entite=entite,
            tache=ecrite["id"],
            type_evenement=type_evenement,
            instant=instant,
            acteur=acteur,
        )


#  `T11` — matrice §8.1 « Archiver un parcours termine », modele §13.5 :
#  « l'archivage automatique intervient apres completion totale des taches
#  obligatoires ». La precondition est DANS le `WHERE`, jamais une lecture
#  prealable : memes discipline que `taches.py` (T8/T9) et que
#  `cycle_de_vie.py` (T6) pour la restauration d'une version. `completed_at`
#  EST pose : ce parcours a ete acheve, pas interrompu — voir la variante
#  « au depart » plus bas, qui ne le pose jamais.
_ARCHIVER_LE_PARCOURS_TERMINE: Final = f"""
UPDATE onboarding_instance SET state = 'archived', completed_at = :instant
 WHERE id = :instance AND entity_id = :entite AND state = 'active'
   AND NOT EXISTS (
       SELECT 1 FROM onboarding_instance_task
       WHERE onboarding_instance_id = :instance AND required = true AND state != 'completed'
   )
RETURNING {_COLONNES_INSTANCE}
"""  # noqa: S608

#  `T11` — matrice §8.2 « le depart d'un collaborateur archive le parcours ».
#  Aucune precondition de completion : un depart archive le parcours qu'il
#  soit termine ou non, et `completed_at` reste NULL — ce parcours n'a pas ete
#  acheve, il a ete INTERROMPU. Appelee par `app.people.archivage.archiver_
#  un_profil`, jamais dupliquee — voir l'en-tete du module.
_ARCHIVER_LE_PARCOURS_AU_DEPART: Final = """
UPDATE onboarding_instance SET state = 'archived'
 WHERE entity_membership_id = :appartenance AND entity_id = :entite AND state = 'active'
RETURNING id
"""

#  `T11` — matrice §8.1 « Restaurer un parcours archive », `ECART-066` (volet
#  parcours) resolu le 28/09/2026 : l'ESM restaure librement dans son entite,
#  meme regime que `peut_restaurer_une_version_de_modele` (T6, DEC-605). La
#  sous-requete correlee refait, de maniere LISIBLE, ce que l'index partiel de
#  `T1` (`uq_onboarding_instance_membership_active`) interdirait de toute
#  facon — §7.32, mais en refusant PROPREMENT plutot que de laisser remonter
#  une `IntegrityError` brute, meme parti que `cycle_de_vie.py` (un seul code
#  de refus, jamais une distinction des causes). `completed_at` est
#  DESAPPOSE : une instance de nouveau `active` ne doit pas porter la marque
#  d'un archivage passe — meme motif que `departure_date` dans
#  `restaurer_un_profil` (LOT 5). Aucune tache n'est rouverte : restaurer un
#  PARCOURS n'est pas restaurer une PERSONNE, et rien dans le corpus ne
#  l'exige.
_RESTAURER_LE_PARCOURS: Final = f"""
UPDATE onboarding_instance
   SET state = 'active', completed_at = NULL
 WHERE id = :instance AND entity_id = :entite AND state = 'archived'
   AND NOT EXISTS (
       SELECT 1 FROM onboarding_instance AS autre
       WHERE autre.entity_membership_id = onboarding_instance.entity_membership_id
         AND autre.entity_id = onboarding_instance.entity_id
         AND autre.state = 'active'
   )
RETURNING {_COLONNES_INSTANCE}
"""  # noqa: S608


def lire_une_instance(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instance: uuid.UUID
) -> Instance | None:
    """Une instance PRECISE de cette appartenance, quel que soit son etat —
    contrairement a `lire_l_instance_active` (`active` seule) et a `lire_le_
    parcours` (la plus recente seule). Sert la garde 404 de la restauration
    (`T11`), voir l'en-tete de `_LIRE_UNE_INSTANCE`."""
    ligne = (
        connexion.execute(
            text(_LIRE_UNE_INSTANCE),
            {"instance": instance, "appartenance": appartenance, "entite": entite},
        )
        .mappings()
        .one_or_none()
    )
    return None if ligne is None else _instance_depuis_la_ligne(ligne)


def archiver_le_parcours_si_termine(
    connexion: Connection, *, entite: uuid.UUID, instance: uuid.UUID, instant: dt.datetime
) -> None:
    """Appelee AUTOMATIQUEMENT par `app.onboarding.taches.terminer_une_tache`,
    apres CHAQUE completion — matrice §8.1, colonne `NEW` = Automatique.

    Ne fait RIEN, silencieusement, si une tache obligatoire reste `todo` ou
    `reopened` — ce n'est pas un echec, c'est le cas courant (la tache qui
    vient d'etre terminee n'etait pas la derniere). Aucune erreur n'est levee
    ici : completer une tache reste un succes, que l'instance se termine ou
    non par le meme geste.

    LOT 10, `T6` : AUCUN `audit_event` separe ici — cette archive AUTOMATIQUE
    est une CONSEQUENCE de « terminer une tache », deja auditee par son
    appelant. Un second evenement decrirait un effet de bord, pas une
    decision distincte de l'acteur — meme lecture que `archiver_le_parcours_
    au_depart` ci-dessous.
    """
    connexion.execute(
        text(_ARCHIVER_LE_PARCOURS_TERMINE),
        {"instance": instance, "entite": entite, "instant": instant},
    )


def archiver_un_parcours_termine(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    instance: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> Instance:
    """Matrice §8.1 « Archiver un parcours termine » — `ESM`/`ADM-E`/`SUPER`
    SEULEMENT (`perimetre.ROLES_D_ARCHIVAGE_ET_RESTAURATION_DU_PARCOURS`),
    geste MANUEL, `T11`.

    L'instance est DEJA resolue par la route (`_resoudre_l_instance_active_
    ou_404`), meme discipline que `terminer_une_tache`/`reouvrir_une_tache`
    (`T8`/`T9`) : le 404 « aucun parcours actif » est la garde de la ROUTE,
    jamais de ce service.

    Refuse 409 si une tache obligatoire n'est pas encore `completed` — cette
    action n'archive qu'un parcours REELLEMENT termine, jamais un parcours en
    cours. Le MEME geste se produit AUTOMATIQUEMENT (`archiver_le_parcours_
    si_termine`, appelee par `taches.terminer_une_tache`) des que la derniere
    tache obligatoire se termine : en pratique, cette route ne trouve donc
    RIEN a faire dans le cas courant, l'automatique ayant deja agi. Elle sert
    de filet pour le residuel — matrice §8.1, l'entitlement existe en toutes
    lettres pour `ESM`/`ADM-E`/`SUPER`, independamment de ce que l'automatique
    couvre deja.

    LOT 10, `T6` : ce geste MANUEL est cable — un acteur humain le declenche,
    verifie par la garde de role. L'automatique (`archiver_le_parcours_si_
    termine`, appelee depuis `terminer_une_tache`) ne l'est PAS separement :
    voir sa propre docstring.
    """
    ligne = (
        connexion.execute(
            text(_ARCHIVER_LE_PARCOURS_TERMINE),
            {"instance": instance, "entite": entite, "instant": instant},
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_PARCOURS_NON_TERMINE,
            message=MESSAGE_PARCOURS_NON_TERMINE,
            statut=status.HTTP_409_CONFLICT,
        )
    archivee = _instance_depuis_la_ligne(ligne)

    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="parcours_archive",
        resource_type="onboarding_instance",
        resource_reference=archivee.id,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Archivage manuel d'un parcours d'onboarding termine",
    )
    return archivee


def archiver_le_parcours_au_depart(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> uuid.UUID | None:
    """Appelee AUTOMATIQUEMENT par `app.people.archivage.archiver_un_profil`,
    au DEPART (`Active --> Departed`, LOT 3 `T9`) — jamais a l'archivage
    FONCTIONNEL de l'appartenance elle-meme (`Departed --> Archived`), pour la
    MEME raison que la revocation des sessions y est deja ancree : le §7.4 (LOT
    3) interdit la fenetre entre les deux. Matrice §8.2 « le depart d'un
    collaborateur archive le parcours ». `T11` s'accroche ici SANS dupliquer
    la logique de revocation — voir l'en-tete du module.

    Rend `None` sans rien ecrire si aucune instance active n'existait : un
    collaborateur jamais affecte a un parcours, ou dont le parcours est deja
    `replaced`/`archived`, n'a rien a archiver de plus.

    LOT 10, `T6` : AUCUN `audit_event` separe ici — cette fonction n'a aucun
    appelant HTTP propre, elle est une CONSEQUENCE de `archiver_un_profil`
    (LOT 2/5, deja audite par `T3` de ce lot). Lui donner un second evenement
    dupliquerait le journal d'UN SEUL geste humain (le depart) plutot que de
    decrire une decision distincte — meme discipline que `T3` pour l'import
    CSV et le transfert en masse, qui « heritent sans cablage separe » des
    fonctions partagees deja auditees.
    """
    ligne = connexion.execute(
        text(_ARCHIVER_LE_PARCOURS_AU_DEPART), {"appartenance": appartenance, "entite": entite}
    ).first()
    return None if ligne is None else uuid.UUID(str(ligne[0]))


def restaurer_un_parcours(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    instance: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> Instance:
    """Matrice §8.1 « Restaurer un parcours archive » — `ESM`/`ADM-E`/`SUPER`
    SEULEMENT, `T11`, `ECART-066` (volet parcours) RESOLU le 28/09/2026 :
    l'ESM restaure librement dans son entite, meme regime que la restauration
    d'une version de modele (`T6`, `DEC-605`) — voir l'en-tete de
    `_RESTAURER_LE_PARCOURS`.

    L'instance est deja resolue par la route (`lire_une_instance`, 404 si
    absente de cette appartenance). Refuse 409 si elle n'est pas `archived`,
    ou si l'appartenance porte deja une instance `active` — l'index partiel
    de `T1` l'interdirait de toute facon.

    `acteur`/`instant` (LOT 10, `T6`) ne servent que l'audit : `onboarding_
    instance` ne declare aucune colonne pour tracer qui restaure, ni quand.
    """
    ligne = (
        connexion.execute(text(_RESTAURER_LE_PARCOURS), {"instance": instance, "entite": entite})
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_PARCOURS_NON_ARCHIVE,
            message=MESSAGE_PARCOURS_NON_ARCHIVE,
            statut=status.HTTP_409_CONFLICT,
        )
    restauree = _instance_depuis_la_ligne(ligne)

    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code="parcours_restaure",
        resource_type="onboarding_instance",
        resource_reference=restauree.id,
        entity_id=entite,
        actor_person_id=acteur,
        summary="Restauration d'un parcours d'onboarding archive",
    )
    return restauree


def tache_depuis_la_ligne(ligne: Any) -> TacheDuParcours:
    return TacheDuParcours(
        id=uuid.UUID(str(ligne["id"])),
        task_reference_id=uuid.UUID(str(ligne["task_reference_id"])),
        title_snapshot=str(ligne["title_snapshot"]),
        description_snapshot=ligne["description_snapshot"],
        required=bool(ligne["required"]),
        due_at=ligne["due_at"],
        state=str(ligne["state"]),
        completed_at=ligne["completed_at"],
        reopened_at=ligne["reopened_at"],
    )


def _instance_depuis_la_ligne(ligne: Any) -> Instance:
    return Instance(
        id=uuid.UUID(str(ligne["id"])),
        template_version_id=uuid.UUID(str(ligne["template_version_id"])),
        reference_date=ligne["reference_date"],
        state=str(ligne["state"]),
        started_at=ligne["started_at"],
        completed_at=ligne["completed_at"],
    )


def _progression_depuis_les_taches(taches: tuple[TacheDuParcours, ...]) -> Progression:
    """Comptee sur ce qui vient d'etre LU, jamais reinterrogee — la MEME liste
    sert la progression et l'affichage, ce qui rend les deux impossibles a
    faire diverger par cette API."""
    obligatoires = [t for t in taches if t.required]
    return Progression(
        taches_obligatoires_totales=len(obligatoires),
        taches_obligatoires_terminees=sum(1 for t in obligatoires if t.state == "completed"),
    )


def _prochaine_tache(taches: tuple[TacheDuParcours, ...]) -> TacheDuParcours | None:
    """La premiere tache NI terminee ni annulee, dans l'ordre `due_at` deja
    trie par la requete — voir l'en-tete, aucun `display_order` ne survit sur
    l'instance."""
    for tache in taches:
        if tache.state not in ("completed", "cancelled"):
            return tache
    return None


def _dsm_actif(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instant: dt.datetime
) -> uuid.UUID | None:
    ligne = connexion.execute(
        text(_DSM_ACTIF), {"appartenance": appartenance, "entite": entite, "instant": instant}
    ).first()
    return None if ligne is None else uuid.UUID(str(ligne[0]))


def _cercle_principal_actif(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instant: dt.datetime
) -> uuid.UUID | None:
    ligne = connexion.execute(
        text(_CERCLE_PRINCIPAL_ACTIF),
        {"appartenance": appartenance, "entite": entite, "instant": instant},
    ).first()
    return None if ligne is None else uuid.UUID(str(ligne[0]))


def _statut_actif(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID, instant: dt.datetime
) -> str | None:
    ligne = connexion.execute(
        text(_STATUT_ACTIF), {"appartenance": appartenance, "entite": entite, "instant": instant}
    ).first()
    return None if ligne is None else str(ligne[0])


def lire_l_appartenance(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> Appartenance | None:
    """Sert la garde 404 unique des routes — jamais un chemin distinct pour
    « appartenance inconnue », meme discipline que `T2`/`T3` (voir l'en-tete
    de `routes.py`) — et le `person_id` dont le raccourci `Soi` a besoin."""
    ligne = (
        connexion.execute(
            text(_LIRE_L_APPARTENANCE), {"appartenance": appartenance, "entite": entite}
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        return None
    return Appartenance(
        person_id=uuid.UUID(str(ligne["person_id"])), arrival_date=ligne["arrival_date"]
    )


def lire_l_instance_active(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> Instance | None:
    """L'instance `active` de cette appartenance, s'il en existe une — jamais
    « la plus recente » : `T8`/`T9` n'agissent QUE sur un parcours vivant,
    jamais sur une instance `replaced` (`T10`) ou `archived` (`T11`). L'index
    partiel de `T1` garantit qu'au plus une ligne correspond.

    **`EtatInstance.COMPLETED` RESTE DECLARE MAIS JAMAIS PRODUIT, ET C'EST
    VERIFIE, PAS UN OUBLI.** Le modele §13.5 le liste comme une des quatre
    valeurs possibles de `state`, mais AUCUNE section du corpus ne decrit de
    transition qui y mene : le cahier dit partout « un parcours termine est
    ARCHIVE » (§8.2, `US007`/`US008`), jamais « … est COMPLETE ». `T11`
    transitionne donc directement `active -> archived` des la completion
    totale des taches obligatoires, sans jamais ecrire `completed` — meme
    classe que `Completed -> Preserved` pour les taches (`T10`, voir
    l'en-tete) : une valeur du modele qui ne correspond a AUCUN etat
    reellement ecrit."""
    ligne = (
        connexion.execute(
            text(_LIRE_L_INSTANCE_ACTIVE), {"appartenance": appartenance, "entite": entite}
        )
        .mappings()
        .one_or_none()
    )
    return None if ligne is None else _instance_depuis_la_ligne(ligne)


def lire_l_instance_actionnable(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> Instance | None:
    """L'instance sur laquelle `taches.terminer_une_tache`/`annuler_la_
    completion`/`reouvrir_une_tache` peuvent encore agir — `T11`.

    **`active` OU `archived`, JAMAIS `replaced`.** L'archivage AUTOMATIQUE a
    la completion (`archiver_le_parcours_si_termine`) ne doit PAS fermer la
    fenetre de cinq minutes de `T8` ni la reouverture administrative de `T9` :
    completer la DERNIERE tache obligatoire archive le parcours dans le MEME
    geste, et le nouvel arrivant doit pouvoir annuler CETTE completion comme
    n'importe quelle autre. Une instance `replaced` (`T10`), elle, est
    VRAIMENT supplantee — ses taches restent frigees pour toujours, aucune
    action n'y a jamais ete permise depuis `T10`.

    La plus RECENTE des deux, meme discipline que `lire_le_parcours` : si un
    NOUVEAU parcours a ete affecte apres l'archivage automatique d'un
    precedent, les taches de l'ancien ne sont plus actionnables par cette
    voie — `restaurer_un_parcours` (`T11`) est le geste EXPLICITE pour les
    rouvrir, jamais une action de tache qui le ferait par effet de bord.
    """
    ligne = (
        connexion.execute(
            text(_LIRE_L_INSTANCE_ACTIONNABLE), {"appartenance": appartenance, "entite": entite}
        )
        .mappings()
        .one_or_none()
    )
    return None if ligne is None else _instance_depuis_la_ligne(ligne)


def enregistrer_un_evenement_de_tache(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    tache: uuid.UUID,
    type_evenement: str,
    instant: dt.datetime,
    acteur: uuid.UUID | None,
    motif: str | None = None,
) -> None:
    """Journal §13.7 — un acteur NULLABLE, meme nature que `auth_event`
    (LOT 3) : voir le commentaire du modele sur `OnboardingTaskEvent`. Partagee
    par `affecter_un_parcours` (`ASSIGNED`, correctif de `T7`) et par
    `app/onboarding/taches.py` (`COMPLETED`/`CANCELLED`, `T8`)."""
    connexion.execute(
        text(_INSERER_EVENEMENT_TACHE),
        {
            "entite": entite,
            "tache": tache,
            "type_evenement": type_evenement,
            "instant": instant,
            "acteur": acteur,
            "motif": motif,
        },
    )


def _lire_les_taches(connexion: Connection, *, instance: uuid.UUID) -> tuple[TacheDuParcours, ...]:
    lignes = connexion.execute(
        text(_LIRE_LES_TACHES_DE_L_INSTANCE), {"instance": instance}
    ).mappings()
    return tuple(tache_depuis_la_ligne(ligne) for ligne in lignes)


def lire_le_parcours(
    connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
) -> Parcours:
    """L'instance la plus recente de cette appartenance, ses taches et sa
    progression — `Parcours` vide si aucune instance n'existe encore, jamais
    une erreur : affecter un parcours est un geste SEPARE (§8.1)."""
    ligne = (
        connexion.execute(
            text(_LIRE_L_INSTANCE_LA_PLUS_RECENTE), {"appartenance": appartenance, "entite": entite}
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        return _AUCUN_PARCOURS
    instance = _instance_depuis_la_ligne(ligne)
    taches = _lire_les_taches(connexion, instance=instance.id)
    return Parcours(
        instance=instance,
        progression=_progression_depuis_les_taches(taches),
        prochaine_tache=_prochaine_tache(taches),
        taches=taches,
    )


def affecter_un_parcours(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    cible: Appartenance,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> Parcours:
    """Matrice §8.1 « Affecter un parcours » — modele §13.5/§13.4.

    `cible` est DEJA RESOLUE par l'appelant (`lire_l_appartenance`), meme
    discipline que `creer_une_version` recevant un `Modele` deja lu (`T5`) :
    le 404 « appartenance inconnue » est la garde de la ROUTE, jamais du
    service.

    Resout le statut actif, le DSM et le cercle de l'appartenance, PUIS le
    modele a instancier par la priorite DSM > CIRCLE > ENTITY > GLOBAL (voir
    l'en-tete), snapshotte ses taches, et refuse 409 sur une seconde instance
    active — l'index partiel de `T1` le garantit, cette fonction le traduit.

    `acteur` : CORRECTIF trouve en ecrivant `T8` (voir l'en-tete du module) —
    une tache snapshottee pose desormais son evenement `ASSIGNED`, avec pour
    acteur la personne qui a affecte ce parcours, jamais `None` : « Affecter
    un parcours » est un geste HUMAIN (§8.1), pas un automatisme.

    LOT 10, `T6` : UN SEUL `audit_event` pour l'appel entier, meme si la
    boucle ci-dessous pose un `onboarding_task_event` PAR tache snapshottee —
    « affecter un parcours » est UNE action metier, jamais une par tache.
    `action_code` reutilise `TypeEvenementTache.ASSIGNED`, le vocabulaire
    DEJA pose par le journal propre a ce domaine (§13.7) — meme lecture que
    `TypeEvenementAuth` a `T2`.
    """
    reference_date = cible.arrival_date

    statut = _statut_actif(connexion, entite=entite, appartenance=appartenance, instant=instant)
    if statut is None:
        raise ErreurApplicative(
            code=CODE_STATUT_INTROUVABLE,
            message=MESSAGE_STATUT_INTROUVABLE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    dsm = _dsm_actif(connexion, entite=entite, appartenance=appartenance, instant=instant)
    cercle = _cercle_principal_actif(
        connexion, entite=entite, appartenance=appartenance, instant=instant
    )

    candidate = connexion.execute(
        text(_VERSION_A_INSTANCIER),
        {"statut": statut, "dsm": dsm, "cercle": cercle, "entite": entite},
    ).first()
    if candidate is None:
        raise ErreurApplicative(
            code=CODE_AUCUN_MODELE_PUBLIE,
            message=MESSAGE_AUCUN_MODELE_PUBLIE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    version_id = uuid.UUID(str(candidate[0]))

    creee = (
        connexion.execute(
            text(_INSERER_INSTANCE),
            {
                "entite": entite,
                "appartenance": appartenance,
                "version": version_id,
                "reference_date": reference_date,
                "instant": instant,
            },
        )
        .mappings()
        .one_or_none()
    )
    if creee is None:
        raise ErreurApplicative(
            code=CODE_PARCOURS_DEJA_ACTIF,
            message=MESSAGE_PARCOURS_DEJA_ACTIF,
            statut=status.HTTP_409_CONFLICT,
        )
    instance = _instance_depuis_la_ligne(creee)

    lignes_taches = connexion.execute(
        text(_TACHES_DE_LA_VERSION), {"version": version_id}
    ).mappings()
    ecrites = []
    for ligne_tache in lignes_taches:
        ecrite = (
            connexion.execute(
                text(_INSERER_TACHE_INSTANCE),
                {
                    "entite": entite,
                    "instance": instance.id,
                    "task_reference_id": ligne_tache["task_reference_id"],
                    "title": ligne_tache["title"],
                    "description": ligne_tache["description"],
                    "required": ligne_tache["required"],
                    "reference_date": reference_date,
                    "due_offset_days": ligne_tache["due_offset_days"],
                },
            )
            .mappings()
            .one()
        )
        tache_ecrite = tache_depuis_la_ligne(ecrite)
        enregistrer_un_evenement_de_tache(
            connexion,
            entite=entite,
            tache=tache_ecrite.id,
            type_evenement=TypeEvenementTache.ASSIGNED.value,
            instant=instant,
            acteur=acteur,
        )
        ecrites.append(tache_ecrite)
    taches = tuple(ecrites)

    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=TypeEvenementTache.ASSIGNED.value,
        resource_type="onboarding_instance",
        resource_reference=instance.id,
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Affectation d'un parcours d'onboarding ({len(taches)} tache(s))",
    )
    return Parcours(
        instance=instance,
        progression=_progression_depuis_les_taches(taches),
        prochaine_tache=_prochaine_tache(taches),
        taches=taches,
    )
