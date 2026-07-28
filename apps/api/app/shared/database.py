"""Acces a PostgreSQL.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §16.2 : SQLAlchemy, Alembic, et **aucune
creation automatique de tables**. Ce module ne contient donc NI `Base`
declarative metier, NI `create_all` : les tables naissent de migrations
Alembic explicites, et le modele de donnees appartient au LOT 2, qui n'est pas
ouvert.

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
    """Moteur SQLAlchemy, cree une seule fois par URL."""
    return _moteur_cache(parametres.url_postgresql())


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
