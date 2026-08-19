"""Les quatre tables du modele de donnees §5.

LOT 2, sous-etape `T2`, story `MVP-L02-US001`.

FONDEMENT — modele de donnees §5.1 `entity`, §5.2 `platform_setting`, §5.3
`entity_setting`, §5.4 `allowed_email_domain`. Champs communs du §3.1.

TROIS LECTURES DU MODELE, POSEES ICI PLUTOT QUE SUPPOSEES.

  1. **Le §5.1 enumere ses colonnes ; les §5.2 et §5.3 n'en enumerent AUCUNE.**
     Ils decrivent des CATEGORIES de parametres -- identite visuelle, durees de
     session, textes d'accueil, contact RGPD -- dont la plupart appartiennent a
     des lots ulterieurs. Inventer un schema de colonnes, ou un catalogue de
     cles, serait exactement ce que la regle §6.5 interdit. Ces deux tables sont
     donc des tables cle / valeur SANS catalogue de cles : chaque lot declarera
     les siennes quand il en aura besoin.

  2. **`allowed_email_domain.entity_id` est NULLABLE**, le §5.4 l'ecrit
     explicitement : « nullable pour un domaine global ». Le mixin
     `RessourceLocale` la declare `NOT NULL` et ne s'applique donc PAS a cette
     table. La colonne est declaree a la main.

  3. **Le §25.2 ne liste PAS `allowed_email_domain`** parmi les relations a
     contrainte temporelle -- il nomme l'appartenance, le metier, le statut, le
     DSM, le cercle principal, les responsabilites et les roles techniques.
     Aucune contrainte d'exclusion n'est donc posee ici : ce serait exiger plus
     que le modele. Le mixin `Periode` est utilise pour ses colonnes, ce qui
     laisse la porte ouverte -- `btree_gist` et la colonne `period` sont deja la,
     donc l'ajouter plus tard serait une migration d'une ligne.

UNE REDONDANCE DU MODELE, ET LA LECTURE RETENUE. Le §5.2 cite « domaines e-mail
autorises » parmi les categories de `platform_setting`, alors que le §5.4 leur
consacre une table. **La table fait autorite** : une table dediee avec ses
colonnes nommees l'emporte sur un libelle dans une liste a puces. Aucune cle de
parametre ne portera de domaine.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import (
    Base,
    ChampsCommuns,
    Periode,
    RessourceLocale,
    contrainte_enumeration,
)


class StatutEntite(enum.StrEnum):
    """Les quatre valeurs du §5.1, dans l'ordre du cycle de vie."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


STATUTS_ENTITE: tuple[str, ...] = tuple(membre.value for membre in StatutEntite)

#  Motif d'une cle de parametre. Il ne dit RIEN des cles admises -- il n'y a pas
#  de catalogue -- seulement de leur FORME : minuscules, chiffres, tirets bas, et
#  des points pour la hierarchie, par exemple `session.duree_minutes`. Une forme
#  contrainte permet de retrouver une famille de cles par prefixe sans avoir a
#  deviner comment elles ont ete ecrites.
MOTIF_CLE_PARAMETRE = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$"


class Entity(ChampsCommuns, Base):
    """Une implantation eXalt — modele §5.1.

    `entity` est un referentiel GLOBAL : elle ne porte pas `entity_id`, et le
    mixin `RessourceLocale` ne s'applique donc pas.

    Les champs communs du §3.1 s'ajoutent aux colonnes du §5.1. Le §5.1 nomme
    deja `created_at` et `archived_at`, qui sont les memes ; il ne nomme pas
    `updated_at`, `version`, ni les colonnes d'auteur, que le §3.1 pose sur « les
    principales tables metier ». `entity` en est une.

    `activated_at` est propre a cette table : c'est elle qui rend la regle
    « `code` immuable apres activation » verifiable, et le declencheur pose par
    la migration `0003` s'appuie dessus.
    """

    __tablename__ = "entity"

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)

    #  Le §5.1 dit « `FR` dans le MVP », ce qui decrit la donnee attendue et non
    #  une contrainte : borner a `FR` empecherait la seconde entite fictive que
    #  la demonstration du lot reclame si elle etait etrangere. La longueur est
    #  bornee a 2, forme ISO 3166-1 alpha-2.
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False)

    #  IANA, par exemple `Europe/Paris`. Aucune validation en base : la liste des
    #  fuseaux vit dans le systeme d'exploitation et change avec lui. Une
    #  contrainte figee ici deviendrait fausse a la premiere mise a jour de
    #  tzdata, sans que rien ne le signale.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    #  `DateTime(timezone=True)` EXPLICITE. Sans lui, SQLAlchemy produit un
    #  `timestamp WITHOUT time zone`, alors que le §5.1 ecrit `timestamptz`. Le
    #  defaut a ete releve a la lecture du brouillon d'`autogenerate`, pas par un
    #  test : c'est exactement l'usage que `DEC-500` prevoit pour ce brouillon.
    activated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        #  §25.1 : `entity(code) UNIQUE`, sans clause partielle. Une entite
        #  archivee garde donc son code reserve, ce qui est voulu : le §5.1 dit
        #  « stable », et reattribuer le code d'une entite archivee rendrait
        #  ambigus tous les journaux d'audit qui le citent.
        UniqueConstraint("code", name="code_unique"),
        contrainte_enumeration("status", StatutEntite, "status_valide"),
        Index("ix_entity_status", "status"),
    )


class PlatformSetting(ChampsCommuns, Base):
    """Parametres globaux de la plateforme — modele §5.2.

    Table cle / valeur, SANS catalogue de cles : voir la lecture 1 en tete de
    module. Le §5.2 pose une interdiction que le code doit respecter : « les
    secrets ne sont jamais enregistres dans cette table ». Elle n'est pas
    exprimable en SQL -- rien ne distingue un secret d'une chaine quelconque --
    et releve donc du service et de la revue.
    """

    __tablename__ = "platform_setting"

    key: Mapped[str] = mapped_column(String(128), nullable=False)

    #  `jsonb` et non `text` : un parametre peut porter une valeur structuree --
    #  une liste de liens internes, un couple de seuils. Le §3.1 avertit que
    #  « `jsonb` ne doit pas remplacer une vraie relation metier » : ici il ne
    #  remplace rien, il porte une valeur de configuration. Les relations
    #  metier ont leurs propres tables.
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("key", name="key_unique"),
        #  La contrainte porte sur la FORME de la cle, pas sur la liste des cles
        #  admises. Un catalogue en base devrait etre modifie par chacun des
        #  douze lots restants.
        CheckConstraint(f"key ~ '{MOTIF_CLE_PARAMETRE}'", name="key_forme_valide"),
    )


class EntitySetting(ChampsCommuns, RessourceLocale, Base):
    """Parametres locaux d'une entite — modele §5.3.

    Ressource LOCALE, donc `entity_id` obligatoire, apporte par le mixin.

    La cle etrangere n'est pas composite ici : le §25.3 impose des couples
    `(id, entity_id)` pour empecher qu'une ressource locale reference une
    ressource locale d'une AUTRE entite. `entity_setting` ne reference aucune
    ressource locale -- seulement son entite. Le sujet est traite en `T11`.
    """

    __tablename__ = "entity_setting"

    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        #  Cle etrangere vers l'entite, et elle n'est pas facultative. Le cahier
        #  §22.2 pose que « toutes les ressources locales comportent un
        #  `entity_id` OU une relation VERIFIABLE vers une entite ». Une colonne
        #  `uuid` sans contrainte n'est pas verifiable : elle pourrait pointer
        #  vers une entite inexistante, et le §2.5 du modele pose le refus par
        #  defaut. `ondelete` n'est PAS declare : une entite ne se supprime pas,
        #  elle s'archive (§2.4), et une suppression en cascade des parametres
        #  d'une entite serait une perte silencieuse.
        #  AUCUN `name=` : un nom explicite ECRASE la convention de nommage du
        #  socle. Mesure du 19/08/2026 -- avec `name="entity"`, les deux tables
        #  locales portaient une contrainte appelee `entity` tout court, ce que
        #  PostgreSQL accepte puisque les noms sont propres a chaque table, mais
        #  qui ne dit ni d'ou ni vers ou. Sans `name=`, la convention produit
        #  `fk_<table>_<colonne>_<table_visee>`.
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        UniqueConstraint("entity_id", "key", name="entite_cle_unique"),
        CheckConstraint(f"key ~ '{MOTIF_CLE_PARAMETRE}'", name="key_forme_valide"),
    )


class AllowedEmailDomain(ChampsCommuns, Periode, Base):
    """Domaine e-mail autorise — modele §5.4.

    `entity_id` est declaree A LA MAIN et NULLABLE : le §5.4 ecrit « nullable
    pour un domaine global ». Le mixin `RessourceLocale` la poserait `NOT NULL`.

    `active` et la periode coexistent parce que le §5.4 demande les deux.
    Lecture retenue : `active` est un interrupteur explicite, que
    l'authentification consulte ; la periode est l'historisation. Les deux
    peuvent donc etre vrais sans se contredire -- un domaine peut etre dans sa
    periode de validite et neanmoins desactive.
    """

    __tablename__ = "allowed_email_domain"

    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    __table_args__ = (
        #  Cle etrangere NULLABLE : PostgreSQL n'exige rien quand la colonne
        #  vaut NULL, ce qui est exactement le « domaine global » du §5.4. Une
        #  valeur non nulle, elle, doit designer une entite existante.
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  Normalise « sans `@` », §5.4. La contrainte verifie la forme : au
        #  moins un point, minuscules, aucun `@`, aucune espace. Elle ne valide
        #  pas l'existence du domaine, ce qui n'est pas verifiable en base.
        CheckConstraint(
            r"domain ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'",
            name="domain_normalise",
        ),
        Index("ix_allowed_email_domain_domain_active", "domain", "active"),
    )
