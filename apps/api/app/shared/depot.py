"""Depots : le cloisonnement par entite rendu STRUCTUREL.

LOT 2, sous-etape `T11`, story `MVP-L02-US006`.

CE QUE CES DEPOTS SONT, ET CE QU'ILS NE SONT PAS

  **Ils ne remplacent PAS les contraintes de la base, et ce n'est pas une
  reserve : c'est le motif.** `DEC-498` l'a tranche pour les contraintes
  d'exclusion : « une regle qui n'existe que dans le code est contournable par
  tout autre chemin d'ecriture ». La base reste l'autorite, et les huit cles
  etrangeres composites du §25.3 refusent une relation croisee quel que soit le
  chemin -- `psql`, une migration, un correctif.

  Leur objet est different et complementaire, et le critere de `US006` le
  demande explicitement : « les contraintes SQL **ET SERVICES** refusent les
  relations incoherentes ». Un depot local **ne sait pas** construire une requete
  sans son `entity_id` : l'oubli n'est pas une faute a eviter, c'est une forme
  qui n'existe pas.

  C'est le §7.2 applique a l'acces aux donnees : **quand une classe d'erreur
  resiste a la vigilance, change d'outil plutot que de promettre de l'attention.**

DEUX TYPES QUI NE PEUVENT PAS SE CONFONDRE, ET C'EST VERIFIE SUR LE SCHEMA

  `DepotLocal` exige une table portant `entity_id` ; `DepotGlobal` exige une
  table qui n'en porte pas. **Les deux le verifient a la construction, en lisant
  le schema reel** -- non une liste recopiee, qui vieillirait au premier ajout de
  table. Employer `DepotGlobal` sur `entity_membership` leve une erreur, et
  employer `DepotLocal` sur `person` aussi.

  Sans cette verification, `DepotGlobal` sur une table locale rendrait les lignes
  de TOUTES les entites en paraissant fonctionner : exactement la fuite que
  `US006` interdit, par le seul chemin que les cles etrangeres ne couvrent pas.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    from sqlalchemy.engine import Connection, Row

#  Un nom de table vient du code de ce projet, jamais d'une entree utilisateur.
#  Il est neanmoins valide, parce qu'il est interpole dans du SQL : un nom
#  fantaisiste doit echouer a la construction, avec un message clair, plutot que
#  de produire du SQL malforme. Meme motif que `MOTIF_VALEUR_ENUMEREE` du socle.
import re

MOTIF_NOM_DE_TABLE = re.compile(r"^[a-z][a-z0-9_]*$")

COLONNE_D_ENTITE = "entity_id"


class ErreurDeDepot(RuntimeError):
    """Emploi incorrect d'un depot : table inconnue, ou depot de mauvais type."""


def _colonnes(connexion: Connection, table: str) -> set[str]:
    resultat = connexion.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table"
        ),
        {"table": table},
    )
    return {ligne[0] for ligne in resultat}


class _Depot:
    """Part commune : validation du nom, existence de la table, et ses colonnes."""

    def __init__(self, connexion: Connection, table: str) -> None:
        if not MOTIF_NOM_DE_TABLE.match(table):
            message = f"nom de table invalide : {table!r}"
            raise ErreurDeDepot(message)
        colonnes = _colonnes(connexion, table)
        if not colonnes:
            message = f"table inconnue dans le schema : {table!r}"
            raise ErreurDeDepot(message)
        self._connexion = connexion
        self._table = table
        self._colonnes = colonnes

    def _valider_les_colonnes(self, noms: Iterable[str]) -> None:
        inconnues = sorted(set(noms) - self._colonnes)
        if inconnues:
            message = f"colonne(s) inconnue(s) sur {self._table} : {inconnues}"
            raise ErreurDeDepot(message)


class DepotLocal(_Depot):
    """Acces a une table LOCALE, toujours borne a une entite.

    Aucune methode n'expose de moyen de lire ou d'ecrire hors de l'entite donnee
    a la construction. `creer` renseigne `entity_id` lui-meme, et refuse une
    valeur contradictoire au lieu de la remplacer en silence.
    """

    def __init__(self, connexion: Connection, table: str, entite: uuid.UUID) -> None:
        super().__init__(connexion, table)
        if COLONNE_D_ENTITE not in self._colonnes:
            message = (
                f"{table!r} ne porte pas `{COLONNE_D_ENTITE}` : c'est une table GLOBALE, "
                f"employer `DepotGlobal`"
            )
            raise ErreurDeDepot(message)
        self._entite = entite

    @property
    def entite(self) -> uuid.UUID:
        return self._entite

    def _ou(self, filtres: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        self._valider_les_colonnes(filtres)
        conditions = [f"{COLONNE_D_ENTITE} = :depot_entite"]
        parametres: dict[str, Any] = {"depot_entite": self._entite}
        for indice, (colonne, valeur) in enumerate(sorted(filtres.items())):
            #  Un parametre par colonne : deux colonnes sur le meme parametre
            #  rendent « inconsistent types deduced » -- defaut `T4-2`, rejoue
            #  deux fois depuis. Le numero garantit l'unicite.
            nom = f"depot_f{indice}"
            conditions.append(f"{colonne} = :{nom}")
            parametres[nom] = valeur
        return " AND ".join(conditions), parametres

    def lister(self, **filtres: Any) -> list[Row[Any]]:
        condition, parametres = self._ou(filtres)
        requete = f"SELECT * FROM {self._table} WHERE {condition} ORDER BY created_at"  # noqa: S608
        return list(self._connexion.execute(text(requete), parametres))

    def compter(self, **filtres: Any) -> int:
        condition, parametres = self._ou(filtres)
        requete = f"SELECT count(*) FROM {self._table} WHERE {condition}"  # noqa: S608
        return self._connexion.execute(text(requete), parametres).scalar_one()  # type: ignore[no-any-return]

    def obtenir(self, identifiant: uuid.UUID) -> Row[Any] | None:
        """Rendre la ligne, ou `None` si elle est d'une AUTRE entite.

        **`None` et non une exception, et non la ligne.** Une ligne d'une autre
        entite doit etre indistinguable d'une ligne inexistante : distinguer les
        deux revelerait son existence, ce que le §2.5 « refus par defaut »
        interdit. C'est le meme raisonnement qu'un 404 plutot qu'un 403 sur une
        ressource qu'on n'a pas le droit de savoir presente.
        """
        condition, parametres = self._ou({})
        parametres["depot_id"] = identifiant
        requete = f"SELECT * FROM {self._table} WHERE {condition} AND id = :depot_id"  # noqa: S608
        return self._connexion.execute(text(requete), parametres).one_or_none()

    def creer(self, **valeurs: Any) -> uuid.UUID:
        declare = valeurs.pop(COLONNE_D_ENTITE, None)
        if declare is not None and declare != self._entite:
            message = (
                f"`{COLONNE_D_ENTITE}` contradictoire : depot borne a {self._entite}, "
                f"valeur fournie {declare}"
            )
            raise ErreurDeDepot(message)
        self._valider_les_colonnes(valeurs)
        colonnes = [COLONNE_D_ENTITE, *sorted(valeurs)]
        parametres: dict[str, Any] = {"depot_entite": self._entite}
        marqueurs = [":depot_entite"]
        for indice, colonne in enumerate(sorted(valeurs)):
            nom = f"depot_v{indice}"
            marqueurs.append(f":{nom}")
            parametres[nom] = valeurs[colonne]
        requete = (
            f"INSERT INTO {self._table} ({', '.join(colonnes)}) "  # noqa: S608
            f"VALUES ({', '.join(marqueurs)}) RETURNING id"
        )
        return self._connexion.execute(text(requete), parametres).scalar_one()  # type: ignore[no-any-return]


class DepotGlobal(_Depot):
    """Acces a une table GLOBALE — `person`, `client`, `platform_setting`, `entity`.

    Il refuse une table locale : sans ce refus, il rendrait les lignes de toutes
    les entites **en paraissant fonctionner**, ce qui est la fuite que `US006`
    interdit par le seul chemin que les cles etrangeres ne couvrent pas.
    """

    def __init__(self, connexion: Connection, table: str) -> None:
        super().__init__(connexion, table)
        if COLONNE_D_ENTITE in self._colonnes:
            message = (
                f"{table!r} porte `{COLONNE_D_ENTITE}` : c'est une table LOCALE, "
                f"employer `DepotLocal` avec son entite"
            )
            raise ErreurDeDepot(message)

    def obtenir(self, identifiant: uuid.UUID) -> Row[Any] | None:
        requete = f"SELECT * FROM {self._table} WHERE id = :depot_id"  # noqa: S608
        return self._connexion.execute(text(requete), {"depot_id": identifiant}).one_or_none()

    def compter(self) -> int:
        requete = f"SELECT count(*) FROM {self._table}"  # noqa: S608
        return self._connexion.execute(text(requete)).scalar_one()  # type: ignore[no-any-return]
