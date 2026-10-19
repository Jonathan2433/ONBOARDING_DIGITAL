"""Les routes editoriales — LOT 6, `T5` a `T10`, stories `MVP-L06-US004` a `US006`.

    GET  /entities/{code}/pages/gestion                  `T10`, l'editeur : toutes, tous etats
    GET  /entities/{code}/pages/{page:uuid}/gestion       `T10`, une page, tous etats + `version`
    GET  /entities/{code}/pages/{type_de_page}/{slug}    `T5`, lire le PUBLIE
    POST /entities/{code}/pages                          `T6`, creer un BROUILLON
    PUT  /entities/{code}/pages/{page}/contenu           `T6`, ecrire le contenu
    POST /entities/{code}/pages/{page}/publication       `T7`, publier
    POST /entities/{code}/pages/{page}/archivage         `T7`, archiver
    POST /entities/{code}/pages/{page}/restauration      `T7`, restaurer
    GET  /entities/{code}/liens                          `T8`, l'accueil : les ACTIFS
    GET  /entities/{code}/liens/gestion                  `T8`, l'editeur : tous
    POST /entities/{code}/liens                          `T8`, creer un lien
    PUT  /entities/{code}/liens/ordre                    `T8`, reordonner
    PUT  /entities/{code}/liens/{lien}                   `T8`, modifier un lien

LES DEUX ROUTES DE GESTION DES PAGES SONT DECLAREES **AVANT** LA LECTURE DE `T5`,
ET L'ORDRE EST SIGNIFIANT — `T10`

  Meme piege que `/liens/ordre` face a `/liens/{lien}` : `/pages/{page}/gestion`
  partage sa FORME (deux segments apres `/pages/`) avec la lecture publique
  `/pages/{type_de_page}/{slug}`. Sans l'ordre de declaration ET le
  convertisseur `{page:uuid}`, une page PUBLIEE dont le slug vaudrait
  litteralement « gestion » serait interceptee par la mauvaise route — mesure
  avec `Route.matches()` de Starlette, voir le detail dans `routeur_contenus`.

DEUX LECTURES DES LIENS, ET DEUX GRILLES — `T8`

  L'accueil ne sert que les liens **actifs** : c'est la raison d'etre du champ
  `active` du §15.3, et les servir tous a tout le monde le viderait de son sens.
  L'ecran de gestion les voit **tous**, sans quoi desactiver un lien serait un
  aller sans retour. Deux audiences, deux routes, **une seule garde par route** :
  un garde-fou dont le perimetre depend d'un parametre de requete est un
  garde-fou qu'on finit par se tromper a relire.

  **L'ORDRE DE DECLARATION DE `/liens/ordre` ET `/liens/{lien}` EST SIGNIFIANT.**
  FastAPI retient la premiere route dont le MOTIF correspond : `/liens/{lien}`
  attraperait `/liens/ordre` puis rendrait 422 sur la conversion en UUID, sans
  jamais laisser la main a la route suivante. `/liens/ordre` est donc declaree
  AVANT, et un test le mesure -- l'inverser ferait echouer ce test au lieu de
  casser un ecran (§7.35).

DEUX ADRESSAGES, ET LA DIFFERENCE EST VOULUE

  La **lecture** adresse par `(type, slug)` : c'est l'adresse publique d'une page
  publiee, et le §15.1 la rend unique dans l'entite et le type. L'**ecriture**
  adresse par **identifiant**, parce qu'elle porte d'abord sur des BROUILLONS --
  que la lecture ne sert pas -- et parce qu'un slug est une adresse de
  publication, pas l'identite d'une ressource en cours de redaction.

  L'identifiant est rendu par la creation, et par la lecture de `T5`.

POURQUOI L'ADRESSE DE LECTURE PORTE LE TYPE **ET** LE SLUG

  L'unicite posee par `T1` est `(entity_id, page_type, slug)` sur les pages non
  archivees -- le §15.1 dit « `slug` | Unique dans l'entite **et le type** ».
  Adresser par le slug seul supposerait une unicite que le modele n'ecrit pas,
  et deux pages de types differents pourraient legitimement le partager.

  Une seule route couvre ainsi les CINQ types du §15.1 -- `HOME`, `FRAMEWORK`,
  `CIRCLE`, `OFFICE`, `LEGAL` -- la ou une route par ressource en aurait demande
  autant, chacune avec sa grille de roles a tenir a jour.

QUI LIT : LA MATRICE §5, ET SUREMENT PAS L'ANNEXE A §13 SEULE

  Le §13 porte une ligne « Consulter » a **six** colonnes et **ni `EMP` ni
  `NEW`**. Ces tableaux n'ONT PAS ces colonnes : une absence n'est pas une
  exclusion, et la lire comme telle refuserait le contenu a l'Employe -- l'acteur
  pour qui ce portail existe. Le §5 accorde « Framework », « Cercles » et
  « Bureaux » aux HUIT roles authentifies ; le contenu d'une page de cercle se
  consulte comme le cercle.

LE 404 COUVRE LE BROUILLON, ET C'EST LE POINT LE PLUS IMPORTANT DE LA LECTURE

  Une page en brouillon rend le MEME 404 qu'un slug inconnu. Distinguer
  apprendrait l'existence d'un brouillon a qui n'a pas le droit de le voir, et
  vaudrait `US006` -- « **previsualiser** puis publier » -- qui est la story de
  `T7`, avec sa propre grille : le §13 donne « Publier » a une portee
  **Perimetre** la ou « Modifier » vaut **Entite**.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final, TypeVar

from fastapi import APIRouter, Depends, Path, Request, status
from pydantic import BaseModel, Field

from app.audit.motif import exiger_un_motif_si_necessaire
from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.content.cycle_de_vie import (
    PageArchivee,
    PagePubliee,
    PageRestauree,
    archiver_une_page,
    publier_une_page,
    restaurer_une_page,
)
from app.content.ecriture import (
    BlocDemande,
    creer_une_page,
    remplacer_le_contenu,
)
from app.content.liens import (
    LienInterne,
    creer_un_lien,
    lister_les_liens,
    modifier_un_lien,
    reordonner_les_liens,
)
from app.content.modeles import TYPES_DE_BLOC, TYPES_DE_LIEN, TYPES_DE_PAGE
from app.content.pages import (
    PayloadNonObjet,
    lire_la_page_de_contenu,
    lire_une_page_pour_edition,
    lister_les_pages_de_l_entite,
)
from app.content.perimetre import (
    ROLES_D_ECRITURE_EDITORIALE,
    ROLES_DE_CREATION,
    ROLES_DE_GESTION_DES_LIENS,
    ActionEditoriale,
    resoudre_le_perimetre_editorial,
)
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import EntiteListee, resoudre_une_entite_active
from app.permissions.dependances import exiger_un_role_dans_l_entite
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

DESCRIPTION_401: Final = "Aucune session valide — la matrice §5 refuse cette ressource a `ANON`."

#  Un payload qui n'est pas un objet est un defaut de DONNEE, pas une faute de
#  l'appelant : 500, et le code le nomme pour que le journal soit exploitable.
CODE_CONTENU_ILLISIBLE: Final = "contenu_illisible"
MESSAGE_CONTENU_ILLISIBLE: Final = "Un bloc de cette page porte un contenu illisible."

#  **LA LONGUEUR MAXIMALE VIENT DE LA COLONNE**, §15.1 : `slug` est
#  `varchar(160)`. L'ecrire ici en dur divergerait au premier changement (§7.27).
LONGUEUR_MAXIMALE_SLUG: Final = 160


class BlocDeContenuRendu(BaseModel):
    """Un bloc, servi comme DONNEE et jamais comme du balisage.

    **`contenu` EST UN OBJET, ET C'EST LE TYPE QUI TIENT « AUCUN HTML EXECUTE ».**
    Il n'existe aucune valeur de cette forme ou un champ designerait du balisage
    a interpreter : le perdre exigerait de changer ce type, pas de retirer un
    controle (§7.35). Ses clefs ne sont pas contraintes -- le corpus n'en nomme
    aucune, `QO-121`.
    """

    identifiant: uuid.UUID
    type_de_bloc: str
    ordre: int
    contenu: dict[str, object]


class ReponseDeLaPageDeContenu(BaseModel):
    """Une page PUBLIEE et ses blocs, dans l'ordre — `MVP-L06-US004`.

    **`nombre_de_blocs` EST DERIVE DU TUPLE.** Deux sources pour une meme
    grandeur divergent (§7.0, sixieme proposition), et un client afficherait
    « 3 blocs » au-dessus de deux.
    """

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    publiee_le: str | None
    blocs: list[BlocDeContenuRendu]
    nombre_de_blocs: int


CODE_CONTENU_HORS_PERIMETRE: Final = "contenu_hors_perimetre"
MESSAGE_CONTENU_HORS_PERIMETRE: Final = "Votre perimetre ne vous permet pas de modifier ce contenu."


class BlocSoumis(BaseModel):
    """Un bloc tel que l'auteur le soumet — LOT 6, `T6`.

    **DEUX CHAMPS, ET LES ABSENTS SONT LE POINT.**

    Il n'y a **ni `ordre`** -- il vaut l'index dans la liste, si bien que deux
    blocs de meme rang sont impossibles a exprimer (§7.35) -- **ni identifiant**
    -- la liste remplace la liste -- **ni aucun champ de nature HTML** : pas de
    `html`, pas de `format`, pas de `rendu`. C'est le type qui tient « aucun HTML
    arbitraire n'est **accepte** », et non un filtre : chercher `<script` serait
    une heuristique, donc un defaut (§7.25).

    `contenu` est un **objet**, et Pydantic refuse tout le reste au format du
    §18.3. C'est ce refus a l'ECRITURE qui garantit que le 500 de `T5` --
    `PayloadNonObjet` -- ne survienne jamais pour une donnee ecrite par l'API.
    """

    type_de_bloc: str = Field(
        min_length=1,
        max_length=32,
        description="L'un des types de `DEC-577` — " + ", ".join(f"`{t}`" for t in TYPES_DE_BLOC),
    )
    contenu: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Les donnees du bloc. **Ses clefs ne sont pas contraintes** : le corpus n'en "
            "nomme aucune, et `QO-121` porte la question a Lea. Ce qui est contraint est "
            "que ce soit un OBJET — un scalaire ou un tableau ne peut pas porter les "
            "« champs structures » du §15.2."
        ),
    )


class DemandeDeCreationDePage(BaseModel):
    """Creer une page — §13 « Creer un contenu general », modele §15.1.

    **AUCUN CHAMP `etat` NI `publiee_le`**, et ce n'est pas un oubli : la valeur
    n'est pas ignoree, elle n'existe pas. Le §13 separe « Modifier » — portee
    Entite — de « Publier » — portee **Perimetre** — et une creation qui pourrait
    publier confondrait deux droits que le document distingue.
    """

    type_de_page: str = Field(
        min_length=1,
        max_length=32,
        description="L'un des types du §15.1 — " + ", ".join(f"`{t}`" for t in TYPES_DE_PAGE),
    )
    titre: str = Field(min_length=1, description="Le titre de la page (§15.1)")
    slug: str = Field(
        min_length=1,
        max_length=LONGUEUR_MAXIMALE_SLUG,
        description="Unique dans l'entite ET le type (§15.1)",
    )
    #  **PAR CODE, COMME PARTOUT AILLEURS DEPUIS `T3` ET `T4`.** Deux modes
    #  d'adressage d'une meme ressource divergeraient, et l'un des deux serait
    #  celui qu'aucun ecran n'emploie.
    cercle: str | None = Field(
        default=None, description="Le `code` du cercle — requis pour une page `CIRCLE` (§15.1)"
    )
    bureau: str | None = Field(
        default=None, description="Le `code` du bureau — requis pour une page `OFFICE` (§15.1)"
    )
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class DemandeDEcritureDuContenu(BaseModel):
    """Remplacer le titre et les blocs d'une page — §13 « Modifier un contenu de … »."""

    #  §18.4 : « les modifications sensibles utilisent une concurrence optimiste.
    #  Une version obsolete produit un 409 **sans ecrasement silencieux** ».
    #  **OBLIGATOIRE, ET C'EST LE DEFAUT `T11-6` DU LOT 5 QUI L'A APPRIS** : un
    #  bouchon rendait 200 sur un corps vide, l'API rend 422.
    version: int = Field(ge=1, description="La version lue — §18.4, concurrence optimiste")
    titre: str = Field(min_length=1, description="Le titre de la page (§15.1)")
    blocs: list[BlocSoumis] = Field(
        default_factory=list,
        description=(
            "La liste **remplace** la liste. Les blocs retires sont ARCHIVES, jamais "
            "supprimes (modele §2.4). Une liste vide est legitime : une page sans bloc "
            "existe, et `T5` la rend avec un tableau vide."
        ),
    )
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class ReponseDeCreationDePage(BaseModel):
    """La page neuve, toujours en BROUILLON."""

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    #  Rendu plutot que tu, et c'est une mesure et non une promesse : l'appelant
    #  LIT que sa page est en brouillon, au lieu de le deduire de la doc.
    etat: str
    version: int


class ReponseDEcritureDuContenu(BaseModel):
    """Ce que l'ecriture a produit — `MVP-L06-US004`.

    **`blocs_archives` EST RAPPORTE PLUTOT QUE TU** (§7.20) : un auteur qui envoie
    deux blocs la ou la page en portait cinq doit voir que trois ont quitte
    l'affichage. Le taire rendrait une suppression accidentelle invisible.
    """

    version: int
    blocs: list[BlocDeContenuRendu]
    nombre_de_blocs: int
    blocs_archives: int


class PageDeGestionRendue(BaseModel):
    """Le sommaire d'une page, TOUS ETATS confondus — `T10`.

    `circle_id`/`office_id` servent a l'ecran a retrouver LA page de SON cercle
    ou de SON bureau, en les confrontant a l'identifiant deja connu — le meme
    que celui que `T3`/`T4` rendent sous `identifiant`.
    """

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    etat: str
    version: int
    circle_id: uuid.UUID | None
    office_id: uuid.UUID | None


class ReponseDesPagesDeGestion(BaseModel):
    """Toutes les pages de l'entite — `T10`. Meme parti que `/liens/gestion`."""

    pages: list[PageDeGestionRendue]


class ReponseDeLaPageDeContenuPourEdition(BaseModel):
    """Une page et ses blocs, TOUS ETATS confondus, avec sa `version` — `T10`.

    **PORTE `version` ET `etat`, QUE LA LECTURE PUBLIQUE DE `T5` NE PORTE PAS** :
    c'est precisement ce qui manquait pour qu'un editeur puisse relire son propre
    brouillon apres un rechargement, et l'ecrire ensuite avec la concurrence
    optimiste du §18.4.
    """

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    etat: str
    version: int
    publiee_le: str | None
    blocs: list[BlocDeContenuRendu]
    nombre_de_blocs: int


class DemandeDeTransition(BaseModel):
    """Publier, archiver ou restaurer — la version, et un motif conditionnel.

    **AUCUN CHAMP D'ETAT CIBLE, ET C'EST LE MEME PARTI QUE LA CREATION DE `T6`.**
    Un champ `etat` laisserait croire a une machine a etats pilotee par
    l'appelant, et il faudrait alors refuser toutes les transitions que le §13
    n'ecrit pas. L'etat cible est porte par la ROUTE : trois chemins, trois
    lignes du §13, et les transitions absentes du document sont **inexprimables**
    plutot que refusees (§7.35).

    **LE MOTIF N'ETAIT PAS OBLIGATOIRE A `T4`**, et le §18.1 en donnait la
    raison : archiver un contenu n'est pas l'un des cinq cas qu'il enumere.
    LOT 10 `T7` ferme `ECART-064` par le sixieme angle, transversal : « toute
    intervention du super-administrateur dans une entite » — qui s'applique
    ICI des que `SUPER` est l'acteur, meme si l'action elle-meme reste hors
    des cinq cas nommement cites.
    """

    #  §18.4, « concurrence optimiste [...] sans ecrasement silencieux ».
    #  Obligatoire comme pour l'ecriture : publier ce qu'un autre vient de
    #  reecrire est exactement ce que ce verrou existe pour empecher.
    version: int = Field(ge=1, description="La version lue — §18.4, concurrence optimiste")
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class ReponseDePublication(BaseModel):
    """`US006`, « la version publiee est identifiable » — la voici, datee."""

    version: int
    etat: str
    publiee_le: dt.datetime


class ReponseDArchivageDUnContenu(BaseModel):
    """Ce que l'archivage a produit.

    `publiee_le` reste rendu : une page archivee **apres** publication garde la
    date a laquelle elle a ete publiee, et `null` distingue celle qui ne l'a
    jamais ete. Deux histoires differentes, deux valeurs differentes.
    """

    version: int
    etat: str
    archivee_le: dt.datetime
    publiee_le: dt.datetime | None


class ReponseDeRestaurationDUnContenu(BaseModel):
    """La page revient en BROUILLON, et `etat` le DIT plutot que la doc.

    Republier est un second geste, explicite, a la grille du §13 « Publier ».
    """

    version: int
    etat: str
    publiee_le: dt.datetime | None


class LienInterneServi(BaseModel):
    """Un lien interne, tel que les cinq routes de `T8` le rendent — modele §15.3.

    **UNE SEULE STRUCTURE POUR LES DEUX AUDIENCES**, y compris `actif`, que la
    lecture publique rend toujours a `true` puisqu'elle ne sert que des actifs.
    Un champ constant parait inutile ; le taire obligerait l'ecran de gestion a
    lire une AUTRE structure, et deux structures pour une meme ressource
    divergent au premier ajout de colonne.

    **`reference_d_icone` EST SERVIE TELLE QUELLE.** Le §15.3 la nomme et ne dit
    NULLE PART quel vocabulaire elle emploie -- aucune bibliotheque d'icones
    n'est citee dans le corpus. C'est le meme parti que `payload_json` chez `T5` :
    une donnee opaque, dont le front connait le sens, plutot qu'une enumeration
    inventee (§6.5).
    """

    identifiant: uuid.UUID
    libelle: str
    url: str
    type_de_lien: str
    description: str | None
    reference_d_icone: str | None
    rang: int
    actif: bool
    version: int


class ReponseDesLiensInternes(BaseModel):
    """La liste ordonnee, et son compte.

    `nombre_de_liens` est **rapporte plutot que tu** (§7.20) : un ecran qui
    n'afficherait rien doit pouvoir distinguer « aucun lien » de « la reponse
    n'est pas arrivee », et un controle qui compte doit confronter son compte a
    un attendu (§7.0, troisieme proposition).
    """

    liens: list[LienInterneServi]
    nombre_de_liens: int


class _ChampsDuLien(BaseModel):
    """Les six champs qui DEFINISSENT un lien — partages par la creation et la modification.

    **NI `rang` NI `identifiant`, ET C'EST LE POINT.** Le rang n'est pas une
    propriete du lien mais de la LISTE : la creation ajoute en queue, et
    `PUT …/liens/ordre` seule le reecrit. L'offrir ici rendrait une permutation
    de deux liens impossible -- mesure du 22/09/2026, l'index unique partiel de
    `T1` refuse un echange en un seul `UPDATE`.

    **AUCUN CHAMP DE NATURE HTML NON PLUS** : ni `html`, ni `format`, ni `rendu`.
    `libelle` et `description` sont du TEXTE, et le critere 6 du lot -- « aucun
    contenu arbitraire ne peut injecter du code » -- est tenu ici par ce qui
    n'existe pas, exactement comme chez `T6`.
    """

    libelle: str = Field(min_length=1, description="Le libelle affiche sur la carte (§15.3)")
    url: str = Field(
        min_length=1,
        description=(
            "L'adresse de la ressource. **Validee selon la liste de protocoles autorises** "
            "du §15.3 — `DEC-587`, `QO-120` : `https` seul, et `http` est refuse sous son "
            "propre code pour que l'auteur voie qu'il lui manque un `s`. Une adresse sans "
            "serveur — « https:quelquechose » — est refusee elle aussi : une liste blanche "
            "de protocoles ne suffit pas, c'est mesure."
        ),
    )
    type_de_lien: str = Field(
        min_length=1,
        #  **LA LONGUEUR VIENT DE LA COLONNE**, §15.3 : `link_type` est
        #  `varchar(32)`. L'ecrire en dur divergerait au premier changement (§7.27).
        max_length=32,
        description="L'un des types du §15.3 — " + ", ".join(f"`{t}`" for t in TYPES_DE_LIEN),
    )
    description: str | None = Field(
        default=None, description="Le texte secondaire de la carte, facultatif (§15.3)"
    )
    reference_d_icone: str | None = Field(
        default=None,
        #  `icon_reference` est `varchar(64)` au §15.3 — derive, pas recopie.
        max_length=64,
        description=(
            "Une reference d'icone, facultative. **Le corpus n'en donne aucun "
            "vocabulaire** : elle est servie telle quelle, et le front en connait le sens."
        ),
    )
    actif: bool = Field(
        default=True,
        description=(
            "Un lien inactif n'est plus servi par l'accueil. **C'est le seul moyen de "
            "retirer un lien** : le §15.3 declare `active` a cote de `archived_at` et "
            "`T1` a refuse de les fondre ; aucune ligne du §13 ni du §19 ne nomme "
            "l'archivage d'un lien."
        ),
    )


class DemandeDeCreationDeLien(_ChampsDuLien):
    """Creer un lien — §13 « Gerer les cartes Hub/Academy/SharePoint », §19.

    **AUCUN CHAMP `version`**, et ce n'est pas un oubli : il n'y a rien a ne pas
    ecraser. Le §18.4 borne les modifications, pas les creations.
    """

    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class DemandeDeModificationDeLien(_ChampsDuLien):
    """Remplacer la definition d'un lien — §19 « Modifier les liens internes »."""

    #  §18.4 : « les modifications sensibles utilisent une concurrence optimiste.
    #  Une version obsolete produit un 409 **sans ecrasement silencieux** ».
    #  Obligatoire, comme chez `T6` et `T7` -- defaut `T11-6` du LOT 5, ou un
    #  bouchon rendait 200 sur un corps vide la ou l'API rend 422.
    version: int = Field(ge=1, description="La version lue — §18.4, concurrence optimiste")
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class DemandeDOrdreDesLiens(BaseModel):
    """Reecrire l'ordre d'affichage — modele §15.3, `display_order`.

    **LE RANG VAUT L'INDEX DE LA LISTE**, jamais une valeur envoyee : deux liens
    de meme rang sont **inexprimables** plutot que refuses (§7.35), exactement
    comme les blocs de `T6`.

    **AUCUN `version` ICI, ET C'EST UN CHOIX QU'IL FAUT DIRE.** La concurrence est
    portee par l'EXIGENCE D'EXHAUSTIVITE : la liste doit nommer exactement une
    fois chacun des liens non archives de l'entite, si bien qu'une creation ou une
    modification concurrente rend l'ordre soumis **incomplet**, donc 422. Un champ
    `version` aurait exige un porteur, et la collection n'en a pas -- le
    fabriquer sur `entity.version`, qui change pour tout autre chose, aurait
    donne un verrou qui se declenche a tort et ne se declenche pas a propos.
    """

    ordre: list[uuid.UUID] = Field(
        description=(
            "Les identifiants des liens, dans l'ordre voulu. **La liste doit etre "
            "exhaustive** : exactement une fois chacun des liens non archives de "
            "l'entite, actifs comme inactifs."
        )
    )
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


#  Le resultat d'une transition : `PagePubliee`, `PageArchivee` ou `PageRestauree`.
#  Un `TypeVar` plutot qu'une union, pour que chaque route recoive EXACTEMENT le
#  type de son service -- une union obligerait chaque appelant a le retrecir, et
#  mypy cesserait de verifier qu'on lit les bons champs.
_Resultat = TypeVar("_Resultat")


def _proteger(parametres: Parametres, requete: Request) -> None:
    """Appliquer les deux barrieres CSRF a une ecriture — `DEC-531`.

    **LE JETON EST LU DANS LE COOKIE, PAS RECU DE LA DEPENDANCE.**
    `SessionEtablie` ne le porte pas a dessein : le faire circuler multiplierait
    les endroits d'ou il peut fuir vers un journal. La garde a valide la session
    depuis ce meme cookie, donc il est la ; s'il manquait, passer `None`
    DESARMERAIT la barriere de jeton en silence, et on refuse plutot.

    **ELLE N'EST PAS RECOPIEE ICI** : `proteger_du_csrf` vit dans
    `app/auth/dependances.py` depuis `T7` du LOT 5, et deux copies d'une meme
    regle divergent au premier changement (`DEC-466`).
    """
    jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
    proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")


def _resoudre_ou_404(connexion: Connection, code: str) -> EntiteListee:
    """L'entite ACTIVE de ce code, ou le 404 que rend tout le reste de l'API."""
    entite = resoudre_une_entite_active(connexion, code)
    if entite is None:
        raise ErreurApplicative(
            code=CODE_ENTITE_INTROUVABLE,
            message=MESSAGE_ENTITE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    return entite


def routeur_contenus(parametres: Parametres) -> APIRouter:
    """Routeur du rendu et de l'ecriture editoriale, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["contenus"])

    #  **DEUX GARDES, DEFINIES ICI ET NON PLUS BAS, POUR UNE RAISON D'ORDRE DE
    #  ROUTES ET NON DE LISIBILITE.** Voir le motif complet au-dessus de
    #  `lire_une_page_pour_gestion` : `/pages/{page}/gestion` doit etre
    #  ENREGISTREE avant `/pages/{type_de_page}/{slug}`, et la garde qu'elle
    #  emploie doit donc exister avant cette declaration.
    garde_de_creation = exiger_un_role_dans_l_entite(parametres, ROLES_DE_CREATION)
    garde_d_ecriture = exiger_un_role_dans_l_entite(parametres, ROLES_D_ECRITURE_EDITORIALE)

    # ========================================================================
    #
    #  LA LECTURE POUR L'EDITEUR — LOT 6, `T10`
    #
    #    **UN TROU DEPUIS `T6`, PAS UN REPORT VOULU.** La lecture de `T5`,
    #    juste en dessous, ne sert que le PUBLIE (`US006`) : un editeur qui
    #    recharge son ecran en cours de redaction, ou revient sur un brouillon
    #    jamais publie, n'avait alors AUCUNE route pour relire son propre
    #    travail — ni `version`, dont l'ecriture suivante a besoin pour la
    #    concurrence optimiste du §18.4.
    #
    #    **MEME PARTI QUE `T8` POUR LES LIENS** : `/liens` ne sert que l'actif,
    #    `/liens/gestion` sert les deux. Ici, la lecture publique ne sert que
    #    le publie, `/pages/gestion` et `/pages/{page}/gestion` servent les
    #    TROIS etats — un editeur qui archive doit pouvoir retrouver sa page
    #    pour la restaurer.
    #
    #    **`/pages/{page}/gestion` EST DECLAREE AVANT `/pages/{type_de_page}/
    #    {slug}`, ET L'ORDRE EST SIGNIFIANT — MEME PIEGE QUE `/liens/ordre`.**
    #    Les deux routes ont DEUX segments apres `/pages/`, et le second de la
    #    lecture publique (`{slug}`) est aussi generique que n'importe quel
    #    segment : sans cet ordre, `GET …/pages/<uuid>/gestion` matcherait
    #    D'ABORD la lecture publique, avec `type_de_page=<uuid>` et
    #    `slug='gestion'`, et rendrait 404 avant que ma route n'ait la main.
    #    **Mesure, pas suppose** : `Route.matches()` de Starlette confirme le
    #    FULL match sur la lecture publique quand l'ordre inverse est essaye.
    #
    # ========================================================================

    @routeur.get(
        "/entities/{code}/pages/gestion",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesPagesDeGestion,
        dependencies=[Depends(garde_d_ecriture)],
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role d'ecriture editoriale dans cette entite."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
        },
        summary="Toutes les pages de l'entite, tous etats confondus",
        description=(
            "`T10`. **AUCUNE PORTEE LOCALE N'EST APPLIQUEE ICI** : la garde verifie qu'un "
            "role d'ecriture editoriale existe quelque part dans l'entite, exactement comme "
            "`/liens/gestion`, qui n'a pas de portee locale non plus. Un Booster voit donc "
            "TOUTES les pages de son entite, mais ne pourra OUVRIR que la sienne — refusee "
            "en 403 par `/pages/{page}/gestion`, qui resout le perimetre."
        ),
    )
    def lister_les_pages_pour_gestion(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee",
        ),
    ) -> ReponseDesPagesDeGestion:
        """Le sommaire de toutes les pages d'une entite — `T10`."""
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            pages = lister_les_pages_de_l_entite(connexion, entite=entite.id)

        return ReponseDesPagesDeGestion(
            pages=[
                PageDeGestionRendue(
                    identifiant=p.identifiant,
                    type_de_page=p.type_de_page,
                    titre=p.titre,
                    slug=p.slug,
                    etat=p.etat,
                    version=p.version,
                    circle_id=p.circle_id,
                    office_id=p.office_id,
                )
                for p in pages
            ]
        )

    @routeur.get(
        #  **`{page:uuid}`, ET NON `{page}`.** Un slug utilisateur peut valoir
        #  litteralement « gestion » (§15.1 : texte libre, jusqu'a 160 caracteres).
        #  Sans le convertisseur, Starlette route sur la FORME du chemin avant
        #  tout controle de type -- mesure avec `Route.matches()` -- et cette
        #  route, enregistree en premier, aurait alors intercepte pour de bon
        #  `GET …/pages/{type_de_page}/gestion` d'une page PUBLIEE reelle. Avec
        #  le convertisseur, un premier segment non-UUID echoue a CETTE route et
        #  retombe sur la lecture publique -- verifie dans les deux sens.
        "/entities/{code}/pages/{page:uuid}/gestion",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLaPageDeContenuPourEdition,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Deux causes, deux codes — memes que l'ecriture. `acces_refuse` : "
                    "aucun role d'ecriture editoriale. `contenu_hors_perimetre` : le role "
                    "existe mais pas sur CETTE page."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite ou page inconnue — un seul gabarit, meme motif que l'ecriture."
                )
            },
        },
        summary="Une page et ses blocs, tous etats confondus, avec sa version",
        description=(
            "`T10`. Sert a l'ecran d'edition de charger ou de recharger une page en cours "
            "de redaction — BROUILLON compris, ce que la lecture publique de `T5` refuse. "
            "**Meme grille que l'ecriture** : le role est verifie, puis le perimetre sur "
            "CETTE page precisement, avec la MEME resolution que `PUT …/contenu`."
        ),
    )
    def lire_une_page_pour_gestion(
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDeLaPageDeContenuPourEdition:
        """Une page et ses blocs, tous etats confondus, pour l'ecran d'edition — `T10`."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_editorial(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                page=page,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if not perimetre.actions:
                #  **L'ENSEMBLE VIDE, PAS L'ABSENCE DE `MODIFIER`.** Mesure le
                #  22/09/2026 : `_actions_selon_l_etat` ne rend que `RESTAURER`
                #  sur une page ARCHIVEE — « on ne modifie pas un archive, on le
                #  restaure ». Exiger `MODIFIER` ici refusait donc CETTE route a
                #  la seule situation qui la justifie : retrouver une page
                #  archivee pour la restaurer. Meme gabarit unique que
                #  l'ecriture pour les autres causes : la page n'existe pas,
                #  elle est d'une autre entite, ou aucun role ne porte sur elle.
                raise ErreurApplicative(
                    code=CODE_CONTENU_HORS_PERIMETRE,
                    message=MESSAGE_CONTENU_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            trouvee = lire_une_page_pour_edition(connexion, entite=entite.id, page=page)
            if trouvee is None:
                #  Le perimetre a resolu des ACTIONS sur cette page : si la
                #  lecture ne la retrouve plus dans la MEME transaction, c'est
                #  qu'aucune ligne ne correspond — un 404, jamais un 500.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )

        return ReponseDeLaPageDeContenuPourEdition(
            identifiant=trouvee.identifiant,
            type_de_page=trouvee.type_de_page,
            titre=trouvee.titre,
            slug=trouvee.slug,
            etat=trouvee.etat,
            version=trouvee.version,
            publiee_le=trouvee.publiee_le,
            blocs=[
                BlocDeContenuRendu(
                    identifiant=b.identifiant,
                    type_de_bloc=b.type_de_bloc,
                    ordre=b.ordre,
                    contenu=b.contenu,
                )
                for b in trouvee.blocs
            ],
            nombre_de_blocs=trouvee.nombre_de_blocs,
        )

    @routeur.get(
        "/entities/{code}/pages/{type_de_page}/{slug}",
        #  `dependencies=` et non `Annotated[...]` : sous `from __future__ import
        #  annotations`, FastAPI resout l'annotation dans les globals du module,
        #  n'y trouve pas la fermeture `parametres`, et rend 422 pour tout le
        #  monde sur un livrable qui PARAIT protege. Mesure du 23/08/2026.
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLaPageDeContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour SIX causes, a dessein : code d'entite "
                    "inconnu, entite non active, type de page inconnu, slug "
                    "inconnu, page d'une AUTRE entite, ou page en BROUILLON / "
                    "archivee. Distinguer le brouillon apprendrait son existence, "
                    "et viderait `US006` de son sens."
                )
            },
        },
        summary="Une page de contenu publiee et ses blocs",
        description=(
            "Les blocs d'une page PUBLIEE, dans leur ordre d'affichage — "
            "`MVP-L06-US004`. "
            "Exige une session : la matrice §5 refuse cette ressource a `ANON` et "
            "l'accorde aux huit roles authentifies **sans distinction**. "
            "**Les blocs sont servis comme DONNEES**, jamais comme du balisage : "
            "le contenu de chaque bloc est un objet JSON, et la reponse ne porte "
            "aucun champ de nature HTML — « aucun HTML arbitraire n'est stocke ou "
            "execute », cahier §10.7 et modele §15.2. "
            "**Les clefs de ce contenu ne sont pas contraintes** : le corpus n'en "
            "nomme aucune, et `QO-121` porte la question. "
            "Une page en BROUILLON rend 404 : la previsualisation est `US006`, "
            "avec sa propre grille de roles."
        ),
    )
    def lire_une_page_de_contenu(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
        type_de_page: str = Path(
            min_length=1,
            max_length=32,
            description=(
                "Le type de page du §15.1 — "
                + ", ".join(f"`{t}`" for t in TYPES_DE_PAGE)
                + ". Un type inconnu rend 404, comme un slug inconnu."
            ),
        ),
        slug: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_SLUG,
            description="Le `slug` de la page, unique dans l'entite ET le type (§15.1)",
        ),
    ) -> ReponseDeLaPageDeContenu:
        """Une page de contenu publiee et ses blocs — cahier §10.7, modele §15.2."""
        with moteur(parametres).begin() as connexion:
            #  **LA MEME RESOLUTION QUE LES DEUX ECRITURES**, et non une copie :
            #  deux chemins d'une meme regle divergent au premier changement
            #  (`DEC-466`). La forme etait ici en clair depuis `T5` ; `T6` l'a
            #  extraite en y ajoutant ses appelants, sans changer le comportement.
            entite = _resoudre_ou_404(connexion, code)
            #  **UN TYPE INCONNU N'EST PAS UNE FAUTE DE SYNTAXE, C'EST UN 404.**
            #  Le refuser en 422 distinguerait « ce type n'existe pas » de « cette
            #  page n'existe pas », ce qui ne sert personne et decrit le schema.
            if type_de_page not in TYPES_DE_PAGE:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            try:
                page = lire_la_page_de_contenu(
                    connexion, entite=entite.id, type_de_page=type_de_page, slug=slug
                )
            except PayloadNonObjet as erreur:
                #  Refuse VISIBLEMENT plutot que corrige en silence (§7.20) : le
                #  message du journal nomme le bloc, celui du client ne le nomme
                #  pas — il n'y peut rien, et l'identifiant ne le regarde pas.
                raise ErreurApplicative(
                    code=CODE_CONTENU_ILLISIBLE,
                    message=MESSAGE_CONTENU_ILLISIBLE,
                    statut=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ) from erreur
            if page is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )

        return ReponseDeLaPageDeContenu(
            identifiant=page.identifiant,
            type_de_page=page.type_de_page,
            titre=page.titre,
            slug=page.slug,
            publiee_le=page.publiee_le,
            blocs=[
                BlocDeContenuRendu(
                    identifiant=b.identifiant,
                    type_de_bloc=b.type_de_bloc,
                    ordre=b.ordre,
                    contenu=b.contenu,
                )
                for b in page.blocs
            ],
            nombre_de_blocs=page.nombre_de_blocs,
        )

    # ========================================================================
    #
    #  L'ECRITURE — LOT 6, `T6`, `MVP-L06-US004` (2 sur 3)
    #
    #    **DEUX GARDES, PARCE QUE LE §13 PORTE DEUX LIGNES DIFFERENTES.** « Creer
    #    un contenu general » ne donne rien a `BOOST` ni a `OFFICE` ; « Modifier
    #    un contenu de cercle » donne au Booster la portee **Cercle**, et
    #    « Modifier un contenu de bureau » au responsable la portee **Bureau**.
    #    Une garde unique accorderait la creation a deux roles que le document en
    #    exclut -- exactement ce que `T8` du LOT 5 a evite en refusant de
    #    reutiliser `ROLES_D_ECRITURE` pour l'archivage.
    #
    #    **ET LA GRILLE DU LOT 5 NE SE REEMPLOIE PAS DANS L'AUTRE SENS NON PLUS :**
    #    `ROLES_D_ECRITURE` contient `DSM`, que le §13 met a tiret sur ses trois
    #    lignes de modification, et ne contient PAS `OFFICE`, qui porte ici un
    #    droit reel. Les deux grilles different dans les deux sens.
    #
    # ========================================================================
    #  **LES DEUX GARDES SONT DEFINIES PLUS HAUT DESORMAIS** — voir la note au
    #  debut de `routeur_contenus`, motivee par l'ordre d'enregistrement de
    #  `/pages/{page}/gestion` face a la lecture publique ci-dessus.

    @routeur.post(
        "/entities/{code}/pages",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeCreationDePage,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role de CREATION dans cette entite. Le §13 "
                    "n'a qu'une ligne de creation — « Creer un contenu general » — et "
                    "elle ne porte ni `BOOST` ni `OFFICE` ni `DSM`. Le Booster **modifie** "
                    "le contenu de son cercle, il ne cree pas sa page, de la meme facon "
                    "que le §10.2 lui refuse « Creer un cercle »."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`slug_deja_pris` : le §15.1 veut le slug unique dans l'entite ET le "
                    "type. L'unicite est partielle sur les pages non archivees."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`type_de_page_refuse` : hors des types controles du §15.1. "
                    "`rattachement_requis` : une page `CIRCLE` exige un cercle, une page "
                    "`OFFICE` un bureau. `ressource_introuvable` : le cercle ou le bureau "
                    "nomme n'est pas dans cette entite, ou il est archive. "
                    "`slug_non_adressable` : une barre oblique rendrait la page "
                    "inatteignable par la route de lecture."
                )
            },
        },
        summary="Creer une page de contenu, en BROUILLON",
        description=(
            "Backlog `MVP-L06-US004`. **La page nait `draft`, et la demande ne porte "
            "aucun champ d'etat** : le §13 separe « Modifier » — portee Entite — de "
            "« Publier » — portee **Perimetre** — et les confondre viderait le critere "
            "« les contenus sont relus avant publication ». La publication est `US006`."
        ),
    )
    def creer_une_page_de_contenu(
        demande: DemandeDeCreationDePage,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        #  `Depends` en defaut et non dans `Annotated` : ce module porte
        #  `from __future__ import annotations`, et FastAPI resout l'annotation
        #  dans les globals du module, ou la fermeture `parametres` n'existe pas.
        #  Le piege est mesure depuis `T1` du LOT 4.
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDeCreationDePage:
        """Creer une page de contenu — matrice §13, modele §15.1."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            creee = creer_une_page(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                type_de_page=demande.type_de_page,
                titre=demande.titre,
                slug=demande.slug,
                code_de_cercle=demande.cercle,
                code_de_bureau=demande.bureau,
                instant=instant,
                motif=demande.motif,
            )

        return ReponseDeCreationDePage(
            identifiant=creee.identifiant,
            type_de_page=creee.type_de_page,
            titre=creee.titre,
            slug=creee.slug,
            etat=creee.etat,
            version=creee.version,
        )

    @routeur.put(
        "/entities/{code}/pages/{page}/contenu",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDEcritureDuContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Deux causes, deux codes. `acces_refuse` : aucun role d'ecriture "
                    "editoriale dans cette entite — `EMP`, `NEW` et **`DSM`** sont dans ce "
                    "cas, la colonne `DSM` du §13 etant a tiret sur les trois lignes de "
                    "modification. `contenu_hors_perimetre` : le role existe mais pas sur "
                    "CETTE page — un Booster sur la page d'un autre cercle, un responsable "
                    "de bureau sur une page de cercle, ou une responsabilite close ou "
                    "encore a venir."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la page a change depuis votre lecture — cahier "
                    "§18.4, « sans ecrasement silencieux ». Couvre aussi la page archivee "
                    "entre la resolution du perimetre et l'ecriture."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`type_de_bloc_refuse` : hors des onze types de `DEC-577`, et la "
                    "reponse les enumere — un auteur qui a prouve son role doit savoir "
                    "ce qu'il peut poser. Un `contenu` qui n'est pas un objet JSON est "
                    "refuse par le type lui-meme, au format du §18.3."
                )
            },
        },
        summary="Remplacer le titre et les blocs d'une page",
        description=(
            "Backlog `MVP-L06-US004`, matrice §13. **La liste remplace la liste**, et "
            "les blocs retires sont **archives**, jamais supprimes (modele §2.4). "
            "`display_order` n'est pas un champ : il vaut l'index dans la liste, si bien "
            "que deux blocs de meme rang sont impossibles a exprimer.<br><br>"
            "**Aucun HTML n'est accepte, et c'est tenu par la STRUCTURE** : le contenu "
            "d'un bloc est un objet JSON, son type est controle, et il n'existe aucun "
            "champ qui designerait une chaine comme du balisage. Un filtre textuel serait "
            "une heuristique — `<` est legitime dans « a &lt; b ».<br><br>"
            "**`state` et `published_at` ne sont jamais touches** : publier est `US006`."
        ),
    )
    def ecrire_le_contenu_d_une_page(
        demande: DemandeDEcritureDuContenu,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[
            uuid.UUID,
            Path(description="L'identifiant de la page, rendu par la creation et par la lecture"),
        ],
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDEcritureDuContenu:
        """Remplacer le contenu d'une page — matrice §13, modele §15.2."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            #  **LES PERMISSIONS SONT RESOLUES A NOUVEAU, DANS CETTE TRANSACTION.**
            #  La garde a resolu les SIENNES, dans sa propre connexion et a son
            #  propre instant : s'y fier ferait ecrire ce qui a ete autorise
            #  ailleurs. Ce n'est pas une seconde copie de la regle, c'est le meme
            #  appel au bon instant et dans le bon perimetre transactionnel.
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_editorial(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                page=page,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEditoriale.MODIFIER not in perimetre.actions:
                #  **UN SEUL GABARIT POUR QUATRE CAUSES** : la page n'existe pas,
                #  elle est d'une autre entite, elle est archivee, ou le role ne
                #  porte pas sur elle. Les distinguer apprendrait l'existence
                #  d'une page a qui n'a pas le droit de l'editer, et le §2.5 pose
                #  le refus par defaut.
                raise ErreurApplicative(
                    code=CODE_CONTENU_HORS_PERIMETRE,
                    message=MESSAGE_CONTENU_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            ecrit = remplacer_le_contenu(
                connexion,
                entite=entite.id,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                titre=demande.titre,
                blocs=tuple(
                    BlocDemande(type_de_bloc=b.type_de_bloc, contenu=b.contenu)
                    for b in demande.blocs
                ),
                instant=instant,
                motif=demande.motif,
            )

        return ReponseDEcritureDuContenu(
            version=ecrit.version,
            blocs=[
                BlocDeContenuRendu(
                    identifiant=b.identifiant,
                    type_de_bloc=b.type_de_bloc,
                    ordre=b.ordre,
                    contenu=b.contenu,
                )
                for b in ecrit.blocs
            ],
            nombre_de_blocs=len(ecrit.blocs),
            blocs_archives=ecrit.blocs_archives,
        )

    #  **LES TROIS ROUTES DU CYCLE PARTAGENT UNE SEULE GARDE, ET C'EST EXACT.**
    #  `ROLES_DE_RESTAURATION` est INCLUS dans `ROLES_D_ECRITURE_EDITORIALE` --
    #  un test le mesure -- donc cette garde laisse passer tout ayant-droit des
    #  trois actions. Ce qui separe la restauration des deux autres n'est pas le
    #  role NU mais le couple (role, page) : un Booster franchit la garde puis se
    #  voit refuser par le perimetre, exactement comme il l'est deja sur la page
    #  d'un autre cercle. Une seconde garde donnerait DEUX endroits ou lire la
    #  meme grille, et c'est ce que `DEC-466` interdit.
    garde_du_cycle = garde_d_ecriture

    def _agir(
        requete: Request,
        *,
        code: str,
        page: uuid.UUID,
        action: ActionEditoriale,
        appelant: SessionEtablie,
        motif: str | None,
        executer: Callable[[Connection, uuid.UUID, dt.datetime], _Resultat],
    ) -> _Resultat:
        """Le chemin commun des trois transitions — CSRF, entite, roles, perimetre.

        **ECRIT UNE FOIS PLUTOT QUE TROIS**, et le motif n'est pas l'economie de
        lignes : trois copies d'une meme sequence de garde divergent au premier
        changement, et la copie oubliee est celle qu'aucun test de format
        n'examine. C'est `ECART-022` et `DEC-466`, appliques a une route.

        **LES PERMISSIONS SONT RESOLUES A NOUVEAU DANS CETTE TRANSACTION.** La
        garde a resolu les SIENNES, dans sa propre connexion et a son propre
        instant : s'y fier ferait agir sur ce qui a ete autorise ailleurs.

        **LE MOTIF DU §18.1 EST VERIFIE ICI, PAS DANS CHAQUE `executer`** — LOT
        10 `T7`, `ECART-064` : les permissions sont deja resolues a cette
        ligne, le controle SUPER n'a besoin d'aucune seconde resolution.
        """
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), motif)
            perimetre = resoudre_le_perimetre_editorial(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                page=page,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if action not in perimetre.actions:
                #  **UN SEUL GABARIT POUR CINQ CAUSES** : la page n'existe pas,
                #  elle est d'une autre entite, le role ne porte pas sur elle, la
                #  transition n'est pas offerte par son etat, ou l'action n'est
                #  pas de sa portee -- le Booster qui veut restaurer. Les
                #  distinguer apprendrait l'existence et l'etat d'une page a qui
                #  n'a pas le droit d'y toucher, et le §2.5 pose le refus par
                #  defaut. C'est l'idiome de `T8` du LOT 5, ou « la cible est
                #  deja archivee » rend le meme 403 que « aucun role ».
                raise ErreurApplicative(
                    code=CODE_CONTENU_HORS_PERIMETRE,
                    message=MESSAGE_CONTENU_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            return executer(connexion, entite.id, instant)

    @routeur.post(
        "/entities/{code}/pages/{page}/publication",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDePublication,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Deux causes, deux codes. `acces_refuse` : aucun role editorial dans "
                    "cette entite. `contenu_hors_perimetre` : le role existe mais pas sur "
                    "CETTE page, **ou la page n'est pas un brouillon** — republier "
                    "ecraserait la date meme que `US006` demande d'identifier, et "
                    "l'archive se restaure avant de se publier."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la page a change depuis votre lecture (§18.4). "
                    "`borne_des_responsables` : publier la page d'un bureau exige entre "
                    "un et trois responsables **actifs** — modele §8.4, `DEC-583`. C'est "
                    "le seul geste du projet qui fasse mordre cette borne."
                )
            },
        },
        summary="Publier une page — le brouillon devient public",
        description=(
            "Backlog `MVP-L06-US006`, matrice §13 « Publier immediatement ». La page "
            "passe de `draft` a `published` et **recoit sa date de publication**, ce qui "
            "la rend servie par la lecture de `T5`.<br><br>"
            "**Il n'existe aucune depublication** : le §13 porte « Publier », « Archiver » "
            "et « Restaurer », et aucune ligne ne ramene une page publiee au brouillon. "
            "Retirer une page du public se fait en l'archivant."
        ),
    )
    def publier_une_page_de_contenu(
        demande: DemandeDeTransition,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_du_cycle),  # noqa: B008
    ) -> ReponseDePublication:
        """Publier une page — matrice §13, story `MVP-L06-US006`."""

        def executer(connexion: Connection, entite: uuid.UUID, instant: dt.datetime) -> PagePubliee:
            return publier_une_page(
                connexion,
                entite=entite,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
                motif=demande.motif,
            )

        publiee = _agir(
            requete,
            code=code,
            page=page,
            action=ActionEditoriale.PUBLIER,
            appelant=appelant,
            motif=demande.motif,
            executer=executer,
        )
        return ReponseDePublication(
            version=publiee.version, etat=publiee.etat, publiee_le=publiee.publiee_le
        )

    @routeur.post(
        "/entities/{code}/pages/{page}/archivage",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDArchivageDUnContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role editorial. `contenu_hors_perimetre` : le "
                    "role ne porte pas sur cette page, ou elle est **deja archivee**."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": "`version_obsolete` : la page a change depuis votre lecture."
            },
        },
        summary="Archiver une page — brouillon comme publiee",
        description=(
            "Backlog `MVP-L06-US006`, matrice §13 « Archiver » et §18 « Archiver un "
            "contenu dans son perimetre ». La page quitte la lecture publique.<br><br>"
            "**`archived_at` ET `state` sont ecrits dans le MEME `UPDATE`**, si bien "
            "qu'ils ne peuvent pas diverger par cette API.<br><br>"
            "**L'archivage LIBERE le slug** — l'index unique du §15.1 est partiel sur "
            "`archived_at IS NULL`. Une page neuve peut donc le reprendre, et c'est "
            "alors la RESTAURATION qui sera refusee, jamais l'archivage.<br><br>"
            "**Un motif devient obligatoire quand `SUPER` est l'acteur** (§18.1, "
            "`ECART-064`, LOT 10 `T7`) — jamais pour `ESM`/`ADM-E`/les roles locaux."
        ),
    )
    def archiver_une_page_de_contenu(
        demande: DemandeDeTransition,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_du_cycle),  # noqa: B008
    ) -> ReponseDArchivageDUnContenu:
        """Archiver une page — matrice §13 et §18."""

        def executer(
            connexion: Connection, entite: uuid.UUID, instant: dt.datetime
        ) -> PageArchivee:
            return archiver_une_page(
                connexion,
                entite=entite,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
                motif=demande.motif,
            )

        archivee = _agir(
            requete,
            code=code,
            page=page,
            action=ActionEditoriale.ARCHIVER,
            appelant=appelant,
            motif=demande.motif,
            executer=executer,
        )
        return ReponseDArchivageDUnContenu(
            version=archivee.version,
            etat=archivee.etat,
            archivee_le=archivee.archivee_le,
            publiee_le=archivee.publiee_le,
        )

    @routeur.post(
        "/entities/{code}/pages/{page}/restauration",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeRestaurationDUnContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role editorial. `contenu_hors_perimetre` : "
                    "la page n'est pas archivee, **ou l'appelant n'a qu'une portee "
                    "locale** — le §13, le §18 et le cahier §10.1 mettent tous trois "
                    "`BOOST` et `OFFICE` a tiret sur la restauration, alors qu'ils "
                    "portent l'archivage de leur propre page. La grille est asymetrique, "
                    "et c'est ecrit trois fois."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la page a change depuis votre lecture. "
                    "`slug_deja_pris` : une page vivante a repris le slug pendant "
                    "l'archivage — la restaurer le mettrait en double."
                )
            },
        },
        summary="Restaurer une page archivee — elle revient en BROUILLON",
        description=(
            "Backlog `MVP-L06-US006`, matrice §18 « Restaurer un contenu | Entite, "
            "restauration fonctionnelle », et `ARB-DROIT-003` qui nomme la condition du "
            "mot « Conditionnel » du §13.<br><br>"
            "**La page revient en `draft`, jamais en `published`** : restaurer n'est pas "
            "publier, le §13 en fait deux lignes a deux grilles, et `RIGHTS-001` refuse "
            "par defaut ce qui n'est pas explicitement accorde. Republier est un second "
            "geste, et il laisse sa trace. `QO-122` porte la question a Lea.<br><br>"
            "**`published_at` est CONSERVE** : la page a ete publiee ce jour-la, et "
            "l'effacer detruirait un fait."
        ),
    )
    def restaurer_une_page_de_contenu(
        demande: DemandeDeTransition,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_du_cycle),  # noqa: B008
    ) -> ReponseDeRestaurationDUnContenu:
        """Restaurer une page archivee — matrice §18, `ARB-DROIT-003`."""

        def executer(
            connexion: Connection, entite: uuid.UUID, instant: dt.datetime
        ) -> PageRestauree:
            return restaurer_une_page(
                connexion,
                entite=entite,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
                motif=demande.motif,
            )

        restauree = _agir(
            requete,
            code=code,
            page=page,
            action=ActionEditoriale.RESTAURER,
            appelant=appelant,
            motif=demande.motif,
            executer=executer,
        )
        return ReponseDeRestaurationDUnContenu(
            version=restauree.version, etat=restauree.etat, publiee_le=restauree.publiee_le
        )

    # ========================================================================
    #
    #  LES LIENS INTERNES — LOT 6, `T8`, `MVP-L06-US005`
    #
    #    **UNE SEULE GARDE D'ECRITURE, ET DEUX SOURCES CONCORDANTES.** Le §13
    #    « Gerer les cartes Hub/Academy/SharePoint » et le §19 « Modifier les
    #    liens internes » donnent le meme ensemble -- `ESM`, `ADM-E`, `SUPER` --
    #    et c'est la premiere grille voisine de ce lot qui concorde. Le §19 n'a
    #    ni colonne `DSM`, ni `BOOST`, ni `OFFICE` : une absence de colonne n'est
    #    pas une exclusion, et c'est le §13 qui les met a tiret.
    #
    #    **AUCUNE PORTEE LOCALE ICI, A LA DIFFERENCE DES PAGES.** Un lien
    #    appartient a l'ENTITE : `internal_link` ne porte ni `circle_id` ni
    #    `office_id`, si bien qu'un Booster n'aurait aucune ressource sur
    #    laquelle borner son droit. La garde de role suffit donc, et il n'y a
    #    rien a resoudre apres elle -- au contraire des pages, ou le couple
    #    (role, page) commande.
    #
    # ========================================================================
    garde_des_liens = exiger_un_role_dans_l_entite(parametres, ROLES_DE_GESTION_DES_LIENS)

    def _servir(liens: tuple[LienInterne, ...]) -> ReponseDesLiensInternes:
        """La meme forme pour les cinq routes — une seule structure, un seul compte."""
        return ReponseDesLiensInternes(
            liens=[
                LienInterneServi(
                    identifiant=lien.identifiant,
                    libelle=lien.libelle,
                    url=lien.url,
                    type_de_lien=lien.type_de_lien,
                    description=lien.description,
                    reference_d_icone=lien.reference_d_icone,
                    rang=lien.rang,
                    actif=lien.actif,
                    version=lien.version,
                )
                for lien in liens
            ],
            nombre_de_liens=len(liens),
        )

    @routeur.get(
        "/entities/{code}/liens",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesLiensInternes,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
        },
        summary="Les liens internes ACTIFS d'une entite",
        description=(
            "Les liens Hub, eXalt Academy, SharePoint et autres ressources internes de "
            "l'entite, dans leur ordre d'affichage — modele §15.3, `MVP-L06-US005`.<br><br>"
            "**Exige une session, et rien de plus.** La matrice §5 porte une ligne "
            "« Liens Hub/Academy/SharePoint » qui donne `—` a `ANON` et **Lecture** aux "
            "huit roles authentifies : c'est le seul tableau du document qui porte `EMP` "
            "et `NEW`, et lire a sa place la ligne « Consulter » du §13 — six colonnes, "
            "ni `EMP` ni `NEW` — refuserait la ressource a l'Employe, pour qui ce portail "
            "existe.<br><br>"
            "**Seuls les liens ACTIFS sont servis.** C'est la raison d'etre du champ "
            "`active` du §15.3. La gestion, qui voit aussi les inactifs, est une autre "
            "route et une autre grille."
        ),
    )
    def lister_les_liens_internes(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
    ) -> ReponseDesLiensInternes:
        """Les liens internes actifs d'une entite — modele §15.3, matrice §5."""
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            liens = lister_les_liens(connexion, entite=entite.id, inclure_les_inactifs=False)
        return _servir(liens)

    @routeur.get(
        "/entities/{code}/liens/gestion",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesLiensInternes,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role de gestion des liens dans cette entite. "
                    "Le §13 et le §19 s'accordent sur `ESM`, `ADM-E` et `SUPER` ; `DSM`, "
                    "`BOOST` et `OFFICE` sont a tiret au §13, et absents du tableau du §19."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
        },
        summary="Tous les liens internes, actifs ET inactifs",
        description=(
            "La meme liste que l'accueil, **plus les liens desactives** — sans quoi "
            "desactiver un lien serait un aller sans retour. Reserve aux roles qui "
            "peuvent les modifier."
        ),
    )
    def lister_les_liens_internes_pour_la_gestion(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        _appelant: SessionEtablie = Depends(garde_des_liens),  # noqa: B008
    ) -> ReponseDesLiensInternes:
        """Tous les liens internes non archives — matrice §13 et §19."""
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            liens = lister_les_liens(connexion, entite=entite.id, inclure_les_inactifs=True)
        return _servir(liens)

    @routeur.post(
        "/entities/{code}/liens",
        status_code=status.HTTP_201_CREATED,
        response_model=LienInterneServi,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": "`acces_refuse` : aucun role de gestion des liens ici."
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "Cinq refus d'URL, chacun sous son code, et ils ne sont pas "
                    "decoratifs — `DEC-587`, `QO-120`. `url_illisible` : aucun protocole. "
                    "`url_ambigue` : le protocole tape et le protocole lu different — un "
                    "caractere de controle change la lecture. `url_non_chiffree` : "
                    "exactement `http`, et il merite son propre message. "
                    "`url_protocole_refuse` : tout autre protocole, et la reponse "
                    "**enumere** ceux qui sont acceptes. `url_sans_hote` : protocole "
                    "autorise mais aucun serveur — « https:quelquechose » passerait une "
                    "liste blanche de protocoles, c'est mesure. "
                    "`type_de_lien_refuse` : hors des types du §15.3."
                )
            },
        },
        summary="Creer un lien interne, EN QUEUE de liste",
        description=(
            "Backlog `MVP-L06-US005`, matrice §13 « Gerer les cartes "
            "Hub/Academy/SharePoint » et §19 « Modifier les liens internes ».<br><br>"
            "**Aucun champ de rang** : le lien est ajoute en queue, le rang valant "
            "`max + 1` lu dans la meme transaction. Deux liens de meme rang sont donc "
            "impossibles a exprimer. Reordonner est un geste distinct, et il doit "
            "l'etre : l'index unique partiel de `T1` refuse un echange en un seul "
            "`UPDATE` — mesure du 22/09/2026.<br><br>"
            "**L'URL est validee selon la liste de protocoles autorises** du §15.3 : "
            "`https` seul. La meme regle est posee EN BASE par la migration `0019`, si "
            "bien qu'aucun autre ecrivain — reprise du prototype, modele generique, "
            "import — ne peut y echapper."
        ),
    )
    def creer_un_lien_interne(
        demande: DemandeDeCreationDeLien,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appelant: SessionEtablie = Depends(garde_des_liens),  # noqa: B008
    ) -> LienInterneServi:
        """Creer un lien interne — modele §15.3, matrice §13 et §19."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            cree = creer_un_lien(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                libelle=demande.libelle,
                url=demande.url,
                type_de_lien=demande.type_de_lien,
                description=demande.description,
                reference_d_icone=demande.reference_d_icone,
                actif=demande.actif,
                instant=instant,
                motif=demande.motif,
            )
        return _servir((cree,)).liens[0]

    #  **DECLAREE AVANT `/liens/{lien}`, ET L'ORDRE EST SIGNIFIANT.** FastAPI
    #  retient la premiere route dont le MOTIF correspond : `/liens/{lien}`
    #  attraperait `/liens/ordre`, puis rendrait 422 sur la conversion en UUID
    #  sans jamais passer la main. Un test le mesure.
    @routeur.put(
        "/entities/{code}/liens/ordre",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesLiensInternes,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": "`acces_refuse` : aucun role de gestion des liens ici."
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`ordre_incomplet` : la liste doit nommer **exactement une fois** "
                    "chacun des liens non archives de l'entite. C'est aussi ce qui tient "
                    "lieu de concurrence optimiste ici : un lien cree entre votre lecture "
                    "et votre envoi rend la liste incomplete, donc refusee."
                )
            },
        },
        summary="Reordonner les liens internes",
        description=(
            "Le rang de chaque lien vaut son **index dans la liste soumise**, si bien "
            "que deux liens de meme rang sont impossibles a exprimer.<br><br>"
            "**La reecriture se fait en deux temps, et c'est une mesure qui l'exige** : "
            "un echange de deux rangs en un seul `UPDATE` est REFUSE par "
            "`uq_internal_link_entity_ordre_non_archive`. Les rangs sont d'abord decales "
            "d'une valeur derivee, puis reposes."
        ),
    )
    def reordonner_les_liens_internes(
        demande: DemandeDOrdreDesLiens,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appelant: SessionEtablie = Depends(garde_des_liens),  # noqa: B008
    ) -> ReponseDesLiensInternes:
        """Reecrire l'ordre d'affichage des liens — modele §15.3."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            liens = reordonner_les_liens(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                ordre=tuple(demande.ordre),
                instant=instant,
                motif=demande.motif,
            )
        return _servir(liens)

    @routeur.put(
        "/entities/{code}/liens/{lien}",
        status_code=status.HTTP_200_OK,
        response_model=LienInterneServi,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": "`acces_refuse` : aucun role de gestion des liens ici."
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite inconnue ou non active, ou `lien_introuvable` : **UNE SEULE "
                    "forme pour trois causes** — le lien n'existe pas, il appartient a "
                    "une AUTRE entite, ou il est archive. Les distinguer apprendrait "
                    "l'existence d'un lien d'une entite ou l'appelant n'a rien prouve "
                    "(§2.5, refus par defaut)."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : le lien a change depuis votre lecture — §18.4, "
                    "« sans ecrasement silencieux »."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": "Les memes cinq refus d'URL qu'a la creation, plus le type."
            },
        },
        summary="Modifier un lien interne, ou le DESACTIVER",
        description=(
            "Backlog `MVP-L06-US005`, matrice §19 « Modifier les liens internes ».<br><br>"
            "**`actif = false` est le seul moyen de retirer un lien de l'accueil**, et "
            "c'est ce que le §15.3 prevoit : il declare `active` a cote de `archived_at`, "
            "et `T1` a refuse de les fondre — on desactive pour retirer de l'affichage, "
            "on archive pour sortir du jeu de donnees. **Aucune route n'archive un "
            "lien** : ni le §13 ni le §19 n'en portent la ligne.<br><br>"
            "**Le rang n'est pas touche** : il appartient a l'ordre de la liste, que "
            "`PUT …/liens/ordre` seule reecrit."
        ),
    )
    def modifier_un_lien_interne(
        demande: DemandeDeModificationDeLien,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        lien: Annotated[
            uuid.UUID, Path(description="L'identifiant du lien, rendu par la creation et la liste")
        ],
        appelant: SessionEtablie = Depends(garde_des_liens),  # noqa: B008
    ) -> LienInterneServi:
        """Remplacer la definition d'un lien interne — modele §15.3, matrice §19."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            modifie = modifier_un_lien(
                connexion,
                entite=entite.id,
                lien=lien,
                acteur=appelant.personne,
                version_attendue=demande.version,
                libelle=demande.libelle,
                url=demande.url,
                type_de_lien=demande.type_de_lien,
                description=demande.description,
                reference_d_icone=demande.reference_d_icone,
                actif=demande.actif,
                instant=instant,
                motif=demande.motif,
            )
        return _servir((modifie,)).liens[0]

    return routeur
