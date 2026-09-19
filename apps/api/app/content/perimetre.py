"""Qui peut ECRIRE quel contenu — annexe A §13, §10.2 et §10.3. LOT 6, `T6`.

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

« ENTITE » N'EST PAS « PERIMETRE », ET C'EST `T7` QUI LE PAIERA

  Toujours au §13, l'`ESM` a « Entite » pour creer et modifier, et
  **« Perimetre »** pour publier et archiver. Une grille unique par role les
  confondrait. Ce module ne porte QUE la modification ; la publication,
  l'archivage et la restauration sont `US006`, sous-etape `T7`.

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
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.content.modeles import TypeDePage
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice


class ActionEditoriale(enum.StrEnum):
    """Les deux actions de `T6`, et elles ont des grilles DIFFERENTES.

    `PUBLIER`, `ARCHIVER` et `RESTAURER` ne sont pas ici : ce sont les trois
    dernieres lignes du §13, story `US006`, sous-etape `T7`. Les declarer sans
    les implementer donnerait des membres que personne ne lit -- §7.32.
    """

    CREER = "creer"
    MODIFIER = "modifier"


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


#  La page existe-t-elle dans cette entite, et quel est son rattachement ? Le
#  couple `(id, entity_id)` porte l'isolation (§25.3) ; un `WHERE` sur l'entite
#  seule confondrait deux pages d'entites differentes.
#
#  **`archived_at IS NULL` : ON NE MODIFIE PAS UNE PAGE ARCHIVEE.** §23.2, « une
#  interdiction liee a la ressource ou a l'etat prevaut sur le cumul des roles ».
#  La restaurer est une AUTRE ligne du §13, a une AUTRE grille -- « Restaurer |
#  ESM Conditionnel » -- et c'est `T7`. Cela vaut aussi pour `SUPER`.
#
#  **AUCUN FILTRE SUR `state`, ET C'EST DELIBERE.** On edite precisement un
#  BROUILLON : exiger `published` rendrait la route inutilisable pour ce qu'elle
#  sert. La lecture de `T5` ne sert que le publie parce qu'elle sert le PUBLIC ;
#  celle-ci sert l'AUTEUR, qui a deja du prouver un role d'ecriture.
_PAGE_MODIFIABLE: Final[str] = """
SELECT page_type, circle_id, office_id
  FROM content_page
 WHERE id = :page AND entity_id = :entite AND archived_at IS NULL
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

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est **deja
    applique** : hors de son entite principale une personne n'a que `EMP`, et
    `EMP` ne porte aucun droit editorial. Le redire ici donnerait deux regles
    pour une seule (`DEC-466`).

    **`CREER` N'EST JAMAIS RENDU PAR CETTE FONCTION**, et ce n'est pas un oubli :
    creer ne porte sur aucune page existante, donc sur aucune cible que cette
    signature puisse recevoir. `peut_creer_une_page` repond a cette question-la.
    """
    ligne = connexion.execute(
        text(_PAGE_MODIFIABLE), {"page": page, "entite": entite}
    ).one_or_none()
    if ligne is None:
        return PerimetreEditorial(actions=frozenset())

    if roles & ROLES_DE_PORTEE_ENTITE:
        return PerimetreEditorial(actions=frozenset({ActionEditoriale.MODIFIER}))

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
    return PerimetreEditorial(actions=frozenset({ActionEditoriale.MODIFIER}))


def peut_creer_une_page(roles: frozenset[RoleDeLaMatrice]) -> bool:
    """§13, « Creer un contenu general » — `ESM`, `ADM-E` et `SUPER`, et eux seuls.

    **AUCUNE CONNEXION, AUCUNE CIBLE, AUCUN INSTANT**, et c'est une difference
    reelle avec `resoudre_le_perimetre_editorial` : la creation ne porte sur
    aucune ressource existante, et les trois roles ont une portee d'entite ou
    globale. Prendre des parametres inutilises laisserait croire qu'ils sont
    examines -- §7.32.
    """
    return bool(roles & ROLES_DE_CREATION)
