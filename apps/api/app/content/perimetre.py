"""Qui peut ECRIRE, PUBLIER, ARCHIVER, RESTAURER — annexe A §13, §18, §19. `T6` a `T8`.

LA GRILLE DE L'ECRITURE DU LOT 5 NE SE REEMPLOIE PAS, ET LA REUTILISER
ELARGIRAIT UN DROIT

  `ROLES_D_ECRITURE` de `app/permissions/perimetre.py` porte la grille du §6.1 --
  les donnees organisationnelles d'une PERSONNE -- et elle contient `DSM`. Le
  §13, section des contenus editoriaux, met la colonne `DSM` **entierement a
  tiret** sur ses trois lignes de modification :

      Action                            DSM  ESM       BOOST   OFFICE  ADM-E    SUPER
      Creer un contenu general          —    Entite    —       —       Entite   Global
      Modifier un contenu de cercle     —    Entite    Cercle  —       Entite   Global
      Modifier un contenu de bureau     —    Entite    —       Bureau  Entite   Global

  Symetriquement, `OFFICE` est absent de `ROLES_D_ECRITURE` -- sa colonne du §6.1
  est a tiret -- et il porte ici un droit REEL sur le contenu de son bureau.
  **Les deux grilles different dans les deux sens** : une seule ferait perdre un
  droit a l'un et en accorderait un a l'autre.

  C'est exactement la lecon de `T8` du LOT 5, ou le §6.1 portait deja DEUX
  grilles -- `ROLES_D_ECRITURE` et `ROLES_DU_CYCLE_DE_VIE` -- et ou reutiliser la
  premiere aurait accorde l'archivage a deux roles que la matrice en exclut.

« CREER » N'EST PAS « MODIFIER », ET LE DOCUMENT N'A QU'UNE LIGNE DE CREATION

  Le §13 ecrit « **Creer** un contenu general » et la donne a `ESM`, `ADM-E` et
  `SUPER` seulement. Ses deux autres lignes disent « **Modifier** un contenu de
  cercle » et « de bureau », et ce sont celles-la qui portent `BOOST` et
  `OFFICE`.

  **Le Booster ne cree donc pas la page de son cercle, il en modifie le
  contenu** -- de la meme facon que le §10.2 lui refuse « Creer un cercle » tout
  en lui donnant « Modifier le contenu du cercle ». Celui qui cree la ressource
  cree sa page ; celui qui a la portee locale en ecrit le contenu.

« ENTITE » N'EST PAS « PERIMETRE » — ET `T7` A MESURE QUE, POUR L'ESM, SI

  Toujours au §13, l'`ESM` a « Entite » pour creer et modifier, et
  **« Perimetre »** pour publier et archiver. Deux mots differents dans la meme
  colonne du meme tableau : `T6` en a conclu, prudemment, qu'il fallait les
  traiter separement.

  **LA LEGENDE §4 NE DEFINIT PAS `Perimetre`.** Mesure du 19/09/2026 : elle
  definit la coche, `—`, `Soi`, `Consultants`, `Cercle`, `Bureau`, `Entite`, `Global`,
  `Lecture` et `Conditionnel` -- dix valeurs, et `Perimetre` n'y est pas, alors
  qu'il est employe dans plus de vingt cellules.

  **MAIS LE §3 LE DEFINIT, DANS UNE COLONNE QUI S'APPELLE « PERIMETRE
  PRINCIPAL » :**

      DSM      « Ses consultants dans son entite »
      ESM      « **Ensemble de son entite** »
      BOOST    « Son cercle et ses membres »
      OFFICE   « Son bureau »
      ADM-E    « Ensemble de son entite »
      SUPER    « Toutes les entites »

  Or la legende §4 definit `Entite` par « **Ensemble de l'entite principale** ».
  **Pour l'`ESM`, `Perimetre` et `Entite` denotent donc le MEME ensemble**, et
  les deux mots du §13 ne se contredisent pas : ils se lisent l'un par l'autre.
  `RIGHTS-009` le redit -- « l'ESM dispose des pouvoirs fonctionnels transverses
  de son entite ».

  C'est ce qui resout `ECART-063` -- voir plus bas.

CE QUE LES §10.2 ET §10.3 AJOUTENT, ET ILS CONCORDENT

  §10.2  « Modifier le contenu du cercle »       —  Entite  Cercle  —       Entite  Global
  §10.3  « Modifier la structure du bureau »     —  Entite  —  **Bureau, contenu
                                                                uniquement**  Entite  Global
  §10.3  « Modifier description, video, ressources »  —  Entite  —  Bureau  Entite  Global

  La cellule « Bureau, **contenu uniquement** » est le troisieme piege du §2.1 de
  la fiche, et il ne mord PAS ici : `T6` n'ecrit que du contenu -- le titre d'une
  page et ses blocs -- jamais le `code`, le `name` ni le `display_order` de la
  table `office`, qui sont sa structure.

CE QUE LE CORPUS NE TRANCHE PAS, ET QUI EST CONSIGNE PLUTOT QU'INVENTE

  Le §10.1 donne au `DSM` « Modifier la page DSM | **Entite ou propre
  contenu** ». **Aucun `page_type` du §15.1 ne porte cette page** -- ni `DSM` ni
  `ESM` n'y figurent, et `T2` a emis pour elles un chemin d'ECRAN sans que rien
  ne dise quel contenu les porte. Deux lectures sont possibles, aucune n'est
  deductible : une page `FRAMEWORK` particuliere, ou un « autre type controle »
  a creer.

  **Aucun droit n'est donc accorde au DSM ici**, ce qui suit le §13 a la lettre.
  Lui ouvrir toutes les pages `FRAMEWORK` serait plus large que ce que le §10.1
  ecrit, et le §6.5 interdit l'hypothese deguisee en decision. `ECART-062`.

LA « PRESENTATION DE L'ENTITE » N'A PAS DE GRILLE PROPRE, ET C'EST UNE MESURE

  Le §13 porte une ligne « **Modifier la presentation de l'entite** », et `T8`
  devait lui trouver une place. Elle n'en demande aucune, et la confrontation du
  22/09/2026 le dit :

      §13 « Modifier la presentation de l'entite »
                       DSM —  ESM Entite  BOOST —  OFFICE —  ADM-E Entite  SUPER Global
      §13 « Creer un contenu general »
                       DSM —  ESM Entite  BOOST —  OFFICE —  ADM-E Entite  SUPER Global

  **Les deux lignes sont identiques cellule par cellule.** Et la presentation est
  une page de contenu -- le cahier situe « l'accueil d'une entite contenant **la
  presentation** et les acces au Framework », et sa page d'accueil commence par
  « 1. presentation de l'entite » --, donc du type `HOME` du §15.1.

  Or `HOME` appartient a `TYPES_SANS_PORTEE_LOCALE`, par SOUSTRACTION : il n'a
  aucune entree dans `PORTEES_LOCALES`. `resoudre_le_perimetre_editorial` le
  reserve donc deja a `ROLES_DE_PORTEE_ENTITE`, soit exactement les trois roles
  que la ligne du §13 nomme. **Aucune ligne de code n'etait a ecrire**, et deux
  tests le MESURENT plutot que ce paragraphe ne l'affirme.

`ECART-063` — LES DEUX GRILLES D'ARCHIVAGE, ET CE QUE LA MESURE EN A FAIT

  `T6` a releve que le §13 et le §18 donnent deux grilles pour « Archiver un
  contenu », divergentes **dans les deux sens**. La mesure du 19/09/2026 les
  reduit a **une seule cellule**, en lisant `Perimetre` par le §3 :

      role     §13 « Archiver »      §18 « Archiver un contenu »   concordent ?
      DSM      —                     Perimetre                     **NON**
      ESM      Perimetre = Entite    Entite                        OUI, meme ensemble
      BOOST    Cercle                Cercle                        OUI
      OFFICE   Bureau                Bureau                        OUI
      ADM-E    Entite                Entite                        OUI
      SUPER    Global                Global                        OUI

  **CINQ ROLES SUR SIX CONCORDENT**, et la divergence apparente de l'`ESM`
  n'etait qu'une difference de VOCABULAIRE. Reste le `DSM`, et sa cellule du §18
  n'est pas implementable :

    - le §3 definit son perimetre comme « ses **consultants** dans son entite »,
      donc un ensemble de PERSONNES ;
    - `content_page` ne porte aucune colonne qui rattache une page a un `DSM` --
      mesure sur le catalogue : `entity_id`, `page_type`, `circle_id`,
      `office_id`, `title`, `slug`, `state`, `published_at`, plus les champs
      communs du §3.1. Ni `person_id`, ni `dsm_id` ;
    - lui accorder un droit exigerait donc d'INVENTER un rattachement, ce que le
      §6.5 interdit -- et le §10.1 du cahier confirme dans le meme sens, sa ligne
      « Archiver/restaurer une page » mettant le `DSM` a **tiret**.

  **Le `—` du §13 est donc retenu**, et ce n'est pas seulement la lecture la plus
  restrictive : c'est la seule que le modele permette d'ecrire.

LA RESTAURATION A UNE GRILLE PLUS ETROITE, ET TROIS SOURCES LE DISENT

      source                                DSM  ESM            BOOST  OFFICE  ADM-E   SUPER
      matrice §13 « Restaurer »             —    Conditionnel   —      —       Entite  Global
      matrice §18 « Restaurer un contenu »  —    Entite, fonct. —      —       Entite  Global
      cahier §10.1 « Archiver/restaurer »   —    Conditionnel   —      —       Entite  Global

  **Le Booster et le responsable de bureau ARCHIVENT leur page et ne la
  RESTAURENT pas.** C'est asymetrique, c'est ecrit trois fois, et c'est
  exactement la lecon de `T8` du LOT 5 : le §6.1 y portait deja deux grilles, et
  reutiliser la premiere aurait accorde l'archivage a deux roles qui en sont
  exclus.

  **`Conditionnel` EST DEFINI** -- §4, « autorise si une regle metier
  complementaire est satisfaite » -- et `ARB-DROIT-003` nomme la regle :
  « l'ESM peut restaurer dans son entite un profil, un **contenu**, un evenement,
  un cercle ou un bureau. Les restaurations **techniques, massives ou liees aux
  imports** restent reservees a l'administrateur d'entite et au
  super-administrateur. » Restaurer UNE page est une restauration fonctionnelle :
  la condition est satisfaite, et ce module n'offre aucun geste massif.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.content.modeles import EtatDePage, TypeDePage
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice


class ActionEditoriale(enum.StrEnum):
    """Les cinq lignes d'action du §13, et elles n'ont PAS toutes la meme grille.

    `T6` n'en portait que deux et disait pourquoi les trois autres n'etaient pas
    declarees : « des membres que personne ne lit » (§7.32). `T7` les lit.

    **TROIS GRILLES DISTINCTES POUR CINQ ACTIONS**, et c'est le document qui les
    separe, pas ce module :

        CREER                 `ESM`, `ADM-E`, `SUPER`  -- une seule ligne au §13
        MODIFIER PUBLIER      les memes, plus `BOOST` sur son cercle et `OFFICE`
        ARCHIVER              sur son bureau
        RESTAURER             `ESM`, `ADM-E`, `SUPER` -- `BOOST` et `OFFICE` en
                              sont EXCLUS, et trois sources le disent
    """

    CREER = "creer"
    MODIFIER = "modifier"
    PUBLIER = "publier"
    ARCHIVER = "archiver"
    RESTAURER = "restaurer"


#  §13, ligne « Creer un contenu general ». **Une seule ligne de creation dans
#  tout le document**, et elle ne porte ni `BOOST` ni `OFFICE`.
ROLES_DE_CREATION: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  Les roles dont la portee est l'ENTITE entiere sur les contenus : les memes
#  trois, et le §13 ecrit « Global » pour `SUPER`. Les routes etant bornees a une
#  entite par leur chemin, les trois se resolvent identiquement -- et le dire
#  vaut mieux que de laisser croire que `SUPER` est traite a part.
ROLES_DE_PORTEE_ENTITE: Final[frozenset[RoleDeLaMatrice]] = ROLES_DE_CREATION


@dataclasses.dataclass(frozen=True, slots=True)
class PorteeLocale:
    """Comment un role obtient une portee BORNEE sur un type de page.

    `responsabilite` est le type de `framework_responsibility_assignment` qui la
    confere, et `colonne` la colonne de `content_page` qui designe la ressource.
    **Le couple est ce qui rend la regle exacte** : un Booster n'ecrit pas « les
    pages de cercle », il ecrit la page **de son cercle**.
    """

    role: RoleDeLaMatrice
    responsabilite: TypeResponsabilite
    colonne: str


#  **LA TABLE EST DECLAREE, PAS DERIVEE, ET C'EST LE BON PARTI ICI.** Elle est
#  une INTERPRETATION que rien dans le code ne porte -- le §7.27 dit alors de la
#  declarer ET d'exiger qu'elle corresponde au reel, comme `RELATIONS_ATTENDUES`
#  de `verifier-historisation.py`. Chaque entree cite sa ligne du document, et un
#  test exige que les colonnes nommees existent sur `content_page`.
PORTEES_LOCALES: Final[dict[str, PorteeLocale]] = {
    #  §13 « Modifier un contenu de cercle | BOOST **Cercle** », et §10.2
    #  « Modifier le contenu du cercle | BOOST **Cercle** » -- concordants.
    TypeDePage.CIRCLE.value: PorteeLocale(
        role=RoleDeLaMatrice.BOOSTER,
        responsabilite=TypeResponsabilite.BOOSTER,
        colonne="circle_id",
    ),
    #  §13 « Modifier un contenu de bureau | OFFICE **Bureau** », et §10.3
    #  « Modifier la structure du bureau | OFFICE **Bureau, contenu
    #  uniquement** » -- concordants, la restriction portant sur la STRUCTURE
    #  que `T6` n'ecrit pas.
    TypeDePage.OFFICE.value: PorteeLocale(
        role=RoleDeLaMatrice.RESPONSABLE_DE_BUREAU,
        responsabilite=TypeResponsabilite.OFFICE_MANAGER,
        colonne="office_id",
    ),
}

#  **PAR SOUSTRACTION, ET C'EST CE QUI REND L'AJOUT SUR.** Un sixieme type de
#  page -- le §15.1 dit « autre type controle » -- tomberait dans cette liste
#  SANS que personne y pense, donc dans le regime le plus RESTRICTIF : entite
#  seulement. L'ecrire en dur ferait l'inverse au premier ajout (§7.27).
TYPES_SANS_PORTEE_LOCALE: Final[frozenset[str]] = frozenset(
    m.value for m in TypeDePage
) - frozenset(PORTEES_LOCALES)

#  Les roles qui portent AU MOINS un droit d'ecriture editoriale quelque part.
#  Sert au garde-fou de role de la route ; la portee par page est resolue
#  ensuite. **DERIVE des deux sources ci-dessus** : ajouter une portee locale
#  sans toucher a cette constante serait une route morte pour le role concerne.
ROLES_D_ECRITURE_EDITORIALE: Final[frozenset[RoleDeLaMatrice]] = ROLES_DE_PORTEE_ENTITE | {
    portee.role for portee in PORTEES_LOCALES.values()
}

#  §13 « Restaurer », §18 « Restaurer un contenu » et cahier §10.1
#  « Archiver/restaurer une page » -- **les trois concordent**, et les trois
#  mettent `BOOST` et `OFFICE` a tiret. La grille de la restauration est donc
#  celle des roles de portee ENTITE, et rien d'autre.
#
#  **DECLARE PLUTOT QU'ALIASE SUR `ROLES_DE_PORTEE_ENTITE`, ET C'EST DELIBERE.**
#  Les deux ensembles coincident aujourd'hui pour une raison qui leur est
#  PROPRE -- l'un parce que trois documents excluent les portees locales de la
#  restauration, l'autre parce que le §13 n'a qu'une ligne de creation. Les
#  aliaser les ferait bouger ENSEMBLE le jour ou une seule des deux raisons
#  change. Un test MESURE leur egalite d'aujourd'hui et echouera si elle cesse,
#  ce qui forcera la decision au lieu de la prendre en silence (§7.32).
ROLES_DE_RESTAURATION: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  §13 « Gerer les cartes Hub/Academy/SharePoint » et §19 « Modifier les liens
#  internes » -- **les deux concordent**, et c'est la premiere grille voisine de
#  ce lot qui le fasse. Confrontation du 22/09/2026 :
#
#      §13 (six colonnes)   DSM —  ESM Entite  BOOST —  OFFICE —  ADM-E Entite  SUPER Global
#      §19 (trois colonnes)        ESM Entite                     ADM-E Entite  SUPER Global
#
#  Le §19 n'a **ni colonne `DSM`, ni `BOOST`, ni `OFFICE`**, ce qui est une
#  absence de colonne et non une exclusion (§7 du `DEC-584`) : c'est le §13, qui
#  les porte, qui les met a tiret. Les deux lectures s'accordent donc, et **aucune
#  n'accorde de portee locale** -- un lien appartient a l'ENTITE, et
#  `internal_link` ne porte ni `circle_id` ni `office_id`.
#
#  **DECLARE PLUTOT QU'ALIASE SUR `ROLES_DE_CREATION`, ET C'EST LE PARTI DE
#  `T7`.** Les deux ensembles coincident aujourd'hui pour des raisons qui leur
#  sont PROPRES -- l'un parce que le §13 n'a qu'une ligne de creation de contenu,
#  l'autre parce que deux sections differentes s'accordent sur les liens. Les
#  aliaser les ferait bouger ENSEMBLE le jour ou une seule des deux raisons
#  change. Un test MESURE leur egalite d'aujourd'hui et echouera si elle cesse,
#  ce qui forcera la decision au lieu de la prendre en silence (§7.32).
ROLES_DE_GESTION_DES_LIENS: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  Ce qu'une portee LOCALE -- Booster, responsable de bureau -- permet sur la
#  page de sa ressource. **`RESTAURER` EN EST ABSENT**, et c'est la seule
#  difference avec la portee d'entite.
#
#  **ECRIT EN EXTENSION, JAMAIS PAR SOUSTRACTION**, contrairement a
#  `TYPES_SANS_PORTEE_LOCALE` -- et les deux partis sont justes pour la meme
#  raison. Un TYPE DE PAGE nouveau doit tomber dans le regime le plus restrictif,
#  donc par soustraction ; une ACTION nouvelle ne doit PAS etre accordee d'office
#  a une portee locale, donc en extension. Un test exige que l'union couvre
#  l'enumeration, si bien qu'un sixieme membre fera echouer le test au lieu de
#  s'accorder tout seul.
ACTIONS_DES_PORTEES_LOCALES: Final[frozenset[ActionEditoriale]] = frozenset(
    {ActionEditoriale.MODIFIER, ActionEditoriale.PUBLIER, ActionEditoriale.ARCHIVER}
)

#  Ce qu'une portee d'ENTITE permet sur une page existante. `CREER` n'en est pas :
#  elle ne porte sur aucune page, et `peut_creer_une_page` y repond.
ACTIONS_DES_ROLES_D_ENTITE: Final[frozenset[ActionEditoriale]] = ACTIONS_DES_PORTEES_LOCALES | {
    ActionEditoriale.RESTAURER
}


@dataclasses.dataclass(frozen=True, slots=True)
class PerimetreEditorial:
    """Les actions editoriales que l'acteur peut mener SUR CETTE PAGE.

    **UN ENSEMBLE VIDE EST LE REFUS**, et il n'y a pas de second champ pour le
    dire -- meme discipline que `PerimetreDEcriture` et `PerimetreDuCycleDeVie`.
    Un booleen derivable de `actions` serait un etat que rien n'empeche de
    contredire, et un champ `motif` ne sortirait jamais : le §2.5 « refus par
    defaut » interdit de reveler pourquoi.
    """

    actions: frozenset[ActionEditoriale]


#  La page existe-t-elle dans cette entite, quel est son rattachement, et dans
#  quel ETAT est-elle ? Le couple `(id, entity_id)` porte l'isolation (§25.3) ;
#  un `WHERE` sur l'entite seule confondrait deux pages d'entites differentes.
#
#  **`T6` FILTRAIT `archived_at IS NULL` ICI, ET `T7` A DU LE REMONTER D'UN CRAN.**
#  Ce filtre disait « on ne modifie pas une page archivee » -- §23.2, « une
#  interdiction liee a la ressource ou a l'etat prevaut sur le cumul des roles ».
#  Il est toujours vrai, mais il ne peut plus vivre dans la REQUETE : une page
#  archivee est precisement la cible de `RESTAURER`, et une requete qui l'exclut
#  rendrait la restauration impossible a resoudre. L'etat est donc LU, et c'est
#  `_actions_selon_l_etat` qui en derive ce qui est permis.
#
#  **AUCUN FILTRE SUR `state` NON PLUS, ET C'EST TOUJOURS DELIBERE.** On edite
#  precisement un BROUILLON : exiger `published` rendrait la route inutilisable
#  pour ce qu'elle sert. La lecture de `T5` ne sert que le publie parce qu'elle
#  sert le PUBLIC ; celle-ci sert l'AUTEUR, qui a deja du prouver un role.
_PAGE_CIBLE: Final[str] = """
SELECT page_type, circle_id, office_id, state, archived_at
  FROM content_page
 WHERE id = :page AND entity_id = :entite
"""

#  §8.4 : une responsabilite ACTIVE de ce type, sur CETTE ressource.
#
#  **`period @> :instant`, JAMAIS `ends_at IS NULL`.** Une affectation FUTURE a
#  elle aussi un `ends_at` nul, et la compter comme active accorderait un droit
#  qui n'existe pas encore : c'est `ECART-056`, et le temoin ou SEUL l'instant
#  avance est celui qui a le plus servi au LOT 5.
#
#  **DEUX DE CES QUATRE FILTRES SONT REDONDANTS, ET LE TEMOIN L'A DIT** -- les
#  retirer laisse les trente-six tests verts. La cause est au catalogue, relevee
#  le 18/09/2026 :
#
#    `responsibility_type`  `ck_..._portee_selon_le_type` est une biconditionnelle
#                           STRICTE : un `circle_id` non nul implique `BOOSTER`,
#                           un `office_id` non nul implique `OFFICE_MANAGER`.
#                           Filtrer sur la colonne fixe donc deja le type.
#    `entity_id`            `fk_framework_responsibility_circle` est COMPOSITE
#                           -- `(circle_id, entity_id) REFERENCES circle(id,
#                           entity_id)` -- donc une responsabilite qui pointe le
#                           cercle C a forcement l'entite de C, comme la page.
#
#  **Les deux sont CONSERVES** : c'est l'idiome de cloisonnement de tout ce
#  depot, et une requete locale qui ne nommerait pas son entite se lirait comme
#  une requete globale. **Mais ils ne sont pas ce qui protege**, et un test exige
#  que la base continue de l'interdire (§7.32). C'est la TROISIEME occurrence de
#  cette classe apres `T4-2` et `T5-1` -- et trois fois sur trois, ce qui
#  protegeait vraiment etait une contrainte ailleurs, deja sous controle.
#
#  **Les deux AUTRES travaillent, eux** : `person_id = :acteur` -- sans lui, la
#  responsabilite de n'importe qui sur ce cercle accorderait le droit -- et
#  `{colonne} = :ressource`, qui borne au cercle du Booster.
_RESPONSABILITE_SUR_LA_RESSOURCE: Final[str] = """
SELECT 1 FROM framework_responsibility_assignment
 WHERE person_id = :acteur AND entity_id = :entite
   AND responsibility_type = :type_de_responsabilite
   AND {colonne} = :ressource
   AND archived_at IS NULL AND period @> :instant
 LIMIT 1
"""


def _actions_selon_l_etat(*, etat: str, archivee: bool) -> frozenset[ActionEditoriale]:
    """Ce que l'ETAT de la page permet, quels que soient les roles — §23.2.

    « Une interdiction liee a la ressource ou a l'**etat** prevaut sur le cumul
    des roles. » Cette fonction porte cette moitie-la, et elle ne connait aucun
    role : `resoudre_le_perimetre_editorial` intersecte les deux.

        archivee              RESTAURER, et elle seule
        draft, non archivee   MODIFIER, PUBLIER, ARCHIVER
        published, idem       MODIFIER, ARCHIVER -- PUBLIER ne s'offre pas deux fois

    **`archived_at` EST LE DISCRIMINANT, PAS `state`, ET LES DEUX PEUVENT
    DIVERGER.** Le §15.1 declare `state` a trois valeurs dont `archived` ; le
    §3.1 declare `archived_at` sur toute table metier. **Le corpus ne dit nulle
    part qu'ils sont equivalents**, et aucune contrainte ne l'exige -- le decor
    de `T4` produit d'ailleurs les deux divergences, deliberement, pour prouver
    que sa lecture de `publie` est exacte. En poser une les rendrait impossibles
    et detruirait cette preuve pour rien (§6.5, §7.41).

    Les deux divergences se lisent donc, et **dans le sens le plus restrictif** :

      - `state = archived` sans `archived_at` : la page n'est pas archivee comme
        RESSOURCE, donc modifiable et archivable -- mais pas publiable, son etat
        n'etant pas `draft` ;
      - `state = published` avec `archived_at` : la page EST archivee, donc seule
        la restauration s'offre -- et la restauration remet `state` a `draft`, ce
        qui repare la divergence au passage.

    **CE QUI GARANTIT QUE L'API N'EN CREE JAMAIS** n'est pas une contrainte,
    c'est que `archiver_une_page` et `restaurer_une_page` ecrivent les deux
    colonnes dans le MEME `UPDATE` : les separer exigerait de casser le code, pas
    d'oublier un appel (§7.35). Un test l'exige dans les deux sens.
    """
    if archivee:
        return frozenset({ActionEditoriale.RESTAURER})
    if etat == EtatDePage.DRAFT.value:
        return frozenset(
            {ActionEditoriale.MODIFIER, ActionEditoriale.PUBLIER, ActionEditoriale.ARCHIVER}
        )
    return frozenset({ActionEditoriale.MODIFIER, ActionEditoriale.ARCHIVER})


def resoudre_le_perimetre_editorial(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    page: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> PerimetreEditorial:
    """Les actions editoriales que `acteur` peut mener sur `page`, dans `entite`.

    **LE RESULTAT EST UNE INTERSECTION DE DEUX CHOSES INDEPENDANTES** : ce que
    les ROLES accordent -- §13, §18 -- et ce que l'ETAT de la page permet --
    §23.2. Les melanger donnerait une regle unique ou deux sources se
    confondraient, et c'est precisement ce que `T6` a refuse de faire pour les
    deux grilles d'ecriture.

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est **deja
    applique** : hors de son entite principale une personne n'a que `EMP`, et
    `EMP` ne porte aucun droit editorial. Le redire ici donnerait deux regles
    pour une seule (`DEC-466`).

    **`CREER` N'EST JAMAIS RENDU PAR CETTE FONCTION**, et ce n'est pas un oubli :
    creer ne porte sur aucune page existante, donc sur aucune cible que cette
    signature puisse recevoir. `peut_creer_une_page` repond a cette question-la.
    """
    ligne = connexion.execute(text(_PAGE_CIBLE), {"page": page, "entite": entite}).one_or_none()
    if ligne is None:
        return PerimetreEditorial(actions=frozenset())

    selon_l_etat = _actions_selon_l_etat(etat=str(ligne[3]), archivee=ligne[4] is not None)

    if roles & ROLES_DE_PORTEE_ENTITE:
        return PerimetreEditorial(actions=selon_l_etat & ACTIONS_DES_ROLES_D_ENTITE)

    portee = PORTEES_LOCALES.get(str(ligne[0]))
    #  **`portee.role not in roles` N'EST PAS REDONDANT AVEC LA REQUETE QUI SUIT,
    #  ET C'EST LE §5.1 QUI LE DIT.** « Hors de son entite principale, une
    #  personne possede uniquement les droits `EMP` ; ses responsabilites [...]
    #  ne s'appliquent pas. » `resoudre_les_permissions` applique deja cette
    #  regle et rend `EMP` seul -- mais la responsabilite, elle, est TOUJOURS en
    #  base. Sans ce test, ce module irait la chercher et la trouverait, donc il
    #  rendrait le droit que le §5.1 vient de retirer.
    if portee is None or portee.role not in roles:
        #  Un type sans portee locale -- `HOME`, `FRAMEWORK`, `LEGAL` -- n'est
        #  ecrit que par les roles d'entite, et c'est le §13 : sa ligne « Creer un
        #  contenu general » ne porte ni `BOOST` ni `OFFICE`, et aucune autre
        #  ligne ne leur donne un contenu qui ne soit pas rattache.
        return PerimetreEditorial(actions=frozenset())

    #  La colonne vient de `PORTEES_LOCALES`, pas de l'appelant : elle ne peut
    #  valoir que `circle_id` ou `office_id`, et un test exige que les deux
    #  existent sur `content_page`. C'est ce qui rend l'interpolation sure.
    ressource = ligne[1] if portee.colonne == "circle_id" else ligne[2]
    if ressource is None:
        #  Une page `CIRCLE` sans `circle_id` est interdite par la contrainte de
        #  verification de `T1`. Le cas ne peut donc pas arriver -- mais le
        #  traiter en refus plutot qu'en exception evite d'inventer un droit si
        #  un type futur rendait le rattachement facultatif.
        return PerimetreEditorial(actions=frozenset())

    requete = _RESPONSABILITE_SUR_LA_RESSOURCE.format(colonne=portee.colonne)
    active = connexion.execute(
        text(requete),
        {
            "acteur": acteur,
            "entite": entite,
            "type_de_responsabilite": portee.responsabilite.value,
            "ressource": ressource,
            "instant": instant,
        },
    ).first()
    if active is None:
        return PerimetreEditorial(actions=frozenset())
    #  **L'INTERSECTION EST CE QUI RETIRE `RESTAURER` AU BOOSTER**, et elle le
    #  fait sans qu'aucun test explicite ne le nomme ici : sa page archivee
    #  n'offre que `RESTAURER`, que `ACTIONS_DES_PORTEES_LOCALES` ne contient
    #  pas. Le resultat est l'ensemble vide, donc le meme 403 que partout.
    return PerimetreEditorial(actions=selon_l_etat & ACTIONS_DES_PORTEES_LOCALES)


def peut_creer_une_page(roles: frozenset[RoleDeLaMatrice]) -> bool:
    """§13, « Creer un contenu general » — `ESM`, `ADM-E` et `SUPER`, et eux seuls.

    **AUCUNE CONNEXION, AUCUNE CIBLE, AUCUN INSTANT**, et c'est une difference
    reelle avec `resoudre_le_perimetre_editorial` : la creation ne porte sur
    aucune ressource existante, et les trois roles ont une portee d'entite ou
    globale. Prendre des parametres inutilises laisserait croire qu'ils sont
    examines -- §7.32.
    """
    return bool(roles & ROLES_DE_CREATION)
