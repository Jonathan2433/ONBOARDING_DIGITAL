"""Depots cloisonnes et services transactionnels.

LOT 2, sous-etape `T11`, story `MVP-L02-US006`, livrable 18 de la roadmap.

LE CRITERE DIT « LES CONTRAINTES SQL **ET SERVICES** REFUSENT LES RELATIONS
INCOHERENTES ». Les contraintes sont eprouvees par `test_isolation.py` ; ce
fichier eprouve le second membre.

  Un depot local **ne sait pas** construire une requete sans son `entity_id` :
  l'oubli n'est pas une faute a eviter, c'est une forme qui n'existe pas. Et les
  deux types de depot **ne peuvent pas se confondre**, ce qui est verifie sur le
  schema reel et non sur une liste recopiee.

Tous ces tests tournent sur une transaction ANNULEE — fiche §6.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.organization import (
    ErreurDeService,
    attribuer_la_categorie_dg,
    responsabilite_dsm_active,
)
from app.shared.database import moteur
from app.shared.depot import DepotGlobal, DepotLocal, ErreurDeDepot


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


def _entite(connexion: Connection, code: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:courriel, :normalise, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"courriel": adresse, "normalise": adresse},
    ).scalar_one()


# ---------------------------------------------------------------------------
#  Les deux types de depot ne peuvent pas se confondre
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_un_depot_GLOBAL_refuse_une_table_locale(cx: Connection) -> None:
    """**LE REFUS LE PLUS IMPORTANT DE CE FICHIER.**

    Sans lui, `DepotGlobal` sur `entity_membership` rendrait les lignes de TOUTES
    les entites **en paraissant fonctionner** — la fuite que `US006` interdit, par
    le seul chemin que les cles etrangeres ne couvrent pas.
    """
    with pytest.raises(ErreurDeDepot, match="table LOCALE"):
        DepotGlobal(cx, "entity_membership")


@pytest.mark.integration
def test_un_depot_LOCAL_refuse_une_table_globale(cx: Connection) -> None:
    """Le pendant : `person` n'a pas d'entite, la borner n'aurait aucun sens."""
    with pytest.raises(ErreurDeDepot, match="table GLOBALE"):
        DepotLocal(cx, "person", uuid.uuid4())


@pytest.mark.integration
def test_le_type_de_depot_est_deduit_du_SCHEMA_et_non_d_une_liste(cx: Connection) -> None:
    """Le classement vient d'`information_schema`, donc il ne peut pas vieillir.

    Une liste recopiee de tables locales deviendrait fausse au premier ajout de
    table — classe `ECART-021`. Ce test le montre en verifiant les DEUX sens sur
    quatre tables reelles.
    """
    entite = uuid.uuid4()
    for table in ("entity_membership", "circle", "job_catalog"):
        DepotLocal(cx, table, entite)  # ne leve pas
    for table in ("person", "client", "platform_setting"):
        DepotGlobal(cx, table)  # ne leve pas


@pytest.mark.integration
def test_un_depot_refuse_une_table_INCONNUE(cx: Connection) -> None:
    with pytest.raises(ErreurDeDepot, match="table inconnue"):
        DepotGlobal(cx, "table_qui_n_existe_pas")


@pytest.mark.integration
def test_un_depot_refuse_un_nom_de_table_FANTAISISTE(cx: Connection) -> None:
    """Le nom est interpole dans du SQL : un nom invalide doit echouer clairement."""
    with pytest.raises(ErreurDeDepot, match="nom de table invalide"):
        DepotGlobal(cx, "person; DROP TABLE person")


# ---------------------------------------------------------------------------
#  Le cloisonnement, en lecture
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_un_depot_local_ne_voit_QUE_son_entite(cx: Connection) -> None:
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    for entite, adresse in (
        (bordeaux, "a@exalt.com"),
        (bordeaux, "b@exalt.com"),
        (lille, "c@exalt.com"),
    ):
        cx.execute(
            text(
                "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                "membership_state, professional_category, profile_visibility) "
                "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft')"
            ),
            {"p": _personne(cx, adresse), "e": entite},
        )
    assert cx.execute(text("SELECT count(*) FROM entity_membership")).scalar_one() == 3
    assert DepotLocal(cx, "entity_membership", bordeaux).compter() == 2
    assert DepotLocal(cx, "entity_membership", lille).compter() == 1
    assert len(DepotLocal(cx, "entity_membership", bordeaux).lister()) == 2


@pytest.mark.integration
def test_obtenir_une_ligne_d_une_AUTRE_entite_rend_None(cx: Connection) -> None:
    """`None`, et non la ligne, et non une exception.

    Une ligne d'une autre entite doit etre **indistinguable d'une ligne
    inexistante** : distinguer les deux revelerait son existence, ce que le §2.5
    « refus par defaut » interdit. Meme raisonnement qu'un 404 plutot qu'un 403.
    """
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    cercle_de_lille = cx.execute(
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :c, :n) RETURNING id"),
        {"e": lille, "c": "TECH", "n": "Tech"},
    ).scalar_one()

    depot_de_lille = DepotLocal(cx, "circle", lille)
    assert depot_de_lille.obtenir(cercle_de_lille) is not None

    depot_de_bordeaux = DepotLocal(cx, "circle", bordeaux)
    assert depot_de_bordeaux.obtenir(cercle_de_lille) is None
    assert depot_de_bordeaux.obtenir(uuid.uuid4()) is None, (
        "une ligne d'une autre entite et une ligne inexistante doivent rendre la MEME valeur"
    )


@pytest.mark.integration
def test_un_filtre_sur_une_colonne_inconnue_est_refuse(cx: Connection) -> None:
    """Un filtre fautif doit echouer a l'appel, non produire du SQL malforme."""
    entite = _entite(cx, "BORDEAUX")
    with pytest.raises(ErreurDeDepot, match="colonne\\(s\\) inconnue"):
        DepotLocal(cx, "circle", entite).lister(colonne_inventee="x")


# ---------------------------------------------------------------------------
#  Le cloisonnement, en ecriture
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_creer_renseigne_entity_id_SANS_qu_on_le_donne(cx: Connection) -> None:
    entite = _entite(cx, "BORDEAUX")
    depot = DepotLocal(cx, "circle", entite)
    identifiant = depot.creer(code="TECH", name="Tech")
    lue = cx.execute(
        text("SELECT entity_id FROM circle WHERE id = :i"), {"i": identifiant}
    ).scalar_one()
    assert lue == entite


@pytest.mark.integration
def test_creer_REFUSE_un_entity_id_contradictoire(cx: Connection) -> None:
    """Il refuse, il ne remplace pas en silence.

    Remplacer serait pire : l'appelant croirait avoir ecrit dans une entite et
    aurait ecrit dans une autre, sans aucun signal.
    """
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    depot = DepotLocal(cx, "circle", bordeaux)
    with pytest.raises(ErreurDeDepot, match="contradictoire"):
        depot.creer(code="TECH", name="Tech", entity_id=lille)
    assert depot.compter() == 0


@pytest.mark.integration
def test_creer_avec_le_MEME_entity_id_est_accepte(cx: Connection) -> None:
    """Temoin du precedent : la redondance explicite est toleree."""
    bordeaux = _entite(cx, "BORDEAUX")
    depot = DepotLocal(cx, "circle", bordeaux)
    depot.creer(code="TECH", name="Tech", entity_id=bordeaux)
    assert depot.compter() == 1


@pytest.mark.integration
def test_creer_avec_une_colonne_inconnue_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "BORDEAUX")
    with pytest.raises(ErreurDeDepot, match="colonne\\(s\\) inconnue"):
        DepotLocal(cx, "circle", entite).creer(code="TECH", name="Tech", inventee=1)


# ---------------------------------------------------------------------------
#  Le service : l'ACTION du §8.4, avec un attributeur REEL
# ---------------------------------------------------------------------------


def _appartenance(connexion: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": _personne(connexion, adresse), "e": entite},
    ).scalar_one()


@pytest.mark.integration
def test_le_service_cree_la_responsabilite_DSM_puis_la_categorie(cx: Connection) -> None:
    """L'ACTION du §8.4, que `T10` avait laissee au service — `DEC-514`.

    **L'ordre est impose par le declencheur** : la responsabilite d'abord, la
    categorie ensuite. C'est ce que le service evite a son appelant de savoir.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    esm = _personne(cx, "esm@exalt.com")

    responsabilite = attribuer_la_categorie_dg(
        cx, entite=entite, appartenance=appartenance, attribue_par=esm, motif="nomination"
    )

    categorie = cx.execute(
        text("SELECT professional_category FROM entity_membership WHERE id = :i"),
        {"i": appartenance},
    ).scalar_one()
    assert categorie == "dg"
    auteur, motif = cx.execute(
        text(
            "SELECT assigned_by_person_id, assignment_reason "
            "FROM framework_responsibility_assignment WHERE id = :i"
        ),
        {"i": responsabilite},
    ).one()
    assert auteur == esm, "l'attributeur REEL est trace — c'est tout le motif du service"
    assert motif == "nomination"


@pytest.mark.integration
def test_sans_le_service_la_BASE_refuse_toujours(cx: Connection) -> None:
    """**Le service ne se substitue pas au declencheur, il le satisfait.**

    S'il etait contourne — `psql`, une migration, un correctif — la base
    refuserait toujours. C'est la doctrine de `DEC-498`.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    with pytest.raises(IntegrityError, match="une categorie dg exige une responsabilite DSM"):
        cx.execute(
            text("UPDATE entity_membership SET professional_category = 'dg' WHERE id = :i"),
            {"i": appartenance},
        )


@pytest.mark.integration
def test_le_service_ne_CREE_PAS_de_doublon_si_la_responsabilite_existe(cx: Connection) -> None:
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    esm = _personne(cx, "esm@exalt.com")

    premiere = attribuer_la_categorie_dg(
        cx, entite=entite, appartenance=appartenance, attribue_par=esm
    )
    seconde = attribuer_la_categorie_dg(
        cx, entite=entite, appartenance=appartenance, attribue_par=esm
    )
    assert premiere == seconde
    total = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment")
    ).scalar_one()
    assert total == 1


@pytest.mark.integration
def test_le_service_REFUSE_une_appartenance_d_une_autre_entite(cx: Connection) -> None:
    """Et le message ne distingue pas « inconnue » de « d'une autre entite ».

    Le §2.5 « refus par defaut » veut qu'on ne revele pas l'existence d'une
    ressource d'une autre entite. Meme parti que `DepotLocal.obtenir`.
    """
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance = _appartenance(cx, lille, "dg@exalt.com")
    esm = _personne(cx, "esm@exalt.com")
    with pytest.raises(ErreurDeService, match="inconnue dans l'entite"):
        attribuer_la_categorie_dg(cx, entite=bordeaux, appartenance=appartenance, attribue_par=esm)
    assert (
        cx.execute(text("SELECT count(*) FROM framework_responsibility_assignment")).scalar_one()
        == 0
    )


@pytest.mark.integration
def test_responsabilite_dsm_active_ne_regarde_QUE_l_entite_donnee(cx: Connection) -> None:
    """« DSM **local** » : le mot local n'est pas decoratif."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance = _appartenance(cx, lille, "dg@exalt.com")
    esm = _personne(cx, "esm@exalt.com")
    attribuer_la_categorie_dg(cx, entite=lille, appartenance=appartenance, attribue_par=esm)

    personne = cx.execute(
        text("SELECT person_id FROM entity_membership WHERE id = :i"), {"i": appartenance}
    ).scalar_one()
    assert responsabilite_dsm_active(cx, entite=lille, personne=personne) is not None
    assert responsabilite_dsm_active(cx, entite=bordeaux, personne=personne) is None
