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
