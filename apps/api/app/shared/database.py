"""Acces a PostgreSQL.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §16.2 : SQLAlchemy, Alembic, et **aucune
creation automatique de tables**. Ce module ne contient donc NI `Base`
declarative, NI `create_all` : les tables naissent de migrations Alembic
explicites.

**Mis a jour au LOT 2, sous-etape `T1`.** La phrase « le modele de donnees
appartient au LOT 2, qui n'est pas ouvert » etait juste quand elle a ete ecrite
et ne l'est plus : le LOT 2 est ouvert depuis le 18/08/2026 (`DEC-496`). La base
declarative vit desormais dans `app/shared/modele.py`, et elle reste separee de
ce module : le socle du modele ne doit pas dependre d'un moteur, sans quoi
importer une table ouvrirait une connexion.

Le moteur est cree paresseusement : importer ce module ne doit pas ouvrir de
connexion, sans quoi les tests unitaires de configuration exigeraient une base
en fonctionnement.
"""

from __future__ import annotations

import functools

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.configuration.settings import Parametres


@functools.lru_cache(maxsize=1)
def _moteur_cache(url: str) -> Engine:
    return create_engine(
        url,
        # pool_pre_ping : une connexion recyclee par PostgreSQL apres un
        # redemarrage du conteneur serait sinon servie morte a la premiere
        # requete suivante. La stack est arretee et redemarree souvent en
        # developpement, le cas n'est pas theorique.
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        future=True,
    )


def moteur(parametres: Parametres) -> Engine:
    """Moteur de l'APPLICATION — le role d'execution, borne au DML.

    Depuis le LOT 3, `T1` (`QO-116`, `DEC-518`), il ne peut ni creer ni modifier
    une table. Un `CREATE TABLE` par ce moteur rend « permission denied for
    schema public », et c'est voulu.
    """
    return _moteur_cache(parametres.url_postgresql())


def moteur_migrations(parametres: Parametres) -> Engine:
    """Moteur des MIGRATIONS — le role qui possede les objets du schema.

    Employe par Alembic, et par les rares tests qui creent des objets pour
    eprouver le socle. **Ne jamais l'employer dans du code applicatif** :
    `make privileges-check` verifie que l'API se connecte bien en execution.
    """
    return _moteur_cache(parametres.url_postgresql_migrations())


def fabrique_de_sessions(parametres: Parametres) -> sessionmaker[Session]:
    """Fabrique de sessions liee au moteur."""
    return sessionmaker(bind=moteur(parametres), expire_on_commit=False, future=True)


def verifier_connexion(parametres: Parametres) -> None:
    """Executer une requete triviale. Leve une exception si la base est injoignable.

    `SELECT 1` et non une simple ouverture de connexion : le pool peut rendre
    une connexion sans que le serveur soit interrogeable. Un controle de
    disponibilite qui ne pose aucune question ne prouve rien.
    """
    with moteur(parametres).connect() as connexion:
        connexion.execute(text("SELECT 1"))
