"""Archiver et restaurer un cercle ou un bureau — LOT 9, `T4`, `MVP-L09-US008`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. le TEMOIN positif : un cercle sans membre actif s'archive puis se
     restaure, `archived_at`/`archived_by_person_id` poses puis effaces, la
     version incrementee aux deux gestes — meme discipline qu'un bureau, qui
     n'a AUCUNE condition de ressource ;
  2. la condition de ressource du §10.2, « si aucun membre actif » : un
     cercle PORTANT un membre actif (meme secondaire) refuse l'archivage en
     `409`, quel que soit le role — ce module ne teste pas les roles, ceux-ci
     sont de la garde generique `exiger_un_role_dans_l_entite`, deja prouvee
     ailleurs ;
  3. le verrou optimiste du §18.4 : une version perimee, une cible inconnue,
     et une cible dans le mauvais etat rendent la MEME forme de refus (§2.5) ;
  4. le conflit de code a la restauration : l'index partiel du §25.1 libere
     le code a l'archivage, et une restauration qui le retrouverait DEJA PRIS
     par un cercle/bureau neuf est refusee plutot que de le dupliquer.

Ce fichier ne reteste PAS `exiger_un_role_dans_l_entite` ni
`resoudre_les_permissions` : des briques generiques, deja prouvees par
d'autres suites, reutilisees sans modification par les routes de `T4`.
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
from app.organization.cycle_de_vie import (
    CODE_CODE_DEJA_PRIS,
    CODE_MEMBRES_ACTIFS,
    CODE_VERSION_OBSOLETE,
    archiver_un_bureau,
    archiver_un_cercle,
    restaurer_un_bureau,
    restaurer_un_cercle,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T4"
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


def _entite(cx: Connection, suffixe: str) -> uuid.UUID:
    code = f"{MARQUEUR}-{suffixe}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _acteur(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Archivage', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
    ).scalar_one()


def _ajouter_un_membre_actif(
    cx: Connection, entite: uuid.UUID, cercle: uuid.UUID, *, type_: str = "secondary"
) -> None:
    """Un membre ACTIF (`ends_at IS NULL`) du cercle — §10.2, « si aucun membre actif »."""
    personne = _acteur(cx, f"MBR-{uuid.uuid4().hex[:6]}")
    appartenance = cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_membership_id, entity_id, circle_id, "
            "membership_type, starts_at) VALUES (:a, :e, :c, :t, :d)"
        ),
        {"a": appartenance, "e": entite, "c": cercle, "t": type_, "d": JANVIER},
    )


@pytest.mark.integration
def test_TEMOIN_un_cercle_SANS_membre_est_archive_puis_restaure(cx: Connection) -> None:
    entite = _entite(cx, "C1")
    acteur = _acteur(cx, "C1")
    cercle = _cercle(cx, entite, "CERCLE1")

    archive = archiver_un_cercle(
        cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=1, instant=JANVIER
    )
    assert archive.version == 2
    assert archive.archive_le == JANVIER

    etat = cx.execute(
        text("SELECT archived_at, archived_by_person_id, version FROM circle WHERE id = :c"),
        {"c": cercle},
    ).one()
    assert etat[0] == JANVIER
    assert etat[1] == acteur
    assert etat[2] == 2

    plus_tard = JANVIER + dt.timedelta(days=1)
    restaure = restaurer_un_cercle(
        cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=2, instant=plus_tard
    )
    assert restaure.version == 3

    etat_final = cx.execute(
        text("SELECT archived_at, archived_by_person_id FROM circle WHERE id = :c"), {"c": cercle}
    ).one()
    assert etat_final[0] is None
    assert etat_final[1] is None


@pytest.mark.integration
def test_archiver_un_cercle_AVEC_un_membre_actif_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "C2")
    acteur = _acteur(cx, "C2")
    cercle = _cercle(cx, entite, "CERCLE2")
    #  Un membre SECONDAIRE suffit : la condition du §10.2 ne distingue pas
    #  principal/secondaire, contrairement a d'autres regles du §8.2.
    _ajouter_un_membre_actif(cx, entite, cercle, type_="secondary")

    with pytest.raises(ErreurApplicative) as excinfo:
        archiver_un_cercle(
            cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=1, instant=JANVIER
        )
    assert excinfo.value.code == CODE_MEMBRES_ACTIFS
    assert excinfo.value.statut == 409

    #  Rien n'a bouge : le refus precede toute ecriture.
    inchange = cx.execute(
        text("SELECT archived_at, version FROM circle WHERE id = :c"), {"c": cercle}
    ).one()
    assert inchange[0] is None
    assert inchange[1] == 1


@pytest.mark.integration
def test_une_version_obsolete_est_refusee_en_409_pour_le_cercle(cx: Connection) -> None:
    entite = _entite(cx, "C3")
    acteur = _acteur(cx, "C3")
    cercle = _cercle(cx, entite, "CERCLE3")

    with pytest.raises(ErreurApplicative) as excinfo:
        archiver_un_cercle(
            cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=99, instant=JANVIER
        )
    assert excinfo.value.code == CODE_VERSION_OBSOLETE
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_restaurer_un_cercle_INEXISTANT_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "C4")
    acteur = _acteur(cx, "C4")

    with pytest.raises(ErreurApplicative) as excinfo:
        restaurer_un_cercle(
            cx,
            entite=entite,
            cercle=uuid.uuid4(),
            acteur=acteur,
            version_attendue=1,
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_VERSION_OBSOLETE
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_restaurer_un_cercle_dont_le_code_a_ete_repris_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "C5")
    acteur = _acteur(cx, "C5")
    cercle = _cercle(cx, entite, "REPRIS")

    archiver_un_cercle(
        cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=1, instant=JANVIER
    )
    #  L'index partiel du §25.1 libere le code : un cercle NEUF peut le reprendre.
    _cercle(cx, entite, "REPRIS")

    with pytest.raises(ErreurApplicative) as excinfo:
        restaurer_un_cercle(
            cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=2, instant=JANVIER
        )
    assert excinfo.value.code == CODE_CODE_DEJA_PRIS
    assert excinfo.value.statut == 409
    assert excinfo.value.champ == "code"


@pytest.mark.integration
def test_TEMOIN_un_bureau_est_archive_puis_restaure(cx: Connection) -> None:
    """Aucune condition de ressource ici, a la difference d'un cercle."""
    entite = _entite(cx, "B1")
    acteur = _acteur(cx, "B1")
    bureau = _bureau(cx, entite, "BUREAU1")

    archive = archiver_un_bureau(
        cx, entite=entite, bureau=bureau, acteur=acteur, version_attendue=1, instant=JANVIER
    )
    assert archive.version == 2
    assert archive.archive_le == JANVIER

    restaure = restaurer_un_bureau(
        cx, entite=entite, bureau=bureau, acteur=acteur, version_attendue=2, instant=JANVIER
    )
    assert restaure.version == 3

    etat_final = cx.execute(
        text("SELECT archived_at, archived_by_person_id FROM office WHERE id = :b"), {"b": bureau}
    ).one()
    assert etat_final[0] is None
    assert etat_final[1] is None


@pytest.mark.integration
def test_restaurer_un_bureau_dont_le_code_a_ete_repris_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "B2")
    acteur = _acteur(cx, "B2")
    bureau = _bureau(cx, entite, "REPRIS-B")

    archiver_un_bureau(
        cx, entite=entite, bureau=bureau, acteur=acteur, version_attendue=1, instant=JANVIER
    )
    _bureau(cx, entite, "REPRIS-B")

    with pytest.raises(ErreurApplicative) as excinfo:
        restaurer_un_bureau(
            cx, entite=entite, bureau=bureau, acteur=acteur, version_attendue=2, instant=JANVIER
        )
    assert excinfo.value.code == CODE_CODE_DEJA_PRIS
    assert excinfo.value.statut == 409
