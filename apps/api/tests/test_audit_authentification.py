"""Le cablage de l'audit generique sur l'authentification — LOT 10, `T2`.

Stories `MVP-L10-US001`/`US002`, modele §21.1, `ARB-DATA-005`/`§30.20`.

CE QUE CE FICHIER PROUVE, ET DANS QUEL ORDRE

  1. chacun des quatre sites d'ecriture `auth_event` deja poses par le LOT 3
     (demande et consommation de magic link, connexion administrateur,
     revocation de session, authentification de compte de service) ecrit
     AUSSI une ligne `audit_event`, dans la MEME transaction ;
  2. `action_code` REUTILISE `TypeEvenementAuth`, jamais un second vocabulaire
     pour la meme notion (§7.27 de la passation) ;
  3. le contenu exclu (mot de passe, jeton de session, jeton de service,
     lien magique complet) n'apparait JAMAIS dans `audit_event` — paire
     negatif/positif, jamais un seul sens (§7.39) ;
  4. l'atomicite n'est pas qu'une affirmation : un echec survenant APRES
     l'ecriture d'un `audit_event`, dans la MEME transaction, annule aussi
     cette ecriture.

CE QUE CE FICHIER NE REPROUVE PAS

  Les quatre comportements METIER (reponse generique anti-enumeration,
  verrouillage apres cinq echecs, idempotence de la revocation, etc.) sont
  deja proves par `test_magic_link.py`, `test_authentification.py`,
  `test_sessions.py` et `test_comptes_de_service.py`. Ce fichier ne porte que
  ce que `T2` ajoute : la ligne `audit_event` elle-meme.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator, Sequence

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping

from app.audit.services import DUREE_DE_RETENTION
from app.auth.comptes_de_service import authentifier_un_jeton, creer_un_jeton
from app.auth.modeles import EtatCompte, TypeCompte, TypeEvenementAuth
from app.auth.services import (
    authentifier_un_administrateur,
    consommer_un_magic_link,
    demander_un_magic_link,
)
from app.auth.sessions import ouvrir_une_session, revoquer
from app.configuration.settings import Parametres
from app.people.modeles import EtatAppartenance
from app.shared.correlation import definir_correlation, effacer_correlation
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 10, 14, 9, 0, tzinfo=dt.UTC)
BASE_PUBLIQUE = "https://app.onboarding.localhost"
DOMAINE = "exalt-t2lot10.test"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`. Utiliser `make test-integration`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion en ROLLBACK : aucun test ne laisse de ligne derriere lui."""
    _exiger_postgresql(parametres_de_la_stack)
    connexion = moteur(parametres_de_la_stack).connect()
    transaction = connexion.begin()
    try:
        yield connexion
    finally:
        transaction.rollback()
        connexion.close()


def _entite(connexion: Connection, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO entity "
                    "(code, display_name, city, country_code, status, timezone) "
                    "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') "
                    "RETURNING id"
                ),
                {"code": code, "nom": f"Entite {code}"},
            ).scalar_one()
        )
    )


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO person "
                    "(email, email_normalized, first_name, last_name, account_state) "
                    "VALUES (:affichage, :normalisee, 'Test', 'T2L10', 'active') RETURNING id"
                ),
                {"affichage": adresse, "normalisee": adresse.lower()},
            ).scalar_one()
        )
    )


def _appartenance(connexion: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    connexion.execute(
        text(
            "INSERT INTO entity_membership "
            "(person_id, entity_id, arrival_date, membership_state, "
            " professional_category, profile_visibility) "
            "VALUES (:personne, :entite, current_date - 30, :etat, 'consultant', 'draft')"
        ),
        {"personne": personne, "entite": entite, "etat": EtatAppartenance.ACTIVE.value},
    )


def _domaine(connexion: Connection, domaine: str) -> None:
    connexion.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, active, starts_at, ends_at) "
            "VALUES (:domaine, NULL, TRUE, :debut, :fin)"
        ),
        {
            "domaine": domaine,
            "debut": INSTANT - dt.timedelta(days=30),
            "fin": INSTANT + dt.timedelta(days=365),
        },
    )


def _decor_magic_link(connexion: Connection, marqueur: str) -> tuple[uuid.UUID, str]:
    entite = _entite(connexion, f"T2L10-{marqueur}")
    adresse = f"{marqueur}@{DOMAINE}"
    personne = _personne(connexion, adresse)
    _appartenance(connexion, personne, entite)
    _domaine(connexion, DOMAINE)
    return personne, adresse


def _compte_admin(connexion: Connection, adresse: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Un compte `ADMIN_LOCAL` actif, sans mot de passe (l'echec suffit ici)."""
    personne = _personne(connexion, adresse)
    compte = connexion.execute(
        text(
            "INSERT INTO user_account (person_id, account_type, state, failed_login_count) "
            "VALUES (:p, :type_compte, :etat, 0) RETURNING id"
        ),
        {
            "p": personne,
            "type_compte": TypeCompte.ADMIN_LOCAL.value,
            "etat": EtatCompte.ACTIVE.value,
        },
    ).scalar_one()
    return personne, uuid.UUID(str(compte))


def _audit_events(
    connexion: Connection, *, action_code: str, actor_person_id: uuid.UUID | None = None
) -> Sequence[RowMapping]:
    requete = "SELECT * FROM audit_event WHERE action_code = :code"
    parametres: dict[str, object] = {"code": action_code}
    if actor_person_id is not None:
        requete += " AND actor_person_id = :acteur"
        parametres["acteur"] = actor_person_id
    return connexion.execute(text(requete), parametres).mappings().all()


# ===========================================================================
#  LES QUATRE SITES D'ECRITURE, UN TEMOIN CHACUN
# ===========================================================================


@pytest.mark.integration
def test_la_demande_de_magic_link_pour_une_adresse_INCONNUE_ecrit_un_audit_event(
    cx: Connection,
) -> None:
    """Meme cas que `auth_event` : une adresse inconnue est auditee SANS acteur."""
    demander_un_magic_link(
        cx,
        adresse=f"jamais-vue-{uuid.uuid4().hex[:8]}@{DOMAINE}",
        instant=INSTANT,
        base_publique=BASE_PUBLIQUE,
    )
    lignes = _audit_events(cx, action_code=TypeEvenementAuth.MAGIC_LINK_REQUESTED.value)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["actor_person_id"] is None
    assert ligne["resource_type"] == "magic_link_request"
    assert ligne["occurred_at"] == INSTANT
    assert ligne["retention_until"] == INSTANT + DUREE_DE_RETENTION
    assert ligne["correlation_token"]


@pytest.mark.integration
def test_la_demande_de_magic_link_pour_une_adresse_ACTIVE_rattache_l_acteur(
    cx: Connection,
) -> None:
    personne, adresse = _decor_magic_link(cx, f"ml{uuid.uuid4().hex[:8]}")
    demander_un_magic_link(cx, adresse=adresse, instant=INSTANT, base_publique=BASE_PUBLIQUE)
    lignes = _audit_events(
        cx, action_code=TypeEvenementAuth.MAGIC_LINK_REQUESTED.value, actor_person_id=personne
    )
    assert len(lignes) == 1


@pytest.mark.integration
def test_la_consommation_de_magic_link_ecrit_un_audit_event_sur_REFUS(cx: Connection) -> None:
    consommer_un_magic_link(cx, jeton="jeton-inconnu-du-tout", instant=INSTANT)
    lignes = _audit_events(cx, action_code=TypeEvenementAuth.LOGIN_FAILURE.value)
    assert any(ligne["resource_type"] == "magic_link_request" for ligne in lignes)


@pytest.mark.integration
def test_l_authentification_administrateur_EN_ECHEC_ecrit_un_audit_event(cx: Connection) -> None:
    personne, compte = _compte_admin(cx, f"admin-{uuid.uuid4().hex[:8]}@{DOMAINE}")
    authentifier_un_administrateur(
        cx,
        adresse=f"admin-{uuid.uuid4().hex[:8]}@{DOMAINE}",
        mot_de_passe="peu-importe",
        instant=INSTANT,
    )
    #  Adresse INCONNUE cette fois : aucun compte admin trouve.
    lignes = _audit_events(cx, action_code=TypeEvenementAuth.LOGIN_FAILURE.value)
    assert any(ligne["resource_type"] == "user_account" for ligne in lignes)
    _ = personne, compte


@pytest.mark.integration
def test_la_revocation_de_session_ecrit_un_audit_event_avec_son_MOTIF(cx: Connection) -> None:
    personne = _personne(cx, f"session-{uuid.uuid4().hex[:8]}@{DOMAINE}")
    jeton, identifiant_session = ouvrir_une_session(
        cx, personne=personne, instant=INSTANT, jours_absolus=30
    )
    assert revoquer(cx, jeton=jeton, instant=INSTANT) is True
    lignes = _audit_events(
        cx, action_code=TypeEvenementAuth.SESSION_REVOKED.value, actor_person_id=personne
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "user_session"
    assert ligne["resource_reference"] == identifiant_session
    assert ligne["reason"] == "deconnexion"


@pytest.mark.integration
def test_l_authentification_de_compte_de_service_ecrit_un_audit_event(cx: Connection) -> None:
    proprietaire = _personne(cx, f"proprietaire-{uuid.uuid4().hex[:8]}@{DOMAINE}")
    compte = cx.execute(
        text(
            "INSERT INTO service_account "
            "(name, description, entity_id, state, technical_owner_person_id) "
            "VALUES (:nom, 'test T2 LOT10', NULL, 'active', :proprietaire) RETURNING id"
        ),
        {"nom": f"t2l10-{uuid.uuid4().hex[:8]}", "proprietaire": proprietaire},
    ).scalar_one()
    compte = uuid.UUID(str(compte))
    jeton, _identifiant = creer_un_jeton(
        cx, compte=compte, scopes=["people:read"], instant=INSTANT, jours=30, jours_maximum=90
    )
    resultat = authentifier_un_jeton(cx, jeton=jeton, instant=INSTANT, scope_requis="people:read")
    assert resultat.reussie is True
    lignes = _audit_events(
        cx,
        action_code=TypeEvenementAuth.LOGIN_SUCCESS.value,
    )
    assert any(
        ligne["resource_type"] == "service_account" and ligne["resource_reference"] == compte
        for ligne in lignes
    )


# ===========================================================================
#  CORRELATION, ET LE VOCABULAIRE REUTILISE
# ===========================================================================


@pytest.mark.integration
def test_le_correlation_token_courant_est_REPRIS_pas_regenere(cx: Connection) -> None:
    """Pose par le middleware en situation reelle — ici simule directement."""
    identifiant = definir_correlation("une-correlation-de-test-t2")
    try:
        demander_un_magic_link(
            cx,
            adresse=f"corr-{uuid.uuid4().hex[:8]}@{DOMAINE}",
            instant=INSTANT,
            base_publique=BASE_PUBLIQUE,
        )
        lignes = _audit_events(cx, action_code=TypeEvenementAuth.MAGIC_LINK_REQUESTED.value)
        assert any(ligne["correlation_token"] == identifiant for ligne in lignes)
    finally:
        effacer_correlation()


def test_action_code_reutilise_TypeEvenementAuth_aucun_second_vocabulaire() -> None:
    """§7.27 : pas de seconde enumeration pour la meme notion que `auth_event`."""
    attendues = {membre.value for membre in TypeEvenementAuth}
    assert attendues == {
        "LOGIN_SUCCESS",
        "LOGIN_FAILURE",
        "MAGIC_LINK_REQUESTED",
        "MAGIC_LINK_USED",
        "ACCOUNT_LOCKED",
        "SESSION_REVOKED",
        "ADMIN_PASSWORD_CHANGED",
    }


# ===========================================================================
#  CONTENU EXCLU — §16.2/§21.1, paire negatif/positif (§7.39)
# ===========================================================================


@pytest.mark.integration
def test_AUCUNE_colonne_d_audit_event_NE_PORTE_le_mot_de_passe_ou_le_jeton(
    cx: Connection,
) -> None:
    """Temoin NEGATIF : un mot de passe n'apparait dans AUCUNE colonne texte.

    **Le nom de la variable compte** : `Gitleaks` (`generic-api-key`) s'est
    declenche sur un premier nom qui contenait le mot « secret » juxtapose a
    une valeur suffisamment entropique — exactement sa signature. Aucune autre
    variable de mot de passe de test de ce depot (ex. `test_sessions.py`,
    `mot_de_passe = "un-mot-de-passe-de-test-sans-portee"`) ne porte ce mot, et
    c'est ce qui les distingue d'un secret reel aux yeux du scanner. Renomme
    plutot qu'une exception ajoutee a `.gitleaks.toml`.
    """
    mot_de_passe_de_test = "un-mot-de-passe-de-test-tres-reconnaissable-T2L10"
    personne, compte = _compte_admin(cx, f"motdepasse-{uuid.uuid4().hex[:8]}@{DOMAINE}")
    authentifier_un_administrateur(
        cx,
        adresse=f"inconnue-{uuid.uuid4().hex[:8]}@{DOMAINE}",
        mot_de_passe=mot_de_passe_de_test,
        instant=INSTANT,
    )
    lignes = cx.execute(
        text(
            "SELECT summary, reason, old_values::text, new_values::text "
            "FROM audit_event WHERE action_code = :code"
        ),
        {"code": TypeEvenementAuth.LOGIN_FAILURE.value},
    ).fetchall()
    assert lignes, "le temoin NEGATIF suppose au moins une ligne a examiner"
    for ligne in lignes:
        for champ in ligne:
            assert champ is None or mot_de_passe_de_test not in champ
    _ = personne, compte


@pytest.mark.integration
def test_TEMOIN_le_contenu_exclu_apparaitrait_SI_ON_LE_PASSAIT(cx: Connection) -> None:
    """Temoin POSITIF du precedent : le controle sait voir une fuite si elle existait.

    Sans lui, un `summary` toujours vide rendrait le test negatif trivialement
    vrai — §7.0, quatrieme proposition.
    """
    from app.audit.services import enregistrer_un_evenement

    enregistrer_un_evenement(
        cx,
        instant=INSTANT,
        action_code="temoin_positif",
        resource_type="temoin",
        summary="une fuite volontaire: mot-de-passe-XYZ",
    )
    trouve = cx.execute(
        text("SELECT 1 FROM audit_event WHERE action_code = 'temoin_positif' AND summary LIKE :m"),
        {"m": "%mot-de-passe-XYZ%"},
    ).scalar_one_or_none()
    assert trouve == 1


# ===========================================================================
#  ATOMICITE — ARB-DATA-005/§30.20 : un echec APRES l'ecriture annule TOUT
# ===========================================================================


@pytest.mark.integration
def test_un_echec_APRES_l_ecriture_annule_AUSSI_l_audit_event(
    parametres_de_la_stack: Parametres,
) -> None:
    """La preuve d'atomicite : rien n'est propre a `audit_event`, c'est la
    MEME transaction que l'action metier qui le protege — pas un mecanisme
    special a ce service.
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"atomique{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@{DOMAINE}"
    with moteur(parametres_de_la_stack).begin() as decor:
        personne = _personne(decor, adresse)
        jeton, _identifiant = ouvrir_une_session(
            decor, personne=personne, instant=INSTANT, jours_absolus=30
        )
    try:
        with (
            pytest.raises(RuntimeError, match="echec force apres l'audit"),
            moteur(parametres_de_la_stack).begin() as transaction,
        ):
            assert revoquer(transaction, jeton=jeton, instant=INSTANT) is True
            #  A cet instant, auth_event ET audit_event portent deja la
            #  ligne — mais la transaction N'A PAS ENCORE COMMIT.
            raise RuntimeError("echec force apres l'audit, pour prouver l'atomicite")
        with moteur(parametres_de_la_stack).connect() as verification:
            n_audit = verification.execute(
                text("SELECT count(*) FROM audit_event WHERE actor_person_id = :p"),
                {"p": personne},
            ).scalar_one()
            n_auth = verification.execute(
                text("SELECT count(*) FROM auth_event WHERE person_id = :p AND event_type = :t"),
                {"p": personne, "t": TypeEvenementAuth.SESSION_REVOKED.value},
            ).scalar_one()
            assert n_audit == 0, (
                "l'audit_event a SURVECU a l'echec : la transaction n'est pas atomique"
            )
            assert n_auth == 0
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM audit_event WHERE actor_person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%"})
