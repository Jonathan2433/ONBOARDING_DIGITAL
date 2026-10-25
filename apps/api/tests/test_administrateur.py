"""Le compte administrateur local — story `MVP-L03-US003`, cahier §7.3, modele §10.2.

LOT 3, sous-etape `T5`.

TROIS FAMILLES DE PROPRIETES, ET LA TROISIEME EST CELLE QU'ON OUBLIE

  1. le HACHAGE       le mot de passe n'est jamais stocke en clair, l'algorithme et
                      ses parametres sont EN BASE, et une empreinte produite avec
                      d'anciens parametres reste verifiable
  2. le VERROUILLAGE  il se declenche au seuil, **et il se relache**
  3. l'ATOMICITE      trois tentatives CONCURRENTES comptent TROIS echecs

  La troisieme n'est pas un raffinement. Lire `failed_login_count`, l'incrementer
  puis decider laisserait trois tentatives simultanees lire la meme valeur et n'en
  compter qu'une : le compteur avancerait de 1 au lieu de 3, **et le verrouillage
  n'arriverait jamais**. Les tests 1 et 2 passeraient sans rien dire -- c'est
  exactement ce que `T4` a mesure sur l'usage unique, et le temoin negatif de cette
  sous-etape le rejoue.

LE TEMPS EST INJECTE

  Le verrou dure quinze minutes et sa fenetre en fait autant : un test qui les
  attendrait serait inutilisable en integration continue. `instant` est un
  parametre, et c'est lui qui fait avancer l'horloge.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.debit import CategorieDeCompteur, purger
from app.auth.modeles import EtatCompte, TypeCompte, TypeEvenementAuth
from app.auth.mots_de_passe import (
    ALGORITHME,
    PARAMETRES_PAR_DEFAUT,
    ParametresInvalides,
    hacher,
    parametres_a_durcir,
    verifier,
)
from app.auth.routes import LONGUEUR_MINIMALE_MOT_DE_PASSE
from app.auth.services import (
    ECHECS_AVANT_VERROUILLAGE,
    MINUTES_DE_FENETRE_D_ECHECS,
    MINUTES_DE_VERROUILLAGE,
    MOTIF_AUCUN_COMPTE_ADMIN,
    MOTIF_AUCUN_MOT_DE_PASSE,
    MOTIF_COMPTE_DESACTIVE,
    MOTIF_COMPTE_VERROUILLE,
    MOTIF_CONNEXION_REUSSIE,
    MOTIF_IDENTIFIANTS_REFUSES,
    Connexion,
    authentifier_un_administrateur,
    changer_le_mot_de_passe,
)
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 8, 21, 10, 30, tzinfo=dt.UTC)
MOT_DE_PASSE = "un-mot-de-passe-de-test-sans-portee"
AUTRE_MOT_DE_PASSE = "un-autre-mot-de-passe-de-test-sans-portee"

#  Borne de la barriere du test de concurrence, et duree du verrou de `B`. Elles
#  restent ECARTEES : la lecon `T4-4` est qu'un `lock_timeout` egal au delai de la
#  barriere rend le test instable une fois sur trois.
DELAI_ATTENTE_VERROU = 10.0
VERROU_TIMEOUT_CONCURRENT = "60s"


# ===========================================================================
#  Le hachage — aucune dependance
# ===========================================================================


def test_l_empreinte_ne_contient_PAS_le_mot_de_passe() -> None:
    """§10.2 : « aucun mot de passe brut ». Le plus elementaire, et il doit exister."""
    empreinte, _ = hacher(MOT_DE_PASSE)
    assert MOT_DE_PASSE not in empreinte


def test_deux_haches_du_MEME_mot_de_passe_DIFFERENT() -> None:
    """Le sel est tire par empreinte.

    Sans lui, deux administrateurs employant le meme mot de passe auraient la
    meme empreinte, et les rapprocher suffirait a le savoir.
    """
    assert hacher(MOT_DE_PASSE)[0] != hacher(MOT_DE_PASSE)[0]


def test_le_bon_mot_de_passe_est_accepte() -> None:
    """LE TEMOIN CENTRAL : sans lui, une fonction qui refuserait tout passerait
    tous les tests de refus ci-dessous.
    """
    empreinte, parametres = hacher(MOT_DE_PASSE)
    assert verifier(MOT_DE_PASSE, empreinte, parametres)


def test_un_mauvais_mot_de_passe_est_refuse() -> None:
    empreinte, parametres = hacher(MOT_DE_PASSE)
    assert not verifier(AUTRE_MOT_DE_PASSE, empreinte, parametres)
    #  Un caractere de plus, un de moins, la casse : trois formes voisines.
    assert not verifier(MOT_DE_PASSE + "x", empreinte, parametres)
    assert not verifier(MOT_DE_PASSE[:-1], empreinte, parametres)
    assert not verifier(MOT_DE_PASSE.upper(), empreinte, parametres)


@pytest.mark.parametrize(
    "malformee", ["", "sans-dollar", "$", "aaa$bbb", "!!!$!!!", "$abc", "abc$"]
)
def test_une_empreinte_MALFORMEE_rend_False_sans_lever(malformee: str) -> None:
    """Une valeur corrompue en base ne doit pas produire une 500.

    Le message d'une erreur 500 finit dans un journal ; et surtout, une exception
    ici distinguerait « empreinte corrompue » de « mot de passe faux », ce qui est
    une information de plus qu'un appelant ne doit pas avoir.
    """
    assert not verifier(MOT_DE_PASSE, malformee, PARAMETRES_PAR_DEFAUT)


def test_des_parametres_INCOMPLETS_levent_en_NOMMANT_le_manquant() -> None:
    """Sans ce controle, un `parameters` tronque rendrait un `KeyError` nu, dont le
    message ne dirait pas qu'il s'agit d'une empreinte de mot de passe.
    """
    for absent in ("n", "r", "p", "longueur_sel", "longueur_cle"):
        tronques = {c: v for c, v in PARAMETRES_PAR_DEFAUT.items() if c != absent}
        with pytest.raises(ParametresInvalides, match=absent):
            verifier(MOT_DE_PASSE, "aaa$bbb", tronques)


def test_un_n_qui_n_est_PAS_une_puissance_de_deux_est_refuse() -> None:
    """scrypt le refuserait de toute facon, mais avec un message d'OpenSSL.

    Le refuser ici NOMME le parametre, ce qu'OpenSSL ne fait pas.
    """
    with pytest.raises(ParametresInvalides, match="puissance de deux"):
        verifier(MOT_DE_PASSE, "aaa$bbb", {**PARAMETRES_PAR_DEFAUT, "n": 1000})


def test_une_empreinte_d_ANCIENS_parametres_reste_verifiable() -> None:
    """**C'EST TOUT LE MOTIF DES DEUX COLONNES DU §10.2.**

    Le §10.2 exige `algorithm` et `parameters` en colonnes « pour pouvoir migrer
    sans casser les comptes ». Ce test le prouve : une empreinte produite avec des
    parametres plus faibles se verifie encore, **avec ses parametres a elle**.
    Sans cette propriete, durcir les parametres deconnecterait tous les
    administrateurs.
    """
    faibles = {**PARAMETRES_PAR_DEFAUT, "n": 2**14}
    empreinte, stockes = hacher(MOT_DE_PASSE, faibles)
    assert verifier(MOT_DE_PASSE, empreinte, stockes)
    #  Et les parametres RENDUS sont bien ceux employes, non ceux du module :
    #  les stocker faux rendrait l'empreinte invérifiable au prochain durcissement.
    assert stockes["n"] == 2**14
    assert parametres_a_durcir(stockes)
    assert not parametres_a_durcir(PARAMETRES_PAR_DEFAUT)


def test_les_parametres_courants_sont_ceux_que_la_decision_nomme() -> None:
    """`DEC-526` nomme `N = 2^16`, `r = 8`, `p = 1`, et le motif est la MEMOIRE.

    scrypt consomme `128 * n * r` octets : 64 Mio ici, 128 a `N = 2^17`. La limite
    du service `api` est de 1 024 Mio (`DEC-440`) — huit connexions simultanees
    suffiraient a la saturer au parametre superieur.
    """
    assert PARAMETRES_PAR_DEFAUT["n"] == 2**16
    assert PARAMETRES_PAR_DEFAUT["r"] == 8
    assert PARAMETRES_PAR_DEFAUT["p"] == 1
    memoire_mio = 128 * PARAMETRES_PAR_DEFAUT["n"] * PARAMETRES_PAR_DEFAUT["r"] / 1024 / 1024
    assert memoire_mio == 64
    assert ALGORITHME == "scrypt"


def test_le_plancher_de_longueur_est_declare_NON_derive() -> None:
    """`QO-118` : aucun document du corpus n'ecrit de politique de mot de passe.

    Ce test ne valide pas la VALEUR — elle attend un arbitrage — il valide qu'elle
    existe en un seul endroit et qu'elle est non triviale. Le jour ou `QO-118` est
    tranchee, une seule ligne change.
    """
    assert LONGUEUR_MINIMALE_MOT_DE_PASSE >= 8


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
    """Connexion en ROLLBACK, avec le role d'EXECUTION — celui de l'API."""
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
                    "VALUES (:a, :a, 'Admin', 'T5', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


def _compte_admin(
    connexion: Connection,
    adresse: str,
    *,
    mot_de_passe: str | None = MOT_DE_PASSE,
    etat: str = EtatCompte.ACTIVE.value,
    changement_exige: bool = False,
    parametres: dict[str, int] | None = None,
) -> uuid.UUID:
    """Un compte `ADMIN_LOCAL` complet.

    `failed_login_count` est NOMMEE : son defaut est cote Python, pas
    `server_default`, et un `INSERT` en SQL brut ne le recoit pas. C'est le defaut
    `T3-2`, dont `T4` avait prevenu `T5`.
    """
    personne = _personne(connexion, adresse)
    compte = uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO user_account "
                    "(person_id, account_type, state, failed_login_count) "
                    "VALUES (:p, :t, :e, 0) RETURNING id"
                ),
                {"p": personne, "t": TypeCompte.ADMIN_LOCAL.value, "e": etat},
            ).scalar_one()
        )
    )
    if mot_de_passe is not None:
        empreinte, effectifs = hacher(mot_de_passe, parametres)
        connexion.execute(
            text(
                "INSERT INTO admin_password_credential "
                "(user_account_id, password_hash, algorithm, parameters, changed_at, "
                " must_change) "
                "VALUES (:c, :h, :a, :params, :quand, :change)"
            ),
            {
                "c": compte,
                "h": empreinte,
                "a": ALGORITHME,
                "params": json.dumps(effectifs),
                "quand": INSTANT,
                "change": changement_exige,
            },
        )
    return compte


def _connecter(
    cx: Connection,
    adresse: str,
    mot_de_passe: str = MOT_DE_PASSE,
    *,
    instant: dt.datetime = INSTANT,
) -> Connexion:
    return authentifier_un_administrateur(
        cx, adresse=adresse, mot_de_passe=mot_de_passe, instant=instant
    )


@pytest.mark.integration
def test_le_BON_mot_de_passe_ouvre_la_connexion(cx: Connection) -> None:
    """LE TEMOIN CENTRAL du service : sans lui, tous les refus seraient satisfaits
    par une fonction qui refuserait tout.
    """
    _compte_admin(cx, "admin-ok@exalt-t5.test")
    resultat = _connecter(cx, "admin-ok@exalt-t5.test")
    assert resultat.motif == MOTIF_CONNEXION_REUSSIE
    assert resultat.reussie
    assert resultat.compte is not None


@pytest.mark.integration
def test_un_MAUVAIS_mot_de_passe_est_refuse(cx: Connection) -> None:
    _compte_admin(cx, "admin-faux@exalt-t5.test")
    resultat = _connecter(cx, "admin-faux@exalt-t5.test", AUTRE_MOT_DE_PASSE)
    assert resultat.motif == MOTIF_IDENTIFIANTS_REFUSES
    assert not resultat.reussie


@pytest.mark.integration
def test_une_adresse_SANS_compte_administrateur_est_refusee(cx: Connection) -> None:
    """Une personne peut exister sans compte `ADMIN_LOCAL` : le §10.1 en fait une
    permission, pas une obligation.
    """
    _personne(cx, "sans-compte@exalt-t5.test")
    assert _connecter(cx, "sans-compte@exalt-t5.test").motif == MOTIF_AUCUN_COMPTE_ADMIN


@pytest.mark.integration
def test_un_compte_employe_ne_sert_PAS_a_la_connexion_administrateur(cx: Connection) -> None:
    """§10.1 : les deux types de compte sont DISTINCTS.

    Sans ce test, une requete qui oublierait `account_type` laisserait un compte
    employe — qui n'a pas de mot de passe — servir de compte administrateur.
    """
    personne = _personne(cx, "employe@exalt-t5.test")
    cx.execute(
        text(
            "INSERT INTO user_account (person_id, account_type, state, failed_login_count) "
            "VALUES (:p, :t, 'active', 0)"
        ),
        {"p": personne, "t": TypeCompte.EMPLOYEE_MAGIC_LINK.value},
    )
    assert _connecter(cx, "employe@exalt-t5.test").motif == MOTIF_AUCUN_COMPTE_ADMIN


@pytest.mark.integration
def test_un_compte_DESACTIVE_est_refuse_meme_avec_le_bon_mot_de_passe(cx: Connection) -> None:
    """§10.1 : `state` vaut `active`, `locked` ou `disabled`.

    Le bon mot de passe est fourni : c'est l'etat SEUL qui refuse. Sans cela, la
    colonne serait sans effet.
    """
    _compte_admin(cx, "admin-off@exalt-t5.test", etat=EtatCompte.DISABLED.value)
    assert _connecter(cx, "admin-off@exalt-t5.test").motif == MOTIF_COMPTE_DESACTIVE


@pytest.mark.integration
def test_un_compte_SANS_mot_de_passe_actif_est_refuse(cx: Connection) -> None:
    """L'index partiel de `T2` garantit qu'il y en a AU PLUS un ; il n'exige pas
    qu'il y en ait un. Un compte sans identifiant doit donc echouer proprement.
    """
    _compte_admin(cx, "admin-nu@exalt-t5.test", mot_de_passe=None)
    assert _connecter(cx, "admin-nu@exalt-t5.test").motif == MOTIF_AUCUN_MOT_DE_PASSE


# --- Le verrouillage : il se declenche, ET il se relache --------------------


@pytest.mark.integration
def test_le_verrouillage_se_DECLENCHE_au_seuil(cx: Connection) -> None:
    """§20.2 : « 5 echecs administrateur en 15 minutes ».

    Les quatre premiers echecs ne verrouillent PAS, et c'est la moitie du test :
    un verrou qui tomberait au premier echec passerait un test qui ne compterait
    que le cinquieme.
    """
    _compte_admin(cx, "admin-verrou@exalt-t5.test")
    for tentative in range(1, ECHECS_AVANT_VERROUILLAGE):
        resultat = _connecter(
            cx,
            "admin-verrou@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative),
        )
        assert resultat.motif == MOTIF_IDENTIFIANTS_REFUSES, f"tentative {tentative}"

    #  Le BON mot de passe passe encore : le compte n'est pas verrouille.
    assert _connecter(
        cx, "admin-verrou@exalt-t5.test", instant=INSTANT + dt.timedelta(seconds=10)
    ).reussie


@pytest.mark.integration
def test_le_CINQUIEME_echec_verrouille_le_compte(cx: Connection) -> None:
    """Et le BON mot de passe est refuse ensuite : c'est ce qui prouve le verrou.

    Sans cette seconde moitie, un compteur qui avancerait sans jamais verrouiller
    passerait le test.
    """
    _compte_admin(cx, "admin-verrou5@exalt-t5.test")
    for tentative in range(ECHECS_AVANT_VERROUILLAGE):
        _connecter(
            cx,
            "admin-verrou5@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative),
        )
    resultat = _connecter(
        cx, "admin-verrou5@exalt-t5.test", instant=INSTANT + dt.timedelta(seconds=30)
    )
    assert resultat.motif == MOTIF_COMPTE_VERROUILLE
    assert not resultat.reussie


@pytest.mark.integration
def test_le_verrouillage_se_RELACHE_apres_quinze_minutes(cx: Connection) -> None:
    """**C'EST LA PARADE AU RISQUE NOMME AU §7 DE LA FICHE** — « le verrouillage
    administrateur bloque Jonathan lui-meme ».

    Le verrou n'est pas definitif : aucune intervention n'est obligatoire. Le
    temps est INJECTE, ce test ne dort pas quinze minutes.
    """
    _compte_admin(cx, "admin-relache@exalt-t5.test")
    for tentative in range(ECHECS_AVANT_VERROUILLAGE):
        _connecter(
            cx,
            "admin-relache@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative),
        )
    #  Une minute AVANT la fin du verrou : encore verrouille.
    presque = INSTANT + dt.timedelta(minutes=MINUTES_DE_VERROUILLAGE - 1)
    assert _connecter(cx, "admin-relache@exalt-t5.test", instant=presque).motif == (
        MOTIF_COMPTE_VERROUILLE
    )
    #  Une minute APRES : le bon mot de passe passe.
    apres = INSTANT + dt.timedelta(minutes=MINUTES_DE_VERROUILLAGE + 1)
    assert _connecter(cx, "admin-relache@exalt-t5.test", instant=apres).reussie


@pytest.mark.integration
def test_une_tentative_sur_un_compte_VERROUILLE_ne_PROLONGE_pas_le_verrou(
    cx: Connection,
) -> None:
    """**SANS CELA, LE VERROUILLAGE DEVIENDRAIT UN DENI DE SERVICE PERMANENT.**

    Un attaquant qui continue de frapper un compte verrouille repousserait la fin
    du verrou a chaque coup, et le titulaire legitime ne pourrait plus jamais se
    connecter. Le verrou est donc examine AVANT le mot de passe, et le compteur
    n'avance pas.
    """
    _compte_admin(cx, "admin-dos@exalt-t5.test")
    for tentative in range(ECHECS_AVANT_VERROUILLAGE):
        _connecter(
            cx,
            "admin-dos@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative),
        )
    fin_initiale = cx.execute(
        text(
            "SELECT u.locked_until FROM user_account u JOIN person p ON p.id = u.person_id "
            "WHERE p.email_normalized = :a"
        ),
        {"a": "admin-dos@exalt-t5.test"},
    ).scalar_one()

    #  Dix tentatives de plus, pendant le verrou.
    for tentative in range(10):
        _connecter(
            cx,
            "admin-dos@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(minutes=1, seconds=tentative),
        )
    fin_apres = cx.execute(
        text(
            "SELECT u.locked_until FROM user_account u JOIN person p ON p.id = u.person_id "
            "WHERE p.email_normalized = :a"
        ),
        {"a": "admin-dos@exalt-t5.test"},
    ).scalar_one()
    assert fin_apres == fin_initiale, "le verrou a ete PROLONGE par des tentatives"


@pytest.mark.integration
def test_la_FENETRE_remet_le_compteur_a_zero(cx: Connection) -> None:
    """« 5 echecs en 15 MINUTES ». Un compteur qui ne se remettrait jamais a zero
    verrouillerait pour cinq echecs etales sur six mois, ce que la phrase du §20.2
    ne dit pas.
    """
    _compte_admin(cx, "admin-fenetre@exalt-t5.test")
    #  Quatre echecs, puis un saut hors fenetre, puis quatre autres : huit echecs
    #  au total, et AUCUN verrou.
    for tentative in range(ECHECS_AVANT_VERROUILLAGE - 1):
        _connecter(
            cx,
            "admin-fenetre@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative),
        )
    plus_tard = INSTANT + dt.timedelta(minutes=MINUTES_DE_FENETRE_D_ECHECS + 1)
    for tentative in range(ECHECS_AVANT_VERROUILLAGE - 1):
        _connecter(
            cx,
            "admin-fenetre@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=plus_tard + dt.timedelta(seconds=tentative),
        )
    assert _connecter(
        cx, "admin-fenetre@exalt-t5.test", instant=plus_tard + dt.timedelta(minutes=1)
    ).reussie


@pytest.mark.integration
def test_une_REUSSITE_remet_le_compteur_a_zero(cx: Connection) -> None:
    """Sans cela, quatre echecs suivis d'une reussite laisseraient le compte a un
    seul echec du verrou — et le prochain faux frappe verrouillerait.
    """
    _compte_admin(cx, "admin-reset@exalt-t5.test")
    for tentative in range(ECHECS_AVANT_VERROUILLAGE - 1):
        _connecter(
            cx,
            "admin-reset@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative),
        )
    assert _connecter(cx, "admin-reset@exalt-t5.test", instant=INSTANT).reussie
    compteur = cx.execute(
        text(
            "SELECT u.failed_login_count FROM user_account u "
            "JOIN person p ON p.id = u.person_id WHERE p.email_normalized = :a"
        ),
        {"a": "admin-reset@exalt-t5.test"},
    ).scalar_one()
    assert compteur == 0


# --- `must_change` et le changement de mot de passe ------------------------


@pytest.mark.integration
def test_must_change_est_REMONTE_a_l_appelant(cx: Connection) -> None:
    """§10.2 : `must_change`. C'est la seule information que la reussite ajoute."""
    _compte_admin(cx, "admin-change@exalt-t5.test", changement_exige=True)
    assert _connecter(cx, "admin-change@exalt-t5.test").changement_exige
    _compte_admin(cx, "admin-libre@exalt-t5.test", changement_exige=False)
    assert not _connecter(cx, "admin-libre@exalt-t5.test").changement_exige


@pytest.mark.integration
def test_le_changement_REVOQUE_l_ancien_et_pose_le_nouveau(cx: Connection) -> None:
    """§10.2 : « aucun historique reversible », et l'index partiel de `T2` exige
    qu'au plus un identifiant soit actif.

    L'ordre est impose : poser le nouveau avant de revoquer l'ancien ferait
    echouer l'insertion. Ce test le prouve en comptant les DEUX lignes.
    """
    compte = _compte_admin(cx, "admin-maj@exalt-t5.test", changement_exige=True)
    changer_le_mot_de_passe(cx, compte=compte, nouveau=AUTRE_MOT_DE_PASSE, instant=INSTANT)
    lignes = cx.execute(
        text(
            "SELECT revoked_at IS NULL, must_change FROM admin_password_credential "
            "WHERE user_account_id = :c ORDER BY changed_at, revoked_at NULLS LAST"
        ),
        {"c": compte},
    ).all()
    assert len(lignes) == 2, "l'ancien identifiant doit etre CONSERVE, revoque"
    actifs = [ligne for ligne in lignes if ligne[0]]
    assert len(actifs) == 1
    #  Le nouveau ne porte plus `must_change` : le changement a eu lieu.
    assert actifs[0][1] is False

    #  Et le nouveau mot de passe fonctionne, l'ancien non.
    assert _connecter(cx, "admin-maj@exalt-t5.test", AUTRE_MOT_DE_PASSE).reussie
    assert not _connecter(cx, "admin-maj@exalt-t5.test", MOT_DE_PASSE).reussie


@pytest.mark.integration
def test_le_changement_est_AUDITE(cx: Connection) -> None:
    """§10.6 : « mot de passe administrateur modifie » est l'un des sept types."""
    compte = _compte_admin(cx, "admin-audit-maj@exalt-t5.test")
    changer_le_mot_de_passe(cx, compte=compte, nouveau=AUTRE_MOT_DE_PASSE, instant=INSTANT)
    types = (
        cx.execute(
            text("SELECT event_type FROM auth_event WHERE user_account_id = :c"),
            {"c": compte},
        )
        .scalars()
        .all()
    )
    assert TypeEvenementAuth.ADMIN_PASSWORD_CHANGED.value in types


@pytest.mark.integration
def test_aucun_evenement_ne_porte_le_mot_de_passe(cx: Connection) -> None:
    """§28.2 et §10.6 : le secret ne doit apparaitre sous AUCUNE forme.

    Le test regarde la ligne ENTIERE, pas la seule colonne attendue — une fuite
    dans `detail` passerait autrement.
    """
    compte = _compte_admin(cx, "admin-secret@exalt-t5.test")
    _connecter(cx, "admin-secret@exalt-t5.test", AUTRE_MOT_DE_PASSE)
    _connecter(cx, "admin-secret@exalt-t5.test")
    changer_le_mot_de_passe(cx, compte=compte, nouveau=AUTRE_MOT_DE_PASSE, instant=INSTANT)
    lignes = (
        cx.execute(
            text("SELECT e::text FROM auth_event e WHERE e.user_account_id = :c"),
            {"c": compte},
        )
        .scalars()
        .all()
    )
    assert lignes, "aucun evenement : ce test ne prouverait rien"
    for ligne in lignes:
        assert MOT_DE_PASSE not in ligne
        assert AUTRE_MOT_DE_PASSE not in ligne


@pytest.mark.integration
def test_les_QUATRE_types_d_evenement_de_T5_sont_traces(cx: Connection) -> None:
    """§10.6. `T5` produit quatre des sept types, et le compte est DERIVE.

    `MAGIC_LINK_REQUESTED` et `MAGIC_LINK_USED` viennent de `T3` et `T4`,
    `SESSION_REVOKED` de `T9`.
    """
    compte = _compte_admin(cx, "admin-quatre@exalt-t5.test")
    _connecter(cx, "admin-quatre@exalt-t5.test")
    for tentative in range(ECHECS_AVANT_VERROUILLAGE):
        _connecter(
            cx,
            "admin-quatre@exalt-t5.test",
            AUTRE_MOT_DE_PASSE,
            instant=INSTANT + dt.timedelta(seconds=tentative + 1),
        )
    changer_le_mot_de_passe(cx, compte=compte, nouveau=AUTRE_MOT_DE_PASSE, instant=INSTANT)
    types = set(
        cx.execute(
            text("SELECT event_type FROM auth_event WHERE user_account_id = :c"),
            {"c": compte},
        )
        .scalars()
        .all()
    )
    attendus = {
        TypeEvenementAuth.LOGIN_SUCCESS.value,
        TypeEvenementAuth.LOGIN_FAILURE.value,
        TypeEvenementAuth.ACCOUNT_LOCKED.value,
        TypeEvenementAuth.ADMIN_PASSWORD_CHANGED.value,
    }
    assert attendus <= types, f"manquants : {sorted(attendus - types)}"
    assert len(attendus) == 4


# --- L'ATOMICITE du compteur, sous concurrence ------------------------------


@pytest.mark.integration
def test_le_compteur_d_echecs_est_ATOMIQUE_sous_CONCURRENCE(
    parametres_de_la_stack: Parametres,
) -> None:
    """**DEUX TENTATIVES CONCURRENTES DOIVENT COMPTER DEUX ECHECS.**

    Lire `failed_login_count`, l'incrementer puis ecrire laisserait deux
    tentatives simultanees lire la meme valeur et n'en compter qu'une : le
    compteur avancerait de 1 au lieu de 2, **et le verrouillage n'arriverait
    jamais**. Tous les tests sequentiels ci-dessus passeraient sans rien dire.

    C'est le meme scenario que `T4` sur l'usage unique, et la meme forme :
    `A` compte sans valider, `B` attend le verrou de ligne, `A` valide, `B`
    reprend. La barriere interroge `pg_blocking_pids()` — une condition observee,
    pas un delai espere.
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t5race{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@exalt-t5.test"

    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as preparation:
        _compte_admin(preparation, adresse)

    resultats: dict[str, object] = {}
    erreurs: list[BaseException] = []

    pret = threading.Event()

    def compter_dans_un_fil() -> None:
        connexion = moteur(parametres_de_la_stack).connect()
        try:
            with connexion.begin():
                connexion.execute(text(f"SET LOCAL lock_timeout = '{VERROU_TIMEOUT_CONCURRENT}'"))
                #  ==========================================================
                #
                #   LE SIGNAL EST POSE ICI, ET SA PLACE EST TOUT L'INTERET
                #
                #     Apres l'ouverture de la connexion et le reglage du
                #     `lock_timeout`, **avant** l'instruction bloquante. La
                #     barriere du fil principal ne demarre donc son horloge
                #     qu'une fois B reellement prete a se bloquer.
                #
                #     **MESURE QUI L'A IMPOSE, EN `T8`.** Deux tests de
                #     concurrence -- celui-ci et ceux de `T4` et `T5` -- ont
                #     echoue par intermittence sur « B n'a pas ete bloquee », et
                #     l'etat observe montrait que **le backend de B n'existait pas
                #     encore** : l'ouverture d'une connexion PostgreSQL neuve
                #     consommait le budget de la barriere, sous la charge d'une
                #     suite complete. Ce n'est pas le verrou qui manquait, c'est
                #     la connexion qui n'etait pas la.
                #
                #     Meme famille que le defaut `T4-4`, ou les deux delais se
                #     chevauchaient : un controle intermittent coute plus cher
                #     qu'un controle faux, parce qu'on apprend a le relancer.
                #
                #  ==========================================================
                pret.set()
                resultats["b"] = authentifier_un_administrateur(
                    connexion,
                    adresse=adresse,
                    mot_de_passe=AUTRE_MOT_DE_PASSE,
                    instant=INSTANT,
                )
        except BaseException as erreur:
            erreurs.append(erreur)
        finally:
            connexion.close()

    premiere = moteur(parametres_de_la_stack).connect()
    try:
        transaction_a = premiere.begin()
        assert not authentifier_un_administrateur(
            premiere, adresse=adresse, mot_de_passe=AUTRE_MOT_DE_PASSE, instant=INSTANT
        ).reussie

        fil = threading.Thread(target=compter_dans_un_fil, daemon=True)
        fil.start()
        #  **LA BARRIERE N'OUVRE SON HORLOGE QU'APRES LE SIGNAL DE B** — voir le
        #  bloc de commentaire dans le fil.
        assert pret.wait(DELAI_ATTENTE_VERROU), (
            f"B n'a pas signale son depart en {DELAI_ATTENTE_VERROU} s : la cause est "
            "l'ouverture de sa connexion, PAS l'absence de verrou"
        )

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

        #  **LE COMPTEUR DOIT VALOIR 2, PAS 1.** C'est l'assertion qui discrimine.
        with moteur(parametres_de_la_stack).connect() as lecture:
            compteur = lecture.execute(
                text(
                    "SELECT u.failed_login_count FROM user_account u "
                    "JOIN person p ON p.id = u.person_id WHERE p.email_normalized = :a"
                ),
                {"a": adresse},
            ).scalar_one()
        assert compteur == 2, (
            f"le compteur vaut {compteur} au lieu de 2 : deux tentatives "
            "concurrentes n'en ont compte qu'une, et le verrouillage n'arrivera "
            "jamais sous charge"
        )
    finally:
        premiere.close()
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                #  LOT 10, `T2` : `audit_event.actor_person_id` reference aussi
                #  `person`, meme motif que la ligne `auth_event` au-dessus — et
                #  la meme classe de defaut que `user_session` en `T6` (§7.21).
                "DELETE FROM audit_event WHERE actor_person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                #  `user_session` A ETE AJOUTEE PAR `T6`, ET SON ABSENCE ICI A
                #  CASSE DIX TESTS SANS RAPPORT.
                #
                #  Ce nettoyage etait complet quand `T5` l'a ecrit : la route de
                #  connexion ne creait alors AUCUNE session. `T6` lui en fait
                #  creer une, la cle etrangere `fk_user_session_person_id_person`
                #  a bloque la suppression de la personne, et le residu a fait
                #  echouer `test_personnes.py`, `test_authentification.py` et
                #  `test_jeu_de_recette.py`. Defaut `T6-2`, et c'est le §7.21 :
                #  un controle ne devient pas faux tout seul.
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM admin_password_credential WHERE user_account_id IN "
                "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM user_account WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= :debut",
                "DELETE FROM audit_event WHERE actor_person_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


# ===========================================================================
#  Les routes — un seul gabarit de refus
# ===========================================================================


@pytest.fixture
def stack_avec_admin(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str]]:
    """Un compte administrateur PERSISTANT : les routes valident leur transaction."""
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t5api{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@exalt-t5.test"
    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as connexion:
        _compte_admin(connexion, adresse)
    try:
        yield parametres_de_la_stack, adresse
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                #  LOT 10, `T2` : `audit_event.actor_person_id` reference aussi
                #  `person`, meme motif que la ligne `auth_event` au-dessus — et
                #  la meme classe de defaut que `user_session` en `T6` (§7.21).
                "DELETE FROM audit_event WHERE actor_person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                #  `user_session` A ETE AJOUTEE PAR `T6`, ET SON ABSENCE ICI A
                #  CASSE DIX TESTS SANS RAPPORT.
                #
                #  Ce nettoyage etait complet quand `T5` l'a ecrit : la route de
                #  connexion ne creait alors AUCUNE session. `T6` lui en fait
                #  creer une, la cle etrangere `fk_user_session_person_id_person`
                #  a bloque la suppression de la personne, et le residu a fait
                #  echouer `test_personnes.py`, `test_authentification.py` et
                #  `test_jeu_de_recette.py`. Defaut `T6-2`, et c'est le §7.21 :
                #  un controle ne devient pas faux tout seul.
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM admin_password_credential WHERE user_account_id IN "
                "(SELECT u.id FROM user_account u JOIN person p ON p.id = u.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM user_account WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= :debut",
                "DELETE FROM audit_event WHERE actor_person_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _reponse(parametres: Parametres, chemin: str, charge: dict[str, str]) -> Response:
    """POST sur une route, sur une application montee avec CES parametres.

    `TestClient.post` n'est pas type par Starlette : l'annotation explicite est ce
    qui permet a mypy strict de verifier les appelants. `DEC-442`.
    """
    with TestClient(creer_application(parametres)) as client:
        reponse: Response = client.post(chemin, json=charge)
    return reponse


@pytest.mark.integration
def test_la_route_de_connexion_accepte_le_BON_mot_de_passe(
    stack_avec_admin: tuple[Parametres, str],
) -> None:
    parametres, adresse = stack_avec_admin
    reponse = _reponse(
        parametres,
        "/api/v1/auth/connexion",
        {"email": adresse, "mot_de_passe": MOT_DE_PASSE},
    )
    assert reponse.status_code == 200
    assert reponse.json()["changement_exige"] is False
    assert reponse.headers["cache-control"] == "no-store"


@pytest.mark.integration
def test_les_CINQ_causes_de_refus_rendent_la_MEME_reponse(
    stack_avec_admin: tuple[Parametres, str],
) -> None:
    """**UN REFUS QUI DISTINGUERAIT LES CAS SERAIT UN ORACLE.**

    Il dirait qu'une adresse porte un compte administrateur, et — pire — il
    apprendrait a un attaquant qu'il a REUSSI a verrouiller le titulaire.

    Les cinq causes sont enumerees : sans l'enumeration, ce test pourrait n'en
    avoir exerce qu'une.
    """
    parametres, adresse = stack_avec_admin
    inconnue = f"inconnue-{uuid.uuid4().hex[:8]}@exalt-t5.test"

    refus = {
        "adresse_inconnue": _reponse(
            parametres,
            "/api/v1/auth/connexion",
            {"email": inconnue, "mot_de_passe": MOT_DE_PASSE},
        ),
        "mot_de_passe_faux": _reponse(
            parametres,
            "/api/v1/auth/connexion",
            {"email": adresse, "mot_de_passe": AUTRE_MOT_DE_PASSE},
        ),
        "adresse_fantaisiste": _reponse(
            parametres,
            "/api/v1/auth/connexion",
            {"email": "pas-une-adresse", "mot_de_passe": MOT_DE_PASSE},
        ),
    }
    #  Quatre echecs de plus verrouillent le compte : le cinquieme refus est donc
    #  « compte verrouille », obtenu sans le declarer.
    for _ in range(ECHECS_AVANT_VERROUILLAGE):
        _reponse(
            parametres,
            "/api/v1/auth/connexion",
            {"email": adresse, "mot_de_passe": AUTRE_MOT_DE_PASSE},
        )
    #  **LE COMPTEUR DE `T8` EST EFFACE ICI, ET C'EST UN CORRECTIF DE `T8`.**
    #
    #  Ce test produit SIX echecs sur la meme adresse pour atteindre l'etat
    #  « compte verrouille ». Depuis `T8`, la limitation par adresse refuse la
    #  sixieme tentative avec un **429**, si bien que ce test echouait sur un
    #  livrable conforme : il n'atteignait plus l'etat qu'il veut eprouver.
    #
    #  L'effacer est le bon geste, et non un contournement : ce test porte sur
    #  l'EGALITE des cinq refus de `T5`, pas sur la limitation de debit -- qui a
    #  ses propres tests et son propre controle. Le verrou obtenu reste **reel**,
    #  produit par six vrais echecs, et c'est ce que ce test voulait prouver.
    #
    #  Le 429 de `T8` n'est PAS un oracle : il arrive pour toute adresse, connue
    #  ou non, et `test_debit.py` le prouve des deux cotes.
    purger(parametres, categorie=CategorieDeCompteur.ECHEC_ADMIN)
    refus["compte_verrouille"] = _reponse(
        parametres, "/api/v1/auth/connexion", {"email": adresse, "mot_de_passe": MOT_DE_PASSE}
    )

    assert len(refus) == 4
    assert {r.status_code for r in refus.values()} == {400}
    #  Les corps sont identiques HORS identifiant de correlation, qui DOIT varier
    #  (cahier §18.3, §28.1). Le neutraliser sans le nommer serait la ou une fuite
    #  se cacherait.
    corps = set()
    correlations = set()
    for reponse in refus.values():
        charge = reponse.json()
        correlations.add(charge["erreur"].pop("identifiant_correlation"))
        corps.add(json.dumps(charge, sort_keys=True))
    assert len(corps) == 1, f"les refus sont distinguables : {corps}"
    assert len(correlations) == len(refus), "les identifiants de correlation ne varient pas"


@pytest.mark.integration
def test_le_changement_par_la_route_EXIGE_le_mot_de_passe_actuel(
    stack_avec_admin: tuple[Parametres, str],
) -> None:
    """Sans session — elles relevent de `T6` — c'est la seule preuve du titulaire.

    Et le refus a la MEME forme que celui de la connexion : sinon cette route
    deviendrait l'oracle que l'autre n'est pas.
    """
    parametres, adresse = stack_avec_admin
    refuse = _reponse(
        parametres,
        "/api/v1/auth/mot-de-passe",
        {
            "email": adresse,
            "mot_de_passe_actuel": AUTRE_MOT_DE_PASSE,
            "nouveau_mot_de_passe": "un-nouveau-mot-de-passe-valide",
        },
    )
    assert refuse.status_code == 400

    accepte = _reponse(
        parametres,
        "/api/v1/auth/mot-de-passe",
        {
            "email": adresse,
            "mot_de_passe_actuel": MOT_DE_PASSE,
            "nouveau_mot_de_passe": "un-nouveau-mot-de-passe-valide",
        },
    )
    assert accepte.status_code == 200
    #  Le nouveau fonctionne, l'ancien non.
    assert (
        _reponse(
            parametres,
            "/api/v1/auth/connexion",
            {"email": adresse, "mot_de_passe": "un-nouveau-mot-de-passe-valide"},
        ).status_code
        == 200
    )
    assert (
        _reponse(
            parametres,
            "/api/v1/auth/connexion",
            {"email": adresse, "mot_de_passe": MOT_DE_PASSE},
        ).status_code
        == 400
    )


@pytest.mark.integration
def test_un_nouveau_mot_de_passe_TROP_COURT_est_refuse(
    stack_avec_admin: tuple[Parametres, str],
) -> None:
    """`QO-118` : le plancher n'est PAS derive du corpus, et il est declare comme
    tel. Ce test verifie qu'il s'applique, non que sa valeur soit la bonne.

    Le refus est un 422 — il ne depend QUE de la forme de la requete, jamais du
    contenu de la base — donc il ne revele rien.
    """
    parametres, adresse = stack_avec_admin
    reponse = _reponse(
        parametres,
        "/api/v1/auth/mot-de-passe",
        {
            "email": adresse,
            "mot_de_passe_actuel": MOT_DE_PASSE,
            "nouveau_mot_de_passe": "a" * (LONGUEUR_MINIMALE_MOT_DE_PASSE - 1),
        },
    )
    assert reponse.status_code == 422
