"""Le trombinoscope pagine — story `MVP-L05-US001`.

LOT 5, sous-etape `T2`.

CE QUE CES TESTS PROUVENT, ET DANS QUEL ORDRE

  Le temoin CENTRAL vient d'abord : un profil `published` d'une appartenance
  `active` **est** rendu. Sans lui, les quatre tests d'exclusion seraient tous
  satisfaits par une route qui ne rend jamais rien -- troisieme proposition du
  §7.0, et la forme de defaut la plus facile a laisser passer.

QUATRE EXCLUSIONS, ET LE DECOR LES PORTE TOUTES EN MEME TEMPS

  `EtatAppartenance` declare **quatre** valeurs et `VisibiliteProfil` **trois**.
  Le §6.1 de la matrice n'en nomme que deux -- « profil actif », « profil
  archive ». Un decor qui ne poserait que les cas nommes reconduirait le defaut
  du §7.34 : un motif ecrit contre les exemples connus.

  Le decor pose donc **une ligne par combinaison utile**, et deux garde-fous de
  couverture echouent si le modele gagne un etat ou une visibilite.

L'EXCLUSION EST PROUVEE POUR UN APPELANT `SUPER`

  Le §6.1 donne « Consulter un profil archive » a `ESM`, `ADM-E` et `SUPER`. Ce
  n'est PAS le trombinoscope, qui porte la ligne « profil actif » : la
  consultation d'un archive est un acte delibere, et elle appartient a `T8`.
  Le prouver avec un appelant `SUPER` fige la decision -- un lot qui voudrait un
  listage privilegie devra casser ce test, donc le decider (§7.32).

LA PAGINATION EST PROUVEE PAR RECOMPOSITION, PAS PAR COMPTAGE

  Compter 25 lignes sur une page ne prouve pas que la pagination est correcte :
  un ordre non total rend le meme compte tout en repetant des lignes et en en
  sautant d'autres. Le test decisif **recompose** la population page par page et
  la compare a la liste entiere -- c'est la seule observation qui differe entre
  un ordre total et un ordre partiel.

LE NETTOYAGE EST BORNE PAR LE TEMPS AUTANT QUE PAR L'IDENTITE

  Huitieme lecon du §7.30 : un refus **sans acteur** -- ici un appel sans cookie
  -- produit une trace qu'aucun filtre par identite n'attrape. Et l'ordre des
  suppressions suit les cles etrangeres : `entity_membership` AVANT `person` et
  AVANT `entity`, qu'elle reference toutes les deux.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import text

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeRoleTechnique

#  **`ETAT_LISTE` ET `VISIBILITE_LISTEE` ONT DEMENAGE EN `T5`**, du trombinoscope
#  vers `modeles.py` : un import circulaire avec `app/media/photo.py` a montre
#  que la regle « profil listable » n'appartient a aucun des deux modules qui
#  l'emploient. Elle est derivee des deux enumerations, et sa place est aupres
#  d'elles.
from app.people.modeles import (
    ETAT_LISTE,
    ETATS_APPARTENANCE,
    SITUATIONS_PROFESSIONNELLES,
    VISIBILITE_LISTEE,
    VISIBILITES_PROFIL,
    EtatAppartenance,
)
from app.people.trombinoscope import (
    COLONNES_EXPOSEES,
    LONGUEUR_MAXIMALE_RECHERCHE,
    TAILLE_MAXIMALE,
    TAILLE_PAR_DEFAUT,
    TAILLES_DE_PAGE,
    TailleDePage,
    lister_le_trombinoscope,
)
from app.shared.database import moteur

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

#  **HTTPS, ET CE N'EST PAS UN DETAIL.** Un cookie `Secure` n'est jamais renvoye
#  sur une origine en clair -- la lecon est en tete de `test_sessions.py`.
ORIGINE_DE_TEST = "https://testserver"

CHEMIN = "/api/v1/entities/{code}/people"
CHEMIN_ENTITE = "/api/v1/entities/{code}"

#  Les HUIT champs que la reponse doit porter, et EXACTEMENT ceux-la.
#
#  **`photo` EST ARRIVE EN `T5`, ET CE TEST L'A DIT AVANT MOI.** Il en exigeait
#  sept ; le huitieme l'a fait echouer, sur un livrable pourtant conforme. C'est
#  exactement son role -- « une colonne ajoutee sans etre voulue fait echouer » --
#  et la bonne reaction est de mettre l'attendu a jour **parce que l'addition est
#  voulue** (`DEC-564`), non d'affaiblir le test en comparant par inclusion.
CHAMPS_ATTENDUS = frozenset(
    {
        "id",
        "person_id",
        "first_name",
        "last_name",
        "preferred_name",
        "professional_category",
        "arrival_date",
        "photo",
    }
)
CHAMPS_ENVELOPPE = frozenset({"collaborateurs", "page", "taille", "total", "pages"})

#  Un instant FIXE : les cinq filtres portent sur des relations historisees, et un
#  decor date par rapport a `now()` rendrait le test dependant de l'heure de son
#  execution. Le temps est INJECTE, jamais attendu.
ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


# ===========================================================================
#  1. Sans base : ce qui est verifiable a la lecture du code
# ===========================================================================


def test_les_trois_tailles_du_cahier_18_2_et_une_seule_source() -> None:
    """§18.2 : « 25 par defaut ; options 25, 50 et 100 ; maximum 100 ».

    **Le tuple est DERIVE du `Literal`**, qui est ce que la route emploie. Deux
    listes ecrites cote a cote divergeraient a la premiere sous-etape qui n'en
    changerait qu'une (§7.27) -- ce test prouve qu'il n'y en a qu'une.
    """
    assert TAILLES_DE_PAGE == (25, 50, 100)
    assert tuple(membre.value for membre in TailleDePage) == TAILLES_DE_PAGE
    assert TAILLE_PAR_DEFAUT == 25
    assert TAILLE_PAR_DEFAUT in TAILLES_DE_PAGE
    #  **`IntEnum` ET NON `Literal`, ET LE MOTIF EST MESURE** : un parametre
    #  d'URL arrive en chaine, et `Literal[25, 50, 100]` REFUSE la chaine « 25 ».
    #  La route refusait donc les trois tailles valides des qu'elles etaient
    #  ecrites, et seul le temoin le voyait. Defaut `T2-3`.
    assert issubclass(TailleDePage, int)
    #  **L'EPREUVE PORTE SUR PYDANTIC, PAS SUR L'ENUMERATION.** `TailleDePage("50")`
    #  interroge l'enumeration par valeur et echoue -- « 50 » n'est pas 50. C'est
    #  Pydantic qui convertit, et c'est lui que FastAPI emploie : eprouver autre
    #  chose serait mesurer une grandeur voisine de celle qui compte (§7.33).
    adaptateur = TypeAdapter(TailleDePage)
    for texte, attendu in (("25", 25), ("50", 50), ("100", 100)):
        assert adaptateur.validate_python(texte) == attendu
    for refus in ("24", "37", "101"):
        with pytest.raises(ValidationError):
            adaptateur.validate_python(refus)
    #  La borne du cahier est le MAXIMUM du tuple, jamais une troisieme constante.
    assert TAILLE_MAXIMALE == 100 == max(TAILLES_DE_PAGE)


def test_les_QUATRE_etats_et_les_TROIS_visibilites_sont_connus_de_ces_tests() -> None:
    """**GARDE-FOU DE COUVERTURE**, et il y en a deux parce qu'il y a deux
    dimensions.

    Si un lot ajoute un cinquieme etat d'appartenance ou une quatrieme
    visibilite, ce test echoue et oblige a decider si le trombinoscope le rend.
    Sans lui, une valeur nouvelle serait silencieusement exclue -- et mes temoins
    d'exclusion continueraient de passer en ne couvrant plus la classe (§7.34).
    """
    assert set(ETATS_APPARTENANCE) == {"future", "active", "departed", "archived"}
    assert set(VISIBILITES_PROFIL) == {"draft", "published", "hidden"}
    #  Les deux valeurs listantes sont DERIVEES des enumerations, jamais ecrites
    #  en litteral dans le service.
    assert ETAT_LISTE == "active"
    assert VISIBILITE_LISTEE == "published"


def test_les_colonnes_exposees_sont_declarees_une_seule_fois() -> None:
    """Les huit champs declares et les huit champs servis se correspondent.

    **LE NOMBRE EST ECRIT, ET C'EST VOULU.** Comparer les deux ensembles entre
    eux ne prouverait rien le jour ou les deux seraient modifies ensemble par
    distraction -- ils viennent de deux fichiers, mais rien n'empeche d'editer
    les deux. Le nombre en dur est le troisieme temoin, et il fait echouer toute
    addition non decidee.
    """
    assert set(COLONNES_EXPOSEES) == CHAMPS_ATTENDUS
    assert len(COLONNES_EXPOSEES) == len(CHAMPS_ATTENDUS) == 8


def test_le_service_refuse_une_taille_hors_liste_meme_sans_HTTP() -> None:
    """**LA VERIFICATION DU SERVICE N'EST PAS UNE REDONDANCE DE CELLE DE HTTP.**

    Le service est appelable hors requete -- un futur export, un script -- et une
    fonction qui accepterait 10 000 rendrait la borne du cahier dependante de son
    appelant. Aucune connexion n'est ouverte : la garde precede la requete.
    """
    for taille in (0, 1, 24, 26, 99, 101, 10_000):
        with pytest.raises(ValueError, match="taille"):
            lister_le_trombinoscope(
                None,  # type: ignore[arg-type]
                entite=uuid.uuid4(),
                page=1,
                taille=taille,
                instant=ANCRAGE,
            )


def test_le_service_refuse_une_page_inferieure_a_un() -> None:
    """`page` est 1-indexee : c'est le numero que l'ecran affiche."""
    for page in (0, -1, -100):
        with pytest.raises(ValueError, match="page"):
            lister_le_trombinoscope(
                None,  # type: ignore[arg-type]
                entite=uuid.uuid4(),
                page=page,
                taille=TAILLE_PAR_DEFAUT,
                instant=ANCRAGE,
            )


# ===========================================================================
#  2. Avec PostgreSQL reel
# ===========================================================================

#  Les six lignes du decor : cinq a exclure, une a rendre. Le libelle sert de
#  nom de famille, ce qui rend l'ordre attendu lisible.
DECOR: tuple[tuple[str, str, str], ...] = (
    ("visible", "active", "published"),
    ("brouillon", "active", "draft"),
    ("masque", "active", "hidden"),
    ("future", "future", "published"),
    ("partie", "departed", "published"),
    ("archivee", "archived", "published"),
)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str]]:
    """Une entite, six appartenances couvrant les deux dimensions, une session.

    **`departed` et `archived` gardent `published`, ET C'EST LE POINT.** Le §22.5
    etape 5 prescrit « masquage du profil » au depart ; mesure le 25/08/2026 :
    aucun code ne pose `profile_visibility` -- `_appliquer` de
    `app/people/services.py` change l'etat et ferme les relations, rien d'autre.
    Un partant reste donc `published` en base. Si le trombinoscope ne filtrait
    que la visibilite, il le listerait.
    """
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t2l5{uuid.uuid4().hex[:10]}"
    code_entite = f"{marqueur}-e"

    with moteur(parametres).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()

    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris')"
            ),
            {"code": code_entite, "nom": f"Entite {marqueur}"},
        )
        for libelle, etat, visibilite in DECOR:
            _poser_un_collaborateur(
                cx,
                marqueur=marqueur,
                code_entite=code_entite,
                nom=libelle,
                prenom="Ada",
                etat=etat,
                visibilite=visibilite,
            )

    try:
        yield parametres, marqueur, code_entite
    finally:
        _nettoyer(parametres, marqueur, debut)


def _poser_un_collaborateur(
    cx: Any,
    *,
    marqueur: str,
    code_entite: str,
    nom: str,
    prenom: str,
    etat: str = EtatAppartenance.ACTIVE.value,
    visibilite: str = "published",
) -> None:
    """Une personne et son appartenance dans l'entite du decor.

    **`departure_date` EST EXIGEE POUR `departed`, ET C'EST LA BASE QUI ME L'A
    APPRIS** : `ck_entity_membership_depart_date_si_departed` s'ecrit
    « membership_state <> 'departed' OR departure_date IS NOT NULL ». Elle ne
    porte PAS sur `archived` -- une appartenance archivee sans date de depart est
    donc legale, ce qu'un decor qui daterait les deux aurait masque.
    """
    adresse = f"{marqueur}-{nom}-{prenom}@exalt-l5t2.test".lower()
    personne = cx.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :a, :prenom, :nom, 'active') RETURNING id"
        ),
        {"a": adresse, "prenom": prenom, "nom": nom},
    ).scalar_one()
    #  **PARAMETRE LIE, PAS D'INTERPOLATION.** La premiere version composait la
    #  date dans la chaine SQL, et `S608` avait raison de le signaler : un
    #  `noqa` aurait museli un avertissement juste. Passer `None` ou une date
    #  donne exactement le meme resultat sans construire de SQL.
    depart = dt.date(2026, 6, 30) if etat == EtatAppartenance.DEPARTED.value else None
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "departure_date, membership_state, professional_category, profile_visibility) "
            "SELECT :personne, id, DATE '2026-01-15', :depart, :etat, 'consultant', "
            ":visibilite FROM entity WHERE code = :code"
        ),
        {
            "personne": personne,
            "depart": depart,
            "etat": etat,
            "visibilite": visibilite,
            "code": code_entite,
        },
    )


def _nettoyer(parametres: Parametres, marqueur: str, debut: dt.datetime) -> None:
    """L'ordre suit les cles etrangeres, et la borne temporelle attrape le reste."""
    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            #  AVANT `person` et AVANT `entity` : elle reference les deux.
            "DELETE FROM entity_membership WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE person_id IN "
            "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
            "DELETE FROM person WHERE email_normalized LIKE :motif",
            "DELETE FROM entity WHERE code LIKE :motif",
            #  Le refus sans acteur n'a ni personne ni compte de service : seule
            #  la borne temporelle l'attrape. §7.30.
            "DELETE FROM auth_event WHERE person_id IS NULL "
            "  AND service_account_id IS NULL AND created_at >= :debut",
        ):
            menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _session(parametres: Parametres, marqueur: str, suffixe: str = "") -> str:
    """Ouvrir une session reelle et rendre son jeton en clair."""
    adresse = f"{marqueur}{suffixe}-appelant@exalt-l5t2.test"
    with moteur(parametres).begin() as cx:
        personne = uuid.UUID(
            str(
                cx.execute(
                    text(
                        "INSERT INTO person "
                        "(email, email_normalized, first_name, last_name, account_state) "
                        "VALUES (:a, :a, 'Appelant', 'T2', 'active') RETURNING id"
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
    parametres: Parametres,
    code: str,
    jeton: str | None,
    *,
    requete: str = "",
    entetes: dict[str, str] | None = None,
    chemin: str = CHEMIN,
) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin.format(code=code) + requete, headers=entetes or {})


def _noms(charge: dict[str, Any]) -> list[str]:
    return [ligne["last_name"] for ligne in charge["collaborateurs"]]


@pytest.mark.integration
def test_un_profil_PUBLIE_et_ACTIF_est_rendu(decor: tuple[Parametres, str, str]) -> None:
    """**LE TEMOIN CENTRAL.** Sans lui, les cinq exclusions seraient satisfaites
    par une route qui ne rend jamais rien.
    """
    parametres, marqueur, code = decor
    reponse = _appeler(parametres, code, _session(parametres, marqueur))
    assert reponse.status_code == 200, reponse.text
    assert _noms(reponse.json()) == ["visible"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("exclu", "motif"),
    [
        ("brouillon", "profil `draft` — pas encore publie, §10.2 le verrouille avant validation"),
        ("masque", "profil `hidden` — le masquage du §22.5 etape 5"),
        ("future", "appartenance `future` — arrivee non atteinte"),
        ("partie", "appartenance `departed` — le §22.5, et son profil est RESTE `published`"),
        ("archivee", "appartenance `archived` — matrice §6.1, reserve a `T8`"),
    ],
)
def test_les_CINQ_lignes_non_listables_sont_absentes(
    decor: tuple[Parametres, str, str], exclu: str, motif: str
) -> None:
    """Chaque exclusion a son cas, et le motif est dans le libelle du parametre.

    **`partie` et `archivee` portent `profile_visibility = 'published'`**, ce qui
    rend ce test discriminant : un filtre qui ne porterait que sur la visibilite
    les rendrait, et le §22.5 etape 5 n'etant implemente nulle part, c'est
    exactement l'etat que la base contient apres un depart.
    """
    parametres, marqueur, code = decor
    reponse = _appeler(parametres, code, _session(parametres, marqueur))
    assert reponse.status_code == 200, reponse.text
    assert exclu not in _noms(reponse.json()), motif


@pytest.mark.integration
def test_les_exclusions_valent_AUSSI_pour_un_super_administrateur(
    decor: tuple[Parametres, str, str],
) -> None:
    """**CE TEST FIGE UNE DECISION, ET C'EST SON OBJET** (§7.32).

    Le §6.1 de la matrice donne « Consulter un profil archive » a `ESM`, `ADM-E`
    et `SUPER`. Ce n'est PAS cette route : le trombinoscope porte la ligne
    « profil actif », et la consultation d'un archive est un acte delibere --
    « besoin fonctionnel » -- qui appartient a `T8`.

    Un lot qui voudrait un listage privilegie devra casser ce test, donc le
    decider. Un commentaire ne l'aurait pas obtenu.
    """
    parametres, marqueur, code = decor
    jeton = _session(parametres, marqueur, "-super")
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                #  **`entity_id` EST NULL, ET C'EST LA BASE QUI L'EXIGE** :
                #  `ck_technical_role_assignment_portee_selon_le_role` s'ecrit
                #  « ENTITY_ADMIN ET entity_id NOT NULL, OU SUPER_ADMIN ET
                #  entity_id NULL ». Le super-administrateur est GLOBAL -- matrice
                #  §5.1, « la seule exception globale » -- et le lier a une entite
                #  serait une contradiction que le schema refuse.
                "INSERT INTO technical_role_assignment "
                "(person_id, entity_id, role_type, starts_at, ends_at) "
                "SELECT p.id, NULL, :role, now() - INTERVAL '1 day', NULL "
                "FROM person p WHERE p.email_normalized = :adresse"
            ),
            {
                "adresse": f"{marqueur}-super-appelant@exalt-l5t2.test",
                "role": TypeRoleTechnique.SUPER_ADMIN.value,
            },
        )
    reponse = _appeler(parametres, code, jeton)
    assert reponse.status_code == 200, reponse.text
    assert _noms(reponse.json()) == ["visible"]


@pytest.mark.integration
def test_l_enveloppe_porte_ses_cinq_champs_et_les_lignes_leurs_huit(
    decor: tuple[Parametres, str, str],
) -> None:
    """Ni plus ni moins : une colonne ajoutee sans etre voulue fait echouer.

    **ET IL A ECHOUE EN `T5`**, quand `photo` est arrive. Le laisser echouer
    jusqu'a ce que l'attendu soit mis a jour est ce qui rend l'addition d'un
    champ **visible en revue** -- un test qui comparerait par inclusion
    laisserait passer n'importe quelle donnee nouvelle en silence.
    """
    parametres, marqueur, code = decor
    charge = _appeler(parametres, code, _session(parametres, marqueur)).json()
    assert set(charge) == CHAMPS_ENVELOPPE
    assert set(charge["collaborateurs"][0]) == CHAMPS_ATTENDUS
    assert charge["page"] == 1
    assert charge["taille"] == TAILLE_PAR_DEFAUT
    assert charge["total"] == 1
    assert charge["pages"] == 1


@pytest.mark.integration
def test_une_autre_entite_ne_voit_pas_ces_collaborateurs(
    decor: tuple[Parametres, str, str],
) -> None:
    """Le filtre porte sur `entity_id`, et une seconde entite le prouve."""
    parametres, marqueur, _code = decor
    autre = f"{marqueur}-e2"
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Lyon', 'FR', 'active', 'Europe/Paris')"
            ),
            {"code": autre, "nom": f"Autre {marqueur}"},
        )
    reponse = _appeler(parametres, autre, _session(parametres, marqueur, "-b"))
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["collaborateurs"] == []
    assert reponse.json()["total"] == 0
    assert reponse.json()["pages"] == 0


# ---------------------------------------------------------------------------
#  Pagination : le volume, l'ordre, et la recomposition
# ---------------------------------------------------------------------------


@pytest.fixture
def foule(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, str, list[str]]]:
    """Cent-vingt-six collaborateurs publies — plus que la plus grande page.

    **LE VOLUME EST LE POINT** (§7.26) : une pagination ne se prouve pas sur
    trente lignes. 126 = 100 + 26, ce qui donne une derniere page NON pleine a
    chacune des trois tailles, et cinq pages a 25 -- le cas ou un ordre non total
    se voit.
    """
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t2l5f{uuid.uuid4().hex[:9]}"
    code_entite = f"{marqueur}-e"

    with moteur(parametres).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()

    #  Des HOMONYMES volontaires : neuf personnes portent le meme nom et le meme
    #  prenom. Sans le troisieme critere de tri, PostgreSQL est libre de les
    #  rendre dans un ordre different d'un appel a l'autre, et la recomposition
    #  echouerait.
    noms = [f"nom{indice // 9:03d}" for indice in range(126)]
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris')"
            ),
            {"code": code_entite, "nom": f"Foule {marqueur}"},
        )
        for indice, nom in enumerate(noms):
            _poser_un_collaborateur(
                cx,
                marqueur=marqueur,
                code_entite=code_entite,
                nom=nom,
                prenom=f"p{indice:03d}",
            )

    try:
        yield parametres, marqueur, code_entite, noms
    finally:
        _nettoyer(parametres, marqueur, debut)


@pytest.mark.integration
@pytest.mark.parametrize("taille", TAILLES_DE_PAGE)
def test_les_TROIS_tailles_du_cahier_sont_servies(
    foule: tuple[Parametres, str, str, list[str]], taille: int
) -> None:
    """25, 50 et 100 — et le total ne depend pas de la taille demandee."""
    parametres, marqueur, code, noms = foule
    reponse = _appeler(
        parametres, code, _session(parametres, marqueur), requete=f"?taille={taille}"
    )
    assert reponse.status_code == 200, reponse.text
    charge = reponse.json()
    assert charge["taille"] == taille
    assert len(charge["collaborateurs"]) == taille
    assert charge["total"] == len(noms) == 126
    assert charge["pages"] == -(-126 // taille)


@pytest.mark.integration
@pytest.mark.parametrize("taille", TAILLES_DE_PAGE)
def test_la_pagination_ne_repete_ni_ne_saute_aucune_ligne(
    foule: tuple[Parametres, str, str, list[str]], taille: int
) -> None:
    """**LE TEST DECISIF, ET IL PROCEDE PAR RECOMPOSITION.**

    Compter 25 lignes sur une page ne prouve rien : un ordre non total rend le
    meme compte tout en repetant des lignes et en en sautant d'autres -- les deux
    observations seraient identiques (§7.0, quatrieme proposition).

    On parcourt donc TOUTES les pages, on concatene, et on exige que la
    concatenation porte exactement les 126 identifiants, chacun une seule fois.
    Le decor contient des homonymes : sans le tri par cle primaire, ce test
    echoue.
    """
    parametres, marqueur, code, noms = foule
    jeton = _session(parametres, marqueur)
    vus: list[str] = []
    pages = -(-len(noms) // taille)
    for page in range(1, pages + 1):
        charge = _appeler(parametres, code, jeton, requete=f"?page={page}&taille={taille}").json()
        assert charge["page"] == page
        vus.extend(ligne["id"] for ligne in charge["collaborateurs"])

    assert len(vus) == len(noms) == 126, "une page a repete ou saute des lignes"
    assert len(set(vus)) == 126, "un identifiant apparait deux fois"

    #  Une page AU-DELA de la derniere est vide, et ce n'est pas une erreur.
    au_dela = _appeler(parametres, code, jeton, requete=f"?page={pages + 1}&taille={taille}").json()
    assert au_dela["collaborateurs"] == []
    assert au_dela["total"] == 126


@pytest.mark.integration
def test_l_ordre_est_nom_puis_prenom_et_la_collation_est_FRANCAISE(
    parametres_de_la_stack: Parametres,
) -> None:
    """Arbitrage du 25/08/2026 : nom, puis prenom.

    **L'EPREUVE EST DISCRIMINANTE SUR LES ACCENTS.** « Elodie » avec accent doit
    se classer avec les E et non apres les Z : c'est ce qui distingue une
    collation ICU `fr-FR` d'un tri par octets. Un decor sans accent aurait donne
    la meme observation dans les deux cas.
    """
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t2l5o{uuid.uuid4().hex[:9]}"
    code_entite = f"{marqueur}-e"
    with moteur(parametres).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()

    #  `Evrard` et `Élodie` : sans ICU, `Élodie` sortirait APRES `Zola`.
    #  **CET ATTENDU A ETE FAUX DANS SA PREMIERE VERSION, ET LE TEST L'A DIT.**
    #  J'avais ecrit l'ordre OCTET -- « Élodie » apres « Zola » -- alors que le
    #  commentaire trois lignes plus haut decrivait l'ordre francais. Ecrire
    #  l'attendu du mode d'echec au lieu de celui du succes est un defaut qu'aucune
    #  relecture n'attrape : seule l'execution le dit.
    attendus = [("Élodie", "Ana"), ("Élodie", "Zoe"), ("Evrard", "Bea"), ("Zola", "Ana")]
    try:
        with moteur(parametres).begin() as cx:
            cx.execute(
                text(
                    "INSERT INTO entity (code, display_name, city, country_code, status, "
                    "timezone) VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris')"
                ),
                {"code": code_entite, "nom": f"Ordre {marqueur}"},
            )
            #  Insere DANS LE DESORDRE : si la route ne triait pas, elle rendrait
            #  l'ordre d'insertion, qui n'est pas l'ordre attendu.
            for nom, prenom in [
                ("Zola", "Ana"),
                ("Élodie", "Zoe"),
                ("Evrard", "Bea"),
                ("Élodie", "Ana"),
            ]:
                _poser_un_collaborateur(
                    cx, marqueur=marqueur, code_entite=code_entite, nom=nom, prenom=prenom
                )
        charge = _appeler(parametres, code_entite, _session(parametres, marqueur)).json()
        obtenus = [(ligne["last_name"], ligne["first_name"]) for ligne in charge["collaborateurs"]]
        assert obtenus == attendus, (
            "l'ordre attendu est nom puis prenom, avec « Élodie » classe avec les E — "
            f"obtenu {obtenus}"
        )
    finally:
        _nettoyer(parametres, marqueur, debut)


# ---------------------------------------------------------------------------
#  HTTP : les refus
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_sans_session_la_route_refuse(decor: tuple[Parametres, str, str]) -> None:
    """La matrice §5 donne `ANON` a tiret sur le trombinoscope.

    **CE TEST EST AUSSI CELUI QUI PROUVE QUE `Annotated` NE PIEGE PAS ICI.** Le
    piege mesure en `T1` du LOT 4 rendait **422** avec `loc: ["query", ...]` :
    FastAPI ne voyait pas la dependance et prenait le parametre pour une chaine
    de requete. Il tenait a une variable de FERMETURE absente des globals du
    module. `TailleDePage` et `Query` sont tous deux importes au niveau module,
    donc resolvables -- et un 401 le prouve la ou un 422 le refuterait.
    """
    parametres, _marqueur, code = decor
    reponse = _appeler(parametres, code, None)
    assert reponse.status_code == 401, reponse.text


@pytest.mark.integration
@pytest.mark.parametrize("taille", [0, 1, 24, 26, 37, 99, 101, 1000])
def test_une_taille_hors_des_TROIS_est_refusee(
    decor: tuple[Parametres, str, str], taille: int
) -> None:
    """Arbitrage du 25/08/2026 : l'API n'accepte que 25, 50 et 100.

    **`101` COUVRE « le maximum de 100 refuse au-dela »**, et `26`, `37`, `99`
    couvrent la liste blanche -- le critere de sortie ne nommait que la premiere
    de ces deux exigences, et une liste blanche qui laisserait passer 99 ne
    serait pas une liste blanche.
    """
    parametres, marqueur, code = decor
    reponse = _appeler(
        parametres, code, _session(parametres, marqueur), requete=f"?taille={taille}"
    )
    assert reponse.status_code == 422, reponse.text
    #  Format du §18.3, produit par `gerer_erreur_validation` et NICHE sous
    #  `erreur` — `construire_corps` est l'unique fabrique de ce corps, et les
    #  cinq cles du §18.3 y sont toutes.
    corps = reponse.json()["erreur"]
    assert corps["code"] == "validation_invalide"
    assert corps["champ"] == "query.taille"
    assert corps["identifiant_correlation"]


@pytest.mark.integration
def test_une_page_inferieure_a_un_est_refusee(decor: tuple[Parametres, str, str]) -> None:
    """`page` est 1-indexee."""
    parametres, marqueur, code = decor
    reponse = _appeler(parametres, code, _session(parametres, marqueur), requete="?page=0")
    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["erreur"]["champ"] == "query.page"


@pytest.mark.integration
def test_le_404_est_IDENTIQUE_a_celui_de_la_route_d_entite(
    decor: tuple[Parametres, str, str],
) -> None:
    """**EN CORPS ET EN EN-TETES**, la correlation etant FIXEE plutot qu'exclue.

    Deux routes qui distingueraient differemment un code inconnu d'une entite non
    active apprendraient, par comparaison, qu'un brouillon existe. Fixer
    `X-Request-ID` vaut mieux qu'exclure le champ : une exclusion laisse la porte
    ouverte a une difference qui se cacherait dedans (lecon de `T2` du LOT 4).
    """
    parametres, marqueur, _code = decor
    jeton = _session(parametres, marqueur)
    correlation = {"X-Request-ID": "l5t2-comparaison-404"}
    inconnu = f"{marqueur}-inexistant"

    trombinoscope = _appeler(parametres, inconnu, jeton, entetes=correlation)
    entite = _appeler(parametres, inconnu, jeton, entetes=correlation, chemin=CHEMIN_ENTITE)

    assert trombinoscope.status_code == entite.status_code == 404
    assert trombinoscope.json() == entite.json()
    interessants = {"content-type", "x-request-id"}
    assert {
        n.lower(): v for n, v in trombinoscope.headers.items() if n.lower() in interessants
    } == {n.lower(): v for n, v in entite.headers.items() if n.lower() in interessants}


# ---------------------------------------------------------------------------
#  T3 : les filtres a travers HTTP
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_un_identifiant_de_filtre_mal_forme_est_refuse(decor: tuple[Parametres, str, str]) -> None:
    """Les quatre axes a identifiant sont typees `uuid.UUID` : FastAPI refuse.

    **LE REFUS PORTE LE FORMAT DU §18.3**, produit par le gestionnaire de
    validation et non par la route -- ecrire un second refus donnerait deux formes
    pour une meme cause.
    """
    parametres, marqueur, code = decor
    jeton = _session(parametres, marqueur)
    for axe in ("cercle", "dsm", "metier", "client"):
        reponse = _appeler(parametres, code, jeton, requete=f"?{axe}=pas-un-uuid")
        assert reponse.status_code == 422, f"{axe} : {reponse.text}"
        assert reponse.json()["erreur"]["champ"] == f"query.{axe}"


@pytest.mark.integration
def test_un_statut_hors_des_DEUX_valeurs_est_refuse(decor: tuple[Parametres, str, str]) -> None:
    """§9.3 : `mission` ou `intercontract`, et rien d'autre.

    **LES DEUX VALEURS VALIDES SONT EPROUVEES AUSSI**, sans quoi un type qui
    refuserait tout passerait ce test -- c'est exactement le defaut `T2-3`, dont
    la lecon est que toute famille de refus a besoin de son temoin.
    """
    parametres, marqueur, code = decor
    jeton = _session(parametres, marqueur)
    for valeur in ("employe", "MISSION", "", "mission-x"):
        reponse = _appeler(parametres, code, jeton, requete=f"?statut={valeur}")
        assert reponse.status_code == 422, f"« {valeur} » accepte : {reponse.text}"
        assert reponse.json()["erreur"]["champ"] == "query.statut"
    for valide in SITUATIONS_PROFESSIONNELLES:
        reponse = _appeler(parametres, code, jeton, requete=f"?statut={valide}")
        assert reponse.status_code == 200, f"« {valide} » refuse : {reponse.text}"


@pytest.mark.integration
def test_un_terme_de_recherche_trop_long_est_refuse(decor: tuple[Parametres, str, str]) -> None:
    """Sans borne, la base normaliserait un terme enorme sur chaque ligne.

    Le temoin est a la borne EXACTE : 128 passe, 129 refuse. Une epreuve qui ne
    testerait que « tres long » ne dirait pas ou est la borne.
    """
    parametres, marqueur, code = decor
    jeton = _session(parametres, marqueur)
    juste = "a" * LONGUEUR_MAXIMALE_RECHERCHE
    trop = "a" * (LONGUEUR_MAXIMALE_RECHERCHE + 1)
    assert _appeler(parametres, code, jeton, requete=f"?recherche={juste}").status_code == 200
    refus = _appeler(parametres, code, jeton, requete=f"?recherche={trop}")
    assert refus.status_code == 422, refus.text
    assert refus.json()["erreur"]["champ"] == "query.recherche"


@pytest.mark.integration
def test_la_recherche_a_travers_HTTP_ignore_les_accents(
    decor: tuple[Parametres, str, str],
) -> None:
    """Le decor porte `visible` : on la trouve par un fragment de son nom.

    **ET UN TEMOIN DANS L'AUTRE SENS** : un terme absent rend une liste vide avec
    un `total` a zero, et non une erreur. Sans lui, une recherche qui refuserait
    tout donnerait la meme observation qu'une recherche correcte sur un terme
    absent.
    """
    parametres, marqueur, code = decor
    jeton = _session(parametres, marqueur)
    trouve = _appeler(parametres, code, jeton, requete="?recherche=isibl").json()
    assert _noms(trouve) == ["visible"], (
        "une sous-chaine du nom doit suffire — et seule la ligne LISTABLE remonte, "
        "les cinq autres etant exclues par leur etat"
    )
    assert trouve["total"] == 1

    #  Le prenom du decor est « Ada » : on le trouve sans accent comme avec.
    #  Le prenom est « Ada » pour les SIX lignes du decor : la recherche par
    #  prenom rend donc la seule qui soit listable, ce qui prouve que les filtres
    #  d'etat et la recherche se composent.
    par_prenom = _appeler(parametres, code, jeton, requete="?recherche=ADA").json()
    assert _noms(par_prenom) == ["visible"], "la recherche doit porter sur le PRENOM aussi"

    vide = _appeler(parametres, code, jeton, requete="?recherche=zzzz-absent").json()
    assert vide["collaborateurs"] == []
    assert vide["total"] == 0
    assert vide["pages"] == 0
