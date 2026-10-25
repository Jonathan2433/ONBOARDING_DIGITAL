"""Qui peut LIRE le journal d'audit, et dans quel perimetre — matrice §16, `T8`.

CE QUE LA MATRICE DONNE, ET LES DEUX POINTS QU'ELLE NE TRANCHAIT PAS

  Le §16 donne six lignes, et les trois premieres gouvernent ce que `T8` sert :

      Consulter                      Consultants | Modifications fonctionnelles
                                      de l'entite | Historique du cercle |
                                      Historique du bureau | Entite | Global
      Rechercher et filtrer          Consultants | Perimetre | Cercle | Bureau
                                      | Entite | Global
      Voir ancien/nouveau contenu    Perimetre | Perimetre | Cercle | Bureau |
                                      Entite | Global
      Consulter les details
      techniques non sensibles       Limite | Limite | Limite | Limite |
                                      Entite | Global

  `ANON`, `EMP` et `NEW` sont a TIRET sur les quatre lignes (§5, « Matrice
  generale de consultation », ligne « Audit ») : aucun des trois ne figure dans
  `ROLES_DE_L_AUDIT` ci-dessous, et la route refuse 403 avant toute resolution
  de perimetre — exactement le refus par defaut du §2.6.

  **`ESM` PORTE DEUX FORMULATIONS DIFFERENTES POUR LA MEME PORTEE.** « Consulter »
  dit « Modifications fonctionnelles de l'entite », les deux lignes suivantes
  disent « Perimetre ». Le mot « Perimetre » n'est pas dans la legende §4 — meme
  piege que `§7.45`/`§7.46` de la passation — mais le §3 le definit : la colonne
  « Perimetre principal » de l'ESM porte « Ensemble de son entite », MOT POUR MOT
  la definition d'`Entite`. Et le §5.1 cadre l'ESM comme administrant « les
  donnees fonctionnelles de son entite » (§8 de la meme matrice) — un mot qui
  decrit l'ESM partout dans le corpus, jamais une restriction de type
  d'evenement. Les deux formulations denotent donc LA MEME portee : `Entite`,
  sans filtre sur le genre d'action. Lecture confirmee par la ligne « Details
  techniques », qui distingue ESM (`Limite`) d'ADM-E/SUPER (`Entite`/`Global`)
  sur un AUTRE axe — celui des COLONNES visibles, pas des LIGNES visibles. Deux
  axes orthogonaux, jamais confondus ici.

  **DEUX ARBITRAGES EXPLICITES DE JONATHAN, POSES AVANT TOUT CODE**
  (`AskUserQuestion`, reformules sans jargon) :

  1. Les evenements d'authentification (connexion, magic link, revocation de
     session) sont ecrits SANS entite depuis `T2` (`auth_event` ne concerne
     jamais une entite, voir `app/audit/lecture.py`). Reponse : le journal d'une
     entite les retrouve par l'entite ACTUELLE du collaborateur (son
     appartenance occupante aujourd'hui), pas celle d'alors.
  2. Le Booster et le responsable de bureau voient AUSSI les evenements sur les
     AUTRES ressources de leur perimetre (le cercle/bureau lui-meme, son
     contenu, ses evenements), pas seulement sur les personnes — fidele au mot
     choisi par la matrice (`Cercle`/`Bureau`, jamais `Consultants` comme pour le
     DSM). Voir `app/audit/lecture.py` pour la traduction SQL complete.

`T9` AJOUTE LA QUATRIEME LIGNE DU §16, « EXPORTER EN CSV »

  Seuls `ADM-E` (son entite) et `SUPER` (global) exportent — les quatre autres
  roles de `ROLES_DE_L_AUDIT` sont a TIRET sur cette ligne precise, confirme
  par le controle d'acceptation §24 point 18 : « l'export d'audit est refuse a
  tous les roles sauf `ADM-E` et `SUPER` ». Le PERIMETRE de l'export est le MEME que
  celui de la lecture (`resoudre_le_perimetre_de_l_audit`, toujours `Entite`
  pour ces deux roles) — aucune troisieme fonction de resolution, l'export ne
  fait QUE filtrer `ROLES_D_EXPORT_DE_L_AUDIT` en plus de `ROLES_DE_L_AUDIT`
  avant d'appeler la MEME lecture. Voir `app/audit/export.py` pour le reste.

CE QUE CE MODULE FAIT, ET CE QU'IL NE FAIT PAS

  Meme separation que partout ailleurs dans ce depot (`app/onboarding/
  perimetre.py` en est le patron direct) : ce module resout UNE portee parmi
  quatre depuis un ensemble de roles deja resolu par `resoudre_les_permissions`.
  Il ne lit JAMAIS la base — `app/audit/lecture.py` traduit la portee en clause
  SQL, et c'est lui qui interroge `framework_responsibility_assignment`,
  `dsm_assignment`, etc. pour savoir QUEL cercle, QUEL bureau precisement.
"""

from __future__ import annotations

import enum
from typing import Final

from app.permissions.services import RoleDeLaMatrice

#  §16, les quatre premieres lignes : six roles, jamais `EMP` ni `NEW` — a la
#  difference de `ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES` (LOT 7) ou d'autres
#  grilles qui admettent `EMP`, le §5 met ce role a TIRET ici, comme `ANON`.
ROLES_DE_L_AUDIT: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.RESPONSABLE_DE_BUREAU,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  §16, ligne « Consulter les details techniques non sensibles » : SEULS
#  `ADM-E` et `SUPER` recoivent `Entite`/`Global` — les quatre autres roles de
#  `ROLES_DE_L_AUDIT` sont `Limite`. Axe des COLONNES exposees par une ligne,
#  jamais des LIGNES visibles (voir l'en-tete). Interpretation du mot
#  « techniques », non definie plus loin par le corpus : `resource_reference`
#  et `correlation_token` sont les deux colonnes que `T1` lui-meme qualifie de
#  « techniques » (`app/audit/modeles.py`, « reference technique » /
#  « jeton de correlation technique ») — aucune troisieme colonne n'est nommee
#  ainsi nulle part dans ce depot, et en inventer une serait §6.5.
ROLES_DES_DETAILS_TECHNIQUES: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  §16, ligne « Exporter en CSV » — `T9` : SEULS `ADM-E` et `SUPER` exportent,
#  tiret partout ailleurs. MEMES DEUX MEMBRES QUE `ROLES_DES_DETAILS_
#  TECHNIQUES` ci-dessus, et c'est une COINCIDENCE DE CETTE MATRICE, PAS UNE
#  IDENTITE CONCEPTUELLE — ce sont deux lignes distinctes du §16, et les
#  fusionner reviendrait a lier au silence deux regles que la matrice pourrait
#  un jour faire diverger (§7.27 : une liste recopiee vieillit au premier
#  ajout, ici dans l'autre sens — une liste FUSIONNEE a tort).
ROLES_D_EXPORT_DE_L_AUDIT: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

_ROLES_ENTITE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)


class PerimetreDAudit(enum.Enum):
    """§16 : QUATRE portees, jamais une combinaison — meme discipline que
    `PerimetreDuSuivi` (LOT 7, `T12`). La portee s'ajuste au role le PLUS LARGE
    detenu, dans l'ordre Entite puis Consultants puis Cercle puis Bureau."""

    ENTITE = "entite"
    CONSULTANTS = "consultants"
    CERCLE = "cercle"
    BUREAU = "bureau"


def resoudre_le_perimetre_de_l_audit(*, roles: frozenset[RoleDeLaMatrice]) -> PerimetreDAudit:
    """§16 : ESM/ADM-E/SUPER -> Entite, DSM -> Consultants, Booster -> Cercle,
    responsable de bureau -> Bureau.

    **PRECONDITION, JAMAIS VERIFIEE ICI** : l'appelant a deja confronte `roles`
    a `ROLES_DE_L_AUDIT` et refuse 403 si l'intersection est vide — cette
    fonction suppose donc qu'au moins un des six roles est present, exactement
    comme `resoudre_le_perimetre_du_suivi` suppose une session deja etablie.
    Une personne qui cumule, par exemple, `DSM` et `BOOSTER` recoit la portee
    la PLUS LARGE des deux (`Cercle` avant `Consultants`, dans cet ordre), pour
    ne jamais lui refuser ce qu'une seule de ses responsabilites donnerait deja.
    """
    if roles & _ROLES_ENTITE:
        return PerimetreDAudit.ENTITE
    if RoleDeLaMatrice.BOOSTER in roles:
        return PerimetreDAudit.CERCLE
    if RoleDeLaMatrice.RESPONSABLE_DE_BUREAU in roles:
        return PerimetreDAudit.BUREAU
    #  Seul `DSM` peut rester a ce point : `ROLES_DE_L_AUDIT` n'a pas d'autre
    #  membre, et la precondition garantit qu'au moins un y est.
    return PerimetreDAudit.CONSULTANTS


def a_les_details_techniques(*, roles: frozenset[RoleDeLaMatrice]) -> bool:
    """§16, ligne « Consulter les details techniques non sensibles ».

    Un seul booleen, jamais un role expose : `app/audit/lecture.py` ne fait que
    traduire cette decision en un champ masque ou non, exactement comme il
    traduit `PerimetreDAudit` en clause SQL — jamais de logique de role hors de
    ce module (voir l'en-tete).
    """
    return bool(roles & ROLES_DES_DETAILS_TECHNIQUES)
