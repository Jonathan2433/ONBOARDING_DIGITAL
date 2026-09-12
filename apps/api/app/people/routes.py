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

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.media.objets import ObjetIntrouvable, lire_l_objet
from app.media.photo import resoudre_la_miniature
from app.people.archivage import archiver_un_profil, restaurer_un_profil
from app.people.ecriture import modifier_les_donnees_organisationnelles
from app.people.modeles import EtatAppartenance, SituationProfessionnelle
from app.people.profil import (
    CercleDuProfil,
    FicheProfil,
    ResponsabiliteDuProfil,
    lire_la_fiche,
    lire_la_fiche_archivee,
)
from app.people.trombinoscope import (
    LONGUEUR_MAXIMALE_RECHERCHE,
    TAILLE_PAR_DEFAUT,
    Filtres,
    TailleDePage,
    lister_le_trombinoscope,
)
from app.permissions.dependances import exiger_un_role_dans_l_entite
from app.permissions.perimetre import (
    ROLES_D_ECRITURE,
    ROLES_DU_CYCLE_DE_VIE,
    ActionDeCycleDeVie,
    ChampOrganisationnel,
    PerimetreDuCycleDeVie,
    resoudre_le_cycle_de_vie,
    resoudre_le_perimetre,
)
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

#  **LE GABARIT DU CHEMIN DE PHOTO, EN UNE SEULE SOURCE.** La route le declare,
#  les deux reponses l'emploient : deux copies divergeraient au premier
#  renommage, et la liste emettrait alors un chemin qui rend 404.
journal = logging.getLogger("app.people")

#  **UN SEUL LITTERAL POUR LES DEUX ROUTES.** Le `GET` de `T4` et le `PATCH`
#  de `T7` servent la MEME ressource : deux litteraux identiques divergeraient
#  au premier renommage, et l'un des deux resterait servi sans que rien ne le
#  dise. Meme motif que `GABARIT_PHOTO`.
GABARIT_FICHE: Final = "/entities/{code}/people/{appartenance}"
GABARIT_PHOTO: Final = "/entities/{code}/people/{appartenance}/photo"

#  Les trois chemins de `T8`. **DES NOMS, PAS DES VERBES** : c'est la convention
#  des cinq ecritures d'authentification du LOT 3 -- `/connexion`,
#  `/deconnexion`, `/magic-link/consommation`.
#
#  Et `fiche-archivee` plutot qu'`archive` : deux segments freres nommes
#  `archivage` et `archive` se confondent a la lecture d'un journal, et c'est
#  precisement dans un journal qu'on les lira.
GABARIT_ARCHIVAGE: Final = "/entities/{code}/people/{appartenance}/archivage"
GABARIT_RESTAURATION: Final = "/entities/{code}/people/{appartenance}/restauration"
GABARIT_FICHE_ARCHIVEE: Final = "/entities/{code}/people/{appartenance}/fiche-archivee"


def chemin_de_la_photo(prefixe: str, code: str, appartenance: uuid.UUID) -> str:
    """Le chemin complet de la miniature, prefixe versionne compris."""
    return prefixe + GABARIT_PHOTO.format(code=code, appartenance=appartenance)


if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

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


class DemandeDeModification(BaseModel):
    """Les six champs du §10.2, tous FACULTATIFS, et la version attendue.

    **`CHAMP ABSENT` ET `CHAMP NUL` NE SONT PAS LA MEME CHOSE, ET LA BASE LE
    PROUVE.** Mesure du 09/09/2026 sur les six colonnes cibles : **seule**
    `professional_status_assignment.client_id` est nullable. Un consultant en
    intercontrat n'a pas de client, donc `client: null` est une valeur LEGITIME ;
    un `metier: null` ne l'est pas, et la base le refuserait avec un message qui
    ne dirait pas que la cause est une demande mal formee.

    `model_fields_set` distingue les deux, et un nul explicite sur les cinq
    colonnes non nullables est refuse en `422` **avant** d'atteindre la base.

    **`extra="forbid"` PLUTOT QUE L'IGNORANCE PAR DEFAUT.** Un client qui
    enverrait `presentation_courte` -- une ligne DISTINCTE du §6.1, hors du
    perimetre de `T7` -- doit l'apprendre. L'ignorer en silence lui ferait croire
    que sa modification a ete prise.
    """

    model_config = ConfigDict(extra="forbid")

    version: int = Field(
        ge=1,
        description=(
            "La version lue sur la fiche. Cahier §18.4 : une version obsolete rend 409 "
            "sans ecrasement silencieux."
        ),
    )
    date_d_arrivee: dt.date | None = Field(default=None, description="Cahier §10.2")
    metier: uuid.UUID | None = Field(default=None, description="`job_catalog_id`")
    statut: SituationProfessionnelle | None = Field(default=None, description="§30.5")
    client: uuid.UUID | None = Field(
        default=None,
        description=(
            "`null` est une valeur LEGITIME : un intercontrat n'a pas de client. "
            "C'est le seul des six champs dont la colonne soit nullable."
        ),
    )
    dsm: uuid.UUID | None = Field(default=None, description="La personne DSM")
    cercle_principal: uuid.UUID | None = Field(default=None, description="§8.2")


#  Les champs dont un `null` EXPLICITE est refuse, parce que leur colonne est
#  `NOT NULL`. **DERIVE D'UNE MESURE, PAS D'UNE INTUITION** : les six colonnes
#  ont ete lues dans `information_schema`, et `client_id` est la seule nullable.
#
#  Retirer une affectation sans la remplacer n'est pas « modifier » : ce serait
#  cloturer sans ouvrir, et le §30.4 veut qu'un consultant actif AIT un DSM.
#  L'operation existe peut-etre, mais elle n'est pas dans le §6.1 et donc pas ici.
CHAMPS_SANS_NUL: Final[frozenset[ChampOrganisationnel]] = frozenset(ChampOrganisationnel) - {
    ChampOrganisationnel.CLIENT
}

CODE_NUL_REFUSE: Final = "valeur_nulle_refusee"
MESSAGE_NUL_REFUSE: Final = (
    "Ce champ ne peut pas etre vide. Pour retirer une affectation, employez l'operation dediee."
)


class ReponseDeModification(BaseModel):
    """Ce qui a change, et la version nouvelle a reutiliser.

    **`champs_modifies` PEUT ETRE VIDE, ET CE N'EST PAS UNE ERREUR.** Une demande
    qui redonne les valeurs courantes ne ferme aucune periode -- l'historique ne
    doit pas se remplir de periodes d'une microseconde -- et la version ne monte
    donc pas. Le dire vaut mieux que de rendre `200` sans expliquer pourquoi
    l'historique n'a pas bouge.
    """

    version: int
    champs_modifies: list[str]


class DemandeDArchivage(BaseModel):
    """La version attendue, et la date de depart facultative.

    **`date_de_depart` N'EST PAS UNE INVENTION** : le §2.1 du cahier range « date
    de depart » parmi les informations que porte `entity_membership`, et le §24.1
    libelle la transition « depart ENREGISTRE ». La rendre facultative est ce qui
    permet d'archiver quelqu'un parti la semaine derniere sans ecrire une date
    fausse -- et a defaut, le jour de l'appel.

    Elle est **ignoree** quand la cible est `future` ou `departed` : le §24.1 n'y
    passe par aucun depart, et l'« arrivee annulee » n'en est pas un.
    """

    model_config = ConfigDict(extra="forbid")

    version: int = Field(
        ge=1,
        description=(
            "La version lue sur la fiche. Cahier §18.4 : une version obsolete rend 409 "
            "sans ecrasement silencieux."
        ),
    )
    date_de_depart: dt.date | None = Field(
        default=None,
        description=(
            "Cahier §2.1. A defaut, le jour de l'appel. La contrainte "
            "`depart_apres_arrivee` refuse une date anterieure a l'arrivee (422)."
        ),
    )


class DemandeDeRestauration(BaseModel):
    """La version attendue, et rien d'autre.

    **AUCUN CHAMP DE REAFFECTATION, ET C'EST UN ARBITRAGE DU 10/09/2026.** La
    restauration remet l'appartenance en `active` et laisse metier, statut,
    client, DSM et cercle **clos** : les redonner est une decision humaine, que le
    `PATCH` de `T7` sert. Voir l'en-tete de `app/people/archivage.py`.
    """

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, description="Cahier §18.4, comme pour l'archivage.")


class ReponseDArchivage(BaseModel):
    """Ce que l'archivage a produit, ET ce qu'il a rapporte sans le traiter.

    **LES QUATRE DERNIERS CHAMPS SONT DES RAPPORTS, PAS DES ECHECS.** Le `T9` du
    LOT 3 les a etablis et motives ; `T8` est ce qui les rend enfin lisibles par
    un humain, puisque le service n'avait aucune route. Les taire aurait laisse
    croire qu'un archivage ne laisse jamais rien derriere lui -- alors qu'il
    laisse, mesure et nomme, des consultants sans DSM.
    """

    version: int
    etat_precedent: str = Field(
        description="`active`, `future` ou `departed` — il dit si un depart a ete enregistre."
    )
    etat_nouveau: str = Field(
        description=(
            "Toujours `archived`. Il est rendu plutot que suppose : sans lui, chaque "
            "client recopierait la cible du §24.1."
        )
    )
    sessions_revoquees: int
    liens_invalides: int
    relations_closes: dict[str, int]
    #  --- ce qui est rapporte, jamais decide ---
    consultants_sans_dsm: list[uuid.UUID] = Field(
        description=(
            "Les consultants dont le partant etait le DSM. Leurs lignes ne sont PAS "
            "closes -- le lien historique est conserve, et le §30.4 veut qu'un "
            "consultant actif ait un DSM : designer le remplacant est humain."
        )
    )
    roles_globaux_conserves: int = Field(
        description="Quitter une entite ne retire pas un role global (§8.6)."
    )
    relations_futures_conservees: dict[str, int] = Field(
        description=(
            "Une relation qui n'a pas commence ne peut pas etre close a cet instant : "
            "`ends_at < starts_at` rendrait la periode invalide."
        )
    )


class ReponseDeRestauration(BaseModel):
    """La version nouvelle, et ce qui reste a redonner a la main."""

    version: int
    etat_precedent: str = Field(description="Toujours `archived` — le §24.1 n'a que ce depart.")
    etat_nouveau: str = Field(description="Toujours `active`.")
    relations_a_redonner: list[str] = Field(
        description=(
            "Les relations de l'appartenance SANS periode courante apres la "
            "restauration — mesurees, pas supposees. La restauration ne rouvre rien."
        )
    )


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
        GABARIT_FICHE,
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

    #  **LA FABRIQUE EST APPELEE UNE FOIS, AU MONTAGE.** Elle fige son
    #  `frozenset` de roles et refuse une liste vide -- une route ainsi gardee
    #  serait morte sans que rien ne le dise.
    garde_d_ecriture = exiger_un_role_dans_l_entite(parametres, ROLES_D_ECRITURE)
    #  **UNE SECONDE GARDE, PARCE QUE LA MATRICE PORTE DEUX GRILLES.** Le §6.1
    #  met `DSM` et `BOOST` a TIRET sur les trois lignes de cycle de vie, alors
    #  qu'ils portent tous deux un droit de modification. Reutiliser
    #  `garde_d_ecriture` accorderait donc l'archivage a deux roles que le
    #  document en exclut, et le §6.2 le redit en clair.
    garde_du_cycle_de_vie = exiger_un_role_dans_l_entite(parametres, ROLES_DU_CYCLE_DE_VIE)

    @routeur.patch(
        GABARIT_FICHE,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeModification,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Deux causes, deux codes. `acces_refuse` : aucun role d'ecriture dans "
                    "cette entite -- `EMP`, `NEW` et `OFFICE` sont dans ce cas, et le §6.2 "
                    "le dit en clair pour `OFFICE`. `champ_hors_perimetre` : le role existe "
                    "mais pas sur CETTE personne, ou pas sur CE champ -- un DSM sur le "
                    "consultant d'un autre DSM, un Booster sur le DSM d'un membre."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite inconnue ou non active. Meme forme que la lecture."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : le profil a change depuis votre lecture -- cahier "
                    "§18.4, « sans ecrasement silencieux ». `periode_incompatible` : une "
                    "affectation POSTERIEURE existe, et l'ecrire chevaucherait un avenir "
                    "decide ailleurs. La base refuse, elle n'arbitre pas."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`valeur_nulle_refusee` : seul `client` accepte `null`, les cinq autres "
                    "colonnes etant `NOT NULL`. `valeur_refusee` : un statut `mission` exige "
                    "un client et un `intercontract` n'en accepte aucun (§30.5)."
                )
            },
        },
        summary="Modifier les donnees organisationnelles d'un collaborateur",
        description=(
            "Les SIX champs que le cahier §10.2 nomme « donnees organisationnelles » : date "
            "d'arrivee, metier, statut, client, DSM, cercle principal. Backlog "
            "`MVP-L05-US006`.<br><br>"
            "**Presentation courte, fun fact et cercles secondaires ne sont PAS ici** : ce sont "
            "des lignes DISTINCTES du §6.1, avec leurs propres portees -- `NEW` peut modifier "
            "son fun fact avant validation, ce qui n'est vrai d'aucun champ ci-dessus.<br><br>"
            "**Les quatre relations historisees sont CLOTUREES puis REOUVERTES**, jamais "
            "ecrasees : §23.4, et une contrainte d'exclusion par table le rend structurel."
        ),
    )
    def modifier_le_profil(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[
            uuid.UUID, Path(description="L'identifiant d'appartenance, rendu par la fiche")
        ],
        demande: DemandeDeModification,
        requete: Request,
        #  **LA DEPENDANCE EST PRISE EN PARAMETRE, PAS EN `dependencies`**, parce
        #  que son verdict est utile : elle rend l'appelant, dont le service a
        #  besoin pour `updated_by_person_id`. En `dependencies` sa valeur serait
        #  jetee et il faudrait une seconde dependance pour la session.
        #
        #  **PREMIER CONSOMMATEUR DE `exiger_un_role_dans_l_entite`**, ecrite et
        #  testee au `T9` du LOT 4 et sans emploi depuis : la matrice §5 ne
        #  distingue aucun role en LECTURE, et la restriction du §5.1 porte sur
        #  l'ECRITURE. Elle repond « cet appelant a-t-il un role d'ecriture ICI »
        #  et refuse `EMP`, `NEW` et `OFFICE` avant toute transaction.
        #  **`Depends` EN DEFAUT, PAS DANS `Annotated`, ET LE MOTIF EST MESURE.**
        #  Ce module porte `from __future__ import annotations` : toute annotation
        #  est une CHAINE, que Pydantic doit resoudre au montage. Or `parametres`
        #  est une variable de FERMETURE du routeur, invisible au niveau module :
        #  la forme `Annotated[SessionEtablie, Depends(fabrique(parametres, ...))]`
        #  fait echouer la construction du schema OpenAPI avec
        #  « is not fully defined ». C'est le piege de `T1` du LOT 4, que le
        #  commentaire du `GET` voisin nomme deja.
        #
        #  **NI `ruff` NI `mypy` NE L'ONT VU** -- les deux passaient au vert. Seul
        #  le montage de l'application l'a dit. §7.28 : lis ce que la cible FAIT.
        #
        #  Le `noqa` est ici JUSTIFIE, et c'est la forme que `permissions/routes.py`
        #  emploie deja depuis le `T8` du LOT 4 : `B008` interdit un appel en
        #  valeur par defaut, ce qui est precisement l'idiome de FastAPI.
        #  **LE GARDE-FOU EST NOMME AU-DESSUS, ET C'EST CE QUI REND LA LIGNE
        #  TENABLE.** `B008` produit DEUX diagnostics sur cette construction --
        #  l'appel interieur ET `Depends` lui-meme -- et une exemption ne couvre
        #  que sa propre ligne. Etale sur trois lignes, il en faudrait deux.
        #  `permissions/routes.py` tient sur une seule depuis le `T8` du LOT 4 ;
        #  nommer la fabrique rend la meme forme possible ici.
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDeModification:
        """Modifier les donnees organisationnelles — matrice §6.1 et §6.2."""
        #  **LE JETON EST LU DANS LE COOKIE, PAS RECU DE LA DEPENDANCE.**
        #  `SessionEtablie` ne le porte pas a dessein -- voir son docstring : le
        #  faire circuler multiplierait les endroits d'ou il peut fuir vers un
        #  journal. La deconnexion procede de la meme facon.
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        #  Le garde-fou a valide la session depuis ce meme cookie, donc il est la.
        #  S'il manquait, passer `None` DESARMERAIT la barriere de jeton en
        #  silence : on refuse plutot, avec le meme gabarit que les autres causes.
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        demandes = _lire_la_demande(demande)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  **LES PERMISSIONS SONT RESOLUES A NOUVEAU, ET DANS CETTE
            #  TRANSACTION.** Le garde-fou a resolu les SIENNES, dans sa propre
            #  connexion et a son propre instant : s'y fier ferait ecrire a `T2`
            #  ce qui a ete autorise a `T1`. Ce n'est pas une seconde copie de la
            #  regle -- c'est le meme appel, au bon instant et dans le bon
            #  perimetre transactionnel.
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible=appartenance,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            modification = modifier_les_donnees_organisationnelles(
                connexion,
                entite=entite.id,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                demande=demandes,
                perimetre=perimetre,
                instant=instant,
            )
        return ReponseDeModification(
            version=modification.version,
            champs_modifies=sorted(champ.value for champ in modification.champs),
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

    # -------------------------------------------------------------------
    #  LE CYCLE DE VIE — LOT 5, `T8`, story `MVP-L05-US007`
    # -------------------------------------------------------------------

    @routeur.post(
        GABARIT_ARCHIVAGE,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDArchivage,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "UNE SEULE forme pour trois causes : l'appelant n'a aucun des trois "
                    "roles du §6.1 dans cette entite, la cible est deja `archived`, ou le "
                    "jeton anti-CSRF manque ou ne correspond pas."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Code inconnu, ou entite existante mais non active."
            },
            status.HTTP_409_CONFLICT: {
                "description": "Version obsolete — cahier §18.4, sans ecrasement silencieux."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "Demande mal formee, ou date de depart anterieure a la date "
                    "d'arrivee (`depart_apres_arrivee`)."
                )
            },
        },
        summary="Archiver un profil",
        description=(
            "« Archiver un profil » du §6.1 — **ESM, administrateur d'entite et "
            "super-administrateur seulement**, `DSM` et `BOOST` etant a tiret sur cette "
            "ligne alors qu'ils modifient. Backlog `MVP-L05-US007`.<br><br>"
            "**L'ACTION PARCOURT LE CHEMIN DU §24.1**, qui n'a aucune transition "
            "`Active --> Archived` : depuis `active`, le depart est enregistre PUIS "
            "l'archivage applique ; depuis `future` (« arrivee annulee ») ou `departed`, "
            "l'archivage seul.<br><br>"
            "**LA REVOCATION TIENT AU DEPART, ET ELLE EST IMMEDIATE** (§7.4, §30.22) : "
            "sessions revoquees, liens actifs invalides, et les SIX relations "
            "historisees du §25.2 closes. Quatre situations sont **rapportees** dans la "
            "reponse plutot que traitees en silence."
        ),
    )
    def archiver_le_profil(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[
            uuid.UUID, Path(description="L'identifiant d'appartenance, rendu par la fiche")
        ],
        demande: DemandeDArchivage,
        requete: Request,
        #  Meme forme que le `PATCH` voisin, et pour les memes deux motifs : le
        #  verdict de la dependance est UTILISE -- `updated_by_person_id` -- et
        #  `Depends` en valeur par defaut est le seul montage resoluble sous
        #  `from __future__ import annotations`.
        appelant: SessionEtablie = Depends(garde_du_cycle_de_vie),  # noqa: B008
    ) -> ReponseDArchivage:
        """Archiver un profil — matrice §6.1, §6.2 et modele §24.1."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite, perimetre = _resoudre_le_cycle(
                connexion, code=code, appelant=appelant, cible=appartenance, instant=instant
            )
            archivage = archiver_un_profil(
                connexion,
                entite=entite,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                perimetre=perimetre,
                instant=instant,
                date_de_depart=demande.date_de_depart,
            )
        return ReponseDArchivage(
            version=archivage.version,
            etat_precedent=archivage.etat_precedent,
            etat_nouveau=EtatAppartenance.ARCHIVED.value,
            sessions_revoquees=archivage.sessions_revoquees,
            liens_invalides=archivage.liens_invalides,
            relations_closes=archivage.relations_closes,
            consultants_sans_dsm=list(archivage.consultants_sans_dsm),
            roles_globaux_conserves=archivage.roles_globaux_conserves,
            relations_futures_conservees=archivage.relations_futures_conservees,
        )

    @routeur.post(
        GABARIT_RESTAURATION,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeRestauration,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "UNE SEULE forme pour trois causes : aucun des trois roles du §6.1, "
                    "la cible n'est pas `archived`, ou le jeton anti-CSRF manque."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Code inconnu, ou entite existante mais non active."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "Version obsolete (§18.4), **ou** la base refuse le retour dans un "
                    "etat occupant — la personne occupe deja une appartenance, ou la "
                    "periode redevenue ouverte en chevauche une posterieure. La cause "
                    "n'est PAS nommee : elle porterait sur une autre entite (§5.1). Elle "
                    "est journalisee cote serveur."
                )
            },
        },
        summary="Reactiver un profil archive",
        description=(
            "« Reactiver un profil archive » du §6.1 — `Archived --> Active`, la "
            "quatrieme et derniere transition du §24.1, « reactivation explicite "
            "autorisee ». Backlog `MVP-L05-US007`.<br><br>"
            "**« CONDITIONNEL » POUR L'ESM N'EST PAS UNE DECISION EN SUSPENS** : le §18 "
            "precise « Entite, restauration **fonctionnelle** » et `ARB-DROIT-003` "
            "reserve a l'ADM-E et au SUPER les restaurations « techniques, massives ou "
            "liees aux imports ». Un profil a l'unite est fonctionnelle.<br><br>"
            "**ELLE NE ROUVRE AUCUNE AFFECTATION** — arbitrage du 10/09/2026. Metier, "
            "statut, client, DSM et cercle restent clos, et `relations_a_redonner` dit "
            "lesquels manquent : les redonner passe par le `PATCH` de `T7`, parce qu'un "
            "DSM reaffecte par la plateforme serait un DSM que personne n'a designe."
        ),
    )
    def restaurer_le_profil(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant d'appartenance")],
        demande: DemandeDeRestauration,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_du_cycle_de_vie),  # noqa: B008
    ) -> ReponseDeRestauration:
        """Reactiver un profil archive — matrice §6.1 et modele §24.1."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite, perimetre = _resoudre_le_cycle(
                connexion, code=code, appelant=appelant, cible=appartenance, instant=instant
            )
            restauration = restaurer_un_profil(
                connexion,
                entite=entite,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                perimetre=perimetre,
                instant=instant,
            )
        return ReponseDeRestauration(
            version=restauration.version,
            etat_precedent=restauration.etat_precedent,
            etat_nouveau=EtatAppartenance.ACTIVE.value,
            relations_a_redonner=list(restauration.relations_a_redonner),
        )

    @routeur.get(
        GABARIT_FICHE_ARCHIVEE,
        status_code=status.HTTP_200_OK,
        response_model=FicheDuProfil,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": "L'appelant n'a aucun des trois roles du §6.1 dans cette entite."
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour quatre causes : code inconnu ou entite non "
                    "active, appartenance inexistante, appartenance d'une autre entite, "
                    "ou appartenance qui n'est PAS archivee. Distinguer apprendrait "
                    "qu'une appartenance existe — §2.5, refus par defaut."
                )
            },
        },
        summary="Consulter un profil archive",
        description=(
            "« Consulter un profil archive » du §6.1 — **ESM (« besoin fonctionnel »), "
            "administrateur d'entite et super-administrateur**. C'est une ligne "
            "DISTINCTE de « Consulter un profil actif », qui est ouverte aux huit "
            "roles : la consultation d'un archive est un acte delibere, d'ou une route "
            "a part plutot qu'un assouplissement de la fiche.<br><br>"
            "**LE TROMBINOSCOPE CONTINUE D'EXCLURE LES ARCHIVES**, y compris pour un "
            "super-administrateur, et un test le fige : le §6.1 lui donne la ligne "
            "« profil actif ».<br><br>"
            "**LA VISIBILITE N'EST PAS FILTREE ICI** : l'archivage ne touche pas "
            "`profile_visibility`, donc un archive peut etre `draft`, `published` ou "
            "`hidden`. Filtrer ferait echouer un acte que le §6.1 autorise.<br><br>"
            "**AUCUNE ENUMERATION DES ARCHIVES N'EXISTE**, et ce n'est pas un oubli : "
            "le corpus n'en decrit aucune (mesure du 10/09/2026, zero occurrence), et "
            "les six axes de filtre du `MVP-L05-US002` sont entite, cercle, DSM, client, "
            "metier et statut. L'identifiant vient donc d'ailleurs — l'historique de "
            "`T9`, ou le back-office du LOT 9."
        ),
    )
    def consulter_la_fiche_archivee(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant d'appartenance")],
        appelant: SessionEtablie = Depends(garde_du_cycle_de_vie),  # noqa: B008
    ) -> FicheDuProfil:
        """Consulter un profil archive — matrice §6.1."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite, perimetre = _resoudre_le_cycle(
                connexion, code=code, appelant=appelant, cible=appartenance, instant=instant
            )
            if ActionDeCycleDeVie.CONSULTER_UN_ARCHIVE not in perimetre.actions:
                #  **UN 404 ET NON UN 403, ET LA DIFFERENCE EST DELIBEREE.** La
                #  garde de role a deja rendu 403 si l'appelant n'a aucun des
                #  trois roles. Arriver ici veut dire qu'il les a et que la CIBLE
                #  n'est pas archivee : lui rendre 403 lui apprendrait qu'une
                #  appartenance existe dans un autre etat, ce que le 404 de la
                #  fiche ordinaire ne dit pas non plus.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            fiche = lire_la_fiche_archivee(
                connexion, entite=entite, appartenance=appartenance, instant=instant
            )
        if fiche is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        #  **AUCUNE PHOTO SUR UNE FICHE ARCHIVEE.** `chemin_de_la_photo` mene a
        #  une route qui exige un profil LISTABLE : le lien serait un 404 garanti.
        #  Un champ qui vaut toujours `null` est ce que `T4` avait refuse pour la
        #  photo elle-meme, et le motif est le meme -- laisser croire.
        return _en_reponse(fiche, photo=None)

    return routeur


def _resoudre_le_cycle(
    connexion: Connection,
    *,
    code: str,
    appelant: SessionEtablie,
    cible: uuid.UUID,
    instant: dt.datetime,
) -> tuple[uuid.UUID, PerimetreDuCycleDeVie]:
    """L'entite active et le perimetre de cycle de vie, en UN exemplaire.

    **LES TROIS ROUTES DE `T8` PARTAGENT CE PROLOGUE**, et l'ecrire trois fois
    donnerait trois regles pour une seule -- `DEC-466`, `ECART-022`. Le jour ou le
    §6.1 gagnerait une quatrieme ligne de cycle de vie, il n'y aurait qu'un
    endroit a lire.

    **LES PERMISSIONS SONT RESOLUES DANS CETTE TRANSACTION**, et non reprises de
    la garde de role : celle-ci a resolu les siennes dans sa propre connexion et
    a son propre instant. Ce n'est pas une seconde copie de la regle, c'est le
    meme appel au bon instant -- exactement le parti de `T7`.
    """
    entite = resoudre_une_entite_active(connexion, code)
    if entite is None:
        raise ErreurApplicative(
            code=CODE_ENTITE_INTROUVABLE,
            message=MESSAGE_ENTITE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
    perimetre = resoudre_le_cycle_de_vie(
        connexion,
        entite=entite.id,
        cible=cible,
        roles=frozenset(permissions.roles),
    )
    return entite.id, perimetre


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


def _lire_la_demande(demande: DemandeDeModification) -> dict[ChampOrganisationnel, object]:
    """Les champs REELLEMENT presents dans le corps, et le refus des nuls interdits.

    **`model_fields_set` EST LA SEULE FACON DE DISTINGUER `absent` DE `null`.**
    Lire les attributs rendrait `None` dans les deux cas, et une demande qui ne
    touche pas au client serait indistinguable d'une demande qui le retire.
    """
    presents: dict[ChampOrganisationnel, object] = {}
    nuls_refuses: list[str] = []
    for champ in ChampOrganisationnel:
        if champ.value not in demande.model_fields_set:
            continue
        valeur = getattr(demande, champ.value)
        if valeur is None and champ in CHAMPS_SANS_NUL:
            nuls_refuses.append(champ.value)
            continue
        #  L'enumeration est rendue a sa VALEUR : la base porte une colonne
        #  `character varying` avec un `CHECK`, pas un type `enum` natif
        #  (`DEC-499`), et lui passer le membre laisserait psycopg deviner.
        presents[champ] = valeur.value if isinstance(valeur, SituationProfessionnelle) else valeur
    if nuls_refuses:
        raise ErreurApplicative(
            code=CODE_NUL_REFUSE,
            message=MESSAGE_NUL_REFUSE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"champs": sorted(nuls_refuses)},
        )
    return presents
