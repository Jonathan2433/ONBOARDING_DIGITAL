"""Les routes de l'onboarding — LOT 7, `T2`/`T3` (fiche), `T4` (catalogue), `T5`
(modeles), `T6` (cycle de vie d'une version), `T7` (instance depuis l'arrivee),
`T8` (terminer/annuler une tache), `T9` (reouverture administrative).

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

`T7` AJOUTE L'INSTANCE DE PARCOURS, SOUS `.../people/{appartenance}/onboarding-parcours`

  Retour a une cible precise, comme `T2`/`T3` : la garde COARSE
  (`exiger_un_role_dans_l_entite`) est doublee d'un permis FIN qui verifie le
  rattachement DSM/Booster (« Affecter ») ou accepte `Soi` en plus
  (« Consulter »). Voir `app/onboarding/instances.py` pour la priorite de
  resolution du modele et `app/onboarding/perimetre.py` pour la TROISIEME
  grille du module — `DSM` y a « Consultants » PLEIN, a la difference de `T2`.

`T8` AJOUTE TERMINER/ANNULER UNE TACHE, SOUS `.../onboarding-parcours/taches/{tache}/...`

  **AUCUNE GARDE COARSE** : `Soi` est la SEULE porte possible sur ces deux
  lignes du §8.1 (QUATRIEME grille, `perimetre.peut_agir_sur_sa_tache_
  onboarding`), donc la dependance est `exiger_une_session`, comme la LECTURE
  du parcours — jamais `exiger_un_role_dans_l_entite`, qui refuserait a tort
  un nouvel arrivant sans aucun role d'entite. Les deux routes resolvent
  l'instance ACTIVE de l'appartenance (`lire_l_instance_active`), jamais « la
  plus recente » : voir `app/onboarding/taches.py`.

`T9` AJOUTE LA REOUVERTURE, SOUS `.../taches/{tache}/reouverture`

  **L'INVERSE DE `T8` : UNE GARDE COARSE SUFFIT, SEULE.** `ROLES_DE_
  REOUVERTURE_DES_TACHES` (`ESM`/`ADM-E`/`SUPER`, CINQUIEME grille) n'a ni
  rattachement DSM/Booster ni portee GLOBAL a distinguer — une tache
  d'instance vit toujours dans UNE entite. `garde_de_reouverture` EST donc
  la verification complete, meme parti que `garde_du_catalogue` (`T4`) :
  aucun appel a `resoudre_les_permissions` ni a une fonction `peut_...`
  n'est necessaire dans le corps de la route. Le motif est OBLIGATOIRE dans
  le corps de la demande (`DemandeDeReouverture`, `min_length=1`) — la
  PREMIERE route du projet a exiger et ECRIRE un motif, la ou `archive_
  reason`/`assignment_reason` restent des colonnes jamais ecrites
  (`ECART-064`).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Final, Literal

from fastapi import APIRouter, Depends, Path, Query, Request, status
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
    lister_les_modeles,
    lister_les_versions,
)
from app.onboarding.instances import (
    CODE_AUCUN_PARCOURS_ACTIF,
    CODE_INSTANCE_INTROUVABLE,
    MESSAGE_AUCUN_PARCOURS_ACTIF,
    MESSAGE_INSTANCE_INTROUVABLE,
    Instance,
    Parcours,
    Progression,
    TacheDuParcours,
    affecter_un_parcours,
    archiver_un_parcours_termine,
    lire_l_appartenance,
    lire_l_instance_actionnable,
    lire_l_instance_active,
    lire_le_parcours,
    lire_une_instance,
    restaurer_un_parcours,
)
from app.onboarding.perimetre import (
    ROLES_D_ARCHIVAGE_ET_RESTAURATION_DU_PARCOURS,
    ROLES_DE_GESTION_DES_MODELES,
    ROLES_DE_GESTION_DU_CATALOGUE_DE_TACHES,
    ROLES_DE_REOUVERTURE_DES_TACHES,
    ROLES_DE_RESTAURATION_DES_MODELES,
    ROLES_DU_PARCOURS_ONBOARDING,
    peut_affecter_un_parcours_onboarding,
    peut_agir_sur_sa_tache_onboarding,
    peut_completer_la_fiche_arrivee,
    peut_corriger_la_fiche_arrivee_apres_publication,
    peut_creer_une_tache_de_reference_globale,
    peut_gerer_un_modele_de_cette_portee,
    peut_lire_la_fiche_arrivee,
    peut_lire_le_parcours_onboarding,
    peut_restaurer_une_version_de_modele,
    peut_valider_et_publier_la_fiche_arrivee,
    resoudre_le_perimetre_du_suivi,
)
from app.onboarding.suivi import lister_les_taches_en_retard
from app.onboarding.taches import annuler_la_completion, reouvrir_une_tache, terminer_une_tache
from app.permissions.dependances import (
    CODE_ROLE_REFUSE,
    MESSAGE_ROLE_REFUSE,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

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


class ReponseDeModeleAvecVersions(ReponseDeModele):
    """Le conteneur ET ses versions — T14, l'ecran d'administration.

    N'existe QUE pour la liste : les routes qui creent ou lisent un modele
    seul (`ReponseDeModele`) n'ont pas besoin de ses versions, deja connues
    de l'appelant a ce moment-la.
    """

    versions: list[ReponseDeVersion]


class ReponseDesModeles(BaseModel):
    """La liste et son compte — §7.20, rapporter plutot que taire."""

    modeles: list[ReponseDeModeleAvecVersions]
    nombre_de_modeles: int


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


class ReponseDeTacheDuParcours(BaseModel):
    """Une ligne de `onboarding_instance_task` — snapshot fige, modele §13.6."""

    id: uuid.UUID
    task_reference_id: uuid.UUID
    title_snapshot: str
    description_snapshot: str | None
    required: bool
    due_at: dt.datetime
    state: str
    completed_at: dt.datetime | None
    reopened_at: dt.datetime | None


class DemandeDeReouverture(BaseModel):
    """§8.3 : « la reouverture exige un motif ». `min_length=1` refuse la
    chaine vide — `NOT NULL` seul (contrainte de la base) l'aurait laissee
    passer, meme piege que la `CHECK` de `T1` sur `length(btrim(...))` (voir
    `compte-rendu-t1-lot-7.md` §2.2)."""

    model_config = ConfigDict(extra="forbid")

    motif: str = Field(min_length=1, description="Le motif de la reouverture — matrice §8.3.")


class ReponseDeLInstance(BaseModel):
    """L'instance elle-meme — modele §13.5."""

    id: uuid.UUID
    template_version_id: uuid.UUID
    reference_date: dt.date
    state: str
    started_at: dt.datetime
    completed_at: dt.datetime | None


class ReponseDeLaProgression(BaseModel):
    """Comptee a la lecture — jamais stockee, critere de sortie n°3 du lot."""

    taches_obligatoires_totales: int
    taches_obligatoires_terminees: int


class ReponseDuParcours(BaseModel):
    """`instance` vaut `null` tant qu'aucun parcours n'a ete affecte — meme
    convention que la fiche d'arrivee (`id`/`version` nuls, `T2`)."""

    instance: ReponseDeLInstance | None
    progression: ReponseDeLaProgression | None
    prochaine_tache: ReponseDeTacheDuParcours | None
    taches: list[ReponseDeTacheDuParcours]


class TacheEnRetardDuSuivi(BaseModel):
    """Une tache en retard et la personne qu'elle concerne — matrice §8.1
    « Consulter les taches en retard », `T12`. Noms en `snake_case`, meme
    convention que `CollaborateurDuTrombinoscope` (LOT 5, `T10`) : le contrat
    de `packages/contracts` traduit vers le `camelCase` du frontend."""

    id: uuid.UUID
    title_snapshot: str
    due_at: dt.datetime
    state: str
    instance_id: uuid.UUID
    appartenance_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str


class ReponseDuSuivi(BaseModel):
    """Une page du suivi, et de quoi savoir ou l'on est — meme forme que
    `ReponseDuTrombinoscope` (LOT 5, `T2`) : `total` porte la population
    entiere de la portee resolue, `pages` est calcule UNE SEULE fois ici."""

    taches: list[TacheEnRetardDuSuivi]
    page: int
    taille: int
    total: int
    pages: int


def _tache_du_parcours_en_reponse(tache: TacheDuParcours) -> ReponseDeTacheDuParcours:
    return ReponseDeTacheDuParcours(
        id=tache.id,
        task_reference_id=tache.task_reference_id,
        title_snapshot=tache.title_snapshot,
        description_snapshot=tache.description_snapshot,
        required=tache.required,
        due_at=tache.due_at,
        state=tache.state,
        completed_at=tache.completed_at,
        reopened_at=tache.reopened_at,
    )


def _instance_en_reponse(instance: Instance) -> ReponseDeLInstance:
    return ReponseDeLInstance(
        id=instance.id,
        template_version_id=instance.template_version_id,
        reference_date=instance.reference_date,
        state=instance.state,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
    )


def _progression_en_reponse(progression: Progression) -> ReponseDeLaProgression:
    return ReponseDeLaProgression(
        taches_obligatoires_totales=progression.taches_obligatoires_totales,
        taches_obligatoires_terminees=progression.taches_obligatoires_terminees,
    )


def _parcours_en_reponse(parcours: Parcours) -> ReponseDuParcours:
    return ReponseDuParcours(
        instance=None if parcours.instance is None else _instance_en_reponse(parcours.instance),
        progression=(
            None if parcours.progression is None else _progression_en_reponse(parcours.progression)
        ),
        prochaine_tache=(
            None
            if parcours.prochaine_tache is None
            else _tache_du_parcours_en_reponse(parcours.prochaine_tache)
        ),
        taches=[_tache_du_parcours_en_reponse(t) for t in parcours.taches],
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

    @routeur.get(
        "/entities/{code}/onboarding/templates",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesModeles,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni DSM, ESM, Booster, ADM-E ni SUPER dans cette entite."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
        },
        summary="Consulter les modeles geres depuis cette entite — T14",
        description=(
            "Matrice §9 : les modeles ATTEIGNABLES par l'appelant dans son propre "
            "perimetre — un DSM ne voit que les siens, un Booster que ceux de son "
            "cercle, un ESM/ADM-E/SUPER tous ceux de l'entite (et les GLOBAUX pour "
            "SUPER). Chaque modele porte ses versions. Trouvee en construisant "
            "l'ecran d'administration : ni `T5` ni `T6` n'avaient de consommateur "
            "pour cette lecture."
        ),
    )
    def lister_les_modeles_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appelant: SessionEtablie = Depends(garde_des_modeles),  # noqa: B008
    ) -> ReponseDesModeles:
        """Les modeles geres par l'appelant, avec leurs versions — matrice §9, T14."""
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
            roles = frozenset(permissions.roles)
            tous = lister_les_modeles(connexion, entite=entite.id)
            visibles = [
                modele
                for modele in tous
                if peut_gerer_un_modele_de_cette_portee(
                    connexion,
                    entite=entite.id,
                    acteur=appelant.personne,
                    roles=roles,
                    portee=modele.scope_type,
                    scope_person_id=modele.scope_person_id,
                    scope_circle_id=modele.scope_circle_id,
                    instant=instant,
                )
            ]
            versions = lister_les_versions(connexion, modeles=[modele.id for modele in visibles])
        versions_par_modele: dict[uuid.UUID, list[ReponseDeVersion]] = {}
        for version in versions:
            versions_par_modele.setdefault(version.template_id, []).append(
                _version_en_reponse(version)
            )
        servis = [
            ReponseDeModeleAvecVersions(
                **_modele_en_reponse(modele).model_dump(),
                versions=versions_par_modele.get(modele.id, []),
            )
            for modele in visibles
        ]
        return ReponseDesModeles(modeles=servis, nombre_de_modeles=len(servis))

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

    #  §8.1 « Affecter un parcours » : DSM/ESM/BOOST/ADM-E/SUPER a la garde
    #  COARSE — OFFICE et EMP refuses avant meme la resolution de portee.
    garde_d_affectation = exiger_un_role_dans_l_entite(parametres, ROLES_DU_PARCOURS_ONBOARDING)

    @routeur.post(
        "/entities/{code}/people/{appartenance}/onboarding-parcours",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDuParcours,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni role d'entite, ni DSM rattache a ce consultant, "
                    "ni Booster du cercle de cette appartenance."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite ou appartenance inconnues."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`parcours_deja_actif` : une instance active existe deja pour cette "
                    "appartenance — modele §13.5, une seule a la fois."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`statut_professionnel_introuvable` : aucune situation active. "
                    "`aucun_modele_publie` : aucun modele ne correspond, a aucun niveau "
                    "de portee — DSM, cercle, entite ou global."
                )
            },
        },
        summary="Affecter un parcours d'onboarding",
        description=(
            "Matrice §8.1 « Affecter un parcours ». Resout le bon modele par la "
            "priorite DSM > CIRCLE > ENTITY > GLOBAL — le plus specifique gagne — "
            "et snapshotte ses taches avec des echeances calculees depuis "
            "`arrival_date`, jamais recalculees plus tard."
        ),
    )
    def affecter_un_parcours_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_affectation),  # noqa: B008
    ) -> ReponseDuParcours:
        """Affecter un parcours — matrice §8.1, modele §13.5."""
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
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_affecter_un_parcours_onboarding(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            parcours = affecter_un_parcours(
                connexion,
                entite=entite.id,
                appartenance=appartenance,
                cible=cible,
                acteur=appelant.personne,
                instant=instant,
            )
        return _parcours_en_reponse(parcours)

    @routeur.get(
        "/entities/{code}/people/{appartenance}/onboarding-parcours",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuParcours,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni Soi, ni role d'entite, ni DSM/Booster rattache."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite ou appartenance inconnues."},
        },
        summary="Consulter le parcours d'onboarding",
        description=(
            "Matrice §8.1 « Consulter son parcours » (Soi) et « ... d'un collaborateur ». "
            "`instance` vaut `null` tant qu'aucun parcours n'a ete affecte. La progression "
            "est COMPTEE a chaque appel, jamais stockee — critere de sortie n°3 du lot."
        ),
    )
    def lire_le_parcours_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDuParcours:
        """Consulter le parcours — matrice §8.1."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_lire_le_parcours_onboarding(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=cible.person_id,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            parcours = lire_le_parcours(connexion, entite=entite.id, appartenance=appartenance)
        return _parcours_en_reponse(parcours)

    #  §8.1 « Marquer une tache comme terminee » / « Annuler la completion
    #  dans les 5 minutes » : PAS de garde COARSE par role — `Soi` est la
    #  SEULE porte, verifiee par `peut_agir_sur_sa_tache_onboarding` apres
    #  resolution de la cible. Meme dependance que la LECTURE du parcours
    #  (`exiger_une_session`), jamais `exiger_un_role_dans_l_entite` : un
    #  nouvel arrivant sans aucun role d'entite doit pouvoir agir sur SA
    #  propre tache.

    def _resoudre_l_instance_active_ou_404(
        connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
    ) -> Instance:
        instance_active = lire_l_instance_active(
            connexion, entite=entite, appartenance=appartenance
        )
        if instance_active is None:
            raise ErreurApplicative(
                code=CODE_AUCUN_PARCOURS_ACTIF,
                message=MESSAGE_AUCUN_PARCOURS_ACTIF,
                statut=status.HTTP_404_NOT_FOUND,
            )
        return instance_active

    #  `T11` : `active` OU `archived` (jamais `replaced`) — voir l'en-tete de
    #  `instances.lire_l_instance_actionnable`. Employee par les TROIS routes
    #  de taches (`T8`/`T9`), jamais par l'affectation ni par l'archivage
    #  MANUEL, qui restent strictement `active` seule.
    def _resoudre_l_instance_actionnable_ou_404(
        connexion: Connection, *, entite: uuid.UUID, appartenance: uuid.UUID
    ) -> Instance:
        instance = lire_l_instance_actionnable(connexion, entite=entite, appartenance=appartenance)
        if instance is None:
            raise ErreurApplicative(
                code=CODE_AUCUN_PARCOURS_ACTIF,
                message=MESSAGE_AUCUN_PARCOURS_ACTIF,
                statut=status.HTTP_404_NOT_FOUND,
            )
        return instance

    @routeur.post(
        "/entities/{code}/people/{appartenance}/onboarding-parcours/taches/{tache}/completion",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTacheDuParcours,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : seul le nouvel arrivant lui-meme agit sur sa tache."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite ou appartenance inconnues. `aucun_parcours_actif` : aucune "
                    "instance active. `tache_introuvable` : identifiant hors de ce parcours."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`transition_de_tache_invalide` : la tache n'est pas `todo` — deja "
                    "terminee, reouverte ou annulee."
                )
            },
        },
        summary="Marquer une tache comme terminee",
        description=(
            "Matrice §8.1 « Marquer une tache comme terminee ». `Soi` uniquement — "
            "tiret partout ailleurs, y compris DSM/BOOST (piege n°1, fiche-lot-7.md §2.1)."
        ),
    )
    def terminer_une_tache_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        tache: Annotated[uuid.UUID, Path(description="L'identifiant de la tache d'instance")],
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeTacheDuParcours:
        """Terminer une tache — matrice §8.1, modele §13.6."""
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
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            if not peut_agir_sur_sa_tache_onboarding(
                acteur=appelant.personne, cible_personne=cible.person_id
            ):
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            instance_active = _resoudre_l_instance_actionnable_ou_404(
                connexion, entite=entite.id, appartenance=appartenance
            )
            terminee = terminer_une_tache(
                connexion,
                entite=entite.id,
                instance=instance_active.id,
                tache=tache,
                acteur=appelant.personne,
                instant=instant,
            )
        return _tache_du_parcours_en_reponse(terminee)

    @routeur.post(
        "/entities/{code}/people/{appartenance}/onboarding-parcours/taches/{tache}/annulation",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTacheDuParcours,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : seul le nouvel arrivant lui-meme agit sur sa tache."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite ou appartenance inconnues. `aucun_parcours_actif` : aucune "
                    "instance active. `tache_introuvable` : identifiant hors de ce parcours."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`transition_de_tache_invalide` : la tache n'est pas `completed`. "
                    "`delai_d_annulation_depasse` : plus de cinq minutes depuis la "
                    "completion — matrice §8.3, seule une reouverture administrative agit."
                )
            },
        },
        summary="Annuler la completion d'une tache dans les cinq minutes",
        description=(
            "Matrice §8.1 « Annuler la completion dans les 5 minutes ». `Soi` uniquement. "
            "La tache redevient `todo`, jamais `cancelled` — voir `app/onboarding/taches.py`."
        ),
    )
    def annuler_la_completion_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        tache: Annotated[uuid.UUID, Path(description="L'identifiant de la tache d'instance")],
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeTacheDuParcours:
        """Annuler une completion dans les cinq minutes — matrice §8.1/§8.3."""
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
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            if not peut_agir_sur_sa_tache_onboarding(
                acteur=appelant.personne, cible_personne=cible.person_id
            ):
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            instance_active = _resoudre_l_instance_actionnable_ou_404(
                connexion, entite=entite.id, appartenance=appartenance
            )
            annulee = annuler_la_completion(
                connexion,
                entite=entite.id,
                instance=instance_active.id,
                tache=tache,
                acteur=appelant.personne,
                instant=instant,
            )
        return _tache_du_parcours_en_reponse(annulee)

    #  §8.1 « Reouvrir apres le delai de 5 minutes » / §8.3 : CINQUIEME grille
    #  du module, INVERSE de la quatrieme. AUCUN sous-cas DSM/Booster rattache
    #  ici (a la difference de `garde_d_affectation`) — la garde coarse EST la
    #  verification complete, meme parti que `garde_du_catalogue` (`T4`).
    garde_de_reouverture = exiger_un_role_dans_l_entite(parametres, ROLES_DE_REOUVERTURE_DES_TACHES)

    @routeur.post(
        "/entities/{code}/people/{appartenance}/onboarding-parcours/taches/{tache}/reouverture",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTacheDuParcours,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : seuls l'ESM, l'administrateur d'entite ou le "
                    "super-administrateur reouvrent — DSM et Booster explicitement "
                    "exclus, meme rattaches (matrice §8.3)."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite ou appartenance inconnues. `aucun_parcours_actif` : aucune "
                    "instance active. `tache_introuvable` : identifiant hors de ce parcours."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`transition_de_tache_invalide` : la tache n'est pas `completed`. "
                    "`reouverture_prematuree` : moins de cinq minutes depuis la "
                    "completion — le nouvel arrivant peut encore annuler lui-meme."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": "Le motif est obligatoire et ne peut pas etre vide."
            },
        },
        summary="Reouvrir une tache apres le delai de cinq minutes",
        description=(
            "Matrice §8.1/§8.3. `ESM`, administrateur d'entite ou super-administrateur "
            "SEULEMENT, motif obligatoire. La tache passe a `reopened`, jamais un retour "
            "a `todo` — reservee a l'annulation en libre service (`T8`)."
        ),
    )
    def reouvrir_une_tache_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        tache: Annotated[uuid.UUID, Path(description="L'identifiant de la tache d'instance")],
        demande: DemandeDeReouverture,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_de_reouverture),  # noqa: B008
    ) -> ReponseDeTacheDuParcours:
        """Reouvrir une tache apres le delai — matrice §8.1/§8.3, modele §13.6."""
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
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            instance_active = _resoudre_l_instance_actionnable_ou_404(
                connexion, entite=entite.id, appartenance=appartenance
            )
            reouverte = reouvrir_une_tache(
                connexion,
                entite=entite.id,
                instance=instance_active.id,
                tache=tache,
                acteur=appelant.personne,
                motif=demande.motif,
                instant=instant,
            )
        return _tache_du_parcours_en_reponse(reouverte)

    #  §8.1 « Archiver un parcours termine » / « Restaurer un parcours
    #  archive » — `T11`, `ECART-066` (volet parcours) resolu. MEME garde
    #  coarse que la reouverture (`T9`) : DSM/BOOST exclus en bloc, aucun
    #  rattachement ni portee GLOBAL a distinguer.
    garde_d_archivage_et_restauration = exiger_un_role_dans_l_entite(
        parametres, ROLES_D_ARCHIVAGE_ET_RESTAURATION_DU_PARCOURS
    )

    @routeur.post(
        "/entities/{code}/people/{appartenance}/onboarding-parcours/archivage",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLInstance,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : seuls l'ESM, l'administrateur d'entite ou le "
                    "super-administrateur archivent manuellement — DSM et Booster "
                    "exclus, meme rattaches (matrice §8.1)."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite ou appartenance inconnues. `aucun_parcours_actif` : "
                    "aucune instance active a archiver."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`parcours_non_termine` : au moins une tache obligatoire n'est "
                    "pas encore `completed` — matrice §8.1, « Archiver un parcours "
                    "termine »."
                )
            },
        },
        summary="Archiver manuellement un parcours d'onboarding termine",
        description=(
            "Matrice §8.1 « Archiver un parcours termine ». Le MEME geste se "
            "produit automatiquement des que la derniere tache obligatoire est "
            "completee (`T8`) — cette route sert de filet pour le residuel, et ne "
            "trouve donc normalement rien a faire dans le cas courant."
        ),
    )
    def archiver_un_parcours_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_archivage_et_restauration),  # noqa: B008
    ) -> ReponseDeLInstance:
        """Archiver manuellement un parcours termine — matrice §8.1, `T11`."""
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
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            instance_active = _resoudre_l_instance_active_ou_404(
                connexion, entite=entite.id, appartenance=appartenance
            )
            archivee = archiver_un_parcours_termine(
                connexion, entite=entite.id, instance=instance_active.id, instant=instant
            )
        return _instance_en_reponse(archivee)

    @routeur.post(
        "/entities/{code}/people/{appartenance}/onboarding-parcours/{instance}/restauration",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLInstance,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : seuls l'ESM, l'administrateur d'entite ou le "
                    "super-administrateur restaurent — DSM et Booster exclus, meme "
                    "rattaches (matrice §8.1)."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Entite ou appartenance inconnues. `instance_introuvable` : cet "
                    "identifiant ne correspond a aucune instance de cette appartenance."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`parcours_non_archivable` : cette instance n'est pas `archived`, "
                    "ou l'appartenance porte deja une instance active."
                )
            },
        },
        summary="Restaurer un parcours d'onboarding archive",
        description=(
            "Matrice §8.1 « Restaurer un parcours archive », `ECART-066` (volet "
            "parcours) resolu le 28/09/2026 : l'ESM restaure librement dans son "
            "entite. Ne rouvre AUCUNE tache — restaurer un parcours n'est pas "
            "restaurer une personne."
        ),
    )
    def restaurer_un_parcours_onboarding(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        instance: Annotated[uuid.UUID, Path(description="L'identifiant de l'instance archivee")],
        requete: Request,
        appelant: SessionEtablie = Depends(garde_d_archivage_et_restauration),  # noqa: B008
    ) -> ReponseDeLInstance:
        """Restaurer un parcours archive — matrice §8.1, `T11`, `ECART-066`."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            cible = lire_l_appartenance(connexion, entite=entite.id, appartenance=appartenance)
            if cible is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            existante = lire_une_instance(
                connexion, entite=entite.id, appartenance=appartenance, instance=instance
            )
            if existante is None:
                raise ErreurApplicative(
                    code=CODE_INSTANCE_INTROUVABLE,
                    message=MESSAGE_INSTANCE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            restauree = restaurer_un_parcours(connexion, entite=entite.id, instance=instance)
        return _instance_en_reponse(restauree)

    @routeur.get(
        "/entities/{code}/onboarding-suivi/taches-en-retard",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuSuivi,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, ou `page` inferieure a 1."
                )
            },
        },
        summary="Suivre les taches en retard dans son perimetre",
        description=(
            "Matrice §8.1 « Consulter les taches en retard », `T12`, `US008`. "
            "Aucun role n'est refuse : la portee s'ajuste au role le plus large "
            "detenu — Entite (ESM/ADM-E/SUPER), Consultants (DSM), Cercle "
            "(Booster), ou Soi en dernier recours, disponible a n'importe qui "
            "sur ses PROPRES taches. « Reporting de base » (cahier, Inclus) : "
            "aucun graphique, aucun export — LOT 10."
        ),
    )
    def suivre_les_taches_en_retard(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[
            int,
            Query(ge=1, description="Numero de page, 1-indexee comme celui que l'ecran affiche"),
        ] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDuSuivi:
        """Suivre les taches en retard — matrice §8.1, `T12`."""
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
            perimetre = resoudre_le_perimetre_du_suivi(roles=frozenset(permissions.roles))
            resultat = lister_les_taches_en_retard(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                perimetre=perimetre,
                page=page,
                taille=int(taille),
                instant=instant,
            )

        pages = -(-resultat.total // int(taille))
        return ReponseDuSuivi(
            taches=[
                TacheEnRetardDuSuivi(
                    id=tache.id,
                    title_snapshot=tache.title_snapshot,
                    due_at=tache.due_at,
                    state=tache.state,
                    instance_id=tache.instance_id,
                    appartenance_id=tache.appartenance_id,
                    person_id=tache.person_id,
                    first_name=tache.first_name,
                    last_name=tache.last_name,
                )
                for tache in resultat.taches
            ],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    return routeur
