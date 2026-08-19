"""Cercles, bureaux et appartenance aux cercles — modele §8.1 a §8.3.

LOT 2, sous-etape `T7`, stories `MVP-L02-US001` et `US003`.

FONDEMENT — modele §8.1 `circle`, §8.2 `circle_membership`, §8.3 `office`,
contraintes §25.1 a §25.4, point 7 de l'ordre du §28.

QUATRE LECTURES, ET LA PREMIERE EVITE UN CONTRESENS.

  1. **AUCUNE EXCLUSION SUR `(entity_membership_id, period)` TOUT COURT.** Le §8.2
     autorise explicitement « plusieurs cercles secondaires actifs » : une
     exclusion sur la seule appartenance les interdirait tous sauf un. Le §25.2 ne
     liste d'ailleurs que le « cercle PRINCIPAL » parmi les relations a contrainte
     temporelle. L'exclusion est donc **PARTIELLE**, restreinte au type
     `principal`.

  2. **LE §25.1 ECRIT SON INDEX LITTERALEMENT**, sur DEUX conditions :
     `circle_membership(entity_membership_id) UNIQUE WHERE
     membership_type='principal' AND ends_at IS NULL`. Il est **OMBRAGE** par
     l'exclusion partielle -- deux principaux actifs ont tous deux `ends_at` a
     NULL, donc des plages non bornees qui se chevauchent toujours.

     **Il est neanmoins conserve, et la difference avec `T5` est nette** : en `T5`
     les deux index retires etaient MA derivation, absente du §25.1. Celui-ci est
     ecrit dans le modele. Meme parti que `ck_entity_membership_depart_apres_
     arrivee` en `T4` : une contrainte ombragee ne coute rien, et redevient la
     seule barriere si l'autre change.

  3. **« DEUX RELATIONS ACTIVES IDENTIQUES AU MEME CERCLE » EST UNE REGLE
     DISTINCTE**, et elle vaut pour les DEUX types. Un index partiel sur
     `(entity_membership_id, circle_id) WHERE ends_at IS NULL` la porte. Elle
     n'empeche pas plusieurs cercles secondaires : ce sont des cercles
     DIFFERENTS, donc des couples differents.

  4. **DEUX REGLES DU §8 NE SONT PAS DE CE RESSORT** :
     - « la couleur ne constitue jamais la seule information visuelle » (§8.1) est
       une regle d'INTERFACE. Elle appartient au LOT 6, avec les contenus, et le
       design system de `T10` du LOT 1 l'a deja anticipee -- ses jetons de marque
       sont des SURFACES portant un texte apparie mesure ;
     - « le Booster d'un cercle secondaire ne modifie pas le cercle principal, le
       DSM, le client ou le statut » (§8.2) porte sur des tables dont trois
       n'existent pas encore. Regle de NON-EFFET, a eprouver en `T9` ou `T10`.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import (
    Base,
    ChampsCommuns,
    Periode,
    RessourceLocale,
    contrainte_enumeration,
    nom_cle_composite,
    nom_exclusion,
)


class TypeAppartenanceCercle(enum.StrEnum):
    """§8.2 : « `membership_type` | `principal` ou `secondary` »."""

    PRINCIPAL = "principal"
    SECONDARY = "secondary"


TYPES_APPARTENANCE_CERCLE: tuple[str, ...] = tuple(
    membre.value for membre in TypeAppartenanceCercle
)


class Circle(ChampsCommuns, RessourceLocale, Base):
    """Cercle d'une entite — modele §8.1."""

    __tablename__ = "circle"

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    #  §8.1 : « `color_token` | Reference de couleur LOCALE ». Une reference, donc
    #  une chaine courte, et non une valeur hexadecimale : le design system de
    #  `packages/ui` porte les couleurs, et une valeur en base contournerait ses
    #  contrastes mesures. Facultative : le §8.1 ne la declare pas obligatoire.
    color_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  §25.1 litteralement : `circle(entity_id, code) UNIQUE WHERE archived_at
        #  IS NULL`. Partiel, comme `job_catalog` : un cercle archive libere son
        #  code.
        Index(
            "uq_circle_entity_id_code_non_archive",
            "entity_id",
            "code",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : cible des cles composites de `circle_membership` et, en `T8`, de
        #  `framework_responsibility_assignment`.
        UniqueConstraint("id", "entity_id"),
        Index("ix_circle_entity_id_display_order", "entity_id", "display_order"),
    )


class Office(ChampsCommuns, RessourceLocale, Base):
    """Bureau d'une entite — modele §8.3.

    Le §8.3 ne pose AUCUNE contrainte propre. La seule regle qui le concerne est
    au §25.4 -- « un bureau publie avec un a trois responsables actifs » -- et elle
    porte sur `framework_responsibility_assignment`, qui arrive en `T8`.
    """

    __tablename__ = "office"

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  §25.1 litteralement : `office(entity_id, code) UNIQUE WHERE archived_at
        #  IS NULL`.
        Index(
            "uq_office_entity_id_code_non_archive",
            "entity_id",
            "code",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : cible des cles composites de `T8`.
        UniqueConstraint("id", "entity_id"),
        Index("ix_office_entity_id_display_order", "entity_id", "display_order"),
    )


class CircleMembership(ChampsCommuns, RessourceLocale, Periode, Base):
    """Historise l'appartenance d'une personne a un cercle — modele §8.2.

    TROIS CONTRAINTES POUR TROIS REGLES DISTINCTES, et il faut les distinguer :

      - `uq_..._principal_actif`    §25.1 : un seul cercle PRINCIPAL actif par
                                   appartenance ;
      - `ex_..._principal`          §25.2 : les periodes des cercles PRINCIPAUX ne
                                   se chevauchent pas. **PARTIELLE** : elle ne
                                   s'applique qu'au type `principal`, sans quoi
                                   elle interdirait les cercles secondaires
                                   multiples que le §8.2 autorise explicitement ;
      - `uq_..._cercle_actif`       §8.2 : « une meme personne ne peut pas avoir
                                   deux relations ACTIVES identiques au meme
                                   cercle ». Vaut pour les DEUX types, et
                                   n'empeche pas plusieurs secondaires -- ce sont
                                   des cercles DIFFERENTS.
    """

    __tablename__ = "circle_membership"

    entity_membership_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    circle_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    membership_type: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        #  §25.3 : « le cercle de la MEME entite », §8.2. Cles COMPOSITES, comme en
        #  `T5` : une paire de cles simples laisserait rattacher une appartenance
        #  de Bordeaux a un cercle de Lille.
        ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("circle_membership", "entity_membership"),
        ),
        ForeignKeyConstraint(
            ["circle_id", "entity_id"],
            ["circle.id", "circle.entity_id"],
            name=nom_cle_composite("circle_membership", "circle"),
        ),
        contrainte_enumeration("membership_type", TypeAppartenanceCercle, "membership_type_valide"),
        #  §25.1, litteralement, sur DEUX conditions.
        Index(
            "uq_circle_membership_principal_actif",
            "entity_membership_id",
            unique=True,
            postgresql_where=text("membership_type = 'principal' AND ends_at IS NULL"),
        ),
        #  §8.2 : « deux relations actives identiques au meme cercle ».
        Index(
            "uq_circle_membership_cercle_actif",
            "entity_membership_id",
            "circle_id",
            unique=True,
            postgresql_where=text("ends_at IS NULL"),
        ),
        #  §25.2, « cercle principal ». PARTIELLE : voir la lecture 1 du module.
        ExcludeConstraint(
            ("entity_membership_id", "="),
            ("period", "&&"),
            name=nom_exclusion("circle_membership", "principal_sans_chevauchement"),
            using="gist",
            where=text("membership_type = 'principal'"),
        ),
        Index("ix_circle_membership_circle_id_ends_at", "circle_id", "ends_at"),
    )


# ===========================================================================
#  Responsabilites Framework, DSM et roles techniques
#  LOT 2, sous-etape `T8`, story `MVP-L02-US004`
# ===========================================================================
#
#  FONDEMENT — modele §8.4 `framework_responsibility_assignment`, §8.5
#  `dsm_assignment`, §8.6 `technical_role_assignment`, contraintes §25.1 a §25.4,
#  point 8 de l'ordre du §28.
#
#  DEUX PERMISSIONS A NE PAS PRENDRE POUR DES INTERDICTIONS -- meme piege qu'en
#  `T7` avec les cercles secondaires.
#
#    - « une personne peut etre Booster de PLUSIEURS CERCLES d'une meme entite »
#      (§8.4) est une PERMISSION. Un index unique sur `person_id WHERE
#      responsibility_type='BOOSTER' AND ends_at IS NULL` l'interdirait ;
#    - « un DSM peut suivre PLUSIEURS CONSULTANTS » (§8.5) de meme : aucune
#      unicite sur `dsm_person_id`.
#
#  ET L'INTERDICTION VOISINE N'EST PAS EXPRIMABLE PAR UN INDEX. « Une personne ne
#  peut pas etre Booster active dans PLUSIEURS ENTITES simultanement » (§8.4)
#  demande que toutes les lignes `BOOSTER` actives d'une personne partagent la
#  MEME entite. Un index unique ne sait pas exprimer « au plus une valeur
#  distincte » : il exprime « au plus une ligne ». C'est donc un declencheur.
#
#  UNE REGLE DU §25.4 N'EST PAS APPLICABLE, ET C'EST UN ECART. « Un bureau PUBLIE
#  possede entre un et trois responsables actifs » (§8.4) suppose un etat de
#  publication sur `office` -- or le §8.3 n'en declare AUCUN : ses champs sont
#  `entity_id`, `code`, `name`, `description`, `location_text`, `display_order`.
#  **La condition du declencheur n'existe pas.** Voir `ECART-031` : la regle est
#  consignee, non inventee.


class TypeResponsabilite(enum.StrEnum):
    """§8.4 : `DSM`, `ESM`, `BOOSTER`, `OFFICE_MANAGER`.

    En MAJUSCULES, contrairement aux autres enumerations de ce lot : c'est ainsi
    que le §8.4 les ecrit, et que le §25.1 les cite -- `responsibility_type =
    'BOOSTER'`. Les noms suivent le modele a la lettre (`DEC-499`).
    """

    DSM = "DSM"
    ESM = "ESM"
    BOOSTER = "BOOSTER"
    OFFICE_MANAGER = "OFFICE_MANAGER"


TYPES_RESPONSABILITE: tuple[str, ...] = tuple(membre.value for membre in TypeResponsabilite)


class TypeRoleTechnique(enum.StrEnum):
    """§8.6 : `ENTITY_ADMIN` porte sur une entite, `SUPER_ADMIN` est global."""

    ENTITY_ADMIN = "ENTITY_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


TYPES_ROLE_TECHNIQUE: tuple[str, ...] = tuple(membre.value for membre in TypeRoleTechnique)


class FrameworkResponsibilityAssignment(ChampsCommuns, Periode, Base):
    """Responsabilites Framework, table generique — modele §8.4, `ARB-DATA-002`.

    `entity_id` est declaree A LA MAIN et NON NULL : le §8.4 l'ecrit « entite de
    responsabilite », donc obligatoire. Le mixin `RessourceLocale` ferait l'affaire,
    mais les cles composites vers `circle` et `office` doivent apparier `entity_id`,
    et les colonnes de portee sont NULLABLES -- une cle composite dont une colonne
    est nulle n'est pas verifiee, ce qui est exactement le comportement voulu.
    """

    __tablename__ = "framework_responsibility_assignment"

    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    responsibility_type: Mapped[str] = mapped_column(String(32), nullable=False)

    #  §8.4 : « obligatoire UNIQUEMENT pour BOOSTER » et « uniquement pour
    #  OFFICE_MANAGER ». Nullables, donc, et les trois contraintes de verification
    #  ci-dessous portent la regle.
    circle_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    office_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    assigned_by_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    #  §8.4 : « obligatoire pour changement sensible ». Le modele ne dit PAS ce
    #  qu'est un changement sensible : la colonne est donc nullable, et la regle
    #  releve du service qui saura de quel changement il s'agit. L'inventer ici
    #  serait decider a la place du LOT 3.
    assignment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  Nom explicite : la convention rendait 67 caracteres. Et un nom par ROLE
        #  est necessaire -- deux cles de cette table visent `person`, elles ne
        #  peuvent pas porter le meme nom.
        ForeignKeyConstraint(
            ["assigned_by_person_id"],
            ["person.id"],
            name="fk_framework_responsibility_assignment_assigned_by",
        ),
        #  §25.3 : cles COMPOSITES vers les ressources locales de portee. Une cle
        #  composite dont une colonne vaut NULL n'est pas verifiee par PostgreSQL,
        #  ce qui convient : `circle_id` est nul pour un `DSM`.
        ForeignKeyConstraint(
            ["circle_id", "entity_id"],
            ["circle.id", "circle.entity_id"],
            name=nom_cle_composite("framework_responsibility", "circle"),
        ),
        ForeignKeyConstraint(
            ["office_id", "entity_id"],
            ["office.id", "office.entity_id"],
            name=nom_cle_composite("framework_responsibility", "office"),
        ),
        #  Nom COURT : `responsibility_type_valide` aurait donne 65 caracteres avec
        #  le prefixe de la convention, pour une limite de 63. Le controle
        #  `noms_de_contraintes_trop_longs` l'a attrape.
        contrainte_enumeration("responsibility_type", TypeResponsabilite, "type_valide"),
        #  Les TROIS regles de portee du §8.4, en une seule contrainte : chaque
        #  type impose exactement l'etat de ses deux colonnes de portee. Une
        #  contrainte par type aurait donne trois messages differents pour une
        #  seule notion, et un type oublie serait passe entre les trois.
        CheckConstraint(
            "(responsibility_type = 'BOOSTER' "
            "AND circle_id IS NOT NULL AND office_id IS NULL) "
            "OR (responsibility_type = 'OFFICE_MANAGER' "
            "AND office_id IS NOT NULL AND circle_id IS NULL) "
            "OR (responsibility_type IN ('DSM', 'ESM') "
            "AND circle_id IS NULL AND office_id IS NULL)",
            name="portee_selon_le_type",
        ),
        #  §25.1, ECRIT LITTERALEMENT, sur DEUX conditions :
        #  `framework_responsibility_assignment(circle_id) UNIQUE WHERE
        #  responsibility_type='BOOSTER' AND ends_at IS NULL`. Un cercle a un seul
        #  Booster actif.
        Index(
            "uq_framework_responsibility_booster_actif_par_cercle",
            "circle_id",
            unique=True,
            postgresql_where=text("responsibility_type = 'BOOSTER' AND ends_at IS NULL"),
        ),
        #  §25.2, « responsabilites » : TROIS exclusions PARTIELLES, et la raison
        #  est un defaut mesure.
        #
        #  **UNE CLE D'EXCLUSION CONTENANT UNE COLONNE NULLABLE NE CONTRAINT RIEN
        #  SUR LES LIGNES OU ELLE EST NULLE.** Ma premiere version mettait
        #  `circle_id` dans une exclusion unique. Or `circle_id` est NUL pour un
        #  `DSM` ou un `ESM`, et l'operateur `=` ne rapproche jamais deux NULL :
        #  deux `DSM` de la meme personne aux periodes qui se chevauchent
        #  n'auraient PAS ete detectes. La contrainte aurait existe sans rien
        #  garantir sur trois types sur quatre.
        #
        #  Chaque exclusion porte donc sur une cle SANS colonne nullable, et sa
        #  clause `WHERE` garantit cette absence de NULL par construction -- la
        #  contrainte `portee_selon_le_type` l'assurant deja.
        #
        #  CE QU'ELLES EMPECHENT, ET RIEN DE PLUS : deux affectations IDENTIQUES
        #  qui se chevauchent. Le §8.4 ne dit rien de la multiplicite pour `DSM`,
        #  `ESM` et `OFFICE_MANAGER` : imposer « une seule active par personne »
        #  serait inventer. Et il autorise EXPLICITEMENT plusieurs cercles pour un
        #  `BOOSTER`, ce que la premiere cle respecte en incluant `circle_id`.
        ExcludeConstraint(
            ("person_id", "="),
            ("circle_id", "="),
            ("period", "&&"),
            name=nom_exclusion("framework_responsibility_assignment", "booster"),
            using="gist",
            where=text("responsibility_type = 'BOOSTER'"),
        ),
        ExcludeConstraint(
            ("person_id", "="),
            ("office_id", "="),
            ("period", "&&"),
            name=nom_exclusion("framework_responsibility_assignment", "office_manager"),
            using="gist",
            where=text("responsibility_type = 'OFFICE_MANAGER'"),
        ),
        ExcludeConstraint(
            ("person_id", "="),
            ("responsibility_type", "="),
            ("period", "&&"),
            name=nom_exclusion("framework_responsibility_assignment", "sans_portee"),
            using="gist",
            where=text("responsibility_type IN ('DSM', 'ESM')"),
        ),
        Index(
            "ix_framework_responsibility_entity_id_type_ends_at",
            "entity_id",
            "responsibility_type",
            "ends_at",
        ),
    )


class DsmAssignment(ChampsCommuns, RessourceLocale, Periode, Base):
    """Relation entre un consultant et son DSM — modele §8.5."""

    __tablename__ = "dsm_assignment"

    consultant_membership_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    #  §8.5 : « personne possedant une responsabilite DSM ACTIVE ». La cle
    #  etrangere garantit que la personne existe ; qu'elle ait la responsabilite
    #  active est une regle INTER-TABLES, portee par declencheur.
    dsm_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["dsm_person_id"], ["person.id"]),
        #  §8.5 : « MEME entite ». Cle composite du §25.3.
        ForeignKeyConstraint(
            ["consultant_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("dsm_assignment", "entity_membership"),
        ),
        #  §25.1, ecrit litteralement : `dsm_assignment(consultant_membership_id)
        #  UNIQUE WHERE ends_at IS NULL`. OMBRAGE par l'exclusion ci-dessous --
        #  deux periodes ouvertes se chevauchent toujours -- mais conserve parce
        #  que le §25.1 l'ecrit. Meme parti qu'en `T7`, et l'inverse de `T5` ou les
        #  index retires etaient une derivation.
        Index(
            "uq_dsm_assignment_consultant_actif",
            "consultant_membership_id",
            unique=True,
            postgresql_where=text("ends_at IS NULL"),
        ),
        #  §8.5 et §25.2 : « les periodes ne se chevauchent pas POUR LE
        #  CONSULTANT ». Sur le consultant, donc, et non sur le DSM : « un DSM peut
        #  suivre plusieurs consultants » est une PERMISSION.
        ExcludeConstraint(
            ("consultant_membership_id", "="),
            ("period", "&&"),
            name=nom_exclusion("dsm_assignment", "sans_chevauchement"),
            using="gist",
        ),
        Index("ix_dsm_assignment_dsm_person_id_ends_at", "dsm_person_id", "ends_at"),
    )


class TechnicalRoleAssignment(ChampsCommuns, Periode, Base):
    """Roles techniques, separes du Framework — modele §8.6.

    `entity_id` est NULLABLE, et c'est le §8.6 qui l'exige : « `SUPER_ADMIN` |
    Globale, `entity_id` nul ». Le mixin `RessourceLocale` la poserait `NOT NULL`,
    comme pour `allowed_email_domain` en `T2` et `client_alias` en `T6`.

    DEUX REGLES DU §8.6 NE SONT PAS DE CE RESSORT, et elles sont dites :
    « toute creation ou cloture est auditee » et « l'attribution d'un
    super-administrateur declenche une alerte de securite » supposent
    `audit_event` et `operational_alert`, §21.1 et §21.2 -- **LOT 10**.
    """

    __tablename__ = "technical_role_assignment"

    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    role_type: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        contrainte_enumeration("role_type", TypeRoleTechnique, "role_type_valide"),
        #  §8.6, litteralement : `ENTITY_ADMIN` porte sur UNE entite,
        #  `SUPER_ADMIN` est global avec `entity_id` NUL.
        CheckConstraint(
            "(role_type = 'ENTITY_ADMIN' AND entity_id IS NOT NULL) "
            "OR (role_type = 'SUPER_ADMIN' AND entity_id IS NULL)",
            name="portee_selon_le_role",
        ),
        #  §25.2, « roles techniques ». Sur le couple (personne, role) : une meme
        #  personne peut etre `ENTITY_ADMIN` et `SUPER_ADMIN`, le §8.6 ne
        #  l'interdisant pas. `entity_id` entre dans la cle pour qu'une personne
        #  puisse administrer deux entites simultanement -- le §8.6 ne l'interdit
        #  pas davantage.
        ExcludeConstraint(
            ("person_id", "="),
            ("role_type", "="),
            ("entity_id", "="),
            ("period", "&&"),
            name=nom_exclusion("technical_role_assignment", "sans_chevauchement"),
            using="gist",
        ),
    )
