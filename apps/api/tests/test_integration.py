"""Tests exigeant PostgreSQL, Redis et MinIO REELS.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — modele de donnees §28
    Chaque migration doit etre eprouvee « sur une base vide », « depuis la
    version precedente », et avec un rollback compatible. La fiche du LOT 1 §5
    ajoute : « execution sur PostgreSQL reel, jamais SQLite ».

    SQLite est donc exclu, et ce n'est pas un detail de confort : ses capacites
    de modification de schema diffèrent tellement de celles de PostgreSQL qu'une
    migration validee sur SQLite ne prouve rien sur la vraie base.

POURQUOI UNE BASE DEDIEE
    Les tests de migration creent et detruisent leur propre base
    `onboarding_test_migration`. Ils ne touchent JAMAIS `onboarding_dev` : un
    test qui detruit la base de travail du developpeur serait un test qu'on
    finit par ne plus lancer.

UN TEST IGNORE N'EST PAS UN TEST QUI PASSE
    Ces tests sont ignores si la stack n'est pas demarree, pour que `make test`
    reste utilisable hors conteneur. Mais `make test-integration` ECHOUE quand
    la stack est absente, au lieu de les ignorer : c'est cette cible qui donne
    la preuve.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.configuration.settings import Parametres
from app.health.dependances import sonder_minio, sonder_postgresql, sonder_redis
from app.main import creer_application
from app.shared.database import moteur

pytestmark = pytest.mark.integration

NOM_BASE_DE_TEST = "onboarding_test_migration"
RACINE_API = Path(__file__).resolve().parents[1]


def _exiger_stack(parametres: Parametres) -> None:
    """Ignorer le test si la stack n'est pas joignable, en le disant clairement."""
    manquants = [
        nom
        for nom, port in (
            ("postgresql", parametres.POSTGRES_PORT),
            ("redis", parametres.REDIS_PORT),
            ("minio", int(parametres.MINIO_ENDPOINT.rsplit(":", 1)[1])),
        )
        if not port_ouvert(HOTE_LOCAL, port)
    ]
    if manquants:
        pytest.skip(
            f"stack absente ({', '.join(manquants)}) — lancer `make up`. "
            "Un test ignore ne prouve rien : utiliser `make test-integration`."
        )


# ============================================================================
#  Sondes de disponibilite : la reciproque du test unitaire
# ============================================================================


def test_les_trois_sondes_reussissent_sur_la_stack_reelle(
    parametres_de_la_stack: Parametres,
) -> None:
    """Temoin positif des sondes.

    Le test unitaire prouve que `ready` sait ECHOUER ; celui-ci prouve qu'il
    sait REUSSIR. Les deux sont necessaires : une sonde toujours en echec est
    aussi inutile qu'une sonde toujours verte.
    """
    _exiger_stack(parametres_de_la_stack)
    for sonde in (sonder_postgresql, sonder_redis, sonder_minio):
        resultat = sonde(parametres_de_la_stack)
        assert resultat.disponible, f"{resultat.nom} indisponible : {resultat.motif}"


def test_ready_repond_200_quand_la_stack_est_la(
    parametres_de_la_stack: Parametres,
) -> None:
    """`/health/ready` renvoie 200 et detaille trois dependances disponibles."""
    _exiger_stack(parametres_de_la_stack)
    client = TestClient(creer_application(parametres_de_la_stack))
    reponse = client.get("/health/ready")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "pret"
    assert len(corps["dependances"]) == 3
    assert all(d["statut"] == "disponible" for d in corps["dependances"])


def test_le_bucket_inexistant_rend_minio_indisponible(
    parametres_de_la_stack: Parametres,
) -> None:
    """Temoin negatif cible : la sonde MinIO verifie bien LE BUCKET.

    Sans ce test, une sonde qui se contenterait de joindre le service passerait
    pour valide alors que l'API ne pourrait servir aucun media.
    """
    _exiger_stack(parametres_de_la_stack)
    parametres = parametres_de_la_stack.model_copy(
        update={"MINIO_BUCKET": f"bucket-absent-{uuid.uuid4().hex[:8]}"}
    )
    assert not sonder_minio(parametres).disponible


# ============================================================================
#  Migration Alembic sur PostgreSQL reel
# ============================================================================


@pytest.fixture
def base_vide(parametres_de_la_stack: Parametres) -> Iterator[Parametres]:
    """Creer une base vide dediee, la detruire a la fin.

    `autocommit` est indispensable : PostgreSQL refuse CREATE DATABASE dans une
    transaction.
    """
    _exiger_stack(parametres_de_la_stack)
    administration = parametres_de_la_stack.model_copy(update={"POSTGRES_DB": "postgres"})
    with psycopg.connect(
        host=administration.POSTGRES_HOST,
        port=administration.POSTGRES_PORT,
        user=administration.POSTGRES_USER,
        password=administration.POSTGRES_PASSWORD,
        dbname="postgres",
        autocommit=True,
    ) as connexion:
        connexion.execute(f'DROP DATABASE IF EXISTS "{NOM_BASE_DE_TEST}"')
        connexion.execute(f'CREATE DATABASE "{NOM_BASE_DE_TEST}"')

    yield parametres_de_la_stack.model_copy(update={"POSTGRES_DB": NOM_BASE_DE_TEST})

    moteur.cache_clear() if hasattr(moteur, "cache_clear") else None
    with psycopg.connect(
        host=administration.POSTGRES_HOST,
        port=administration.POSTGRES_PORT,
        user=administration.POSTGRES_USER,
        password=administration.POSTGRES_PASSWORD,
        dbname="postgres",
        autocommit=True,
    ) as connexion:
        connexion.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (NOM_BASE_DE_TEST,),
        )
        connexion.execute(f'DROP DATABASE IF EXISTS "{NOM_BASE_DE_TEST}"')


def _alembic(parametres: Parametres, *commande: str) -> str:
    """Executer une commande Alembic en processus separe, et rendre sa sortie.

    Un sous-processus, et non l'API Python d'Alembic : `env.py` lit la
    configuration a l'import, et l'executer dans le processus de test
    contaminerait les tests suivants.
    """
    import os
    import shutil
    import subprocess

    environnement = os.environ.copy()
    environnement.update(
        {
            "POSTGRES_HOST": parametres.POSTGRES_HOST,
            "POSTGRES_PORT": str(parametres.POSTGRES_PORT),
            "POSTGRES_DB": parametres.POSTGRES_DB,
            "POSTGRES_USER": parametres.POSTGRES_USER,
            "POSTGRES_PASSWORD": parametres.POSTGRES_PASSWORD,
            "REDIS_PASSWORD": parametres.REDIS_PASSWORD,
            "MINIO_ROOT_USER": parametres.MINIO_ROOT_USER,
            "MINIO_ROOT_PASSWORD": parametres.MINIO_ROOT_PASSWORD,
            "MINIO_BUCKET": parametres.MINIO_BUCKET,
        }
    )
    # Chemin absolu resolu, et non « uv » : un nom relatif dependrait du PATH du
    # processus appelant, ce qui rend le test sensible a l'environnement.
    executable = shutil.which("uv")
    assert executable, "uv est introuvable dans le PATH"
    resultat = subprocess.run(  # noqa: S603 - commande fixe, aucun argument utilisateur
        [executable, "run", "alembic", *commande],
        cwd=RACINE_API,
        env=environnement,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultat.returncode == 0, (
        f"alembic {' '.join(commande)} a echoue :\n{resultat.stdout}\n{resultat.stderr}"
    )
    return resultat.stdout


MOTIF_TETE = re.compile(r"^([0-9a-z_]+)\s*\(head", re.MULTILINE)


def _tete_de_migration(parametres: Parametres) -> str:
    """Revision de tete, DERIVEE d'Alembic et jamais recopiee.

    POURQUOI CETTE FONCTION EXISTE. Trois tests de cette suite annoncaient
    `"0001"` EN DUR. Ils etaient justes en `T3`, quand c'etait la seule revision
    du depot, et sont devenus faux des que le LOT 2 a ajoute `0002` -- sans que
    rien ne le signale avant l'echec.

    C'est `ECART-024` rejoue, et la parade est celle de `ECART-021` : un nombre
    ou un identifiant qu'on recopie finit par mentir, un nombre qu'on derive de
    sa source ne peut pas. Onze migrations restent a ecrire dans ce lot ; sans
    cette fonction, chacune aurait casse les memes trois tests.
    """
    sortie = _alembic(parametres, "heads")
    # Annotation explicite : `re.findall` est type `list[Any]`, et mypy strict
    # refuse de rendre un `Any` depuis une fonction annoncant `str`.
    tetes: list[str] = MOTIF_TETE.findall(sortie)
    assert len(tetes) == 1, (
        f"une seule tete de migration attendue, {len(tetes)} trouvee(s) dans :\n{sortie}"
    )
    return tetes[0]


def _revision_appliquee(parametres: Parametres) -> str | None:
    """Revision inscrite dans `alembic_version`, ou None si la table est absente."""
    with moteur(parametres).connect() as connexion:
        presente = connexion.execute(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ).scalar_one()
        if not presente:
            return None
        return connexion.execute(text("SELECT version_num FROM alembic_version")).scalar()


def _tables_publiques(parametres: Parametres) -> set[str]:
    """Tables du schema public, hors table de suivi d'Alembic."""
    with moteur(parametres).connect() as connexion:
        lignes = connexion.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).scalars()
        return set(lignes)


def test_la_migration_s_applique_sur_une_base_vide(base_vide: Parametres) -> None:
    """Modele §28 : application sur une base vide."""
    assert _revision_appliquee(base_vide) is None, "la base doit partir vierge"
    _alembic(base_vide, "upgrade", "head")
    assert _revision_appliquee(base_vide) == _tete_de_migration(base_vide)


def test_la_migration_ne_cree_aucune_table_metier(base_vide: Parametres) -> None:
    """Garde-fou de perimetre : aucune table a la sortie de `T1` du LOT 2.

    **Mis a jour le 18/08/2026.** Ce test disait « c'est le LOT 2 qui possede le
    modele », le LOT 2 n'etant pas ouvert. Il l'est depuis le 18/08/2026
    (`DEC-496`), et sa sous-etape `T1` ne cree deliberement aucune table : elle
    pose le socle declaratif et l'unique extension.

    **Ce test ECHOUERA en `T2`, et c'est voulu.** Il faudra alors y inscrire la
    liste des tables attendues. Une table qui apparaitrait sans que ce test soit
    mis a jour serait une table creee sans decision.
    """
    _alembic(base_vide, "upgrade", "head")
    assert _tables_publiques(base_vide) == set()


def test_la_migration_se_rejoue_sans_effet(base_vide: Parametres) -> None:
    """Modele §28 : rejeu depuis l'etat precedent."""
    _alembic(base_vide, "upgrade", "head")
    _alembic(base_vide, "upgrade", "head")
    assert _revision_appliquee(base_vide) == _tete_de_migration(base_vide)


def test_le_downgrade_puis_upgrade_est_compatible(base_vide: Parametres) -> None:
    """Modele §28 : `downgrade` puis `upgrade` compatible.

    Le cahier §29.8 exige de verifier la compatibilite du schema avant tout
    retour arriere : une migration qu'on ne sait pas annuler rend le rollback
    applicatif impossible.
    """
    tete = _tete_de_migration(base_vide)

    _alembic(base_vide, "upgrade", "head")
    assert _revision_appliquee(base_vide) == tete

    _alembic(base_vide, "downgrade", "base")
    assert _revision_appliquee(base_vide) is None

    _alembic(base_vide, "upgrade", "head")
    assert _revision_appliquee(base_vide) == tete


def test_aucune_table_n_est_creee_automatiquement(base_vide: Parametres) -> None:
    """`DB_AUTO_CREATE=false` : importer l'API ne cree aucune table.

    Le cahier §16.2 interdit toute creation automatique. Le test le prouve en
    demarrant l'application sur une base vide SANS migration, puis en constatant
    qu'aucune table n'existe.
    """
    client = TestClient(creer_application(base_vide))
    client.get("/health/live")
    assert _revision_appliquee(base_vide) is None
    assert _tables_publiques(base_vide) == set()
