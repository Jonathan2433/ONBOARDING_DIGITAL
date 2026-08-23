"""La liste des entites du portail national — story `MVP-L04-US001`.

LOT 4, sous-etape `T1`.

CE QUE CES TESTS PROUVENT, ET DANS QUEL ORDRE

  Le temoin CENTRAL vient d'abord : une entite `active` **est** rendue. Sans lui,
  les trois tests d'exclusion seraient tous satisfaits par une route qui ne rend
  jamais rien -- c'est la troisieme proposition du §7.0, et c'est la forme de
  defaut la plus facile a laisser passer.

TROIS ETATS NON ACTIFS, PAS DEUX

  `StatutEntite` declare `draft`, `active`, `suspended` et `archived`. Le critere
  de sortie de `T1` ecrit dans la fiche ne nomme que « `suspended` ou
  `archived` » : ce sont deux **exemples**. `draft` est le troisieme, et il a son
  temoin ici. §7.34, ecrit la veille de cette sous-etape.

LE NETTOYAGE EST BORNE PAR LE TEMPS AUTANT QUE PAR L'IDENTITE

  `T10` du LOT 3 a paye la lecon : un refus **sans acteur** -- ici un appel sans
  cookie -- produit une trace qu'aucun filtre par identite n'attrape. La borne
  temporelle est relevee AVANT tout, et `make residu-check` echoue si une ligne
  survit.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.sessions import ouvrir_une_session, revoquer
from app.configuration.settings import Parametres
from app.entities.modeles import STATUTS_ENTITE, StatutEntite
from app.entities.services import COLONNES_EXPOSEES
from app.main import creer_application
from app.shared.database import moteur

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

#  **HTTPS, ET CE N'EST PAS UN DETAIL.** Un cookie `Secure` n'est jamais renvoye
#  sur une origine en clair : la lecon est ecrite en tete de `test_sessions.py`, et
#  un test qui retirerait `Secure` pour passer ne prouverait rien de cet attribut.
ORIGINE_DE_TEST = "https://testserver"

CHEMIN = "/api/v1/entities"

#  Les quatre champs que la reponse doit porter, et EXACTEMENT ceux-la. Une
#  colonne ajoutee a la requete sans etre voulue ici fait echouer le test.
CHAMPS_ATTENDUS = frozenset({"id", "code", "nom", "ville"})


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


# ===========================================================================
#  Sans base : ce qui est verifiable a la lecture du code
# ===========================================================================


def test_les_QUATRE_etats_du_modele_sont_connus_de_ce_test() -> None:
    """**GARDE-FOU DE COUVERTURE.** Si un lot ajoute un cinquieme statut d'entite,
    ce test echoue et oblige a decider s'il est actif ou non.

    Sans lui, un statut nouveau serait silencieusement rendu ou silencieusement
    exclu selon le hasard de sa valeur -- et mes trois temoins d'exclusion
    continueraient de passer en ne couvrant plus la classe. C'est exactement le
    defaut du §7.34 : un motif ecrit contre les exemples connus.
    """
    assert set(STATUTS_ENTITE) == {"draft", "active", "suspended", "archived"}
    assert StatutEntite.ACTIVE.value == "active"


def test_les_colonnes_exposees_sont_declarees_une_seule_fois() -> None:
    """Les quatre colonnes SQL et les quatre champs de la reponse se correspondent.

    Les noms diffirent -- `display_name` devient `nom`, `city` devient `ville` --
    donc c'est le NOMBRE et l'intention qui sont compares, pas les libelles. Le
    test existe pour qu'une cinquieme colonne ajoutee a la requete ne parte pas
    dans la reponse sans decision.
    """
    assert COLONNES_EXPOSEES == ("id", "code", "display_name", "city")
    assert len(CHAMPS_ATTENDUS) == len(COLONNES_EXPOSEES)


# ===========================================================================
#  Avec PostgreSQL reel
# ===========================================================================


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, dict[str, str]]]:
    """Une personne, une session, et QUATRE entites — une par statut.

    Le nettoyage retire d'abord les traces sans acteur, bornees par le temps :
    un appel sans cookie n'est rattache a personne.
    """
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t1l4{uuid.uuid4().hex[:10]}"

    with moteur(parametres).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()

    codes: dict[str, str] = {}
    with moteur(parametres).begin() as cx:
        for statut in STATUTS_ENTITE:
            code = f"{marqueur}-{statut}"
            cx.execute(
                text(
                    "INSERT INTO entity "
                    "(code, display_name, city, country_code, status, timezone) "
                    "VALUES (:code, :nom, 'Bordeaux', 'FR', :statut, 'Europe/Paris')"
                ),
                {"code": code, "nom": f"Entite {statut} {marqueur}", "statut": statut},
            )
            codes[statut] = code

    try:
        yield parametres, marqueur, codes
    finally:
        with moteur(parametres).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM entity WHERE code LIKE :motif",
                #  Le refus sans acteur — un appel sans cookie — n'a ni personne
                #  ni compte de service. Seule la borne temporelle l'attrape.
                #  Sixieme occurrence de cette classe, §7.30.
                "DELETE FROM auth_event WHERE person_id IS NULL "
                "  AND service_account_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _session(parametres: Parametres, marqueur: str, suffixe: str = "") -> str:
    """Ouvrir une session reelle et rendre son jeton en clair."""
    adresse = f"{marqueur}{suffixe}@exalt-l4t1.test"
    with moteur(parametres).begin() as cx:
        personne = uuid.UUID(
            str(
                cx.execute(
                    text(
                        "INSERT INTO person "
                        "(email, email_normalized, first_name, last_name, account_state) "
                        "VALUES (:a, :a, 'Portail', 'T1', 'active') RETURNING id"
                    ),
                    {"a": adresse},
                ).scalar_one()
            )
        )
        jeton, _ = ouvrir_une_session(
            cx,
            personne=personne,
            instant=dt.datetime.now(tz=dt.UTC),
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
    return jeton


def _appeler(
    parametres: Parametres, jeton: str | None, entetes: dict[str, str] | None = None
) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN, headers=entetes or {})


def _signature(reponse: Any) -> tuple[int, Any, dict[str, str]]:
    """Tout ce que l'appelant peut observer : statut, corps ENTIER, en-tetes ENTIERS.

    **AUCUN CHAMP N'EST EXCLU, ET C'EST DELIBERE.** L'idiome du LOT 3 remplacait
    `identifiant_correlation` par une constante avant de comparer. Mesure du
    23/08/2026 : c'est le SEUL champ qui differait, en corps comme en en-tete
    `x-request-id`, et il suffit de **fixer** la correlation a l'appel pour que
    les deux reponses deviennent identiques a l'octet.

    Fixer vaut mieux qu'exclure : une exclusion laisse la porte ouverte a une
    difference qui se cacherait dans le champ exclu.
    """
    return (
        reponse.status_code,
        reponse.json(),
        {nom.lower(): valeur for nom, valeur in reponse.headers.items()},
    )


def _codes_rendus(charge: dict[str, Any]) -> set[str]:
    return {entite["code"] for entite in charge["entites"]}


@pytest.mark.integration
def test_une_entite_ACTIVE_est_rendue(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """**LE TEMOIN CENTRAL.** Sans lui, les trois exclusions seraient satisfaites
    par une route qui ne rend jamais rien.
    """
    parametres, marqueur, codes = decor
    reponse = _appeler(parametres, _session(parametres, marqueur))
    assert reponse.status_code == 200, reponse.text
    assert codes["active"] in _codes_rendus(reponse.json())


@pytest.mark.integration
@pytest.mark.parametrize("statut", ["draft", "suspended", "archived"])
def test_une_entite_NON_ACTIVE_n_est_PAS_rendue(
    decor: tuple[Parametres, str, dict[str, str]],
    statut: str,
) -> None:
    """Cahier §8.3 : « un acces a chaque entite ACTIVE ».

    **TROIS ETATS, non les deux que la fiche nomme.** `draft` est le troisieme, et
    une entite en brouillon proposee sur la page nationale serait exactement le
    defaut que le critere veut empecher.
    """
    parametres, marqueur, codes = decor
    reponse = _appeler(parametres, _session(parametres, marqueur))
    assert reponse.status_code == 200, reponse.text
    rendus = _codes_rendus(reponse.json())
    assert codes[statut] not in rendus
    #  Et l'active est bien la : sinon ce test passerait sur une reponse vide.
    assert codes["active"] in rendus


@pytest.mark.integration
def test_sans_cookie_la_route_REFUSE(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """Matrice §5 : `ANON` est a tiret sur « Page nationale et carte des entites »."""
    parametres, _, _ = decor
    reponse = _appeler(parametres, None)
    assert reponse.status_code == 401, reponse.text
    #  Aucune entite ne fuit dans le corps du refus.
    assert "entites" not in reponse.text


@pytest.mark.integration
def test_un_jeton_INCONNU_est_refuse_COMME_un_cookie_absent(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """**LES DEUX REFUS SONT COMPARES, pas seulement constates.**

    Cinq causes, une seule reponse : les distinguer apprendrait a un appelant
    qu'un jeton a existe. C'est l'egalite anti-enumeration de `T3` du LOT 3,
    transposee a une route metier.
    """
    parametres, _, _ = decor
    #  La correlation est FIXEE pour les deux appels : c'est ce qui rend la
    #  comparaison TOTALE plutot que partielle. Mesure a l'appui dans `_signature`.
    correlation = {"X-Request-ID": "l4t1-egalite-des-refus"}
    sans = _appeler(parametres, None, correlation)
    inconnu = _appeler(parametres, "oss_" + "0" * 43, correlation)
    assert sans.status_code == 401, sans.text
    #  L'egalite est verifiee APRES avoir exige 401 : deux reponses 200 seraient
    #  identiques elles aussi, et l'assertion passerait sur un livrable ouvert.
    #  C'est le defaut `T8-1` du LOT 3, et il avait fait passer mon test.
    assert _signature(sans) == _signature(inconnu)


@pytest.mark.integration
def test_une_session_REVOQUEE_est_refusee(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """La revocation de `T9` doit valoir sur les routes metier, pas seulement sur
    la route de session."""
    parametres, marqueur, _ = decor
    jeton = _session(parametres, marqueur, "-revoque")
    assert _appeler(parametres, jeton).status_code == 200
    with moteur(parametres).begin() as cx:
        assert revoquer(cx, jeton=jeton, instant=dt.datetime.now(tz=dt.UTC))
    assert _appeler(parametres, jeton).status_code == 401


@pytest.mark.integration
def test_la_reponse_porte_EXACTEMENT_quatre_champs(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """Ni `status`, ni `timezone`, ni `country_code`.

    `status` serait **constant** — toute ligne rendue est active — et un champ
    constant apprend a ne pas le lire.
    """
    parametres, marqueur, codes = decor
    charge = _appeler(parametres, _session(parametres, marqueur)).json()
    notre = next(e for e in charge["entites"] if e["code"] == codes["active"])
    assert set(notre) == CHAMPS_ATTENDUS, set(notre)


@pytest.mark.integration
def test_la_reponse_n_est_PAS_MISE_EN_CACHE(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """`Cache-Control: no-store`. Caddy est devant : sans cet en-tete, un
    mandataire partage pourrait servir a un second appelant la reponse du
    premier."""
    parametres, marqueur, _ = decor
    reponse = _appeler(parametres, _session(parametres, marqueur))
    assert reponse.headers.get("cache-control") == "no-store"


@pytest.mark.integration
def test_l_ORDRE_est_TOTAL_donc_reproductible(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """Deux entites de MEME nom d'affichage, codes differents.

    `ORDER BY display_name` seul laisserait PostgreSQL libre de les rendre dans un
    ordre different d'un appel a l'autre. Le tri porte aussi sur `code`, qui est
    UNIQUE : l'ordre devient total.
    """
    parametres, marqueur, _ = decor
    nom_partage = f"Homonyme {marqueur}"
    with moteur(parametres).begin() as cx:
        for suffixe in ("zzz", "aaa"):
            cx.execute(
                text(
                    "INSERT INTO entity "
                    "(code, display_name, city, country_code, status, timezone) "
                    "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris')"
                ),
                {"code": f"{marqueur}-{suffixe}", "nom": nom_partage},
            )

    jeton = _session(parametres, marqueur)
    ordres = []
    for _ in range(3):
        charge = _appeler(parametres, jeton).json()
        ordres.append([e["code"] for e in charge["entites"] if e["nom"] == nom_partage])

    assert ordres[0] == [f"{marqueur}-aaa", f"{marqueur}-zzz"], ordres[0]
    assert ordres[0] == ordres[1] == ordres[2]


@pytest.mark.integration
def test_la_lecture_RAFRAICHIT_l_activite_de_la_session(
    decor: tuple[Parametres, str, dict[str, str]],
) -> None:
    """**CE QUE LA DEPENDANCE DOCUMENTE, MESURE.**

    `exiger_une_session` reutilise `lire_et_rafraichir`, donc chaque lecture
    metier ecrit `last_activity_at`. C'est le reexamen que `DEC-531` renvoyait au
    LOT 4 : l'entorse du §7.4 ne disparait pas, elle se generalise. La mesurer
    vaut mieux que de l'affirmer.
    """
    parametres, marqueur, _ = decor
    jeton = _session(parametres, marqueur, "-activite")

    #  **AUCUN DECOR NE RECULE `last_activity_at`, ET C'EST LA BASE QUI L'A DIT.**
    #  Ma premiere version la reculait d'une heure pour se donner un ecart
    #  confortable : `ck_user_session_activite_apres_creation` l'a refusee, puisque
    #  l'activite serait devenue anterieure a la creation. C'est la classe `T9-1`
    #  du LOT 3 -- un defaut de decor de test attrape par une contrainte.
    #
    #  L'ecart naturel suffit : la session est ouverte dans une transaction, l'appel
    #  HTTP a lieu ensuite, et `now()` est l'instant de debut de transaction en
    #  microsecondes. Deux transactions distinctes ne peuvent pas le partager.
    with moteur(parametres).connect() as cx:
        avant = cx.execute(
            text(
                "SELECT last_activity_at FROM user_session "
                "WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE :m)"
            ),
            {"m": f"{marqueur}-activite%"},
        ).scalar_one()

    assert _appeler(parametres, jeton).status_code == 200

    with moteur(parametres).connect() as cx:
        apres = cx.execute(
            text(
                "SELECT last_activity_at FROM user_session "
                "WHERE person_id IN (SELECT id FROM person WHERE email_normalized LIKE :m)"
            ),
            {"m": f"{marqueur}-activite%"},
        ).scalar_one()

    assert apres > avant, f"avant={avant} apres={apres}"
