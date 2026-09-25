"""La demande de magic link — story `MVP-L03-US001`, cahier §7.2, modele §10.3.

LOT 3, sous-etape `T3`.

LE CRITERE EST UNE EGALITE, ET C'EST CE QUI STRUCTURE CE FICHIER

  Un test qui verifierait « une adresse inconnue est refusee » prouverait le
  CONTRAIRE de ce que la story demande. `US001` exige que la reponse soit
  **identique** : c'est une egalite entre deux observations, pas un refus.

  La comparaison porte donc sur le **corps**, le **code** et les **en-tetes** --
  et elle porte son TEMOIN : un test exige que le comparateur signale deux
  reponses reellement differentes. Sans lui, un comparateur casse rendrait
  « identiques » sur tout, et les autres tests passeraient pour rien. C'est la
  quatrieme proposition du §7.0.

CHAQUE REGLE A DEUX TESTS : CELUI QUI L'ENFREINT, ET LE TEMOIN QUI LA RESPECTE

  Et pour les cinq conditions du cahier §7.2, le temoin ne se contente pas
  d'accepter un cas simple : il prouve que la condition **n'interdit pas ce que le
  corpus autorise**. Le cas decisif est le compte `user_account` ABSENT, qui doit
  etre accepte -- exiger son existence rendrait la feature inutilisable, aucun lot
  n'en creant aujourd'hui.

LE TEMPS EST INJECTE, JAMAIS ATTENDU

  Le §6 de la fiche du lot l'exige : un test qui dormirait quinze minutes serait
  inutilisable en integration continue. `demander_un_magic_link` recoit son
  `instant` en parametre, et un test verifie que la borne est **exactement**
  quinze minutes -- la contrainte en base exige l'egalite, pas un intervalle.

CE QUI TOURNE SANS LA STACK, ET CE QUI L'EXIGE

  Les tests de la reponse generique montent l'application avec `TestClient` et
  exigent PostgreSQL : le service ecrit reellement. Ils portent le marqueur
  `integration`. Ceux du jeton et du masquage n'exigent rien.
"""

from __future__ import annotations

import datetime as dt
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, VARIABLES_MINIMALES, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.jetons import (
    LONGUEUR_EMPREINTE,
    PREFIXE_MAGIC_LINK,
    empreinte_d_origine,
    empreinte_de_jeton,
    engendrer_jeton_magic_link,
    ressemble_a_un_jeton_magic_link,
)
from app.auth.modeles import (
    MINUTES_DE_VALIDITE_DU_MAGIC_LINK,
    EtatCompte,
    TypeCompte,
    TypeEvenementAuth,
)
from app.auth.routes import (
    MESSAGE_GENERIQUE,
    origine_de_la_requete,
)
from app.auth.services import (
    MOTIF_ADRESSE_INCONNUE,
    MOTIF_APPARTENANCE_NON_ACTIVE,
    MOTIF_COMPTE_NON_ACTIF,
    MOTIF_CONSOMME,
    MOTIF_DOMAINE_NON_AUTORISE,
    MOTIF_LIEN_EMIS,
    MOTIF_LIEN_REFUSE,
    MOTIF_PERSONNE_NON_ACTIVE,
    Consommation,
    Demande,
    consommer_un_magic_link,
    demander_un_magic_link,
)
from app.configuration.settings import (
    ConfigurationInvalide,
    Parametres,
    charger_parametres,
)
from app.main import creer_application
from app.shared.database import moteur
from observabilite.masquage import LONGUEUR_MINIMALE_D_ALEA

#  Un instant FIXE. Employer `now()` rendrait un test dependant de l'heure a
#  laquelle il tourne, et le §25.2 a deja montre que les bornes temporelles sont
#  le terrain le plus glissant du projet.
INSTANT = dt.datetime(2026, 8, 21, 10, 30, tzinfo=dt.UTC)

DOMAINE_AUTORISE = "exalt-t3.test"
DOMAINE_NON_AUTORISE = "ailleurs-t3.test"
BASE_PUBLIQUE = "https://app.onboarding.localhost"

#  Les en-tetes dont la variation est LEGITIME, et la liste est fermee.
#  `X-Request-ID` DOIT varier -- c'est un identifiant de correlation, cahier
#  §28.1. La liste est nommee ici plutot que devinee : c'est exactement
#  l'endroit ou une fuite pourrait se cacher.
EN_TETES_VARIABLES = frozenset({"x-request-id", "date"})

#  Bornes du test de concurrence. **LES DEUX VALEURS DOIVENT RESTER ECARTEES**,
#  et c'est un correctif : quand elles etaient egales, le `lock_timeout` de B et
#  le delai de la barriere s'affrontaient, et le test echouait une fois sur trois.
#  Un controle intermittent coute plus cher qu'un controle faux. Defaut `T4-4`.
DELAI_ATTENTE_VERROU = 10.0
VERROU_TIMEOUT_B = "60s"


# ===========================================================================
#  Le jeton — aucune dependance
# ===========================================================================


def test_un_jeton_porte_le_prefixe_et_assez_d_alea() -> None:
    """Sans prefixe, aucun detecteur ne pourrait etre exact plutot qu'heuristique."""
    jeton = engendrer_jeton_magic_link()
    assert jeton.startswith(PREFIXE_MAGIC_LINK)
    #  LA BORNE EST DERIVEE, JAMAIS RECOPIEE. Ecrire `>= 40` ici aurait cree une
    #  troisieme copie du nombre, a cote de la constante et du motif Gitleaks :
    #  §7.27, une liste ou une valeur recopiee vieillit au premier changement.
    #  Un jeton plus court que cette borne rendrait les deux detecteurs AVEUGLES.
    assert len(jeton) - len(PREFIXE_MAGIC_LINK) >= LONGUEUR_MINIMALE_D_ALEA


def test_deux_jetons_ne_sont_jamais_egaux() -> None:
    """Un jeton previsible serait un contournement d'authentification."""
    jetons = {engendrer_jeton_magic_link() for _ in range(200)}
    assert len(jetons) == 200


def test_l_empreinte_fait_exactement_soixante_quatre_hexadecimaux() -> None:
    """La colonne est bornee a cette longueur, et `make secrets-check` s'en sert."""
    empreinte = empreinte_de_jeton(engendrer_jeton_magic_link())
    assert len(empreinte) == LONGUEUR_EMPREINTE
    assert all(caractere in "0123456789abcdef" for caractere in empreinte)


def test_l_empreinte_ne_contient_JAMAIS_le_jeton() -> None:
    """Le temoin de l'evidence : une empreinte qui contiendrait sa source ne serait pas une."""
    jeton = engendrer_jeton_magic_link()
    assert jeton not in empreinte_de_jeton(jeton)
    assert PREFIXE_MAGIC_LINK not in empreinte_de_jeton(jeton)


def test_l_empreinte_d_origine_EXIGE_une_cle() -> None:
    """Sans cle, l'empreinte d'une adresse IPv4 se renverse en enumerant 2^32 valeurs.

    Elle ne serait donc pas une valeur minimisee, seulement une valeur qui en a
    l'air. Le refus est explicite plutot que silencieux.
    """
    with pytest.raises(ValueError, match="cle non vide"):
        empreinte_d_origine("203.0.113.7", "")


def test_l_empreinte_d_origine_depend_de_la_cle_ET_de_l_origine() -> None:
    """Le temoin : deux origines distinctes doivent donner deux empreintes distinctes.

    Sans ce test, une implementation qui rendrait une constante passerait le test
    precedent — et la limitation de debit de `T8` deviendrait un plafond global.
    """
    cle = "cle-de-test-sans-portee"
    autre = "autre-cle-de-test-sans-portee"
    assert empreinte_d_origine("203.0.113.7", cle) != empreinte_d_origine("203.0.113.8", cle)
    assert empreinte_d_origine("203.0.113.7", cle) != empreinte_d_origine("203.0.113.7", autre)
    assert len(empreinte_d_origine("203.0.113.7", cle)) == LONGUEUR_EMPREINTE


def test_le_detecteur_reconnait_un_jeton_REELLEMENT_engendre() -> None:
    """La lecon `T4-1` : un test de filtre enumere ce que CE projet produit.

    Un exemple de documentation aurait pu passer alors que la forme reelle ne
    passe pas -- c'est exactement ce qui etait arrive a `redis://:mdp@`.
    """
    assert ressemble_a_un_jeton_magic_link(engendrer_jeton_magic_link())


def test_le_detecteur_ne_crie_PAS_au_loup_sur_du_texte_ordinaire() -> None:
    """Un garde-fou a faux positifs est pire qu'aucun garde-fou — §7.25."""
    for anodin in (
        "une phrase parfaitement ordinaire sans aucun secret dedans",
        "oml_trop_court",
        "omlsansunderscore" + "a" * 50,
        "/api/v1/auth/magic-link",
        "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
    ):
        assert not ressemble_a_un_jeton_magic_link(anodin), anodin


# ===========================================================================
#  Le garde-fou de configuration
# ===========================================================================


def test_un_TTL_divergent_du_modele_REFUSE_le_demarrage() -> None:
    """La base impose quinze minutes : une variable a 20 ferait echouer l'insertion.

    Le garde-fou nomme la variable, ce que le message de PostgreSQL ne ferait
    pas -- il parlerait d'une contrainte dont l'operateur ignore le nom.
    """
    manquements = Parametres(**VARIABLES_MINIMALES, MAGIC_LINK_TTL_MINUTES=20).controler()
    assert any("MAGIC_LINK_TTL_MINUTES" in m for m in manquements), manquements
    #  Et la VALEUR fautive n'apparait pas : regle absolue du module de
    #  configuration, deja eprouvee par `test_aucun_message_ne_divulgue_une_valeur`.
    assert not any(" 20" in m for m in manquements), manquements


def test_la_fabrique_LEVE_sur_un_TTL_divergent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le temoin du chemin reel : `charger_parametres` refuse de rendre un objet.

    `controler()` seul rend une liste ; c'est `charger_parametres()` qu'uvicorn
    appelle, et c'est elle qui doit empecher le demarrage.
    """
    for nom, valeur in VARIABLES_MINIMALES.items():
        monkeypatch.setenv(nom, str(valeur))
    monkeypatch.setenv("MAGIC_LINK_TTL_MINUTES", "20")
    with pytest.raises(ConfigurationInvalide, match="MAGIC_LINK_TTL_MINUTES"):
        charger_parametres()


def test_le_TTL_du_modele_est_accepte() -> None:
    """Le temoin : le garde-fou ne refuse pas la valeur legitime."""
    parametres = Parametres(
        **VARIABLES_MINIMALES, MAGIC_LINK_TTL_MINUTES=MINUTES_DE_VALIDITE_DU_MAGIC_LINK
    )
    assert parametres.controler() == []


# ===========================================================================
#  L'origine de la requete
# ===========================================================================


class _RequeteFactice:
    """Le minimum dont `origine_de_la_requete` a besoin. Pas de client HTTP ici."""

    def __init__(self, en_tetes: dict[str, str], pair: str | None) -> None:
        self.headers = en_tetes
        self.client = type("_Pair", (), {"host": pair})() if pair else None


def test_l_origine_retient_le_DERNIER_element_de_x_forwarded_for() -> None:
    """Le premier element est fourni par le CLIENT, donc forgeable a volonte.

    S'en servir permettrait de contourner la limitation de debit de `T8` en
    changeant d'en-tete a chaque requete. Caddy AJOUTE l'adresse de son pair a la
    fin : c'est celle-la qui fait foi.
    """
    requete = _RequeteFactice(
        {"x-forwarded-for": "203.0.113.66, 198.51.100.9, 172.20.0.4"}, "172.20.0.4"
    )
    assert origine_de_la_requete(requete) == "172.20.0.4"  # type: ignore[arg-type]


def test_l_origine_retombe_sur_le_pair_sans_en_tete() -> None:
    """Le temoin : sans mandataire, l'adresse du pair est la seule disponible."""
    assert origine_de_la_requete(_RequeteFactice({}, "203.0.113.7")) == "203.0.113.7"  # type: ignore[arg-type]


def test_l_origine_vaut_None_quand_le_transport_n_en_donne_aucune() -> None:
    """Aucune valeur inventee : `None` est honnete, `0.0.0.0` serait une fiction."""
    assert origine_de_la_requete(_RequeteFactice({}, None)) is None  # type: ignore[arg-type]


# ===========================================================================
#  Le service et la route — PostgreSQL REEL
# ===========================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion en ROLLBACK : aucun test ne laisse de ligne derriere lui.

    Le role est celui de l'EXECUTION, comme l'API : un droit manquant a
    l'execution ferait donc echouer ces tests, ce qui est l'effet recherche.
    """
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


def _personne(connexion: Connection, adresse: str, *, etat: str = "active") -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO person "
                    "(email, email_normalized, first_name, last_name, account_state) "
                    "VALUES (:affichage, :normalisee, 'Test', 'T3', :etat) RETURNING id"
                ),
                {
                    "affichage": adresse,
                    "normalisee": adresse.lower(),
                    "etat": etat,
                },
            ).scalar_one()
        )
    )


def _appartenance(
    connexion: Connection, personne: uuid.UUID, entite: uuid.UUID, *, etat: str = "active"
) -> None:
    """Une appartenance dans l'etat demande.

    **`departed` EXIGE UNE DATE DE DEPART**, et ma premiere version l'omettait :
    la contrainte `ck_entity_membership_depart_date_si_departed`, posee en `T4` du
    LOT 2, l'a refusee. Defaut `T3-1`, et c'est la base qui a fait son travail --
    un decor de test qui contourne une contrainte du modele n'eprouve pas le
    modele.

    **ET LA DATE DE DEPART EST DERIVEE DE LA MEME REFERENCE QUE L'ARRIVEE.**
    Elle valait `dt.date(2026, 8, 20)` -- une date ABSOLUE -- contre une arrivee
    a `current_date - 30`, qui BOUGE. Le 20/09/2026, `current_date - 30` a
    depasse le 20/08, l'arrivee est passee APRES le depart, et la periode
    `daterange` du §25.2 est devenue invalide : « range lower bound must be less
    than or equal to range upper bound ». Une bombe a retardement, posee sans le
    savoir et explosee sur du code que personne n'avait touche.

    **Les deux bornes viennent donc du MEME `current_date`**, si bien qu'aucune
    date du calendrier ne peut les inverser. C'est le §7.0, sixieme proposition,
    applique au temps : deux grandeurs qu'une contrainte compare doivent venir
    de la meme source.
    """
    connexion.execute(
        text(
            "INSERT INTO entity_membership "
            "(person_id, entity_id, arrival_date, departure_date, membership_state, "
            " professional_category, profile_visibility) "
            "VALUES (:personne, :entite, current_date - 30, "
            "        CASE WHEN :depart THEN current_date - 10 END, :etat, "
            "        'consultant', 'draft')"
        ),
        {
            "personne": personne,
            "entite": entite,
            "etat": etat,
            #  **DERIVE, JAMAIS ABSOLU** : `current_date - 10` tombe toujours
            #  APRES `current_date - 30`, quelle que soit la date du jour.
            "depart": etat == "departed",
        },
    )


def _compte(connexion: Connection, personne: uuid.UUID, *, type_compte: str, etat: str) -> None:
    """Un `user_account` dans l'etat demande.

    **`failed_login_count` ET `state` SONT NOMMEES EXPLICITEMENT**, et ce n'est pas
    du zele : leurs defauts sont declares COTE PYTHON (`default=`), non
    `server_default`. Un `INSERT` en SQL brut ne les recoit donc pas, et la
    colonne `NOT NULL` refuse la ligne. Defaut `T3-2`.

    **`T5` rencontrera exactement cela** en creant des comptes administrateurs :
    `must_change` de `admin_password_credential` est dans le meme cas.
    """
    connexion.execute(
        text(
            "INSERT INTO user_account (person_id, account_type, state, failed_login_count) "
            "VALUES (:personne, :type_compte, :etat, 0)"
        ),
        {"personne": personne, "type_compte": type_compte, "etat": etat},
    )


def _domaine(
    connexion: Connection,
    domaine: str,
    *,
    entite: uuid.UUID | None = None,
    actif: bool = True,
    debut: dt.datetime | None = None,
    fin: dt.datetime | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, active, starts_at, ends_at) "
            "VALUES (:domaine, :entite, :actif, :debut, :fin)"
        ),
        {
            "domaine": domaine,
            "entite": entite,
            "actif": actif,
            "debut": debut or (INSTANT - dt.timedelta(days=30)),
            "fin": fin,
        },
    )


def _decor(
    connexion: Connection,
    *,
    marqueur: str,
    etat_personne: str = "active",
    etat_appartenance: str = "active",
    domaine: str = DOMAINE_AUTORISE,
    domaine_autorise: bool = True,
) -> str:
    """Une entite, une personne, son appartenance, et le domaine — puis l'adresse."""
    entite = _entite(connexion, f"T3-{marqueur}")
    adresse = f"{marqueur}@{domaine}"
    personne = _personne(connexion, adresse, etat=etat_personne)
    _appartenance(connexion, personne, entite, etat=etat_appartenance)
    if domaine_autorise:
        _domaine(connexion, domaine)
    return adresse


def _demander(connexion: Connection, adresse: str, *, instant: dt.datetime = INSTANT) -> Demande:
    return demander_un_magic_link(
        connexion, adresse=adresse, instant=instant, base_publique=BASE_PUBLIQUE
    )


# --- Les cinq conditions du cahier §7.2, chacune avec son temoin -------------


@pytest.mark.integration
def test_un_profil_ACTIF_recoit_un_lien(cx: Connection) -> None:
    """LE TEMOIN CENTRAL. Sans lui, tous les refus ci-dessous seraient satisfaits
    par un service qui ne rendrait JAMAIS de lien -- et l'egalite des reponses
    serait vraie et sans valeur.
    """
    adresse = _decor(cx, marqueur="actif")
    demande = _demander(cx, adresse)
    assert demande.motif == MOTIF_LIEN_EMIS
    assert demande.lien is not None
    assert demande.destinataire == adresse
    assert demande.lien.startswith(f"{BASE_PUBLIQUE}/connexion/lien?token={PREFIXE_MAGIC_LINK}")


@pytest.mark.integration
def test_une_adresse_INCONNUE_ne_produit_aucun_lien(cx: Connection) -> None:
    """Cahier §7.2 : « la personne doit deja exister dans PostgreSQL »."""
    demande = _demander(cx, f"jamais-vue-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}")
    assert demande.motif == MOTIF_ADRESSE_INCONNUE
    assert demande.lien is None
    assert demande.personne is None


@pytest.mark.integration
def test_une_personne_NON_ACTIVE_ne_recoit_AUCUN_lien(cx: Connection) -> None:
    """Modele §10.3 : « Personne **active** existante ». Exister ne suffit pas."""
    adresse = _decor(cx, marqueur="suspendue", etat_personne="suspended")
    demande = _demander(cx, adresse)
    assert demande.motif == MOTIF_PERSONNE_NON_ACTIVE
    assert demande.lien is None


@pytest.mark.integration
def test_un_profil_ARCHIVE_ne_recoit_AUCUN_lien(cx: Connection) -> None:
    """**LE CONTROLE §30.11 DU MODELE**, et le cahier §23.2 l'ecrit aussi.

    « Un profil archive ne recoit pas de magic link ». Le §6.2 nomme
    `entity_membership` le « profil », et `archived` est l'un de ses quatre etats.
    """
    adresse = _decor(cx, marqueur="archive", etat_appartenance="archived")
    demande = _demander(cx, adresse)
    assert demande.motif == MOTIF_APPARTENANCE_NON_ACTIVE
    assert demande.lien is None


@pytest.mark.integration
@pytest.mark.parametrize("etat", ["future", "departed", "archived"])
def test_les_TROIS_etats_non_actifs_sont_tous_ecartes(cx: Connection, etat: str) -> None:
    """Le cahier §7.2 exige « active », donc les trois autres etats sont ecartes.

    Tester le seul `archived` laisserait croire que le filtre nomme cet etat. Il
    exige l'etat actif, ce qui est plus fort et couvre les trois.
    """
    adresse = _decor(cx, marqueur=f"etat-{etat}", etat_appartenance=etat)
    assert _demander(cx, adresse).motif == MOTIF_APPARTENANCE_NON_ACTIVE


@pytest.mark.integration
def test_un_domaine_NON_AUTORISE_ne_recoit_AUCUN_lien(cx: Connection) -> None:
    """Cahier §7.2 : « son adresse doit appartenir a un domaine autorise »."""
    adresse = _decor(
        cx, marqueur="hors-domaine", domaine=DOMAINE_NON_AUTORISE, domaine_autorise=False
    )
    demande = _demander(cx, adresse)
    assert demande.motif == MOTIF_DOMAINE_NON_AUTORISE
    assert demande.lien is None


@pytest.mark.integration
def test_un_domaine_DESACTIVE_ne_recoit_AUCUN_lien(cx: Connection) -> None:
    """Modele §5.4 : `active` « controle l'usage lors de l'authentification ».

    La ligne EXISTE : c'est l'interrupteur seul qui refuse. Sans ce test, un
    service qui ignorerait `active` passerait le test precedent.
    """
    entite = _entite(cx, "T3-domaine-off")
    adresse = f"domaine-off@{DOMAINE_AUTORISE}"
    _appartenance(cx, _personne(cx, adresse), entite)
    _domaine(cx, DOMAINE_AUTORISE, actif=False)
    assert _demander(cx, adresse).motif == MOTIF_DOMAINE_NON_AUTORISE


@pytest.mark.integration
def test_un_domaine_HORS_DE_SA_PERIODE_ne_recoit_AUCUN_lien(cx: Connection) -> None:
    """Le §5.4 demande `active` ET la periode. Retenir la seule `active` laisserait
    un domaine expire autoriser une connexion.
    """
    entite = _entite(cx, "T3-domaine-expire")
    adresse = f"domaine-expire@{DOMAINE_AUTORISE}"
    _appartenance(cx, _personne(cx, adresse), entite)
    _domaine(
        cx,
        DOMAINE_AUTORISE,
        actif=True,
        debut=INSTANT - dt.timedelta(days=60),
        fin=INSTANT - dt.timedelta(days=1),
    )
    assert _demander(cx, adresse).motif == MOTIF_DOMAINE_NON_AUTORISE


@pytest.mark.integration
def test_un_domaine_LOCAL_autorise_SON_entite(cx: Connection) -> None:
    """Le temoin du domaine local : `entity_id` non nul autorise CETTE entite."""
    entite = _entite(cx, "T3-domaine-local")
    adresse = f"domaine-local@{DOMAINE_AUTORISE}"
    _appartenance(cx, _personne(cx, adresse), entite)
    _domaine(cx, DOMAINE_AUTORISE, entite=entite)
    assert _demander(cx, adresse).motif == MOTIF_LIEN_EMIS


@pytest.mark.integration
def test_un_domaine_LOCAL_n_autorise_PAS_une_AUTRE_entite(cx: Connection) -> None:
    """Le §2.5 pose le refus par defaut. L'inverse ferait d'un domaine local un
    domaine global en silence -- une fuite qui paraitrait fonctionner.
    """
    autre = _entite(cx, "T3-domaine-autre")
    entite = _entite(cx, "T3-domaine-mien")
    adresse = f"domaine-croise@{DOMAINE_AUTORISE}"
    _appartenance(cx, _personne(cx, adresse), entite)
    _domaine(cx, DOMAINE_AUTORISE, entite=autre)
    assert _demander(cx, adresse).motif == MOTIF_DOMAINE_NON_AUTORISE


@pytest.mark.integration
@pytest.mark.parametrize("etat", [EtatCompte.LOCKED.value, EtatCompte.DISABLED.value])
def test_un_compte_EXISTANT_et_non_actif_refuse_le_lien(cx: Connection, etat: str) -> None:
    """La cinquieme condition, DERIVEE du §10.1 et declaree dans `services.py`.

    Un compte `locked` ou `disabled` qui recevrait quand meme des liens rendrait
    la colonne `state` sans effet -- or `T5` s'en servira pour le verrouillage et
    `T9` pour la revocation.
    """
    entite = _entite(cx, f"T3-compte-{etat}")
    adresse = f"compte-{etat}@{DOMAINE_AUTORISE}"
    personne = _personne(cx, adresse)
    _appartenance(cx, personne, entite)
    _domaine(cx, DOMAINE_AUTORISE)
    _compte(cx, personne, type_compte=TypeCompte.EMPLOYEE_MAGIC_LINK.value, etat=etat)
    assert _demander(cx, adresse).motif == MOTIF_COMPTE_NON_ACTIF


@pytest.mark.integration
def test_un_compte_ABSENT_n_est_PAS_un_refus(cx: Connection) -> None:
    """**LE TEMOIN DE L'ASYMETRIE, ET C'EST LE PLUS IMPORTANT DES CINQ.**

    `magic_link_request` reference `person_id`, JAMAIS `user_account_id`, et aucun
    lot ne cree aujourd'hui de ligne `user_account`. Exiger son existence serait
    exiger plus que le modele et rendrait la feature inutilisable -- le defaut du
    §7.20.
    """
    adresse = _decor(cx, marqueur="sans-compte")
    assert (
        cx.execute(
            text(
                "SELECT count(*) FROM user_account u JOIN person p ON p.id = u.person_id "
                "WHERE p.email_normalized = :adresse"
            ),
            {"adresse": adresse},
        ).scalar_one()
        == 0
    )
    assert _demander(cx, adresse).motif == MOTIF_LIEN_EMIS


@pytest.mark.integration
def test_un_compte_ADMIN_LOCAL_non_actif_ne_bloque_PAS_le_magic_link(cx: Connection) -> None:
    """Le §10.1 permet DEUX comptes distincts. Un compte administrateur verrouille
    ne dit rien du compte employe : confondre les deux verrouillerait l'un par
    l'autre. C'est le contresens que `T7` et `T8` du LOT 2 ont appris a eviter.
    """
    entite = _entite(cx, "T3-admin-verrouille")
    adresse = f"admin-verrouille@{DOMAINE_AUTORISE}"
    personne = _personne(cx, adresse)
    _appartenance(cx, personne, entite)
    _domaine(cx, DOMAINE_AUTORISE)
    _compte(
        cx,
        personne,
        type_compte=TypeCompte.ADMIN_LOCAL.value,
        etat=EtatCompte.DISABLED.value,
    )
    assert _demander(cx, adresse).motif == MOTIF_LIEN_EMIS


# --- L'emission : invalidation, expiration, empreinte -----------------------


@pytest.mark.integration
def test_une_seconde_demande_INVALIDE_la_premiere(cx: Connection) -> None:
    """Modele §10.3 : « le dernier lien invalide les precedents encore actifs ».

    Et l'index partiel de `T2` REFUSERAIT l'insertion sans cette invalidation :
    ce test echouerait par une erreur d'integrite, non par une assertion.
    """
    adresse = _decor(cx, marqueur="deux-demandes")
    premier = _demander(cx, adresse)
    second = _demander(cx, adresse, instant=INSTANT + dt.timedelta(minutes=1))
    assert premier.lien != second.lien

    lignes = (
        cx.execute(
            text(
                "SELECT m.invalidated_at IS NULL FROM magic_link_request m "
                "JOIN person p ON p.id = m.person_id "
                "WHERE p.email_normalized = :adresse ORDER BY m.requested_at"
            ),
            {"adresse": adresse},
        )
        .scalars()
        .all()
    )
    #  Deux lignes, et une SEULE encore active. Compter les lignes sans compter
    #  les actives laisserait passer une invalidation qui n'aurait rien fait.
    assert list(lignes) == [False, True]


@pytest.mark.integration
def test_l_expiration_est_EXACTEMENT_quinze_minutes(cx: Connection) -> None:
    """La contrainte `expiration_a_quinze_minutes` exige l'EGALITE, pas un
    intervalle. Le temps est INJECTE : aucun test ne dort.
    """
    adresse = _decor(cx, marqueur="expiration")
    _demander(cx, adresse)
    demande_a, expire_a = cx.execute(
        text(
            "SELECT m.requested_at, m.expires_at FROM magic_link_request m "
            "JOIN person p ON p.id = m.person_id WHERE p.email_normalized = :adresse"
        ),
        {"adresse": adresse},
    ).one()
    assert expire_a - demande_a == dt.timedelta(minutes=MINUTES_DE_VALIDITE_DU_MAGIC_LINK)
    assert demande_a == INSTANT


@pytest.mark.integration
def test_la_base_ne_porte_QUE_l_empreinte_du_jeton(cx: Connection) -> None:
    """Modele §10.3 : « Hash uniquement ». Le jeton du lien ne doit apparaitre
    dans AUCUNE colonne.
    """
    adresse = _decor(cx, marqueur="empreinte")
    demande = _demander(cx, adresse)
    assert demande.lien is not None
    jeton = demande.lien.split("token=")[1]

    (empreinte,) = cx.execute(
        text(
            "SELECT m.token_hash FROM magic_link_request m "
            "JOIN person p ON p.id = m.person_id WHERE p.email_normalized = :adresse"
        ),
        {"adresse": adresse},
    ).one()
    assert empreinte == empreinte_de_jeton(jeton)
    assert jeton not in empreinte
    #  Et le TEMOIN d'exhaustivite : aucune colonne texte de la ligne ne porte le
    #  jeton. Verifier la seule colonne attendue laisserait passer une fuite dans
    #  `request_origin_hash` ou dans le `detail` de l'audit.
    tout = cx.execute(
        text(
            "SELECT m::text, e::text FROM magic_link_request m "
            "JOIN person p ON p.id = m.person_id "
            "LEFT JOIN auth_event e ON e.person_id = p.id "
            "WHERE p.email_normalized = :adresse"
        ),
        {"adresse": adresse},
    ).one()
    assert PREFIXE_MAGIC_LINK not in str(tout)


@pytest.mark.integration
def test_l_empreinte_d_origine_est_STOCKEE_quand_elle_est_fournie(cx: Connection) -> None:
    """`T8` en aura besoin. Une colonne laissee nulle par `T3` serait
    inexploitable retroactivement.
    """
    adresse = _decor(cx, marqueur="origine")
    attendue = empreinte_d_origine("172.20.0.4", "cle-de-test-sans-portee")
    demander_un_magic_link(
        cx,
        adresse=adresse,
        instant=INSTANT,
        base_publique=BASE_PUBLIQUE,
        empreinte_origine=attendue,
    )
    stockee = cx.execute(
        text(
            "SELECT m.request_origin_hash FROM magic_link_request m "
            "JOIN person p ON p.id = m.person_id WHERE p.email_normalized = :adresse"
        ),
        {"adresse": adresse},
    ).scalar_one()
    assert stockee == attendue


# --- L'audit ---------------------------------------------------------------


@pytest.mark.integration
def test_une_adresse_INCONNUE_est_tracee_SANS_personne(cx: Connection) -> None:
    """`T2` a pose `auth_event.person_id` nullable exactement pour ce cas.

    Un echec sur une adresse inconnue doit pouvoir etre trace sans rattacher
    l'evenement a une personne inexistante.
    """
    avant = cx.execute(
        text(
            "SELECT count(*) FROM auth_event "
            "WHERE person_id IS NULL AND event_type = 'MAGIC_LINK_REQUESTED'"
        )
    ).scalar_one()
    _demander(cx, f"inconnue-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}")
    apres = cx.execute(
        text(
            "SELECT count(*) FROM auth_event "
            "WHERE person_id IS NULL AND event_type = 'MAGIC_LINK_REQUESTED'"
        )
    ).scalar_one()
    assert apres == avant + 1


@pytest.mark.integration
def test_l_audit_ne_porte_JAMAIS_l_adresse_demandee(cx: Connection) -> None:
    """Le §10.6 exclut les donnees sensibles, et consigner une adresse ABSENTE de
    la base creerait une donnee personnelle que la plateforme n'avait pas.
    """
    inconnue = f"a-ne-pas-consigner-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}"
    _demander(cx, inconnue)
    lignes = (
        cx.execute(text("SELECT e::text FROM auth_event e WHERE e.person_id IS NULL"))
        .scalars()
        .all()
    )
    assert all(inconnue not in ligne for ligne in lignes)


@pytest.mark.integration
def test_chaque_motif_de_refus_est_trace_avec_sa_personne(cx: Connection) -> None:
    """Un refus non trace serait un acces refuse dont rien ne garde le souvenir."""
    adresse = _decor(cx, marqueur="refus-trace", etat_appartenance="archived")
    _demander(cx, adresse)
    detail = cx.execute(
        text(
            "SELECT e.detail FROM auth_event e JOIN person p ON p.id = e.person_id "
            "WHERE p.email_normalized = :adresse"
        ),
        {"adresse": adresse},
    ).scalar_one()
    assert detail == MOTIF_APPARTENANCE_NON_ACTIVE


# ===========================================================================
#  LA REPONSE GENERIQUE — l'egalite, et son temoin
# ===========================================================================


def _application(parametres: Parametres) -> TestClient:
    return TestClient(creer_application(parametres))


def _reponses(
    parametres: Parametres, adresses: list[str]
) -> list[tuple[int, bytes, dict[str, str]]]:
    """POST sur la route pour chaque adresse, et rendre de quoi comparer."""
    obtenues: list[tuple[int, bytes, dict[str, str]]] = []
    with _application(parametres) as client:
        for adresse in adresses:
            reponse = client.post("/api/v1/auth/magic-link", json={"email": adresse})
            obtenues.append(
                (
                    reponse.status_code,
                    reponse.content,
                    {nom.lower(): valeur for nom, valeur in reponse.headers.items()},
                )
            )
    return obtenues


def _ecarts(
    gauche: tuple[int, bytes, dict[str, str]], droite: tuple[int, bytes, dict[str, str]]
) -> list[str]:
    """Tout ce qui distingue deux reponses, hors en-tetes legitimement variables."""
    ecarts: list[str] = []
    if gauche[0] != droite[0]:
        ecarts.append(f"code {gauche[0]} != {droite[0]}")
    if gauche[1] != droite[1]:
        ecarts.append(f"corps {gauche[1]!r} != {droite[1]!r}")
    for nom in sorted((set(gauche[2]) | set(droite[2])) - EN_TETES_VARIABLES):
        if gauche[2].get(nom) != droite[2].get(nom):
            ecarts.append(f"en-tete {nom} : {gauche[2].get(nom)!r} != {droite[2].get(nom)!r}")
    return ecarts


@pytest.fixture
def stack_avec_domaine(parametres_de_la_stack: Parametres) -> Iterator[Parametres]:
    """Un decor PERSISTANT, parce que la route ouvre sa propre transaction.

    Les autres tests roulent en `rollback` sur leur propre connexion ; la route,
    elle, valide la sienne. Le decor doit donc etre visible d'une AUTRE connexion,
    et il est retire a la fin — y compris ce que la route a ecrit.
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t3api{uuid.uuid4().hex[:10]}"
    active = f"{marqueur}.active@{DOMAINE_AUTORISE}"
    archivee = f"{marqueur}.archivee@{DOMAINE_AUTORISE}"
    #  L'INSTANT DE DEPART EST RELEVE AVANT TOUT, ET C'EST UN CORRECTIF.
    #
    #  Les evenements d'audit d'une adresse INCONNUE n'ont ni personne, ni
    #  adresse : ils ne peuvent donc pas porter le marqueur, et ma premiere
    #  version les laissait en base. Dix-huit lignes residuelles ont fait
    #  ECHOUER deux tests de `T2`, qui comptent `auth_event` sans filtre.
    #  Defaut `T3-3`. Le borne temporelle est ce qui les rend supprimables sans
    #  toucher a autre chose.
    with moteur(parametres_de_la_stack).connect() as connexion:
        debut = connexion.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as connexion:
        entite = _entite(connexion, f"T3-{marqueur}")
        _appartenance(connexion, _personne(connexion, active), entite)
        _appartenance(connexion, _personne(connexion, archivee), entite, etat="archived")
        _domaine(connexion, DOMAINE_AUTORISE)
    try:
        yield parametres_de_la_stack.model_copy(
            update={
                #  Un hote SMTP volontairement injoignable : ce bloc de tests
                #  eprouve la REPONSE, pas l'envoi. Et l'echec d'envoi ne doit
                #  precisement RIEN changer a la reponse -- c'est le test
                #  `test_un_echec_d_envoi_ne_change_PAS_la_reponse`.
                "SMTP_HOST": "127.0.0.1",
                "SMTP_PORT": 1,
            }
        )
    finally:
        with moteur(parametres_de_la_stack).begin() as connexion:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM magic_link_request WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM entity_membership WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM entity WHERE code = :code",
                "DELETE FROM allowed_email_domain WHERE domain = :domaine",
                #  Les evenements SANS personne, bornes a cette execution.
                "DELETE FROM auth_event WHERE person_id IS NULL "
                "  AND event_type = 'MAGIC_LINK_REQUESTED' AND occurred_at >= :debut",
            ):
                connexion.execute(
                    text(requete),
                    {
                        "motif": f"{marqueur}%",
                        "code": f"T3-{marqueur}",
                        "domaine": DOMAINE_AUTORISE,
                        "debut": debut,
                    },
                )


@pytest.mark.integration
def test_la_reponse_est_IDENTIQUE_pour_une_adresse_connue_et_inconnue(
    stack_avec_domaine: Parametres,
) -> None:
    """**LE CRITERE DE `US001`, ET C'EST UNE EGALITE.**

    La comparaison porte sur le corps, le code ET les en-tetes. Le seul code HTTP
    ne prouverait rien : deux reponses peuvent porter le meme 202 et des corps
    differents.
    """
    marqueur = _adresse_active(stack_avec_domaine)
    connue, inconnue = _reponses(
        stack_avec_domaine, [marqueur, f"jamais-vue-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}"]
    )
    assert _ecarts(connue, inconnue) == []
    assert connue[0] == 202
    assert MESSAGE_GENERIQUE.encode("utf-8") in connue[1]


@pytest.mark.integration
def test_la_reponse_est_IDENTIQUE_pour_un_profil_archive(
    stack_avec_domaine: Parametres,
) -> None:
    """§30.11 — le refus ne doit pas se lire dans la reponse.

    Un profil archive existe : distinguer son cas de celui d'une adresse inconnue
    revelerait qu'un compte existe, ce qui est precisement l'enumeration que
    `US001` interdit.
    """
    active = _adresse_active(stack_avec_domaine)
    archivee = active.replace(".active@", ".archivee@")
    r_active, r_archivee = _reponses(stack_avec_domaine, [active, archivee])
    assert _ecarts(r_active, r_archivee) == []


@pytest.mark.integration
def test_les_SEULS_en_tetes_qui_varient_sont_ceux_qui_le_DOIVENT(
    stack_avec_domaine: Parametres,
) -> None:
    """La liste d'exclusion est EXIGEE, pas supposee.

    C'est exactement l'endroit ou une fuite pourrait se cacher : un en-tete
    ajoute sur un seul des deux chemins disparaitrait de la comparaison s'il
    suffisait de l'exclure sans le nommer.
    """
    active = _adresse_active(stack_avec_domaine)
    gauche, droite = _reponses(
        stack_avec_domaine, [active, f"jamais-vue-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}"]
    )
    varies = {
        nom for nom in set(gauche[2]) | set(droite[2]) if gauche[2].get(nom) != droite[2].get(nom)
    }
    assert varies <= EN_TETES_VARIABLES, f"en-tetes inattendus : {sorted(varies)}"
    #  Et `X-Request-ID` DOIT varier : s'il ne variait pas, la correlation du
    #  cahier §28.1 serait cassee, ce qui est un autre defaut.
    assert "x-request-id" in varies


@pytest.mark.integration
def test_TEMOIN_le_comparateur_sait_ECHOUER(stack_avec_domaine: Parametres) -> None:
    """**Sans ce temoin, les trois tests precedents ne prouvent rien.**

    Un comparateur casse rendrait « aucun ecart » sur deux reponses reellement
    differentes, et les egalites ci-dessus passeraient pour rien. C'est la
    quatrieme proposition du §7.0.
    """
    active = _adresse_active(stack_avec_domaine)
    with _application(stack_avec_domaine) as client:
        generique = client.post("/api/v1/auth/magic-link", json={"email": active})
        malformee = client.post("/api/v1/auth/magic-link", json={"pas_le_champ": 1})
    gauche = (
        generique.status_code,
        generique.content,
        {n.lower(): v for n, v in generique.headers.items()},
    )
    droite = (
        malformee.status_code,
        malformee.content,
        {n.lower(): v for n, v in malformee.headers.items()},
    )
    assert malformee.status_code == 422
    assert _ecarts(gauche, droite) != []


@pytest.mark.integration
def test_une_adresse_FANTAISISTE_recoit_la_MEME_reponse(
    stack_avec_domaine: Parametres,
) -> None:
    """Aucune validation de forme sur l'adresse, et c'est deliberé.

    Un 422 sur une adresse « mal formee » donnerait a un attaquant un premier
    oracle -- « cette forme est acceptable » -- avant le second. Une saisie
    fantaisiste suit donc le meme chemin qu'une adresse inconnue.
    """
    active = _adresse_active(stack_avec_domaine)
    reference, fantaisiste, vide = _reponses(
        stack_avec_domaine, [active, "pas-du-tout-une-adresse", ""]
    )
    assert _ecarts(reference, fantaisiste) == []
    assert _ecarts(reference, vide) == []


@pytest.mark.integration
def test_un_echec_d_envoi_ne_change_PAS_la_reponse(stack_avec_domaine: Parametres) -> None:
    """**SI L'ENVOI POUVAIT CHANGER LA REPONSE, LA PANNE SERAIT L'ORACLE.**

    Le decor pointe volontairement sur un SMTP injoignable. Une adresse connue
    rendrait alors 500 quand une inconnue rendrait 202 : l'enumeration
    redeviendrait possible le jour d'une panne de messagerie.
    """
    active = _adresse_active(stack_avec_domaine)
    connue, inconnue = _reponses(
        stack_avec_domaine, [active, f"jamais-vue-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}"]
    )
    assert connue[0] == 202
    assert _ecarts(connue, inconnue) == []


@pytest.mark.integration
def test_la_route_ecrit_REELLEMENT_un_lien_pour_la_connue_et_aucun_pour_l_inconnue(
    stack_avec_domaine: Parametres,
) -> None:
    """L'egalite des reponses serait vraie et VIDE si rien ne se passait jamais.

    Ce test est le temoin de l'egalite : il prouve que les deux chemins font des
    choses differentes tout en repondant la meme chose.
    """
    active = _adresse_active(stack_avec_domaine)
    inconnue = f"jamais-vue-{uuid.uuid4().hex[:8]}@{DOMAINE_AUTORISE}"
    _reponses(stack_avec_domaine, [active, inconnue])
    with moteur(stack_avec_domaine).connect() as connexion:
        actifs = connexion.execute(
            text(
                "SELECT count(*) FROM magic_link_request m JOIN person p ON p.id = m.person_id "
                "WHERE p.email_normalized = :adresse "
                "  AND m.used_at IS NULL AND m.invalidated_at IS NULL"
            ),
            {"adresse": active},
        ).scalar_one()
        inconnues = connexion.execute(
            text("SELECT count(*) FROM person WHERE email_normalized = :adresse"),
            {"adresse": inconnue},
        ).scalar_one()
    assert actifs == 1
    assert inconnues == 0


@pytest.mark.integration
def test_un_corps_trop_long_est_refuse_sans_toucher_a_la_base(
    stack_avec_domaine: Parametres,
) -> None:
    """La borne ne depend QUE de la requete, jamais du contenu de la base.

    Elle protege d'un corps sans limite, et son refus ne revele rien.
    """
    with _application(stack_avec_domaine) as client:
        reponse = client.post(
            "/api/v1/auth/magic-link", json={"email": "a" * 321 + "@exemple.test"}
        )
    assert reponse.status_code == 422


def _adresse_active(parametres: Parametres) -> str:
    """Retrouver l'adresse active du decor, sans la recopier depuis la fixture."""
    with moteur(parametres).connect() as connexion:
        return str(
            connexion.execute(
                text(
                    "SELECT email_normalized FROM person "
                    "WHERE email_normalized LIKE 't3api%.active@%' "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            ).scalar_one()
        )


# ===========================================================================
#  LA CONSOMMATION — LOT 3, sous-etape `T4`, story `MVP-L03-US002`
# ===========================================================================
#
#  TROIS PROPRIETES, ET LA TROISIEME EST CELLE QU'ON OUBLIE
#
#    1. usage unique         un second usage echoue
#    2. expiration           un lien de 16 minutes echoue, un de 15 passe encore
#    3. **ATOMICITE**        deux requetes CONCURRENTES portant le meme jeton ne
#                            peuvent pas reussir toutes les deux
#
#  La troisieme n'est pas un raffinement. Un service qui LIRAIT `used_at` puis
#  ecrirait laisserait deux requetes simultanees passer la lecture avant que l'une
#  n'ecrive : le lien serait consomme deux fois, et **un lien de connexion
#  rejouable est un contournement d'authentification**. Les tests 1 et 2
#  passeraient pourtant sans rien dire.
#
#  Elle s'eprouve sur DEUX connexions reelles, et le resultat est deterministe :
#  PostgreSQL verrouille la ligne au premier `UPDATE`, la seconde transaction
#  attend le `COMMIT`, puis ne trouve plus de ligne a mettre a jour.


def _lien(cx: Connection, adresse: str, *, instant: dt.datetime = INSTANT) -> str:
    """Emettre un lien et rendre le JETON qu'il porte."""
    demande = _demander(cx, adresse, instant=instant)
    assert demande.lien is not None, f"aucun lien emis : {demande.motif}"
    return demande.lien.split("token=")[1]


def _consommer(cx: Connection, jeton: str, *, instant: dt.datetime = INSTANT) -> Consommation:
    return consommer_un_magic_link(cx, jeton=jeton, instant=instant)


@pytest.mark.integration
def test_un_lien_VALIDE_est_consomme(cx: Connection) -> None:
    """LE TEMOIN CENTRAL. Sans lui, tous les refus ci-dessous seraient satisfaits
    par une fonction qui refuserait TOUT.
    """
    adresse = _decor(cx, marqueur="conso-ok")
    consommation = _consommer(cx, _lien(cx, adresse))
    assert consommation.motif == MOTIF_CONSOMME
    assert consommation.reussie
    assert consommation.personne is not None


@pytest.mark.integration
def test_un_SECOND_usage_echoue(cx: Connection) -> None:
    """§10.3 : « usage unique ». Le critere litteral de `US002`."""
    adresse = _decor(cx, marqueur="conso-deux-fois")
    jeton = _lien(cx, adresse)
    assert _consommer(cx, jeton).reussie
    seconde = _consommer(cx, jeton)
    assert seconde.motif == MOTIF_LIEN_REFUSE
    assert seconde.personne is None


@pytest.mark.integration
def test_un_lien_de_SEIZE_minutes_echoue(cx: Connection) -> None:
    """§10.3 : « 15 minutes apres emission ». Le temps est INJECTE, aucun test ne dort."""
    adresse = _decor(cx, marqueur="conso-16min")
    jeton = _lien(cx, adresse)
    tard = INSTANT + dt.timedelta(minutes=MINUTES_DE_VALIDITE_DU_MAGIC_LINK + 1)
    assert _consommer(cx, jeton, instant=tard).motif == MOTIF_LIEN_REFUSE


@pytest.mark.integration
def test_un_lien_de_QUATORZE_minutes_passe_encore(cx: Connection) -> None:
    """Le temoin de la borne : elle ne doit pas etre plus stricte que le modele.

    Sans lui, une expiration a cinq minutes passerait le test precedent — et le
    livrable serait plus severe que le §10.3, ce qui est le defaut du §7.20.
    """
    adresse = _decor(cx, marqueur="conso-14min")
    jeton = _lien(cx, adresse)
    tot = INSTANT + dt.timedelta(minutes=MINUTES_DE_VALIDITE_DU_MAGIC_LINK - 1)
    assert _consommer(cx, jeton, instant=tot).reussie


@pytest.mark.integration
def test_la_borne_est_SEMI_OUVERTE_a_quinze_minutes_pile(cx: Connection) -> None:
    """A l'instant EXACT de l'expiration, le lien est expire.

    Le §10.3 dit « 15 minutes apres emission » sans trancher l'inclusion. La
    convention du socle -- plages semi-ouvertes `[debut, fin)` -- est appliquee,
    et **elle est declaree ici** plutot que laissee au hasard d'un `>` ou d'un
    `>=` : un lecteur doit pouvoir savoir lequel des deux a ete choisi.
    """
    adresse = _decor(cx, marqueur="conso-15pile")
    jeton = _lien(cx, adresse)
    pile = INSTANT + dt.timedelta(minutes=MINUTES_DE_VALIDITE_DU_MAGIC_LINK)
    assert _consommer(cx, jeton, instant=pile).motif == MOTIF_LIEN_REFUSE


@pytest.mark.integration
def test_un_lien_INVALIDE_par_une_nouvelle_demande_echoue(cx: Connection) -> None:
    """§10.3 : « le dernier lien invalide les precedents encore actifs ».

    C'est le troisieme critere de `US002`, et il relie les deux sous-etapes : `T3`
    pose `invalidated_at`, `T4` doit le RESPECTER. Un service qui ne regarderait
    que `used_at` accepterait un lien pourtant remplace.
    """
    adresse = _decor(cx, marqueur="conso-invalide")
    ancien = _lien(cx, adresse)
    nouveau = _lien(cx, adresse, instant=INSTANT + dt.timedelta(minutes=1))
    assert ancien != nouveau
    assert _consommer(cx, ancien).motif == MOTIF_LIEN_REFUSE
    #  Et le temoin : le NOUVEAU passe. Sans lui, une implementation qui
    #  refuserait les deux passerait le test.
    assert _consommer(cx, nouveau, instant=INSTANT + dt.timedelta(minutes=2)).reussie


@pytest.mark.integration
def test_un_jeton_INCONNU_echoue(cx: Connection) -> None:
    """Aucune ligne ne porte cette empreinte."""
    assert _consommer(cx, engendrer_jeton_magic_link()).motif == MOTIF_LIEN_REFUSE


@pytest.mark.integration
def test_un_jeton_FANTAISISTE_echoue_sans_lever(cx: Connection) -> None:
    """Le porteur controle entierement cette valeur : elle ne doit provoquer
    aucune exception, seulement un refus.
    """
    for fantaisiste in ("", "pas-un-jeton", "oml_", "'; DROP TABLE person; --"):
        assert _consommer(cx, fantaisiste).motif == MOTIF_LIEN_REFUSE


@pytest.mark.integration
def test_les_QUATRE_causes_de_refus_rendent_le_MEME_motif(cx: Connection) -> None:
    """Un seul gabarit d'echec — derivation declaree, §3 de la fiche du lot.

    `T11` ne prevoit qu'UN ecran pour « lien expire ou consomme ». Ce test exige
    que les quatre causes soient **indistinguables**, et il les enumere : sans
    l'enumeration, il pourrait n'en avoir examine qu'une.
    """
    adresse = _decor(cx, marqueur="conso-quatre")

    consomme = _lien(cx, adresse)
    _consommer(cx, consomme)

    expire = _lien(cx, adresse, instant=INSTANT + dt.timedelta(minutes=1))
    tard = INSTANT + dt.timedelta(minutes=30)

    remplace = _lien(cx, adresse, instant=INSTANT + dt.timedelta(minutes=2))
    _lien(cx, adresse, instant=INSTANT + dt.timedelta(minutes=3))

    causes = {
        "inconnu": _consommer(cx, engendrer_jeton_magic_link()),
        "deja_consomme": _consommer(cx, consomme),
        "expire": _consommer(cx, expire, instant=tard),
        "remplace": _consommer(cx, remplace, instant=INSTANT + dt.timedelta(minutes=4)),
    }
    assert len(causes) == 4, "les quatre causes doivent toutes etre exercees"
    assert {c.motif for c in causes.values()} == {MOTIF_LIEN_REFUSE}
    assert {c.personne for c in causes.values()} == {None}


@pytest.mark.integration
def test_la_consommation_est_ATOMIQUE_sous_CONCURRENCE(
    parametres_de_la_stack: Parametres,
) -> None:
    """**LE SCENARIO QUI DISCRIMINE, ET IL A FALLU DEUX ESSAIS POUR L'ECRIRE.**

    Un service qui LIRAIT `used_at` puis ecrirait laisserait deux requetes
    simultanees passer la lecture avant que l'une n'ecrive : le lien serait
    consomme DEUX fois, et **un lien de connexion rejouable est un contournement
    d'authentification**. Les tests d'usage unique et d'expiration passeraient
    pourtant sans rien dire.

    **DEUX VERSIONS DE CE TEST N'ONT RIEN PROUVE, ET C'EST INSTRUCTIF.**

      La premiere validait A **avant** de lancer B : purement sequentielle, donc
      equivalente au test « un second usage echoue ». Defaut `T4-1`.

      La seconde bornait B par un `lock_timeout` court et exigeait qu'elle echoue
      sur le verrou. **Elle ne discriminait pas davantage** : un service qui lit
      puis ecrit prend le MEME verrou au moment d'ecrire, donc il aurait produit
      exactement la meme observation. Defaut `T4-2`, et c'est la quatrieme
      proposition du §7.0 -- *un controle dont l'echec produirait la meme
      observation que le succes ne prouve rien.*

    **CE QUI DISCRIMINE EST QUE B ATTENDE, PUIS REPRENNE :**

      1. A consomme, tient le verrou, **ne valide pas** ;
      2. B, dans un fil, tente de consommer -> elle **attend** le verrou ;
      3. A valide. B reprend, et c'est LA que les deux implementations divergent :
           - compare-et-pose : la clause `WHERE` est reevaluee apres l'obtention
             du verrou, `used_at` n'est plus nul, **0 ligne** -> REFUS ;
           - lire-puis-ecrire : la lecture avait deja conclu « eligible », et
             l'ecriture n'a plus de garde -> **SUCCES**, donc double consommation.
      4. **TEMOIN** : sur un AUTRE lien, non verrouille, B reussit.

    **AUCUNE ATTENTE ARBITRAIRE.** La barriere de l'etape 2 n'est pas un `sleep` :
    une troisieme connexion interroge `pg_stat_activity` jusqu'a voir un backend
    reellement en attente de verrou. C'est une condition observee, pas un delai
    espere -- et elle est bornee, pour qu'un echec soit un echec et non un blocage
    de l'integration continue.
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t4race{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@{DOMAINE_AUTORISE}"
    autre_adresse = f"{marqueur}.temoin@{DOMAINE_AUTORISE}"

    #  Le decor est VALIDE, non annule : les connexions concurrentes doivent voir
    #  la meme ligne, ce qu'un `rollback` partage rendrait impossible.
    with moteur(parametres_de_la_stack).begin() as preparation:
        entite = _entite(preparation, f"T4-{marqueur}")
        _appartenance(preparation, _personne(preparation, adresse), entite)
        _appartenance(preparation, _personne(preparation, autre_adresse), entite)
        _domaine(preparation, DOMAINE_AUTORISE)
        jeton = _lien(preparation, adresse)
        jeton_temoin = _lien(preparation, autre_adresse)

    resultats: dict[str, Consommation] = {}
    erreurs: list[BaseException] = []

    #  L'INSTANT DE DEPART, POUR LE NETTOYAGE. Le refus de B ecrit un
    #  `LOGIN_FAILURE` dont `person_id` est NUL -- c'est voulu, un jeton refuse ne
    #  designe personne -- et **le marqueur ne peut donc pas l'atteindre**. Sans
    #  cette borne, une ligne restait en base a chaque execution. Defaut `T4-5`,
    #  et c'est la meme classe que `T3-3` : la troisieme fois que la trace d'un
    #  refus sans personne echappe a un nettoyage.
    #
    #  Le filtre porte sur `created_at`, non sur `occurred_at` : `occurred_at`
    #  vaut l'instant INJECTE du test, qui n'a rien a voir avec l'heure reelle.
    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()

    pret = threading.Event()

    def consommer_dans_un_fil() -> None:
        """B : sa propre connexion, et un `lock_timeout` GENEREUX.

        Genereux et non court : le but est qu'elle ATTENDE puis reprenne, pas
        qu'elle abandonne. Il existe malgre tout pour qu'un verrou jamais relache
        fasse echouer le test au lieu de le suspendre.

        **IL DOIT RESTER TRES SUPERIEUR A `DELAI_ATTENTE_VERROU`.** Quand les deux
        etaient egaux, B abandonnait pile au moment ou la barriere renoncait, et
        le test echouait une fois sur trois -- defaut `T4-4`.
        """
        connexion = moteur(parametres_de_la_stack).connect()
        try:
            with connexion.begin():
                connexion.execute(text(f"SET LOCAL lock_timeout = '{VERROU_TIMEOUT_B}'"))
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
                resultats["b"] = consommer_un_magic_link(connexion, jeton=jeton, instant=INSTANT)
        except BaseException as erreur:
            erreurs.append(erreur)
            #  Sinon la barriere attendrait un signal qui ne viendra jamais.
            pret.set()
        finally:
            connexion.close()

    premiere = moteur(parametres_de_la_stack).connect()
    try:
        #  --- 1. A consomme et NE VALIDE PAS : elle tient le verrou ---------
        transaction_a = premiere.begin()
        resultat_a = consommer_un_magic_link(premiere, jeton=jeton, instant=INSTANT)
        assert resultat_a.reussie, "la premiere transaction doit gagner"

        #  --- 2. B attend le verrou, et on l'OBSERVE ------------------------
        fil = threading.Thread(target=consommer_dans_un_fil, daemon=True)
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
                #  LA SONDE RAPPORTE CE QU'ELLE VOIT, pas seulement un booleen.
                #  Une barriere qui echoue en disant « je n'ai rien vu » coute des
                #  cycles ; celle qui dit CE qu'elle a vu donne la cause. §7.18.
                #  `pg_blocking_pids()` DEMANDE DIRECTEMENT « qui est bloque
                #  par qui ». Ma premiere sonde filtrait sur le TEXTE de la
                #  requete et sur `wait_event_type` : elle n'a jamais vu B, alors
                #  que B etait demonstrablement bloquee -- son erreur disait
                #  « while updating tuple in relation magic_link_request ».
                #  Une sonde qui interroge la relation de blocage elle-meme ne
                #  depend d'aucun detail de presentation. Defaut `T4-4`.
                observe = [
                    tuple(ligne)
                    for ligne in sonde.execute(
                        text(
                            "SELECT pid, pg_blocking_pids(pid), state, "
                            "       wait_event_type, left(query, 50) "
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
        assert en_attente, (
            "aucun backend n'attend de verrou sur `magic_link_request` : B n'a pas "
            "ete bloquee, la barriere n'a donc rien synchronise et ce test ne "
            f"prouve rien. Etat observe : {observe}"
        )

        #  --- 3. A valide. B reprend, et c'est LA que ca discrimine ---------
        transaction_a.commit()
        fil.join(timeout=DELAI_ATTENTE_VERROU)
        assert not fil.is_alive(), "B ne s'est jamais debloquee"
        assert not erreurs, f"B a leve : {erreurs}"

        resultat_b = resultats["b"]
        assert resultat_b.motif == MOTIF_LIEN_REFUSE, (
            "B A AUSSI CONSOMME LE LIEN. L'usage unique n'est pas atomique : la "
            "condition n'est pas reevaluee apres l'obtention du verrou."
        )
        assert resultat_b.personne is None

        #  --- 4. TEMOIN : une consommation NON concurrente reussit ---------
        #  Sans lui, une implementation qui refuserait tout passerait l'etape 3.
        with moteur(parametres_de_la_stack).begin() as connexion:
            temoin = consommer_un_magic_link(connexion, jeton=jeton_temoin, instant=INSTANT)
        assert temoin.reussie, "le TEMOIN echoue : le service refuse un lien valide"

        #  Et le compte en base : `used_at` pose UNE fois sur UNE ligne.
        with moteur(parametres_de_la_stack).connect() as lecture:
            poses = lecture.execute(
                text(
                    "SELECT count(*) FROM magic_link_request m "
                    "JOIN person p ON p.id = m.person_id "
                    "WHERE p.email_normalized = :adresse AND m.used_at IS NOT NULL"
                ),
                {"adresse": adresse},
            ).scalar_one()
        assert poses == 1
    finally:
        premiere.close()
        #  LE NETTOYAGE, QUE MA REECRITURE AVAIT SUPPRIME. Defaut `T4-3` : ce
        #  test valide sa transaction, donc rien ne s'annule tout seul. Les
        #  residus ont fait echouer l'execution suivante, exactement comme le
        #  defaut `T3-3`. La lecon est la meme, et c'est la deuxieme fois.
        #
        #  ==================================================================
        #
        #   `T8` A AJOUTE DEUX GARDE-FOUS ICI, ET LE MOTIF EST MESURE
        #
        #     Ce test a echoue DEUX FOIS sur huit executions completes pendant
        #     `T8`, jamais en isolement (3 sur 3) ni sur son seul fichier (58 sur
        #     58) -- meme famille que le defaut `T4-4`, ou il etait intermittent
        #     une fois sur trois. Et chaque fois, **son echec en a produit huit
        #     autres** dans `test_personnes.py` et `test_roles_et_perimetres.py`,
        #     qui comptent des lignes sans filtre : son decor etait reste en base.
        #
        #     Un nettoyage en `finally` ne suffit donc pas : si B tient encore un
        #     verrou de ligne, le `DELETE` **attend**, et sans borne il pend ou
        #     laisse tout derriere lui. Les deux garde-fous ci-dessous ne
        #     corrigent pas l'intermittence -- sa cause n'est pas etablie -- ils
        #     empechent qu'un echec en devienne neuf, et ils **nomment** ce qui
        #     s'est passe. C'est la lecon centrale du §7.18 : la premiere
        #     correction a ecrire est celle qui te dira pourquoi.
        #
        #  ==================================================================
        if fil.is_alive():
            print(  # un diagnostic doit etre VISIBLE dans le journal de test
                "\n  DIAGNOSTIC : le fil B est encore vivant au nettoyage. S'il tient un "
                "verrou, le nettoyage va echouer sur `lock_timeout`, et le decor restera "
                "en base — ce qui fera echouer des tests SANS RAPPORT."
            )
        with moteur(parametres_de_la_stack).begin() as menage:
            #  Borne le nettoyage : sans elle, un verrou non relache suspend la
            #  suite au lieu de la faire echouer.
            menage.execute(text("SET LOCAL lock_timeout = '5s'"))
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM magic_link_request WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM entity_membership WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM entity WHERE code = :code",
                "DELETE FROM allowed_email_domain WHERE domain = :domaine",
                #  Les evenements SANS personne, bornes a cette execution.
                "DELETE FROM auth_event WHERE person_id IS NULL   AND created_at >= :debut",
            ):
                menage.execute(
                    text(requete),
                    {
                        "motif": f"{marqueur}%",
                        "code": f"T4-{marqueur}",
                        "domaine": DOMAINE_AUTORISE,
                        "debut": debut,
                    },
                )


@pytest.mark.integration
def test_une_consommation_REUSSIE_est_tracee_MAGIC_LINK_USED(cx: Connection) -> None:
    """§10.6 : « magic link utilise » est l'un des sept types."""
    adresse = _decor(cx, marqueur="conso-audit-ok")
    _consommer(cx, _lien(cx, adresse))
    types = (
        cx.execute(
            text(
                "SELECT e.event_type FROM auth_event e JOIN person p ON p.id = e.person_id "
                "WHERE p.email_normalized = :adresse ORDER BY e.occurred_at, e.event_type"
            ),
            {"adresse": adresse},
        )
        .scalars()
        .all()
    )
    assert TypeEvenementAuth.MAGIC_LINK_USED.value in types
    #  **PAS de `LOGIN_SUCCESS`**, et c'est une precision : rien n'est encore
    #  connecte. `T6` cree la session, et c'est elle qui tracera un succes.
    assert TypeEvenementAuth.LOGIN_SUCCESS.value not in types


@pytest.mark.integration
def test_un_refus_est_trace_LOGIN_FAILURE_SANS_personne(cx: Connection) -> None:
    """Un jeton inconnu ne designe personne, et l'echec doit rester traçable.

    `auth_event.person_id` est nullable exactement pour cela — `T2` l'a posé.
    """
    avant = cx.execute(
        text(
            "SELECT count(*) FROM auth_event "
            "WHERE person_id IS NULL AND event_type = :type_evenement"
        ),
        {"type_evenement": TypeEvenementAuth.LOGIN_FAILURE.value},
    ).scalar_one()
    _consommer(cx, engendrer_jeton_magic_link())
    apres = cx.execute(
        text(
            "SELECT count(*) FROM auth_event "
            "WHERE person_id IS NULL AND event_type = :type_evenement"
        ),
        {"type_evenement": TypeEvenementAuth.LOGIN_FAILURE.value},
    ).scalar_one()
    assert apres == avant + 1


@pytest.mark.integration
def test_l_audit_ne_porte_NI_le_jeton_NI_son_empreinte(cx: Connection) -> None:
    """§10.3 : « aucun lien complet dans les logs **ou l'audit** ».

    L'empreinte non plus : elle n'apporterait rien a un audit, et
    `magic_link_request` la porte deja. Ce test regarde la ligne ENTIERE, pas la
    seule colonne attendue — une fuite dans `detail` passerait autrement.
    """
    adresse = _decor(cx, marqueur="conso-audit-secret")
    jeton = _lien(cx, adresse)
    _consommer(cx, jeton)
    lignes = (
        cx.execute(
            text(
                "SELECT e::text FROM auth_event e JOIN person p ON p.id = e.person_id "
                "WHERE p.email_normalized = :adresse"
            ),
            {"adresse": adresse},
        )
        .scalars()
        .all()
    )
    assert lignes, "aucun evenement : le test ne prouverait rien"
    for ligne in lignes:
        assert jeton not in ligne
        assert empreinte_de_jeton(jeton) not in ligne
        assert PREFIXE_MAGIC_LINK not in ligne
