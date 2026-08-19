"""Clients globaux, activations locales et alias — modele §7.1 a §7.3.

LOT 2, sous-etape `T6`, story `MVP-L02-US003`.

DEUX TESTS PORTENT SUR DES NON-ACTIONS, ET CE SONT LES PLUS DIFFICILES A ECRIRE.

  - « les rapprochements ne fusionnent rien automatiquement » est le critere
    d'acceptation de `US003` sur les alias, et `DATA-005` l'arbitrage qui le
    fonde. Une regle de NON-action ne se prouve qu'en montrant que l'etat
    n'a PAS change ;
  - la normalisation minimale se prouve de la meme facon : en montrant qu'elle
    NE rapproche PAS deux noms que rien n'autorise a rapprocher.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.clients import STATUTS_CLIENT, StatutClient, normaliser_nom_client
from app.configuration.settings import Parametres
from app.shared.database import moteur

# ============================================================================
#  1. Unitaires
# ============================================================================


def test_les_deux_statuts_du_modele() -> None:
    """§7.1 : « `status` | `active` ou `archived` ». Deux, la ou `entity` en a quatre."""
    assert STATUTS_CLIENT == ("active", "archived")
    assert [m.value for m in StatutClient] == list(STATUTS_CLIENT)


def test_la_normalisation_reduit_casse_et_espaces() -> None:
    assert normaliser_nom_client("  ACME   Corporation  ") == "acme corporation"


def test_la_normalisation_ne_RAPPROCHE_PAS_ce_que_rien_n_autorise() -> None:
    """L'etroitesse de la normalisation est IMPOSEE par le modele, pas subie.

    `DATA-005` exige une validation humaine des alias, et le §7.3 conclut
    qu'« aucune proposition de rapprochement n'ecrit directement dans cette table
    sans validation humaine ».

    **Une normalisation qui retirerait les traits d'union, les accents ou les
    formes juridiques serait ce rapprochement automatique**, fait en amont et sans
    laisser de trace dans `client_alias`. Ce test le verrouille.
    """
    assert normaliser_nom_client("Saint-Gobain") != normaliser_nom_client("Saint Gobain")
    assert normaliser_nom_client("Elevate") != normaliser_nom_client("Élevate")
    assert normaliser_nom_client("Acme SAS") != normaliser_nom_client("Acme")


# ============================================================================
#  2. Integration
# ============================================================================


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


def _client(
    connexion: Connection, nom: str = "acme corporation", *, statut: str = "active"
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affiche, :statut) RETURNING id"
        ),
        {"canonique": nom, "affiche": nom.title(), "statut": statut},
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


def _personne(connexion: Connection, adresse: str = "valideur@exalt-company.com") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, 'Val', 'Ideur', 'active') RETURNING id"
        ),
        {"a": adresse, "b": adresse},
    ).scalar_one()


def _activer(connexion: Connection, entite: uuid.UUID, client: uuid.UUID) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c) RETURNING id"),
        {"e": entite, "c": client},
    ).scalar_one()


def _alias(
    connexion: Connection,
    client: uuid.UUID,
    valideur: uuid.UUID,
    alias: str = "acme corp",
    *,
    entite: uuid.UUID | None = None,
    valide: bool = True,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO client_alias (alias_normalized, client_id, entity_id, "
            "validated_by_person_id, validated_at) VALUES (:alias, :c, :e, :v, "
            "CASE WHEN :valide THEN now() ELSE NULL END)"
        ),
        {"alias": alias, "c": client, "e": entite, "v": valideur, "valide": valide},
    )


# ----------------------------------------------------------------------------
#  §7.1 — client, referentiel GLOBAL
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_client_est_GLOBAL_et_ne_porte_pas_entity_id(cx: Connection) -> None:
    """`DATA-004` : « les clients sont globaux et actives par entite »."""
    colonnes = set(
        cx.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'client'")
        )
        .scalars()
        .all()
    )
    assert "entity_id" not in colonnes, (
        "client est global : une colonne entity_id contredirait DATA-004. "
        "Le rattachement local est porte par entity_client."
    )
    for attendue in ("canonical_name", "display_name", "status"):
        assert attendue in colonnes, f"colonne du §7.1 absente : {attendue}"


@pytest.mark.integration
def test_le_nom_canonique_est_unique(cx: Connection) -> None:
    _client(cx, "acme corporation")
    with pytest.raises(IntegrityError) as echec:
        _client(cx, "acme corporation")
    assert "uq_client_canonical_name" in str(echec.value)


@pytest.mark.integration
def test_deux_noms_canoniques_differents_sont_acceptes(cx: Connection) -> None:
    """Temoin du precedent."""
    _client(cx, "acme corporation")
    _client(cx, "saint-gobain")
    assert cx.execute(text("SELECT count(*) FROM client")).scalar_one() == 2


@pytest.mark.integration
def test_un_nom_canonique_NON_normalise_est_refuse(cx: Connection) -> None:
    """« Nom officiel UNIQUE SELON NORMALISATION », §7.1. Voie de `ECART-029`.

    Exiger que la valeur STOCKEE soit deja normalisee rend l'index unique simple
    suffisant : deux graphies du meme nom ne peuvent pas coexister, l'une ne
    pouvant pas etre ecrite.
    """
    cas = (
        ("ACME Corporation", "canonical_name_en_minuscules"),
        (" acme corporation", "canonical_name_espaces_reduits"),
        ("acme corporation ", "canonical_name_espaces_reduits"),
        ("acme  corporation", "canonical_name_espaces_reduits"),
        ("", "canonical_name_non_vide"),
    )
    for valeur, contrainte in cas:
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            _client(cx, valeur)
        assert contrainte in str(echec.value), f"attendu {contrainte} pour {valeur!r}"


@pytest.mark.integration
def test_les_noms_normalises_sont_acceptes(cx: Connection) -> None:
    """Temoin : la normalisation minimale ne refuse pas ce qui est legitime.

    Elle accepte traits d'union, accents et formes juridiques -- precisement ce
    qu'une normalisation agressive aurait ecrase, et donc rapproche
    automatiquement.
    """
    for nom in ("saint-gobain", "élevate", "acme sas", "a"):
        _client(cx, nom)
    assert cx.execute(text("SELECT count(*) FROM client")).scalar_one() == 4


@pytest.mark.integration
def test_les_deux_statuts_sont_acceptes_et_un_troisieme_refuse(cx: Connection) -> None:
    for indice, statut in enumerate(STATUTS_CLIENT):
        _client(cx, f"client{indice}", statut=statut)
    assert cx.execute(text("SELECT count(*) FROM client")).scalar_one() == len(STATUTS_CLIENT)
    with pytest.raises(IntegrityError) as echec:
        _client(cx, "autre", statut="suspended")
    assert "status_valide" in str(echec.value)


# ----------------------------------------------------------------------------
#  §7.2 — entity_client, et ses trois capacites
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_client_est_PARTAGE_entre_plusieurs_entites(cx: Connection) -> None:
    """§7.2, premiere capacite : « partager le meme client entre plusieurs entites »."""
    client = _client(cx)
    _activer(cx, _entite(cx, "BORDEAUX"), client)
    _activer(cx, _entite(cx, "LILLE"), client)
    assert cx.execute(text("SELECT count(*) FROM entity_client")).scalar_one() == 2
    assert cx.execute(text("SELECT count(*) FROM client")).scalar_one() == 1, (
        "un seul client global, active deux fois : c'est tout le propos de DATA-004"
    )


@pytest.mark.integration
def test_une_activation_ne_se_duplique_pas(cx: Connection) -> None:
    """L'unicite n'est PAS partielle : reactiver doit reutiliser la ligne existante."""
    entite, client = _entite(cx), _client(cx)
    _activer(cx, entite, client)
    with pytest.raises(IntegrityError) as echec:
        _activer(cx, entite, client)
    assert "uq_entity_client_entity_id_client_id" in str(echec.value)


@pytest.mark.integration
def test_l_ABSENCE_d_activation_est_signifiante(cx: Connection) -> None:
    """§7.2, deuxieme capacite : « ne pas afficher tous les clients partout ».

    Aucune colonne ne dit « visible » : c'est l'EXISTENCE de la ligne qui le dit.
    Ce test montre qu'un client global peut exister sans etre active nulle part.
    """
    _client(cx, "acme corporation")
    _entite(cx)
    assert cx.execute(text("SELECT count(*) FROM client")).scalar_one() == 1
    assert cx.execute(text("SELECT count(*) FROM entity_client")).scalar_one() == 0


@pytest.mark.integration
def test_l_archivage_LOCAL_ne_touche_PAS_au_client_global(cx: Connection) -> None:
    """§7.2, troisieme capacite : « archiver localement sans supprimer le client global »."""
    client = _client(cx, "acme corporation")
    activation = _activer(cx, _entite(cx, "BORDEAUX"), client)
    autre = _activer(cx, _entite(cx, "LILLE"), client)

    cx.execute(
        text(
            "UPDATE entity_client SET archived_at = now(), archive_reason = 'fin de mission' "
            "WHERE id = :i"
        ),
        {"i": activation},
    )

    statut_global = cx.execute(
        text("SELECT status, archived_at FROM client WHERE id = :i"), {"i": client}
    ).one()
    assert statut_global.status == "active", "le client GLOBAL reste actif"
    assert statut_global.archived_at is None
    autre_encore_active = cx.execute(
        text("SELECT archived_at FROM entity_client WHERE id = :i"), {"i": autre}
    ).scalar_one()
    assert autre_encore_active is None, "l'autre entite n'est pas affectee"


@pytest.mark.integration
def test_une_activation_exige_un_client_ET_une_entite_existants(cx: Connection) -> None:
    entite, client = _entite(cx), _client(cx)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _activer(cx, entite, uuid.uuid4())
    assert "fk_entity_client_client_id_client" in str(echec.value)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _activer(cx, uuid.uuid4(), client)
    assert "fk_entity_client_entity_id_entity" in str(echec.value)


# ----------------------------------------------------------------------------
#  §7.3 — client_alias, et la validation humaine de `DATA-005`
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_alias_SANS_validation_est_refuse(cx: Connection) -> None:
    """§7.3 et `DATA-005` : « validation humaine obligatoire ».

    La derniere phrase du §7.3 leve l'ambiguite du mot « obligatoire » : « aucune
    proposition de rapprochement n'ecrit directement dans cette table sans
    validation humaine ». Une proposition en attente ne vit donc PAS ici -- elle
    vivra dans `import_decision`, §19.4, au LOT 9.
    """
    with pytest.raises(IntegrityError) as echec:
        _alias(cx, _client(cx), _personne(cx), valide=False)
    assert "validated_at" in str(echec.value)


@pytest.mark.integration
def test_un_alias_VALIDE_est_accepte(cx: Connection) -> None:
    """Temoin du precedent."""
    _alias(cx, _client(cx), _personne(cx))
    ligne = cx.execute(
        text("SELECT alias_normalized, entity_id, validated_at FROM client_alias")
    ).one()
    assert ligne.alias_normalized == "acme corp"
    assert ligne.entity_id is None, "un alias GLOBAL a une entite nulle (§7.3)"
    assert ligne.validated_at is not None


@pytest.mark.integration
def test_un_alias_LOCAL_est_accepte(cx: Connection) -> None:
    """§7.3 : « `entity_id` nullable SI alias global » — donc renseignable sinon."""
    _alias(cx, _client(cx), _personne(cx), entite=_entite(cx))
    entite = cx.execute(text("SELECT entity_id FROM client_alias")).scalar_one()
    assert entite is not None


@pytest.mark.integration
def test_un_alias_exige_un_client_ET_un_valideur_existants(cx: Connection) -> None:
    client, valideur = _client(cx), _personne(cx)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _alias(cx, uuid.uuid4(), valideur)
    assert "fk_client_alias_client_id_client" in str(echec.value)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _alias(cx, client, uuid.uuid4())
    assert "fk_client_alias_validated_by_person_id_person" in str(echec.value)


@pytest.mark.integration
def test_un_alias_non_normalise_est_refuse(cx: Connection) -> None:
    """La meme normalisation que `canonical_name` : un alias se compare a des noms.

    Deux normalisations differentes rendraient la comparaison fausse.
    """
    client, valideur = _client(cx), _personne(cx)
    for valeur, contrainte in (
        ("ACME Corp", "alias_normalized_en_minuscules"),
        ("acme  corp", "alias_normalized_espaces_reduits"),
        ("", "alias_normalized_non_vide"),
    ):
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            _alias(cx, client, valideur, valeur)
        assert contrainte in str(echec.value), f"attendu {contrainte} pour {valeur!r}"


@pytest.mark.integration
def test_un_alias_ne_FUSIONNE_RIEN_automatiquement(cx: Connection) -> None:
    """Critere d'acceptation de `US003` : « les rapprochements ne fusionnent rien ».

    UNE REGLE DE NON-ACTION, ET ELLE SE PROUVE EN MONTRANT QUE RIEN N'A CHANGE.
    Creer un alias vers un client canonique ne doit ni modifier ce client, ni
    toucher au client dont l'alias porte le nom, ni en supprimer aucun.
    """
    canonique = _client(cx, "acme corporation")
    homonyme = _client(cx, "acme corp")
    valideur = _personne(cx)

    avant = cx.execute(
        text(
            "SELECT id, canonical_name, display_name, status, version, archived_at "
            "FROM client ORDER BY canonical_name"
        )
    ).all()

    #  L'alias « acme corp » designe le client canonique, alors qu'un AUTRE client
    #  porte ce nom : c'est precisement le cas ou une fusion automatique serait
    #  tentante et destructrice.
    _alias(cx, canonique, valideur, "acme corp")

    apres = cx.execute(
        text(
            "SELECT id, canonical_name, display_name, status, version, archived_at "
            "FROM client ORDER BY canonical_name"
        )
    ).all()

    assert apres == avant, (
        "creer un alias a modifie les clients : DATA-005 et le §7.3 l'interdisent"
    )
    assert cx.execute(text("SELECT count(*) FROM client")).scalar_one() == 2, (
        "les deux clients doivent subsister, homonyme compris"
    )
    assert homonyme != canonique


# ----------------------------------------------------------------------------
#  La dette de `T5`, acquittee
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_une_situation_MISSION_exige_un_client_EXISTANT(cx: Connection) -> None:
    """DETTE DE `T5` ACQUITTEE, et eprouvee par le COMPORTEMENT.

    En `T5`, `client_id` etait un `uuid` sans cle etrangere : n'importe quelle
    valeur passait. La cle est ajoutee par `0007`, et ce test le prouve autrement
    qu'en lisant le catalogue -- il tente l'insertion.
    """
    entite = _entite(cx)
    personne = _personne(cx, "consultant@exalt-company.com")
    appartenance = cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()

    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        cx.execute(
            text(
                "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
                "status, client_id, starts_at) VALUES (:e, :a, 'mission', :c, now())"
            ),
            {"e": entite, "a": appartenance, "c": uuid.uuid4()},
        )
    assert "fk_professional_status_assignment_client_id_client" in str(echec.value)

    #  Temoin : avec un client REEL, l'insertion passe.
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, client_id, starts_at) VALUES (:e, :a, 'mission', :c, now())"
        ),
        {"e": entite, "a": appartenance, "c": _client(cx)},
    )
    assert cx.execute(text("SELECT count(*) FROM professional_status_assignment")).scalar_one() == 1
