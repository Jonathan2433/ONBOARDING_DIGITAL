"""Les routes de l'onboarding — LOT 7, `T2`/`T3` (fiche), `T4` (catalogue), `T5`
(modeles), `T6` (cycle de vie d'une version).

Montee sous `/entities/{code}/people/{appartenance}/arrival-profile`, a cote
des routes de `app.people.routes` dont elle reutilise la resolution d'entite
et le gabarit de 404 unique — un chemin distinct pour « code d'entite inconnu »
apprendrait qu'une appartenance existe, l'exact defaut que ce projet refuse
depuis le LOT 4.

`T3` AJOUTE DEUX ECRITURES, `LECTURE` PUIS `PERMISSION` DANS LA MEME TRANSACTION

  Les deux routes d'ecriture relisent la fiche et resolvent les permissions
  dans LEUR PROPRE transaction, jamais celle d'un appel anterieur — meme
  discipline que `modifier_le_profil` (LOT 5, `T7`) : une garde perimee
  autoriserait une ecriture sur un etat qui a change entre-temps.

`T4` AJOUTE LE CATALOGUE DES TACHES, SOUS `/entities/{code}/onboarding/task-references`

  Contrairement a la fiche d'arrivee, le permis ne depend ici d'AUCUNE cible
  precise — matrice §9, une simple appartenance de role dans l'entite (voir
  `perimetre.py`). Les deux routes emploient donc `exiger_un_role_dans_l_entite`,
  la garde generique posee au LOT 4 pour exactement ce cas, plutot que de
  reecrire une resolution manuelle comme `T2`/`T3` le font pour la fiche
  (ou `Soi` et le rattachement DSM/Booster exigent une cible).

`T5` AJOUTE LES MODELES ET LEURS VERSIONS, SOUS `/entities/{code}/onboarding/templates`

  **MEME GARDE GENERIQUE QU'AU `T4`**, mais le permis FIN ne s'arrete pas a la
  garde : `onboarding_template` porte de vraies colonnes de portee
  (`scope_person_id`, `scope_circle_id`), et `peut_gerer_un_modele_de_cette_
  portee` (`perimetre.py`) doit lire la BASE pour verifier qu'un DSM agit sur
  SES consultants, ou qu'un Booster agit sur SON cercle — jamais une simple
  appartenance de role, contrairement au catalogue de `T4`.

  **TROIS ROUTES, LA MEME GARDE, DEUX RESOLUTIONS DE PORTEE DIFFERENTES** :
  creer un modele resout la portee DECLAREE par la demande ; creer une
  version ou y composer des taches resout la portee DEJA ECRITE du modele
  EXISTANT, lu en base — jamais celle que l'appelant pretendrait avoir.

`T6` AJOUTE LE CYCLE DE VIE D'UNE VERSION — PUBLIER, ARCHIVER, RESTAURER

  Publier et archiver reutilisent `garde_des_modeles` et `peut_gerer_un_
  modele_de_cette_portee`, EXACTEMENT comme les trois routes de `T5` — meme
  grille du §9. **Restaurer emploie une garde SEPAREE, `garde_de_
  restauration`** : DSM et BOOSTER y sont exclus DES LA GARDE COARSE, jamais
  seulement au permis fin, parce que la matrice les met a TIRET en bloc sur
  cette ligne precise — pas de sous-cas « son propre modele » comme ailleurs.
  Voir `app/onboarding/cycle_de_vie.py` pour les trois transitions et la
  resolution d'`ECART-066`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Final, Literal

from fastapi import APIRouter, Depends, Path, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Connection

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.configuration.settings import Parametres
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.onboarding.catalogue import (
    TacheDeReference,
    creer_une_tache_de_reference,
    lire_le_catalogue_de_taches,
)
from app.onboarding.cycle_de_vie import (
    VersionArchivee,
    VersionPubliee,
    VersionRestauree,
    archiver_une_version,
    publier_une_version,
    restaurer_une_version,
)
from app.onboarding.ecriture import completer_la_fiche_arrivee, valider_et_publier_la_fiche_arrivee
from app.onboarding.fiche_arrivee import FicheArrivee, lire_la_fiche_arrivee
from app.onboarding.gabarits import (
    CODE_MODELE_INTROUVABLE,
    CODE_PORTEE_INCOHERENTE,
    CODE_VERSION_INTROUVABLE,
    MESSAGE_MODELE_INTROUVABLE,
    MESSAGE_PORTEE_INCOHERENTE,
    MESSAGE_VERSION_INTROUVABLE,
    Modele,
    NouvelleTacheDeVersion,
    TacheDeVersion,
    VersionDeModele,
    creer_un_modele,
    creer_une_version,
    definir_les_taches_de_la_version,
    lire_un_modele,
    lire_une_version,
)
from app.onboarding.perimetre import (
    ROLES_DE_GESTION_DES_MODELES,
    ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES,
    ROLES_DE_RESTAURATION_DES_MODELES,
    peut_completer_la_fiche_arrivee,
    peut_corriger_la_fiche_arrivee_apres_publication,
    peut_creer_une_tache_de_reference_globale,
    peut_gerer_un_modele_de_cette_portee,
    peut_lire_la_fiche_arrivee,
    peut_restaurer_une_version_de_modele,
    peut_valider_et_publier_la_fiche_arrivee,
)
from app.permissions.dependances import (
    CODE_ROLE_REFUSE,
    MESSAGE_ROLE_REFUSE,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

CODE_FICHE_HORS_PERIMETRE: Final = "fiche_arrivee_hors_perimetre"
MESSAGE_FICHE_HORS_PERIMETRE: Final = "Votre perimetre ne vous permet pas de consulter cette fiche."
MESSAGE_FICHE_HORS_PERIMETRE_ECRITURE: Final = (
    "Votre perimetre ne vous permet pas de modifier cette fiche."
)


class CercleDeLaFicheArrivee(BaseModel):
    """Le cercle principal, s'il existe — §10.2, reutilise depuis `T2`."""

    code: str
    nom: str
    jeton_de_couleur: str | None


class FicheDArrivee(BaseModel):
    """La fiche d'arrivee — modele §12.1, donnees organisationnelles du §10.2.

    `id` et `version` valent `None` tant qu'aucune ligne `arrival_profile`
    n'existe : c'est `T3` qui la cree. Un client qui les recoit nuls sait qu'il
    doit CREER, pas mettre a jour.
    """

    id: uuid.UUID | None
    version: int | None
    state: str
    entity_membership_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    arrival_date: dt.date
    metier: str | None
    statut: str | None
    client: str | None
    dsm: str | None
    cercle_principal: CercleDeLaFicheArrivee | None
    short_intro: str | None
    fun_fact: str | None
    validated_at: dt.datetime | None
    published_at: dt.datetime | None
    recent_until: dt.date | None


class DemandeDeCompletion(BaseModel):
    """Les deux champs propres de la fiche, tous FACULTATIFS — matrice §7.

    `version` a `None` signifie « aucune ligne n'existe encore d'apres ma
    derniere lecture » — c'est exactement ce que la lecture rend tant que
    personne n'a rien ecrit. Une version presente exige la ligne existante et
    sa version exacte (§18.4).

    `extra="forbid"` : `photo_media_id` N'EST PAS ICI. Aucune route d'upload ni
    d'autorisation de media n'existe encore — l'accepter en silence ferait
    croire a un client qu'il peut deja attacher une photo par cette route.
    """

    model_config = ConfigDict(extra="forbid")

    version: int | None = Field(
        default=None,
        ge=1,
        description="La version lue. `null` si `id`/`version` valaient `null` a la lecture.",
    )
    short_intro: str | None = Field(default=None, description="Presentation courte — modele §12.1")
    fun_fact: str | None = Field(default=None, description="Facultatif — modele §12.1")


class ReponseDeCompletion(BaseModel):
    """Ce que la completion rend : l'identite de la ligne et sa version."""

    id: uuid.UUID
    version: int
    state: str


class DemandeDeValidation(BaseModel):
    """La seule chose que « Valider et publier » demande : la version lue."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, description="La version lue sur la fiche — cahier §18.4.")


class ReponseDeValidation(BaseModel):
    """Ce que la validation rend : l'etat nouveau et les trois marqueurs ecrits."""

    id: uuid.UUID
    version: int
    state: str
    validated_at: dt.datetime
    published_at: dt.datetime
    recent_until: dt.date


def _champs_presents(demande: DemandeDeCompletion) -> dict[str, str | None]:
    """Les champs REELLEMENT envoyes, jamais leurs valeurs par defaut.

    `model_fields_set` distingue « absent » de « envoye a `null` » — un fun
    fact qu'on retire explicitement n'est pas la meme demande qu'un corps qui
    ne touche pas au fun fact. Meme discipline que `people/routes.py::
    _lire_la_demande`.
    """
    return {
        champ: getattr(demande, champ)
        for champ in ("short_intro", "fun_fact")
        if champ in demande.model_fields_set
    }


def _en_reponse(fiche: FicheArrivee) -> FicheDArrivee:
    return FicheDArrivee(
        id=fiche.id,
        version=fiche.version,
        state=fiche.state,
        entity_membership_id=fiche.entity_membership_id,
        person_id=fiche.person_id,
        first_name=fiche.first_name,
        last_name=fiche.last_name,
        preferred_name=fiche.preferred_name,
        arrival_date=fiche.arrival_date,
        metier=fiche.metier,
        statut=fiche.statut,
        client=fiche.client,
        dsm=fiche.dsm,
        cercle_principal=(
            None
            if fiche.cercle_principal is None
            else CercleDeLaFicheArrivee(
                code=fiche.cercle_principal.code,
                nom=fiche.cercle_principal.nom,
                jeton_de_couleur=fiche.cercle_principal.jeton_de_couleur,
            )
        ),
        short_intro=fiche.short_intro,
        fun_fact=fiche.fun_fact,
        validated_at=fiche.validated_at,
        published_at=fiche.published_at,
        recent_until=fiche.recent_until,
    )


class DemandeDeTacheDeReference(BaseModel):
    """Creer une tache de reference — matrice §9 « Creer une tache de reference »."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=1,
        max_length=64,
        description="Identifiant fonctionnel STABLE — modele §13.1. Ferme `ECART-013`.",
    )
    title: str = Field(min_length=1, description="Libelle — modele §13.1")
    description: str | None = Field(
        default=None, description="Instructions affichees au nouvel arrivant, facultatif"
    )
    category: str | None = Field(
        default=None, max_length=64, description="Categorie d'affichage, facultative"
    )
    portee: Literal["ENTITE", "GLOBAL"] = Field(
        default="ENTITE",
        description=(
            "`ENTITE` (par defaut) : une tache propre a l'entite du chemin — DSM, ESM, "
            "BOOST, ADM-E ou SUPER. `GLOBAL` : une tache reutilisable par TOUTE entite "
            "(`entity_id` NULL, modele §13.1) — reservee a SUPER, matrice §9."
        ),
    )


class ReponseDeTacheDeReference(BaseModel):
    """Une ligne du catalogue, telle que servie — modele §13.1."""

    id: uuid.UUID
    entity_id: uuid.UUID | None
    code: str
    title: str
    description: str | None
    category: str | None
    active: bool


class ReponseDuCatalogueDeTaches(BaseModel):
    """La liste, et son compte — §7.20, rapporter plutot que taire."""

    taches: list[ReponseDeTacheDeReference]
    nombre_de_taches: int


def _tache_en_reponse(tache: TacheDeReference) -> ReponseDeTacheDeReference:
    return ReponseDeTacheDeReference(
        id=tache.id,
        entity_id=tache.entity_id,
        code=tache.code,
        title=tache.title,
        description=tache.description,
        category=tache.category,
        active=tache.active,
    )


class DemandeDeModele(BaseModel):
    """Creer un modele — matrice §9 « Creer un modele », modele §13.2."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Nom du modele — modele §13.2")
    target_status: Literal["mission", "intercontract"] = Field(
        description="Le statut professionnel cible — modele §13.2, §6.5"
    )
    portee: Literal["GLOBAL", "ENTITY", "DSM", "CIRCLE"] = Field(
        description=(
            "`scope_type` — modele §13.2. `DSM` exige `scope_person_id` (et lui seul), "
            "`CIRCLE` exige `scope_circle_id` (et lui seul), `ENTITY`/`GLOBAL` n'exigent "
            "ni l'un ni l'autre."
        )
    )
    scope_person_id: uuid.UUID | None = Field(
        default=None, description="Le DSM concerne — requis SEULEMENT si `portee: DSM`"
    )
    scope_circle_id: uuid.UUID | None = Field(
        default=None, description="Le cercle concerne — requis SEULEMENT si `portee: CIRCLE`"
    )


class ReponseDeModele(BaseModel):
    """Le conteneur, tel que cree — modele §13.2."""

    id: uuid.UUID
    entity_id: uuid.UUID | None
    name: str
    target_status: str
    scope_type: str
    scope_person_id: uuid.UUID | None
    scope_circle_id: uuid.UUID | None
    state: str


class DemandeDeVersion(BaseModel):
    """Creer une nouvelle version brouillon — matrice §9, modele §13.3."""

    model_config = ConfigDict(extra="forbid")

    change_summary: str | None = Field(default=None, description="Resume du changement, facultatif")


class ReponseDeVersion(BaseModel):
    """La version, telle que creee — modele §13.3."""

    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    state: str
    change_summary: str | None


class DemandeDeTacheDeVersion(BaseModel):
    """Une ligne de la liste — modele §13.4. `display_order` n'est PAS ici :
    il vaut l'INDEX de cette ligne dans la liste recue, jamais un rang saisi.
    """

    model_config = ConfigDict(extra="forbid")

    task_reference_id: uuid.UUID = Field(description="La tache de reference reutilisee")
    required: bool = Field(default=True, description="Obligatoire ou facultative — modele §13.4")
    due_offset_days: int = Field(ge=0, description="Echeance relative a l'arrivee, en jours")
    title_override: str | None = Field(
        default=None, description="Libelle de remplacement, facultatif"
    )
    description_override: str | None = Field(
        default=None, description="Instructions de remplacement, facultatives"
    )


class DemandeDesTachesDeVersion(BaseModel):
    """La liste ENTIERE des taches d'une version — matrice §9 « Ajouter ou
    reordonner des taches », UNE seule ligne pour les deux gestes."""

    model_config = ConfigDict(extra="forbid")

    taches: list[DemandeDeTacheDeVersion]


class ReponseDeTacheDeVersion(BaseModel):
    """Une ligne, telle qu'ecrite — modele §13.4."""

    id: uuid.UUID
    task_reference_id: uuid.UUID
    display_order: int
    required: bool
    due_offset_days: int
    title_override: str | None
    description_override: str | None


class ReponseDesTachesDeVersion(BaseModel):
    """La liste et son compte — §7.20, rapporter plutot que taire."""

    taches: list[ReponseDeTacheDeVersion]
    nombre_de_taches: int


def _modele_en_reponse(modele: Modele) -> ReponseDeModele:
    return ReponseDeModele(
        id=modele.id,
        entity_id=modele.entity_id,
        name=modele.name,
        target_status=modele.target_status,
        scope_type=modele.scope_type,
        scope_person_id=modele.scope_person_id,
        scope_circle_id=modele.scope_circle_id,
        state=modele.state,
    )


def _version_en_reponse(version: VersionDeModele) -> ReponseDeVersion:
    return ReponseDeVersion(
        id=version.id,
        template_id=version.template_id,
        version_number=version.version_number,
        state=version.state,
        change_summary=version.change_summary,
    )


def _tache_de_version_en_reponse(tache: TacheDeVersion) -> ReponseDeTacheDeVersion:
    return ReponseDeTacheDeVersion(
        id=tache.id,
        task_reference_id=tache.task_reference_id,
        display_order=tache.display_order,
        required=tache.required,
        due_offset_days=tache.due_offset_days,
        title_override=tache.title_override,
        description_override=tache.description_override,
    )


class ReponseDePublicationDeVersion(BaseModel):
    """Ce qu'une publication a produit — modele §13.3, `T6`."""

    id: uuid.UUID
    version_number: int
    state: str
    published_at: dt.datetime
    published_by_person_id: uuid.UUID


class ReponseDArchivageDeVersion(BaseModel):
    """Ce qu'un archivage a produit — pas d'instant ni d'acteur, voir
    `cycle_de_vie.py`."""

    id: uuid.UUID
    version_number: int
    state: str


class ReponseDeRestaurationDeVersion(BaseModel):
    """Ce qu'une restauration a produit — `state` revient a `published`,
    JAMAIS a `draft`. Voir `cycle_de_vie.py`."""

    id: uuid.UUID
    version_number: int
    state: str
    published_at: dt.datetime | None
    published_by_person_id: uuid.UUID | None


def _publication_en_reponse(version: VersionPubliee) -> ReponseDePublicationDeVersion:
    return ReponseDePublicationDeVersion(
        id=version.id,
        version_number=version.version_number,
        state=version.state,
        published_at=version.published_at,
        published_by_person_id=version.published_by_person_id,
    )


def _archivage_en_reponse(version: VersionArchivee) -> ReponseDArchivageDeVersion:
    return ReponseDArchivageDeVersion(
        id=version.id, version_number=version.version_number, state=version.state
    )


def _restauration_en_reponse(version: VersionRestauree) -> ReponseDeRestaurationDeVersion:
    return ReponseDeRestaurationDeVersion(
        id=version.id,
        version_number=version.version_number,
        state=version.state,
        published_at=version.published_at,
        published_by_person_id=version.published_by_person_id,
    )


def _verifier_coherence_de_la_portee(demande: DemandeDeModele) -> None:
    """Le PLANCHER, avant que la contrainte `colonnes_de_portee_selon_scope_type`
    (migration `0020`) ne le refuse en 500 — meme parti a deux etages que
    `content/liens.py` : la contrainte est ce que nul ne contourne, ce refus
    est le message EXACT, en 422."""
    if demande.portee == "DSM":
        coherente = demande.scope_person_id is not None and demande.scope_circle_id is None
    elif demande.portee == "CIRCLE":
        coherente = demande.scope_circle_id is not None and demande.scope_person_id is None
    else:
        coherente = demande.scope_person_id is None and demande.scope_circle_id is None
    if not coherente:
        raise ErreurApplicative(
            code=CODE_PORTEE_INCOHERENTE,
            message=MESSAGE_PORTEE_INCOHERENTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


def routeur_onboarding(parametres: Parametres) -> APIRouter:
    """Routeur de l'onboarding, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["onboarding"])

    @routeur.get(
        "/entities/{code}/people/{appartenance}/arrival-profile",
        status_code=status.HTTP_200_OK,
        response_model=FicheDArrivee,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Le perimetre de lecture du §7 ne couvre pas cette fiche : ni "
                    "SOI, ni ESM/ADM-E/SUPER dans l'entite, ni Booster du cercle "
                    "de la cible. `DSM` est a TIRET sur CETTE ligne du §7, malgre "
                    "« Consultants » ailleurs dans la matrice."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour trois causes : code d'entite inconnu, "
                    "appartenance inconnue ou d'une AUTRE entite, ou appartenance "
                    "ni FUTURE ni ACTIVE."
                )
            },
        },
        summary="Consulter la fiche d'arrivee d'un collaborateur",
        description=(
            "Donnees organisationnelles preremplies — arrivee, metier, statut, DSM, "
            "client, cercle principal, cahier §9.4 — et champs propres a la fiche "
            "— etat, presentation, fun fact, modele §12.1. Aucune ligne "
            "`arrival_profile` n'est creee par cette lecture : `id`/`version` "
            "valent `null` tant qu'elle n'existe pas."
        ),
    )
    def lire_la_fiche(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite, unique et jamais reattribue",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> FicheDArrivee:
        """Consulter la fiche d'arrivee — cahier §9.4, modele §12.1."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_lire_la_fiche_arrivee(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=fiche.person_id,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_FICHE_HORS_PERIMETRE,
                    message=MESSAGE_FICHE_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
        return _en_reponse(fiche)

    @routeur.patch(
        "/entities/{code}/people/{appartenance}/arrival-profile",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeCompletion,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "DEUX grilles distinctes selon l'etat de la fiche — matrice §7. "
                    "Brouillon (« Completer ») : Soi, ESM/ADM-E/SUPER dans l'entite, "
                    "Booster du cercle de la cible ; `DSM`/`OFFICE` a TIRET. Publiee "
                    "(« Corriger apres publication ») : l'INVERSE sur `NEW` (perd le "
                    "droit, §6.2) et `DSM` (le retrouve, Consultants) ; `OFFICE` "
                    "reste a TIRET."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Meme forme que la lecture : trois causes indistinguables."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la fiche a change depuis votre lecture, ou "
                    "votre `version` ne correspond pas a son existence reelle. "
                    "`fiche_arrivee_etat_incompatible` : la fiche est ARCHIVEE — seul "
                    "etat sans aucune ligne d'ecriture au §7."
                )
            },
        },
        summary="Completer, ou corriger apres publication",
        description=(
            "Matrice §7, DEUX lignes servies par la MEME route — l'ecriture ne "
            "differe pas, seul le PERMIS depend de l'etat. « Completer photo, "
            "presentation et fun fact » (brouillon) : cree la fiche a la premiere "
            "completion (`version: null`), la modifie ensuite. « Corriger apres "
            "publication » : les memes deux champs, apres que `state` soit devenu "
            "`published` — le nouvel arrivant PERD ce droit (§6.2), le DSM le "
            "RETROUVE (Consultants).<br><br>"
            "**`photo_media_id` n'est pas ici** : aucune route d'upload ou "
            "d'autorisation de media n'existe encore — residu nomme, comme la "
            "lecture de `T2` l'a deja ete pour la miniature."
        ),
    )
    def completer_la_fiche(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite, unique et jamais reattribue",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        demande: DemandeDeCompletion,
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeCompletion:
        """Completer ou corriger la fiche d'arrivee — matrice §7, selon l'etat.

        `MVP-L07-US001` (2/2) avant publication, `MVP-L07-US002` (corrections
        ulterieures) apres.
        """
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
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            roles = frozenset(permissions.roles)
            #  LE PERMIS DEPEND DE L'ETAT COURANT — matrice §7, DEUX lignes
            #  distinctes. `draft` (ou pas de ligne encore) : « Completer »,
            #  Soi/Support/Support cercle. `published` : « Corriger apres
            #  publication », l'INVERSE sur `NEW` (perd le droit) et `DSM`
            #  (le retrouve). Toute autre valeur (`archived`) n'a AUCUNE ligne
            #  d'ecriture : refusee ici, jamais laissee au service.
            if fiche.state == "draft":
                autorise = peut_completer_la_fiche_arrivee(
                    connexion,
                    entite=entite.id,
                    acteur=appelant.personne,
                    cible_appartenance=appartenance,
                    cible_personne=fiche.person_id,
                    roles=roles,
                    instant=instant,
                )
            elif fiche.state == "published":
                autorise = peut_corriger_la_fiche_arrivee_apres_publication(
                    connexion,
                    entite=entite.id,
                    acteur=appelant.personne,
                    cible_appartenance=appartenance,
                    cible_personne=fiche.person_id,
                    roles=roles,
                    instant=instant,
                )
            else:
                autorise = False
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_FICHE_HORS_PERIMETRE,
                    message=MESSAGE_FICHE_HORS_PERIMETRE_ECRITURE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            ecrite = completer_la_fiche_arrivee(
                connexion,
                entite=entite.id,
                appartenance=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                champs=_champs_presents(demande),
                instant=instant,
            )
        return ReponseDeCompletion(id=ecrite.id, version=ecrite.version, state=ecrite.state)

    @routeur.post(
        "/entities/{code}/people/{appartenance}/arrival-profile/validation",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeValidation,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Soi, ou ESM/ADM-E/SUPER dans l'entite. **`BOOST` est a TIRET "
                    "ICI**, la SEULE des trois lignes du §7 ou il l'est : un Booster "
                    "aide a completer, jamais a valider ni publier."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Meme forme que la lecture : trois causes indistinguables."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la fiche a change depuis votre lecture. "
                    "`fiche_arrivee_etat_incompatible` : deja validee, ou aucune "
                    "ligne n'existe encore — rien a valider."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`fiche_arrivee_presentation_manquante` : la presentation courte "
                    "est obligatoire avant validation — modele §12.1."
                )
            },
        },
        summary="Valider et publier la fiche d'arrivee",
        description=(
            "Matrice §7.1 : la publication est AUTOMATIQUE a la validation, jamais un "
            "second geste — `state` passe de `draft` a `published` directement, "
            "`validated_at` et `published_at` portant le MEME instant. `recent_until` "
            "est calcule par PostgreSQL — modele §12.1, « un mois apres la date "
            "d'arrivee »."
        ),
    )
    def valider_la_fiche(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite, unique et jamais reattribue",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        demande: DemandeDeValidation,
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeValidation:
        """Valider et publier — matrice §7.1, `MVP-L07-US002`."""
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
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_valider_et_publier_la_fiche_arrivee(
                acteur=appelant.personne,
                cible_personne=fiche.person_id,
                roles=frozenset(permissions.roles),
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_FICHE_HORS_PERIMETRE,
                    message=MESSAGE_FICHE_HORS_PERIMETRE_ECRITURE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            validee = valider_et_publier_la_fiche_arrivee(
                connexion,
                entite=entite.id,
                appartenance=appartenance,
                acteur=appelant.personne,
                version_attendue=demande.version,
                arrival_date=fiche.arrival_date,
                instant=instant,
            )
        return ReponseDeValidation(
            id=validee.id,
            version=validee.version,
            state=validee.state,
            validated_at=validee.validated_at,
            published_at=validee.published_at,
            recent_until=validee.recent_until,
        )

    #  §9 : « Creer » et « Reutiliser une tache de reference » partagent une
    #  seule grille (voir `perimetre.py`) — une garde GENERIQUE suffit donc,
    #  contrairement a la fiche d'arrivee ou le permis depend d'une CIBLE.
    garde_du_catalogue = exiger_un_role_dans_l_entite(
        parametres, ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES
    )

    @routeur.get(
        "/entities/{code}/onboarding/task-references",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuCatalogueDeTaches,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni DSM, ESM, Booster, ADM-E ni SUPER dans cette entite."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
        },
        summary="Consulter le catalogue des taches reutilisables",
        description=(
            "Matrice §9 « Reutiliser une tache de reference ». Rend les taches PROPRES "
            "a l'entite du chemin ET les taches GLOBALES — modele §13.1 : un modele de "
            "cette entite peut reutiliser l'une comme l'autre, `T5`."
        ),
    )
    def lister_le_catalogue_de_taches(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        _appelant: SessionEtablie = Depends(garde_du_catalogue),  # noqa: B008
    ) -> ReponseDuCatalogueDeTaches:
        """Le catalogue reutilisable dans cette entite — modele §13.1."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            taches = lire_le_catalogue_de_taches(connexion, entite=entite.id)
        servies = [_tache_en_reponse(tache) for tache in taches]
        return ReponseDuCatalogueDeTaches(taches=servies, nombre_de_taches=len(servies))

    @routeur.post(
        "/entities/{code}/onboarding/task-references",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeTacheDeReference,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    '`acces_refuse` : hors de la matrice §9, ou `portee: "GLOBAL"` '
                    "demandee par un role autre que SUPER — seul SUPER atteint Global."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`code_de_tache_deja_utilise` : ce code existe deja dans ce perimetre "
                    "(cette entite, ou le catalogue global)."
                )
            },
        },
        summary="Creer une tache de reference — ferme ECART-013",
        description=(
            "Matrice §9 « Creer une tache de reference ». Le `code` est l'identifiant "
            "FONCTIONNEL STABLE que `T10` (changement mission <-> intercontrat) "
            "reutilisera pour conserver une tache commune deja terminee — `ECART-013`."
        ),
    )
    def creer_une_tache_du_catalogue(
        demande: DemandeDeTacheDeReference,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appelant: SessionEtablie = Depends(garde_du_catalogue),  # noqa: B008
    ) -> ReponseDeTacheDeReference:
        """Creer une tache de reference — matrice §9, modele §13.1."""
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
            #  La garde a deja verifie l'appartenance a l'un des CINQ roles —
            #  suffisant pour `ENTITE`. `GLOBAL` exige STRICTEMENT SUPER, une
            #  distinction que la garde generique ne porte pas : resolue ICI.
            if demande.portee == "GLOBAL":
                permissions = resoudre_les_permissions(
                    connexion, appelant.personne, entite.id, instant
                )
                if not peut_creer_une_tache_de_reference_globale(
                    roles=frozenset(permissions.roles)
                ):
                    raise ErreurApplicative(
                        code=CODE_ROLE_REFUSE,
                        message=MESSAGE_ROLE_REFUSE,
                        statut=status.HTTP_403_FORBIDDEN,
                    )
                entite_de_la_tache = None
            else:
                entite_de_la_tache = entite.id
            creee = creer_une_tache_de_reference(
                connexion,
                entite=entite_de_la_tache,
                code=demande.code,
                title=demande.title,
                description=demande.description,
                category=demande.category,
            )
        return _tache_en_reponse(creee)

    #  §9 : « Creer un modele », « Creer une nouvelle version », « Ajouter ou
    #  reordonner des taches » partagent la MEME grille brute (voir
    #  `perimetre.py`) — la garde generique borne donc les trois a l'un des
    #  cinq roles ; le permis FIN, qui differe par ligne, se resout ensuite
    #  dans chaque route via `peut_gerer_un_modele_de_cette_portee`.
    garde_des_modeles = exiger_un_role_dans_l_entite(parametres, ROLES_DE_GESTION_DES_MODELES)
    #  §9 « Restaurer une version » : DSM et BOOSTER y sont a TIRET, jamais un
    #  sous-cas — la garde COARSE les exclut donc deja, contrairement a
    #  `garde_des_modeles`. `ECART-066` resolu, voir `perimetre.py`.
    garde_de_restauration = exiger_un_role_dans_l_entite(
        parametres, ROLES_DE_RESTAURATION_DES_MODELES
    )

    @routeur.post(
        "/entities/{code}/onboarding/templates",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeModele,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : hors de la matrice §9 pour cette portee — un DSM "
                    "hors de ses propres consultants, un Booster hors de son propre "
                    "cercle, `OFFICE`, ou une portee GLOBAL demandee par un role autre "
                    "que SUPER."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`portee_de_modele_incoherente` : `scope_person_id`/`scope_circle_id` "
                    "ne correspondent pas a la portee demandee — modele §13.2."
                )
            },
        },
        summary="Creer un modele d'onboarding",
        description=(
            "Matrice §9 « Creer un modele ». Le conteneur seul : aucune version, aucune "
            "tache — `T5` livre les trois gestes separement, comme le §9 les separe."
        ),
    )
    def creer_un_modele_onboarding(
        demande: DemandeDeModele,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appelant: SessionEtablie = Depends(garde_des_modeles),  # noqa: B008
    ) -> ReponseDeModele:
        """Creer le conteneur d'un modele — matrice §9, modele §13.2."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")
        _verifier_coherence_de_la_portee(demande)

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
            autorise = peut_gerer_un_modele_de_cette_portee(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                portee=demande.portee,
                scope_person_id=demande.scope_person_id,
                scope_circle_id=demande.scope_circle_id,
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            entite_du_modele = None if demande.portee == "GLOBAL" else entite.id
            cree = creer_un_modele(
                connexion,
                entite=entite_du_modele,
                name=demande.name,
                target_status=demande.target_status,
                scope_type=demande.portee,
                scope_person_id=demande.scope_person_id,
                scope_circle_id=demande.scope_circle_id,
            )
        return _modele_en_reponse(cree)

    @routeur.post(
        "/entities/{code}/onboarding/templates/{template_id}/versions",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeVersion,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : la portee DEJA ECRITE de ce modele refuse cet acteur."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite inconnue, ou `modele_introuvable` — inexistant, ou d'une "
                    "AUTRE entite (isolation, meme discipline que le catalogue de `T4`)."
                )
            },
        },
        summary="Creer une nouvelle version brouillon",
        description=(
            "Matrice §9 « Creer une nouvelle version ». `version_number` est calcule "
            "en base — modele §13.3."
        ),
    )
    def creer_une_nouvelle_version(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        template_id: Annotated[uuid.UUID, Path(description="L'identifiant du modele")],
        demande: DemandeDeVersion,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_des_modeles),  # noqa: B008
    ) -> ReponseDeVersion:
        """Creer une nouvelle version brouillon — matrice §9, modele §13.3."""
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
            modele = lire_un_modele(connexion, entite=entite.id, modele=template_id)
            if modele is None:
                raise ErreurApplicative(
                    code=CODE_MODELE_INTROUVABLE,
                    message=MESSAGE_MODELE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_gerer_un_modele_de_cette_portee(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                portee=modele.scope_type,
                scope_person_id=modele.scope_person_id,
                scope_circle_id=modele.scope_circle_id,
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            creee = creer_une_version(
                connexion, modele=modele.id, change_summary=demande.change_summary
            )
        return _version_en_reponse(creee)

    @routeur.put(
        "/entities/{code}/onboarding/templates/{template_id}/versions/{version_id}/tasks",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesTachesDeVersion,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : la portee DEJA ECRITE de ce modele refuse cet acteur."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite, modele (`modele_introuvable`) ou version "
                    "(`version_de_modele_introuvable`) inconnus."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_de_modele_immuable` : cette version est publiee ou "
                    "retiree — modele §13.3, le temoin de cette sous-etape."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`tache_hors_perimetre_du_modele` : une tache de reference qui "
                    "n'est ni globale ni propre a l'entite de ce modele."
                )
            },
        },
        summary="Poser ou reordonner les taches d'une version",
        description=(
            "Matrice §9 « Ajouter ou reordonner des taches », UNE seule ligne pour les "
            "deux gestes. La liste ENTIERE remplace la precedente, `display_order` "
            "valant l'INDEX de chaque ligne recue — meme lecture que `content_block` "
            "au LOT 6."
        ),
    )
    def definir_les_taches_de_la_version_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        template_id: Annotated[uuid.UUID, Path(description="L'identifiant du modele")],
        version_id: Annotated[uuid.UUID, Path(description="L'identifiant de la version")],
        demande: DemandeDesTachesDeVersion,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_des_modeles),  # noqa: B008
    ) -> ReponseDesTachesDeVersion:
        """Poser la liste des taches d'une version brouillon — matrice §9, modele §13.4."""
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
            modele = lire_un_modele(connexion, entite=entite.id, modele=template_id)
            if modele is None:
                raise ErreurApplicative(
                    code=CODE_MODELE_INTROUVABLE,
                    message=MESSAGE_MODELE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            version = lire_une_version(connexion, modele=modele.id, version=version_id)
            if version is None:
                raise ErreurApplicative(
                    code=CODE_VERSION_INTROUVABLE,
                    message=MESSAGE_VERSION_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_gerer_un_modele_de_cette_portee(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                portee=modele.scope_type,
                scope_person_id=modele.scope_person_id,
                scope_circle_id=modele.scope_circle_id,
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            demandees = [
                NouvelleTacheDeVersion(
                    task_reference_id=tache.task_reference_id,
                    required=tache.required,
                    due_offset_days=tache.due_offset_days,
                    title_override=tache.title_override,
                    description_override=tache.description_override,
                )
                for tache in demande.taches
            ]
            ecrites = definir_les_taches_de_la_version(
                connexion, modele=modele, version=version, taches=demandees
            )
        servies = [_tache_de_version_en_reponse(tache) for tache in ecrites]
        return ReponseDesTachesDeVersion(taches=servies, nombre_de_taches=len(servies))

    def _resoudre_entite_modele_et_version(
        connexion: Connection, *, code: str, template_id: uuid.UUID, version_id: uuid.UUID
    ) -> tuple[uuid.UUID, Modele, VersionDeModele]:
        """Les trois lectures communes aux trois transitions — factorisees ici
        plutot que recopiees trois fois (§7.27)."""
        entite = resoudre_une_entite_active(connexion, code)
        if entite is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        modele = lire_un_modele(connexion, entite=entite.id, modele=template_id)
        if modele is None:
            raise ErreurApplicative(
                code=CODE_MODELE_INTROUVABLE,
                message=MESSAGE_MODELE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        version = lire_une_version(connexion, modele=modele.id, version=version_id)
        if version is None:
            raise ErreurApplicative(
                code=CODE_VERSION_INTROUVABLE,
                message=MESSAGE_VERSION_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        return entite.id, modele, version

    @routeur.post(
        "/entities/{code}/onboarding/templates/{template_id}/versions/{version_id}/publication",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDePublicationDeVersion,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : la portee DEJA ECRITE de ce modele refuse cet acteur."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite, modele ou version inconnus, ou d'une AUTRE entite."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`transition_de_version_invalide` : seul un BROUILLON peut etre publie."
                )
            },
        },
        summary="Publier une version — le brouillon devient immuable",
        description=(
            "Matrice §9 « Publier une version ». `draft` devient `published` et recoit "
            "sa date de publication — modele §13.3. Aucune depublication : retirer une "
            "version se fait en l'archivant."
        ),
    )
    def publier_une_version_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        template_id: Annotated[uuid.UUID, Path(description="L'identifiant du modele")],
        version_id: Annotated[uuid.UUID, Path(description="L'identifiant de la version")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_des_modeles),  # noqa: B008
    ) -> ReponseDePublicationDeVersion:
        """Publier une version — matrice §9, modele §13.3."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, modele, version = _resoudre_entite_modele_et_version(
                connexion, code=code, template_id=template_id, version_id=version_id
            )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite_id, instant)
            autorise = peut_gerer_un_modele_de_cette_portee(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                portee=modele.scope_type,
                scope_person_id=modele.scope_person_id,
                scope_circle_id=modele.scope_circle_id,
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            publiee = publier_une_version(
                connexion, version=version.id, acteur=appelant.personne, instant=instant
            )
        return _publication_en_reponse(publiee)

    @routeur.post(
        "/entities/{code}/onboarding/templates/{template_id}/versions/{version_id}/archivage",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDArchivageDeVersion,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : la portee DEJA ECRITE de ce modele refuse cet acteur."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite, modele ou version inconnus, ou d'une AUTRE entite."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`transition_de_version_invalide` : seule une version PUBLIEE peut "
                    "etre archivee — pas un brouillon, pas une version deja retiree."
                )
            },
        },
        summary="Archiver une version — la retirer de la circulation",
        description=(
            "Matrice §9 « Archiver une version ». `published` devient `retired`. Aucun "
            "motif : le §18.1 n'enumere pas ce geste parmi ses cinq cas obligatoires."
        ),
    )
    def archiver_une_version_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        template_id: Annotated[uuid.UUID, Path(description="L'identifiant du modele")],
        version_id: Annotated[uuid.UUID, Path(description="L'identifiant de la version")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_des_modeles),  # noqa: B008
    ) -> ReponseDArchivageDeVersion:
        """Archiver une version — matrice §9, modele §13.3."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, modele, version = _resoudre_entite_modele_et_version(
                connexion, code=code, template_id=template_id, version_id=version_id
            )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite_id, instant)
            autorise = peut_gerer_un_modele_de_cette_portee(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                portee=modele.scope_type,
                scope_person_id=modele.scope_person_id,
                scope_circle_id=modele.scope_circle_id,
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            archivee = archiver_une_version(connexion, version=version.id)
        return _archivage_en_reponse(archivee)

    @routeur.post(
        "/entities/{code}/onboarding/templates/{template_id}/versions/{version_id}/restauration",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeRestaurationDeVersion,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : DSM et BOOSTER sont exclus EN BLOC sur cette ligne "
                    "du §9 — jamais un sous-cas de leur propre modele, a la difference "
                    "des autres gestes. `ECART-066` resolu : l'ESM restaure desormais "
                    "comme `ADM-E`, dans son entite."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite, modele ou version inconnus, ou d'une AUTRE entite."
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`transition_de_version_invalide` : seule une version RETIREE peut "
                    "etre restauree."
                )
            },
        },
        summary="Restaurer une version — la reactiver, sans rouvrir son edition",
        description=(
            "Matrice §9 « Restaurer une version ». `retired` redevient `published` — "
            "JAMAIS `draft` : la version reste immuable, modele §13.3. "
            "`published_at`/`published_by_person_id` d'origine sont conserves."
        ),
    )
    def restaurer_une_version_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        template_id: Annotated[uuid.UUID, Path(description="L'identifiant du modele")],
        version_id: Annotated[uuid.UUID, Path(description="L'identifiant de la version")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_de_restauration),  # noqa: B008
    ) -> ReponseDeRestaurationDeVersion:
        """Restaurer une version — matrice §9, modele §13.3, `ECART-066` resolu."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, modele, version = _resoudre_entite_modele_et_version(
                connexion, code=code, template_id=template_id, version_id=version_id
            )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite_id, instant)
            autorise = peut_restaurer_une_version_de_modele(
                portee=modele.scope_type, roles=frozenset(permissions.roles)
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            restauree = restaurer_une_version(connexion, version=version.id)
        return _restauration_en_reponse(restauree)

    return routeur
