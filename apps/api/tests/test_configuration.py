"""Les onze garde-fous de demarrage.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT
    `docs/operations/politique-configuration-et-secrets.md` §6 : QUATRE
    controles dans tous les environnements, SEPT lorsque `APP_ENV=production`.
    Le cahier §20.3 exige un refus de demarrer.

DISCIPLINE APPLIQUEE ICI
    Chaque garde-fou a DEUX tests : un qui l'enfreint et verifie qu'il refuse,
    un temoin qui respecte la regle et verifie qu'il laisse passer. Un
    garde-fou qui refuse tout serait aussi inutile qu'un garde-fou qui accepte
    tout ; seuls les deux tests ensemble prouvent qu'il discrimine.

    Les sept derniers ne s'exercent qu'en forcant `APP_ENV=production` : en
    developpement, ils ne s'appliquent pas, et un test qui les eprouverait sans
    forcer cette valeur passerait sans rien verifier.
"""

from __future__ import annotations

from typing import Any

import pytest

# Import du conftest en module de premier niveau : pytest insere le repertoire
# de tests dans sys.path. `tests.conftest` echouerait, faute de __init__.py —
# volontairement absent, deux paquets homonymes `tests` ayant fait echouer mypy
# et pytest en T1 (defaut T1-2).
from conftest import VARIABLES_MINIMALES

from app.configuration.settings import (
    LONGUEUR_MINIMALE_CLE,
    ConfigurationInvalide,
    Parametres,
    charger_parametres,
)

CLE_VALIDE = "c" * LONGUEUR_MINIMALE_CLE


def construire(**surcharges: Any) -> Parametres:
    """Construire une configuration a partir du jeu minimal valide."""
    valeurs = dict(VARIABLES_MINIMALES)
    valeurs.update(surcharges)
    return Parametres(**valeurs)


def base_production(**surcharges: Any) -> Parametres:
    """Configuration de production par ailleurs conforme aux sept controles."""
    valeurs: dict[str, Any] = {
        "APP_ENV": "production",
        "APP_SECRET_KEY": CLE_VALIDE,
        "EMAIL_PROVIDER": "smtp",
        "API_DOCS_ENABLED": False,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_PROTECTION_ENABLED": True,
        "DB_AUTO_CREATE": False,
        "PUBLIC_BASE_URL": "https://onboarding.exalt-company.com",
    }
    valeurs.update(surcharges)
    return construire(**valeurs)


def motifs(parametres: Parametres) -> str:
    """Concatener les manquements, pour une recherche de sous-chaine lisible."""
    return " | ".join(parametres.controler())


# ============================================================================
#  Temoins d'ensemble
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
def test_une_configuration_minimale_de_developpement_est_acceptee() -> None:
    """Temoin positif global : sans lui, tous les tests d'echec ne prouveraient rien."""
    assert construire().controler() == []


@pytest.mark.usefixtures("environnement_vierge")
def test_une_configuration_de_production_conforme_est_acceptee() -> None:
    """Temoin positif du volet production."""
    assert base_production().controler() == []


# ============================================================================
#  Les QUATRE controles applicables a tous les environnements
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
@pytest.mark.parametrize("variable", sorted(VARIABLES_MINIMALES))
def test_1_une_variable_obligatoire_absente_refuse_le_demarrage(variable: str) -> None:
    """Garde-fou 1 : chacune des sept variables obligatoires est verifiee."""
    parametres = construire(**{variable: ""})
    assert f"{variable} : variable obligatoire absente" in motifs(parametres)


@pytest.mark.usefixtures("environnement_vierge")
def test_2_une_valeur_change_me_residuelle_refuse_le_demarrage() -> None:
    """Garde-fou 2 : aucune variable ne doit valoir encore CHANGE_ME_*."""
    parametres = construire(POSTGRES_PASSWORD="CHANGE_ME_MOT_DE_PASSE_POSTGRES")
    assert "POSTGRES_PASSWORD : valeur encore non renseignee" in motifs(parametres)


@pytest.mark.usefixtures("environnement_vierge")
def test_2bis_une_valeur_renseignee_ne_declenche_pas_le_garde_fou() -> None:
    """Temoin : le garde-fou 2 ne se declenche pas sur une valeur normale."""
    assert "non renseignee" not in motifs(construire())


@pytest.mark.usefixtures("environnement_vierge")
def test_3_un_entier_illisible_refuse_le_demarrage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garde-fou 3 : une valeur typee invalide refuse le demarrage.

    Le test passe par `charger_parametres()`, le POINT D'ENTREE REEL, et non par
    le constructeur. La premiere version de ce test appelait `Parametres(...)`
    directement : elle attendait `ConfigurationInvalide` et recevait la
    `ValidationError` brute de Pydantic. C'est `charger_parametres` qui traduit
    l'une en l'autre, pour que l'appelant n'ait qu'un seul cas a traiter — un
    test qui court-circuite le point d'entree ne prouve pas ce qu'il croit.
    """
    for nom, valeur in VARIABLES_MINIMALES.items():
        monkeypatch.setenv(nom, str(valeur))
    monkeypatch.setenv("POSTGRES_PORT", "pas-un-entier")
    with pytest.raises(ConfigurationInvalide) as capture:
        charger_parametres()
    assert "POSTGRES_PORT" in str(capture.value)


@pytest.mark.usefixtures("environnement_vierge")
def test_3bis_une_enumeration_hors_domaine_refuse_le_demarrage() -> None:
    """Garde-fou 3 : LOG_LEVEL hors de l'enumeration attendue."""
    parametres = construire(LOG_LEVEL="bavard")
    assert "LOG_LEVEL : valeur hors de l'enumeration" in motifs(parametres)


@pytest.mark.usefixtures("environnement_vierge")
def test_3ter_un_port_hors_plage_refuse_le_demarrage() -> None:
    """Garde-fou 3 : un port en dehors de 1-65535."""
    assert "POSTGRES_PORT : hors de la plage" in motifs(construire(POSTGRES_PORT=70000))


@pytest.mark.usefixtures("environnement_vierge")
def test_4_un_log_format_autre_que_json_refuse_le_demarrage() -> None:
    """Garde-fou 4 : LOG_FORMAT doit valoir json (cahier §28.1)."""
    assert "LOG_FORMAT : doit valoir json" in motifs(construire(LOG_FORMAT="text"))


@pytest.mark.usefixtures("environnement_vierge")
def test_4bis_log_format_json_ne_declenche_pas_le_garde_fou() -> None:
    """Temoin du garde-fou 4."""
    assert "LOG_FORMAT" not in motifs(construire(LOG_FORMAT="json"))


# ============================================================================
#  Les SEPT controles propres a APP_ENV=production
#
#  Ils sont eprouves en FORCANT APP_ENV=production. C'est indispensable : en
#  developpement ils ne s'appliquent pas, et les tester sans forcer cette
#  valeur donnerait sept tests qui passent sans rien verifier.
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
@pytest.mark.parametrize(
    ("surcharge", "attendu"),
    [
        ({"APP_SECRET_KEY": ""}, "APP_SECRET_KEY : absente ou plus courte"),
        ({"APP_SECRET_KEY": "trop-courte"}, "APP_SECRET_KEY : absente ou plus courte"),
        ({"EMAIL_PROVIDER": "mailpit"}, "EMAIL_PROVIDER : mailpit est interdit"),
        ({"API_DOCS_ENABLED": True}, "API_DOCS_ENABLED : doit valoir false"),
        ({"SESSION_COOKIE_SECURE": False}, "SESSION_COOKIE_SECURE : doit valoir true"),
        (
            {"CSRF_PROTECTION_ENABLED": False},
            "CSRF_PROTECTION_ENABLED : doit valoir true",
        ),
        ({"DB_AUTO_CREATE": True}, "DB_AUTO_CREATE : doit valoir false"),
        (
            {"PUBLIC_BASE_URL": "http://onboarding.exalt-company.com"},
            "PUBLIC_BASE_URL : doit commencer par https://",
        ),
    ],
)
def test_les_sept_controles_de_production_refusent_le_demarrage(
    surcharge: dict[str, Any], attendu: str
) -> None:
    """Chacun des sept controles de production refuse une valeur non conforme."""
    assert attendu in motifs(base_production(**surcharge))


@pytest.mark.usefixtures("environnement_vierge")
@pytest.mark.parametrize(
    "surcharge",
    [
        {"EMAIL_PROVIDER": "mailpit"},
        {"API_DOCS_ENABLED": True},
        {"SESSION_COOKIE_SECURE": False},
        {"CSRF_PROTECTION_ENABLED": False},
        {"DB_AUTO_CREATE": True},
        {"PUBLIC_BASE_URL": "http://localhost"},
        #  `{"APP_SECRET_KEY": ""}` A ETE RETIRE DE CETTE LISTE PAR `T7` DU LOT 3.
        #
        #  Elle n'etait obligatoire qu'en production. Depuis `T7`, elle est
        #  CONSOMMEE sans repli : le jeton anti-CSRF en est derive par HMAC, et
        #  `jeton_pour` leve sur une cle vide -- il n'existe pas de jeton
        #  « degrade » qui aurait un sens. Une cle vide est donc un manquement
        #  UNIVERSEL, et ce test avait raison d'echouer. §7.21.
        #
        #  Le cas est desormais couvert par
        #  `test_une_cle_secrete_vide_est_refusee_dans_TOUS_les_environnements`.
    ],
)
def test_les_controles_de_production_ne_sappliquent_pas_en_developpement(
    surcharge: dict[str, Any],
) -> None:
    """Temoin negatif du perimetre : hors production, ces valeurs sont admises.

    Sans ce test, un garde-fou applique a tous les environnements par erreur
    passerait inapercu — et rendrait le developpement local impossible, Mailpit
    et la documentation interactive y etant indispensables.
    """
    assert construire(APP_ENV="development", **surcharge).controler() == []


# ============================================================================
#  Confidentialite des messages
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
def test_aucun_message_ne_divulgue_une_valeur() -> None:
    """Le message nomme la variable fautive, JAMAIS sa valeur.

    Un message de configuration finit dans un journal, une capture d'ecran ou
    un ticket. La politique de secrets §6 l'exige explicitement.
    """
    # Deux valeurs distinctives, choisies pour ne pouvoir apparaitre dans aucun
    # message legitime. La premiere version de ce test cherchait « court », qui
    # est un fragment du message « plus courte que 32 caracteres » : le test
    # echouait sur son propre libelle, pas sur une fuite.
    mot_de_passe_temoin = "ZgQvTemoinMotDePasseQuiNeDoitPasFuiter"
    cle_temoin = "ZgQvTemoinCleTropCourte"
    parametres = base_production(
        APP_SECRET_KEY=cle_temoin,
        POSTGRES_PASSWORD=mot_de_passe_temoin,
        LOG_FORMAT="text",
    )
    rapport = motifs(parametres)
    assert mot_de_passe_temoin not in rapport
    assert cle_temoin not in rapport
    # Temoin positif : le rapport n'est pas vide, donc l'absence ci-dessus
    # signifie bien quelque chose.
    assert "APP_SECRET_KEY" in rapport
    assert "LOG_FORMAT" in rapport


@pytest.mark.usefixtures("environnement_vierge")
def test_l_exception_liste_tous_les_manquements_dun_coup() -> None:
    """Trois manquements simultanes sont tous rapportes.

    Corriger une configuration en decouvrant les erreurs une par une, redemarrage
    apres redemarrage, est un cout inutile.
    """
    parametres = base_production(
        APP_SECRET_KEY="",
        EMAIL_PROVIDER="mailpit",
        LOG_FORMAT="text",
    )
    manquements = parametres.controler()
    #  QUATRE, ET NON TROIS, DEPUIS `T7` DU LOT 3. Une cle vide declenche
    #  desormais DEUX garde-fous : celui des variables obligatoires — universel —
    #  et celui de la longueur en production. Les deux disent vrai, et les deux
    #  nomment la meme variable : l'operateur lit deux lignes pour un defaut, ce
    #  qui est verbeux mais jamais trompeur. Les fusionner ferait qu'un garde-fou
    #  masquerait l'autre.
    assert len(manquements) == 4, manquements
    erreur = ConfigurationInvalide(manquements)
    assert "4 garde-fou(s)" in str(erreur)


@pytest.mark.usefixtures("environnement_vierge")
def test_une_cle_secrete_vide_est_refusee_dans_TOUS_les_environnements() -> None:
    """**AJOUTE PAR `T7` DU LOT 3, ET IL REMPLACE UN CAS INVERSE.**

    `APP_SECRET_KEY` n'etait obligatoire qu'en production. Depuis `T7`, le jeton
    anti-CSRF en est derive par HMAC et `jeton_pour` **leve** sur une cle vide :
    il n'existe pas de jeton « degrade ». Une API demarree en developpement avec
    une cle vide rendrait donc 500 sur la route de session -- le defaut se
    manifesterait a la premiere connexion, **loin de sa cause**.

    C'est exactement ce qu'un garde-fou de demarrage existe pour eviter.
    """
    for environnement in ("development", "recette", "production"):
        manquements = construire(APP_ENV=environnement, APP_SECRET_KEY="").controler()
        assert any("APP_SECRET_KEY" in m for m in manquements), environnement
    #  Le temoin : une cle presente ne declenche rien en developpement.
    assert construire(APP_ENV="development").controler() == []
