"""La route du trombinoscope — story `MVP-L05-US001`.

LOT 5, sous-etape `T2`.

La derivation complete -- qui peut lire, quels etats sont exclus, pourquoi les
deux filtres sont necessaires, d'ou vient l'ordre -- est dans l'en-tete de
`app/people/trombinoscope.py`. Ce module ne porte que ce qui releve de HTTP.

LE 404 EST CELUI DES DEUX AUTRES ROUTES D'ENTITE, EN CORPS ET EN EN-TETES

  Un code inconnu et une entite non active rendent la **meme** reponse que
  `/entities/{code}` et `/entities/{code}/permissions`. Deux routes qui
  distingueraient differemment apprendraient, par comparaison, qu'un brouillon
  existe -- et le LOT 9 en creera avant publication.

  Le gabarit n'est pas recopie : il est **importe** de `app.entities.routes`.

LE REFUS D'UNE TAILLE HORS LISTE EST UN 422 QUE JE N'ECRIS PAS

  `taille` est typee `TailleDePage`, un `Literal` des trois valeurs du §18.2.
  FastAPI refuse donc toute autre valeur avant d'entrer dans le corps, et
  `gerer_erreur_validation` traduit le refus au format du §18.3 -- `code`,
  `message`, `champ`, `details` et identifiant de correlation. Ecrire ici un
  `ErreurApplicative` de plus donnerait **deux** formes de refus pour une meme
  cause, et la seconde serait celle qu'aucun test de format n'examine.

  **Le service verifie POURTANT la meme chose, et ce n'est pas une redondance :**
  il est appelable hors HTTP -- par un futur export, par un script -- et une
  fonction qui accepte silencieusement une taille de 10 000 rendrait la borne du
  cahier dependante de son appelant.

`page` EST 1-INDEXEE, ET C'EST LE NUMERO QUE L'ECRAN AFFICHE

  Une page 0 n'a pas de sens pour un lecteur. `ge=1` fait refuser `page=0` par le
  meme 422, et la conversion en decalage est faite une seule fois, dans le
  service.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.media.objets import ObjetIntrouvable, lire_l_objet
from app.media.photo import resoudre_la_miniature
from app.people.modeles import SituationProfessionnelle
from app.people.profil import CercleDuProfil, FicheProfil, ResponsabiliteDuProfil, lire_la_fiche
from app.people.trombinoscope import (
    LONGUEUR_MAXIMALE_RECHERCHE,
    TAILLE_PAR_DEFAUT,
    Filtres,
    TailleDePage,
    lister_le_trombinoscope,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

#  **LE GABARIT DU CHEMIN DE PHOTO, EN UNE SEULE SOURCE.** La route le declare,
#  les deux reponses l'emploient : deux copies divergeraient au premier
#  renommage, et la liste emettrait alors un chemin qui rend 404.
journal = logging.getLogger("app.people")

GABARIT_PHOTO: Final = "/entities/{code}/people/{appartenance}/photo"


def chemin_de_la_photo(prefixe: str, code: str, appartenance: uuid.UUID) -> str:
    """Le chemin complet de la miniature, prefixe versionne compris."""
    return prefixe + GABARIT_PHOTO.format(code=code, appartenance=appartenance)


if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres


class CollaborateurDuTrombinoscope(BaseModel):
    """Une ligne du trombinoscope.

    Huit champs depuis `T5`, qui a ajoute la **photo**. Les informations
    professionnelles ne sont toujours pas jointes : le motif est dans l'en-tete de
    `trombinoscope.py`, section « ce que `T3` ne fait toujours pas ».

    Les noms sont en `snake_case`, comme `est_entite_principale` de `T8` du
    LOT 4 : c'est le contrat de `packages/contracts` qui traduit vers le
    `camelCase` du frontend, et sa garde **leve** si un champ manque.
    """

    id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    professional_category: str
    arrival_date: dt.date
    #  **LE CHEMIN DE LA MINIATURE, OU `None` POUR L'AVATAR NEUTRE.**
    #
    #  Un chemin et non un booleen : le frontend l'emploie tel quel. Et le chemin
    #  d'une ROUTE, non l'`object_key` de la variante -- exposer la cle
    #  divulguerait la disposition du stockage, et le navigateur n'en pourrait
    #  rien faire.
    #
    #  `None` couvre CINQ causes -- pas d'autorisation, retiree, pas encore
    #  active, media non `ready`, aucune variante -- et c'est voulu : distinguer
    #  « il a une photo mais tu n'y as pas droit » de « il n'a pas de photo »
    #  apprendrait ce que le §21.2 ne veut pas dire.
    photo: str | None


class CercleDeLaFiche(BaseModel):
    """Un cercle, principal ou secondaire — §10.2."""

    code: str
    nom: str
    jeton_de_couleur: str


class ResponsabiliteDeLaFiche(BaseModel):
    """Une responsabilite Framework et sa portee — §8.4.

    `cercle` et `bureau` s'excluent : le §8.4 l'impose par contrainte, et le type
    dit lequel des deux est renseigne.
    """

    type: str
    cercle: str | None
    bureau: str | None


class FicheDuProfil(BaseModel):
    """Les champs du §10.2, ET la photo depuis `T5` -- un CHEMIN, jamais des octets.

    **AUCUN CHAMP N'EST MASQUE**, et ce n'est pas un oubli : la matrice ne definit
    aucune visibilite par champ. Le motif complet est dans l'en-tete de
    `app/people/profil.py`, et un test fige l'absence pour qu'un lot ulterieur
    doive la decider. `ECART-051`.
    """

    id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    professional_category: str
    arrival_date: dt.date
    short_bio: str | None
    fun_fact: str | None
    metier: str | None
    statut: str | None
    client: str | None
    dsm: str | None
    cercle_principal: CercleDeLaFiche | None
    cercles_secondaires: list[CercleDeLaFiche]
    responsabilites: list[ResponsabiliteDeLaFiche]
    #  Meme regle que dans la liste : le chemin de la miniature, ou `None`.
    photo: str | None


class ReponseDuTrombinoscope(BaseModel):
    """Une page du trombinoscope, et de quoi savoir ou l'on est.

    `total` porte la population entiere, `pages` le nombre de pages. Le §10.1
    exige une « vue paginee » : sans ces deux nombres, l'ecran ne peut ni dire
    « page 2 sur 6 » ni desactiver le bouton suivant. `pages` est calcule **une
    seule fois, ici** -- le laisser au client dupliquerait la regle dans chaque
    consommateur.
    """

    collaborateurs: list[CollaborateurDuTrombinoscope]
    page: int
    taille: int
    total: int
    pages: int


def routeur_trombinoscope(parametres: Parametres) -> APIRouter:
    """Routeur du trombinoscope, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["trombinoscope"])

    #  La dependance passe par `dependencies=`, jamais par `Annotated[...]` : le
    #  piege est mesure dans `app/entities/routes.py`, et il produit un livrable
    #  qui PARAIT protege tout en refusant tout le monde avec un 422.
    @routeur.get(
        "/entities/{code}/people",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuTrombinoscope,
        responses={
            status.HTTP_401_UNAUTHORIZED: {
                "description": (
                    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie "
                    "absent, jeton inconnu, session revoquee, duree absolue depassee, "
                    "inactivite depassee."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour DEUX causes : le code est inconnu, ou "
                    "l'entite existe sans etre active. Identique en corps ET en "
                    "en-tetes a celle de `/entities/{code}`."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, ou `page` "
                    "inferieure a 1. Format du §18.3, produit par le gestionnaire "
                    "de validation et non par cette route."
                )
            },
        },
        summary="Lister les collaborateurs publies et actifs d'une entite",
        description=(
            "Le trombinoscope d'une entite, pagine. Cahier §18.2 : 25 par defaut, "
            "options 25, 50 et 100. Toute autre taille est refusee — arbitrage du "
            "25/08/2026. Exige une session : la matrice §5 refuse cette ressource a "
            "`ANON` et l'accorde aux huit roles authentifies, sans distinction, si "
            "bien qu'aucun role n'est examine ici. "
            "Seuls les profils `published` d'une appartenance `active` sont rendus : "
            "les deux filtres sont necessaires, et le motif mesure est dans le module "
            "de service. L'ordre est nom puis prenom, total par la cle primaire."
        ),
    )
    def lister_les_collaborateurs(
        #  `Path` et `Query` en defaut sont les fabriques de FastAPI, que ruff
        #  connait : `B008` ne s'y declenche pas, et un `noqa` inutile ferait
        #  echouer `RUF100`.
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite, unique et jamais reattribue",
        ),
        page: int = Query(
            1,
            ge=1,
            description="Numero de page, 1-indexee comme celui que l'ecran affiche",
        ),
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
        recherche: Annotated[
            str | None,
            Query(
                max_length=LONGUEUR_MAXIMALE_RECHERCHE,
                description="Cherche dans le prenom ET le nom, accents ignores",
            ),
        ] = None,
        cercle: Annotated[uuid.UUID | None, Query(description="Identifiant d'un cercle")] = None,
        dsm: Annotated[
            uuid.UUID | None, Query(description="Identifiant de la personne DSM")
        ] = None,
        metier: Annotated[
            uuid.UUID | None, Query(description="Identifiant d'un metier du catalogue")
        ] = None,
        client: Annotated[uuid.UUID | None, Query(description="Identifiant d'un client")] = None,
        statut: Annotated[
            SituationProfessionnelle | None,
            Query(description="`mission` ou `intercontract` — cahier §9.3"),
        ] = None,
    ) -> ReponseDuTrombinoscope:
        """Lister le trombinoscope — cahier §10.1 et §18.2, backlog `MVP-L05-US001`."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                #  Le motif precis ne sort pas : deux causes, une seule reponse.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  La resolution et la page sont dans la MEME transaction : une entite
            #  suspendue entre les deux rendrait un trombinoscope d'entite
            #  inaccessible.
            #  `int(taille)` : `TailleDePage` est un `IntEnum`, et le service est
            #  HTTP-agnostique -- il recoit un entier, pas un type de la couche
            #  web. C'est aussi ce que le pilote attend en parametre lie.
            resultat = lister_le_trombinoscope(
                connexion,
                entite=entite.id,
                page=page,
                taille=int(taille),
                #  L'instant est pris UNE fois, ici, et passe au service : les
                #  cinq filtres portent sur des relations historisees, et deux
                #  appels a `now()` dans la meme requete pourraient differer.
                instant=dt.datetime.now(tz=dt.UTC),
                filtres=Filtres(
                    recherche=recherche,
                    cercle=cercle,
                    dsm=dsm,
                    metier=metier,
                    client=client,
                    statut=None if statut is None else statut.value,
                ),
            )

        #  Division entiere par excedent, sans `math.ceil` : une division
        #  flottante sur un total de plusieurs millions perdrait en precision.
        pages = -(-resultat.total // int(taille))

        return ReponseDuTrombinoscope(
            collaborateurs=[
                CollaborateurDuTrombinoscope(
                    id=ligne.id,
                    person_id=ligne.person_id,
                    first_name=ligne.first_name,
                    last_name=ligne.last_name,
                    preferred_name=ligne.preferred_name,
                    professional_category=ligne.professional_category,
                    arrival_date=ligne.arrival_date,
                    photo=(
                        chemin_de_la_photo(parametres.API_PREFIX, code, ligne.id)
                        if ligne.a_une_photo
                        else None
                    ),
                )
                for ligne in resultat.collaborateurs
            ],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    @routeur.get(
        "/entities/{code}/people/{appartenance}",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=FicheDuProfil,
        responses={
            status.HTTP_401_UNAUTHORIZED: {
                "description": (
                    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie "
                    "absent, jeton inconnu, session revoquee, duree absolue depassee, "
                    "inactivite depassee."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour QUATRE causes : le code d'entite est inconnu, "
                    "l'entite n'est pas active, l'appartenance n'existe pas ou appartient "
                    "a une AUTRE entite, ou son profil n'est pas listable. Distinguer "
                    "apprendrait qu'un brouillon existe."
                )
            },
        },
        summary="Consulter la fiche profil complete d'un collaborateur",
        description=(
            "Les champs du cahier §10.2, ET la photo depuis `T5` — un CHEMIN vers la "
            "MINIATURE, ou `null` pour l'avatar neutre du §21.2. "
            "Exige une session : la matrice §5 donne « Fiches collaborateur », « Statut "
            "mission/intercontrat » et « Client actif » en LECTURE aux huit roles "
            "authentifies, sans distinction. "
            "AUCUN CHAMP N'EST MASQUE : la matrice ne definit aucune visibilite par "
            "champ, et en inventer une serait le §6.5 — voir `ECART-051`. "
            "La population est celle du trombinoscope : une fiche accessible alors que "
            "la liste l'exclut rendrait le filtre de la liste decoratif."
        ),
    )
    def lire_le_profil(
        #  Les DEUX parametres sont en `Annotated`, et pas seulement le second :
        #  Python refuse un parametre sans defaut apres un parametre qui en a un.
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite, unique et jamais reattribue",
            ),
        ],
        #  `Annotated` et non un defaut : ruff n'exempte `Path` de `B008` que pour
        #  les annotations qu'il reconnait, et `uuid.UUID` n'en fait pas partie.
        #  La forme est sure ici -- `Path` et `uuid` sont importes au niveau
        #  module, donc resolvables (le piege de `T1` du LOT 4 tenait a une
        #  variable de FERMETURE), et un test sans session le prouve par un 401.
        appartenance: Annotated[
            uuid.UUID,
            Path(description="L'identifiant de l'appartenance, rendu par le trombinoscope"),
        ],
    ) -> FicheDuProfil:
        """Consulter une fiche profil — cahier §10.2, backlog `MVP-L05-US004`."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            instant = dt.datetime.now(tz=dt.UTC)
            fiche = lire_la_fiche(
                connexion,
                entite=entite.id,
                appartenance=appartenance,
                instant=instant,
            )
            #  **LE MEME SERVICE QUE LA ROUTE DE PHOTO**, dans la MEME
            #  transaction que la fiche : le champ annonce donc exactement ce
            #  que la route servira, et non ce qu'une seconde regle croirait.
            miniature = (
                resoudre_la_miniature(
                    connexion,
                    entite=entite.id,
                    appartenance=appartenance,
                    instant=instant,
                )
                if fiche is not None
                else None
            )

        if fiche is None:
            #  **LE MEME REFUS QUE POUR UNE ENTITE INCONNUE**, et c'est delibere :
            #  quatre causes, une seule reponse. Un refus distinct pour « cette
            #  appartenance existe mais son profil est masque » apprendrait
            #  l'existence de la personne.
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        return _en_reponse(
            fiche,
            photo=(
                None
                if miniature is None
                else chemin_de_la_photo(parametres.API_PREFIX, code, appartenance)
            ),
        )

    @routeur.get(
        GABARIT_PHOTO,
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_class=Response,
        responses={
            status.HTTP_200_OK: {
                "content": {"image/*": {}},
                "description": "Les octets de la MINIATURE. Jamais ceux de l'original.",
            },
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Aucune photo a servir — l'appelant affiche l'avatar neutre du "
                    "§21.2. UNE SEULE forme pour SEPT causes : entite inconnue ou non "
                    "active, appartenance inexistante ou d'une autre entite, profil non "
                    "listable, pas d'autorisation active, media non `ready`, aucune "
                    "variante `thumbnail`, ou objet absent du stockage. Distinguer "
                    "« il a une photo mais tu n'y as pas droit » de « il n'a pas de "
                    "photo » apprendrait ce que le §21.2 ne veut pas dire."
                )
            },
        },
        summary="Servir la miniature autorisee d'un collaborateur",
        description=(
            "La variante `thumbnail`, et JAMAIS l'original — cahier §25.3 et backlog "
            "`MVP-L05-US005`. Quatre conditions : autorisation ACTIVE (§12.2), media "
            "`ready` (§16.1), meme entite (§25.3), variante `thumbnail` presente. "
            "La generation des variantes appartient au LOT 11 (`MVP-L11-US005`) : cette "
            "route SELECTIONNE et SERT, elle ne fabrique rien."
        ),
    )
    def servir_la_photo(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant d'appartenance")],
    ) -> Response:
        """Servir la miniature — cahier §25.3, backlog `MVP-L05-US005`."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            miniature = (
                None
                if entite is None
                else resoudre_la_miniature(
                    connexion,
                    entite=entite.id,
                    appartenance=appartenance,
                    instant=dt.datetime.now(tz=dt.UTC),
                )
            )

        if miniature is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        try:
            octets = lire_l_objet(parametres, miniature.object_key)
        except ObjetIntrouvable as erreur:
            #  **LE MEME REFUS, ET LA CAUSE JOURNALISEE ICI MEME.**
            #
            #  Un navigateur ne peut rien faire de la distinction entre « la
            #  miniature a disparu du stockage » et « il n'a pas de photo » ;
            #  l'exploitant, lui, en a besoin -- sinon une panne de MinIO produit
            #  des avatars neutres **en silence**, a l'echelle de tout le
            #  trombinoscope, et rien ne le dit.
            #
            #  **ET C'EST ICI QUE CA DOIT ETRE ECRIT, PAS DANS LE GESTIONNAIRE.**
            #  `gerer_erreur_applicative` ne journalise RIEN -- mesure du
            #  07/09/2026, `app/shared/errors.py` -- et mon commentaire affirmait
            #  d'abord le contraire : defaut `T5-1`, classe §7.11, dans mon propre
            #  code. La correction est de rendre l'affirmation vraie.
            #
            #  `resultat: echec` et non `refus` : `DEC-468`, l'appelant n'a rien
            #  fait de mal. La cle est journalisee -- c'est la seule facon de
            #  retrouver l'objet -- et elle n'est pas un secret : le §16.1 interdit
            #  qu'un client la FOURNISSE, pas qu'un journal serveur la porte.
            journal.error(
                "miniature illisible dans le stockage : avatar neutre servi",
                extra={
                    "resultat": "echec",
                    "code_erreur": "miniature_illisible",
                    "cle_objet": miniature.object_key,
                },
            )
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            ) from erreur

        return Response(content=octets, media_type=miniature.mime)

    return routeur


def _cercle(cercle: CercleDuProfil) -> CercleDeLaFiche:
    return CercleDeLaFiche(
        code=cercle.code, nom=cercle.nom, jeton_de_couleur=cercle.jeton_de_couleur
    )


def _responsabilite(responsabilite: ResponsabiliteDuProfil) -> ResponsabiliteDeLaFiche:
    return ResponsabiliteDeLaFiche(
        type=responsabilite.type, cercle=responsabilite.cercle, bureau=responsabilite.bureau
    )


def _en_reponse(fiche: FicheProfil, *, photo: str | None) -> FicheDuProfil:
    """Le domaine vers la reponse HTTP, champ par champ.

    **AUCUN `**dataclasses.asdict()`**, et c'est deliberé : une conversion
    automatique ferait passer un champ NOUVEAU du domaine vers la reponse sans que
    personne ne l'ait decide. Le §10.2 enumere les champs ; les enumerer ici aussi
    rend toute addition visible en revue.
    """
    return FicheDuProfil(
        id=fiche.id,
        person_id=fiche.person_id,
        first_name=fiche.first_name,
        last_name=fiche.last_name,
        preferred_name=fiche.preferred_name,
        professional_category=fiche.professional_category,
        arrival_date=fiche.arrival_date,
        short_bio=fiche.short_bio,
        fun_fact=fiche.fun_fact,
        metier=fiche.metier,
        statut=fiche.statut,
        client=fiche.client,
        dsm=fiche.dsm,
        cercle_principal=(
            None if fiche.cercle_principal is None else _cercle(fiche.cercle_principal)
        ),
        cercles_secondaires=[_cercle(c) for c in fiche.cercles_secondaires],
        responsabilites=[_responsabilite(r) for r in fiche.responsabilites],
        photo=photo,
    )
