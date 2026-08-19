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
    Integer,
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
    Periode,
    RessourceLocale,
    contrainte_enumeration,
    nom_cle_composite,
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
        #  AUCUN `name=` : la convention rend `uq_entity_membership_id_entity_id`,
        #  prefixe par la table. Un nom explicite comme `id_entite_unique` ecrase ce
        #  prefixe, et **une contrainte UNIQUE cree un INDEX, dont le nom est global
        #  au schema** : la collision avec `job_catalog` s'est produite en `T5`.
        #  La migration `0006` renomme la contrainte creee par `0005`.
        UniqueConstraint("id", "entity_id"),
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


# ===========================================================================
#  Metiers et situations professionnelles — LOT 2, `T5`, story `MVP-L02-US003`
# ===========================================================================
#
#  FONDEMENT — modele §6.3 `job_catalog`, §6.4 `membership_job_assignment`,
#  §6.5 `professional_status_assignment`, contraintes §25.1 a §25.3, point 5 de
#  l'ordre du §28.
#
#  QUATRE LECTURES, POSEES PLUTOT QUE SUPPOSEES.
#
#    1. **LA VALEUR STOCKEE EST `intercontract`, EN ANGLAIS.** Le modele emploie
#       les deux orthographes, et la mesure les separe nettement : `intercontract`
#       aux lignes 352, 361 et 770, TOUJOURS entre accents graves, donc la ou il
#       specifie une VALEUR ; `intercontrat` aux lignes 48, 69, 353, 915 et 1710,
#       en PROSE, donc la ou il nomme le concept. Les noms de colonnes et de
#       valeurs suivent le modele a la lettre -- `DEC-499` -- donc l'anglais.
#       `ECART-012` citait la forme francaise dans son champ Source : corrige.
#
#    2. **LE §6.4 N'ENUMERE AUCUNE COLONNE.** Il donne trois contraintes, et
#       celles-ci disent ce qu'il faut : « une seule affectation metier active »
#       exige un etat courant reperable, « le metier appartient a la meme entite
#       que l'appartenance » exige `entity_id` et des cles composites du §25.3,
#       « les periodes ne se chevauchent pas » exige une plage. Les colonnes sont
#       DERIVEES de ces trois exigences, et de rien d'autre.
#
#    3. **`client_id` N'A PAS ENCORE DE CLE ETRANGERE**, et ce n'est pas un
#       oubli. Le §6.5 la veut vers `client`, que le §28 place au point 6, donc
#       en `T6`. La colonne est declaree ici -- le §6.5 l'exige -- et la
#       contrainte sera ajoutee par la migration de `T6`. L'alternative aurait
#       ete de deplacer cette table en `T6`, ce qui aurait contredit l'ordre du
#       §28 et le decoupage valide par Jonathan.
#
#    4. **DEUX REGLES DU §6.5 NE SONT PAS APPLICABLES EN `T5`** : « `mission`
#       exige un client ACTIF POUR L'ENTITE » et « `intercontract` interdit un
#       client actif » supposent `entity_client`, qui arrive en `T6`. Ce qui EST
#       applicable ici est la FORME que le §6.5 pose dans son tableau de
#       colonnes : « `client_id` obligatoire en mission, nul en intercontrat ».
#       C'est une contrainte de ligne, et elle est posee.


class SituationProfessionnelle(enum.StrEnum):
    """§6.5 : « `status` | `mission` ou `intercontract` ».

    **`ECART-012` PORTE PRECISEMENT SUR CETTE ENUMERATION**, et il est echu dans
    cette sous-etape : pour une categorie `dg`, ou pour une personne dont
    l'activite n'est pas une mission client, `intercontract` est la seule valeur
    possible -- or le terme designe, dans le langage metier, un consultant en
    attente de mission. Le trombinoscope du LOT 5 l'afficherait.

    **Ce n'est PAS une decision technique.** Le registre recommande de ne pas
    modifier le modele, et d'arbitrer entre conditionner l'AFFICHAGE ou ajouter
    une TROISIEME valeur. **Lea decide du produit.** Cette sous-etape implemente
    donc ce que le modele valide ecrit -- deux valeurs -- et instruit la question.

    **Et le cout de chaque issue est connu** : conditionner l'affichage ne touche
    pas au socle ; ajouter une troisieme valeur est une migration d'UNE LIGNE,
    parce que `DEC-499` a choisi une contrainte de verification et non un type
    `enum` natif. C'etait le motif, et il se realise ici.
    """

    MISSION = "mission"
    INTERCONTRACT = "intercontract"


SITUATIONS_PROFESSIONNELLES: tuple[str, ...] = tuple(
    membre.value for membre in SituationProfessionnelle
)


class JobCatalog(ChampsCommuns, RessourceLocale, Base):
    """Catalogue de metiers configurable par entite — modele §6.3."""

    __tablename__ = "job_catalog"

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    #  Le §6.3 nomme `display_order` sans en donner le type. Un entier, avec un
    #  defaut : sans defaut, toute insertion devrait le fournir alors que le §6.3
    #  ne le presente pas comme obligatoire.
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        #  §25.1, litteralement : `job_catalog(entity_id, code) UNIQUE WHERE
        #  archived_at IS NULL`. Index PARTIEL : un metier archive libere son
        #  code, contrairement a `entity(code)` dont l'unicite n'est pas
        #  partielle. La difference est dans le §25.1 lui-meme, et elle se
        #  comprend : un code d'entite est cite dans les journaux d'audit, un
        #  code de metier est une donnee de configuration locale.
        Index(
            "uq_job_catalog_entity_id_code_non_archive",
            "entity_id",
            "code",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        #  §25.3 : cible des cles composites de `membership_job_assignment`.
        #  Sans `name=` : voir `entity_membership` et `noms_d_index_en_collision`.
        UniqueConstraint("id", "entity_id"),
        Index("ix_job_catalog_entity_id_active", "entity_id", "active"),
    )


class MembershipJobAssignment(ChampsCommuns, RessourceLocale, Periode, Base):
    """Historise le metier d'une appartenance — modele §6.4.

    Colonnes DERIVEES des trois contraintes du §6.4 : voir la lecture 2 en tete
    de section.

    Le mixin `Periode` s'applique ici -- contrairement a `entity_membership` --
    parce que le §6.4 ne parle pas de DATES mais de periodes, et que le §25.1
    ecrit ses index partiels avec `ends_at IS NULL` pour les relations de ce
    genre. Les bornes sont donc des `timestamptz`.
    """

    __tablename__ = "membership_job_assignment"

    entity_membership_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    job_catalog_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        #  §25.3 : DEUX cles etrangeres COMPOSITES, et c'est ce qui applique « le
        #  metier appartient a la meme entite que l'appartenance ». Une paire de
        #  cles simples vers `entity_membership(id)` et `job_catalog(id)`
        #  laisserait affecter un metier de Lille a une appartenance de Bordeaux :
        #  rien ne relierait les deux entites. En passant `entity_id` dans les
        #  deux cles, l'entite est forcement la meme -- c'est la MEME colonne.
        #  NOMS EXPLICITES, et le motif est mesure : la convention concatene
        #  toutes les colonnes d'une cle composite et depasse la limite de 63
        #  octets de PostgreSQL -- 77 et 65 caracteres ici. Voir
        #  `nom_cle_composite`.
        ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("membership_job_assignment", "entity_membership"),
        ),
        ForeignKeyConstraint(
            ["job_catalog_id", "entity_id"],
            ["job_catalog.id", "job_catalog.entity_id"],
            name=nom_cle_composite("membership_job_assignment", "job_catalog"),
        ),
        #  §6.4 : « une seule affectation metier active » ET « les periodes ne se
        #  chevauchent pas ». **UNE SEULE CONTRAINTE PORTE LES DEUX**, et c'est un
        #  resultat de mesure, non une economie.
        #
        #  J'avais d'abord ajoute un index unique partiel `WHERE ends_at IS NULL`,
        #  sur le motif que le §25.1 emploie pour `dsm_assignment`. Mesure du
        #  19/08/2026 : **il ne peut JAMAIS se declencher**. Deux affectations
        #  actives ont toutes deux `ends_at` a NULL, donc deux plages NON BORNEES,
        #  donc elles se chevauchent TOUJOURS -- `[janvier,)` contient decembre.
        #  L'exclusion les refuse systematiquement la premiere.
        #
        #  C'est l'INVERSE de `entity_membership`, ou l'index partiel et
        #  l'exclusion sont complementaires : la-bas l'index porte sur
        #  `membership_state`, pas sur `ends_at`, et deux appartenances occupantes
        #  peuvent avoir des periodes disjointes. **Le meme motif est
        #  complementaire dans une table et redondant dans l'autre, et seule la
        #  mesure les distingue.**
        #
        #  L'index est donc retire. Il n'etait pas ecrit dans le §25.1 -- qui ne
        #  mentionne pas cette table -- c'etait ma derivation, et elle etait
        #  inutile. Un index redondant coute a chaque ecriture et laisse croire
        #  qu'il travaille.
        ExcludeConstraint(
            ("entity_membership_id", "="),
            ("period", "&&"),
            name=nom_exclusion("membership_job_assignment", "sans_chevauchement"),
            using="gist",
        ),
    )


class ProfessionalStatusAssignment(ChampsCommuns, RessourceLocale, Periode, Base):
    """Historise la situation professionnelle — modele §6.5."""

    __tablename__ = "professional_status_assignment"

    entity_membership_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False)

    #  §6.5 : « `client_id` | Obligatoire en mission, nul en intercontrat ».
    #  AUCUNE cle etrangere pour l'instant : `client` arrive en `T6`, point 6 de
    #  l'ordre du §28. La contrainte sera ajoutee par la migration de `T6`.
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    #  §6.5 : « `reason` | Facultatif, audit fonctionnel ».
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        #  Nom explicite : la convention rendait 82 caracteres. Voir
        #  `nom_cle_composite`.
        ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("professional_status_assignment", "entity_membership"),
        ),
        contrainte_enumeration("status", SituationProfessionnelle, "status_valide"),
        #  §6.5, tableau de colonnes : la FORME de la regle client. Ce qui n'est
        #  PAS ici -- « mission exige un client ACTIF POUR L'ENTITE » -- suppose
        #  `entity_client`, donc `T6`.
        CheckConstraint(
            "(status = 'mission') = (client_id IS NOT NULL)",
            name="client_selon_le_statut",
        ),
        #  §6.5 : « une seule situation active par appartenance » ET §25.2. Une
        #  seule contrainte porte les deux, pour la raison mesuree expliquee sur
        #  `MembershipJobAssignment` : deux situations actives ont toutes deux
        #  `ends_at` a NULL, donc des plages non bornees qui se chevauchent
        #  toujours. Un index partiel `WHERE ends_at IS NULL` ne pourrait jamais
        #  se declencher.
        ExcludeConstraint(
            ("entity_membership_id", "="),
            ("period", "&&"),
            name=nom_exclusion("professional_status_assignment", "sans_chevauchement"),
            using="gist",
        ),
    )
