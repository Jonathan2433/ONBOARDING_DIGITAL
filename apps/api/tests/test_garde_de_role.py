"""`exiger_un_role_dans_l_entite` — LOT 4, `T9`, story `MVP-L04-US005`.

CE FICHIER EST L'AUTORITE, PAS LE MENU

  La roadmap du LOT 4 dit « route guards uniquement ergonomiques » et « controles
  d'autorisation systematiques dans l'API ». La matrice §2.6 : « le frontend peut
  masquer ou afficher les actions [...] mais **l'API reste l'autorite finale** ».
  Et le §24.20 en fait un controle d'acceptation : « les actions interdites sont
  refusees cote API, **meme si la requete est construite manuellement** ».

  Une requete construite a la main, c'est exactement ce que ces tests emettent.

L'APPLICATION EST JETABLE, ET LE PRECEDENT EST CELUI DE `exiger_un_scope`

  `T9` du LOT 3 a eprouve son garde-fou de scope sur une application minimale
  portant une seule route `/protege`, en nommant le residuel : aucune route de
  production n'etait inventee. **Le meme choix ici, pour le meme motif** : le
  §9.4 de la passation ecarte tout ecran d'administration de ce lot, donc aucune
  route metier ne doit naitre pour porter le garde-fou.

  **Ce que cela ne prouve pas, et il faut le dire :** la traversee de Caddy. Les
  quinze controles de `make permissions-check` la couvrent pour la resolution des
  permissions ; le refus par role, lui, n'est prouve qu'ici, sur une vraie
  application FastAPI avec de vrais codes HTTP.

LES QUATRE CONTROLES D'ACCEPTATION DU §24 QUE CE FICHIER COUVRE

    §24.1   « un employe consulte toutes les entites mais ne modifie aucune autre »
    §24.7   « un administrateur d'entite n'accede pas aux autres entites »
    §24.12  « un role cloture ne continue pas a accorder des permissions »
    §24.20  « les actions interdites sont refusees cote API, meme si la requete
             est construite manuellement »
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.permissions.dependances import (
    PARAMETRE_DE_CHEMIN,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative, gerer_erreur_applicative

MANIFESTE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "packages"
    / "contracts"
    / "src"
    / "contrat-api.json"
)


def _roles_administration() -> tuple[RoleDeLaMatrice, ...]:
    """Les roles qui ouvrent l'administration, LUS DU MANIFESTE DU CONTRAT.

    **PAS UNE SECONDE LISTE.** Ma premiere version ecrivait les trois roles ici
    ET dans `apps/web/src/routes.ts` : deux derivations du meme §20, dans deux
    langages, sans rien pour les confronter. C'est §7.27, et la parade est celle
    que `DEC-492` a posee -- le manifeste est la source unique lue par TypeScript
    et par Python.

    Les valeurs sont **converties** en `RoleDeLaMatrice`, ce qui ajoute une
    exigence utile : un code du manifeste qui ne serait pas un role connu leve
    ici, au lieu de rendre la garde inerte en silence.
    """
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    codes = manifeste["rolesAdministration"]
    assert codes, "le manifeste ne declare aucun role d'administration"
    return tuple(RoleDeLaMatrice(code) for code in codes)


ROLES_ADMINISTRATION = _roles_administration()

ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
JOUR = dt.timedelta(days=1)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


#  **CE PREFIXE EST CE QUI REND LE NETTOYAGE EXACT.** Toutes les entites et
#  personnes de ce fichier le portent, donc la suppression se DERIVE — `LIKE
#  'T9-%'` — au lieu de tenir une liste d'identifiants qui vieillirait au premier
#  test ajoute (§7.27).
MARQUEUR = "T9-"
MARQUEUR_PERSONNE = "t9-"

#  L'ordre est celui des dependances, et il compte : **le nettoyage est UNE SEULE
#  transaction, et son echec l'annule ENTIEREMENT** — rien n'est supprime, pas
#  meme ce qui aurait pu l'etre. C'est le defaut `T2-2` du LOT 4, dont les 23
#  tests d'integration en echec ne nommaient jamais la cause.
_SUPPRESSIONS = (
    "DELETE FROM auth_event WHERE person_id IN (SELECT id FROM person WHERE"
    " email_normalized LIKE :personnes)",
    "DELETE FROM user_session WHERE person_id IN (SELECT id FROM person WHERE"
    " email_normalized LIKE :personnes)",
    "DELETE FROM technical_role_assignment WHERE person_id IN (SELECT id FROM person WHERE"
    " email_normalized LIKE :personnes)",
    "DELETE FROM framework_responsibility_assignment WHERE person_id IN (SELECT id FROM"
    " person WHERE email_normalized LIKE :personnes)",
    "DELETE FROM entity_membership WHERE person_id IN (SELECT id FROM person WHERE"
    " email_normalized LIKE :personnes)",
    "DELETE FROM person WHERE email_normalized LIKE :personnes",
    "DELETE FROM entity WHERE code LIKE :entites",
)


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Une connexion qui COMMITE, et qui nettoie explicitement ensuite.

    **LE ROLLBACK EST LE MAUVAIS OUTIL ICI, ET LA MESURE L'A DIT.** Ces tests
    emettent de vraies requetes HTTP par `TestClient`, donc l'API lit sur une
    AUTRE connexion : des lignes en transaction ouverte lui sont invisibles. Il
    faut donc commiter — et `cx.commit()` dans une fixture a rollback ne laisse
    plus rien a annuler.

    Premiere version : la fixture de `test_permissions.py` a ete reprise telle
    quelle. Resultat mesure le 24/08/2026 — **le premier run a laisse ses lignes
    commitees, et le second a echoue sur `code_unique`** avec un message qui ne
    nommait pas la cause. C'est la huitieme occurrence de la classe du §7.30, et
    `make residu-check` est ce qui l'aurait dit.

    Le nettoyage est donc EXPLICITE, derive du prefixe, et **verifie** : la
    fixture echoue si un residu subsiste, plutot que de le laisser empoisonner un
    autre fichier de test.
    """
    _exiger_postgresql(parametres_de_la_stack)
    parametres_de_suppression = {
        "personnes": f"{MARQUEUR_PERSONNE}%",
        "entites": f"{MARQUEUR}%",
    }
    with moteur(parametres_de_la_stack).connect() as connexion:
        try:
            yield connexion
        finally:
            connexion.rollback()
            for requete in _SUPPRESSIONS:
                connexion.execute(text(requete), parametres_de_suppression)
            connexion.commit()
            restants = connexion.execute(
                text(
                    "SELECT (SELECT count(*) FROM entity WHERE code LIKE :entites)"
                    " + (SELECT count(*) FROM person WHERE email_normalized LIKE :personnes)"
                ),
                parametres_de_suppression,
            ).scalar_one()
            assert restants == 0, (
                f"{restants} ligne(s) marquee(s) subsistent : elles feraient echouer les tests "
                f"du LOT 2, qui comptent `person` et `entity` EN ABSOLU"
            )


def _application(parametres: Parametres) -> FastAPI:
    """Une application minimale portant UNE route gardee, et une route TEMOIN.

    **LA ROUTE TEMOIN EST CE QUI DONNE UN SENS AUX REFUS.** Sans elle, un 403 sur
    la route gardee serait indistinguable d'une application qui refuse tout le
    monde — et c'est exactement le defaut qu'un `Annotated` mal place avait
    produit en `T1` : un livrable qui PARAIT protege et refuse tout le monde.

    **ET LA SECONDE ROUTE GARDEE N'A PAS DE PARAMETRE `code`.** Elle eprouve le
    garde-fou de montage : sans lui, la dependance lirait `None`, l'entite serait
    introuvable, et la route rendrait 404 pour tout le monde en paraissant sure.
    """
    application = FastAPI()
    application.add_exception_handler(ErreurApplicative, gerer_erreur_applicative)
    garde = exiger_un_role_dans_l_entite(parametres, ROLES_ADMINISTRATION)

    @application.get("/entities/{code}/administration", dependencies=[Depends(garde)])
    def administration() -> dict[str, str]:
        return {"resultat": "ok"}

    @application.get("/sans-parametre", dependencies=[Depends(garde)])
    def sans_parametre() -> dict[str, str]:  # pragma: no cover — elle doit lever
        return {"resultat": "ok"}

    return application


def _entite(connexion: Connection, code: str, statut: str = "active") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', :statut, 'Europe/Paris', "
            "CASE WHEN :statut_bis = 'draft' THEN NULL ELSE now() END) RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code, "statut": statut, "statut_bis": statut},
    ).scalar_one()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Garde', 'L4T9', 'active') RETURNING id"
        ),
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(connexion: Connection, personne: uuid.UUID, entite: uuid.UUID) -> None:
    connexion.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:personne, :entite, :arrivee, 'active', 'consultant', 'draft')"
        ),
        {"personne": personne, "entite": entite, "arrivee": (ANCRAGE - 30 * JOUR).date()},
    )


def _responsabilite(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    type_responsabilite: str,
    *,
    fin: dt.datetime | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at, ends_at) "
            "VALUES (:personne, :entite, :type_resp, :personne_bis, :debut, :fin)"
        ),
        {
            "personne": personne,
            "personne_bis": personne,
            "entite": entite,
            "type_resp": type_responsabilite,
            "debut": ANCRAGE - 10 * JOUR,
            "fin": fin,
        },
    )


def _client(
    cx: Connection,
    parametres: Parametres,
    personne: uuid.UUID | None = None,
    *,
    lever: bool = True,
) -> TestClient:
    """Un client HTTP porteur du cookie, comme un navigateur.

    **LE COOKIE EST POSE SUR LE CLIENT, PAS SUR LA REQUETE.** `TestClient`
    deprecie la seconde forme, et son motif est bon : la persistance des cookies
    par requete est ambigue. Un navigateur, lui, porte son cookie.
    """
    #  `raise_server_exceptions` se lit A LA CONSTRUCTION : le poser apres coup
    #  n'a aucun effet, et le test du garde-fou de montage echouait pour cela.
    client = TestClient(_application(parametres), raise_server_exceptions=lever)
    if personne is not None:
        client.cookies.update(_cookie(cx, personne, parametres))
    return client


def _cookie(cx: Connection, personne: uuid.UUID, parametres: Parametres) -> dict[str, str]:
    """Ouvrir une vraie session et rendre le cookie que le navigateur enverrait.

    **LA SESSION EST REELLE, PAS SIMULEE.** Un test qui contournerait
    `ouvrir_une_session` n'eprouverait pas le chemin que la production emprunte —
    c'est la lecon `T8` du LOT 1 : un test qui court-circuite le point d'entree
    reel ne prouve pas ce qu'il croit.
    """
    jeton, _ = ouvrir_une_session(
        cx,
        personne=personne,
        instant=dt.datetime.now(tz=dt.UTC),
        jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
    )
    #  **LE COMMIT EST INDISPENSABLE, ET SON ABSENCE RENDAIT 401.** L'API lit sur
    #  une AUTRE connexion : une session en transaction ouverte lui est invisible,
    #  et le garde-fou refusait alors pour absence de session au lieu d'absence de
    #  role. **Les deux refus sont differents et le test le distingue** — 401
    #  contre 403 — donc l'erreur s'est nommee elle-meme. C'est pour cela que
    #  l'ordre des refus est teste separement.
    cx.commit()
    return {parametres.SESSION_COOKIE_NAME: jeton}


# ============================================================================
#  1. Le garde-fou refuse, et il refuse la BONNE chose
# ============================================================================


@pytest.mark.integration
def test_un_EMPLOYE_sans_responsabilite_est_REFUSE(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """§24.1 : « un employe consulte toutes les entites mais ne modifie aucune autre ».

    C'est la requete CONSTRUITE A LA MAIN du §24.20 : le menu ne proposait rien,
    et l'appel arrive quand meme.
    """
    a = _entite(cx, "T9-EMP-A")
    p = _personne(cx, "t9-emp@exalt-company.com")
    _appartenance(cx, p, a)
    cx.commit()

    with _client(cx, parametres_de_la_stack, p) as client:
        reponse = client.get("/entities/T9-EMP-A/administration")

    assert reponse.status_code == 403
    corps = reponse.json()
    assert corps["erreur"]["code"] == "acces_refuse"
    #  **LE MOTIF NE SORT PAS.** Ni le role manquant, ni l'entite principale : les
    #  distinguer serait un oracle, et on apprendrait ou sont les administrateurs.
    for interdit in ("ESM", "ADM-E", "SUPER", "principale", "responsabilite active"):
        assert interdit not in corps["erreur"]["message"], (
            f"le message nomme « {interdit} », donc il renseigne l'appelant"
        )


@pytest.mark.integration
def test_un_ESM_de_SON_entite_est_ACCEPTE_le_temoin_qui_donne_un_sens_aux_refus(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """LE TEMOIN CENTRAL. Sans lui, tous les 403 seraient satisfaits par un garde
    qui refuse tout le monde — le defaut mesure en `T1`, ou un `Annotated` mal
    place rendait 422 a chacun en paraissant proteger.
    """
    a = _entite(cx, "T9-ESM-A")
    p = _personne(cx, "t9-esm@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value)
    cx.commit()

    with _client(cx, parametres_de_la_stack, p) as client:
        reponse = client.get("/entities/T9-ESM-A/administration")

    assert reponse.status_code == 200, reponse.text
    assert reponse.json() == {"resultat": "ok"}


@pytest.mark.integration
def test_le_MEME_ESM_est_REFUSE_dans_une_AUTRE_entite(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """§24.7 et §5.1 : « ses responsabilites [...] ne s'appliquent pas ».

    **LE MEME APPELANT, LA MEME SESSION, DEUX ENTITES.** C'est ce qui distingue ce
    test d'un simple « un inconnu est refuse » : la seule variable est l'entite du
    chemin, donc l'echec ne peut avoir aucune autre cause.
    """
    a = _entite(cx, "T9-DEUX-A")
    b = _entite(cx, "T9-DEUX-B")
    p = _personne(cx, "t9-deux@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value)
    cx.commit()

    with _client(cx, parametres_de_la_stack, p) as client:
        chez_lui = client.get("/entities/T9-DEUX-A/administration")
        ailleurs = client.get("/entities/T9-DEUX-B/administration")

    assert chez_lui.status_code == 200, chez_lui.text
    assert ailleurs.status_code == 403, (
        "le §5.1 interdit que la responsabilite s'applique ailleurs, et l'entite B existe"
    )
    assert b is not None


@pytest.mark.integration
def test_un_role_CLOTURE_n_ouvre_plus_la_route(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """§24.12 : « un role cloture ne continue pas a accorder des permissions »."""
    a = _entite(cx, "T9-CLOS-A")
    p = _personne(cx, "t9-clos@exalt-company.com")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value, fin=ANCRAGE - 5 * JOUR)
    cx.commit()

    with _client(cx, parametres_de_la_stack, p) as client:
        reponse = client.get("/entities/T9-CLOS-A/administration")

    assert reponse.status_code == 403


@pytest.mark.integration
def test_le_SUPER_ADMINISTRATEUR_ouvre_la_route_PARTOUT(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """§5.1 : « le super-administrateur constitue la seule exception globale »."""
    a = _entite(cx, "T9-SUPER-A")
    b = _entite(cx, "T9-SUPER-B")
    p = _personne(cx, "t9-super@exalt-company.com")
    _appartenance(cx, p, a)
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, "
            "starts_at, ends_at) VALUES (:p, NULL, :r, :d, NULL)"
        ),
        {"p": p, "r": TypeRoleTechnique.SUPER_ADMIN.value, "d": ANCRAGE - JOUR},
    )
    cx.commit()

    with _client(cx, parametres_de_la_stack, p) as client:
        assert client.get("/entities/T9-SUPER-A/administration").status_code == 200
        assert client.get("/entities/T9-SUPER-B/administration").status_code == 200
    assert b is not None


@pytest.mark.integration
def test_sans_session_le_garde_rend_401_et_non_403(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """**L'ORDRE DES REFUS COMPTE.** Un 403 sans session dirait « vous etes connu
    mais sans droit », ce qui est faux et renseigne l'appelant sur l'existence de
    la ressource. La session se verifie d'abord.
    """
    a = _entite(cx, "T9-ANON-A")
    cx.commit()

    with _client(cx, parametres_de_la_stack) as client:
        reponse = client.get("/entities/T9-ANON-A/administration")

    assert reponse.status_code == 401
    assert a is not None


@pytest.mark.integration
def test_une_entite_NON_ACTIVE_rend_404_et_non_403(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Verification 7 du §2.6, « l'etat de la ressource ».

    Et le meme 404 qu'ailleurs : pour l'appelant, une entite `draft` n'existe pas.
    Rendre 403 apprendrait qu'elle existe.
    """
    d = _entite(cx, "T9-DRAFT-D", statut="draft")
    p = _personne(cx, "t9-draft@exalt-company.com")
    a = _entite(cx, "T9-DRAFT-A")
    _appartenance(cx, p, a)
    _responsabilite(cx, p, a, TypeResponsabilite.ESM.value)
    cx.commit()

    with _client(cx, parametres_de_la_stack, p) as client:
        reponse = client.get("/entities/T9-DRAFT-D/administration")

    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "entite_introuvable"
    assert d is not None


# ============================================================================
#  2. Les garde-fous de PROGRAMMATION — ils doivent etre bruyants
# ============================================================================


def test_une_liste_de_roles_VIDE_leve_a_la_construction(
    parametres_de_la_stack: Parametres,
) -> None:
    """Une route gardee par un ensemble vide serait MORTE, en silence.

    Elle refuserait tout le monde, y compris le super-administrateur, et rien ne
    le dirait. Le refus est donc une exception de programmation, pas un 403.
    """
    with pytest.raises(ValueError, match="sans aucun role"):
        exiger_un_role_dans_l_entite(parametres_de_la_stack, [])


def test_les_roles_sont_FIGES_a_la_construction(parametres_de_la_stack: Parametres) -> None:
    """Un iterable consomme une seule fois rendrait la dependance vraie au premier
    appel et fausse aux suivants, EN SILENCE. Le `frozenset` est pris une fois.
    """
    generateur = (role for role in ROLES_ADMINISTRATION)
    garde = exiger_un_role_dans_l_entite(parametres_de_la_stack, generateur)
    #  Le generateur est desormais epuise ; la dependance doit rester valide.
    assert list(generateur) == []
    assert garde is not None


@pytest.mark.integration
def test_une_route_SANS_parametre_de_chemin_leve_au_lieu_de_refuser_tout_le_monde(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """**LE DEFAUT QUE CE TEST EMPECHE EST SILENCIEUX.** Une route gardee montee
    sans `{code}` ferait lire `None` a la dependance : l'entite serait introuvable,
    et la route rendrait **404 pour tout le monde en paraissant sure**. C'est
    exactement la classe du §7.0, quatrieme proposition.

    Une erreur de montage doit etre BRUYANTE, et un 500 l'est.
    """
    p = _personne(cx, "t9-montage@exalt-company.com")
    a = _entite(cx, "T9-MONTAGE-A")
    _appartenance(cx, p, a)
    cx.commit()

    #  `lever=False` pour OBSERVER le 500 plutot que de laisser l'exception
    #  remonter dans le test : c'est le code HTTP qui est le critere.
    with _client(cx, parametres_de_la_stack, p, lever=False) as client:
        reponse = client.get("/sans-parametre")

    assert reponse.status_code == 500, (
        "une route gardee sans parametre de chemin doit LEVER, pas refuser silencieusement"
    )


#  Prefixes ENTITE-LESS, jamais gardes par `exiger_un_role_dans_l_entite` — la
#  dependance EXIGE un parametre de chemin `code` (voir son propre docstring),
#  structurellement absent d'une ressource GLOBALE. `POST /bug-reports` (T11)
#  n'avait aucune accolade et echappait deja au filtre ci-dessous ; les routes
#  `/alerts/...` (LOT 10, T13 — `operational_alert` ne porte aucun `entity_id`,
#  voir `app/support/perimetre_alertes.py`) sont les PREMIERES a porter un
#  parametre de chemin SANS jamais porter `{code}` — meme motif structurel,
#  exclusion explicite plutot qu'un filtre elargi qui masquerait une vraie
#  faute de frappe ailleurs.
_PREFIXES_SANS_GARDE_D_ENTITE = ("/api/v1/alerts",)


def test_le_nom_du_parametre_de_chemin_est_celui_du_CONTRAT() -> None:
    """`PARAMETRE_DE_CHEMIN` doit valoir le nom que les routes emploient.

    Une faute de frappe ici serait SILENCIEUSE — voir le test precedent. Le nom
    est donc confronte au **manifeste du contrat**, qui est la source unique lue
    par TypeScript et par Python (`DEC-492`), et non a une chaine recopiee.

    **La premiere version de ce test importait un module que j'avais invente.**
    Il aurait echoue a la collecte — bruyamment, donc sans danger — mais il
    n'aurait rien confronte. §7.10 : inspecte ce qui existe, ne te fie pas a ta
    memoire d'une API.
    """
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    gabarits = [
        point["chemin"]
        for point in manifeste["endpoints"]
        if "{" in point["chemin"] and not point["chemin"].startswith(_PREFIXES_SANS_GARDE_D_ENTITE)
    ]
    assert gabarits, "aucun gabarit parametre dans le contrat : le test ne prouverait rien"
    for gabarit in gabarits:
        assert f"{{{PARAMETRE_DE_CHEMIN}}}" in gabarit, (
            f"le gabarit {gabarit} ne porte pas `{{{PARAMETRE_DE_CHEMIN}}}` : la dependance "
            f"lirait `None` et la route refuserait tout le monde en silence"
        )


def test_les_roles_d_administration_sont_CEUX_DU_PARAGRAPHE_20() -> None:
    """Le manifeste declare `ESM`, `ADM-E`, `SUPER` — trois, et pas deux.

    **CE TEST DECLARE UNE INTERPRETATION ET EXIGE QU'ELLE TIENNE**, ce qui est ce
    que le §7.27 prescrit d'une liste que rien d'autre ne porte. Le §20 de la
    matrice donne une colonne a ces trois roles et a aucun autre ; si la liste du
    manifeste changeait, ce test le dirait, et celui qui la change devrait relire
    le §20.

    **Et l'inclusion de `ESM` est le point le plus facile a perdre** : l'intuition
    dit « administrateur d'entite et super-administrateur ». Le §20 lui donne
    quatre actions d'attribution que `ADM-E` n'a pas.
    """
    assert ROLES_ADMINISTRATION == (
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    )
    #  Et `EMP` n'y est PAS : ce serait ouvrir l'administration a tout le monde.
    assert RoleDeLaMatrice.EMPLOYE not in ROLES_ADMINISTRATION
