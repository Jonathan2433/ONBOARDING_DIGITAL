"""Moindre privilege PostgreSQL — cahier §20.1, `QO-116`, `DEC-518`.

LOT 3, sous-etape `T1`.

CE QUE CES TESTS GARDENT

  `QO-116` a mesure le 18/08/2026 que l'application se connectait a PostgreSQL
  avec un compte **superutilisateur**, proprietaire du cluster : il pouvait
  detruire la base, lire toute table et creer toute extension. Le cahier §20.1
  pose le moindre privilege.

  `T1` a cree deux roles et fait basculer l'application sur le plus etroit. **Ces
  tests sont ce qui empeche la regression** : `make privileges-check` l'eprouve a
  la main, et ces tests l'eprouvent a CHAQUE pull request.

  Les quatre premiers sont **unitaires** : ils lisent les URL construites, sans
  toucher a la base. Les suivants sont d'integration et exigent PostgreSQL reel --
  parce qu'un droit ne se lit pas dans une chaine de connexion.

TROIS COMPTES, ET PAS DEUX

  `initdb` cree un superutilisateur, et rien ne peut l'empecher d'exister.
  Pretendre le contraire serait pire que le nommer. Ce qui change, c'est que
  l'application ne l'emploie plus, et un test l'exige nommement.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, VARIABLES_MINIMALES, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError

from app.configuration.settings import Parametres
from app.shared.database import moteur, moteur_migrations

# ---------------------------------------------------------------------------
#  Unitaires — quelle URL emploie quel role ?
# ---------------------------------------------------------------------------

REGLAGES_TEMOINS = {
    **VARIABLES_MINIMALES,
    "POSTGRES_USER": "compte_superutilisateur",
    "POSTGRES_PASSWORD": "secret-super",
    "POSTGRES_MIGRATIONS_USER": "compte_migrations",
    "POSTGRES_MIGRATIONS_PASSWORD": "secret-migrations",
    "POSTGRES_RUNTIME_USER": "compte_execution",
    "POSTGRES_RUNTIME_PASSWORD": "secret-execution",
}


def test_l_URL_de_l_application_emploie_le_role_d_EXECUTION() -> None:
    """**LE TEST QUI GARDE `QO-116`.**

    `url_postgresql()` employait `POSTGRES_USER` -- le superutilisateur -- jusqu'au
    LOT 3. Si quelqu'un l'y ramenait, ce test echouerait, et son nom dirait
    pourquoi.
    """
    url = Parametres(**REGLAGES_TEMOINS).url_postgresql()
    assert "compte_execution:secret-execution@" in url
    assert "compte_superutilisateur" not in url, (
        "l'application ne doit JAMAIS se connecter avec le compte cree par `initdb`"
    )
    assert "compte_migrations" not in url, (
        "l'application n'a pas besoin du droit de creer des tables"
    )


def test_l_URL_des_MIGRATIONS_emploie_le_role_de_migration() -> None:
    url = Parametres(**REGLAGES_TEMOINS).url_postgresql_migrations()
    assert "compte_migrations:secret-migrations@" in url
    assert "compte_superutilisateur" not in url, (
        "les migrations n'ont pas besoin du superutilisateur : `btree_gist` est "
        "une extension DE CONFIANCE, installable avec `CREATE ON DATABASE`"
    )


def test_l_URL_du_superutilisateur_reste_disponible_pour_l_approvisionnement() -> None:
    """`CREATE ROLE` exige le superutilisateur : la nier serait se mentir.

    Son unique usage legitime est `make roles-provision`, et
    `make privileges-check` verifie que l'application, elle, ne l'emploie pas.
    """
    url = Parametres(**REGLAGES_TEMOINS).url_postgresql_superutilisateur()
    assert "compte_superutilisateur:secret-super@" in url


def test_les_TROIS_URL_sont_DISTINCTES() -> None:
    """Le temoin des trois precedents.

    Sans lui, une implementation qui rendrait la meme URL partout passerait les
    trois tests ci-dessus des lors qu'elle porterait le bon utilisateur -- ce qui
    est impossible pour les trois a la fois, mais le dire explicitement vaut mieux
    que de le deduire.
    """
    parametres = Parametres(**REGLAGES_TEMOINS)
    urls = {
        parametres.url_postgresql(),
        parametres.url_postgresql_migrations(),
        parametres.url_postgresql_superutilisateur(),
    }
    assert len(urls) == 3, f"{len(urls)} URL distinctes, 3 attendues"


def test_les_quatre_variables_des_roles_sont_OBLIGATOIRES() -> None:
    """Sans elles, l'API se connecterait avec un utilisateur vide.

    Le garde-fou les a nommees en `T1` sur une pile reelle : « Demarrage refuse :
    4 garde-fou(s) de configuration en echec ». Ce test verifie qu'elles sont bien
    dans la liste, et le test parametre de `test_configuration.py` en tire
    automatiquement un cas par variable.
    """
    obligatoires = Parametres(**REGLAGES_TEMOINS).OBLIGATOIRES
    for nom in (
        "POSTGRES_MIGRATIONS_USER",
        "POSTGRES_MIGRATIONS_PASSWORD",
        "POSTGRES_RUNTIME_USER",
        "POSTGRES_RUNTIME_PASSWORD",
    ):
        assert nom in obligatoires, f"{nom} doit etre obligatoire dans tous les environnements"


# ---------------------------------------------------------------------------
#  Integration — un droit ne se lit pas dans une chaine de connexion
# ---------------------------------------------------------------------------


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion de l'APPLICATION — le role d'execution."""
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


@pytest.fixture
def cx_migrations(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion des MIGRATIONS — celle qui possede le schema."""
    _exiger_postgresql(parametres_de_la_stack)
    with moteur_migrations(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


@pytest.mark.integration
def test_la_connexion_de_l_application_n_est_PAS_superutilisateur(cx: Connection) -> None:
    """La mesure de `QO-116`, rejouee — et elle doit desormais rendre `false`.

    Le 18/08/2026, `SELECT rolsuper FROM pg_roles WHERE rolname = current_user`
    rendait `t`. Ce test exige `f`.
    """
    nom, superutilisateur, creer_base, creer_role = cx.execute(
        text(
            "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = current_user"
        )
    ).one()
    assert superutilisateur is False, f"{nom} est superutilisateur — `QO-116` est de retour"
    assert creer_base is False, f"{nom} peut creer une base"
    assert creer_role is False, f"{nom} peut creer un role"


@pytest.mark.integration
def test_l_application_ne_peut_PAS_creer_de_table(cx: Connection) -> None:
    """**LE COEUR DU MOINDRE PRIVILEGE.**

    Sans cette epreuve, un role a qui l'on aurait accorde trop de droits donnerait
    la MEME observation qu'un role correctement borne : les deux se connectent et
    lisent.
    """
    with pytest.raises(ProgrammingError, match="permission denied for schema public"):
        cx.execute(text("CREATE TABLE zz_interdit (id uuid PRIMARY KEY)"))


@pytest.mark.integration
def test_l_application_ne_peut_PAS_modifier_une_table(cx: Connection) -> None:
    with pytest.raises(ProgrammingError, match="must be owner of table"):
        cx.execute(text("ALTER TABLE entity ADD COLUMN zz_interdit text"))


@pytest.mark.integration
def test_l_application_ne_peut_PAS_supprimer_une_table(cx: Connection) -> None:
    with pytest.raises(ProgrammingError, match="must be owner of table"):
        cx.execute(text("DROP TABLE entity"))


@pytest.mark.integration
def test_l_application_ne_peut_PAS_vider_une_table(cx: Connection) -> None:
    """`TRUNCATE` est un DDL deguise : il contourne les declencheurs `ON DELETE`.

    Il n'est donc pas dans les droits accordes, et ce test le dit explicitement --
    sans quoi on pourrait croire que « ecrire des lignes » l'inclut.
    """
    with pytest.raises(ProgrammingError, match="permission denied for table"):
        cx.execute(text("TRUNCATE entity"))


@pytest.mark.integration
def test_l_application_PEUT_lire_et_ecrire_des_lignes(cx: Connection) -> None:
    """**LE TEMOIN INDISPENSABLE.**

    Un role qui ne pourrait RIEN faire passerait les quatre tests precedents. Sans
    celui-ci, ils ne prouveraient pas le moindre privilege mais l'absence de
    privilege.
    """
    identifiant = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
            "VALUES (:code, :nom, :ville, 'FR', 'draft', 'Europe/Paris') RETURNING id"
        ),
        {"code": "ZZPRIV", "nom": "ZZ", "ville": "ZZ"},
    ).scalar_one()
    assert isinstance(identifiant, uuid.UUID)
    lu = cx.execute(text("SELECT count(*) FROM entity WHERE id = :i"), {"i": identifiant})
    assert lu.scalar_one() == 1
    cx.execute(text("UPDATE entity SET display_name = 'ZZ2' WHERE id = :i"), {"i": identifiant})
    cx.execute(text("DELETE FROM entity WHERE id = :i"), {"i": identifiant})


@pytest.mark.integration
def test_les_migrations_PEUVENT_creer_une_table(cx_migrations: Connection) -> None:
    """Le pendant : sans ce droit, aucune migration ne s'appliquerait."""
    cx_migrations.execute(text("CREATE TABLE zz_temoin_migrations (id uuid PRIMARY KEY)"))
    presente = cx_migrations.execute(
        text("SELECT to_regclass('public.zz_temoin_migrations') IS NOT NULL")
    ).scalar_one()
    assert presente is True


@pytest.mark.integration
def test_les_tables_appartiennent_au_role_de_MIGRATION(cx: Connection) -> None:
    """Sans la propriete, une migration future ne pourrait ni ALTER ni DROP.

    Le compte est **derive** : toutes les tables metier, sans exception. Un
    proprietaire different sur une seule table ferait echouer ce test en la
    nommant.
    """
    proprietaires: dict[str, int] = {
        str(ligne[0]): int(ligne[1])
        for ligne in cx.execute(
            text(
                "SELECT tableowner, count(*) FROM pg_tables "
                "WHERE schemaname = 'public' GROUP BY tableowner"
            )
        )
    }
    assert len(proprietaires) == 1, (
        f"les tables ont {len(proprietaires)} proprietaires : {proprietaires}. "
        f"Une seule est attendue, le role de migration."
    )
    proprietaire = next(iter(proprietaires))
    assert "migrations" in proprietaire, (
        f"les tables appartiennent a {proprietaire}, qui n'est pas le role de migration"
    )
