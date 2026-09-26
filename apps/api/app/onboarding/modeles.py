"""Les huit tables du lot — modele §12.1 et §13.1 a §13.7.

LOT 7, sous-etape `T1`, socle de toutes les stories du lot.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  Il pose `arrival_profile` (§12.1) et les six tables d'onboarding (§13.1 a
  §13.7), avec les champs communs du §3.1 et les cles COMPOSITES du §25.3 la ou
  elles sont SURES. Il ne pose aucun service, aucune route : la lecture arrive
  en `T2`/`T7`, l'ecriture en `T3`/`T5`/`T6`/`T8`/`T9`/`T10`.

  `photo_authorization` N'EST PAS RECREEE. Elle existe depuis le LOT 5
  (migration `0014`) : `arrival_profile.photo_media_id` s'y raccroche par
  `media_asset`, jamais par une nouvelle table.

POURQUOI DEUX TABLES SEULEMENT PORTENT UN `entity_id` NULLABLE, ET LES AUTRES
NON

  Le §13.1 et le §13.2 ECRIVENT explicitement « `entity_id` | Nullable pour une
  tache/un modele GLOBAL ». Ce sont les deux SEULS endroits du corpus qui
  admettent l'absence d'entite. `onboarding_task_reference` et
  `onboarding_template` portent donc un `entity_id` nullable, hors du mixin
  `RessourceLocale` qui l'exigerait NOT NULL.

  Toutes les autres tables du lot sont locales EN SUBSTANCE — un profil
  d'arrivee, une instance, une tache d'instance, un evenement appartiennent
  toujours a UNE entite, par la chaine de l'appartenance — et recoivent donc
  `RessourceLocale` comme `content_block` l'a fait au LOT 6 pour la meme raison
  (§25.3 est AUSSI le modele).

POURQUOI LES VERSIONS ET LES TACHES DE MODELE N'ONT PAS D'`entity_id`, ALORS
QUE LA REGLE CI-DESSUS DEVRAIT LEUR EN DONNER UN

  `onboarding_template_version` et `onboarding_template_task` heritent leur
  portee de `onboarding_template`, dont l'`entity_id` est NULLABLE. Le §4.14 de
  `CLAUDE.md` est explicite : **MATCH SIMPLE rend une cle composite INERTE des
  qu'une colonne est nulle**. Donner un `entity_id` nullable a ces deux tables
  et l'apparier par une cle composite aurait rendu la cle etrangere vers
  `onboarding_template`/`onboarding_template_version` elle-meme INERTE pour
  tout modele GLOBAL — la table racine du lot n'aurait alors plus GARANTI que
  `template_id` designe une ligne existante. Une cle SIMPLE, toujours appliquee,
  est donc la seule option sure ici. La coherence d'entite entre un modele et
  les taches de reference qu'il reutilise (une tache d'une entite dans un
  modele d'une AUTRE entite) N'EST PAS VERIFIEE EN BASE : c'est un residuel
  nomme, a instruire par le SERVICE en `T5`.

  **MEME MOTIF, TROUVE PAR `make isolation-check` ET NON ANTICIPE** :
  `onboarding_template.scope_circle_id` a d'abord recu une cle COMPOSITE vers
  `circle`, au motif qu'une contrainte structurelle garantit `entity_id` NOT
  NULL des que `scope_circle_id` l'est. Le controle l'a refusee quand meme :
  il exige `entity_id` NOT NULL a la SOURCE, sans condition, et ne raisonne pas
  sur une contrainte tierce. Cle SIMPLE retenue ; la coherence d'entite entre
  un modele `CIRCLE` et son cercle est elle aussi un residuel service, `T5`.

CE QUE LE MODELE N'ECRIT PAS, ET QUI RESTE DONC OUVERT

  1. **`§13.7` ne nomme AUCUNE colonne.** Il decrit le ROLE de la table — journal
     des affectations, completions, annulations, reouvertures, retenues et
     annulations de tache — jamais sa forme. Les colonnes ci-dessous sont
     DERIVEES de ce role, et de `auth_event` (LOT 3, meme nature : un journal
     d'evenements, un acteur NULLABLE, une raison facultative).
  2. **`ECART-066` reste ouvert.** La restauration « Conditionnelle » d'un
     modele ou d'une instance archives par l'ESM n'est definie nulle part : ce
     module pose les etats `archived`/`replaced` qu'une restauration devra lire,
     mais aucune route ne la sert avant que l'ecart soit tranche (`T6`/`T11`).
     **`onboarding_template_version.state` PORTE DESORMAIS SA PROPRE
     ENUMERATION** (`EtatDeLaVersionDuModele`, `T5`, migration `0021`) — ce
     paragraphe annoncait un residu ici, corrige, jamais en modifiant `0020`.
  3. **`ECART-012` n'est pas resolu.** `target_status` ne porte que
     `mission`/`intercontract`, les deux seules valeurs du modele §6.5 — la MEME
     enumeration que `SituationProfessionnelle`, reutilisee ici plutot que
     recopiee (§7.27).
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.people.modeles import SituationProfessionnelle
from app.shared.modele import (
    Base,
    ChampsCommuns,
    RessourceLocale,
    contrainte_enumeration,
    nom_cle_composite,
)

# ===========================================================================
#  Fiche d'arrivee — modele §12.1
# ===========================================================================


class EtatFicheArrivee(enum.StrEnum):
    """§12.1 : « `state` | `draft`, `validated`, `published`, `archived` »."""

    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED = "archived"


ETATS_FICHE_ARRIVEE: tuple[str, ...] = tuple(membre.value for membre in EtatFicheArrivee)


class ArrivalProfile(ChampsCommuns, RessourceLocale, Base):
    """La fiche d'arrivee d'un nouvel arrivant — modele §12.1."""

    __tablename__ = "arrival_profile"

    entity_membership_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    #  §12.1 : « Obligatoire AVANT VALIDATION ». Nullable en base — une fiche
    #  `draft` toute neuve n'en porte pas encore — la contrainte ci-dessous
    #  n'exige la presence que passe l'etat `draft`.
    short_intro: Mapped[str | None] = mapped_column(Text, nullable=True)
    fun_fact: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_media_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    validated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #  §12.1 : « Un mois apres la date d'arrivee ». Calculee et ECRITE a la
    #  publication (`T3`) : la stocker evite de recalculer `arrival_date + 1
    #  mois` a chaque lecture de l'accueil, qui interroge potentiellement des
    #  centaines de fiches.
    recent_until: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("arrival_profile", "entity_membership"),
        ),
        #  `media_asset` est RessourceLocale, `entity_id` y est TOUJOURS NOT
        #  NULL : la cle composite est donc pleinement fiable, MATCH SIMPLE ne
        #  s'y derobe que si `photo_media_id` lui-meme est NULL — ce qui est le
        #  comportement voulu pour une photo facultative, comme `content_page`
        #  l'a deja fait pour `circle_id`/`office_id`.
        ForeignKeyConstraint(
            ["photo_media_id", "entity_id"],
            ["media_asset.id", "media_asset.entity_id"],
            name=nom_cle_composite("arrival_profile", "media_asset"),
        ),
        contrainte_enumeration("state", EtatFicheArrivee, "state_valide"),
        #  §6.2 : « une fiche par appartenance ». Jamais partielle : une fiche
        #  archivee garde son unicite, a la difference d'un slug ou d'un code —
        #  il ne peut logiquement pas exister DEUX fiches, meme historiques,
        #  pour la meme appartenance.
        UniqueConstraint("entity_membership_id", name="uq_arrival_profile_entity_membership_id"),
        CheckConstraint(
            #  `IS NOT NULL` EXPLICITE, ET CE N'EST PAS UNE REDONDANCE.
            #  `length(btrim(NULL))` rend NULL, et une CHECK CONSTRAINT dont
            #  l'expression rend NULL est SATISFAITE — seul FALSE la refuse.
            #  Sans cette clause, une fiche `validated` sans `short_intro`
            #  aurait ete acceptee : trouve par le temoin, pas par relecture.
            "state = 'draft' OR (short_intro IS NOT NULL AND length(btrim(short_intro)) > 0)",
            name="short_intro_requis_hors_brouillon",
        ),
        UniqueConstraint("id", "entity_id"),
    )


# ===========================================================================
#  Catalogue des taches — modele §13.1
# ===========================================================================


class OnboardingTaskReference(ChampsCommuns, Base):
    """Catalogue stable des taches reutilisables — modele §13.1.

    **PAS `RessourceLocale`** : `entity_id` est NULLABLE par le modele
    lui-meme, pour la tache GLOBALE. Voir l'en-tete du module.
    """

    __tablename__ = "onboarding_task_reference"

    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  §13.1 : « stable et unique DANS SON PERIMETRE ». Un `entity_id`
        #  nullable interdit une unicite simple — deux lignes `entity_id IS
        #  NULL` ne se heurtent JAMAIS sous un index classique, NULL n'etant
        #  jamais egal a NULL. Deux index PARTIELS, un par perimetre.
        Index(
            "uq_onboarding_task_reference_entity_code_non_archive",
            "entity_id",
            "code",
            unique=True,
            postgresql_where=text("entity_id IS NOT NULL AND archived_at IS NULL"),
        ),
        Index(
            "uq_onboarding_task_reference_code_globale_non_archive",
            "code",
            unique=True,
            postgresql_where=text("entity_id IS NULL AND archived_at IS NULL"),
        ),
    )


# ===========================================================================
#  Modeles et leurs versions — modele §13.2 a §13.4
# ===========================================================================


class PorteeDuModele(enum.StrEnum):
    """§13.2 : « `scope_type` | `GLOBAL`, `ENTITY`, `DSM`, `CIRCLE` »."""

    GLOBAL = "GLOBAL"
    ENTITY = "ENTITY"
    DSM = "DSM"
    CIRCLE = "CIRCLE"


PORTEES_DU_MODELE: tuple[str, ...] = tuple(membre.value for membre in PorteeDuModele)


class EtatDuModele(enum.StrEnum):
    """§13.2 : « `state` | `draft`, `active`, `archived` »."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


ETATS_DU_MODELE: tuple[str, ...] = tuple(membre.value for membre in EtatDuModele)


class OnboardingTemplate(ChampsCommuns, Base):
    """Conteneur logique d'un modele — modele §13.2.

    **PAS `RessourceLocale`** : `entity_id` est NULLABLE par le modele
    lui-meme, pour le modele GLOBAL. Voir l'en-tete du module.
    """

    __tablename__ = "onboarding_template"

    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    target_status: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    scope_circle_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["scope_person_id"], ["person.id"]),
        #  SIMPLE, et non composite — et ce n'est PAS le raisonnement tente
        #  puis abandonne : la contrainte structurelle ci-dessous garantit bien
        #  que `entity_id` de CETTE table est NOT NULL des que
        #  `scope_circle_id` l'est, mais `make isolation-check` exige
        #  `entity_id` NOT NULL a la SOURCE, sans condition — §4.14 de
        #  `CLAUDE.md`, defaut `T8-1` transpose. La coherence d'entite entre un
        #  modele CIRCLE et son cercle n'est donc PAS verifiee en base :
        #  residuel nomme, a instruire par le SERVICE en `T5`.
        ForeignKeyConstraint(["scope_circle_id"], ["circle.id"]),
        contrainte_enumeration("target_status", SituationProfessionnelle, "target_status_valide"),
        contrainte_enumeration("scope_type", PorteeDuModele, "scope_type_valide"),
        contrainte_enumeration("state", EtatDuModele, "state_valide"),
        #  §13.2, LES QUATRE CONTRAINTES DU MODELE, DERIVEES EN UNE SEULE
        #  IMPLICATION PAR PORTEE. « Un scope DSM exige un DSM actif dans
        #  l'entite » et « un scope CIRCLE exige un cercle de la MEME entite »
        #  ne sont pas verifiables en base — savoir si UNE personne est DSM
        #  ACTIF exige de lire `dsm_assignment` a l'instant present, ce qu'une
        #  contrainte de table ne peut pas faire. Ce que la base PEUT garantir,
        #  et garantit ici, est la FORME : quelle colonne est renseignee pour
        #  quelle portee.
        CheckConstraint(
            "(scope_type = 'GLOBAL' AND entity_id IS NULL "
            " AND scope_person_id IS NULL AND scope_circle_id IS NULL)"
            " OR (scope_type = 'ENTITY' AND entity_id IS NOT NULL"
            " AND scope_person_id IS NULL AND scope_circle_id IS NULL)"
            " OR (scope_type = 'DSM' AND entity_id IS NOT NULL"
            " AND scope_person_id IS NOT NULL AND scope_circle_id IS NULL)"
            " OR (scope_type = 'CIRCLE' AND entity_id IS NOT NULL"
            " AND scope_circle_id IS NOT NULL AND scope_person_id IS NULL)",
            name="colonnes_de_portee_selon_scope_type",
        ),
    )


class EtatDeLaVersionDuModele(enum.StrEnum):
    """§13.3 : « `state` | `draft`, `published`, `retired` ».

    **DISTINCTE DE `EtatDuModele`, ET C'EST LE RESIDU NOMME PAR `T1`, CORRIGE
    ICI.** Le conteneur (`onboarding_template`, §13.2) et sa version (§13.3)
    portent CHACUN une colonne `state`, mais avec des valeurs DIFFERENTES —
    `draft`/`active`/`archived` pour l'un, `draft`/`published`/`retired` pour
    l'autre. `T1` avait pose la migration `0020` en reutilisant `EtatDuModele`
    pour les deux, un defaut trouve en relisant le §13 en preparant `T4`
    (`compte-rendu-t4-lot-7.md` §2.6) : la contrainte `state_valide` de la
    version REFUSAIT `published`, la valeur meme que son cycle de vie exige.
    Migration `0021` : jamais une correction de `0020`, deja appliquee.
    """

    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


ETATS_DE_LA_VERSION_DU_MODELE: tuple[str, ...] = tuple(
    membre.value for membre in EtatDeLaVersionDuModele
)


class OnboardingTemplateVersion(ChampsCommuns, Base):
    """Une publication immuable d'un modele — modele §13.3.

    Pas d'`entity_id` propre : elle herite sa portee de `onboarding_template`,
    dont l'`entity_id` est nullable. Voir l'en-tete du module — c'est le motif
    exact qui interdit une cle composite ici.
    """

    __tablename__ = "onboarding_template_version"

    template_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #  **PAS la convention de `ChampsCommuns.created_by_person_id`.**
    #  `make isolation-check` exige une cle etrangere sur toute colonne `_id`
    #  qui n'est pas l'une des TROIS colonnes d'auteur nommees du §3.1 — ce
    #  n'en est pas une, c'est une colonne DOMAINE, comme
    #  `auth_event.person_id`. FK simple : `person` est globale.
    published_by_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["template_id"], ["onboarding_template.id"]),
        ForeignKeyConstraint(["published_by_person_id"], ["person.id"]),
        contrainte_enumeration("state", EtatDeLaVersionDuModele, "state_valide"),
        UniqueConstraint(
            "template_id", "version_number", name="uq_onboarding_template_version_number"
        ),
        CheckConstraint("version_number > 0", name="version_number_positif"),
    )


class OnboardingTemplateTask(ChampsCommuns, Base):
    """Une tache associee a une version — modele §13.4.

    Pas d'`entity_id` propre, pour le meme motif que `OnboardingTemplateVersion`.
    **La coherence d'entite entre `task_reference_id` et le modele qui la
    reutilise n'est PAS verifiee en base** : residuel nomme dans l'en-tete.
    """

    __tablename__ = "onboarding_template_task"

    template_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    task_reference_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    due_offset_days: Mapped[int] = mapped_column(Integer, nullable=False)
    title_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        #  NOMS EXPLICITES COURTS : la convention par defaut concatene table,
        #  colonne et table visee et depasse la limite de 63 octets de
        #  PostgreSQL sur ces deux cles — mesure, pas anticipe. Voir
        #  `noms_de_contraintes_trop_longs` en tete de `app/shared/modele.py`.
        ForeignKeyConstraint(
            ["template_version_id"],
            ["onboarding_template_version.id"],
            name=nom_cle_composite("onboarding_template_task", "onboarding_template_version"),
        ),
        ForeignKeyConstraint(
            ["task_reference_id"],
            ["onboarding_task_reference.id"],
            name=nom_cle_composite("onboarding_template_task", "onboarding_task_reference"),
        ),
        CheckConstraint("display_order >= 0", name="ordre_positif"),
        #  §25.1 « notamment » : deux taches de meme rang dans une version
        #  rendraient l'affichage non deterministe — meme motif que
        #  `content_block` au LOT 6.
        Index(
            "uq_onboarding_template_task_version_ordre_non_archive",
            "template_version_id",
            "display_order",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
    )


# ===========================================================================
#  Instances — modele §13.5 a §13.7
# ===========================================================================


class EtatInstance(enum.StrEnum):
    """§13.5 : « `state` | `active`, `completed`, `archived`, `replaced` »."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    REPLACED = "replaced"


ETATS_INSTANCE: tuple[str, ...] = tuple(membre.value for membre in EtatInstance)


class OnboardingInstance(ChampsCommuns, RessourceLocale, Base):
    """Un parcours affecte a une appartenance — modele §13.5."""

    __tablename__ = "onboarding_instance"

    entity_membership_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    template_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    reference_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_instance_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    replacement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("onboarding_instance", "entity_membership"),
        ),
        #  SIMPLE, et non composite : voir l'en-tete du module. NOM EXPLICITE
        #  COURT : voir le commentaire equivalent sur `OnboardingTemplateTask`.
        ForeignKeyConstraint(
            ["template_version_id"],
            ["onboarding_template_version.id"],
            name=nom_cle_composite("onboarding_instance", "onboarding_template_version"),
        ),
        #  COMPOSITE, contrairement a `template_version_id` juste au-dessus :
        #  les deux cotes sont `onboarding_instance`, dont l'`entity_id` est
        #  TOUJOURS NOT NULL — aucun piege MATCH SIMPLE ici, et §2.5 exige que
        #  le remplacement reste dans la MEME entite.
        ForeignKeyConstraint(
            ["replaced_by_instance_id", "entity_id"],
            ["onboarding_instance.id", "onboarding_instance.entity_id"],
            name=nom_cle_composite("onboarding_instance", "onboarding_instance_replacement"),
        ),
        contrainte_enumeration("state", EtatInstance, "state_valide"),
        #  §13.5 : « une SEULE instance active par appartenance ». Meme motif
        #  exact que `uq_entity_membership_person_id_occupante` au LOT 2 : un
        #  index unique PARTIEL, restreint a l'etat occupant.
        Index(
            "uq_onboarding_instance_membership_active",
            "entity_membership_id",
            unique=True,
            postgresql_where=text("state = 'active'"),
        ),
        UniqueConstraint("id", "entity_id"),
    )


class EtatTacheInstance(enum.StrEnum):
    """§13.6 : « `state` | `todo`, `completed`, `reopened`, `cancelled` »."""

    TODO = "todo"
    COMPLETED = "completed"
    REOPENED = "reopened"
    CANCELLED = "cancelled"


ETATS_TACHE_INSTANCE: tuple[str, ...] = tuple(membre.value for membre in EtatTacheInstance)


class OnboardingInstanceTask(ChampsCommuns, RessourceLocale, Base):
    """Snapshot d'une tache affectee — modele §13.6."""

    __tablename__ = "onboarding_instance_task"

    onboarding_instance_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    #  SIMPLE, et non composite : `onboarding_task_reference.entity_id` est
    #  nullable, voir l'en-tete du module.
    task_reference_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    title_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    description_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    due_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'todo'"))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #  PAS la convention `ChampsCommuns` : colonnes DOMAINE, pas les trois
    #  colonnes d'auteur du §3.1. `make isolation-check` exige une cle
    #  etrangere. FK simple : `person` est globale.
    completed_by_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    reopened_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_by_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    reopen_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["onboarding_instance_id", "entity_id"],
            ["onboarding_instance.id", "onboarding_instance.entity_id"],
            name=nom_cle_composite("onboarding_instance_task", "onboarding_instance"),
        ),
        ForeignKeyConstraint(["completed_by_person_id"], ["person.id"]),
        ForeignKeyConstraint(["reopened_by_person_id"], ["person.id"]),
        ForeignKeyConstraint(
            ["task_reference_id"],
            ["onboarding_task_reference.id"],
            name=nom_cle_composite("onboarding_instance_task", "onboarding_task_reference"),
        ),
        contrainte_enumeration("state", EtatTacheInstance, "state_valide"),
        #  Matrice §8.3, a la lettre : « La reouverture EXIGE un motif ». Une
        #  reouverture sans raison n'est pas une reouverture partielle, c'est
        #  une ligne invalide.
        CheckConstraint(
            "reopened_at IS NULL OR reopen_reason IS NOT NULL",
            name="motif_requis_a_la_reouverture",
        ),
        #  Une tache n'apparait qu'une fois par instance.
        UniqueConstraint(
            "onboarding_instance_id",
            "task_reference_id",
            name="uq_onboarding_instance_task_reference",
        ),
        UniqueConstraint("id", "entity_id"),
    )


class TypeEvenementTache(enum.StrEnum):
    """§13.7, les evenements DECRITS en prose, jamais enumeres en colonnes.

    Six evenements, un par ligne du §13.7 : affectation, completion, annulation
    dans les cinq minutes, reouverture administrative, conservation lors d'un
    remplacement, annulation lors d'un changement de parcours.
    """

    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REOPENED = "REOPENED"
    RETAINED_ON_REPLACEMENT = "RETAINED_ON_REPLACEMENT"
    CANCELLED_ON_REPLACEMENT = "CANCELLED_ON_REPLACEMENT"


TYPES_EVENEMENT_TACHE: tuple[str, ...] = tuple(membre.value for membre in TypeEvenementTache)


class OnboardingTaskEvent(ChampsCommuns, RessourceLocale, Base):
    """Journal des changements d'etat d'une tache d'instance — modele §13.7.

    Meme nature que `auth_event` (LOT 3) : un journal d'evenements, un acteur
    NULLABLE — une archivage automatique n'a pas d'acteur humain — et une
    raison facultative.
    """

    __tablename__ = "onboarding_task_event"

    onboarding_instance_task_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True
    )
    actor_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["onboarding_instance_task_id", "entity_id"],
            ["onboarding_instance_task.id", "onboarding_instance_task.entity_id"],
            name=nom_cle_composite("onboarding_task_event", "onboarding_instance_task"),
        ),
        ForeignKeyConstraint(["actor_person_id"], ["person.id"]),
        contrainte_enumeration("event_type", TypeEvenementTache, "event_type_valide"),
    )
