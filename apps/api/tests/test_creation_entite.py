"""Creer une entite depuis des modeles generiques — LOT 9, `T12`, `MVP-L09-US007`.

CE QUE CETTE SUITE PROUVE

  1. une entite se cree DIRECTEMENT `active` (`activated_at` pose), et son
     premier administrateur est nomme dans la MEME transaction
     (`technical_role_assignment`, `ENTITY_ADMIN`) ;
  2. un code deja utilise est refuse en 409, sans deuxieme ecriture ;
  3. une personne introuvable est refusee en 422, AVANT toute ecriture ;
  4. `est_super_administrateur` (extrait de `resoudre_les_permissions`,
     branche 1) rend le meme verdict pour une entite GLOBALE (`entity_id`
     n'intervient pas dans son calcul).

Ce fichier ne reteste PAS la resolution `DSM > CIRCLE > ENTITY > GLOBAL` du
LOT 7, ni le rendu `null` des contenus d'une entite vierge (LOT 6/8) : les
deux sont deja prouves la-bas, et l'entete de `app/entities/creation.py`
explique pourquoi aucun des deux n'a besoin d'un nouveau code ici.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.entities.creation import (
    CODE_CODE_DEJA_UTILISE,
    CODE_PERSONNE_INTROUVABLE,
    DemandeDeCreationDEntite,
    creer_une_entite,
)
from app.organization.modeles import TypeRoleTechnique
from app.permissions.services import est_super_administrateur
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T12"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Creation', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
    ).scalar_one()


def _demande(*, code: str, administrateur: uuid.UUID) -> DemandeDeCreationDEntite:
    return DemandeDeCreationDEntite(
        code=code,
        display_name=f"Entite {code}",
        city="Lyon",
        country_code="FR",
        timezone="Europe/Paris",
        premier_administrateur=administrateur,
    )


@pytest.mark.integration
def test_TEMOIN_une_entite_se_cree_avec_son_premier_administrateur(cx: Connection) -> None:
    code = f"{MARQUEUR}-N1"
    admin = _personne(cx, "ADMIN1")
    acteur = _personne(cx, "SUPER1")

    cree = creer_une_entite(
        cx, demande=_demande(code=code, administrateur=admin), acteur=acteur, instant=JANVIER
    )

    assert cree.code == code
    assert cree.version == 1

    statut, activee = cx.execute(
        text("SELECT status, activated_at FROM entity WHERE id = :id"), {"id": cree.id}
    ).one()
    assert statut == "active"
    assert activee is not None

    role = cx.execute(
        text(
            "SELECT role_type, entity_id FROM technical_role_assignment "
            "WHERE person_id = :p AND entity_id = :e"
        ),
        {"p": admin, "e": cree.id},
    ).one()
    assert role[0] == TypeRoleTechnique.ENTITY_ADMIN.value
    assert role[1] == cree.id


@pytest.mark.integration
def test_aucun_contenu_ni_responsabilite_n_existe_pour_une_entite_neuve(cx: Connection) -> None:
    """L'entite nait VIERGE — voir l'arbitrage dans l'en-tete du module source."""
    admin = _personne(cx, "ADMIN2")
    acteur = _personne(cx, "SUPER2")
    cree = creer_une_entite(
        cx,
        demande=_demande(code=f"{MARQUEUR}-N2", administrateur=admin),
        acteur=acteur,
        instant=JANVIER,
    )

    pages = cx.execute(
        text("SELECT count(*) FROM content_page WHERE entity_id = :e"), {"e": cree.id}
    ).scalar_one()
    cercles = cx.execute(
        text("SELECT count(*) FROM circle WHERE entity_id = :e"), {"e": cree.id}
    ).scalar_one()
    responsabilites = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment WHERE entity_id = :e"),
        {"e": cree.id},
    ).scalar_one()
    assert (pages, cercles, responsabilites) == (0, 0, 0)


@pytest.mark.integration
def test_un_code_deja_utilise_est_refuse_en_409_sans_deuxieme_ecriture(cx: Connection) -> None:
    code = f"{MARQUEUR}-DUP"
    admin1, admin2 = _personne(cx, "ADMIN3"), _personne(cx, "ADMIN4")
    acteur = _personne(cx, "SUPER3")
    creer_une_entite(
        cx, demande=_demande(code=code, administrateur=admin1), acteur=acteur, instant=JANVIER
    )
    avant = cx.execute(
        text("SELECT count(*) FROM entity WHERE code = :c"), {"c": code}
    ).scalar_one()

    with pytest.raises(ErreurApplicative) as excinfo, cx.begin_nested():
        creer_une_entite(
            cx, demande=_demande(code=code, administrateur=admin2), acteur=acteur, instant=JANVIER
        )
    assert excinfo.value.code == CODE_CODE_DEJA_UTILISE
    assert excinfo.value.statut == 409

    apres = cx.execute(
        text("SELECT count(*) FROM entity WHERE code = :c"), {"c": code}
    ).scalar_one()
    assert apres == avant == 1


@pytest.mark.integration
def test_une_personne_introuvable_est_refusee_en_422_avant_toute_ecriture(cx: Connection) -> None:
    acteur = _personne(cx, "SUPER4")
    code = f"{MARQUEUR}-N5"
    avant = cx.execute(text("SELECT count(*) FROM entity")).scalar_one()

    with pytest.raises(ErreurApplicative) as excinfo:
        creer_une_entite(
            cx,
            demande=_demande(code=code, administrateur=uuid.uuid4()),
            acteur=acteur,
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_PERSONNE_INTROUVABLE
    assert excinfo.value.statut == 422

    apres = cx.execute(text("SELECT count(*) FROM entity")).scalar_one()
    assert apres == avant


@pytest.mark.integration
def test_est_super_administrateur_ne_depend_d_aucune_entite(cx: Connection) -> None:
    personne = _personne(cx, "GLOBAL")
    assert est_super_administrateur(cx, personne, JANVIER) is False

    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, NULL, :role, :debut)"
        ),
        {"p": personne, "role": TypeRoleTechnique.SUPER_ADMIN.value, "debut": JANVIER},
    )
    assert est_super_administrateur(cx, personne, JANVIER) is True
