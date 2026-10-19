"""Ecrire un contenu editorial — cahier §10.7, modele §15, §18.4. LOT 6, `T6`.

LE TROISIEME VERBE : « ACCEPTE »

  Le corpus ecrit QUATRE fois la meme exigence, en trois verbes que le decoupage
  separe :

      stocke    `T1` -- aucune colonne ne peut porter du HTML libre
      execute   `T5` -- la reponse ne porte aucun champ de nature HTML
      accepte   **ici**

  **ET IL EST TENU PAR LA STRUCTURE, JAMAIS PAR UN FILTRE**, exactement comme les
  deux precedents. Un filtre textuel serait une heuristique, donc un defaut
  (§7.25) : `<` est legitime dans « a < b », `&` dans « R&D », et chercher
  `<script` laisserait passer `<img onerror=…`. Un garde-fou a faux positifs
  apprend a passer outre ; un a faux negatifs ment.

  Ce qui est exact est structurel : **la demande n'offre aucun champ par lequel
  un auteur puisse declarer que sa chaine est du balisage.** Le contenu d'un bloc
  est un objet JSON, son type est controle, et il n'existe ni champ `html`, ni
  `format`, ni `rendu`. Le perdre exigerait de changer le type, pas de retirer un
  appel (§7.35).

  **Consequence assumee, et il faut la dire :** du balisage ECRIT dans une valeur
  de texte est **conserve tel quel**, et `T5` le ressert tel quel. Ce n'est pas
  une faille -- c'est la preuve que cette API stocke des DONNEES. Le retirer en
  silence serait pire : un contenu mange sans que personne le sache, et un
  controle qui ne pourrait pas distinguer « filtre » de « rien a filtrer ».

CE QUI EST REELLEMENT REFUSE, PARCE QUE C'EST EXACT

  1. **un `block_type` hors des onze de `DEC-577`** -- c'est « les blocs
     autorises sont valides » du critere de `US004`. La contrainte de
     verification de `T1` le refuserait aussi, mais en `IntegrityError`, donc en
     500 : un auteur a besoin d'un 422 qui nomme le bloc fautif ;
  2. **un contenu qui n'est pas un objet JSON.** `T5` refuse deja cela en
     LECTURE, en 500, parce qu'un tel bloc est alors un defaut de donnee. Le
     refuser ICI, en 422, est ce qui garantit que ce 500 ne survienne jamais pour
     une donnee ecrite par l'API.

CE QUE CE MODULE NE TOUCHE JAMAIS : `state` ET `published_at`

  Le §13 separe « Modifier » -- portee **Entite** pour l'ESM -- de « Publier » et
  « Archiver » -- portee **Perimetre**. Deux mots differents, donc deux droits.
  Une ecriture qui passerait une page en `published` confondrait les deux, et
  viderait le critere de sortie n°1 du lot : « les contenus sont relus **avant**
  publication ». C'est `US006`, sous-etape `T7`.

  **Une page naissante est donc toujours `draft`**, et la demande de creation ne
  porte aucun champ d'etat : la valeur n'est pas « ignoree », elle n'existe pas.

LES BLOCS RETIRES SONT ARCHIVES, JAMAIS SUPPRIMES

  §2.4 du modele : « Les ressources metier sont archivees par `archived_at` et
  `archived_by`. La suppression physique est reservee aux donnees temporaires,
  aux purges RGPD, et aux operations explicitement autorisees au
  super-administrateur. » Un bloc retire d'une page n'est aucun des trois.

  **Et cela n'exige AUCUN motif.** Le §18.1 enumere les cinq actions qui en
  demandent un -- purge definitive, revocation d'un acces actif, changement
  sensible de role, rollback d'import, intervention du super-administrateur dans
  une entite -- et retirer un bloc n'y est pas. En exiger un serait une invention
  (§6.5) ; le supposer inutile sans lire le §18.1 aurait ete une negligence.

  **Ce n'est PAS « archiver un contenu » au sens du §13 et du §18**, qui vise la
  PAGE prise comme ressource -- celle qui disparait de la lecture. Retirer un
  bloc au cours d'une edition est le mecanisme meme de « Modifier un contenu ».
  La distinction est reelle : cette route n'ecrit jamais `content_page.archived_at`.

L'ORDRE D'AFFICHAGE EST L'ORDRE DU TABLEAU, ET C'EST STRUCTUREL

  `display_order` n'est PAS un champ de la demande : il vaut l'index du bloc dans
  la liste envoyee. Deux blocs de meme rang deviennent donc **impossibles a
  exprimer**, la ou un champ libre les aurait laisses passer jusqu'a l'index
  unique de `T1` -- qui aurait rendu un 500. §7.35 : la propriete est tenue par
  la structure, la perdre exigerait de changer la signature.

LA CONCURRENCE OPTIMISTE EST ANCREE SUR `content_page.version`

  §18.4, litteralement : « les modifications sensibles utilisent une concurrence
  optimiste. Une version obsolete produit une reponse HTTP 409 **sans ecrasement
  silencieux** ». La page est la racine de l'agregat, et les blocs n'ont pas de
  version propre qui aurait un sens : deux editeurs qui remplacent la liste
  entiere doivent entrer en conflit, meme s'ils touchent des blocs differents.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.audit.services import enregistrer_un_evenement
from app.content.modeles import TYPES_DE_BLOC, TYPES_DE_PAGE, EtatDePage, TypeDePage
from app.content.perimetre import ActionEditoriale
from app.shared.errors import ErreurApplicative

CODE_TYPE_DE_BLOC_REFUSE: Final = "type_de_bloc_refuse"
MESSAGE_TYPE_DE_BLOC_REFUSE: Final = (
    "Ce type de bloc n'est pas autorise. Les blocs autorises sont ceux du cahier §10.7 "
    "et du modele §15.2."
)

CODE_VERSION_OBSOLETE: Final = "version_obsolete"
MESSAGE_VERSION_OBSOLETE: Final = (
    "Ce contenu a change depuis votre lecture. Rechargez-le avant de le modifier."
)

CODE_SLUG_DEJA_PRIS: Final = "slug_deja_pris"
MESSAGE_SLUG_DEJA_PRIS: Final = (
    "Une page de ce type porte deja ce slug dans cette entite. Le §15.1 les veut uniques."
)

CODE_RATTACHEMENT_REQUIS: Final = "rattachement_requis"
MESSAGE_RATTACHEMENT_REQUIS: Final = (
    "Ce type de page exige la ressource a laquelle il se rattache — modele §15.1."
)

CODE_RESSOURCE_INTROUVABLE: Final = "ressource_introuvable"
MESSAGE_RESSOURCE_INTROUVABLE: Final = (
    "Le cercle ou le bureau nomme n'existe pas dans cette entite, ou il est archive."
)

CODE_SLUG_NON_ADRESSABLE: Final = "slug_non_adressable"
MESSAGE_SLUG_NON_ADRESSABLE: Final = (
    "Un slug ne peut pas contenir de barre oblique : il est adresse comme un segment de chemin."
)

CODE_TYPE_DE_PAGE_REFUSE: Final = "type_de_page_refuse"
MESSAGE_TYPE_DE_PAGE_REFUSE: Final = (
    "Ce type de page n'est pas autorise. Les types controles sont ceux du modele §15.1."
)

#  **LE SEUL CARACTERE REFUSE, ET IL EST DERIVE DE L'ADRESSAGE, PAS D'UN FORMAT.**
#
#  Le corpus ne donne AUCUN format de slug -- ni casse, ni jeu de caracteres,
#  zero occurrence dans les cinq documents de cadrage -- et en inventer un serait
#  le §6.5. Mais `T5` adresse une page par `…/pages/{type_de_page}/{slug}`, et un
#  parametre de chemin FastAPI ne capture pas la barre oblique : une page dont le
#  slug en contiendrait serait creee et **rien ne pourrait jamais la servir**.
#
#  Le refus ne decrit donc pas une convention d'ecriture, il refuse un slug qui
#  rendrait la page inatteignable. Un test le MESURE plutot que de l'affirmer.
CARACTERE_NON_ADRESSABLE: Final = "/"

#  **L'ETAT DE NAISSANCE EST DERIVE DE L'ENUMERATION** (`DEC-544`, meme parti que
#  `ETAT_RENDU` de `T5`) : si le §15.1 renommait ses etats, cette constante
#  resterait juste ou echouerait bruyamment, jamais silencieusement fausse.
ETAT_A_LA_CREATION: Final[str] = EtatDePage.DRAFT.value

#  Les types de page qui EXIGENT un rattachement, et la colonne qui le porte.
#  **Derives du modele §15.1** -- « `circle_id` | Requis pour une page de cercle »,
#  « `office_id` | Requis pour une page de bureau » -- et ce sont les memes deux
#  contraintes de verification que `T1` a posees. Les nommer ici permet de rendre
#  un 422 lisible la ou la base rendrait un 500.
RATTACHEMENTS_REQUIS: Final[dict[str, str]] = {
    TypeDePage.CIRCLE.value: "circle_id",
    TypeDePage.OFFICE.value: "office_id",
}


@dataclasses.dataclass(frozen=True, slots=True)
class BlocDemande:
    """Un bloc tel que l'auteur le soumet.

    **AUCUN `display_order`**, et c'est le point : il vaut l'index dans la liste.
    **AUCUN identifiant** non plus -- la liste remplace la liste, et prendre un
    identifiant laisserait croire a une mise a jour bloc par bloc que ce module
    ne fait pas.
    """

    type_de_bloc: str
    contenu: dict[str, object]


@dataclasses.dataclass(frozen=True, slots=True)
class BlocEcrit:
    """Un bloc tel qu'il vient d'etre ecrit."""

    identifiant: uuid.UUID
    type_de_bloc: str
    ordre: int
    contenu: dict[str, object]


@dataclasses.dataclass(frozen=True, slots=True)
class PageCreee:
    """Une page neuve, toujours en BROUILLON."""

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    etat: str
    version: int


@dataclasses.dataclass(frozen=True, slots=True)
class ContenuEcrit:
    """Ce que le remplacement a produit.

    `blocs_archives` est rapporte plutot que tu : un auteur qui envoie deux blocs
    la ou la page en portait cinq doit voir que trois ont quitte l'affichage.
    """

    version: int
    blocs: tuple[BlocEcrit, ...]
    blocs_archives: int


_INSERER_LA_PAGE: Final = text(
    """
    INSERT INTO content_page
      (entity_id, page_type, circle_id, office_id, title, slug, state,
       created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :type_de_page, :cercle, :bureau, :titre, :slug, :etat,
       :acteur, :acteur, :instant, :instant)
    RETURNING id, version
    """
)

#  **LA VERSION EST LUE `FOR UPDATE`.** Sans le verrou, deux remplacements
#  concurrents liraient la meme version, la trouveraient tous deux a jour, et le
#  second ecraserait le premier -- exactement ce que le §18.4 appelle un
#  « ecrasement silencieux ». C'est la lecture qui doit verrouiller, pas
#  l'ecriture : au moment ou l'on ecrit, le mal est fait.
_ETAT_DE_LA_PAGE: Final = text(
    """
    SELECT version, title
      FROM content_page
     WHERE id = :page AND entity_id = :entite AND archived_at IS NULL
       FOR UPDATE
    """
)

#  §2.4 : les blocs retires sont ARCHIVES. L'index unique de `T1` etant partiel
#  sur `archived_at IS NULL`, cet `UPDATE` libere les rangs pour l'insertion qui
#  suit, dans la MEME transaction.
_ARCHIVER_LES_BLOCS: Final = text(
    """
    UPDATE content_block
       SET archived_at = :instant,
           archived_by_person_id = :acteur,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE content_page_id = :page AND entity_id = :entite AND archived_at IS NULL
    """
)

_INSERER_UN_BLOC: Final = text(
    """
    INSERT INTO content_block
      (entity_id, content_page_id, block_type, display_order, payload_json,
       created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :page, :type_de_bloc, :ordre, CAST(:charge AS jsonb),
       :acteur, :acteur, :instant, :instant)
    RETURNING id
    """
)

#  **`state` ET `published_at` SONT ABSENTS DE CET `UPDATE`, ET C'EST LE POINT.**
#  Les y ajouter confondrait « Modifier » et « Publier », que le §13 separe par
#  deux portees differentes.
_METTRE_A_JOUR_LA_PAGE: Final = text(
    """
    UPDATE content_page
       SET title = :titre,
           updated_at = :instant,
           updated_by_person_id = :acteur,
           version = version + 1
     WHERE id = :page AND entity_id = :entite
    RETURNING version
    """
)

#  La ressource nommee existe-t-elle, NON ARCHIVEE, dans CETTE entite ? Le couple
#  `(id, entity_id)` porte l'isolation (§25.3) ; resoudre par le code seul
#  rattacherait une page au cercle d'une autre entite, ce que la cle composite
#  refuserait ensuite en 500.
_CERCLE_PAR_CODE: Final = text(
    "SELECT id FROM circle WHERE entity_id = :entite AND code = :code AND archived_at IS NULL"
)
_BUREAU_PAR_CODE: Final = text(
    "SELECT id FROM office WHERE entity_id = :entite AND code = :code AND archived_at IS NULL"
)


def _valider_les_types_de_bloc(blocs: tuple[BlocDemande, ...]) -> None:
    """Refuser un type hors des onze de `DEC-577` — critere « les blocs autorises sont valides ».

    **LE PERIMETRE EST DERIVE DE L'ENUMERATION** (§7.27) : un douzieme type y
    entrerait sans que personne y pense, et un type retire en sortirait de meme.
    """
    for rang, bloc in enumerate(blocs):
        if bloc.type_de_bloc not in TYPES_DE_BLOC:
            raise ErreurApplicative(
                code=CODE_TYPE_DE_BLOC_REFUSE,
                message=MESSAGE_TYPE_DE_BLOC_REFUSE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ=f"blocs[{rang}].type_de_bloc",
                #  **LES TYPES AUTORISES SORTENT, ET CE N'EST PAS UNE FUITE.**
                #  Le §15.2 les enumere dans un document de cadrage, et un auteur
                #  qui a prouve un role d'ecriture doit savoir ce qu'il peut
                #  poser : les lui cacher rendrait l'ecran de `T10` impossible a
                #  ecrire sans deviner.
                details={"types_autorises": list(TYPES_DE_BLOC)},
            )


def resoudre_le_rattachement(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    type_de_page: str,
    code_de_cercle: str | None,
    code_de_bureau: str | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Resoudre le cercle et le bureau nommes par leur CODE, dans cette entite.

    **PAR CODE ET NON PAR IDENTIFIANT**, parce que c'est ainsi que tout le reste
    de l'API adresse un cercle et un bureau depuis `T3` et `T4` --
    `…/circles/{code_cercle}`. Deux modes d'adressage pour une meme ressource
    divergeraient, et l'un des deux serait celui qu'aucun ecran n'emploie.

    **AUCUNE INTERDICTION CROISEE**, et c'est delibere : le §15.1 ecrit « requis
    pour une page de cercle », jamais « interdit ailleurs » -- au contraire du
    §8.4, qui dit en toutes lettres que `BOOSTER` « interdit `office_id` ». `T1`
    a pose les deux contraintes sous cette forme d'IMPLICATION seule, et en
    ajouter une ici donnerait a l'API une regle que le schema ne porte pas.
    """
    cercle: uuid.UUID | None = None
    bureau: uuid.UUID | None = None

    if code_de_cercle is not None:
        cercle = connexion.execute(
            _CERCLE_PAR_CODE, {"entite": entite, "code": code_de_cercle}
        ).scalar_one_or_none()
        if cercle is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_RESSOURCE_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="cercle",
            )

    if code_de_bureau is not None:
        bureau = connexion.execute(
            _BUREAU_PAR_CODE, {"entite": entite, "code": code_de_bureau}
        ).scalar_one_or_none()
        if bureau is None:
            raise ErreurApplicative(
                code=CODE_RESSOURCE_INTROUVABLE,
                message=MESSAGE_RESSOURCE_INTROUVABLE,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="bureau",
            )

    colonne = RATTACHEMENTS_REQUIS.get(type_de_page)
    if colonne is not None:
        #  La contrainte de verification de `T1` refuserait aussi ce cas, mais en
        #  `IntegrityError`, donc en 500. Un auteur a droit a un 422 qui nomme le
        #  champ manquant.
        manquant = cercle is None if colonne == "circle_id" else bureau is None
        if manquant:
            raise ErreurApplicative(
                code=CODE_RATTACHEMENT_REQUIS,
                message=MESSAGE_RATTACHEMENT_REQUIS,
                statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                champ="cercle" if colonne == "circle_id" else "bureau",
            )

    return cercle, bureau


def creer_une_page(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    type_de_page: str,
    titre: str,
    slug: str,
    code_de_cercle: str | None,
    code_de_bureau: str | None,
    instant: dt.datetime,
    motif: str | None = None,
) -> PageCreee:
    """Creer une page en BROUILLON — §13 « Creer un contenu general ».

    L'appelant a deja prouve `ROLES_DE_CREATION` : ce module ne rejuge pas les
    roles, il ecrit. Le §13 donne cette ligne a `ESM`, `ADM-E` et `SUPER` seuls.
    """
    #  **LE TYPE EST VALIDE ICI, PAS LAISSE A LA CONTRAINTE.** `page_type_valide`
    #  refuserait aussi, en `IntegrityError`, donc en 500 -- et un 500 sur une
    #  faute de l'appelant l'accuserait d'un defaut du service. Meme motif et
    #  meme perimetre DERIVE que pour les types de bloc (§7.27).
    if type_de_page not in TYPES_DE_PAGE:
        raise ErreurApplicative(
            code=CODE_TYPE_DE_PAGE_REFUSE,
            message=MESSAGE_TYPE_DE_PAGE_REFUSE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="type_de_page",
            details={"types_autorises": list(TYPES_DE_PAGE)},
        )

    if CARACTERE_NON_ADRESSABLE in slug:
        raise ErreurApplicative(
            code=CODE_SLUG_NON_ADRESSABLE,
            message=MESSAGE_SLUG_NON_ADRESSABLE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="slug",
        )

    cercle, bureau = resoudre_le_rattachement(
        connexion,
        entite=entite,
        type_de_page=type_de_page,
        code_de_cercle=code_de_cercle,
        code_de_bureau=code_de_bureau,
    )

    try:
        ligne = connexion.execute(
            _INSERER_LA_PAGE,
            {
                "entite": entite,
                "type_de_page": type_de_page,
                "cercle": cercle,
                "bureau": bureau,
                #  Un parametre PAR COLONNE, et ce n'est pas une coquetterie :
                #  `title` est `text` et `slug` est `varchar(160)`. Un parametre
                #  lie partage par deux colonnes de types differents rend
                #  « inconsistent types deduced for parameter $1 », et le message
                #  ne nomme ni la table ni la colonne. Quatre occurrences, et
                #  `make parametres-check` le refuse depuis `DEC-580`.
                "titre": titre,
                "slug": slug,
                "etat": ETAT_A_LA_CREATION,
                "acteur": acteur,
                "instant": instant,
            },
        ).one()
    except IntegrityError as erreur:
        raise _traduire_un_refus_de_la_base(erreur) from erreur

    #  LOT 10, `T4` : `ActionEditoriale.CREER` est deja le vocabulaire du
    #  perimetre (§7.27), reutilise tel quel comme `action_code`.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEditoriale.CREER.value,
        resource_type="content_page",
        resource_reference=ligne[0],
        entity_id=entite,
        actor_person_id=acteur,
        summary=f"Creation de la page « {titre} » ({type_de_page})",
        reason=motif,
    )

    return PageCreee(
        identifiant=ligne[0],
        type_de_page=type_de_page,
        titre=titre,
        slug=slug,
        etat=ETAT_A_LA_CREATION,
        version=int(ligne[1]),
    )


def remplacer_le_contenu(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    page: uuid.UUID,
    acteur: uuid.UUID,
    version_attendue: int,
    titre: str,
    blocs: tuple[BlocDemande, ...],
    instant: dt.datetime,
    motif: str | None = None,
) -> ContenuEcrit:
    """Remplacer le titre et les blocs d'une page — §13 « Modifier un contenu de … ».

    L'appelant a deja resolu `PerimetreEditorial` : ce module ne rejuge pas les
    roles. Il refuse en revanche ce qu'aucune grille de role ne couvre -- une
    version obsolete, un type de bloc hors liste -- parce qu'il est appelable
    hors HTTP et qu'une fonction qui accepterait un douzieme type rendrait le
    controle du §15.2 dependant de son appelant (corollaire du §7.37).

    **UNE LISTE VIDE EST LEGITIME** : une page peut n'avoir aucun bloc, `T5` le
    dit et rend un tuple vide. Refuser le vide obligerait a passer par une
    suppression de page pour vider un contenu.
    """
    _valider_les_types_de_bloc(blocs)

    etat = connexion.execute(_ETAT_DE_LA_PAGE, {"page": page, "entite": entite}).one_or_none()
    if etat is None:
        #  La page a ete archivee entre la resolution du perimetre et ici. Le
        #  perimetre l'aurait deja refusee ; ce garde-fou existe parce que les
        #  deux lectures sont deux instants, et qu'un `UPDATE` sur zero ligne
        #  rendrait un succes vide -- §7.0, quatrieme proposition.
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
        )

    if int(etat[0]) != version_attendue:
        raise ErreurApplicative(
            code=CODE_VERSION_OBSOLETE,
            message=MESSAGE_VERSION_OBSOLETE,
            statut=status.HTTP_409_CONFLICT,
            details={"version_actuelle": int(etat[0])},
        )

    archives = connexion.execute(
        _ARCHIVER_LES_BLOCS, {"page": page, "entite": entite, "acteur": acteur, "instant": instant}
    ).rowcount

    ecrits: list[BlocEcrit] = []
    try:
        for rang, bloc in enumerate(blocs):
            identifiant = connexion.execute(
                _INSERER_UN_BLOC,
                {
                    "entite": entite,
                    "page": page,
                    "type_de_bloc": bloc.type_de_bloc,
                    "ordre": rang,
                    #  **`json.dumps` PUIS `CAST(… AS jsonb)`, ET NON L'OBJET
                    #  DIRECTEMENT.** Le pilote adapterait un `dict` en `jsonb`,
                    #  mais le parametre est alors d'un type que le serveur doit
                    #  deduire ; le passer en `text` puis le convertir rend le
                    #  type explicite et le message d'erreur lisible.
                    "charge": json.dumps(bloc.contenu),
                    "acteur": acteur,
                    "instant": instant,
                },
            ).scalar_one()
            ecrits.append(
                BlocEcrit(
                    identifiant=identifiant,
                    type_de_bloc=bloc.type_de_bloc,
                    ordre=rang,
                    contenu=bloc.contenu,
                )
            )
    except (IntegrityError, DataError) as erreur:
        raise _traduire_un_refus_de_la_base(erreur) from erreur

    ancien_titre = str(etat[1])
    version = int(
        connexion.execute(
            _METTRE_A_JOUR_LA_PAGE,
            {
                "page": page,
                "entite": entite,
                "titre": titre,
                "acteur": acteur,
                "instant": instant,
            },
        ).scalar_one()
    )

    #  LOT 10, `T4` : UN SEUL `audit_event` pour l'appel entier -- « remplacer
    #  le titre et les blocs d'une page » est UNE action metier, meme si elle
    #  ecrit trois choses en SQL (archivage des anciens blocs, insertion des
    #  nouveaux, mise a jour du titre). Aucune enum ne nomme cette action a la
    #  granularite du champ (a la difference de `T3`, LOT 2) : `MODIFIER` du
    #  perimetre editorial est deja le bon niveau.
    enregistrer_un_evenement(
        connexion,
        instant=instant,
        action_code=ActionEditoriale.MODIFIER.value,
        resource_type="content_page",
        resource_reference=page,
        entity_id=entite,
        actor_person_id=acteur,
        summary=(
            f"Remplacement du contenu de la page ({len(ecrits)} bloc(s), {archives} archive(s))"
        ),
        old_values={"titre": ancien_titre},
        new_values={"titre": titre},
        reason=motif,
    )

    return ContenuEcrit(
        version=version, blocs=tuple(ecrits), blocs_archives=int(archives if archives > 0 else 0)
    )


def _traduire_un_refus_de_la_base(erreur: IntegrityError | DataError) -> ErreurApplicative:
    """Traduire un refus du schema en reponse du §18.3.

    **LE DISCRIMINANT EST LE NOM DE LA CONTRAINTE, ET C'EST PLUS EXACT QUE LE
    TYPE D'EXCEPTION.** `T7` du LOT 5 discriminait sur le type psycopg, ce qui
    suffisait la : ses cinq refus possibles etaient d'especes differentes. Ici
    **deux `UniqueViolation` distinctes existent** -- le slug de `content_page`,
    et le rang d'un bloc -- et seul le nom les separe. Un controle exact vaut
    mieux qu'un controle large (§7.25).

    Le nom vient de `diag.constraint_name`, une donnee **structuree** du
    protocole PostgreSQL : ce n'est pas le texte du message, qui est localise et
    change de version en version.

    **CE QUI N'EST PAS RECONNU REMONTE**, et c'est voulu : le rang d'un bloc
    etant derive de l'index de la liste, une violation de
    `uq_content_block_page_ordre_non_archive` signalerait un defaut de CE module,
    pas une faute de l'appelant. Un 500 bruyant vaut mieux qu'un 422 qui
    l'accuserait a tort (§7.20).
    """
    cause = erreur.orig
    diagnostic = getattr(cause, "diag", None)
    contrainte = str(getattr(diagnostic, "constraint_name", "") or "")

    if contrainte == "uq_content_page_entity_type_slug_non_archive":
        return ErreurApplicative(
            code=CODE_SLUG_DEJA_PRIS,
            message=MESSAGE_SLUG_DEJA_PRIS,
            statut=status.HTTP_409_CONFLICT,
            champ="slug",
        )
    raise erreur
