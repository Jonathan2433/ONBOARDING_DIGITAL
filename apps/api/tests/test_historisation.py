"""Historisation des SEPT relations du modele §25.2.

LOT 2, sous-etape `T9`, story `MVP-L02-US004`.

CETTE SOUS-ETAPE NE CREE AUCUNE TABLE. Les sept relations existent depuis `T4` a
`T8`, et chacune a son test. Ce que `T9` apporte est ce qu'aucune sous-etape ne
portait :

  - le COMPTE des relations historisees, confronte a un attendu DERIVE du modele ;
  - la preuve que « toute modification cloture la periode precedente et en cree une
    neuve » fonctionne AU NIVEAU DE LA BASE ;
  - un controle systematique contre le defaut `T8-1`, et le test qui prouve sa
    correction sur `technical_role_assignment`.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.modeles import metadonnees
from app.shared.database import moteur

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)

RACINE = pathlib.Path(__file__).resolve().parents[3]
MODELE = RACINE / "docs" / "architecture" / "MODELE_DONNEES_EXALT.md"

#  Les tables qui portent les sept relations du §25.2. Le compte attendu est
#  DERIVE du modele par le test suivant, jamais recopie.
TABLES_HISTORISEES = {
    "entity_membership",
    "membership_job_assignment",
    "professional_status_assignment",
    "dsm_assignment",
    "circle_membership",
    "framework_responsibility_assignment",
    "technical_role_assignment",
}


def test_le_compte_des_relations_est_DERIVE_du_modele() -> None:
    """Le §25.2 enumere ses relations : le compte vient de la, pas de moi.

    Recopier « 7 » serait un `ECART-021` en puissance -- un nombre affirme sans
    etre derive de sa source. Ce test lit la liste a puces du §25.2 et confronte
    son compte au nombre de tables que nous declarons historisees.
    """
    texte = MODELE.read_text(encoding="utf-8")
    debut = texte.index("## 25.2 Contraintes temporelles")
    section = texte[debut : texte.index("## 25.3", debut)]
    apres = section.index("Relations concernées :")
    libelles = [
        ligne.strip().lstrip("- ").rstrip(" ;.")
        for ligne in section[apres:].splitlines()
        if ligne.strip().startswith("- ")
    ]
    assert len(libelles) == len(TABLES_HISTORISEES), (
        f"le §25.2 enumere {len(libelles)} relation(s) : {libelles}, "
        f"et nous en declarons {len(TABLES_HISTORISEES)} historisees. "
        "Rattacher la relation manquante, ou dire pourquoi elle ne l'est pas."
    )


def test_chaque_table_historisee_porte_une_exclusion_DECLAREE() -> None:
    """Au niveau des metadonnees, avant meme d'interroger la base.

    Le controle `make historisation-check` verifie l'etat REEL ; celui-ci verifie
    le DECLARE. Les deux sont necessaires : `alembic check` etant aveugle aux
    contraintes d'exclusion -- mesure du 19/08/2026 -- le declare et le reel
    peuvent diverger sans que rien ne le signale.
    """
    sans_exclusion = []
    for nom in sorted(TABLES_HISTORISEES):
        table = metadonnees.tables[nom]
        exclusions = [c for c in table.constraints if type(c).__name__ == "ExcludeConstraint"]
        if not exclusions:
            sans_exclusion.append(nom)
    assert not sans_exclusion, f"tables historisees sans exclusion declaree : {sans_exclusion}"


def test_aucune_colonne_nullable_dans_une_cle_d_exclusion_sans_IS_NOT_NULL() -> None:
    """Le controle systematique ne du defaut `T8-1`, au niveau du DECLARE.

    Une cle d'exclusion contenant une colonne nullable ne contraint RIEN sur les
    lignes ou elle est nulle : l'operateur `=` ne rapproche jamais deux NULL. La
    clause `WHERE` doit donc l'exclure EXPLICITEMENT -- et non s'appuyer sur une
    autre contrainte, dont la disparition serait silencieuse.

    LE TEST COMPTE CE QU'IL A EXAMINE, et confronte ce compte a un attendu. Sans
    cela, une erreur d'enumeration le rendrait creux : il passerait en n'ayant rien
    regarde. C'est la troisieme proposition du §7.0.
    """
    fautives: list[str] = []
    examinees = 0
    nullables_vues = 0
    for table in metadonnees.tables.values():
        for contrainte in table.constraints:
            if type(contrainte).__name__ != "ExcludeConstraint":
                continue
            examinees += 1
            #  `getattr(..., None)` puis conversion explicite : evaluer une clause
            #  SQLAlchemy comme un booleen leve `TypeError`, sa valeur de verite
            #  n'etant pas definie. `or ""` ne convient donc pas.
            where = getattr(contrainte, "where", None)
            clause = "" if where is None else str(where)
            #  `getattr` et non l'attribut direct : `table.constraints` est type
            #  `set[Constraint]`, et `Constraint` ne declare pas `columns`. mypy
            #  strict le refuse, alors que `ExcludeConstraint` la porte bien.
            colonnes: Any = getattr(contrainte, "columns", [])
            for colonne in colonnes:
                if not colonne.nullable:
                    continue
                nullables_vues += 1
                if f"{colonne.name} IS NOT NULL" not in clause:
                    fautives.append(f"{table.name}.{colonne.name} dans {contrainte.name}")

    assert examinees >= 7, (
        f"{examinees} exclusion(s) examinee(s) : le §25.2 en attend au moins sept, "
        "une par relation. Un compte plus faible signale une erreur d'enumeration."
    )
    assert nullables_vues >= 3, (
        f"{nullables_vues} colonne(s) nullable(s) trouvee(s) dans les cles d'exclusion. "
        "Il en existe au moins trois -- `circle_id`, `office_id`, `entity_id` -- donc un "
        "compte plus faible signale que le test ne regarde pas ce qu'il croit."
    )
    assert not fautives, (
        f"colonnes nullables dans une cle d'exclusion sans `IS NOT NULL` explicite : "
        f"{sorted(fautives)}. Defaut `T8-1`."
    )


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"a": adresse, "b": adresse},
    ).scalar_one()


def _entite(connexion: Connection, code: str = "BORDEAUX") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


# ----------------------------------------------------------------------------
#  Le critere de `US004` : « toute modification cloture puis cree »
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_cloturer_PUIS_creer_est_accepte(cx: Connection) -> None:
    """Critere d'acceptation de `US004`, eprouve AU NIVEAU DE LA BASE.

    « Toute modification clôture la relation precedente et cree une nouvelle
    periode. » Aucune contrainte ne l'exprime : c'est un COMPORTEMENT. Ce que la
    base garantit est que la sequence correcte PASSE et que la sequence fautive
    ECHOUE -- et c'est ce que ce test et le suivant prouvent, en une seule
    transaction, comme un service le ferait.

    **L'ORCHESTRATION reste a faire.** Aucun service ne l'applique avant `T11` :
    la base refuse la faute, elle ne corrige pas l'appelant.
    """
    entite = _entite(cx)
    personne = _personne(cx, "resp@exalt.com")
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, 'ENTITY_ADMIN', :debut)"
        ),
        {"p": personne, "e": entite, "debut": JANVIER},
    )
    #  La sequence CORRECTE : clore, puis creer.
    cx.execute(
        text("UPDATE technical_role_assignment SET ends_at = :fin WHERE person_id = :p"),
        {"fin": JUIN, "p": personne},
    )
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, 'ENTITY_ADMIN', :debut)"
        ),
        {"p": personne, "e": entite, "debut": JUIN},
    )
    periodes = (
        cx.execute(text("SELECT period::text FROM technical_role_assignment ORDER BY starts_at"))
        .scalars()
        .all()
    )
    assert len(periodes) == 2, "l'historique est conserve, pas ecrase (§2.3)"
    assert periodes[0].endswith('2026-06-01 00:00:00+00")')
    assert periodes[1].endswith(",)"), "la nouvelle periode est ouverte"


@pytest.mark.integration
def test_creer_SANS_cloturer_est_refuse(cx: Connection) -> None:
    """Le temoin du precedent, et c'est lui qui prouve que la base garantit la regle."""
    entite = _entite(cx)
    personne = _personne(cx, "resp@exalt.com")
    for _ in range(2):
        pass
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, 'ENTITY_ADMIN', :debut)"
        ),
        {"p": personne, "e": entite, "debut": JANVIER},
    )
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, "
                "starts_at) VALUES (:p, :e, 'ENTITY_ADMIN', :debut)"
            ),
            {"p": personne, "e": entite, "debut": JUIN},
        )
    assert "ex_technical_role_assignment_entity_admin" in str(echec.value)


# ----------------------------------------------------------------------------
#  Le defaut trouve par le controle de `T9`, et sa correction
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_deux_SUPER_ADMIN_qui_se_chevauchent_sont_refuses(cx: Connection) -> None:
    """CE TEST PROUVE LA CORRECTION D'UN DEFAUT QUE `T8` AVAIT LAISSE.

    `technical_role_assignment` portait une exclusion dont la cle incluait
    `entity_id`. Or `entity_id` est NUL pour un `SUPER_ADMIN` -- le §8.6 l'exige --
    et l'operateur `=` ne rapproche jamais deux NULL : **deux `SUPER_ADMIN` de la
    meme personne aux periodes qui se chevauchent n'auraient PAS ete detectes**.

    Le defaut est exactement `T8-1`, dans une table ou je croyais l'avoir traite :
    j'avais corrige `framework_responsibility_assignment` et pas celle-ci. **Une
    correction appliquee a la main table par table en oublie une.** C'est le
    controle mecanique de `T9` qui l'a trouve, pas un test.
    """
    personne = _personne(cx, "super@exalt.com")
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, role_type, starts_at, ends_at) "
            "VALUES (:p, 'SUPER_ADMIN', :debut, :fin)"
        ),
        {"p": personne, "debut": JANVIER, "fin": DECEMBRE},
    )
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO technical_role_assignment (person_id, role_type, starts_at) "
                "VALUES (:p, 'SUPER_ADMIN', :debut)"
            ),
            {"p": personne, "debut": JUIN},
        )
    assert "ex_technical_role_assignment_super_admin" in str(echec.value)


@pytest.mark.integration
def test_deux_SUPER_ADMIN_de_periodes_disjointes_sont_acceptes(cx: Connection) -> None:
    """Temoin : l'exclusion ne refuse pas toute succession."""
    personne = _personne(cx, "super@exalt.com")
    for debut, fin in ((JANVIER, JUIN), (JUIN, None)):
        cx.execute(
            text(
                "INSERT INTO technical_role_assignment (person_id, role_type, starts_at, "
                "ends_at) VALUES (:p, 'SUPER_ADMIN', :debut, :fin)"
            ),
            {"p": personne, "debut": debut, "fin": fin},
        )
    total = cx.execute(text("SELECT count(*) FROM technical_role_assignment")).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_les_SEPT_relations_portent_une_exclusion_EN_BASE(cx: Connection) -> None:
    """Le compte, confronte a un attendu, sur l'etat REEL.

    Doublon assume du script `make historisation-check` : celui-ci tourne dans la
    suite de tests, donc a chaque pull request, la ou le script est une cible
    separee. Et `alembic check` etant AVEUGLE aux exclusions -- mesure du
    19/08/2026 -- il n'existe aucun autre garde-fou.
    """
    portees = set(
        cx.execute(text("SELECT conrelid::regclass::text FROM pg_constraint WHERE contype = 'x'"))
        .scalars()
        .all()
    )
    manquantes = TABLES_HISTORISEES - portees
    assert not manquantes, (
        f"{len(manquantes)} relation(s) du §25.2 sans exclusion en base : {sorted(manquantes)}"
    )
    assert len(TABLES_HISTORISEES & portees) == 7, (
        f"7 relations attendues, {len(TABLES_HISTORISEES & portees)} trouvees"
    )
