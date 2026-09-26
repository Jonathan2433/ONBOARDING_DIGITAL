"""Les routes de l'onboarding — LOT 7, `T2`/`T3` (fiche d'arrivee), `T4` (catalogue).

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
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Final, Literal

from fastapi import APIRouter, Depends, Path, Request, status
from pydantic import BaseModel, ConfigDict, Field

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
from app.onboarding.ecriture import completer_la_fiche_arrivee, valider_et_publier_la_fiche_arrivee
from app.onboarding.fiche_arrivee import FicheArrivee, lire_la_fiche_arrivee
from app.onboarding.perimetre import (
    ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES,
    peut_completer_la_fiche_arrivee,
    peut_corriger_la_fiche_arrivee_apres_publication,
    peut_creer_une_tache_de_reference_globale,
    peut_lire_la_fiche_arrivee,
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

    return routeur
