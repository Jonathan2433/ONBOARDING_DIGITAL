"""Limitation de debit — stories `MVP-L03-US001` et `US003`, cahier §20.1, §20.2.

LOT 3, sous-etape `T8`.

CE FICHIER PROUVE TROIS CHOSES DISTINCTES, ET LA TROISIEME EST LA PLUS UTILE

  1. **les seuils sont ceux du cahier**, et ils sont RELUS dans le cahier par un
     test plutot que recopies ici. Un seuil recopie vieillit au premier
     changement, et c'est la classe `ECART-021` -- rejouee une douzaine de fois
     dans ce projet ;
  2. **la limitation refuse**, et la detection **ne refuse pas** : le §20.2
     emploie deux verbes differents, « limitation » et « alerte », et les
     confondre bloquerait tout un bureau derriere un partage d'adresse ;
  3. **la limite ne devient pas l'oracle que `T3` a ferme.** Si le 429 n'arrivait
     que pour les adresses connues, il dirait « ce compte existe ». Les deux
     chemins sont donc compares **corps et en-tetes**, exactement comme `T3`
     comparait ses 202.

LE TEMPS S'INJECTE, ET AUCUN TEST NE DORT

  Une fenetre d'une heure ne s'attend pas. Ce qui est verifiable sans dormir est
  ce qui compte : que le delai soit **pose** a la creation, qu'il ne soit
  **jamais repousse**, et que le compteur soit **atomique**. Le reste est le
  travail de Redis, et le mesurer reviendrait a tester Redis.
"""

from __future__ import annotations

import json as _json
import re
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import redis
from conftest import HOTE_LOCAL, VARIABLES_MINIMALES, port_ouvert
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.debit import (
    DEMANDES_DE_LIEN_PAR_ADRESSE,
    DEMANDES_PAR_ORIGINE,
    ECHECS_ADMIN_PAR_ADRESSE,
    FENETRE_DEMANDES_DE_LIEN,
    FENETRE_ECHECS_ADMIN,
    PREFIXE_REDIS,
    CategorieDeCompteur,
    Comptage,
    CompteurIndisponible,
    compter,
    empreinte_pour_le_debit,
    lire,
    purger,
    reinitialiser,
)
from app.auth.jetons import empreinte_d_origine, empreinte_minimisee
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
MOT_DE_PASSE = "Un-Mot-De-Passe-Suffisamment-Long-8"
MAUVAIS_MOT_DE_PASSE = "Ce-N-Est-Pas-Le-Bon-Mot-De-Passe-9"

#  Les memes que `T3` : ceux qui varient d'une reponse a l'autre sans rien dire
#  du contenu de la base.
EN_TETES_VARIABLES = frozenset({"x-request-id", "date"})

CAHIER = Path(__file__).resolve().parents[3] / "docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md"

#  Un port qu'aucun service du projet n'emploie : les 14 publications sont
#  nommees dans `exploitation-locale.md`, et 6399 n'en est pas.
PORT_FERME = 6399


# ===========================================================================
#  Les seuils : DERIVES DU CAHIER, jamais recopies
# ===========================================================================


def test_les_trois_seuils_sont_ceux_du_CAHIER_relu() -> None:
    """**LE CONTROLE QUI AURAIT ATTRAPE `ECART-034`.**

    La fiche du lot annonçait « le cahier exige une limitation, **sans donner de
    seuil** ». Le §20.2 en donne six. Ce test relit le cahier et exige que les
    trois constantes correspondent aux phrases qui les produisent -- si bien
    qu'une modification du cahier, ou une constante changee a la main, fait
    echouer la suite au lieu de passer en silence.
    """
    texte = CAHIER.read_text(encoding="utf-8")
    attendu = f"{DEMANDES_DE_LIEN_PAR_ADRESSE} demandes de magic link par adresse et par heure"
    assert attendu in texte
    assert f"{DEMANDES_PAR_ORIGINE} demandes depuis une même origine en une heure" in texte
    assert f"{ECHECS_ADMIN_PAR_ADRESSE} échecs administrateur en 15 minutes" in texte


def test_les_deux_VERBES_du_cahier_sont_distincts() -> None:
    """**LA DISTINCTION QUI COMMANDE TOUT LE COMPORTEMENT.**

    Une seule des trois lignes est une « limitation ». Si le cahier changeait de
    verbe, ce test echouerait -- et il devrait, parce que le comportement du
    module en depend entierement.
    """
    texte = CAHIER.read_text(encoding="utf-8")
    assert (
        f"{DEMANDES_DE_LIEN_PAR_ADRESSE} demandes de magic link par adresse et par heure : "
        "limitation" in texte
    )
    assert f"{DEMANDES_PAR_ORIGINE} demandes depuis une même origine en une heure : alerte" in texte
    assert f"{ECHECS_ADMIN_PAR_ADRESSE} échecs administrateur en 15 minutes : alerte" in texte


def test_la_fenetre_des_echecs_admin_vient_de_la_MEME_phrase_que_le_verrou_de_T5() -> None:
    """`T5` a pose 5 echecs et 15 minutes ; `T8` reemploie les deux memes nombres.

    Rien n'est invente : le test le prouve en comparant aux constantes de `T5`.
    """
    from app.auth.services import ECHECS_AVANT_VERROUILLAGE, MINUTES_DE_FENETRE_D_ECHECS

    assert ECHECS_ADMIN_PAR_ADRESSE == ECHECS_AVANT_VERROUILLAGE
    assert FENETRE_ECHECS_ADMIN == MINUTES_DE_FENETRE_D_ECHECS * 60


def test_la_fenetre_de_la_limitation_est_UNE_HEURE() -> None:
    """« par heure », litteralement."""
    assert FENETRE_DEMANDES_DE_LIEN == 3600


# ===========================================================================
#  Le comptage : la comparaison, et la minimisation
# ===========================================================================


def test_le_plafond_est_un_nombre_d_evenements_AUTORISES() -> None:
    """**`>` ET NON `>=`, ET LA DIFFERENCE EST DE UN.**

    « 10 demandes par heure » veut dire que la dixieme passe. `INCR` rendant la
    valeur deja incrementee, la dixieme demande rend 10 et la onzieme 11.
    """
    assert Comptage(valeur=9, plafond=10, secondes_restantes=60).depasse is False
    assert Comptage(valeur=10, plafond=10, secondes_restantes=60).depasse is False
    assert Comptage(valeur=11, plafond=10, secondes_restantes=60).depasse is True


def test_l_empreinte_EXIGE_une_cle() -> None:
    """Une cle vide produirait une empreinte non salee, reversible par enumeration.

    Le message nomme **ce que** la valeur represente, jamais la valeur.
    """
    with pytest.raises(ValueError, match="cle non vide") as capture:
        empreinte_minimisee("jean@exemple.fr", "", quoi="une adresse e-mail")
    assert "jean@exemple.fr" not in str(capture.value)


def test_l_empreinte_d_origine_DELEGUE_a_l_empreinte_minimisee() -> None:
    """Une seule implementation : deux fonctions HMAC voisines divergeraient.

    Si elles divergeaient, deux compteurs censes porter sur la meme valeur
    compteraient separement **en paraissant fonctionner**.
    """
    cle = "une-cle-de-test-suffisamment-longue"
    assert empreinte_d_origine("10.0.0.1", cle) == empreinte_minimisee(
        "10.0.0.1", cle, quoi="une adresse IP"
    )


def test_l_empreinte_est_STABLE_et_DISCRIMINANTE() -> None:
    cle = "une-cle-de-test-suffisamment-longue"
    a = empreinte_pour_le_debit("jean@exemple.fr", cle, quoi="une adresse e-mail")
    assert a == empreinte_pour_le_debit("jean@exemple.fr", cle, quoi="une adresse e-mail")
    assert a != empreinte_pour_le_debit("jeanne@exemple.fr", cle, quoi="une adresse e-mail")
    assert a != empreinte_pour_le_debit("jean@exemple.fr", cle + "x", quoi="une adresse e-mail")
    #  Hexadecimal : aucun caractere de separation ne peut collisionner avec un
    #  autre espace de noms Redis.
    assert re.fullmatch(r"[0-9a-f]{64}", a)


# ===========================================================================
#  Redis : l'atomicite, et le delai qui ne se repousse pas
# ===========================================================================


def _exiger_redis(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.REDIS_PORT):
        pytest.skip(
            "Redis absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def categorie_jetable(parametres_de_la_stack: Parametres) -> Iterator[str]:
    """Une categorie propre a ce test, purgee avant ET apres.

    **PURGEE AVANT AUSSI**, et c'est le defaut `T4-3` : une execution
    interrompue laisserait des compteurs, et la suivante echouerait sur un
    livrable conforme.
    """
    _exiger_redis(parametres_de_la_stack)
    nom = f"essai-{uuid.uuid4().hex[:12]}"
    purger(parametres_de_la_stack, categorie=nom)
    try:
        yield nom
    finally:
        purger(parametres_de_la_stack, categorie=nom)


@pytest.mark.integration
def test_INCR_rend_la_valeur_DEJA_incrementee(
    parametres_de_la_stack: Parametres, categorie_jetable: str
) -> None:
    """C'est ce qui rend la decision atomique : un seul aller-retour decide."""
    for attendu in (1, 2, 3):
        comptage = compter(
            parametres_de_la_stack,
            categorie=categorie_jetable,
            valeur_minimisee="a" * 64,
            plafond=10,
            fenetre_secondes=60,
        )
        assert comptage.valeur == attendu


@pytest.mark.integration
def test_le_delai_est_POSE_des_la_premiere_fois_et_JAMAIS_REPOUSSE(
    parametres_de_la_stack: Parametres, categorie_jetable: str
) -> None:
    """**LES DEUX DEFAUTS QUE `EXPIRE … NX` DANS UNE TRANSACTION EVITE.**

    Sans transaction, une mort du processus entre `INCR` et `EXPIRE` laisserait
    une cle **sans delai** : l'adresse serait bloquee definitivement. Sans `NX`,
    le delai serait repousse a chaque demande : un attaquant qui envoie une
    requete par minute maintiendrait la cle vivante **pour toujours**, et
    l'adresse d'un collaborateur legitime resterait bloquee.
    """
    premier = compter(
        parametres_de_la_stack,
        categorie=categorie_jetable,
        valeur_minimisee="b" * 64,
        plafond=10,
        fenetre_secondes=90,
    )
    #  Jamais -1 (« pas de delai ») ni -2 (« absente ») : la transaction pose les
    #  deux ensemble.
    assert 0 < premier.secondes_restantes <= 90
    #  Le second appel emploie une fenetre DEUX FOIS plus longue : si `NX`
    #  n'agissait pas, le delai restant augmenterait.
    second = compter(
        parametres_de_la_stack,
        categorie=categorie_jetable,
        valeur_minimisee="b" * 64,
        plafond=10,
        fenetre_secondes=180,
    )
    assert second.secondes_restantes <= premier.secondes_restantes


@pytest.mark.integration
def test_TEMOIN_DE_CONCURRENCE_dix_comptages_simultanes_donnent_DIX(
    parametres_de_la_stack: Parametres, categorie_jetable: str
) -> None:
    """**LE TEMOIN DU COMPARE-ET-POSE, CINQUIEME OCCURRENCE DU PATRON.**

    Lire puis ecrire laisserait dix demandes simultanees lire « 0 » et se croire
    toutes les premieres : le compteur avancerait de 1 au lieu de 10, et la
    limite n'arriverait jamais. Un test sequentiel est **aveugle** a ce
    defaut -- mesure quatre fois dans ce lot.

    Ce test ne dort pas : il lance dix appels de front et compare l'ensemble des
    valeurs rendues a l'ensemble attendu. Si deux appels rendaient la meme
    valeur, l'ensemble serait plus petit.
    """
    empreinte = "c" * 64

    def un_appel(_: int) -> int:
        return compter(
            parametres_de_la_stack,
            categorie=categorie_jetable,
            valeur_minimisee=empreinte,
            plafond=100,
            fenetre_secondes=60,
        ).valeur

    with ThreadPoolExecutor(max_workers=10) as executeur:
        valeurs = list(executeur.map(un_appel, range(10)))

    assert sorted(valeurs) == list(range(1, 11)), (
        f"dix comptages simultanes ont rendu {sorted(valeurs)} : "
        "deux valeurs identiques signifient que l'increment n'est pas atomique"
    )


@pytest.mark.integration
def test_LIRE_ne_compte_pas(parametres_de_la_stack: Parametres, categorie_jetable: str) -> None:
    """Le §20.2 compte des « echecs », non des tentatives : la lecture est separee."""
    compter(
        parametres_de_la_stack,
        categorie=categorie_jetable,
        valeur_minimisee="d" * 64,
        plafond=10,
        fenetre_secondes=60,
    )
    for _ in range(3):
        assert (
            lire(
                parametres_de_la_stack,
                categorie=categorie_jetable,
                valeur_minimisee="d" * 64,
                plafond=10,
            ).valeur
            == 1
        )


@pytest.mark.integration
def test_lire_une_cle_ABSENTE_rend_zero(
    parametres_de_la_stack: Parametres, categorie_jetable: str
) -> None:
    """Zero ne depasse pas : une adresse jamais vue n'est jamais refusee."""
    comptage = lire(
        parametres_de_la_stack, categorie=categorie_jetable, valeur_minimisee="e" * 64, plafond=5
    )
    assert comptage.valeur == 0
    assert comptage.secondes_restantes == 0
    assert comptage.depasse is False


@pytest.mark.integration
def test_REINITIALISER_efface(parametres_de_la_stack: Parametres, categorie_jetable: str) -> None:
    """Appelee sur succes : sans elle, un administrateur qui se trompe puis
    reussit resterait bloque quinze minutes.
    """
    compter(
        parametres_de_la_stack,
        categorie=categorie_jetable,
        valeur_minimisee="f" * 64,
        plafond=10,
        fenetre_secondes=60,
    )
    reinitialiser(parametres_de_la_stack, categorie=categorie_jetable, valeur_minimisee="f" * 64)
    assert (
        lire(
            parametres_de_la_stack,
            categorie=categorie_jetable,
            valeur_minimisee="f" * 64,
            plafond=10,
        ).valeur
        == 0
    )


@pytest.mark.integration
def test_la_categorie_CLOISONNE_les_compteurs(
    parametres_de_la_stack: Parametres, categorie_jetable: str
) -> None:
    """Sans elle, une adresse et une origine partageraient un compteur."""
    autre = f"{categorie_jetable}-bis"
    try:
        compter(
            parametres_de_la_stack,
            categorie=categorie_jetable,
            valeur_minimisee="g" * 64,
            plafond=10,
            fenetre_secondes=60,
        )
        assert (
            lire(
                parametres_de_la_stack, categorie=autre, valeur_minimisee="g" * 64, plafond=10
            ).valeur
            == 0
        )
    finally:
        purger(parametres_de_la_stack, categorie=autre)


@pytest.mark.integration
def test_PURGER_ne_touche_QUE_sa_categorie(
    parametres_de_la_stack: Parametres, categorie_jetable: str
) -> None:
    """Elle ne peut effacer ni une file Dramatiq ni une cle d'idempotence de `T7`."""
    autre = f"{categorie_jetable}-garde"
    try:
        compter(
            parametres_de_la_stack,
            categorie=autre,
            valeur_minimisee="h" * 64,
            plafond=10,
            fenetre_secondes=60,
        )
        compter(
            parametres_de_la_stack,
            categorie=categorie_jetable,
            valeur_minimisee="h" * 64,
            plafond=10,
            fenetre_secondes=60,
        )
        assert purger(parametres_de_la_stack, categorie=categorie_jetable) == 1
        assert (
            lire(
                parametres_de_la_stack, categorie=autre, valeur_minimisee="h" * 64, plafond=10
            ).valeur
            == 1
        )
    finally:
        purger(parametres_de_la_stack, categorie=autre)


def test_un_compteur_INJOIGNABLE_leve_plutot_que_de_deviner() -> None:
    """**ON NE DEVINE NI « SOUS LE SEUIL » NI « AU-DESSUS ».**

    Le premier laisserait une panne de Redis desactiver la protection ; le second
    refuserait tout le monde sans le dire. L'appelant tranche, et le §20.1 le
    fait par « refus par defaut ».

    Le message nomme la classe de l'erreur, **jamais l'URL de Redis** — qui porte
    un mot de passe.
    """
    parametres = Parametres.model_validate(
        {**VARIABLES_MINIMALES, "REDIS_HOST": HOTE_LOCAL, "REDIS_PORT": PORT_FERME}
    )
    with pytest.raises(CompteurIndisponible) as capture:
        compter(
            parametres,
            categorie="essai",
            valeur_minimisee="i" * 64,
            plafond=10,
            fenetre_secondes=60,
        )
    assert "injoignable" in str(capture.value)
    assert parametres.REDIS_PASSWORD not in str(capture.value)


# ===========================================================================
#  Les routes reelles — LE CRITERE, ET L'EGALITE QUE `T3` A OUVERTE
# ===========================================================================

DOMAINE_AUTORISE = "exalt-t8.test"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`.")


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
                    "VALUES (:a, :a, 'Debit', 'T8', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


def _appartenance(connexion: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    connexion.execute(
        text(
            "INSERT INTO entity_membership "
            "(person_id, entity_id, arrival_date, departure_date, membership_state, "
            " professional_category, profile_visibility) "
            "VALUES (:personne, :entite, current_date - 30, NULL, 'active', "
            "        'consultant', 'draft')"
        ),
        {"personne": personne, "entite": entite},
    )


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str]]:
    """Une adresse CONNUE et autorisee, un compte administrateur, et Redis propre.

    **LES TROIS CATEGORIES SONT PURGEES AVANT ET APRES.** Sans la purge d'avant,
    une execution interrompue laisserait des compteurs et la suivante echouerait
    sur un livrable conforme -- defaut `T4-3`. Sans celle d'apres, ce fichier
    ferait echouer les tests de `T3`, qui comptent les liens actifs.
    """
    _exiger_postgresql(parametres_de_la_stack)
    _exiger_redis(parametres_de_la_stack)
    from app.auth.mots_de_passe import ALGORITHME, hacher

    marqueur = f"t8api{uuid.uuid4().hex[:10]}"
    connue = f"{marqueur}.connue@{DOMAINE_AUTORISE}"
    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as connexion:
        entite = _entite(connexion, f"T8-{marqueur}")
        personne = _personne(connexion, connue)
        _appartenance(connexion, personne, entite)
        connexion.execute(
            text(
                "INSERT INTO allowed_email_domain "
                "(domain, entity_id, active, starts_at, ends_at) "
                "VALUES (:d, NULL, TRUE, now() - interval '30 days', NULL)"
            ),
            {"d": DOMAINE_AUTORISE},
        )
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
                " must_change) VALUES (:c, :h, :a, :params, now(), FALSE)"
            ),
            {
                "c": compte,
                "h": empreinte,
                "a": ALGORITHME,
                "params": _json.dumps(parametres_hachage),
            },
        )
    _purger_tout(parametres_de_la_stack)
    parametres = parametres_de_la_stack.model_copy(
        update={
            "PUBLIC_BASE_URL": ORIGINE_DE_TEST,
            #  Un hote SMTP injoignable : ce fichier eprouve la LIMITE, pas
            #  l'envoi -- et un echec d'envoi ne change pas la reponse depuis `T3`.
            "SMTP_HOST": HOTE_LOCAL,
            "SMTP_PORT": 1,
        }
    )
    try:
        yield parametres, connue, f"{marqueur}.inconnue@{DOMAINE_AUTORISE}"
    finally:
        _purger_tout(parametres_de_la_stack)
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
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
                "DELETE FROM entity_membership WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM entity WHERE code = :code",
                "DELETE FROM allowed_email_domain WHERE domain = :domaine",
                #  **AUCUN TYPE D'EVENEMENT N'EST NOMME ICI**, et c'est la lecon
                #  `T5-6` : `magic-link-check` nommait `MAGIC_LINK_REQUESTED` et
                #  a vieilli des que `T4` a ajoute `LOGIN_FAILURE`. Une trace
                #  sans personne echappe a tout nettoyage par identite ; seule la
                #  borne temporelle l'attrape, et elle ne vieillit pas.
                "DELETE FROM auth_event WHERE person_id IS NULL AND occurred_at >= :debut",
            ):
                menage.execute(
                    text(requete),
                    {
                        "motif": f"{marqueur}%",
                        "code": f"T8-{marqueur}",
                        "domaine": DOMAINE_AUTORISE,
                        "debut": debut,
                    },
                )


def _purger_tout(parametres: Parametres) -> None:
    for categorie in (
        CategorieDeCompteur.DEMANDE_DE_LIEN,
        CategorieDeCompteur.ORIGINE,
        CategorieDeCompteur.ECHEC_ADMIN,
    ):
        purger(parametres, categorie=categorie)


def _client(parametres: Parametres) -> TestClient:
    return TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST)


def _signature(reponse: Response) -> tuple[int, object, dict[str, str]]:
    """Ce qui doit etre IDENTIQUE entre deux refus, hors identifiant de correlation."""
    corps = reponse.json()
    if isinstance(corps, dict) and "erreur" in corps:
        corps = {**corps, "erreur": {**corps["erreur"], "identifiant_correlation": "IGNORE"}}
    return reponse.status_code, corps, {n.lower(): v for n, v in reponse.headers.items()}


def _demander(client: TestClient, parametres: Parametres, adresse: str) -> Response:
    reponse: Response = client.post(
        f"{parametres.API_PREFIX}/auth/magic-link", json={"email": adresse}
    )
    return reponse


@pytest.mark.integration
def test_LA_ONZIEME_DEMANDE_est_refusee_pour_une_adresse_CONNUE(
    decor: tuple[Parametres, str, str],
) -> None:
    """**LE CRITERE : « les limites produisent les resultats attendus ».**

    Les dix premieres passent -- c'est le temoin, sans lequel une route cassee
    donnerait la meme observation -- et la onzieme est refusee.
    """
    parametres, connue, _ = decor
    with _client(parametres) as client:
        for rang in range(DEMANDES_DE_LIEN_PAR_ADRESSE):
            reponse = _demander(client, parametres, connue)
            assert reponse.status_code == 202, f"la demande {rang + 1} aurait du passer"
        refus = _demander(client, parametres, connue)
    assert refus.status_code == 429
    assert refus.json()["erreur"]["code"] == "trop_de_demandes"
    assert refus.json()["erreur"]["details"]["secondes_avant_reprise"] > 0


@pytest.mark.integration
def test_LA_ONZIEME_DEMANDE_est_refusee_pour_une_adresse_INCONNUE(
    decor: tuple[Parametres, str, str],
) -> None:
    """**LE PIEGE PRINCIPAL DE `T8`, ET IL EST FERME ICI.**

    Si le compteur ne portait que sur les adresses connues -- en comptant par
    exemple les lignes de `magic_link_request`, qui n'existent que pour un profil
    actif et autorise -- alors une adresse inconnue ne serait JAMAIS limitee. Le
    429 dirait « ce compte existe », et l'oracle que `T3` a ferme serait rouvert.
    """
    parametres, _, inconnue = decor
    with _client(parametres) as client:
        for _ in range(DEMANDES_DE_LIEN_PAR_ADRESSE):
            assert _demander(client, parametres, inconnue).status_code == 202
        refus = _demander(client, parametres, inconnue)
    assert refus.status_code == 429


@pytest.mark.integration
def test_LES_DEUX_REFUS_SONT_IDENTIQUES_corps_ET_en_tetes(
    decor: tuple[Parametres, str, str],
) -> None:
    """**L'EGALITE, MESUREE COMME `T3` LA MESURAIT** : corps ET en-tetes.

    Un meme code 429 avec un corps ou un en-tete different trahirait l'existence
    du compte tout autant qu'un code different. Seuls `x-request-id` et `date`
    varient, et l'identifiant de correlation -- qui varie par construction.
    """
    parametres, connue, inconnue = decor
    with _client(parametres) as client:
        for adresse in (connue, inconnue):
            for _ in range(DEMANDES_DE_LIEN_PAR_ADRESSE):
                assert _demander(client, parametres, adresse).status_code == 202
        refus_connue = _signature(_demander(client, parametres, connue))
        refus_inconnue = _signature(_demander(client, parametres, inconnue))

    #  **CES DEUX ASSERTIONS SONT UN CORRECTIF, ET C'EST LE §7.0 PROPOSITION 4.**
    #
    #  Ma premiere version comparait seulement les deux signatures. Elle PASSAIT
    #  avec la limitation retiree du routeur -- mesure faite -- parce que deux
    #  reponses 202 sont identiques elles aussi : l'echec produisait exactement
    #  la meme observation que le succes. Le temoin negatif l'a dit en passant la
    #  ou il devait echouer, et c'est toujours le controle qui est en cause, pas
    #  le temoin.
    assert refus_connue[0] == 429, "l'adresse connue n'a PAS ete limitee"
    assert refus_inconnue[0] == 429, "l'adresse inconnue n'a PAS ete limitee"

    ecarts = [
        f"corps {refus_connue[1]!r} != {refus_inconnue[1]!r}"
        for _ in (1,)
        if refus_connue[1] != refus_inconnue[1]
    ]
    ecarts += (
        [f"code {refus_connue[0]} != {refus_inconnue[0]}"]
        if refus_connue[0] != refus_inconnue[0]
        else []
    )
    for nom in sorted((set(refus_connue[2]) | set(refus_inconnue[2])) - EN_TETES_VARIABLES):
        if refus_connue[2].get(nom) != refus_inconnue[2].get(nom):
            ecarts.append(
                f"en-tete {nom} : {refus_connue[2].get(nom)!r} != {refus_inconnue[2].get(nom)!r}"
            )
    assert not ecarts, f"la limitation revele l'existence du compte : {ecarts}"


@pytest.mark.integration
def test_VARIER_LA_CASSE_ne_contourne_PAS_la_limite(
    decor: tuple[Parametres, str, str],
) -> None:
    """L'adresse est normalisee AVANT d'etre comptee.

    Sans cela, `Jean@x.fr` et `jean@x.fr` auraient deux compteurs, et alterner la
    casse suffirait a doubler le plafond -- ou a le contourner entierement, une
    adresse ayant autant de graphies que de lettres.
    """
    parametres, _, inconnue = decor
    with _client(parametres) as client:
        for _ in range(DEMANDES_DE_LIEN_PAR_ADRESSE):
            assert _demander(client, parametres, inconnue).status_code == 202
        refus = _demander(client, parametres, inconnue.upper())
    assert refus.status_code == 429


@pytest.mark.integration
def test_DEUX_ADRESSES_DIFFERENTES_ont_des_compteurs_DISTINCTS(
    decor: tuple[Parametres, str, str],
) -> None:
    """**TEMOIN.** Sans lui, un compteur unique pour tout le monde passerait les
    tests de refus ci-dessus tout en bloquant la plateforme entiere.
    """
    parametres, connue, inconnue = decor
    with _client(parametres) as client:
        for _ in range(DEMANDES_DE_LIEN_PAR_ADRESSE):
            assert _demander(client, parametres, inconnue).status_code == 202
        assert _demander(client, parametres, inconnue).status_code == 429
        #  L'autre adresse n'a rien consomme.
        assert _demander(client, parametres, connue).status_code == 202


@pytest.mark.integration
def test_LA_SURVEILLANCE_D_ORIGINE_NE_REFUSE_JAMAIS(
    decor: tuple[Parametres, str, str],
) -> None:
    """**LE VERBE DU CAHIER, EPROUVE.** §20.2 : « 50 demandes depuis une meme
    origine en une heure : **alerte** », quand la ligne voisine dit
    « limitation ».

    Cinquante et une demandes depuis la meme origine, sur des adresses toutes
    differentes pour que la limitation par adresse ne s'en mele pas : **aucune
    n'est refusee**. Confondre les deux verbes bloquerait tout un bureau derriere
    un partage d'adresse.
    """
    parametres, _, inconnue = decor
    codes = set()
    with _client(parametres) as client:
        for rang in range(DEMANDES_PAR_ORIGINE + 1):
            codes.add(_demander(client, parametres, f"o{rang}.{inconnue}").status_code)
    assert codes == {202}, f"la surveillance d'origine a refuse : {sorted(codes)}"


@pytest.mark.integration
def test_LA_CONNEXION_ADMIN_est_refusee_apres_CINQ_echecs(
    decor: tuple[Parametres, str, str],
) -> None:
    """§20.2, « 5 echecs administrateur en 15 minutes ».

    Les cinq premiers echecs rendent 400 -- le refus generique de `T5`, qui ne
    distingue pas ses cinq causes -- et le sixieme rend 429.
    """
    parametres, connue, _ = decor
    with _client(parametres) as client:
        for rang in range(ECHECS_ADMIN_PAR_ADRESSE):
            reponse = client.post(
                f"{parametres.API_PREFIX}/auth/connexion",
                json={"email": connue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
            )
            assert reponse.status_code == 400, f"l'echec {rang + 1} aurait du rendre 400"
        refus = client.post(
            f"{parametres.API_PREFIX}/auth/connexion",
            json={"email": connue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
        )
    assert refus.status_code == 429


@pytest.mark.integration
def test_LA_CONNEXION_ADMIN_est_refusee_de_MEME_pour_une_adresse_INCONNUE(
    decor: tuple[Parametres, str, str],
) -> None:
    """**LE TROU DU VERROU DE `T5`, ET L'ORACLE QU'IL AURAIT OUVERT.**

    `failed_login_count` vit sur `user_account` : une adresse SANS compte n'a
    aucun compteur, donc peut etre sollicitee sans fin. Et si le compteur Redis
    ne portait QUE sur ces adresses, la sixieme tentative rendrait 429 pour une
    adresse inconnue et 400 pour une adresse connue : **le code HTTP deviendrait
    l'oracle**. Les deux rendent 429.
    """
    parametres, _, inconnue = decor
    with _client(parametres) as client:
        for _ in range(ECHECS_ADMIN_PAR_ADRESSE):
            reponse = client.post(
                f"{parametres.API_PREFIX}/auth/connexion",
                json={"email": inconnue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
            )
            assert reponse.status_code == 400
        refus = client.post(
            f"{parametres.API_PREFIX}/auth/connexion",
            json={"email": inconnue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
        )
    assert refus.status_code == 429


@pytest.mark.integration
def test_UN_SUCCES_EFFACE_le_compteur_d_echecs(decor: tuple[Parametres, str, str]) -> None:
    """**LE RISQUE NOMME AU §7 DE LA FICHE : « le verrouillage bloque Jonathan ».**

    Quatre echecs, une connexion reussie, puis un echec : le compteur repart de
    un, donc la reponse est 400 et non 429. Sans l'effacement, un administrateur
    qui se trompe puis reussit resterait refuse quinze minutes.

    Reussir exige le mot de passe : effacer ne donne rien a un attaquant.
    """
    parametres, connue, _ = decor
    with _client(parametres) as client:
        for _ in range(ECHECS_ADMIN_PAR_ADRESSE - 1):
            client.post(
                f"{parametres.API_PREFIX}/auth/connexion",
                json={"email": connue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
            )
        reussie = client.post(
            f"{parametres.API_PREFIX}/auth/connexion",
            json={"email": connue, "mot_de_passe": MOT_DE_PASSE},
        )
        assert reussie.status_code == 200
        #  Quatre echecs de plus : sans l'effacement, le total serait a huit et
        #  celui-ci rendrait 429.
        for _ in range(ECHECS_ADMIN_PAR_ADRESSE - 1):
            suivant = client.post(
                f"{parametres.API_PREFIX}/auth/connexion",
                json={"email": connue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
            )
            assert suivant.status_code == 400


@pytest.mark.integration
def test_REDIS_INJOIGNABLE_refuse_la_demande_au_lieu_de_la_laisser_passer(
    decor: tuple[Parametres, str, str],
) -> None:
    """**CAHIER §20.1, PREMIER PRINCIPE : « refus par defaut ».**

    Laisser passer ferait d'une panne de Redis le moyen de desactiver la
    protection. Le 503 est le code juste : la cause est une dependance
    indisponible, non la requete -- et `/health/ready` la nomme deja.
    """
    parametres, _, inconnue = decor
    sans_redis = parametres.model_copy(update={"REDIS_PORT": PORT_FERME})
    with _client(sans_redis) as client:
        reponse = _demander(client, sans_redis, inconnue)
    assert reponse.status_code == 503
    assert reponse.json()["erreur"]["code"] == "memoire_indisponible"


@pytest.mark.integration
def test_AUCUNE_CLE_REDIS_NE_PORTE_UNE_ADRESSE_NI_UNE_IP(
    decor: tuple[Parametres, str, str],
) -> None:
    """**LE SECOND CRITERE DE LA FICHE, LITTERALEMENT.**

    « la valeur minimisee `request_origin_hash` du §10.3 est employee, jamais une
    adresse IP brute ». Ce test le verifie sur les cles REELLEMENT posees dans
    Redis, non sur le code -- une lecture du code prouverait l'intention, pas le
    resultat.

    Il vaut aussi pour l'adresse e-mail, que le critere ne nommait pas : la
    mettre en clair dans Redis y placerait une donnee personnelle, dans un
    magasin qui n'a aucune politique de conservation.
    """
    parametres, connue, _ = decor
    with _client(parametres) as client:
        assert _demander(client, parametres, connue).status_code == 202
        client.post(
            f"{parametres.API_PREFIX}/auth/connexion",
            json={"email": connue, "mot_de_passe": MAUVAIS_MOT_DE_PASSE},
        )

    client_redis = redis.Redis.from_url(parametres.url_redis())
    cles = [
        c.decode("utf-8") if isinstance(c, bytes) else str(c)
        for c in client_redis.scan_iter(match=f"{PREFIXE_REDIS}*", count=500)
    ]
    assert cles, "aucune cle posee : le test ne prouverait rien"
    for cle in cles:
        assert "@" not in cle, f"une adresse e-mail figure en clair : {cle}"
        assert not re.search(r"\d{1,3}(\.\d{1,3}){3}", cle), (
            f"une adresse IP figure en clair : {cle}"
        )
        #  La partie variable est une empreinte hexadecimale de 64 caracteres.
        assert re.fullmatch(rf"{re.escape(PREFIXE_REDIS)}[a-z-]+:[0-9a-f]{{64}}", cle), cle
