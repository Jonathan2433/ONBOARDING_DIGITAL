"""Socle declaratif du modele de donnees.

LOT 2, sous-etape `T1`, story `MVP-L02-US008`.

Ce module ne declare AUCUNE table. Il pose ce dont toutes les tables du lot
auront besoin : la base declarative, la convention de nommage des contraintes,
les champs communs du modele de donnees §3.1, et la representation des periodes
du §25.2. Les tables elles-memes arrivent en `T2` et suivantes.

FONDEMENT — modele de donnees §3.1 pour les champs communs, §25.1 pour les index
uniques partiels, §25.2 pour les contraintes temporelles, §25.3 pour les cles
etrangeres composites.

DEUX REGLES DE NOMMAGE, ET ELLES SONT DELIBEREES.

  1. Les noms de tables et de colonnes sont ceux du modele de donnees, a la
     lettre, donc en anglais : `entity`, `entity_membership`, `starts_at`,
     `archived_at`. Le reste du code de ce projet est en francais, et c'est une
     exception assumee : un dictionnaire de traduction entre le modele et le
     schema serait un endroit ou les deux divergent en silence. Une chose, un
     nom.
  2. Les identifiants Python de ce module -- fonctions, mixins, constantes --
     restent en francais, comme partout ailleurs dans ce depot.
"""

from __future__ import annotations

import datetime as dt
import enum
import re
import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Integer,
    MetaData,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSTZRANGE, Range
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
#  Convention de nommage des contraintes
#
#  POURQUOI ELLE EST OBLIGATOIRE, ET PAS UN CONFORT. Une migration de retour
#  arriere doit NOMMER les objets qu'elle supprime. Sans convention, le nom est
#  choisi par PostgreSQL a la creation, il n'apparait nulle part dans le code,
#  et un `downgrade()` ecrit a la main ne peut pas le deviner. Le critere de
#  sortie du lot exige que les migrations soient rejouables : c'est cette
#  convention qui le rend possible.
#
#  `ck` emploie `%(constraint_name)s` et NON `%(column_0_name)s` : une
#  contrainte de verification peut porter sur plusieurs colonnes, ou sur aucune
#  en particulier. Consequence a connaitre : toute `CheckConstraint` DOIT
#  recevoir un `name=`, sinon SQLAlchemy leve une erreur au moment du DDL. Ce
#  n'est pas une gene, c'est le garde-fou : une contrainte anonyme est une
#  contrainte qu'on ne peut pas defaire.
# ---------------------------------------------------------------------------
CONVENTION_DE_NOMMAGE = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

#  PostgreSQL tronque SILENCIEUSEMENT tout identifiant au-dela de 63 octets.
#  Deux contraintes dont les noms ne differeraient qu'apres le 63e caractere
#  entreraient en collision sans qu'aucun message ne le dise. Un controle
#  confronte les noms engendres a cette limite.
LIMITE_IDENTIFIANT_POSTGRESQL = 63

metadonnees = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)


class Base(DeclarativeBase):
    """Base declarative de toutes les tables du modele."""

    metadata = metadonnees


# ---------------------------------------------------------------------------
#  Champs communs — modele de donnees §3.1
# ---------------------------------------------------------------------------
class ChampsCommuns:
    """Les champs que le §3.1 pose sur les principales tables metier.

    `id` recoit DEUX defauts, et ce n'est pas une redondance :

      - le defaut Python `uuid4` donne son identifiant a l'objet AVANT le
        `flush`, ce dont les factories du `T12` ont besoin pour construire un
        graphe d'objets qui se referencent ;
      - le defaut serveur `gen_random_uuid()` couvre tout ce qui ne passe pas par
        l'ORM : une migration, un correctif SQL, un jeu d'essai charge par
        `psql`. Cette fonction est fournie par le NOYAU de PostgreSQL depuis la
        version 13 -- mesure du 18/08/2026 sur le serveur de ce projet, elle est
        rattachee a « le NOYAU » et non a une extension. `pgcrypto` est donc
        inutile, et n'est pas installee.

    `created_by_person_id` et les deux autres colonnes d'auteur sont des `uuid`
    SANS cle etrangere vers `person`, et c'est un choix trace :

      - le §3.1 les ecrit `uuid null` et ne mentionne aucune cle etrangere ;
      - `entity` se cree avant `person` -- ordre du §28 -- donc la contrainte ne
        pourrait pas exister au moment ou la premiere table la porte ;
      - le LOT 10 devra effacer ou anonymiser des personnes au titre du RGPD ;
        une cle etrangere y opposerait une contrainte a defaire.

    `version` est declaree parce que le §3.1 l'exige. Elle n'est PAS cablee en
    verrou optimiste ici : ce cablage change la semantique de tout `UPDATE`, et
    c'est un choix par table, a faire dans la sous-etape qui ecrit des mises a
    jour. Le dire plutot que de le laisser croire.

    `updated_at` est renseignee par l'ORM a chaque mise a jour. **Un `UPDATE`
    ecrit directement en SQL ne la met PAS a jour** : seul un declencheur le
    garantirait, et il n'y en a pas. C'est une limite connue, non un oubli.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )

    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by_person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by_person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    #  `Text` et non `String` sans longueur : le §3.1 ecrit `archive_reason text
    #  null`. Sans le type explicite, SQLAlchemy produit un `VARCHAR` sans borne,
    #  ce qui n'est pas faux mais n'est pas ce que le modele ecrit. Defaut de `T1`,
    #  releve en `T2` a la lecture du brouillon de migration.
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RessourceLocale:
    """`entity_id`, pour les ressources qui appartiennent a une entite.

    Le §3.1 l'ecrit « si la ressource est locale », d'ou un mixin distinct :
    `person` et `client` sont globaux et ne doivent PAS porter cette colonne.

    La cle etrangere n'est pas declaree ici mais table par table, parce que le
    §25.3 exige des cles COMPOSITES `(id, entity_id)` pour empecher les
    references inter-entites : le couple depend de la table referencee.
    """

    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)


# ---------------------------------------------------------------------------
#  Periodes — modele de donnees §25.2
# ---------------------------------------------------------------------------
class Periode:
    """Une relation historisee : deux bornes, et la plage qui en derive.

    DEUX REPRESENTATIONS DE LA MEME CHOSE, ET LES DEUX SONT NECESSAIRES.

      - `starts_at` et `ends_at` sont la SOURCE. Le §25.1 ecrit ses index
        uniques partiels avec `WHERE ends_at IS NULL` : sans ces deux colonnes,
        ses contraintes ne s'ecrivent pas telles qu'il les pose ;
      - `period` est une colonne GENEREE, calculee par PostgreSQL a partir des
        deux precedentes. Le §25.2 reclame des contraintes d'exclusion sur des
        plages temporelles, et une contrainte d'exclusion a besoin d'une plage.

    Une colonne generee ne peut pas diverger de sa source : c'est PostgreSQL
    qui la calcule, jamais l'application. Deux colonnes maintenues en parallele
    par du code finiraient par se contredire.

    `tstzrange(starts_at, ends_at)` produit une plage semi-ouverte `[debut,
    fin)` : la fin d'une periode et le debut de la suivante peuvent porter le
    meme instant sans se chevaucher. C'est exactement ce qu'une succession
    historique demande.

    `ends_at` a `NULL` donne une plage sans borne superieure, `[debut,)`, ce qui
    est la representation d'une relation TOUJOURS ACTIVE.
    """

    starts_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    period: Mapped[Range[dt.datetime]] = mapped_column(
        TSTZRANGE,
        # `persisted=True` -> GENERATED ALWAYS AS (...) STORED. PostgreSQL 17
        # n'implemente pas les colonnes generees virtuelles, et une contrainte
        # d'exclusion exige de toute facon une colonne stockee.
        Computed("tstzrange(starts_at, ends_at)", persisted=True),
        nullable=False,
    )


# ---------------------------------------------------------------------------
#  Enumerations — contrainte de verification, et non type `enum` natif
# ---------------------------------------------------------------------------
#  MOTIF ELARGI EN `T8`, ET LE MOTIF DE L'ELARGISSEMENT EST UNE LECON.
#
#  La premiere version exigeait des MINUSCULES : `^[a-z][a-z0-9_]*$`. Elle
#  etait juste pour `T2` a `T7`, dont toutes les enumerations du modele sont en
#  minuscules -- `draft`, `active`, `mission`, `principal`.
#
#  Le §8.4 et le §8.6 ecrivent les leurs en MAJUSCULES : `DSM`, `ESM`,
#  `BOOSTER`, `OFFICE_MANAGER`, `ENTITY_ADMIN`, `SUPER_ADMIN`. Et le §25.1 les
#  cite ainsi : `responsibility_type = 'BOOSTER'`. La casse est donc une
#  DECISION DU MODELE, pas un style de ce depot.
#
#  **L'objet de ce controle n'a jamais ete la casse** : c'est d'empecher qu'une
#  valeur portant une apostrophe, une espace ou un caractere exotique ne produise
#  du SQL malforme dans la contrainte interpolee. Le motif est elargi a la casse
#  libre, et cet objet est preserve entierement.
#
#  C'est le §7.21 de la passation, dans un controle que j'ai ecrit moi-meme en
#  `T1` : juste a sa date, rendu faux par une table ulterieure.
MOTIF_VALEUR_ENUMEREE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def contrainte_enumeration(
    colonne: str, enumeration: type[enum.StrEnum], nom: str, *, nullable: bool = False
) -> CheckConstraint:
    """Contrainte de verification bornant `colonne` aux valeurs de `enumeration`.

    POURQUOI PAS UN TYPE `enum` NATIF DE POSTGRESQL, et le motif est mesure sur
    un cas reel de ce projet. Ajouter une valeur a un type `enum` natif est
    facile ; en RETIRER une ou la RENOMMER exige de recreer le type et de
    reecrire toutes les colonnes qui s'en servent. Or `ECART-012` est ouvert et
    echu dans ce lot : il porte precisement sur l'ajout d'une TROISIEME valeur a
    la situation professionnelle, aujourd'hui bornee a `mission` et
    `intercontrat`. Une contrainte de verification se modifie par une migration
    d'une ligne.

    Les valeurs sont interpolees dans du SQL. Elles viennent de notre propre
    code, mais un motif les valide tout de meme : une valeur qui contiendrait
    une apostrophe produirait du SQL malforme, et le refus vaut mieux que le
    diagnostic.
    """
    valeurs = [membre.value for membre in enumeration]
    if not valeurs:
        message = f"enumeration vide pour la contrainte {nom}"
        raise ValueError(message)
    for valeur in valeurs:
        if not MOTIF_VALEUR_ENUMEREE.match(valeur):
            message = (
                f"valeur enumeree refusee pour la contrainte {nom} : {valeur!r}. "
                f"Attendu : lettres, chiffres et tirets bas, commencant par une lettre. "
                f"La CASSE est libre : elle est decidee par le modele de donnees"
            )
            raise ValueError(message)

    liste = ", ".join(f"'{valeur}'" for valeur in valeurs)
    expression = f"{colonne} IN ({liste})"
    if nullable:
        expression = f"{colonne} IS NULL OR {expression}"
    return CheckConstraint(expression, name=nom)


#  PREFIXE DES CONTRAINTES D'EXCLUSION, ET POURQUOI IL EST A LA CHARGE DU
#  DEVELOPPEUR.
#
#  La convention de nommage de SQLAlchemy connait cinq cles -- `ix`, `uq`, `ck`,
#  `fk`, `pk` -- et AUCUNE pour les contraintes d'exclusion. Un
#  `ExcludeConstraint` prend donc son `name=` tel quel, sans prefixe de table.
#
#  Or PostgreSQL implemente une contrainte d'exclusion par un INDEX, et **les
#  noms d'index sont uniques a l'echelle du SCHEMA**, pas par table -- a la
#  difference des noms de contraintes. Deux tables portant chacune une exclusion
#  nommee `sans_chevauchement` echouent donc a la creation de la seconde :
#  « relation "sans_chevauchement" already exists ».
#
#  Mesure du 19/08/2026 : le defaut est apparu en `T4`, revele par la table
#  d'essai de `T1` qui portait deja ce nom. Le §25.2 prevoit des exclusions sur
#  SEPT relations : sans regle, la collision se reproduirait six fois.
#
#  Regle retenue : `ex_<table>_<objet>`, et un controle la verifie.
PREFIXE_EXCLUSION = "ex"


def nom_exclusion(table: str, objet: str) -> str:
    """Nom conventionnel d'une contrainte d'exclusion : `ex_<table>_<objet>`."""
    return f"{PREFIXE_EXCLUSION}_{table}_{objet}"


def noms_exclusions_non_conformes(metadata: MetaData | None = None) -> list[tuple[str, str]]:
    """Contraintes d'exclusion dont le nom n'est pas prefixe par leur table.

    Retourne les couples `(table, nom)`. Une liste vide est le resultat attendu.
    """
    cible = metadonnees if metadata is None else metadata
    fautives: list[tuple[str, str]] = []
    for table in cible.tables.values():
        for contrainte in table.constraints:
            if type(contrainte).__name__ != "ExcludeConstraint":
                continue
            nom = getattr(contrainte, "name", None)
            attendu = f"{PREFIXE_EXCLUSION}_{table.name}_"
            if not isinstance(nom, str) or not nom.startswith(attendu):
                fautives.append((table.name, str(nom)))
    return sorted(fautives)


def noms_d_index_en_collision(metadata: MetaData | None = None) -> list[tuple[str, list[str]]]:
    """Objets que PostgreSQL implemente par un INDEX et qui partagent un nom.

    Retourne les couples `(nom, tables)`. Une liste vide est le resultat attendu.

    POURQUOI CE CONTROLE CIBLE LE MODE DE DEFAILLANCE, ET NON UNE CONVENTION.
    PostgreSQL implemente par un index les cles PRIMAIRES, les contraintes
    UNIQUE, les contraintes d'EXCLUSION et bien sur les index. **Et les noms
    d'index sont uniques a l'echelle du SCHEMA**, pas par table -- a la
    difference des noms de contraintes de verification ou de cles etrangeres.

    La collision s'est produite DEUX FOIS, et pour la meme cause de fond :

      - `T4`, `sans_chevauchement` : une exclusion, ou la convention de
        SQLAlchemy n'a aucune cle, donc le nom explicite etait obligatoire mais
        n'etait pas prefixe ;
      - `T5`, `id_entite_unique` : une contrainte UNIQUE, que la convention
        SAVAIT nommer -- `uq_<table>_<colonnes>` -- et dont un `name=` explicite
        a ecrase le prefixe.

    **La cause commune est le `name=` explicite.** Un controle qui ne verifierait
    qu'un prefixe laisserait passer deux tables prefixant de la meme facon ; ce
    controle-ci compare les noms entre eux, ce qui est exactement ce que
    PostgreSQL fera.

    LA DOCTRINE QUI EN DECOULE, ET ELLE EST COURTE

      cle PRIMAIRE, contrainte UNIQUE, index  ne PAS passer de `name=`. La
                                              convention prefixe deja par la
                                              table.
      contrainte de VERIFICATION              passer un nom COURT et descriptif :
                                              la convention le prefixe, le jeton
                                              `%(constraint_name)s` l'exigeant.
      cle etrangere                           laisser la convention, SAUF si elle
                                              depasse 63 octets -- cas des cles
                                              COMPOSITES. Alors
                                              `nom_cle_composite`.
      contrainte d'EXCLUSION                  toujours `nom_exclusion` : la
                                              convention n'a aucune cle pour
                                              elles.
    """
    cible = metadonnees if metadata is None else metadata
    par_nom: dict[str, list[str]] = {}
    familles_indexees = {"PrimaryKeyConstraint", "UniqueConstraint", "ExcludeConstraint"}
    for table in cible.tables.values():
        objets: list[Any] = [*table.constraints, *table.indexes]
        for objet in objets:
            famille = type(objet).__name__
            if famille not in familles_indexees and famille != "Index":
                continue
            nom = getattr(objet, "name", None)
            if isinstance(nom, str):
                par_nom.setdefault(nom, []).append(table.name)
    return sorted((nom, sorted(tables)) for nom, tables in par_nom.items() if len(tables) > 1)


def nom_cle_composite(table: str, table_visee: str) -> str:
    """Nom d'une cle etrangere COMPOSITE : `fk_<table>_<table_visee>`.

    POURQUOI LA CONVENTION NE SUFFIT PAS ICI. La convention rend
    `fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s`, ce qui est
    parfait pour une cle simple. Pour une cle COMPOSITE, `column_0_N_name`
    concatene toutes les colonnes, et le nom explose :

        fk_professional_status_assignment_entity_membership_id_entity_id_entity_membership
        -> 82 caracteres, pour une limite de 63

    Mesure du 19/08/2026, sous-etape `T5` : TROIS cles composites depassaient, a
    77, 65 et 82 caracteres. **PostgreSQL tronque a 63 octets EN SILENCE**, et
    deux noms qui ne differeraient qu'apres le 63e caractere entreraient en
    collision sans qu'aucun message ne le dise.

    C'est le controle `noms_de_contraintes_trop_longs`, pose en `T1`, qui l'a
    attrape -- quatre sous-etapes plus tard, et sur des noms que les metadonnees
    ne portaient pas encore quand il a ete ecrit.

    Le nom retenu decrit la RELATION et non ses colonnes : `<table>` vers
    `<table_visee>`. Il reste unique par table, ce qui suffit -- les noms de
    contraintes sont propres a chaque table, contrairement aux noms d'index
    (voir `nom_exclusion`).
    """
    return f"fk_{table}_{table_visee}"


def noms_de_contraintes_trop_longs(metadata: MetaData | None = None) -> list[tuple[str, int]]:
    """Contraintes et index dont le nom depasse la limite de PostgreSQL.

    Retourne les couples `(nom, longueur)`. Une liste vide est le resultat
    attendu. Ce controle existe parce que la troncature est SILENCIEUSE : rien
    ne signale que deux noms sont devenus identiques.
    """
    cible = metadonnees if metadata is None else metadata
    trouves: list[tuple[str, int]] = []
    for table in cible.tables.values():
        objets: list[Any] = [*table.constraints, *table.indexes]
        for objet in objets:
            nom = getattr(objet, "name", None)
            if isinstance(nom, str) and len(nom) > LIMITE_IDENTIFIANT_POSTGRESQL:
                trouves.append((nom, len(nom)))
    return sorted(trouves)
