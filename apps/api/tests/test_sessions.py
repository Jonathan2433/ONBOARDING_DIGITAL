"""Sessions utilisateur — story `MVP-L03-US004`, cahier §7.4, modele §10.4.

LOT 3, sous-etape `T6`.

QUATRE FAMILLES, ET LA QUATRIEME EST CELLE QU'ON OUBLIE

  1. le COOKIE       les trois attributs du §7.4 sur la reponse REELLE, et le
                     jeton n'apparait dans AUCUN corps
  2. les DEUX        inactivite a 7 jours, duree absolue a 30 -- et chacune est
     EXPIRATIONS     bornee des deux cotes, sinon une expiration a cinq minutes
                     passerait le test de l'expiration
  3. la REVOCATION   la deconnexion revoque, elle n'efface pas, et elle est
                     IDEMPOTENTE
  4. l'ATOMICITE     deux requetes concurrentes ne doivent pas RAVIVER une
                     session que l'une des deux vient de laisser expirer

  La quatrieme est la troisieme occurrence du meme patron dans ce lot -- apres
  l'usage unique de `T4` et le compteur d'echecs de `T5`. Lire `last_activity_at`,
  decider, puis ecrire laisserait deux requetes juger valide une session expiree.

LE TEMPS EST INJECTE

  Sept jours et trente jours ne s'attendent pas. `lire_et_rafraichir` recoit son
  `instant`, et c'est lui qui fait avancer l'horloge.
"""

from __future__ import annotations

import datetime as dt
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.modeles import (
    JOURS_D_INACTIVITE_DE_SESSION,
    JOURS_MAXIMUM_DE_SESSION,
    TypeEvenementAuth,
)
from app.auth.sessions import (
    MOTIF_SESSION_ABSENTE,
    MOTIF_SESSION_REFUSEE,
    MOTIF_SESSION_VALIDE,
    REVOCATION_DECONNEXION,
    Session,
    empreinte_de_session,
    engendrer_un_jeton_de_session,
    lire_et_rafraichir,
    ouvrir_une_session,
    revoquer,
)
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.database import moteur
from observabilite.masquage import MASQUE, PREFIXE_SESSION, masquer

INSTANT = dt.datetime(2026, 8, 21, 10, 30, tzinfo=dt.UTC)

#  **LE CLIENT DE TEST PARLE HTTPS, ET CE N'EST PAS UN DETAIL.**
#
#  `TestClient` emploie `http://testserver` par defaut. Un cookie marque `Secure`
#  n'est **jamais renvoye sur une origine non chiffree** : mes deux premiers tests
#  d'aller-retour rendaient 401, et le code etait juste -- c'etait le client qui
#  exercait une autre configuration que la vraie.
#
#  La correction n'est PAS de retirer `Secure` dans les tests : ce serait eprouver
#  un cookie que la production n'emploie pas. C'est de parler HTTPS, comme Caddy le
#  fait (`DEC-446`). Un test qui contourne un attribut de securite pour passer ne
#  prouve rien de cet attribut.
ORIGINE_DE_TEST = "https://testserver"

#  Bornes du test de concurrence. **ECARTEES**, lecon `T4-4` : un `lock_timeout`
#  egal au delai de la barriere rend le test instable une fois sur trois.
DELAI_ATTENTE_VERROU = 10.0
VERROU_TIMEOUT_CONCURRENT = "60s"


# ===========================================================================
#  Le jeton — aucune dependance
# ===========================================================================


def test_le_jeton_porte_le_prefixe_RESERVE_en_T3() -> None:
    """`oss_` a ete reserve en `T3` dans `observabilite.masquage`, avec son motif.

    **Une regle declaree et jamais exercee est une regle dont on ne sait pas si
    elle marche** — c'est ce que la passation de `T5` demandait a `T6` de
    verifier.
    """
    jeton = engendrer_un_jeton_de_session()
    assert jeton.startswith(PREFIXE_SESSION)
    assert PREFIXE_SESSION == "oss_"


def test_deux_jetons_de_session_ne_sont_jamais_egaux() -> None:
    """Un jeton de session previsible est un contournement d'authentification."""
    assert len({engendrer_un_jeton_de_session() for _ in range(200)}) == 200


def test_l_empreinte_fait_soixante_quatre_hexadecimaux() -> None:
    """§25.1 : `user_session(session_token_hash)` UNIQUE, colonne bornee a 64."""
    empreinte = empreinte_de_session(engendrer_un_jeton_de_session())
    assert len(empreinte) == 64
    assert all(c in "0123456789abcdef" for c in empreinte)


def test_le_jeton_de_session_est_MASQUE_par_les_barrieres() -> None:
    """La lecon `T4-1` : un test de filtre eprouve la forme que CE projet produit.

    Le prefixe etait declare depuis `T3` ; c'est ici qu'il est **exerce** sur un
    jeton reellement engendre par le code des sessions.
    """
    jeton = engendrer_un_jeton_de_session()
    assert masquer(jeton, cle="message") == MASQUE
    assert masquer({"detail": f"session {jeton} refusee"})["detail"] == MASQUE


# ===========================================================================
#  Le service — PostgreSQL REEL
# ===========================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion en ROLLBACK, role d'EXECUTION — celui de l'API."""
    _exiger_postgresql(parametres_de_la_stack)
    connexion = moteur(parametres_de_la_stack).connect()
    transaction = connexion.begin()
    try:
        yield connexion
    finally:
        transaction.rollback()
        connexion.close()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO person "
                    "(email, email_normalized, first_name, last_name, account_state) "
                    "VALUES (:a, :a, 'Session', 'T6', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


def _ouvrir(cx: Connection, adresse: str, *, instant: dt.datetime = INSTANT) -> str:
    jeton, _ = ouvrir_une_session(
        cx,
        personne=_personne(cx, adresse),
        instant=instant,
        jours_absolus=JOURS_MAXIMUM_DE_SESSION,
    )
    return jeton


def _lire(cx: Connection, jeton: str | None, *, instant: dt.datetime = INSTANT) -> Session:
    return lire_et_rafraichir(
        cx, jeton=jeton, instant=instant, jours_d_inactivite=JOURS_D_INACTIVITE_DE_SESSION
    )


@pytest.mark.integration
def test_une_session_FRAICHE_est_valide(cx: Connection) -> None:
    """LE TEMOIN CENTRAL : sans lui, tous les refus seraient satisfaits par une
    fonction qui refuserait tout.
    """
    etat = _lire(cx, _ouvrir(cx, "fraiche@exalt-t6.test"))
    assert etat.motif == MOTIF_SESSION_VALIDE
    assert etat.valide
    assert etat.personne is not None


@pytest.mark.integration
def test_un_cookie_ABSENT_n_est_pas_une_erreur(cx: Connection) -> None:
    """Un visiteur non connecte n'est pas un incident : il n'a simplement pas de
    session. Le motif le distingue en interne, la reponse HTTP non.
    """
    assert _lire(cx, None).motif == MOTIF_SESSION_ABSENTE
    assert _lire(cx, "").motif == MOTIF_SESSION_ABSENTE


@pytest.mark.integration
def test_un_jeton_INCONNU_est_refuse(cx: Connection) -> None:
    assert _lire(cx, engendrer_un_jeton_de_session()).motif == MOTIF_SESSION_REFUSEE


@pytest.mark.integration
def test_un_jeton_FANTAISISTE_est_refuse_sans_lever(cx: Connection) -> None:
    """Le porteur controle entierement cette valeur."""
    for fantaisiste in ("pas-un-jeton", "oss_", "'; DROP TABLE person; --", "x" * 500):
        assert _lire(cx, fantaisiste).motif == MOTIF_SESSION_REFUSEE


# --- Les deux expirations, bornees des DEUX cotes --------------------------


@pytest.mark.integration
def test_l_inactivite_de_HUIT_jours_expire_la_session(cx: Connection) -> None:
    """§10.4 : « Expiration inactive apres 7 jours »."""
    jeton = _ouvrir(cx, "inactive@exalt-t6.test")
    tard = INSTANT + dt.timedelta(days=JOURS_D_INACTIVITE_DE_SESSION + 1)
    assert _lire(cx, jeton, instant=tard).motif == MOTIF_SESSION_REFUSEE


@pytest.mark.integration
def test_une_inactivite_de_SIX_jours_reste_valide(cx: Connection) -> None:
    """Le temoin de la borne : elle ne doit pas etre plus stricte que le modele.

    Sans lui, une expiration a cinq minutes passerait le test precedent — et le
    livrable serait plus severe que le §10.4, defaut du §7.20.
    """
    jeton = _ouvrir(cx, "active6j@exalt-t6.test")
    tot = INSTANT + dt.timedelta(days=JOURS_D_INACTIVITE_DE_SESSION - 1)
    assert _lire(cx, jeton, instant=tot).valide


@pytest.mark.integration
def test_l_activite_REPOUSSE_l_inactivite(cx: Connection) -> None:
    """**C'EST LE POINT DE L'INACTIVITE, ET NON DE LA DUREE.**

    Une lecture au sixieme jour repousse la borne : la session vit encore au
    onzieme. Sans ce test, une implementation qui bornerait sur `created_at`
    passerait les deux precedents — elle expirerait au septieme jour quoi qu'il
    arrive, et ce serait une duree absolue de sept jours, non une inactivite.
    """
    jeton = _ouvrir(cx, "repousse@exalt-t6.test")
    assert _lire(cx, jeton, instant=INSTANT + dt.timedelta(days=6)).valide
    assert _lire(cx, jeton, instant=INSTANT + dt.timedelta(days=11)).valide
    #  Et huit jours APRES la derniere activite, elle expire.
    assert _lire(cx, jeton, instant=INSTANT + dt.timedelta(days=19)).motif == (
        MOTIF_SESSION_REFUSEE
    )


@pytest.mark.integration
def test_la_duree_ABSOLUE_l_emporte_sur_l_activite(cx: Connection) -> None:
    """§10.4 : « absolute_expires_at | Maximum 30 jours ».

    **C'EST LE TEST QUI DISTINGUE LES DEUX EXPIRATIONS.** Une session gardee
    active par des lectures regulieres doit MOURIR au trentieme jour. Sans lui,
    une implementation qui n'aurait que l'inactivite vivrait indefiniment.
    """
    jeton = _ouvrir(cx, "absolue@exalt-t6.test")
    #  Une lecture tous les cinq jours : l'inactivite ne se declenche jamais.
    for jour in range(5, JOURS_MAXIMUM_DE_SESSION, 5):
        assert _lire(cx, jeton, instant=INSTANT + dt.timedelta(days=jour)).valide, jour
    #  Au trente-et-unieme, la duree absolue l'emporte.
    assert (
        _lire(cx, jeton, instant=INSTANT + dt.timedelta(days=JOURS_MAXIMUM_DE_SESSION + 1)).motif
        == MOTIF_SESSION_REFUSEE
    )


@pytest.mark.integration
def test_la_base_REFUSE_une_session_de_plus_de_trente_jours(cx: Connection) -> None:
    """La contrainte `duree_absolue_bornee` de la migration `0012`.

    Le service ne peut donc pas la contourner : l'invariant est en base, et le
    garde-fou de demarrage refuse une variable divergente. Trois barrieres pour
    la meme regle, et c'est voulu.
    """
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError, match="duree_absolue_bornee"), cx.begin_nested():
        ouvrir_une_session(
            cx,
            personne=_personne(cx, "trop-longue@exalt-t6.test"),
            instant=INSTANT,
            jours_absolus=JOURS_MAXIMUM_DE_SESSION + 1,
        )


# --- La revocation ---------------------------------------------------------


@pytest.mark.integration
def test_la_revocation_INVALIDE_la_session(cx: Connection) -> None:
    jeton = _ouvrir(cx, "revoquee@exalt-t6.test")
    assert revoquer(cx, jeton=jeton, instant=INSTANT)
    assert _lire(cx, jeton).motif == MOTIF_SESSION_REFUSEE


@pytest.mark.integration
def test_la_revocation_N_EFFACE_PAS_la_ligne(cx: Connection) -> None:
    """§10.4 : `revoked_at` et `revoke_reason` existent pour etre RENSEIGNES.

    Supprimer la ligne perdrait quand et pourquoi — et `T9` devra distinguer une
    deconnexion volontaire d'une revocation au depart.
    """
    jeton = _ouvrir(cx, "trace@exalt-t6.test")
    revoquer(cx, jeton=jeton, instant=INSTANT)
    ligne = cx.execute(
        text(
            "SELECT revoked_at IS NOT NULL, revoke_reason FROM user_session "
            "WHERE session_token_hash = :e"
        ),
        {"e": empreinte_de_session(jeton)},
    ).one()
    assert ligne[0] is True
    assert ligne[1] == REVOCATION_DECONNEXION


@pytest.mark.integration
def test_la_revocation_est_IDEMPOTENTE(cx: Connection) -> None:
    """**UNE SECONDE DECONNEXION NE DOIT PAS FABRIQUER UN SECOND EVENEMENT.**

    Une trace d'audit qui compterait deux revocations pour une seule session
    serait fausse, et `T12` devra compter ces evenements.
    """
    jeton = _ouvrir(cx, "idempotente@exalt-t6.test")
    assert revoquer(cx, jeton=jeton, instant=INSTANT) is True
    assert revoquer(cx, jeton=jeton, instant=INSTANT + dt.timedelta(minutes=1)) is False
    evenements = cx.execute(
        text("SELECT count(*) FROM auth_event WHERE event_type = :t AND occurred_at >= :d"),
        {"t": TypeEvenementAuth.SESSION_REVOKED.value, "d": INSTANT},
    ).scalar_one()
    assert evenements == 1


@pytest.mark.integration
def test_revoquer_un_jeton_INCONNU_ne_trace_RIEN(cx: Connection) -> None:
    """Sans cela, un attaquant pourrait remplir l'audit en postant des jetons
    inventes sur la deconnexion.
    """
    avant = cx.execute(
        text("SELECT count(*) FROM auth_event WHERE event_type = :t"),
        {"t": TypeEvenementAuth.SESSION_REVOKED.value},
    ).scalar_one()
    assert revoquer(cx, jeton=engendrer_un_jeton_de_session(), instant=INSTANT) is False
    assert revoquer(cx, jeton=None, instant=INSTANT) is False
    apres = cx.execute(
        text("SELECT count(*) FROM auth_event WHERE event_type = :t"),
        {"t": TypeEvenementAuth.SESSION_REVOKED.value},
    ).scalar_one()
    assert apres == avant


@pytest.mark.integration
def test_la_revocation_est_TRACEE_SESSION_REVOKED(cx: Connection) -> None:
    """§10.6 : « session revoquee » est l'un des sept types."""
    jeton = _ouvrir(cx, "audit-revoc@exalt-t6.test")
    revoquer(cx, jeton=jeton, instant=INSTANT)
    lignes = (
        cx.execute(
            text("SELECT e::text FROM auth_event e WHERE e.event_type = :t"),
            {"t": TypeEvenementAuth.SESSION_REVOKED.value},
        )
        .scalars()
        .all()
    )
    assert lignes, "aucun evenement : ce test ne prouverait rien"
    #  Et NI le jeton NI son empreinte n'y figurent — §10.3 et §28.2.
    for ligne in lignes:
        assert jeton not in ligne
        assert empreinte_de_session(jeton) not in ligne
        assert PREFIXE_SESSION not in ligne


# --- L'ATOMICITE du rafraichissement --------------------------------------


@pytest.mark.integration
def test_le_rafraichissement_est_ATOMIQUE_sous_CONCURRENCE(
    parametres_de_la_stack: Parametres,
) -> None:
    """**UNE SESSION EXPIREE NE DOIT PAS ETRE RAVIVEE PAR UNE REQUETE CONCURRENTE.**

    Lire `last_activity_at`, decider, puis ecrire laisserait deux requetes juger
    valide une session que l'une des deux vient de laisser expirer : la seconde
    lirait l'ancienne valeur, conclurait « valide », et **ecrirait un
    `last_activity_at` frais sur une session morte**.

    Le scenario est celui de `T4` et `T5`, pour la troisieme fois : `A` rafraichit
    sans valider, `B` attend le verrou de ligne, `A` valide, `B` reprend. La
    barriere interroge `pg_blocking_pids()` — une condition observee, pas un delai
    espere.

    **Ce qui discrimine** : apres le commit de `A`, la clause `WHERE` de `B` est
    reevaluee. Comme `A` a REVOQUE la session, `B` ne trouve plus de ligne
    eligible et refuse. Un lire-puis-ecrire aurait deja conclu « valide ».
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t6race{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@exalt-t6.test"

    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as preparation:
        jeton = _ouvrir(preparation, adresse)

    resultats: dict[str, object] = {}
    erreurs: list[BaseException] = []

    def lire_dans_un_fil() -> None:
        connexion = moteur(parametres_de_la_stack).connect()
        try:
            with connexion.begin():
                connexion.execute(text(f"SET LOCAL lock_timeout = '{VERROU_TIMEOUT_CONCURRENT}'"))
                resultats["b"] = lire_et_rafraichir(
                    connexion,
                    jeton=jeton,
                    instant=INSTANT,
                    jours_d_inactivite=JOURS_D_INACTIVITE_DE_SESSION,
                )
        except BaseException as erreur:
            erreurs.append(erreur)
        finally:
            connexion.close()

    premiere = moteur(parametres_de_la_stack).connect()
    try:
        transaction_a = premiere.begin()
        #  `A` REVOQUE la session, et ne valide pas : elle tient le verrou.
        assert revoquer(premiere, jeton=jeton, instant=INSTANT) is True

        fil = threading.Thread(target=lire_dans_un_fil, daemon=True)
        fil.start()

        limite = time.monotonic() + DELAI_ATTENTE_VERROU
        en_attente = False
        observe: list[tuple[object, ...]] = []
        with moteur(parametres_de_la_stack).connect() as sonde:
            while time.monotonic() < limite:
                observe = [
                    tuple(ligne)
                    for ligne in sonde.execute(
                        text(
                            "SELECT pid, pg_blocking_pids(pid), left(query, 50) "
                            "FROM pg_stat_activity "
                            "WHERE datname = current_database() "
                            "  AND pid <> pg_backend_pid() AND query <> ''"
                        )
                    )
                ]
                en_attente = any(ligne[1] for ligne in observe)
                if en_attente or erreurs:
                    break
                time.sleep(0.05)
        assert not erreurs, f"B a echoue avant d'attendre : {erreurs}"
        assert en_attente, f"B n'a pas ete bloquee ; etat observe : {observe}"

        transaction_a.commit()
        fil.join(timeout=DELAI_ATTENTE_VERROU)
        assert not fil.is_alive(), "B ne s'est jamais debloquee"
        assert not erreurs, f"B a leve : {erreurs}"

        etat = resultats["b"]
        assert getattr(etat, "motif", None) == MOTIF_SESSION_REFUSEE, (
            "B a RAVIVE une session revoquee : la condition n'est pas reevaluee "
            "apres l'obtention du verrou"
        )
    finally:
        premiere.close()
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


# ===========================================================================
#  Les routes et le COOKIE
# ===========================================================================


@pytest.fixture
def stack_avec_admin(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str]]:
    """Un compte administrateur PERSISTANT : les routes valident leur transaction.

    Rend `(parametres, adresse, mot de passe)`. Le mot de passe est fixe et sans
    portee : aucun compte reel ne l'emploie.
    """
    _exiger_postgresql(parametres_de_la_stack)
    from app.auth.mots_de_passe import ALGORITHME, hacher

    marqueur = f"t6api{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@exalt-t6.test"
    mot_de_passe = "un-mot-de-passe-de-test-sans-portee"
    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as connexion:
        personne = _personne(connexion, adresse)
        compte = connexion.execute(
            text(
                "INSERT INTO user_account "
                "(person_id, account_type, state, failed_login_count) "
                "VALUES (:p, 'ADMIN_LOCAL', 'active', 0) RETURNING id"
            ),
            {"p": personne},
        ).scalar_one()
        empreinte, parametres_hachage = hacher(mot_de_passe)
        import json as _json

        connexion.execute(
            text(
                "INSERT INTO admin_password_credential "
                "(user_account_id, password_hash, algorithm, parameters, changed_at, "
                " must_change) VALUES (:c, :h, :a, :params, :quand, FALSE)"
            ),
            {
                "c": compte,
                "h": empreinte,
                "a": ALGORITHME,
                "params": _json.dumps(parametres_hachage),
                "quand": INSTANT,
            },
        )
    try:
        yield parametres_de_la_stack, adresse, mot_de_passe
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM admin_password_credential WHERE user_account_id IN "
                "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM user_account WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


@pytest.mark.integration
def test_la_connexion_pose_un_cookie_avec_les_TROIS_attributs(
    stack_avec_admin: tuple[Parametres, str, str],
) -> None:
    """**LE CRITERE LITTERAL DU §7.4** : `HttpOnly`, `Secure`, `SameSite`.

    Les trois sont exiges sur l'en-tete `Set-Cookie` REEL, non sur l'intention du
    code. Et le nom du cookie est celui que `.env.example` declare depuis le
    LOT 0 : `exalt_session`.
    """
    parametres, adresse, mot_de_passe = stack_avec_admin
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        reponse = client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
        )
    assert reponse.status_code == 200
    pose = reponse.headers.get("set-cookie", "")
    assert parametres.SESSION_COOKIE_NAME in pose, pose
    assert "HttpOnly" in pose, pose
    assert "Secure" in pose, pose
    assert "SameSite=lax" in pose.replace("samesite", "SameSite"), pose
    assert "Path=/" in pose, pose


@pytest.mark.integration
def test_le_JETON_n_apparait_dans_AUCUN_corps_de_reponse(
    stack_avec_admin: tuple[Parametres, str, str],
) -> None:
    """**C'EST CE QUI REND LE CRITERE « AUCUN JETON DANS `localStorage` » TENABLE.**

    Un frontend qui recoit un jeton finit par le stocker. Ne jamais le lui donner
    rend la regle structurelle plutot que disciplinaire — §7.2.
    """
    parametres, adresse, mot_de_passe = stack_avec_admin
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        connexion = client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        jeton = client.cookies.get(parametres.SESSION_COOKIE_NAME)
        session = client.get("/api/v1/auth/session")
    assert jeton, "aucun cookie pose : ce test ne prouverait rien"
    assert jeton not in connexion.text
    assert jeton not in session.text
    assert PREFIXE_SESSION not in connexion.text
    assert PREFIXE_SESSION not in session.text


@pytest.mark.integration
def test_le_cookie_ouvre_l_acces_a_la_session(
    stack_avec_admin: tuple[Parametres, str, str],
) -> None:
    """Le temoin de bout en bout : le cookie fait un aller-retour REEL."""
    parametres, adresse, mot_de_passe = stack_avec_admin
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        connexion = client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["personne"] == connexion.json()["personne"]


@pytest.mark.integration
def test_SANS_cookie_la_session_est_refusee(
    stack_avec_admin: tuple[Parametres, str, str],
) -> None:
    parametres, _, _ = stack_avec_admin
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        assert client.get("/api/v1/auth/session").status_code == 401


@pytest.mark.integration
def test_la_deconnexion_INVALIDE_le_cookie_et_le_retire(
    stack_avec_admin: tuple[Parametres, str, str],
) -> None:
    """Deux effets, et il faut les deux : la session est revoquee cote serveur, et
    le cookie est retire cote navigateur.

    **Le serveur est l'autorite** — c'est pourquoi le test rejoue la session avec
    le jeton d'origine apres la deconnexion, et exige un refus.
    """
    parametres, adresse, mot_de_passe = stack_avec_admin
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
        )
        jeton = client.cookies.get(parametres.SESSION_COOKIE_NAME)
        assert client.get("/api/v1/auth/session").status_code == 200

        sortie = client.post("/api/v1/auth/deconnexion")
        assert sortie.status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 401

    #  Le jeton d'origine, rejoue sur un client NEUF : le serveur doit refuser,
    #  meme si le navigateur avait garde le cookie.
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as autre:
        autre.cookies.set(parametres.SESSION_COOKIE_NAME, jeton or "")
        assert autre.get("/api/v1/auth/session").status_code == 401


@pytest.mark.integration
def test_la_deconnexion_rend_TOUJOURS_200(
    stack_avec_admin: tuple[Parametres, str, str],
) -> None:
    """Sans session, avec un jeton inconnu, deux fois de suite : toujours 200.

    Un 401 apprendrait qu'un jeton a existe, et une deconnexion n'a de toute
    facon rien a refuser.
    """
    parametres, _, _ = stack_avec_admin
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        assert client.post("/api/v1/auth/deconnexion").status_code == 200
        client.cookies.set(parametres.SESSION_COOKIE_NAME, engendrer_un_jeton_de_session())
        assert client.post("/api/v1/auth/deconnexion").status_code == 200
        assert client.post("/api/v1/auth/deconnexion").status_code == 200
