"""Environnement Alembic.

LOT 1, sous-etape T3, story MVP-L01-US003.

L'URL de connexion est construite depuis les variables d'environnement, jamais
lue dans `alembic.ini` : le cahier §20.3 impose la configuration par
environnement, et une URL en dur dans un fichier versionne contiendrait un mot
de passe.

**Mis a jour au LOT 2, sous-etape `T1`.** `target_metadata` valait `None`
« jusqu'au LOT 2 » : c'est fait, il porte desormais les metadonnees de
`app.shared.modele`.

CE QUE CE CABLAGE PERMET, ET CE QU'IL NE PERMET PAS. Il rend `alembic check`
utilisable -- la commande existe en Alembic 1.18.5, verifie -- donc il rend
DETECTABLE un ecart entre le modele declare et le schema reellement applique.
Il rend aussi `--autogenerate` possible, et c'est la que la prudence s'impose :
autogenerate n'ecrit PAS les clauses `WHERE` des index partiels du §25.1, ni les
contraintes d'exclusion du §25.2, ni les colonnes generees. Il sert de BROUILLON
et jamais de livrable ; chaque migration est relue et completee a la main.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.configuration.settings import charger_parametres

#  `app.modeles` et non `app.shared.modele` : ce module importe TOUS les modules
#  de modeles, ce qui est la condition pour que leurs tables soient inscrites
#  dans les metadonnees. Importer seulement le socle rendrait `target_metadata`
#  vide alors que la base porte des tables, et `--autogenerate` proposerait de
#  supprimer tout le schema.
from app.modeles import metadonnees

configuration = context.config

# LOT 2 : les metadonnees, portant toutes les tables declarees a ce jour.
target_metadata = metadonnees

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
