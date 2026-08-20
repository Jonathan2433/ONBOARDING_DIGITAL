"""`person` — identite globale, eprouvee sur PostgreSQL reel.

LOT 2, sous-etape `T3`, story `MVP-L02-US002`.

Comme en `T2`, toutes les ecritures passent par du SQL : ce qui est eprouve, ce
sont les contraintes de la BASE, pas celles de l'ORM.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.people import ETATS_COMPTE, EtatCompte, normaliser_email
from app.shared.database import moteur

# ============================================================================
#  1. Unitaires
# ============================================================================


def test_les_cinq_etats_du_modele() -> None:
    """§6.1 : `pending`, `active`, `suspended`, `departed`, `anonymized`."""
    assert ETATS_COMPTE == ("pending", "active", "suspended", "departed", "anonymized")
    assert [m.value for m in EtatCompte] == list(ETATS_COMPTE)


def test_la_normalisation_met_en_minuscules_et_retire_les_bordures() -> None:
    assert normaliser_email("  Jean.DUPONT@Exalt-Company.COM  ") == "jean.dupont@exalt-company.com"


def test_la_normalisation_ne_touche_NI_aux_points_NI_au_plus() -> None:
    """L'etroitesse de la normalisation est un choix, pas un oubli.

    Retirer les points ou couper a un `+` fusionnerait des personnes DISTINCTES.
    Aucun document du corpus ne le demande, et deux collaborateurs peuvent
    parfaitement s'appeler `j.dupont` et `jdupont`.
    """
    assert normaliser_email("j.dupont@exalt.com") == "j.dupont@exalt.com"
    assert normaliser_email("jdupont+equipe@exalt.com") == "jdupont+equipe@exalt.com"
    assert normaliser_email("j.dupont@exalt.com") != normaliser_email("jdupont@exalt.com")


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
    """Connexion dans une transaction TOUJOURS annulee."""
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _creer_personne(
    connexion: Connection,
    affichage: str = "Jean.Dupont@Exalt-Company.com",
    *,
    normalise: str | None = None,
    etat: str = "pending",
    anonymise: bool = False,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, "
            "account_state, anonymized_at) VALUES (:affichage, :normalise, 'Jean', 'Dupont', "
            ":etat, CASE WHEN :anonymise THEN now() ELSE NULL END)"
        ),
        {
            "affichage": affichage,
            "normalise": normaliser_email(affichage) if normalise is None else normalise,
            "etat": etat,
            "anonymise": anonymise,
        },
    )


@pytest.mark.integration
def test_une_personne_minimale_se_cree(cx: Connection) -> None:
    """La valeur d'affichage garde sa casse ; la forme normalisee est en minuscules."""
    _creer_personne(cx)
    ligne = cx.execute(
        text("SELECT email, email_normalized, account_state, version, anonymized_at FROM person")
    ).one()
    assert ligne.email == "Jean.Dupont@Exalt-Company.com", "l'affichage garde sa casse (§6.1)"
    assert ligne.email_normalized == "jean.dupont@exalt-company.com"
    assert ligne.account_state == "pending"
    assert ligne.version == 1
    assert ligne.anonymized_at is None


@pytest.mark.integration
def test_person_est_GLOBALE_et_ne_porte_pas_entity_id(cx: Connection) -> None:
    """`ARB-DATA-001` : identite globale, donnees locales dans l'appartenance."""
    colonnes = set(
        cx.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'person'")
        )
        .scalars()
        .all()
    )
    assert "entity_id" not in colonnes, (
        "person est globale : une colonne entity_id contredirait ARB-DATA-001"
    )
    for attendue in (
        "email",
        "email_normalized",
        "first_name",
        "last_name",
        "preferred_name",
        "account_state",
        "created_at",
        "anonymized_at",
    ):
        assert attendue in colonnes, f"colonne du §6.1 absente : {attendue}"


@pytest.mark.integration
def test_AUCUNE_table_d_authentification_n_existe(cx: Connection) -> None:
    """Garde-fou de perimetre : l'authentification appartient au LOT 3.

    Le §28 groupe « `person` et authentification » a son point 3, ce qui pourrait
    faire croire qu'elles vont ensemble. Ce controle mesure que non.
    """
    interdites = {
        "user_account",
        "admin_password_credential",
        "magic_link_request",
        "user_session",
        "service_account",
        "service_token",
        "auth_event",
    }
    presentes = set(
        cx.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        .scalars()
        .all()
    )
    fautives = interdites & presentes
    assert not fautives, (
        f"tables d'authentification presentes : {sorted(fautives)}. "
        "Elles appartiennent au LOT 3, porte G3."
    )


# ----------------------------------------------------------------------------
#  Unicite, et l'insensibilite a la casse du §6.1
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_l_email_normalise_est_unique(cx: Connection) -> None:
    _creer_personne(cx, "Jean.Dupont@Exalt-Company.com")
    with pytest.raises(IntegrityError) as echec:
        _creer_personne(cx, "jean.dupont@exalt-company.com")
    assert "email_normalized_unique" in str(echec.value)


@pytest.mark.integration
def test_deux_adresses_differentes_sont_acceptees(cx: Connection) -> None:
    """Temoin du precedent."""
    _creer_personne(cx, "jean.dupont@exalt-company.com")
    _creer_personne(cx, "marie.martin@exalt-company.com")
    assert cx.execute(text("SELECT count(*) FROM person")).scalar_one() == 2


@pytest.mark.integration
def test_une_forme_normalisee_avec_MAJUSCULES_est_refusee(cx: Connection) -> None:
    """C'est ce refus qui rend l'unicite insensible a la casse.

    Le §6.1 exige une unicite insensible a la casse, le §25.1 un index simple.
    Interdire une forme normalisee non minuscule concilie les deux : deux
    graphies du meme e-mail ne peuvent pas coexister, puisque l'une des deux ne
    peut pas etre ecrite.
    """
    with pytest.raises(IntegrityError) as echec:
        _creer_personne(
            cx, "Jean.Dupont@Exalt-Company.com", normalise="Jean.Dupont@Exalt-Company.com"
        )
    assert "email_normalise_en_minuscules" in str(echec.value)


@pytest.mark.integration
def test_une_forme_normalisee_implausible_est_refusee(cx: Connection) -> None:
    for mauvaise in ("jean dupont@exalt.com", "@exalt.com", "jean.dupont-exalt.com"):
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            _creer_personne(cx, "Jean@exalt.com", normalise=mauvaise)
        assert "email_normalise_plausible" in str(echec.value), (
            f"attendu un refus de plausibilite pour {mauvaise!r}"
        )


@pytest.mark.integration
def test_les_formes_normalisees_plausibles_sont_acceptees(cx: Connection) -> None:
    """Temoin : la contrainte de plausibilite ne refuse pas tout.

    Elle accepte volontairement des adresses qu'un validateur strict rejetterait :
    le corpus n'en prescrit aucun, et un refus a l'import du LOT 9 couterait plus
    cher qu'une adresse mal formee stockee.
    """
    for bonne in ("j@exalt.fr", "jean.dupont+equipe@exalt-company.com", "j_d@sous.exalt.co.uk"):
        _creer_personne(cx, bonne)
    assert cx.execute(text("SELECT count(*) FROM person")).scalar_one() == 3


# ----------------------------------------------------------------------------
#  Etat du compte et anonymisation
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_etat_hors_liste_est_refuse(cx: Connection) -> None:
    with pytest.raises(IntegrityError) as echec:
        _creer_personne(cx, etat="parti")
    assert "account_state_valide" in str(echec.value)


@pytest.mark.integration
def test_les_cinq_etats_sont_acceptes(cx: Connection) -> None:
    """Temoin : les cinq valeurs du §6.1 passent, `anonymized` avec son horodatage."""
    for indice, etat in enumerate(ETATS_COMPTE):
        _creer_personne(
            cx, f"personne{indice}@exalt.com", etat=etat, anonymise=(etat == "anonymized")
        )
    assert cx.execute(text("SELECT count(*) FROM person")).scalar_one() == len(ETATS_COMPTE)


@pytest.mark.integration
def test_l_etat_anonymized_exige_un_horodatage(cx: Connection) -> None:
    with pytest.raises(IntegrityError) as echec:
        _creer_personne(cx, etat="anonymized", anonymise=False)
    assert "anonymisation_coherente" in str(echec.value)


@pytest.mark.integration
def test_un_horodatage_d_anonymisation_exige_l_etat(cx: Connection) -> None:
    """L'autre sens de la meme coherence : un horodatage sans l'etat decrirait
    une anonymisation qui n'a pas pris."""
    with pytest.raises(IntegrityError) as echec:
        _creer_personne(cx, etat="active", anonymise=True)
    assert "anonymisation_coherente" in str(echec.value)


@pytest.mark.integration
def test_une_personne_anonymisee_ne_peut_PAS_etre_reactivee(cx: Connection) -> None:
    """§6.1 : « sans creation d'une nouvelle identite ». Regle portee par declencheur."""
    _creer_personne(cx, etat="anonymized", anonymise=True)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(text("UPDATE person SET account_state = 'active'"))
    assert "une personne anonymisee ne peut pas etre reactivee" in str(echec.value), (
        "le message doit etre COMPLET : il est ecrit sur deux litteraux SQL adjacents, "
        "que PostgreSQL concatene. Ce test est ce qui le prouve."
    )


@pytest.mark.integration
def test_aucune_sortie_de_anonymized_n_est_permise(cx: Connection) -> None:
    """Le declencheur refuse TOUTE sortie, pas seulement vers `active`.

    Le §6.1 ne prevoit aucune sortie, et l'anonymisation est irreversible par
    nature : les donnees qu'elle a effacees ne sont plus la pour etre restaurees.
    """
    _creer_personne(cx, etat="anonymized", anonymise=True)
    for cible in ("pending", "active", "suspended", "departed"):
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            cx.execute(text("UPDATE person SET account_state = :etat"), {"etat": cible})
        assert "person_anonymisation_terminale" in str(echec.value) or (
            "ne peut pas etre reactivee" in str(echec.value)
        ), f"sortie vers {cible!r} non refusee"


@pytest.mark.integration
def test_les_autres_transitions_d_etat_restent_permises(cx: Connection) -> None:
    """Temoin : le declencheur ne verrouille QUE la sortie de `anonymized`."""
    _creer_personne(cx, etat="pending")
    for etat in ("active", "suspended", "departed"):
        cx.execute(text("UPDATE person SET account_state = :etat"), {"etat": etat})
    final = cx.execute(text("SELECT account_state FROM person")).scalar_one()
    assert final == "departed"


@pytest.mark.integration
def test_l_anonymisation_elle_meme_est_permise(cx: Connection) -> None:
    """Second temoin : on doit pouvoir ENTRER dans `anonymized`."""
    _creer_personne(cx, etat="departed")
    cx.execute(text("UPDATE person SET account_state = 'anonymized', anonymized_at = now()"))
    ligne = cx.execute(text("SELECT account_state, anonymized_at FROM person")).one()
    assert ligne.account_state == "anonymized"
    assert ligne.anonymized_at is not None
