"""Qui archive et restaure un cercle ou un bureau — matrice §10.2, §10.3, §18.

LOT 9, sous-etape `T4`, story `MVP-L09-US008`.

LA MEME GRILLE POUR LES DEUX RESSOURCES, ET C'EST ECRIT TROIS FOIS

  Le §10.2 (« Archiver un cercle », « Restaurer un cercle ») et le §10.3 (memes
  lignes pour un bureau) donnent, a la lettre pres, la MEME grille : `DSM` et
  `BOOST` et `OFFICE` a TIRET, `ESM` ET `ADM-E` « Entite », `SUPER` « Global ».
  Le §18 (« Archives, restauration et purge ») la redit une troisieme fois, pour
  les deux ressources a la fois : « Restaurer un cercle ou bureau | Entite,
  restauration fonctionnelle | Entite | Global ».

  **AUCUN BOOSTER NI RESPONSABLE DE BUREAU ICI**, contrairement au contenu
  editorial (`app.content.perimetre`) ou aux evenements, qui accordent tous deux
  une portee locale a ces roles. Le §10.2 et le §10.3 ne la leur donnent QUE sur
  le CONTENU du cercle/bureau (description, ressources, galerie) -- jamais sur
  la STRUCTURE, qui est ce module. Une seule grille suffit donc, la ou le
  contenu en declare une par action (§7.45).

« CONDITIONNEL » N'EST PAS UNE DECISION A PRENDRE, ET C'EST DEJA TRANCHE

  Meme lecture qu'au cycle de vie d'un profil (`app.permissions.perimetre`) et
  qu'a celui d'une page (`app.content.cycle_de_vie`) : le mot « Conditionnel »
  du §10.2/§10.3 pour l'ESM n'est pas un point en suspens. `ARB-DROIT-003` le
  definit en toutes lettres, pour CINQ ressources dont le cercle et le bureau :
  « l'ESM peut restaurer dans son entite un profil, un contenu, un evenement,
  un cercle ou un bureau. Les restaurations techniques, massives ou liees aux
  imports restent reservees a l'administrateur d'entite et au
  super-administrateur. » Un cercle ou un bureau a l'unite, par une route
  dediee, EST une restauration fonctionnelle : l'ESM est autorise, exactement
  comme l'ADM-E et le SUPER -- la meme grille sert donc les deux actions.

UNE INTERDICTION LIEE A LA RESSOURCE, PAS AU ROLE

  Le §10.2 porte une condition que le §10.3 ne porte PAS : « Archiver un cercle
  | Entite, **si aucun membre actif** ». Ce n'est pas une case de la grille des
  roles -- elle vaut pour `ESM`, `ADM-E` ET `SUPER` sans distinction -- c'est un
  etat de la ressource, au meme titre que « la cible est deja archivee » pour un
  profil (`T8` du LOT 5) ou que la borne des responsables d'un bureau publie
  (`T7` du LOT 6, `DEC-583`). Elle est donc verifiee par le SERVICE
  (`app.organization.cycle_de_vie`), jamais par ce module, qui ne resout que les
  roles.

CE QUE CE MODULE NE REGLAIT PAS, ET QUE LOT 11 `T3` FERME

  Ce paragraphe disait, depuis le LOT 9 : « la CREATION et la MODIFICATION DE
  STRUCTURE d'un cercle ou d'un bureau ne sont demandees par aucune sous-etape
  […] les construire ici deborderait le perimetre d'une sous-etape ». C'etait
  vrai a sa date, et c'est devenu faux le jour ou Jonathan a constate ce trou a
  l'ouverture du LOT 11 (`DEC-674`, 30/10/2026) et l'a ajoute hors backlog a
  `T3` (`docs/operations/fiche-lot-11.md` §1.2) — §7.21 de la passation : un
  paragraphe juste hier peut etre faux aujourd'hui, et c'est nous qui l'avons
  rendu faux en comblant le trou qu'il decrivait.

  **« Creer un cercle »/« Creer un bureau » (§10.2/§10.3) PORTENT LA MEME
  GRILLE que « Archiver »/« Restaurer » dans ces deux memes tableaux** — `ESM`
  et `ADM-E` « Entite », `SUPER` « Global », les trois autres roles a tiret.
  `ROLES_DE_CYCLE_DE_VIE_FRAMEWORK` est donc REUTILISEE telle quelle pour la
  creation (§7.27) : une seconde constante identique aurait pu diverger en
  silence du jour ou l'une des deux grilles change.

  **L'ATTRIBUTION DU BOOSTER ET DU RESPONSABLE DE BUREAU EST UNE GRILLE
  SEPAREE, RECOPIEE ET NON CALQUEE SUR CELLE-CI** — §20 : « Affecter ou
  remplacer un Booster »/« Affecter un responsable de bureau », `ESM` Entite,
  `SUPER` Global, et **`ADM-E` EXCLU** (« L'administrateur d'entite ne peut pas
  attribuer les responsabilites Framework », §20 et `ARB-DROIT-002`). Memes
  deux roles que `ROLES_DE_CYCLE_DE_VIE_FRAMEWORK` moins l'administrateur
  d'entite — une divergence d'une seule case qui justifie une constante a part,
  jamais une exception codee en dur sur la premiere.

  **« Consulter un cercle/bureau archive »** n'est demande par AUCUNE ligne du
  §10.2, du §10.3 ni du §18 -- a la difference du profil, dont le §6.1 porte
  explicitement cette troisieme ligne. L'inventer ici serait le §6.5 : les
  routes de `T4` prennent donc l'identifiant du cercle/bureau DIRECTEMENT (son
  `id`, pas son `code`, pour la meme raison que le transfert d'un collaborateur
  prend une `appartenance` et non un nom), et la facon de le DECOUVRIR reste
  une question pour la sous-etape qui construira l'ecran (`T14`).
"""

from __future__ import annotations

from typing import Final

from app.permissions.services import RoleDeLaMatrice

#  **MEME GRILLE POUR LE CERCLE ET LE BUREAU, ET LES TROIS ACTIONS** (creer,
#  archiver, restaurer). Voir l'en-tete du module : le §10.2, le §10.3 et le
#  §18 la donnent plusieurs fois, identique a chaque fois.
ROLES_DE_CYCLE_DE_VIE_FRAMEWORK: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  **LOT 11, `T3`.** §20 « Affecter ou remplacer un Booster »/« Affecter un
#  responsable de bureau »/« Retirer une responsabilite Framework » — `ESM`
#  Entite, `SUPER` Global. `ADM-E` EXCLU, a la difference de la grille
#  ci-dessus : voir l'en-tete du module.
ROLES_D_ATTRIBUTION_FRAMEWORK: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)
