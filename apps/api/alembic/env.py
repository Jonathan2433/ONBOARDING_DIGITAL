"""Environnement Alembic.

LOT 1, sous-etape T3, story MVP-L01-US003.

L'URL de connexion est construite depuis les variables d'environnement, jamais
lue dans `alembic.ini` : le cahier §20.3 impose la configuration par
environnement, et une URL en dur dans un fichier versionne contiendrait un mot
de passe.

`target_metadata` vaut `None` et le restera jusqu'au LOT 2 : il n'existe aucun
modele SQLAlchemy metier. Le declarer vide plutot que d'inventer une `Base`
evite qu'un `alembic revision --autogenerate` lance par erreur ne produise une
migration de suppression de tout le schema.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.configuration.settings import charger_parametres

configuration = context.config

# Aucun modele metier au LOT 1. Voir le LOT 2.
target_metadata = None

parametres = charger_parametres()
configuration.set_main_option("sqlalchemy.url", parametres.url_postgresql())


def executer_hors_ligne() -> None:
    """Emettre le SQL sans se connecter, pour relecture ou application manuelle."""
    context.configure(
        url=configuration.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def executer_en_ligne() -> None:
    """Appliquer les migrations sur une connexion reelle.

    PostgreSQL uniquement : le modele §28 exige que chaque migration soit
    eprouvee sur une base vide, depuis la version precedente, et jamais sur
    SQLite, dont les capacites de migration diffèrent trop.
    """
    section = configuration.get_section(configuration.config_ini_section, {})
    moteur = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with moteur.connect() as connexion:
        context.configure(
            connection=connexion,
            target_metadata=target_metadata,
            # Une migration s'applique entierement ou pas du tout.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executer_hors_ligne()
else:
    executer_en_ligne()
