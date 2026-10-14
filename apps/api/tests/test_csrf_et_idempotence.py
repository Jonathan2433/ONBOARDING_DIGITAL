"""CSRF et idempotence — story `MVP-L03-US005`, cahier §7.4, §18.6, §20.1.

LOT 3, sous-etape `T7`.

DEUX BARRIERES CSRF, ET LEUR PORTEE DIFFERE — C'EST CE QUI STRUCTURE CE FICHIER

  Trois ecritures PRECEDENT toute session : demander un lien, le consommer, se
  connecter. Un jeton anti-CSRF suppose une session pour le delivrer, donc elles
  n'en exigent pas -- seule l'origine y est controlee.

  Une seule ecriture dispose d'une session : la deconnexion. Elle exige les deux.

  **Chaque barriere a son test ET son temoin** : le refus, et le cas legitime qui
  doit passer. Sans le temoin, une protection qui refuserait TOUT passerait les
  tests de refus.

L'IDEMPOTENCE COUVRE LA DOUBLE SOUMISSION, PAS LE REJEU DURABLE

  Et c'est dit dans le module comme ici. La garantie est adossee a Redis, donc
  non durable : elle couvre le double clic, pas un rejeu a plusieurs jours.
  L'idempotence durable des six operations du cahier §18.6 restera portee par
  `async_job.idempotency_key` au **LOT 11** -- c'est la que le modele la declare.
"""

from __future__ import annotations

import datetime as dt
import json as _json
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.csrf import (
    EN_TETE_JETON,
    MOTIF_JETON_ABSENT,
    MOTIF_JETON_INVALIDE,
    MOTIF_ORIGINE_ETRANGERE,
    CsrfRefuse,
    controler_l_origine,
    controler_le_jeton,
    jeton_pour,
    origine_attendue,
)
from app.auth.idempotence import (
    EN_TETE_CLE,
    CleInvalide,
    controler_la_cle,
    liberer,
    reserver,
)
from app.auth.sessions import empreinte_de_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 8, 21, 10, 30, tzinfo=dt.UTC)
MOT_DE_PASSE = "un-mot-de-passe-de-test-sans-portee"

#  Le client de test parle HTTPS : un cookie `Secure` n'est jamais renvoye sur
#  une origine non chiffree. Lecon `T6-1`.
ORIGINE_DE_TEST = "https://testserver"


# ===========================================================================
#  L'origine — aucune dependance
# ===========================================================================


def test_l_origine_attendue_est_reduite_au_schema_et_a_l_hote() -> None:
    """`PUBLIC_BASE_URL` peut porter un chemin ou une barre finale ; un navigateur
    n'envoie jamais qu'une origine. Les comparer telles quelles echouerait sur un
    detail de configuration.
    """
    assert origine_attendue("https://app.onboarding.localhost/") == (
        "https://app.onboarding.localhost"
    )
    assert origine_attendue("https://app.recette.onboarding.localhost:8443") == (
        "https://app.recette.onboarding.localhost:8443"
    )
    assert origine_attendue("https://app.onboarding.localhost/un/chemin") == (
        "https://app.onboarding.localhost"
    )
    #  Une valeur inexploitable rend une chaine vide, et `controler_l_origine`
    #  s'abstient alors — plutot que de refuser tout sur une configuration
    #  incomplete sans dire pourquoi.
    assert origine_attendue("pas-une-url") == ""


def test_une_origine_ETRANGERE_est_refusee() -> None:
    attendue = origine_attendue("https://app.onboarding.localhost")
    for etrangere in (
        "https://mechant.example",
        "http://app.onboarding.localhost",
        "https://app.onboarding.localhost:8443",
        "https://evil.app.onboarding.localhost",
    ):
        with pytest.raises(CsrfRefuse) as refus:
            controler_l_origine(origine=etrangere, attendue=attendue)
        assert refus.value.motif == MOTIF_ORIGINE_ETRANGERE, etrangere


def test_la_BONNE_origine_est_acceptee() -> None:
    """Le temoin : sans lui, une protection qui refuserait tout passerait le test
    precedent. La barre finale est toleree — un navigateur ne l'envoie pas, mais
    un client peut.
    """
    attendue = origine_attendue("https://app.onboarding.localhost")
    controler_l_origine(origine="https://app.onboarding.localhost", attendue=attendue)
    controler_l_origine(origine="https://app.onboarding.localhost/", attendue=attendue)


def test_une_origine_ABSENTE_n_est_PAS_refusee() -> None:
    """**C'EST UN CHOIX DECLARE, PAS UN TROU.**

    Un navigateur pose `Origin` sur toute requete non sûre ; son absence signale
    un appel hors navigateur. La refuser casserait `curl`, les sondes et les
    contrôles d'exploitation — et n'apporterait rien : le CSRF est une attaque de
    navigateur, et un appelant sans navigateur n'usurpe l'identite de personne.
    """
    attendue = origine_attendue("https://app.onboarding.localhost")
    controler_l_origine(origine=None, attendue=attendue)
    controler_l_origine(origine="", attendue=attendue)


def test_sans_origine_attendue_le_controle_s_ABSTIENT() -> None:
    """Sur une configuration incomplete, refuser tout rendrait l'API inutilisable
    sans dire pourquoi. Le garde-fou de `PUBLIC_BASE_URL` est ailleurs, et c'est
    lui qui doit parler.
    """
    controler_l_origine(origine="https://n-importe-quoi.example", attendue="")


# ===========================================================================
#  Le jeton — derive, jamais stocke
# ===========================================================================


def test_le_jeton_EXIGE_une_cle() -> None:
    """Sans cle, le jeton serait calculable par quiconque."""
    with pytest.raises(ValueError, match="cle non vide"):
        jeton_pour("a" * 64, "")


def test_le_jeton_est_LIE_a_la_session() -> None:
    """**C'EST CE QUI REND LE DOUBLE ENVOI SOLIDE.** Un jeton d'une autre session
    ne correspond pas : le voler sans le cookie ne sert a rien.
    """
    cle = "cle-de-test-sans-portee"
    jeton = jeton_pour("a" * 64, cle)
    controler_le_jeton(presente=jeton, empreinte_de_session="a" * 64, cle=cle)
    with pytest.raises(CsrfRefuse) as refus:
        controler_le_jeton(presente=jeton, empreinte_de_session="b" * 64, cle=cle)
    assert refus.value.motif == MOTIF_JETON_INVALIDE


def test_le_jeton_depend_de_la_CLE() -> None:
    """Une rotation d'`APP_SECRET_KEY` invalide les jetons en cours — acceptable :
    ils sont recalcules a chaque lecture de session, sans etat a migrer.
    """
    assert jeton_pour("a" * 64, "cle-un") != jeton_pour("a" * 64, "cle-deux")


@pytest.mark.parametrize("absent", [None, ""])
def test_un_jeton_ABSENT_est_refuse(absent: str | None) -> None:
    with pytest.raises(CsrfRefuse) as refus:
        controler_le_jeton(presente=absent, empreinte_de_session="a" * 64, cle="cle")
    assert refus.value.motif == MOTIF_JETON_ABSENT


def test_un_jeton_FANTAISISTE_est_refuse_sans_lever_autre_chose() -> None:
    """Le porteur controle entierement cette valeur."""
    for fantaisiste in ("x" * 64, "pas-un-jeton", "0", "z" * 500):
        with pytest.raises(CsrfRefuse) as refus:
            controler_le_jeton(presente=fantaisiste, empreinte_de_session="a" * 64, cle="cle")
        assert refus.value.motif == MOTIF_JETON_INVALIDE


# ===========================================================================
#  Les cles d'idempotence — Redis REEL
# ===========================================================================


@pytest.mark.parametrize(
    "mauvaise",
    ["", "court", "a" * 201, "avec espace", "avec/slash", "avec#diese", "é" * 20],
)
def test_une_cle_MALFORMEE_est_refusee(mauvaise: str) -> None:
    """**UNE CLE N'EST PAS NETTOYEE, ELLE EST REFUSEE.** Nettoyer ferait que deux
    cles differentes deviendraient la meme — et deux operations distinctes se
    bloqueraient l'une l'autre.
    """
    with pytest.raises(CleInvalide):
        controler_la_cle(mauvaise)


def test_les_formes_ACCEPTABLES_le_sont() -> None:
    """Le temoin : sans lui, une validation qui refuserait tout passerait le test
    precedent.
    """
    for bonne in ("abcdefgh", "a" * 200, "cle.avec_des:tirets-et.points", uuid.uuid4().hex):
        controler_la_cle(bonne)


def _exiger_redis(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.REDIS_PORT):
        pytest.skip(
            "Redis absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.mark.integration
def test_une_MEME_cle_ne_se_reserve_QU_UNE_fois(parametres_de_la_stack: Parametres) -> None:
    """**LE CRITERE LITTERAL DE `US005`** : une meme cle rejouee ne produit qu'un
    effet.
    """
    _exiger_redis(parametres_de_la_stack)
    cle = f"t7-{uuid.uuid4().hex}"
    try:
        assert reserver(parametres_de_la_stack, route="essai", cle=cle) is True
        assert reserver(parametres_de_la_stack, route="essai", cle=cle) is False
        assert reserver(parametres_de_la_stack, route="essai", cle=cle) is False
    finally:
        liberer(parametres_de_la_stack, route="essai", cle=cle)


@pytest.mark.integration
def test_la_cle_est_CLOISONNEE_par_route(parametres_de_la_stack: Parametres) -> None:
    """§20.1 : « unique dans son **perimetre** ».

    Sans cloisonnement, une demande de lien bloquerait une deconnexion portant la
    meme cle — deux operations differentes se refuseraient l'une l'autre.
    """
    _exiger_redis(parametres_de_la_stack)
    cle = f"t7-{uuid.uuid4().hex}"
    try:
        assert reserver(parametres_de_la_stack, route="route-a", cle=cle) is True
        assert reserver(parametres_de_la_stack, route="route-b", cle=cle) is True
    finally:
        liberer(parametres_de_la_stack, route="route-a", cle=cle)
        liberer(parametres_de_la_stack, route="route-b", cle=cle)


@pytest.mark.integration
def test_LIBERER_permet_de_recommencer(parametres_de_la_stack: Parametres) -> None:
    """**C'EST CE QUI REND LE MECANISME UTILISABLE.** Une cle reservee sur une
    operation qui a echoue resterait sinon posee six heures, et un client qui
    recommence — ce qu'on attend de lui apres une erreur — serait refuse sans rien
    avoir obtenu.
    """
    _exiger_redis(parametres_de_la_stack)
    cle = f"t7-{uuid.uuid4().hex}"
    try:
        assert reserver(parametres_de_la_stack, route="essai", cle=cle) is True
        liberer(parametres_de_la_stack, route="essai", cle=cle)
        assert reserver(parametres_de_la_stack, route="essai", cle=cle) is True
    finally:
        liberer(parametres_de_la_stack, route="essai", cle=cle)


@pytest.mark.integration
def test_liberer_une_cle_INEXISTANTE_ne_leve_pas(parametres_de_la_stack: Parametres) -> None:
    """Elle est appelee dans un chemin d'erreur : y lever masquerait la cause."""
    _exiger_redis(parametres_de_la_stack)
    liberer(parametres_de_la_stack, route="essai", cle=f"jamais-{uuid.uuid4().hex}")


# ===========================================================================
#  Les routes — protections REELLES
# ===========================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`.")


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO person "
                    "(email, email_normalized, first_name, last_name, account_state) "
                    "VALUES (:a, :a, 'Csrf', 'T7', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


@pytest.fixture
def stack(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str]]:
    """Un compte administrateur PERSISTANT, et l'origine du client de test.

    `PUBLIC_BASE_URL` est forcee a l'origine du `TestClient` : sans cela, toutes
    les ecritures seraient refusees pour origine etrangere, et les tests ne
    prouveraient rien de la protection — ils prouveraient qu'elle refuse tout.
    """
    _exiger_postgresql(parametres_de_la_stack)
    from app.auth.mots_de_passe import ALGORITHME, hacher

    marqueur = f"t7api{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@exalt-t7.test"
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
        empreinte, parametres_hachage = hacher(MOT_DE_PASSE)
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
    parametres = parametres_de_la_stack.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    try:
        yield parametres, adresse, MOT_DE_PASSE
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                #  LOT 10, `T2` : `audit_event.actor_person_id` reference aussi
                #  `person`, meme motif que la ligne `auth_event` au-dessus.
                "DELETE FROM audit_event WHERE actor_person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM magic_link_request WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM admin_password_credential WHERE user_account_id IN "
                "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM user_account WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                #  `entity_membership` ET `entity` : les deux tests d'idempotence
                #  en creent, parce qu'un lien n'est emis qu'a un profil ACTIF
                #  dans un domaine autorise. Les omettre laissait la cle
                #  etrangere bloquer la suppression de la personne — et c'est la
                #  meme classe de defaut que `T6` a rencontree cinq fois, cette
                #  fois dans une fixture NEUVE. Ecrire un nettoyage complet est
                #  plus difficile qu'il n'y parait.
                "DELETE FROM entity_membership WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM entity WHERE code LIKE 'T7-%' OR code LIKE 'T7b-%'",
                "DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= :debut",
                "DELETE FROM audit_event WHERE actor_person_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _client(parametres: Parametres) -> TestClient:
    return TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST)


@pytest.mark.integration
def test_une_ECRITURE_depuis_une_origine_ETRANGERE_est_refusee(
    stack: tuple[Parametres, str, str],
) -> None:
    """**LE CRITERE : une ecriture sans protection est REFUSEE.**

    Les cinq ecritures du lot sont enumerees : sans l'enumeration, ce test
    pourrait n'en avoir exerce qu'une.
    """
    parametres, adresse, mot_de_passe = stack
    ecritures = {
        "/api/v1/auth/magic-link": {"email": adresse},
        "/api/v1/auth/magic-link/consommation": {"token": "oml_" + "z" * 43},
        "/api/v1/auth/connexion": {"email": adresse, "mot_de_passe": mot_de_passe},
        "/api/v1/auth/mot-de-passe": {
            "email": adresse,
            "mot_de_passe_actuel": mot_de_passe,
            "nouveau_mot_de_passe": "un-nouveau-mot-de-passe-valide",
        },
        "/api/v1/auth/deconnexion": {},
    }
    assert len(ecritures) == 5, "les cinq ecritures du lot doivent etre exercees"
    with _client(parametres) as client:
        for chemin, corps in ecritures.items():
            reponse = client.post(chemin, json=corps, headers={"Origin": "https://mechant.example"})
            assert reponse.status_code == 403, f"{chemin} rend {reponse.status_code}"
            assert reponse.json()["erreur"]["code"] == "requete_refusee"


@pytest.mark.integration
def test_TEMOIN_les_memes_ecritures_passent_depuis_la_BONNE_origine(
    stack: tuple[Parametres, str, str],
) -> None:
    """**SANS CE TEMOIN, UNE PROTECTION QUI REFUSERAIT TOUT PASSERAIT LE TEST
    PRECEDENT.**

    Chaque route est exercee avec la bonne origine, et le seul verdict exige est
    « pas 403 » : leur code de succes ou de refus metier differe, et ce n'est pas
    ce que ce test mesure.

    **LA DECONNEXION EST EXCLUE DE CETTE LISTE, ET MA PREMIERE VERSION L'Y
    INCLUAIT.** Elle a echoue avec `assert 403 != 403`, et **elle avait raison** :
    le test venait de se connecter, donc une session existait, donc le jeton etait
    exige. La bonne origine ne suffit pas pour elle -- c'est tout l'objet de la
    seconde barriere. Son temoin est
    `test_la_DECONNEXION_exige_un_jeton_quand_une_session_existe`, qui fournit le
    jeton. Defaut `T7-2`.
    """
    parametres, adresse, mot_de_passe = stack
    with _client(parametres) as client:
        for chemin, corps in (
            ("/api/v1/auth/magic-link", {"email": adresse}),
            ("/api/v1/auth/connexion", {"email": adresse, "mot_de_passe": mot_de_passe}),
            (
                "/api/v1/auth/mot-de-passe",
                {
                    "email": adresse,
                    "mot_de_passe_actuel": mot_de_passe,
                    "nouveau_mot_de_passe": "un-nouveau-mot-de-passe-valide",
                },
            ),
        ):
            reponse = client.post(chemin, json=corps, headers={"Origin": ORIGINE_DE_TEST})
            assert reponse.status_code != 403, f"{chemin} refuse a tort"


@pytest.mark.integration
def test_une_ecriture_SANS_en_tete_Origin_passe(
    stack: tuple[Parametres, str, str],
) -> None:
    """Choix declare : un appel hors navigateur n'a pas d'`Origin`.

    Le refuser casserait `curl`, les sondes et `make api-check` — et n'apporterait
    rien, le CSRF etant une attaque de navigateur.
    """
    parametres, adresse, _ = stack
    with _client(parametres) as client:
        reponse = client.post("/api/v1/auth/magic-link", json={"email": adresse})
    assert reponse.status_code == 202


@pytest.mark.integration
def test_la_DECONNEXION_exige_un_jeton_quand_une_session_existe(
    stack: tuple[Parametres, str, str],
) -> None:
    """**LA SEULE ECRITURE DU LOT QUI EXIGE UN JETON**, parce qu'elle est la seule
    a disposer d'une session pour en deriver un.

    Un site tiers qui deconnecte un utilisateur est une nuisance reelle, et
    `SameSite=lax` ne la bloque pas toujours.
    """
    parametres, adresse, mot_de_passe = stack
    with _client(parametres) as client:
        client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
            headers={"Origin": ORIGINE_DE_TEST},
        )
        #  Sans jeton, avec une session : REFUSE.
        sans = client.post("/api/v1/auth/deconnexion", headers={"Origin": ORIGINE_DE_TEST})
        assert sans.status_code == 403
        #  La session est toujours valide : le refus n'a rien deconnecte.
        assert client.get("/api/v1/auth/session").status_code == 200

        #  Avec le jeton obtenu de la route de session : ACCEPTE.
        jeton = client.get("/api/v1/auth/session").json()["jeton_csrf"]
        avec = client.post(
            "/api/v1/auth/deconnexion",
            headers={"Origin": ORIGINE_DE_TEST, EN_TETE_JETON: jeton},
        )
        assert avec.status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 401


@pytest.mark.integration
def test_un_jeton_d_une_AUTRE_session_est_refuse(
    stack: tuple[Parametres, str, str],
) -> None:
    """C'est la liaison a la session qui rend le double envoi solide : un jeton
    vole sur une autre session ne correspond pas.
    """
    parametres, adresse, mot_de_passe = stack
    with _client(parametres) as client:
        client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
            headers={"Origin": ORIGINE_DE_TEST},
        )
        #  Un jeton calcule sur une empreinte de session qui n'est pas la sienne.
        etranger = jeton_pour(empreinte_de_session("oss_" + "z" * 43), parametres.APP_SECRET_KEY)
        reponse = client.post(
            "/api/v1/auth/deconnexion",
            headers={"Origin": ORIGINE_DE_TEST, EN_TETE_JETON: etranger},
        )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_la_deconnexion_SANS_cookie_n_exige_AUCUN_jeton(
    stack: tuple[Parametres, str, str],
) -> None:
    """Il n'y aurait rien a proteger, et exiger un jeton ferait echouer une
    deconnexion qui doit rendre 200 en toute circonstance.
    """
    parametres, _, _ = stack
    with _client(parametres) as client:
        reponse = client.post("/api/v1/auth/deconnexion", headers={"Origin": ORIGINE_DE_TEST})
    assert reponse.status_code == 200


@pytest.mark.integration
def test_les_TROIS_causes_de_refus_CSRF_sont_indistinguables(
    stack: tuple[Parametres, str, str],
) -> None:
    """Distinguer « jeton absent » de « jeton invalide » dirait a un attaquant
    s'il s'est approche. Le motif interne va au journal, pas a la reponse.
    """
    parametres, adresse, mot_de_passe = stack
    with _client(parametres) as client:
        client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
            headers={"Origin": ORIGINE_DE_TEST},
        )
        refus = {
            "origine_etrangere": client.post(
                "/api/v1/auth/deconnexion",
                headers={"Origin": "https://mechant.example"},
            ),
            "jeton_absent": client.post(
                "/api/v1/auth/deconnexion", headers={"Origin": ORIGINE_DE_TEST}
            ),
            "jeton_invalide": client.post(
                "/api/v1/auth/deconnexion",
                headers={"Origin": ORIGINE_DE_TEST, EN_TETE_JETON: "x" * 64},
            ),
        }
    assert len(refus) == 3
    assert {r.status_code for r in refus.values()} == {403}
    corps = set()
    for reponse in refus.values():
        charge = reponse.json()
        charge["erreur"].pop("identifiant_correlation")
        corps.add(_json.dumps(charge, sort_keys=True))
    assert len(corps) == 1, f"les refus CSRF sont distinguables : {corps}"


# --- L'idempotence sur la route ---------------------------------------------


@pytest.mark.integration
def test_une_MEME_cle_ne_produit_QU_UN_lien(stack: tuple[Parametres, str, str]) -> None:
    """**LE CRITERE DE `US005` SUR LA SEULE ROUTE OU IL CHANGE QUELQUE CHOSE.**

    Un double clic sur « demander un lien » envoie deux e-mails ET invalide le
    premier : l'utilisateur recoit deux messages dont un seul fonctionne. Avec une
    cle, le second appel rend la meme reponse SANS reemettre.
    """
    parametres, adresse, _ = stack
    #  Le decor complet : une entite, une appartenance active, un domaine
    #  autorise — sinon aucun lien ne serait emis, et le test passerait pour la
    #  mauvaise raison.
    with moteur(parametres).begin() as connexion:
        entite = connexion.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:c, 'Entite T7', 'Bordeaux', 'FR', 'active', 'Europe/Paris') "
                "RETURNING id"
            ),
            {"c": f"T7-{uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        personne = connexion.execute(
            text("SELECT id FROM person WHERE email_normalized = :a"), {"a": adresse}
        ).scalar_one()
        connexion.execute(
            text(
                "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                "membership_state, professional_category, profile_visibility) "
                "VALUES (:p, :e, current_date - 30, 'active', 'consultant', 'draft')"
            ),
            {"p": personne, "e": entite},
        )
        connexion.execute(
            text(
                "INSERT INTO allowed_email_domain (domain, entity_id, active, starts_at) "
                "VALUES ('exalt-t7.test', NULL, TRUE, now() - interval '1 day')"
            )
        )

    cle = f"t7-{uuid.uuid4().hex}"
    try:
        with _client(parametres) as client:
            premiere = client.post(
                "/api/v1/auth/magic-link",
                json={"email": adresse},
                headers={"Origin": ORIGINE_DE_TEST, EN_TETE_CLE: cle},
            )
            seconde = client.post(
                "/api/v1/auth/magic-link",
                json={"email": adresse},
                headers={"Origin": ORIGINE_DE_TEST, EN_TETE_CLE: cle},
            )
        assert premiere.status_code == 202
        #  **LA MEME REPONSE**, pas une erreur : le client qui a perdu la premiere
        #  doit pouvoir la reobtenir.
        assert seconde.status_code == 202
        assert seconde.json() == premiere.json()

        #  **UN SEUL LIEN EN BASE.** C'est l'assertion qui discrimine : sans
        #  idempotence, il y en aurait deux — un invalide et un actif.
        with moteur(parametres).connect() as lecture:
            total = lecture.execute(
                text(
                    "SELECT count(*) FROM magic_link_request m "
                    "JOIN person p ON p.id = m.person_id "
                    "WHERE p.email_normalized = :a"
                ),
                {"a": adresse},
            ).scalar_one()
        assert total == 1, f"{total} liens au lieu de 1 : la cle n'a pas protege"
    finally:
        liberer(parametres, route="demande-magic-link", cle=cle)
        with moteur(parametres).begin() as menage:
            menage.execute(text("DELETE FROM allowed_email_domain WHERE domain = 'exalt-t7.test'"))


@pytest.mark.integration
def test_SANS_cle_deux_demandes_produisent_DEUX_liens(
    stack: tuple[Parametres, str, str],
) -> None:
    """**LE TEMOIN DU TEST PRECEDENT.**

    Sans lui, une route qui n'emettrait jamais qu'un lien — pour une raison
    etrangere a l'idempotence — passerait l'assertion « un seul lien ». Ici, deux
    demandes sans cle en produisent bien deux, dont un invalide.
    """
    parametres, adresse, _ = stack
    with moteur(parametres).begin() as connexion:
        entite = connexion.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:c, 'Entite T7b', 'Bordeaux', 'FR', 'active', 'Europe/Paris') "
                "RETURNING id"
            ),
            {"c": f"T7b-{uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        personne = connexion.execute(
            text("SELECT id FROM person WHERE email_normalized = :a"), {"a": adresse}
        ).scalar_one()
        connexion.execute(
            text(
                "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                "membership_state, professional_category, profile_visibility) "
                "VALUES (:p, :e, current_date - 30, 'active', 'consultant', 'draft')"
            ),
            {"p": personne, "e": entite},
        )
        connexion.execute(
            text(
                "INSERT INTO allowed_email_domain (domain, entity_id, active, starts_at) "
                "VALUES ('exalt-t7.test', NULL, TRUE, now() - interval '1 day')"
            )
        )
    try:
        with _client(parametres) as client:
            for _ in range(2):
                client.post(
                    "/api/v1/auth/magic-link",
                    json={"email": adresse},
                    headers={"Origin": ORIGINE_DE_TEST},
                )
        with moteur(parametres).connect() as lecture:
            total, actifs = lecture.execute(
                text(
                    "SELECT count(*), count(*) FILTER (WHERE m.used_at IS NULL "
                    "  AND m.invalidated_at IS NULL) "
                    "FROM magic_link_request m JOIN person p ON p.id = m.person_id "
                    "WHERE p.email_normalized = :a"
                ),
                {"a": adresse},
            ).one()
        assert total == 2, f"{total} liens au lieu de 2 : le temoin ne prouve rien"
        assert actifs == 1, "le dernier lien doit invalider le precedent (§10.3)"
    finally:
        with moteur(parametres).begin() as menage:
            menage.execute(text("DELETE FROM allowed_email_domain WHERE domain = 'exalt-t7.test'"))


@pytest.mark.integration
def test_une_cle_MALFORMEE_rend_422_sans_toucher_a_la_base(
    stack: tuple[Parametres, str, str],
) -> None:
    """Le refus ne depend QUE de la requete, jamais du contenu de la base."""
    parametres, adresse, _ = stack
    with _client(parametres) as client:
        reponse = client.post(
            "/api/v1/auth/magic-link",
            json={"email": adresse},
            headers={"Origin": ORIGINE_DE_TEST, EN_TETE_CLE: "court"},
        )
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champ"] == EN_TETE_CLE


@pytest.mark.integration
def test_la_route_de_session_n_exige_AUCUN_jeton(
    stack: tuple[Parametres, str, str],
) -> None:
    """**RESIDUEL NOMME, ET IL EST DELIBERE.**

    `GET …/auth/session` ecrit — elle rafraichit `last_activity_at` — et n'exige
    pourtant aucun jeton. Trois raisons, et la premiere suffit : **c'est elle qui
    DELIVRE le jeton**, l'exiger serait circulaire. Voir `routes.py`.
    """
    parametres, adresse, mot_de_passe = stack
    with _client(parametres) as client:
        client.post(
            "/api/v1/auth/connexion",
            json={"email": adresse, "mot_de_passe": mot_de_passe},
            headers={"Origin": ORIGINE_DE_TEST},
        )
        #  Sans jeton, et meme depuis une origine etrangere : elle repond.
        assert client.get("/api/v1/auth/session").status_code == 200
        assert (
            client.get(
                "/api/v1/auth/session", headers={"Origin": "https://mechant.example"}
            ).status_code
            == 200
        )


def _reponse(client: TestClient, chemin: str, corps: dict[str, str]) -> Response:
    reponse: Response = client.post(chemin, json=corps)
    return reponse
