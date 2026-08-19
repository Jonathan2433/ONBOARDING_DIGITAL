"""`person` — l'identite globale d'une personne.

LOT 2, sous-etape `T3`, story `MVP-L02-US002`.

FONDEMENT — modele de donnees §6.1, contraintes du §25.1, arbitrage
`ARB-DATA-001` : « conserver une identite globale unique et placer toutes les
donnees locales dans l'appartenance a l'entite ».

`person` EST GLOBALE. Elle ne porte donc PAS `entity_id`, et le mixin
`RessourceLocale` ne s'y applique pas. Tout ce qui est propre a une entite --
metier, statut professionnel, cercle, DSM -- vit dans `entity_membership` et ses
satellites, a partir de `T4`.

AUCUNE TABLE D'AUTHENTIFICATION ICI. Le §28 du modele groupe « `person` et
authentification » a son point 3, mais c'est un ordre GLOBAL sur dix-sept etapes
couvrant tous les lots : il dit ou placer l'authentification quand on y arrivera,
pas qu'il faut la faire maintenant. `user_account`, `magic_link_request`,
`user_session` et `auth_event` appartiennent au **LOT 3**. Rien ne les exige plus
tot : c'est `user_account` qui reference `person`, jamais l'inverse.

DEUX PASSAGES DU CORPUS A CONCILIER, ET LA LECTURE RETENUE.

  Le §6.1 exige « unicite INSENSIBLE A LA CASSE de `email_normalized` ». Le §25.1
  ecrit `person(email_normalized) UNIQUE`, c'est-a-dire un index SIMPLE, qui est
  sensible a la casse.

  Les deux se concilient sans choisir : une contrainte exige que la valeur
  STOCKEE soit deja en minuscules. L'insensibilite devient alors structurelle --
  deux graphies du meme e-mail ne peuvent pas coexister, puisque l'une des deux
  ne peut pas etre ecrite -- et l'index simple du §25.1 suffit.

  C'est plus fort qu'un index fonctionnel sur `lower(email_normalized)` : celui-ci
  empecherait le doublon mais laisserait entrer une valeur non normalisee, alors
  que la colonne s'appelle `_normalized`.

CE QUE LA NORMALISATION NE FAIT PAS, ET C'EST DELIBERE. Elle met en minuscules et
retire les espaces de bordure. Elle ne retire PAS les points, ne coupe PAS a un
`+`, et ne touche a aucune particularite de fournisseur. Ces regles-la
fusionneraient des personnes DISTINCTES, et aucun document du corpus ne les
demande.

UNE REGLE DU §6.1 QUI N'EST PAS DE CETTE SOUS-ETAPE : « le nom et l'e-mail ne
sont pas dupliques dans les tables d'appartenance ». Elle porte sur
`entity_membership`, qui n'existe pas encore -- sous-etape `T4`.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import (
    Base,
    ChampsCommuns,
    RessourceLocale,
    contrainte_enumeration,
    nom_exclusion,
)


class EtatCompte(enum.StrEnum):
    """Les cinq valeurs du §6.1, dans l'ordre du cycle de vie.

    `ANONYMIZED` est terminal : le §6.1 pose qu'« une personne anonymisee ne peut
    pas etre reactivee sans creation d'une nouvelle identite ». La regle est
    portee par un declencheur, la migration `0004` -- une contrainte de ligne ne
    voit pas l'etat PRECEDENT.
    """

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPARTED = "departed"
    ANONYMIZED = "anonymized"


ETATS_COMPTE: tuple[str, ...] = tuple(membre.value for membre in EtatCompte)


def normaliser_email(valeur: str) -> str:
    """Forme normalisee d'une adresse : minuscules, sans espaces de bordure.

    C'est la SEULE normalisation appliquee, et son etroitesse est un choix. Voir
    l'en-tete du module : retirer les points ou couper a un `+` fusionnerait des
    personnes distinctes, et aucun document du corpus ne le demande.

    La contrainte `email_normalise_en_minuscules` en base refuse toute valeur que
    cette fonction n'aurait pas produite. Le controle ne depend donc pas de la
    discipline de l'appelant.
    """
    return valeur.strip().lower()


class Person(ChampsCommuns, Base):
    """Identite globale d'une personne — modele §6.1."""

    __tablename__ = "person"

    #  `email` est la valeur d'AFFICHAGE, §6.1 : la casse que la personne emploie
    #  pour elle-meme. Elle n'est pas unique -- c'est `email_normalized` qui
    #  porte l'unicite -- et elle n'est pas normalisee, sinon elle ne servirait a
    #  rien.
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False)

    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    account_state: Mapped[str] = mapped_column(String(16), nullable=False)

    anonymized_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        #  §25.1 : `person(email_normalized) UNIQUE`, index SIMPLE. Il suffit
        #  parce que la contrainte suivante interdit d'y ecrire deux graphies.
        UniqueConstraint("email_normalized", name="email_normalized_unique"),
        #  L'insensibilite a la casse du §6.1, rendue structurelle.
        CheckConstraint(
            "email_normalized = lower(email_normalized)",
            name="email_normalise_en_minuscules",
        ),
        #  La part STRICTEMENT verifiable de la forme d'une adresse : pas
        #  d'espace, et une arobase qui n'est pas en premiere position. Aucune
        #  validation plus poussee : le corpus n'en prescrit aucune, et une
        #  expression pretendant valider une adresse selon la RFC rejette des
        #  adresses legitimes -- un refus a l'import du LOT 9 coute plus cher
        #  qu'une adresse mal formee stockee.
        CheckConstraint(
            "email_normalized !~ '\\s' AND position('@' IN email_normalized) > 1",
            name="email_normalise_plausible",
        ),
        contrainte_enumeration("account_state", EtatCompte, "account_state_valide"),
        #  Coherence entre l'etat et l'horodatage. DERIVEE, non ecrite telle
        #  quelle : le §6.1 declare les deux colonnes sans lier leurs valeurs.
        #  Une personne `anonymized` sans horodatage rendrait le LOT 10 incapable
        #  de dire QUAND l'anonymisation a eu lieu, ce que le RGPD exige de
        #  tracer ; et un horodatage sans l'etat decrirait une anonymisation qui
        #  n'a pas pris.
        CheckConstraint(
            "(account_state = 'anonymized') = (anonymized_at IS NOT NULL)",
            name="anonymisation_coherente",
        ),
    )


# ===========================================================================
#  `entity_membership` — LOT 2, sous-etape `T4`, story `MVP-L02-US002`
# ===========================================================================
#
#  FONDEMENT — modele §6.2, principe §2.2, etats §24.1, contraintes §25.1 a
#  §25.3, point 4 de l'ordre du §28.
#
#  C'EST LA TABLE QUI PORTE LA REGLE CENTRALE DE `US002` : une seule
#  appartenance active ou future par personne.
#
#  CINQ LECTURES, POSEES PLUTOT QUE SUPPOSEES.
#
#    1. **« PRINCIPALE » EST DESCRIPTIF, PAS UNE COLONNE.** Le §6.2 ecrit « une
#       seule appartenance active ou future PRINCIPALE par personne », mais
#       n'expose aucune colonne qui distinguerait une appartenance principale
#       d'une autre, et le §25.1 ecrit son index SANS notion de principal :
#       `entity_membership(person_id) UNIQUE WHERE membership_state IN
#       ('future','active')`. Le §2.2 tranche : « une consultation d'une autre
#       entite ne cree pas une appartenance supplementaire ». Au MVP, toute
#       appartenance EST principale, et l'index du §25.1 dit exactement la
#       regle.
#
#    2. **LES DATES SONT DES `date`, PAS DES `timestamptz`.** Le mixin `Periode`
#       du socle ne s'applique donc PAS : il produit un `tstzrange`. La plage
#       generee ici est un `daterange`, et la contrainte d'exclusion porte sur
#       elle.
#
#    3. **`version` EST CABLEE EN VERROU OPTIMISTE**, et c'est la premiere table
#       ou le modele le demande explicitement -- §6.2, « `version` | entier |
#       Concurrence optimiste ». `T1` avait declare la colonne sans la cabler,
#       en disant que le cablage serait un choix par table : le voici.
#
#    4. **LE COUPLE `(id, entity_id)` EST UNIQUE**, §25.3. Il n'a aucune utilite
#       pour cette table elle-meme -- `id` est deja unique -- mais il est la
#       CIBLE des cles etrangeres composites que `T5` a `T8` poseront :
#       `membership_job_assignment`, `circle_membership`, `dsm_assignment`. Sans
#       lui, ces tables ne pourraient pas garantir qu'elles referencent une
#       appartenance de LEUR entite. Le poser a la creation evite d'alterer la
#       table plus tard.
#
#    5. **AUCUNE COLONNE `first_name`, `last_name` NI `email`.** Le §6.1 pose
#       que « le nom et l'e-mail ne sont pas dupliques dans les tables
#       d'appartenance ». C'est une regle de NON-DUPLICATION, donc une absence :
#       un controle la verifie, puisqu'une absence ne se declare pas.


class EtatAppartenance(enum.StrEnum):
    """Les quatre valeurs du §6.2.

    Le diagramme du §24.1 en montre CINQ, `Anonymized` compris. La colonne du
    §6.2 n'en declare que quatre, et c'est elle qui fait autorite : l'anonymisation
    est une operation sur la PERSONNE -- `person.account_state` porte deja la
    valeur -- et non sur son appartenance. Voir `ECART-030`.

    `archived` n'est PAS terminal : le §24.1 autorise `Archived --> Active`,
    « reactivation explicite autorisee ». Aucun declencheur ne l'interdit donc,
    contrairement a `person.account_state = 'anonymized'`.
    """

    FUTURE = "future"
    ACTIVE = "active"
    DEPARTED = "departed"
    ARCHIVED = "archived"


ETATS_APPARTENANCE: tuple[str, ...] = tuple(membre.value for membre in EtatAppartenance)

#  Les etats qui occupent la place unique du §25.1.
ETATS_OCCUPANTS: tuple[str, ...] = (EtatAppartenance.FUTURE.value, EtatAppartenance.ACTIVE.value)


class CategorieProfessionnelle(enum.StrEnum):
    """§6.2 : « `consultant`, `dg`, autre categorie configurable ulterieure ».

    Le modele annonce donc explicitement que d'autres valeurs viendront. C'est
    exactement le motif qui a fait choisir une contrainte de verification plutot
    qu'un type `enum` natif en `DEC-499` : ajouter une valeur ici est une
    migration d'une ligne, alors qu'en retirer une d'un `enum` natif exigerait de
    recreer le type et de reecrire les colonnes dependantes.
    """

    CONSULTANT = "consultant"
    DG = "dg"


CATEGORIES_PROFESSIONNELLES: tuple[str, ...] = tuple(
    membre.value for membre in CategorieProfessionnelle
)


class VisibiliteProfil(enum.StrEnum):
    """§6.2 : `draft`, `published`, `hidden`."""

    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"


VISIBILITES_PROFIL: tuple[str, ...] = tuple(membre.value for membre in VisibiliteProfil)


class EntityMembership(ChampsCommuns, RessourceLocale, Base):
    """Profil d'une personne dans une entite — modele §6.2."""

    __tablename__ = "entity_membership"

    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    arrival_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    departure_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    #  Plage GENEREE, semi-ouverte `[arrivee, depart)`, comme la convention posee
    #  en `T1` : la fin d'une periode et le debut de la suivante peuvent porter le
    #  meme jour sans se chevaucher. C'est ce qu'une succession d'appartenances
    #  demande. `departure_date` a NULL donne une plage non bornee.
    period: Mapped[Any] = mapped_column(
        DATERANGE,
        Computed("daterange(arrival_date, departure_date)", persisted=True),
        nullable=False,
    )

    membership_state: Mapped[str] = mapped_column(String(16), nullable=False)
    professional_category: Mapped[str] = mapped_column(String(32), nullable=False)

    short_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    fun_fact: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile_visibility: Mapped[str] = mapped_column(String(16), nullable=False)
    profile_published_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    #  §6.2 : « `version` | entier | Concurrence optimiste ». Le cablage fait que
    #  tout `UPDATE` par l'ORM porte `WHERE version = <lu>` et incremente la
    #  colonne : une mise a jour concurrente leve `StaleDataError` au lieu
    #  d'ecraser silencieusement. La colonne vient de `ChampsCommuns`, le
    #  cablage est propre a cette table.
    #  RUF012 reclame un `ClassVar` ici ; mypy le REFUSE, parce que
    #  `DeclarativeBase` de SQLAlchemy declare `__mapper_args__` en variable
    #  d'instance. Les deux outils se contredisent, et c'est la declaration de
    #  SQLAlchemy qui fait foi : le dictionnaire reste nu, et l'avis de Ruff est
    #  tu ICI et nulle part ailleurs.
    __mapper_args__ = {"version_id_col": ChampsCommuns.version}  # noqa: RUF012

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  §25.1, LA REGLE CENTRALE DE `US002` : une seule appartenance dans un
        #  etat occupant, par personne. Index unique PARTIEL : les appartenances
        #  `departed` et `archived` ne comptent pas, ce qui permet l'historique
        #  du §2.2 -- « plusieurs appartenances historiques, une seule active ».
        Index(
            "uq_entity_membership_person_id_occupante",
            "person_id",
            unique=True,
            postgresql_where=text(
                "membership_state IN (" + ", ".join(f"'{e}'" for e in ETATS_OCCUPANTS) + ")"
            ),
        ),
        #  §25.2 et §6.2 : « pas de chevauchement temporel entre deux
        #  appartenances principales ». Sans clause `WHERE` : le §6.2 l'ecrit
        #  sans restriction d'etat, donc deux appartenances HISTORIQUES ne
        #  doivent pas se chevaucher non plus -- une personne n'a pas ete dans
        #  deux entites en meme temps, meme dans le passe.
        ExcludeConstraint(
            ("person_id", "="),
            ("period", "&&"),
            #  `nom_exclusion` et non un nom nu : PostgreSQL implemente une
            #  exclusion par un INDEX, et les noms d'index sont uniques a
            #  l'echelle du SCHEMA. Voir la regle en tete de `app/shared/modele.py`.
            name=nom_exclusion("entity_membership", "sans_chevauchement"),
            using="gist",
        ),
        #  §25.3 : couple unique, cible des cles etrangeres composites de `T5` a
        #  `T8`. Voir la lecture 4 en tete de section.
        UniqueConstraint("id", "entity_id", name="id_entite_unique"),
        CheckConstraint(
            "departure_date IS NULL OR departure_date >= arrival_date",
            name="depart_apres_arrivee",
        ),
        #  DERIVEE du §24.1, non ecrite telle quelle : la transition
        #  `Active --> Departed` y est libellee « depart ENREGISTRE ». Un depart
        #  qui n'est pas date n'est pas enregistre.
        #
        #  Elle ne vaut QUE pour `departed`. `archived` peut venir de `Future`
        #  -- « arrivee annulee » au §24.1 -- donc sans aucune date de depart.
        CheckConstraint(
            "membership_state <> 'departed' OR departure_date IS NOT NULL",
            name="depart_date_si_departed",
        ),
        contrainte_enumeration("membership_state", EtatAppartenance, "membership_state_valide"),
        contrainte_enumeration(
            "professional_category", CategorieProfessionnelle, "professional_category_valide"
        ),
        contrainte_enumeration("profile_visibility", VisibiliteProfil, "profile_visibility_valide"),
        Index("ix_entity_membership_entity_id_membership_state", "entity_id", "membership_state"),
    )
