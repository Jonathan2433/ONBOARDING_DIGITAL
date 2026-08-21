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


def _esm(connexion: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    """Une personne REELLEMENT ESM de cette entite — LOT 3, `T5`.

    **CES TESTS NOMMAIENT DEJA LEUR ATTRIBUTEUR `esm`, MAIS IL N'ETAIT ESM DE
    RIEN.** C'etait sans consequence tant que personne ne verifiait son droit ;
    `T5` acquitte la dette du §8.4, et les quatre tests ont echoue -- avec raison.
    §7.21 : un controle ne devient pas faux tout seul.

    L'intention du nom est desormais portee par la base, non par le nom.
    """
    personne = _personne(connexion, adresse)
    connexion.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, '2026-01-01T00:00:00Z')"
        ),
        {"p": personne, "e": entite},
    )
    return personne


def _super_administrateur(connexion: Connection, adresse: str) -> uuid.UUID:
    """Une personne SUPER_ADMIN — role technique GLOBAL, §8.6, `entity_id` NUL."""
    personne = _personne(connexion, adresse)
    connexion.execute(
        text(
            "INSERT INTO technical_role_assignment "
            "(person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, NULL, 'SUPER_ADMIN', '2026-01-01T00:00:00Z')"
        ),
        {"p": personne},
    )
    return personne


@pytest.mark.integration
def test_un_attributeur_SANS_DROIT_est_refuse(cx: Connection) -> None:
    """**LA DETTE DE `T11` DU LOT 2, ACQUITTEE — §8.4.**

    « Un DG recoit automatiquement une responsabilite DSM » suppose un attributeur,
    et le §8.4 exige qu'il soit « ESM ou super-administrateur ». `T11` avait pose
    l'attributeur en parametre obligatoire mais **ne verifiait pas son droit** : le
    service acceptait n'importe qui.

    Le cas exerce ici est le plus trompeur : un **DSM** de l'entite. Il a un role,
    il est legitime, et il n'a PAS ce droit-la — le DSM encadre des consultants,
    il n'administre pas les categories.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    dsm = _personne(cx, "dsm@exalt.com")
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, '2026-01-01T00:00:00Z')"
        ),
        {"p": dsm, "e": entite},
    )
    with pytest.raises(ErreurDeService, match="ni ESM"):
        attribuer_la_categorie_dg(cx, entite=entite, appartenance=appartenance, attribue_par=dsm)


@pytest.mark.integration
def test_un_SUPER_ADMINISTRATEUR_peut_attribuer(cx: Connection) -> None:
    """Le temoin global : le §8.6 le pose sans entite, la matrice en fait « la
    seule exception globale ». Sans ce test, une implementation qui n'accepterait
    QUE l'ESM passerait le precedent.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    patron = _super_administrateur(cx, "super@exalt.com")
    assert attribuer_la_categorie_dg(
        cx, entite=entite, appartenance=appartenance, attribue_par=patron
    )


@pytest.mark.integration
def test_un_ESM_d_une_AUTRE_entite_est_refuse(cx: Connection) -> None:
    """**LA PORTEE EST LE POINT.** Le §8.4 fait de l'ESM une responsabilite
    d'ENTITE. Un ESM de Lille n'administre pas Bordeaux, et l'accepter ferait de
    lui un super-administrateur en silence — exactement l'inverse du §2.5.
    """
    bordeaux = _entite(cx, "BORDEAUX")
    lille = _entite(cx, "LILLE")
    appartenance = _appartenance(cx, bordeaux, "dg@exalt.com")
    esm_de_lille = _esm(cx, lille, "esm-lille@exalt.com")
    with pytest.raises(ErreurDeService, match="ni ESM"):
        attribuer_la_categorie_dg(
            cx, entite=bordeaux, appartenance=appartenance, attribue_par=esm_de_lille
        )


@pytest.mark.integration
def test_un_ESM_dont_la_responsabilite_est_CLOTUREE_est_refuse(cx: Connection) -> None:
    """**Controle §24.12 du cahier** : « un role cloture ne continue pas a
    accorder des permissions ».

    Sans ce test, une verification ecrite `ends_at IS NULL` passerait — et elle
    accepterait aussi une responsabilite FUTURE, dont `ends_at` est nul lui aussi.
    C'est pourquoi la verification interroge la plage `period`, non la colonne.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    ancien_esm = _personne(cx, "ex-esm@exalt.com")
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, "
            " starts_at, ends_at) "
            "VALUES (:p, :e, 'ESM', :p, '2024-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"
        ),
        {"p": ancien_esm, "e": entite},
    )
    with pytest.raises(ErreurDeService, match="ni ESM"):
        attribuer_la_categorie_dg(
            cx, entite=entite, appartenance=appartenance, attribue_par=ancien_esm
        )


@pytest.mark.integration
def test_un_ESM_dont_la_responsabilite_est_FUTURE_est_refuse(cx: Connection) -> None:
    """Le second piege de `ends_at IS NULL` : une responsabilite a venir en a un.

    Elle ne doit rien accorder aujourd'hui, et c'est la plage `period` qui le dit.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    futur_esm = _personne(cx, "futur-esm@exalt.com")
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, '2099-01-01T00:00:00Z')"
        ),
        {"p": futur_esm, "e": entite},
    )
    with pytest.raises(ErreurDeService, match="ni ESM"):
        attribuer_la_categorie_dg(
            cx, entite=entite, appartenance=appartenance, attribue_par=futur_esm
        )


@pytest.mark.integration
def test_le_service_cree_la_responsabilite_DSM_puis_la_categorie(cx: Connection) -> None:
    """L'ACTION du §8.4, que `T10` avait laissee au service — `DEC-514`.

    **L'ordre est impose par le declencheur** : la responsabilite d'abord, la
    categorie ensuite. C'est ce que le service evite a son appelant de savoir.
    """
    entite = _entite(cx, "BORDEAUX")
    appartenance = _appartenance(cx, entite, "dg@exalt.com")
    esm = _esm(cx, entite, "esm@exalt.com")

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
    esm = _esm(cx, entite, "esm@exalt.com")

    premiere = attribuer_la_categorie_dg(
        cx, entite=entite, appartenance=appartenance, attribue_par=esm
    )
    seconde = attribuer_la_categorie_dg(
        cx, entite=entite, appartenance=appartenance, attribue_par=esm
    )
    assert premiere == seconde
    #  LE COMPTE PORTE SUR LE TYPE `DSM`, ET C'EST UN CORRECTIF DE `T5`.
    #
    #  Ce test comptait TOUTE la table et attendait 1. Depuis que l'attributeur
    #  est un ESM reel — la dette du §8.4, acquittee — le decor y pose une
    #  seconde ligne, et le compte global valait 2. **Le compte n'a pas ete
    #  relache : il a ete rendu EXACT**, sur ce que ce test mesure vraiment — le
    #  service ne doit pas creer un second `DSM`. §7.21.
    total = cx.execute(
        text(
            "SELECT count(*) FROM framework_responsibility_assignment "
            "WHERE responsibility_type = 'DSM'"
        )
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
    #  L'ESM est celui de BORDEAUX : c'est l'entite VISEE par l'appel. Sans ce
    #  droit, le service refuserait pour la mauvaise raison, et ce test ne
    #  prouverait plus ce qu'il annonce — le refus doit venir de l'appartenance
    #  etrangere, pas du droit.
    esm = _esm(cx, bordeaux, "esm@exalt.com")
    with pytest.raises(ErreurDeService, match="inconnue dans l'entite"):
        attribuer_la_categorie_dg(cx, entite=bordeaux, appartenance=appartenance, attribue_par=esm)
    #  LE COMPTE PORTE SUR `DSM` : ce que ce test verifie est que le service n'a
    #  RIEN CREE. Le decor, lui, contient legitimement la responsabilite ESM de
    #  l'attributeur depuis `T5`. Compter toute la table melangerait le decor et
    #  l'effet mesure. §7.21.
    assert (
        cx.execute(
            text(
                "SELECT count(*) FROM framework_responsibility_assignment "
                "WHERE responsibility_type = 'DSM'"
            )
        ).scalar_one()
        == 0
    )


@pytest.mark.integration
def test_responsabilite_dsm_active_ne_regarde_QUE_l_entite_donnee(cx: Connection) -> None:
    """« DSM **local** » : le mot local n'est pas decoratif."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance = _appartenance(cx, lille, "dg@exalt.com")
    esm = _esm(cx, lille, "esm@exalt.com")
    attribuer_la_categorie_dg(cx, entite=lille, appartenance=appartenance, attribue_par=esm)

    personne = cx.execute(
        text("SELECT person_id FROM entity_membership WHERE id = :i"), {"i": appartenance}
    ).scalar_one()
    assert responsabilite_dsm_active(cx, entite=lille, personne=personne) is not None
    assert responsabilite_dsm_active(cx, entite=bordeaux, personne=personne) is None
