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
from typing import TYPE_CHECKING, Annotated, Any, Final

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.audit.motif import exiger_un_motif_si_necessaire
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
from app.people.catalogues import lister_le_catalogue_des_metiers
from app.people.creation import (
    CODE_ACCES_REFUSE,
    MESSAGE_ACCES_REFUSE,
    DemandeDAppartenance,
    DemandeDeCollaborateur,
    creer_un_collaborateur,
)
from app.people.ecriture import modifier_les_donnees_organisationnelles
from app.people.historique import HistoriqueOrganisationnel, lire_l_historique
from app.people.modeles import EtatAppartenance, SituationProfessionnelle
from app.people.profil import (
    CercleDuProfil,
    FicheProfil,
    ResponsabiliteDuProfil,
    lire_la_fiche,
    lire_la_fiche_archivee,
)
from app.people.transfert import changer_d_entite
from app.people.transfert_masse import (
    TAILLE_MAXIMALE_DU_LOT,
    ElementDuTransfertEnMasse,
    ResultatDUnTransfert,
    executer_le_transfert_en_masse,
)
from app.people.trombinoscope import (
    LONGUEUR_MAXIMALE_RECHERCHE,
    Filtres,
    lister_le_trombinoscope,
)
from app.permissions.dependances import exiger_un_role_dans_l_entite
from app.permissions.perimetre import (
    ROLES_D_ECRITURE,
    ROLES_DE_L_HISTORIQUE,
    ROLES_DU_CYCLE_DE_VIE,
    ActionDeCycleDeVie,
    ChampOrganisationnel,
    PerimetreDuCycleDeVie,
    PropositionDeCreation,
    resoudre_l_acces_a_l_historique,
    resoudre_l_autorisation_de_creation,
    resoudre_le_cycle_de_vie,
    resoudre_le_perimetre,
)
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

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

#  **LE CHEMIN DE COLLECTION DE `T2`, LOT 9.** Pas `/people/creation` — un nom
#  de verbe, contrairement a la convention des ecritures d'authentification
#  (§7, "des NOMS, pas des VERBES") qui vaut pour une ACTION sur une ressource
#  deja identifiee. Ici la ressource n'existe pas encore : `POST` sur la
#  collection EST le verbe, par la convention REST que ce depot emploie deja
#  pour `POST /entities/{code}/events` (LOT 8, `T3`).
GABARIT_COLLECTION: Final = "/entities/{code}/people"

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

#  Le chemin de `T3`, LOT 9. `code` est l'entite QUITTEE, meme convention que
#  les trois precedents ; l'entite d'ARRIVEE vient de la demande.
GABARIT_CHANGEMENT_D_ENTITE: Final = "/entities/{code}/people/{appartenance}/changement-d-entite"

#  Le chemin de `T9`. Un NOM, comme les autres.
GABARIT_HISTORIQUE: Final = "/entities/{code}/people/{appartenance}/historique"

#  Les deux chemins de `T11`, LOT 9. `code` est l'entite SOURCE de tous les
#  elements du lot, meme convention que `GABARIT_CHANGEMENT_D_ENTITE` — la
#  destination, elle, varie par element et vient du corps. `/apercu` est un
#  SEGMENT DE PLUS sur la MEME collection, jamais une seconde ressource : les
#  deux executent exactement le meme chemin, seule la finalite (ecrire ou
#  non) differe (voir `app.people.transfert_masse`).
GABARIT_TRANSFERT_EN_MASSE: Final = "/entities/{code}/people/transferts-en-masse"
GABARIT_TRANSFERT_EN_MASSE_APERCU: Final = f"{GABARIT_TRANSFERT_EN_MASSE}/apercu"


def chemin_de_la_photo(prefixe: str, code: str, appartenance: uuid.UUID) -> str:
    """Le chemin complet de la miniature, prefixe versionne compris."""
    return prefixe + GABARIT_PHOTO.format(code=code, appartenance=appartenance)


if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres


class CollaborateurDuTrombinoscope(BaseModel):
    """Une ligne du trombinoscope.

    **DOUZE champs depuis `T10`, qui a ajoute les QUATRE du VERSO.** Le §10.1 dit
    « le **verso** presente les informations **professionnelles principales** », et
    un ecran ne peut pas inventer ce que l'API ne sert pas. Le cout est une
    TROISIEME requete, bornee aux lignes de la page : voir `_ENRICHISSEMENT` dans
    `trombinoscope.py`.

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

    #  **LES QUATRE DU VERSO, TOUS FACULTATIFS**, et c'est le schema qui le dit :
    #  un nouvel arrivant peut n'avoir ni metier, ni statut, ni cercle, et
    #  `client_id` est nul en `intercontract`.
    metier: str | None
    statut: str | None
    client: str | None
    cercle: CercleDeLaListeRendu | None


class CercleDeLaListeRendu(BaseModel):
    """Le cercle principal d'une ligne, avec son jeton de couleur.

    **LE NOM VOYAGE AVEC LE JETON, ET LE §10.1 L'EXIGE** : « la couleur du cercle
    peut etre utilisee sur les bordures, arriere-plans legers et badges, mais
    **jamais comme seul moyen de transmettre une information** ». Servir le seul
    jeton rendrait la regle inapplicable a l'ecran.
    """

    code: str
    nom: str
    #  **NULLABLE** : `circle.color_token` l'est au catalogue, et un `str(None)`
    #  servait la chaine « None ». Defaut `T10-8`.
    jeton_de_couleur: str | None


class CercleDeLaFiche(BaseModel):
    """Un cercle, principal ou secondaire — §10.2."""

    code: str
    nom: str
    jeton_de_couleur: str | None


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
    #  **§18.4 — LA VERSION, SANS LAQUELLE AUCUN ECRAN NE PEUT ECRIRE.** Les trois
    #  ecritures l'exigent dans leur corps, et aucune lecture ne la servait : le
    #  premier ecran qui a tente d'archiver a recu `422 Field required`, defaut
    #  `T11-6`. La servir ici ne relache RIEN -- la concurrence optimiste reste
    #  entiere, l'appelant doit toujours renvoyer la version qu'il a lue.
    version: int
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


LONGUEUR_MAXIMALE_ADRESSE: Final = 320


class DemandeDeCreationDeCollaborateur(BaseModel):
    """Creer un collaborateur — matrice §6.1, cahier §10.2. LOT 9 `T2`.

    **AUCUN CHAMP `professional_category`, ET CE N'EST PAS UN OUBLI.** Voir
    l'en-tete de `app/people/creation.py` : la categorie `dg` exige une action
    separee, non exposee par ce depot. Toute creation par cette route est un
    `consultant`.

    **`client` ACCEPTE `null`, SEUL DES SIX CHAMPS** : un statut `intercontract`
    n'a pas de client, meme regle que `DemandeDeModification`. `dsm` est
    FACULTATIF, absent par defaut — tous les consultants n'en recoivent pas un
    a la creation.
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=LONGUEUR_MAXIMALE_ADRESSE)
    prenom: str = Field(min_length=1, description="`first_name`")
    nom: str = Field(min_length=1, description="`last_name`")
    nom_prefere: str | None = Field(default=None, description="`preferred_name`, facultatif")
    date_d_arrivee: dt.date = Field(description="Cahier §10.2")
    metier: uuid.UUID = Field(description="`job_catalog_id`")
    statut: SituationProfessionnelle = Field(description="§30.5")
    client: uuid.UUID | None = Field(
        default=None,
        description="`null` est legitime : un intercontrat n'a pas de client.",
    )
    dsm: uuid.UUID | None = Field(default=None, description="La personne DSM, facultative")
    cercle_principal: uuid.UUID = Field(description="§8.2")
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class ReponseDeCreationDeCollaborateur(BaseModel):
    """L'appartenance nouvellement creee, et sa version initiale."""

    appartenance: uuid.UUID
    version: int


class MetierRendu(BaseModel):
    """Un metier du catalogue — modele §6.3. LOT 9 `T14`."""

    identifiant: uuid.UUID
    code: str
    label: str


class ReponseDuCatalogueDesMetiers(BaseModel):
    """Les metiers ACTIFS et non archives d'une entite — LOT 9 `T14`.

    Pose en construisant l'ecran back-office : `job_catalog_id` est un champ
    obligatoire de la creation (`T2`) et du changement d'entite (`T3`) depuis
    l'ouverture du lot, et aucune route n'en servait la liste jusqu'ici — un
    formulaire ne peut pas proposer un choix dont il ne connait pas les
    options. Meme motif que `GET .../templates`, pose par `T14` du LOT 7.
    """

    metiers: list[MetierRendu]


class DemandeDeChangementDEntite(BaseModel):
    """Changer un collaborateur d'entite — cahier §11.1, §16.3. LOT 9 `T3`.

    **`version` PORTE SUR L'ANCIENNE APPARTENANCE**, celle du chemin — meme
    convention que `DemandeDeModification` : la version lue sur la fiche, pas
    sur une ressource qui n'existe pas encore. Les six champs organisationnels
    sont ceux de la NOUVELLE appartenance, dans `entite_destination` ; aucune
    valeur n'y est reportee de l'ancienne, meme discipline que `T2`.
    """

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, description="La version lue sur l'ANCIENNE appartenance")
    entite_destination: str = Field(
        min_length=1,
        max_length=LONGUEUR_MAXIMALE_CODE,
        description="Le `code` de l'entite d'arrivee",
    )
    date_d_arrivee: dt.date = Field(description="Dans l'entite d'arrivee — cahier §10.2")
    metier: uuid.UUID = Field(description="`job_catalog_id`, dans l'entite d'arrivee")
    statut: SituationProfessionnelle
    client: uuid.UUID | None = Field(default=None, description="`null` si `intercontract`")
    dsm: uuid.UUID | None = Field(default=None, description="La personne DSM, facultative")
    cercle_principal: uuid.UUID = Field(description="Dans l'entite d'arrivee")
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class ReponseDeChangementDEntite(BaseModel):
    """Ce que le transfert a produit, des deux cotes — meme rapport qu'un archivage."""

    nouvelle_appartenance: uuid.UUID
    version: int
    etat_precedent: str = Field(description="`active` ou `future`, sur l'ANCIENNE appartenance")
    sessions_revoquees: int
    liens_invalides: int
    relations_closes: dict[str, int]
    parcours_onboarding_archive: uuid.UUID | None


class ElementDeTransfertEnMasseRequete(BaseModel):
    """Un transfert demande, dans le lot — MEMES CHAMPS que l'unitaire (`T3`).

    `appartenance` remplace le parametre de chemin : chaque element du lot
    nomme sa PROPRE cible, l'entite source etant commune (celle du chemin).
    """

    model_config = ConfigDict(extra="forbid")

    appartenance: uuid.UUID = Field(description="L'identifiant d'appartenance, dans l'entite")
    version: int = Field(ge=1, description="La version lue sur l'ANCIENNE appartenance")
    entite_destination: str = Field(
        min_length=1,
        max_length=LONGUEUR_MAXIMALE_CODE,
        description="Le `code` de l'entite d'arrivee",
    )
    date_d_arrivee: dt.date = Field(description="Dans l'entite d'arrivee — cahier §10.2")
    metier: uuid.UUID = Field(description="`job_catalog_id`, dans l'entite d'arrivee")
    statut: SituationProfessionnelle
    client: uuid.UUID | None = Field(default=None, description="`null` si `intercontract`")
    dsm: uuid.UUID | None = Field(default=None, description="La personne DSM, facultative")
    cercle_principal: uuid.UUID = Field(description="Dans l'entite d'arrivee")


class DemandeDeTransfertEnMasse(BaseModel):
    """Le lot complet — borne par `TAILLE_MAXIMALE_DU_LOT`, une sauvegarde
    d'ingenierie et non une regle metier (voir `app.people.transfert_masse`).
    """

    model_config = ConfigDict(extra="forbid")

    elements: list[ElementDeTransfertEnMasseRequete] = Field(
        min_length=1,
        max_length=TAILLE_MAXIMALE_DU_LOT,
        description="Un a cent elements — chacun traite dans son propre savepoint",
    )
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


class ResultatDeTransfertRendu(BaseModel):
    """Le sort d'UN element — jamais une exception qui emporterait les autres.

    Les six champs de succes et les deux champs d'echec sont tous facultatifs
    et MUTUELLEMENT exclusifs selon `succes` — meme discipline rendue que
    pour un refus individuel (§18.3), seulement porte PAR element plutot que
    par la reponse entiere.
    """

    appartenance: uuid.UUID
    succes: bool
    nouvelle_appartenance: uuid.UUID | None = None
    version: int | None = None
    etat_precedent: str | None = None
    sessions_revoquees: int | None = None
    liens_invalides: int | None = None
    relations_closes: dict[str, int] | None = None
    parcours_onboarding_archive: uuid.UUID | None = None
    code_erreur: str | None = None
    message_erreur: str | None = None


class ReponseDeTransfertEnMasse(BaseModel):
    """`total`/`reussites`/`echecs` sont DERIVES de `resultats`, jamais une
    seconde source qui pourrait diverger — meme principe que la reconciliation
    du rapport d'import (`T10`), une lecture fraiche plutot qu'un compteur.
    """

    resultats: list[ResultatDeTransfertRendu]
    total: int
    reussites: int
    echecs: int


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
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


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
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
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
    motif: str | None = Field(
        default=None,
        max_length=2000,
        description="Le motif du §18.1 — obligatoire pour `SUPER` (`ECART-064`).",
    )


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
    parcours_onboarding_archive: uuid.UUID | None = Field(
        description=(
            "LOT 7 `T11` : l'identifiant du parcours d'onboarding archive par ce "
            "depart, ou `null` si aucun parcours actif n'existait, ou si l'archivage "
            "vient d'une arrivee annulee (`future`) plutot que d'un depart."
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


class PeriodeMetierRendue(BaseModel):
    """Une affectation metier et sa periode — §6.4."""

    metier: str
    debut: dt.datetime
    fin: dt.datetime | None


class PeriodeStatutRendue(BaseModel):
    """Le statut ET son client : UNE SEULE periode, §6.5."""

    statut: str
    client: str | None
    debut: dt.datetime
    fin: dt.datetime | None


class PeriodeCercleRendue(BaseModel):
    """Une appartenance a un cercle, avec son type — §8.2."""

    code: str
    nom: str
    type: str
    debut: dt.datetime
    fin: dt.datetime | None


class PeriodeDsmRendue(BaseModel):
    """Un rattachement DSM et sa periode — §8.5."""

    dsm: str
    debut: dt.datetime
    fin: dt.datetime | None


class PeriodeResponsabiliteRendue(BaseModel):
    """Une responsabilite Framework et sa portee — §8.4."""

    type: str
    cercle: str | None
    bureau: str | None
    debut: dt.datetime
    fin: dt.datetime | None


class ReponseDeLHistorique(BaseModel):
    """Les cinq axes, dont un peut valoir `null`.

    **`null` ET `[]` NE DISENT PAS LA MEME CHOSE, ET C'EST LE POINT.** `[]`
    signifie « il n'y a rien a montrer » ; `null` signifie « ce n'est pas dans
    ton perimetre ». Les confondre ferait croire a un DSM que son consultant n'a
    jamais porte de responsabilite — une affirmation FAUSSE, et le §7.21 dit
    qu'un champ qui ment apprend a ne pas le lire.

    **La cle reste PRESENTE a `null` plutot qu'absente** : un consommateur qui
    doit tester l'existence d'une cle avant de la lire finit par se tromper, et
    c'est deja le parti du format d'erreur du §18.3.

    **Et ce n'est pas une fuite** : un axe `null` l'est pour TOUTES les cibles de
    ce role, jamais selon la cible. On n'apprend rien de la personne consultee.
    """

    metier: list[PeriodeMetierRendue] | None
    statut: list[PeriodeStatutRendue] | None
    cercle: list[PeriodeCercleRendue] | None
    dsm: list[PeriodeDsmRendue] | None
    responsabilites: list[PeriodeResponsabiliteRendue] | None


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
                    metier=ligne.metier,
                    statut=ligne.statut,
                    client=ligne.client,
                    cercle=(
                        None
                        if ligne.cercle is None
                        else CercleDeLaListeRendu(
                            code=ligne.cercle.code,
                            nom=ligne.cercle.nom,
                            jeton_de_couleur=ligne.cercle.jeton_de_couleur,
                        )
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
    #  **UNE TROISIEME GRILLE, ET LE DOCUMENT EN PORTE BIEN TROIS.** L'ecriture
    #  vient du §6.1, le cycle de vie de ses trois lignes d'archivage, et la
    #  lecture d'historique de la ligne « Audit » du §5 — qui refuse `EMP` et
    #  `NEW`, et ne donne rien a `OFFICE` sur une personne : le §6.2 l'ecrit, et
    #  AUCUNE table ne rattache un collaborateur a un bureau (`ECART-059`).
    garde_de_l_historique = exiger_un_role_dans_l_entite(parametres, ROLES_DE_L_HISTORIQUE)

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
                    "un client et un `intercontract` n'en accepte aucun (§30.5). "
                    "`aucun_modele_publie` : un changement de `statut` remplace le parcours "
                    "d'onboarding actif (`T10`, modele §6.5) et aucun modele publie ne "
                    "correspond au nouveau statut, pour cette entite, ce DSM ou ce cercle."
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
            "ecrasees : §23.4, et une contrainte d'exclusion par table le rend structurel.<br><br>"
            "**Un changement de `statut` (mission &harr; intercontrat) remplace automatiquement "
            "le parcours d'onboarding actif** (`T10`, modele §6.5) : l'ancienne instance passe "
            "`replaced`, une nouvelle est instanciee depuis le modele du nouveau statut, et les "
            "taches communes deja terminees sont conservees par reference stable. Un changement "
            "de `client` seul, meme statut, ne remplace rien."
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
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            modification = modifier_les_donnees_organisationnelles(
                connexion,
                entite=entite.id,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                demande=demandes,
                perimetre=perimetre,
                instant=instant,
                motif=demande.motif,
            )
        return ReponseDeModification(
            version=modification.version,
            champs_modifies=sorted(champ.value for champ in modification.champs),
        )

    @routeur.post(
        GABARIT_COLLECTION,
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeCreationDeCollaborateur,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role d'ecriture dans cette entite, ou un role "
                    "d'ecriture dont la proposition sort du perimetre -- un DSM qui designe "
                    "un AUTRE DSM, un Booster qui vise un cercle qui n'est pas le sien ou qui "
                    "tente d'assigner un DSM (meme exclusion que la modification)."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite inconnue ou non active. Meme forme que la lecture."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`valeur_refusee` : un statut `mission` exige un client, un "
                    "`intercontract` n'en accepte aucun (§30.5) ; ou le DSM designe n'a "
                    "pas de responsabilite DSM active dans cette entite."
                )
            },
        },
        summary="Creer manuellement un collaborateur",
        description=(
            "Matrice §6.1 « Creer manuellement un profil », cahier §10.2. Backlog "
            "`MVP-L09-US002` (1/2).<br><br>"
            "**Categorie professionnelle toujours `consultant`** : la categorie `dg` exige "
            "une action separee, non exposee par ce depot — voir l'en-tete de "
            "`app/people/creation.py`.<br><br>"
            "**Six champs organisationnels poses a la creation** : date d'arrivee, metier, "
            "statut, client, DSM (facultatif), cercle principal. Les modifier ensuite est "
            "`T3`, pas cette route."
        ),
    )
    def creer_le_profil(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        demande: DemandeDeCreationDeCollaborateur,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDeCreationDeCollaborateur:
        """Creer un collaborateur — matrice §6.1, cahier §10.2."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = resoudre_l_autorisation_de_creation(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                proposition=PropositionDeCreation(
                    circle_id=demande.cercle_principal,
                    dsm_person_id=demande.dsm,
                ),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            cree = creer_un_collaborateur(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                demande=DemandeDeCollaborateur(
                    email=demande.email,
                    first_name=demande.prenom,
                    last_name=demande.nom,
                    preferred_name=demande.nom_prefere,
                    appartenance=DemandeDAppartenance(
                        arrival_date=demande.date_d_arrivee,
                        job_catalog_id=demande.metier,
                        status=demande.statut,
                        client_id=demande.client,
                        dsm_person_id=demande.dsm,
                        circle_id=demande.cercle_principal,
                    ),
                ),
                instant=instant,
                motif=demande.motif,
            )
        return ReponseDeCreationDeCollaborateur(
            appartenance=cree.appartenance, version=cree.version
        )

    @routeur.post(
        GABARIT_CHANGEMENT_D_ENTITE,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeChangementDEntite,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : meme grille que la creation (`T2`), evaluee sur "
                    "L'ENTITE D'ARRIVEE — un DSM qui designe un AUTRE DSM, un Booster "
                    "hors de son cercle ou qui tente d'assigner un DSM."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite (depart ou arrivee) inconnue ou non active."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la fiche a change depuis votre lecture. "
                    "`etat_incompatible` : l'appartenance n'est ni `active` ni `future` — "
                    "on ne transfere pas un profil deja parti ou archive."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`valeur_refusee` : la biconditionnelle statut/client dans l'entite "
                    "d'arrivee, ou le DSM designe sans responsabilite DSM active la-bas."
                )
            },
        },
        summary="Changer un collaborateur d'entite",
        description=(
            "Cahier §11.1, §16.3 : « le changement d'entite cloture l'ancienne "
            "appartenance et les responsabilites incompatibles », operation ATOMIQUE. "
            "Backlog `MVP-L09-US002` (2/2).<br><br>"
            "**MEME PERIMETRE QUE LA CREATION (`T2`)**, evalue sur l'entite d'ARRIVEE : "
            "un DSM ne transfere que vers SON propre perimetre de consultants, un "
            "Booster que dans SON cercle et sans DSM.<br><br>"
            "**L'ANCIENNE APPARTENANCE VA JUSQU'A `archived`** — `Active --> Departed "
            "--> Archived`, ou `Future --> Archived` seul — et TOUTES les sessions et "
            "liens magiques de la personne sont revoques, meme moteur que le depart "
            "(arbitrage de Jonathan du 08/10/2026). Une nouvelle fiche d'arrivee devra "
            "etre completee dans l'entite d'arrivee."
        ),
    )
    def changer_l_entite(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[
            uuid.UUID, Path(description="L'identifiant d'appartenance, rendu par la fiche")
        ],
        demande: DemandeDeChangementDEntite,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDeChangementDEntite:
        """Changer un collaborateur d'entite — cahier §11.1, §16.3."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_source = resoudre_une_entite_active(connexion, code)
            entite_destination = resoudre_une_entite_active(connexion, demande.entite_destination)
            if entite_source is None or entite_destination is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(
                connexion, appelant.personne, entite_destination.id, instant
            )
            autorise = resoudre_l_autorisation_de_creation(
                connexion,
                entite=entite_destination.id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                proposition=PropositionDeCreation(
                    circle_id=demande.cercle_principal,
                    dsm_person_id=demande.dsm,
                ),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            transfert = changer_d_entite(
                connexion,
                entite_source=entite_source.id,
                entite_destination=entite_destination.id,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                demande=DemandeDAppartenance(
                    arrival_date=demande.date_d_arrivee,
                    job_catalog_id=demande.metier,
                    status=demande.statut,
                    client_id=demande.client,
                    dsm_person_id=demande.dsm,
                    circle_id=demande.cercle_principal,
                ),
                instant=instant,
                motif=demande.motif,
            )
        return ReponseDeChangementDEntite(
            nouvelle_appartenance=transfert.nouvelle_appartenance,
            version=transfert.version,
            etat_precedent=transfert.etat_precedent,
            sessions_revoquees=transfert.sessions_revoquees,
            liens_invalides=transfert.liens_invalides,
            relations_closes=transfert.relations_closes,
            parcours_onboarding_archive=transfert.parcours_onboarding_archive,
        )

    def _elements_du_lot(
        demande: DemandeDeTransfertEnMasse,
    ) -> tuple[ElementDuTransfertEnMasse, ...]:
        return tuple(
            ElementDuTransfertEnMasse(
                appartenance=element.appartenance,
                entite_destination_code=element.entite_destination,
                version_attendue=element.version,
                circle_id=element.cercle_principal,
                dsm_person_id=element.dsm,
                demande=DemandeDAppartenance(
                    arrival_date=element.date_d_arrivee,
                    job_catalog_id=element.metier,
                    status=element.statut,
                    client_id=element.client,
                    dsm_person_id=element.dsm,
                    circle_id=element.cercle_principal,
                ),
            )
            for element in demande.elements
        )

    def _resultat_rendu(resultat: ResultatDUnTransfert) -> ResultatDeTransfertRendu:
        transfert = resultat.transfert
        return ResultatDeTransfertRendu(
            appartenance=resultat.appartenance,
            succes=resultat.succes,
            nouvelle_appartenance=transfert.nouvelle_appartenance if transfert else None,
            version=transfert.version if transfert else None,
            etat_precedent=transfert.etat_precedent if transfert else None,
            sessions_revoquees=transfert.sessions_revoquees if transfert else None,
            liens_invalides=transfert.liens_invalides if transfert else None,
            relations_closes=transfert.relations_closes if transfert else None,
            parcours_onboarding_archive=transfert.parcours_onboarding_archive
            if transfert
            else None,
            code_erreur=resultat.code_erreur,
            message_erreur=resultat.message_erreur,
        )

    def _reponse_du_lot(
        resultats: tuple[ResultatDUnTransfert, ...],
    ) -> ReponseDeTransfertEnMasse:
        rendus = [_resultat_rendu(resultat) for resultat in resultats]
        reussites = sum(1 for rendu in rendus if rendu.succes)
        return ReponseDeTransfertEnMasse(
            resultats=rendus,
            total=len(rendus),
            reussites=reussites,
            echecs=len(rendus) - reussites,
        )

    _REPONSES_DU_TRANSFERT_EN_MASSE: dict[int | str, dict[str, Any]] = {
        status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
        status.HTTP_403_FORBIDDEN: {
            "description": (
                "`acces_refuse` : aucun role d'ecriture dans l'entite SOURCE (chemin). "
                "Un refus par ELEMENT (destination hors perimetre) est RAPPORTE dans le "
                "corps, jamais leve ici."
            )
        },
        status.HTTP_404_NOT_FOUND: {"description": "Entite source inconnue ou non active."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Lot vide ou de plus de cent elements, ou un element mal forme."
        },
    }

    @routeur.post(
        GABARIT_TRANSFERT_EN_MASSE_APERCU,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTransfertEnMasse,
        responses=_REPONSES_DU_TRANSFERT_EN_MASSE,
        summary="Previsualiser un transfert en masse",
        description=(
            "Backlog `MVP-L09-US003` : « la previsualisation indique l'impact ». "
            "Execute EXACTEMENT le meme chemin que l'execution reelle — meme "
            "permission par element, meme appel a `changer_d_entite` — dans un "
            "savepoint TOUJOURS annule : rien n'est jamais ecrit par cet appel, "
            "succes ou echec. L'impact rendu (sessions revoquees, liens invalides, "
            "relations closes) est donc le resultat REEL, jamais une estimation."
        ),
    )
    def previsualiser_le_transfert_en_masse(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        demande: DemandeDeTransfertEnMasse,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDeTransfertEnMasse:
        """Previsualiser un transfert en masse — `US003`, aucune ecriture durable."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_source = resoudre_une_entite_active(connexion, code)
            if entite_source is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(
                connexion, appelant.personne, entite_source.id, instant
            )
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            resultats = executer_le_transfert_en_masse(
                connexion,
                entite_source=entite_source.id,
                acteur=appelant.personne,
                elements=_elements_du_lot(demande),
                instant=instant,
                mode="apercu",
                motif=demande.motif,
            )
        return _reponse_du_lot(resultats)

    @routeur.post(
        GABARIT_TRANSFERT_EN_MASSE,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTransfertEnMasse,
        responses=_REPONSES_DU_TRANSFERT_EN_MASSE,
        summary="Executer un transfert en masse",
        description=(
            "Backlog `MVP-L09-US003` : « les operations sont idempotentes […] les "
            "erreurs partielles sont explicites ». Chaque element dans son PROPRE "
            "savepoint (`app.imports.execution`, `T9`) : un refus n'affecte aucun "
            "autre element, et la reponse rapporte CHAQUE sort individuellement.<br>"
            "<br>**IDEMPOTENT SANS MECANISME NOUVEAU** (cahier §18.6) : rejouer le "
            "MEME lot refuse chaque element deja transfere en `409` "
            "(`etat_incompatible`), explicite, jamais rejoue ni ecrase."
        ),
    )
    def executer_le_transfert_en_masse_route(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        demande: DemandeDeTransfertEnMasse,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDeTransfertEnMasse:
        """Executer un transfert en masse — `US003`."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_source = resoudre_une_entite_active(connexion, code)
            if entite_source is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(
                connexion, appelant.personne, entite_source.id, instant
            )
            exiger_un_motif_si_necessaire(frozenset(permissions.roles), demande.motif)
            resultats = executer_le_transfert_en_masse(
                connexion,
                entite_source=entite_source.id,
                acteur=appelant.personne,
                elements=_elements_du_lot(demande),
                instant=instant,
                mode="execution",
                motif=demande.motif,
            )
        return _reponse_du_lot(resultats)

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
            entite, perimetre, roles = _resoudre_le_cycle(
                connexion, code=code, appelant=appelant, cible=appartenance, instant=instant
            )
            exiger_un_motif_si_necessaire(roles, demande.motif)
            archivage = archiver_un_profil(
                connexion,
                entite=entite,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                perimetre=perimetre,
                instant=instant,
                date_de_depart=demande.date_de_depart,
                motif=demande.motif,
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
            parcours_onboarding_archive=archivage.parcours_onboarding_archive,
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
            entite, perimetre, roles = _resoudre_le_cycle(
                connexion, code=code, appelant=appelant, cible=appartenance, instant=instant
            )
            exiger_un_motif_si_necessaire(roles, demande.motif)
            restauration = restaurer_un_profil(
                connexion,
                entite=entite,
                cible=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                perimetre=perimetre,
                instant=instant,
                motif=demande.motif,
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
            entite, perimetre, _roles = _resoudre_le_cycle(
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

    # -------------------------------------------------------------------
    #  L'HISTORIQUE ORGANISATIONNEL — LOT 5, `T9`, story `MVP-L05-US008`
    # -------------------------------------------------------------------

    @routeur.get(
        GABARIT_HISTORIQUE,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLHistorique,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "L'appelant ne porte AUCUN role de lecture d'historique dans cette "
                    "entite. C'est le cas d'`EMP`, de `NEW` et du responsable de bureau "
                    "— la ligne « Audit » du §5 les met a tiret, et le §6.2 ecrit qu'un "
                    "responsable de bureau « n'obtient aucun droit general sur les "
                    "profils du seul fait de sa responsabilite de bureau »."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour QUATRE causes : code inconnu ou entite non "
                    "active, appartenance inexistante, appartenance d'une AUTRE entite, "
                    "ou cible hors du perimetre de l'appelant — un DSM qui n'est pas "
                    "celui de ce consultant, un Booster dont ce n'est pas le cercle "
                    "principal. Distinguer apprendrait de qui l'on n'est pas responsable."
                )
            },
        },
        summary="Consulter l'historique organisationnel d'un collaborateur",
        description=(
            "Les periodes de metier, de statut et client, de cercle, de DSM et de "
            "responsabilites — backlog `MVP-L05-US008`.<br><br>"
            "**AUCUN AUDIT TECHNIQUE N'EST EXPOSE, ET C'EST STRUCTUREL** : aucune "
            "requete ne touche `auth_event`, et aucune periode rendue n'a de champ qui "
            "puisse porter `created_by_person_id`, `updated_by_person_id`, "
            "`assigned_by_person_id`, `version`, `created_at` ou `updated_at`. Le §16.2 "
            "enumere ce qu'aucun role ne peut consulter depuis l'audit : rien de tout "
            "cela ne vit dans les tables lues ici.<br><br>"
            "**QUI LIT QUOI — la ligne « Audit » du §5**, qui refuse `EMP` et `NEW` : un "
            "DSM lit l'historique de SES consultants, un Booster celui des membres "
            "PRINCIPAUX de son cercle, l'ESM et l'administrateur d'entite celui de "
            "l'entite, le super-administrateur partout.<br><br>"
            "**L'AXE DES RESPONSABILITES EST PLUS FERME**, et le §20 le dit a part : "
            "« Consulter l'historique des roles | ESM | ADM-E | SUPER ». Le §23.2 "
            "tranche — une interdiction liee a la ressource prevaut sur le cumul — donc "
            "cet axe vaut `null` pour un DSM et pour un Booster. `null` n'est PAS `[]` : "
            "le premier dit « hors perimetre », le second « rien a montrer ».<br><br>"
            "**AUCUNE GRILLE D'ETAT** : un profil `departed` ou `archived` a justement "
            "l'historique le plus interessant, et exiger un etat occupant le rendrait "
            "inaccessible au moment ou il sert."
        ),
    )
    def consulter_l_historique(
        code: Annotated[
            str,
            Path(min_length=1, max_length=LONGUEUR_MAXIMALE_CODE, description="Le `code`"),
        ],
        appartenance: Annotated[
            uuid.UUID, Path(description="L'identifiant d'appartenance, rendu par la fiche")
        ],
        appelant: SessionEtablie = Depends(garde_de_l_historique),  # noqa: B008
    ) -> ReponseDeLHistorique:
        """Consulter l'historique organisationnel — matrice §5 et §20."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  Les permissions sont resolues DANS cette transaction, comme en `T7`
            #  et `T8` : la garde a resolu les siennes dans sa propre connexion et
            #  a son propre instant.
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            acces = resoudre_l_acces_a_l_historique(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible=appartenance,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            #  **UN ACCES VIDE REND 404, ET NON 403.** La garde a deja rendu 403 si
            #  l'appelant ne porte aucun role d'historique. Arriver ici avec un
            #  ensemble vide veut dire que la CIBLE est hors de sa portee — ou
            #  qu'elle n'existe pas. Les deux rendent la meme forme : distinguer
            #  apprendrait a un DSM de qui il n'est pas responsable.
            if not acces.axes:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            historique = lire_l_historique(
                connexion,
                entite=entite.id,
                cible=appartenance,
                acces=acces,
                instant=instant,
            )
        if historique is None:  # pragma: no cover — course : la cible a disparu entre-temps
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        return _historique_en_reponse(historique)

    @routeur.get(
        "/entities/{code}/job-catalog",
        #  **`dependencies=` et non `Annotated[...]`** : meme piege mesure dans
        #  `app/organization/routes.py` (le Framework). Aucun role n'est
        #  distingue : une session etablie suffit, meme regime que les autres
        #  lectures de reference (Framework, cercle, bureau).
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuCatalogueDesMetiers,
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
                    "l'entite existe sans etre active."
                )
            },
        },
        summary="Le catalogue des metiers configurables de l'entite",
        description=(
            "Les metiers ACTIFS et non archives — modele §6.3. Pose en "
            "construisant l'ecran back-office (`T14`) : `job_catalog_id` est "
            "obligatoire a la creation d'un collaborateur et au changement "
            "d'entite depuis l'ouverture du lot, et aucune route n'en servait "
            "la liste jusque-la."
        ),
    )
    def lire_le_catalogue_des_metiers(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
    ) -> ReponseDuCatalogueDesMetiers:
        """Le catalogue des metiers d'une entite, en lecture — LOT 9 `T14`."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            metiers = lister_le_catalogue_des_metiers(connexion, entite=entite.id)
        return ReponseDuCatalogueDesMetiers(
            metiers=[
                MetierRendu(identifiant=m.identifiant, code=m.code, label=m.label) for m in metiers
            ]
        )

    return routeur


def _historique_en_reponse(historique: HistoriqueOrganisationnel) -> ReponseDeLHistorique:
    """Traduire les structures du service en modeles de reponse.

    **UN AXE `None` RESTE `None`**, jamais `[]` : c'est toute la distinction que
    `ReponseDeLHistorique` porte, et l'ecraser ici la perdrait en silence.
    """
    return ReponseDeLHistorique(
        metier=None
        if historique.metier is None
        else [
            PeriodeMetierRendue(metier=p.metier, debut=p.debut, fin=p.fin)
            for p in historique.metier
        ],
        statut=None
        if historique.statut is None
        else [
            PeriodeStatutRendue(statut=p.statut, client=p.client, debut=p.debut, fin=p.fin)
            for p in historique.statut
        ],
        cercle=None
        if historique.cercle is None
        else [
            PeriodeCercleRendue(code=p.code, nom=p.nom, type=p.type, debut=p.debut, fin=p.fin)
            for p in historique.cercle
        ],
        dsm=None
        if historique.dsm is None
        else [PeriodeDsmRendue(dsm=p.dsm, debut=p.debut, fin=p.fin) for p in historique.dsm],
        responsabilites=None
        if historique.responsabilites is None
        else [
            PeriodeResponsabiliteRendue(
                type=p.type, cercle=p.cercle, bureau=p.bureau, debut=p.debut, fin=p.fin
            )
            for p in historique.responsabilites
        ],
    )


def _resoudre_le_cycle(
    connexion: Connection,
    *,
    code: str,
    appelant: SessionEtablie,
    cible: uuid.UUID,
    instant: dt.datetime,
) -> tuple[uuid.UUID, PerimetreDuCycleDeVie, frozenset[RoleDeLaMatrice]]:
    """L'entite active, le perimetre de cycle de vie, et les ROLES — en UN exemplaire.

    **LES TROIS ROUTES DE `T8` PARTAGENT CE PROLOGUE**, et l'ecrire trois fois
    donnerait trois regles pour une seule -- `DEC-466`, `ECART-022`. Le jour ou le
    §6.1 gagnerait une quatrieme ligne de cycle de vie, il n'y aurait qu'un
    endroit a lire.

    **LES PERMISSIONS SONT RESOLUES DANS CETTE TRANSACTION**, et non reprises de
    la garde de role : celle-ci a resolu les siennes dans sa propre connexion et
    a son propre instant. Ce n'est pas une seconde copie de la regle, c'est le
    meme appel au bon instant -- exactement le parti de `T7`.

    Les roles sont rendus en plus depuis LOT 10 `T7` : `SUPER_ADMINISTRATEUR`
    fait toujours partie de `ROLES_DU_CYCLE_DE_VIE`, donc le controle du motif
    (`ECART-064`) n'a besoin que de l'ensemble COMPLET, jamais d'une seconde
    intersection.
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
    return entite.id, perimetre, frozenset(permissions.roles)


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
        version=fiche.version,
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
