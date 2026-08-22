"""Les sept tables d'authentification — modele §10.

LOT 3, sous-etape `T2`.

CHAQUE CONTRAINTE A DEUX TESTS : celui qui l'enfreint, et le TEMOIN qui la
respecte. Et pour les quatre unicites derivees, le temoin ne se contente pas
d'accepter un cas simple : **il prouve que la contrainte n'interdit pas ce que le
modele autorise**. C'est le contresens que `T7` et `T8` du LOT 2 ont appris a
eviter -- un index unique naif sur `person_id` casserait la permission du §10.1
d'avoir DEUX comptes.

LES SEPT TABLES SONT CREEES PAR LA MIGRATION `0012`, sous le regime du moindre
privilege de `T1` : un test verifie qu'elles sont **immediatement lisibles** par le
role d'execution, sur les tables REELLES et non sur une table jetable.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.auth import (
    ETATS_COMPTE,
    JOURS_MAXIMUM_DE_SESSION,
    MINUTES_DE_VALIDITE_DU_MAGIC_LINK,
    TYPES_COMPTE,
    TYPES_EVENEMENT_AUTH,
)
from app.configuration.settings import Parametres
from app.shared.database import moteur

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
EMPREINTE = "a" * 64

TABLES_D_AUTHENTIFICATION = (
    "user_account",
    "admin_password_credential",
    "magic_link_request",
    "user_session",
    "service_account",
    "service_token",
    "auth_event",
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
            "VALUES (:courriel, :normalise, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"courriel": adresse, "normalise": adresse},
    ).scalar_one()


def _compte(
    connexion: Connection, personne: uuid.UUID, type_compte: str = "EMPLOYEE_MAGIC_LINK"
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO user_account (person_id, account_type, state, failed_login_count) "
            "VALUES (:p, :t, 'active', 0) RETURNING id"
        ),
        {"p": personne, "t": type_compte},
    ).scalar_one()


def _magic_link(
    connexion: Connection,
    personne: uuid.UUID,
    empreinte: str,
    *,
    minutes: int = MINUTES_DE_VALIDITE_DU_MAGIC_LINK,
    utilise: bool = False,
    invalide: bool = False,
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO magic_link_request (person_id, token_hash, requested_at, expires_at, "
            "used_at, invalidated_at) "
            "VALUES (:p, :h, :demande, :demande + make_interval(mins => :m), :u, :i) RETURNING id"
        ),
        {
            "p": personne,
            "h": empreinte,
            "demande": JANVIER,
            "m": minutes,
            "u": JANVIER if utilise else None,
            "i": JANVIER if invalide else None,
        },
    ).scalar_one()


# ---------------------------------------------------------------------------
#  Le point de passation de `T1` : les tables NEUVES sont-elles lisibles ?
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_les_SEPT_tables_sont_lisibles_par_le_role_d_EXECUTION(cx: Connection) -> None:
    """**LE TEST QUE `T1` A DEMANDE**, et il porte sur les tables REELLES.

    `make privileges-check` prouve les privileges par defaut sur une table
    JETABLE. Celui-ci les prouve sur les sept tables que la migration `0012` vient
    de creer : c'est la difference entre « le mecanisme fonctionne » et « il a
    fonctionne pour ces tables-la ».

    Sans les privileges par defaut de `T1`, chaque migration devrait accorder ses
    droits, et l'oubli echouerait a l'EXECUTION alors que la migration a REUSSI.
    """
    lues = 0
    for table in TABLES_D_AUTHENTIFICATION:
        #  Le nom vient d'un tuple de ce module, jamais d'une entree.
        total = cx.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608
        assert total >= 0
        lues += 1
    assert lues == len(TABLES_D_AUTHENTIFICATION) == 7, f"{lues} tables lues, 7 attendues"


# ---------------------------------------------------------------------------
#  §10.1 `user_account`
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_une_personne_PEUT_avoir_les_DEUX_types_de_compte(cx: Connection) -> None:
    """§10.1 : « un compte employe ET, si necessaire, un compte administrateur local ».

    **C'EST UNE PERMISSION, ET LE TEMOIN QUI COMPTE.** Un index unique naif sur
    `person_id` seul la casserait, et le livrable paraitrait correct puisqu'il
    refuserait bien quelque chose -- exactement le contresens de `T7` et `T8`.
    """
    personne = _personne(cx, "double@exalt.com")
    for type_compte in TYPES_COMPTE:
        _compte(cx, personne, type_compte)
    total = cx.execute(
        text("SELECT count(*) FROM user_account WHERE person_id = :p"), {"p": personne}
    ).scalar_one()
    assert total == len(TYPES_COMPTE) == 2


@pytest.mark.integration
def test_deux_comptes_du_MEME_type_sont_refuses(cx: Connection) -> None:
    """L'interdiction, distincte de la permission ci-dessus."""
    personne = _personne(cx, "double@exalt.com")
    _compte(cx, personne, "ADMIN_LOCAL")
    with pytest.raises(IntegrityError, match="uq_user_account_person_id_account_type"):
        _compte(cx, personne, "ADMIN_LOCAL")


@pytest.mark.integration
def test_un_type_de_compte_hors_liste_est_refuse(cx: Connection) -> None:
    personne = _personne(cx, "a@exalt.com")
    with pytest.raises(IntegrityError, match="account_type_valide"):
        _compte(cx, personne, "MAGIQUE")


@pytest.mark.integration
def test_tous_les_etats_declares_sont_acceptes(cx: Connection) -> None:
    """Temoin du precedent : la contrainte n'interdit pas les valeurs du modele."""
    for indice, etat in enumerate(ETATS_COMPTE):
        personne = _personne(cx, f"etat{indice}@exalt.com")
        cx.execute(
            text(
                "INSERT INTO user_account (person_id, account_type, state, failed_login_count) "
                "VALUES (:p, 'ADMIN_LOCAL', :e, 0)"
            ),
            {"p": personne, "e": etat},
        )
    total = cx.execute(text("SELECT count(*) FROM user_account")).scalar_one()
    assert total == len(ETATS_COMPTE) == 3


@pytest.mark.integration
def test_un_compteur_d_echecs_negatif_est_refuse(cx: Connection) -> None:
    personne = _personne(cx, "a@exalt.com")
    with pytest.raises(IntegrityError, match="failed_login_count_positif"):
        cx.execute(
            text(
                "INSERT INTO user_account (person_id, account_type, state, failed_login_count) "
                "VALUES (:p, 'ADMIN_LOCAL', 'active', -1)"
            ),
            {"p": personne},
        )


# ---------------------------------------------------------------------------
#  §10.2 `admin_password_credential`
# ---------------------------------------------------------------------------


def _identifiant(connexion: Connection, compte: uuid.UUID, *, revoque: bool = False) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO admin_password_credential (user_account_id, password_hash, algorithm, "
            "parameters, changed_at, must_change, revoked_at) "
            "VALUES (:c, :empreinte, 'argon2id', :parametres, :quand, false, :revoque) "
            "RETURNING id"
        ),
        {
            "c": compte,
            "empreinte": "$argon2id$v=19$m=65536,t=3,p=4$c2VsZXQ$empreinte",
            "parametres": json.dumps({"m": 65536, "t": 3, "p": 4}),
            "quand": JANVIER,
            "revoque": JANVIER if revoque else None,
        },
    ).scalar_one()


@pytest.mark.integration
def test_deux_mots_de_passe_ACTIFS_pour_un_compte_sont_refuses(cx: Connection) -> None:
    """Derive de `revoked_at` : deux empreintes actives rendraient la verification ambigue."""
    compte = _compte(cx, _personne(cx, "admin@exalt.com"), "ADMIN_LOCAL")
    _identifiant(cx, compte)
    with pytest.raises(IntegrityError, match="uq_admin_password_credential"):
        _identifiant(cx, compte)


@pytest.mark.integration
def test_un_mot_de_passe_REVOQUE_permet_un_nouveau(cx: Connection) -> None:
    """Temoin du precedent : l'unicite est PARTIELLE, elle n'interdit pas la rotation."""
    compte = _compte(cx, _personne(cx, "admin@exalt.com"), "ADMIN_LOCAL")
    _identifiant(cx, compte, revoque=True)
    _identifiant(cx, compte)
    total = cx.execute(text("SELECT count(*) FROM admin_password_credential")).scalar_one()
    assert total == 2


# ---------------------------------------------------------------------------
#  §10.3 `magic_link_request`
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_deux_liens_ACTIFS_pour_une_personne_sont_refuses(cx: Connection) -> None:
    """§10.3 : « le dernier lien invalide les precedents encore actifs ».

    **L'INDEX PARTIEL PORTE L'INVARIANT, PAS L'ACTION.** Il ne fait pas
    l'invalidation : il la rend OBLIGATOIRE. Un service qui insererait sans
    invalider verrait son insertion refusee, ce qui est le parti de `DEC-514`.
    """
    personne = _personne(cx, "lien@exalt.com")
    _magic_link(cx, personne, "a" * 64)
    with pytest.raises(IntegrityError, match="uq_magic_link_request_person_id_actif"):
        _magic_link(cx, personne, "b" * 64)


@pytest.mark.integration
def test_un_nouveau_lien_est_accepte_apres_INVALIDATION(cx: Connection) -> None:
    """Temoin : l'invariant n'interdit pas la reemission, il l'ordonne."""
    personne = _personne(cx, "lien@exalt.com")
    _magic_link(cx, personne, "a" * 64, invalide=True)
    _magic_link(cx, personne, "b" * 64)
    total = cx.execute(text("SELECT count(*) FROM magic_link_request")).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_un_nouveau_lien_est_accepte_apres_CONSOMMATION(cx: Connection) -> None:
    """Second temoin : un lien consomme n'est plus actif."""
    personne = _personne(cx, "lien@exalt.com")
    _magic_link(cx, personne, "a" * 64, utilise=True)
    _magic_link(cx, personne, "b" * 64)
    assert cx.execute(text("SELECT count(*) FROM magic_link_request")).scalar_one() == 2


@pytest.mark.integration
def test_deux_liens_de_MEME_empreinte_sont_refuses(cx: Connection) -> None:
    """§25.1, litteralement : `magic_link_request(token_hash) UNIQUE`."""
    _magic_link(cx, _personne(cx, "un@exalt.com"), EMPREINTE)
    with pytest.raises(IntegrityError, match="uq_magic_link_request_token_hash"):
        _magic_link(cx, _personne(cx, "deux@exalt.com"), EMPREINTE)


@pytest.mark.integration
def test_une_expiration_AUTRE_que_quinze_minutes_est_refusee(cx: Connection) -> None:
    """§10.3 : « 15 minutes apres emission ». La valeur est dans le cahier."""
    with pytest.raises(IntegrityError, match="expiration_a_quinze_minutes"):
        _magic_link(cx, _personne(cx, "a@exalt.com"), EMPREINTE, minutes=16)


@pytest.mark.integration
def test_une_expiration_a_EXACTEMENT_quinze_minutes_est_acceptee(cx: Connection) -> None:
    """Temoin du precedent, et il emploie la constante — jamais un 15 recopie."""
    _magic_link(
        cx,
        _personne(cx, "a@exalt.com"),
        EMPREINTE,
        minutes=MINUTES_DE_VALIDITE_DU_MAGIC_LINK,
    )
    assert cx.execute(text("SELECT count(*) FROM magic_link_request")).scalar_one() == 1


@pytest.mark.integration
def test_un_lien_a_la_fois_CONSOMME_et_INVALIDE_est_refuse(cx: Connection) -> None:
    """Les deux colonnes decrivent des fins de vie exclusives."""
    with pytest.raises(IntegrityError, match="fin_de_vie_exclusive"):
        _magic_link(cx, _personne(cx, "a@exalt.com"), EMPREINTE, utilise=True, invalide=True)


# ---------------------------------------------------------------------------
#  §10.4 `user_session`
# ---------------------------------------------------------------------------


def _session(connexion: Connection, personne: uuid.UUID, *, jours: int) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO user_session (session_token_hash, person_id, last_activity_at, "
            "absolute_expires_at) "
            "VALUES (:h, :p, now(), now() + make_interval(days => :j)) RETURNING id"
        ),
        {"h": uuid.uuid4().hex + uuid.uuid4().hex, "p": personne, "j": jours},
    ).scalar_one()


@pytest.mark.integration
def test_une_session_de_TRENTE_jours_est_acceptee(cx: Connection) -> None:
    """§10.4 : « absolute_expires_at | Maximum 30 jours ». La borne est INCLUSE."""
    _session(cx, _personne(cx, "a@exalt.com"), jours=JOURS_MAXIMUM_DE_SESSION)
    assert cx.execute(text("SELECT count(*) FROM user_session")).scalar_one() == 1


@pytest.mark.integration
def test_une_session_de_TRENTE_ET_UN_jours_est_refusee(cx: Connection) -> None:
    with pytest.raises(IntegrityError, match="duree_absolue_bornee"):
        _session(cx, _personne(cx, "a@exalt.com"), jours=JOURS_MAXIMUM_DE_SESSION + 1)


@pytest.mark.integration
def test_deux_sessions_de_MEME_empreinte_sont_refusees(cx: Connection) -> None:
    """§25.1, litteralement : `user_session(session_token_hash) UNIQUE`."""
    personne = _personne(cx, "a@exalt.com")
    cx.execute(
        text(
            "INSERT INTO user_session (session_token_hash, person_id, last_activity_at, "
            "absolute_expires_at) VALUES (:h, :p, now(), now() + interval '1 day')"
        ),
        {"h": EMPREINTE, "p": personne},
    )
    with pytest.raises(IntegrityError, match="uq_user_session_session_token_hash"):
        cx.execute(
            text(
                "INSERT INTO user_session (session_token_hash, person_id, last_activity_at, "
                "absolute_expires_at) VALUES (:h, :p, now(), now() + interval '1 day')"
            ),
            {"h": EMPREINTE, "p": personne},
        )


# ---------------------------------------------------------------------------
#  §10.5 `service_account` et `service_token`
# ---------------------------------------------------------------------------


def _compte_de_service(
    connexion: Connection, nom: str, proprietaire: uuid.UUID, *, entite: uuid.UUID | None = None
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO service_account (name, entity_id, state, technical_owner_person_id) "
            "VALUES (:nom, :e, 'active', :o) RETURNING id"
        ),
        {"nom": nom, "e": entite, "o": proprietaire},
    ).scalar_one()


@pytest.mark.integration
def test_un_compte_de_service_SANS_entite_est_accepte(cx: Connection) -> None:
    """§10.5 : « une entite FACULTATIVE ». C'est la seule table de ce lot qui en porte une."""
    _compte_de_service(cx, "integration-si", _personne(cx, "tech@exalt.com"))
    entite = cx.execute(text("SELECT entity_id FROM service_account")).scalar_one()
    assert entite is None


@pytest.mark.integration
def test_deux_comptes_de_service_de_MEME_nom_sont_refuses(cx: Connection) -> None:
    proprietaire = _personne(cx, "tech@exalt.com")
    _compte_de_service(cx, "integration-si", proprietaire)
    with pytest.raises(IntegrityError, match="uq_service_account_name"):
        _compte_de_service(cx, "integration-si", proprietaire)


@pytest.mark.integration
def test_des_scopes_qui_ne_sont_PAS_un_tableau_sont_refuses(cx: Connection) -> None:
    """§10.5 : « les scopes ». Aucun catalogue n'existe — c'est `T10` — mais la
    FORME est contrainte : un objet ou une chaine passerait sans cette contrainte.
    """
    compte = _compte_de_service(cx, "integration-si", _personne(cx, "tech@exalt.com"))
    with pytest.raises(IntegrityError, match="scopes_est_un_tableau"):
        cx.execute(
            text(
                "INSERT INTO service_token (service_account_id, token_hash, expires_at, scopes) "
                "VALUES (:c, :h, now() + interval '1 day', :s)"
            ),
            {"c": compte, "h": EMPREINTE, "s": json.dumps({"lecture": True})},
        )


@pytest.mark.integration
def test_des_scopes_en_TABLEAU_sont_acceptes(cx: Connection) -> None:
    """Temoin du precedent."""
    compte = _compte_de_service(cx, "integration-si", _personne(cx, "tech@exalt.com"))
    cx.execute(
        text(
            "INSERT INTO service_token (service_account_id, token_hash, expires_at, scopes) "
            "VALUES (:c, :h, now() + interval '1 day', :s)"
        ),
        {"c": compte, "h": EMPREINTE, "s": json.dumps(["lecture:personnes"])},
    )
    assert cx.execute(text("SELECT count(*) FROM service_token")).scalar_one() == 1


# ---------------------------------------------------------------------------
#  §10.6 `auth_event`
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_les_SEPT_types_d_evenement_sont_acceptes(cx: Connection) -> None:
    """§10.6 en compte SEPT, et le compte est DERIVE de l'enumeration."""
    for type_evenement in TYPES_EVENEMENT_AUTH:
        cx.execute(
            text("INSERT INTO auth_event (event_type, occurred_at) VALUES (:t, :quand)"),
            {"t": type_evenement, "quand": JANVIER},
        )
    #  LE FILTRE SUR `occurred_at` EST UN CORRECTIF DE `T3`, ET IL N'AFFAIBLIT
    #  RIEN : le test compte toujours les SEPT lignes qu'il vient d'inserer.
    #
    #  Sa version de `T2` comptait `auth_event` SANS filtre, ce qui supposait la
    #  table vide. C'etait vrai tant qu'aucun code applicatif n'y ecrivait ; `T3`
    #  y ecrit un evenement par demande de magic link, et ce test a echoue. §7.21 :
    #  un controle ne devient pas faux tout seul, il le devient quand le monde
    #  change autour de lui -- et ici le changement EST le livrable.
    total = cx.execute(
        text("SELECT count(*) FROM auth_event WHERE occurred_at = :quand"),
        {"quand": JANVIER},
    ).scalar_one()
    assert total == len(TYPES_EVENEMENT_AUTH) == 7


@pytest.mark.integration
def test_un_type_d_evenement_hors_liste_est_refuse(cx: Connection) -> None:
    with pytest.raises(IntegrityError, match="event_type_valide"):
        cx.execute(
            text("INSERT INTO auth_event (event_type, occurred_at) VALUES ('BIDON', :quand)"),
            {"quand": JANVIER},
        )


@pytest.mark.integration
def test_un_evenement_SANS_personne_est_accepte(cx: Connection) -> None:
    """**CE N'EST PAS UN RELACHEMENT, C'EST LE CAS QUI COMPTE.**

    Un echec de connexion sur une adresse INCONNUE doit pouvoir etre trace sans
    rattacher l'evenement a une personne qui n'existe pas -- c'est precisement ce
    que la reponse generique anti-enumeration du §10.3 protege. `person_id` et
    `user_account_id` sont donc nullables.
    """
    cx.execute(
        text(
            "INSERT INTO auth_event (event_type, occurred_at, request_origin_hash) "
            "VALUES ('LOGIN_FAILURE', :quand, :origine)"
        ),
        {"quand": JANVIER, "origine": EMPREINTE},
    )
    #  Meme correctif de `T3` que ci-dessus : la ligne examinee est celle que ce
    #  test vient d'inserer, identifiee par son empreinte d'origine et son
    #  horodatage. `.one()` sans filtre echouait des qu'une autre ligne existait.
    personne, compte = cx.execute(
        text(
            "SELECT person_id, user_account_id FROM auth_event "
            "WHERE occurred_at = :quand AND request_origin_hash = :origine"
        ),
        {"quand": JANVIER, "origine": EMPREINTE},
    ).one()
    assert personne is None
    assert compte is None
