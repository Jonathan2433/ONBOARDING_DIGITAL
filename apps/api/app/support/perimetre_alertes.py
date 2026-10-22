"""Qui consulte et qui traite une alerte operationnelle — matrice §17, `T13`.

LOT 10, sous-étape `T13`, story `MVP-L10-US007`.

UNE RESSOURCE GLOBALE RENCONTRE UNE GRILLE ENTITÉ/GLOBAL : LA SEULE LECTURE COHÉRENTE

  Le §17 pose trois lignes propres aux alertes, après les deux déjà servies
  par `T11`/`T12` :

      Consulter les alertes de sécurité   —   Limité fonctionnel   —   —   Entité   Global
      Acquitter une alerte                —   —   —   —   Entité   Global
      Résoudre ou commenter une alerte    —   —   —   —   Entité   Global

  **`operational_alert` NE PORTE AUCUN `entity_id`** (modèle §21.2, `T1` —
  voir l'en-tête d'`app/audit/modeles.py` : une alerte opérationnelle n'est
  pas un fait D'UNE entité). La grille Entité/Global ne peut donc PAS se lire
  comme un filtrage par entité : il n'y a aucune colonne à filtrer. Elle se
  lit comme ce qu'elle a toujours été pour `SUPER` (une portée qui s'étend à
  tout), et pour `ADM-E` elle s'étend PAREIL : le détenir DANS N'IMPORTE
  QUELLE entité suffit, puisqu'aucune alerte n'« appartient » à une entité
  précise dont il faudrait restreindre la vue.

  Mesuré avant d'écrire : `resoudre_les_permissions` (LOT 4, `T8`) n'accorde
  `ADM-E`/`ESM` que DANS l'entité PRINCIPALE consultée — aucune route de ce
  dépôt n'avait encore eu besoin de « ce rôle, n'importe où » avant cette
  ressource globale, à l'exception de `SUPER` (`est_super_administrateur`,
  extrait par `T12` du LOT 9 pour la création d'entité, qui n'a elle non plus
  aucune entité à consulter). Ce module ÉTEND ce même patron à `ADM-E` et
  `ESM`, pour la MÊME raison structurelle : une garde qui n'a aucune entité à
  interroger ne peut pas passer par `resoudre_les_permissions`.

« LIMITÉ FONCTIONNEL » : LE MÊME MOT QUE LA « LECTURE FONCTIONNELLE » DE `T12`

  La matrice écrit « Limité fonctionnel » pour l'`ESM` — pas seulement
  « Limité », qu'elle réserve juste au-dessus à « Consulter les KPI
  techniques » — le MÊME adjectif que la « lecture fonctionnelle » de
  `PerimetreDesSignalements` (`T12`), qui masque un « contexte technique non
  sensible » nommé par le backlog `US005`. `operational_alert` n'a pas de
  backlog qui nomme ses champs techniques un par un, mais le modèle distingue
  déjà ce qui EST technique de ce qui est l'ÉTAT MÉTIER d'une alerte :
  `source` (vocabulaire OUVERT nommant le sous-système émetteur — « API,
  worker, security, backup, Uptime Kuma » — un détail de plomberie de
  supervision) et `fingerprint` (une clé de déduplication opaque, jamais
  lisible par un humain) contre `severity`/`state`/les trois horodatages/
  l'assignation, qui disent CE QUI est cassé, depuis quand, et si quelqu'un
  s'en occupe. Même principe que `T12`, appliqué par analogie textuelle
  plutôt qu'inventé : l'ESM lit TOUTES les alertes (aucun filtrage par
  rangée n'étant possible), avec `source`/`fingerprint` masqués.

AUCUN MOTIF OBLIGATOIRE ICI, ET CE N'EST PAS UN OUBLI

  Le §18.1/`RIGHTS-017` (`ECART-064`, fermé par `T7`) exige un motif pour
  « une intervention du super-administrateur DANS UNE ENTITÉ ». Une alerte
  n'est JAMAIS dans une entité : le modèle ne lui en donne aucune. La
  précondition textuelle du §18.1 ne peut donc jamais être remplie ici, et
  `app.audit.motif.exiger_un_motif_si_necessaire` n'est appelé par AUCUNE
  route de ce module — première exemption du genre depuis que `T7` a rendu
  la règle permanente, mais elle procède de la même lecture littérale du
  cahier que `T9` a déjà appliquée pour exempter une LECTURE (un export n'est
  pas une « intervention ») : ici, ce n'est pas la nature de l'écriture qui
  exempte, c'est l'absence totale d'entité où « intervenir ».

AUCUNE PORTÉE « SOI » : LA MATRICE NE PRÉVOIT AUCUN PLANCHER À COMBLER

  À la différence des signalements (où `Soi` est un plancher universel pour
  TOUTE session établie, `T12`), les trois lignes ci-dessus NE DONNENT RIEN à
  `DSM`/`BOOST`/`OFFICE` : les tirets se lisent normalement, comme un refus.
  Résoudre un périmètre rend donc `None` pour ces rôles (et pour `EMP`, qui
  n'a même pas de colonne dans cette table de la matrice), et les routes de
  lecture renvoient 403 — jamais un repli `Soi` qu'aucune cellule ne nomme.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.permissions.services import RoleDeLaMatrice, est_super_administrateur

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection


class PerimetreDesAlertes(enum.Enum):
    """§17 : deux portées seulement, aucun plancher — voir l'en-tête du module."""

    COMPLET = "complet"
    LIMITE = "limite"


#  §17 « Acquitter une alerte »/« Résoudre ou commenter une alerte » : les
#  deux verbes d'écriture partagent EXACTEMENT la même grille (ADM-E Entité,
#  SUPER Global, les quatre autres à tiret) — une seule constante pour les
#  deux routes, jamais deux déclarations qui pourraient diverger (§7.27).
ROLES_DE_TRAITEMENT_DES_ALERTES: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE, RoleDeLaMatrice.SUPER_ADMINISTRATEUR}
)


def _est_administrateur_d_entite_quelque_part(
    connexion: Connection, personne: uuid.UUID, instant: dt.datetime
) -> bool:
    """`personne` tient-elle `ENTITY_ADMIN`, DANS N'IMPORTE QUELLE entité, à `instant`.

    Même requête qu'`est_super_administrateur` (`app.permissions.services`),
    SANS le filtre `entity_id IS NULL` qui est propre à `SUPER_ADMIN` —
    extension du même patron, nécessaire ici seulement : voir l'en-tête du
    module.
    """
    return bool(
        connexion.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM technical_role_assignment "
                "  WHERE person_id = :personne_adm AND role_type = :type_adm "
                "    AND archived_at IS NULL AND period @> :instant_adm"
                ")"
            ),
            {
                "personne_adm": personne,
                "type_adm": TypeRoleTechnique.ENTITY_ADMIN.value,
                "instant_adm": instant,
            },
        ).scalar_one()
    )


def _est_esm_quelque_part(connexion: Connection, personne: uuid.UUID, instant: dt.datetime) -> bool:
    """`personne` tient-elle une responsabilité `ESM`, DANS N'IMPORTE QUELLE entité."""
    return bool(
        connexion.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM framework_responsibility_assignment "
                "  WHERE person_id = :personne_esm AND responsibility_type = :type_esm "
                "    AND archived_at IS NULL AND period @> :instant_esm"
                ")"
            ),
            {
                "personne_esm": personne,
                "type_esm": TypeResponsabilite.ESM.value,
                "instant_esm": instant,
            },
        ).scalar_one()
    )


def resoudre_les_roles_pour_les_alertes(
    connexion: Connection, *, personne: uuid.UUID, instant: dt.datetime
) -> frozenset[RoleDeLaMatrice]:
    """Les rôles de `personne` pertinents pour les alertes, TOUTES ENTITÉS confondues.

    Ressource globale (voir l'en-tête du module) : ni `resoudre_les_permissions`
    (qui exige une entité consultée) ni son résultat ne s'appliquent ici —
    cette fonction en est l'équivalent entité-less, pour les trois seuls rôles
    que le §17 mentionne sur ces lignes (`ESM`, `ADM-E`, `SUPER`).
    """
    roles: set[RoleDeLaMatrice] = set()
    if est_super_administrateur(connexion, personne, instant):
        roles.add(RoleDeLaMatrice.SUPER_ADMINISTRATEUR)
    if _est_administrateur_d_entite_quelque_part(connexion, personne, instant):
        roles.add(RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE)
    if _est_esm_quelque_part(connexion, personne, instant):
        roles.add(RoleDeLaMatrice.ESM)
    return frozenset(roles)


def resoudre_le_perimetre_des_alertes(
    *, roles: frozenset[RoleDeLaMatrice]
) -> PerimetreDesAlertes | None:
    """§17 « Consulter les alertes de sécurité » : `None` = refusé, jamais un
    repli `Soi` (voir l'en-tête du module — aucune des trois lignes n'en porte)."""
    if roles & ROLES_DE_TRAITEMENT_DES_ALERTES:
        return PerimetreDesAlertes.COMPLET
    if RoleDeLaMatrice.ESM in roles:
        return PerimetreDesAlertes.LIMITE
    return None


def a_la_lecture_complete(*, perimetre: PerimetreDesAlertes) -> bool:
    """`source`/`fingerprint` sont-ils visibles pour ce périmètre ?"""
    return perimetre is PerimetreDesAlertes.COMPLET
