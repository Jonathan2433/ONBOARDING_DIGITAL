"""Comptes de service et scopes — story `MVP-L03-US007`, cahier §22, modele §10.5.

LOT 3, sous-etape `T10`.

LE CRITERE A TROIS MOITIES, ET CHACUNE A SON TEMOIN

  « Un jeton **hors scope** est refuse · l'**expiration** est effective · **chaque
  appel** est audite ».

  Sans temoin, un mecanisme qui refuserait TOUT passerait les trois : le jeton
  legitime avec le bon scope doit passer, et il est verifie a chaque fois.

DEUX CHOSES QUE CE FICHIER PROUVE ET QU'ON POURRAIT CROIRE ACQUISES

  1. **les cinq scopes sont RELUS dans le cahier**, et le fait que la liste soit
     ouverte l'est aussi -- « par exemple ». Une liste recopiee vieillit au premier
     ajout, §7.27 ;
  2. **la trace est conservee meme quand l'appel est refuse.** Un jeton vivant d'un
     compte desactive met `last_used_at` a jour PUIS est refuse : mettre l'etat du
     compte dans la clause `WHERE` aurait perdu cette trace, or un compte desactive
     qu'on continue de solliciter est exactement ce qu'un operateur veut voir.

LE TEMPS S'INJECTE — AUCUN TEST N'ATTEND UNE EXPIRATION

  Un jeton de 90 jours ne s'attend pas. L'instant est un parametre partout, et
  l'expiration est eprouvee en interrogeant a un instant posterieur.
"""

from __future__ import annotations

import datetime as dt
import json as _json
import re
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.auth.comptes_de_service import (
    MOTIF_COMPTE_DESACTIVE,
    MOTIF_JETON_ACCEPTE,
    MOTIF_JETON_INCONNU,
    MOTIF_JETON_MAL_FORME,
    MOTIF_JETON_PERIME_OU_REVOQUE,
    MOTIF_SCOPE_MANQUANT,
    Authentification,
    DureeRefusee,
    authentifier_un_jeton,
    creer_un_jeton,
    engendrer_un_jeton_de_service,
    revoquer_un_jeton,
)
from app.auth.dependances import exiger_un_scope
from app.auth.jetons import empreinte_de_jeton
from app.auth.scopes import (
    MOTIF_SCOPE,
    SCOPES_DU_CAHIER,
    SCOPES_MAXIMUM_PAR_JETON,
    ScopeInvalide,
    controler_les_scopes,
    couvre,
)
from app.configuration.settings import Parametres
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative, gerer_erreur_applicative

CAHIER = Path(__file__).resolve().parents[3] / "docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md"
INSTANT = dt.datetime(2026, 8, 22, 12, 0, tzinfo=dt.UTC)
PLAFOND = 90


# ===========================================================================
#  Les scopes : RELUS dans le cahier, jamais recopies
# ===========================================================================


def test_les_cinq_scopes_sont_ceux_du_CAHIER_relu() -> None:
    """**LE CONTROLE QUI AURAIT ATTRAPE `ECART-036`.**

    Le §8 de la fiche annonçait « aucun document n'enumere » les scopes. Le §22 en
    donne cinq. Ce test relit le cahier : une liste modifiee a la main, ou un
    cahier qui changerait, font echouer la suite au lieu de passer en silence.
    """
    texte = CAHIER.read_text(encoding="utf-8")
    section = texte[texte.index("## 22. Comptes de service") : texte.index("### 22.1")]
    trouves = tuple(re.findall(r"^([a-z][a-z0-9_]*:[a-z][a-z0-9_]*)$", section, re.MULTILINE))
    assert trouves == SCOPES_DU_CAHIER, f"le cahier §22 enumere {trouves}"


def test_le_cahier_dit_PAR_EXEMPLE_donc_la_liste_n_est_PAS_fermee() -> None:
    """**LA NUANCE QUI COMMANDE LA VALIDATION.**

    « Chaque compte de service possede des scopes explicites, **par exemple** : … ».
    Une liste blanche fermee contredirait ces deux mots et bloquerait le LOT 9 --
    qui creera ses propres scopes d'import. La validation porte donc sur la FORME.

    Si le cahier fermait un jour sa liste, ce test echouerait — et il devrait.
    """
    texte = CAHIER.read_text(encoding="utf-8")
    assert "des scopes explicites, par exemple" in texte


def test_les_cinq_scopes_respectent_la_forme_DERIVEE_d_eux() -> None:
    """La forme n'est pas inventee : elle est celle que les cinq exemples partagent."""
    for scope in SCOPES_DU_CAHIER:
        assert MOTIF_SCOPE.match(scope), scope


@pytest.mark.parametrize(
    "mauvais",
    [
        "People:read",  # majuscule
        "people read",  # espace
        "people:",  # action absente
        ":read",  # domaine absent
        "people:read:extra",  # deux separateurs
        "people-read",  # pas de separateur
        "1people:read",  # commence par un chiffre
        "",
    ],
)
def test_une_forme_INVALIDE_est_refusee(mauvais: str) -> None:
    """Le message nomme la valeur : un scope n'est pas une donnee personnelle."""
    with pytest.raises(ScopeInvalide, match="scope invalide"):
        controler_les_scopes([mauvais])


def test_une_liste_VIDE_est_refusee() -> None:
    """Un jeton sans scope n'accorde rien — mais il EXISTE, et c'est un piege."""
    with pytest.raises(ScopeInvalide, match="vide"):
        controler_les_scopes([])


def test_un_DOUBLON_est_refuse_et_non_deduplique() -> None:
    """Dedupliquer accepterait une liste fautive en silence — §7.25."""
    with pytest.raises(ScopeInvalide, match="double"):
        controler_les_scopes(["people:read", "people:read"])


def test_TROP_de_scopes_est_refuse() -> None:
    """`RIGHTS-018` : « scopes limites au besoin exact »."""
    with pytest.raises(ScopeInvalide, match="maximum"):
        controler_les_scopes([f"domaine{i}:action" for i in range(SCOPES_MAXIMUM_PAR_JETON + 1)])


def test_une_valeur_qui_n_est_PAS_une_liste_est_refusee() -> None:
    """La valeur peut venir d'un `jsonb`, donc de la base, donc de n'importe quoi."""
    for mauvaise in ("people:read", 42, None, {"people": "read"}):
        with pytest.raises(ScopeInvalide, match="liste est attendue"):
            controler_les_scopes(mauvaise)


def test_couvre_est_EXACT_sans_joker_ni_hierarchie() -> None:
    """**LE TEMOIN QUI DIT CE QUE LE MECANISME NE FAIT PAS.**

    Le cahier n'ecrit AUCUNE hierarchie de scopes. En inventer une accorderait des
    droits que personne n'a accordes — ce que `RIGHTS-018` interdit.
    """
    accordes = ("people:read", "email:send")
    assert couvre(accordes, "people:read") is True
    assert couvre(accordes, "email:send") is True
    #  Ni joker, ni prefixe, ni implication.
    assert couvre(accordes, "people:import") is False
    assert couvre(("people:*",), "people:read") is False
    assert couvre(("people:import",), "people:read") is False


def test_le_jeton_porte_le_prefixe_de_la_FAMILLE() -> None:
    """`ost_` vient de `observabilite.masquage`, source unique.

    Les trois barrieres de masquage et la regle Gitleaks le connaissent deja :
    `T10` n'a rien a y ajouter, et ce test le prouve plutot que de l'affirmer.
    """
    from observabilite.masquage import PREFIXE_JETON_DE_SERVICE, PREFIXES_DE_JETON

    jeton = engendrer_un_jeton_de_service()
    assert jeton.startswith(PREFIXE_JETON_DE_SERVICE)
    assert PREFIXE_JETON_DE_SERVICE in PREFIXES_DE_JETON
    assert len(jeton) > 40
    assert engendrer_un_jeton_de_service() != jeton


def test_le_plafond_par_defaut_est_l_arbitrage_de_QO_072() -> None:
    """90 jours, arbitrage de Jonathan du 22/08/2026, `QO-072` close.

    **ET IL RESTE CONFIGURABLE**, ce que le §10.5 exige littéralement — a l'inverse
    des seuils de debit du §20.2, que `T8` a poses en constantes.
    """
    from conftest import VARIABLES_MINIMALES

    assert Parametres.model_validate(dict(VARIABLES_MINIMALES)).SERVICE_TOKEN_MAX_DAYS == PLAFOND
    surcharge = Parametres.model_validate({**VARIABLES_MINIMALES, "SERVICE_TOKEN_MAX_DAYS": 7})
    assert surcharge.SERVICE_TOKEN_MAX_DAYS == 7


# ===========================================================================
#  Le decor reel
# ===========================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`.")


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    " account_state) VALUES (:a, :a, 'Service', 'T10', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


def _compte(
    cx: Connection, nom: str, proprietaire: uuid.UUID, *, etat: str = "active"
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO service_account (name, description, entity_id, state, "
                    " technical_owner_person_id) "
                    "VALUES (:nom, 'Compte de verification', NULL, :etat, :p) RETURNING id"
                ),
                {"nom": nom, "etat": etat, "p": proprietaire},
            ).scalar_one()
        )
    )


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str, uuid.UUID]]:
    """Une personne proprietaire, un compte de service ACTIF, et une borne de temps.

    Le nettoyage retire `auth_event` d'abord : depuis la migration `0013`, la
    colonne `service_account_id` porte une cle etrangere vers `service_account`, et
    l'omettre bloquerait la suppression du compte. **C'est la sixieme fois de ce lot
    qu'une table nouvelle rend un nettoyage incomplet** — §7.21.
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t10api{uuid.uuid4().hex[:10]}"
    adresse = f"{marqueur}@exalt-t10.test"
    #  **L'INSTANT DE DEPART EST RELEVE AVANT TOUT, ET C'EST UN CORRECTIF `T10-2`.**
    #  Un jeton MAL FORME ou INCONNU refuse produit un evenement sans acteur -- ni
    #  personne, ni compte -- donc il echappe aux deux filtres par identite. Treize
    #  lignes sont restees en base a ma premiere execution.
    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    with moteur(parametres_de_la_stack).begin() as cx:
        proprietaire = _personne(cx, adresse)
        compte = _compte(cx, marqueur, proprietaire)
    try:
        yield parametres_de_la_stack, marqueur, compte
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE service_account_id IN "
                "(SELECT id FROM service_account WHERE name LIKE :motif)",
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM service_token WHERE service_account_id IN "
                "(SELECT id FROM service_account WHERE name LIKE :motif)",
                "DELETE FROM service_account WHERE name LIKE :motif",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                #  **SIXIEME OCCURRENCE DANS CE LOT**, et j'ai ecrit cette lecon
                #  dans le compte rendu de `T9` une sous-etape plus tot : *la trace
                #  d'un refus SANS ACTEUR echappe a tout nettoyage par identite.*
                #  Seule la borne temporelle l'attrape, et elle ne vieillit pas.
                #  Aucun type d'evenement n'est nomme ici -- lecon `T5-6`.
                "DELETE FROM auth_event WHERE person_id IS NULL "
                "  AND service_account_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(text(requete), {"motif": f"{marqueur}%", "debut": debut})


def _jeton(
    parametres: Parametres,
    compte: uuid.UUID,
    scopes: tuple[str, ...] = ("people:read",),
    *,
    jours: int = 30,
    instant: dt.datetime = INSTANT,
) -> tuple[str, uuid.UUID]:
    with moteur(parametres).begin() as cx:
        return creer_un_jeton(
            cx,
            compte=compte,
            scopes=scopes,
            instant=instant,
            jours=jours,
            jours_maximum=PLAFOND,
        )


def _authentifier(
    parametres: Parametres, jeton: str, scope: str, *, instant: dt.datetime = INSTANT
) -> Authentification:
    with moteur(parametres).begin() as cx:
        return authentifier_un_jeton(cx, jeton=jeton, instant=instant, scope_requis=scope)


def _evenements(parametres: Parametres, compte: uuid.UUID) -> list[tuple[str, str]]:
    with moteur(parametres).connect() as cx:
        return [
            (r[0], r[1])
            for r in cx.execute(
                text(
                    "SELECT event_type, detail FROM auth_event "
                    "WHERE service_account_id = :c ORDER BY occurred_at, id"
                ),
                {"c": compte},
            )
        ]


# ===========================================================================
#  LE CRITERE
# ===========================================================================


@pytest.mark.integration
def test_TEMOIN_un_jeton_avec_le_BON_scope_est_accepte(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """**LE TEMOIN, ET IL VIENT D'ABORD.** Sans lui, un mecanisme qui refuserait
    tout passerait les trois moities du critere.
    """
    parametres, _, compte = decor
    jeton, _ = _jeton(parametres, compte, ("people:read", "email:send"))
    verdict = _authentifier(parametres, jeton, "people:read")
    assert verdict.reussie is True
    assert verdict.compte == compte
    assert verdict.scopes == ("people:read", "email:send")
    assert _evenements(parametres, compte) == [("LOGIN_SUCCESS", MOTIF_JETON_ACCEPTE)]


@pytest.mark.integration
def test_UN_JETON_HORS_SCOPE_est_refuse(decor: tuple[Parametres, str, uuid.UUID]) -> None:
    """**PREMIERE MOITIE DU CRITERE**, littéralement.

    Le jeton est parfaitement valide : il n'a simplement pas ce scope-la. Le compte
    n'est PAS rendu sur un refus — le rendre inviterait a s'en servir.
    """
    parametres, _, compte = decor
    jeton, _ = _jeton(parametres, compte, ("people:read",))
    verdict = _authentifier(parametres, jeton, "people:import")
    assert verdict.reussie is False
    assert verdict.motif == MOTIF_SCOPE_MANQUANT
    assert verdict.compte is None
    assert _evenements(parametres, compte) == [("LOGIN_FAILURE", MOTIF_SCOPE_MANQUANT)]


@pytest.mark.integration
def test_L_EXPIRATION_EST_EFFECTIVE_sans_attendre(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """**DEUXIEME MOITIE DU CRITERE, et le temps est INJECTE.**

    Un jeton de 30 jours ne s'attend pas. On interroge a un instant posterieur, et
    la borne est **semi-ouverte** : a l'instant exact de l'expiration, le jeton est
    perime — comme le magic link de `T4`.
    """
    parametres, _, compte = decor
    jeton, _ = _jeton(parametres, compte, jours=30)
    peremption = INSTANT + dt.timedelta(days=30)

    #  Un instant AVANT : accepte.
    assert _authentifier(
        parametres, jeton, "people:read", instant=peremption - dt.timedelta(seconds=1)
    ).reussie
    #  A l'instant EXACT : refuse. `expires_at > instant`, non `>=`.
    refus = _authentifier(parametres, jeton, "people:read", instant=peremption)
    assert refus.reussie is False
    #  **PERIME, ET NON INCONNU** : le refus est ATTRIBUE au compte, sinon l'audit
    #  ne dirait pas qui s'obstine avec une cle morte. C'est mon propre controle
    #  `service-check` qui l'a trouve, en comptant deux evenements au lieu de trois.
    assert refus.motif == MOTIF_JETON_PERIME_OU_REVOQUE
    assert _evenements(parametres, compte)[-1] == ("LOGIN_FAILURE", MOTIF_JETON_PERIME_OU_REVOQUE)


@pytest.mark.integration
def test_CHAQUE_APPEL_pose_last_used_at_ET_un_evenement(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """**TROISIEME MOITIE DU CRITERE** : « chaque appel est audite ».

    Le §10.5 declare « la derniere utilisation », et l'`UPDATE … RETURNING` la pose
    **dans la meme operation** que la verification : une trace posee dans un second
    temps peut manquer.
    """
    parametres, _, compte = decor
    jeton, identifiant = _jeton(parametres, compte)
    for rang in range(3):
        instant = INSTANT + dt.timedelta(minutes=rang)
        _authentifier(parametres, jeton, "people:read", instant=instant)
        with moteur(parametres).connect() as cx:
            derniere = cx.execute(
                text("SELECT last_used_at FROM service_token WHERE id = :i"),
                {"i": identifiant},
            ).scalar_one()
        assert derniere == instant, f"appel {rang + 1} : `last_used_at` n'a pas suivi"
    assert len(_evenements(parametres, compte)) == 3


@pytest.mark.integration
def test_UN_JETON_REVOQUE_est_refuse_et_la_revocation_est_IDEMPOTENTE(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """§22.1 : « les jetons sont revocables et expirables »."""
    parametres, _, compte = decor
    jeton, identifiant = _jeton(parametres, compte)
    with moteur(parametres).begin() as cx:
        assert revoquer_un_jeton(cx, identifiant=identifiant, instant=INSTANT) is True
        #  Idempotente : la seconde fois ne deplace pas `revoked_at`.
        assert revoquer_un_jeton(cx, identifiant=identifiant, instant=INSTANT) is False
    assert _authentifier(parametres, jeton, "people:read").reussie is False


@pytest.mark.integration
def test_UN_COMPTE_DESACTIVE_est_refuse_MAIS_la_trace_est_CONSERVEE(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """**LA RAISON POUR LAQUELLE L'ETAT N'EST PAS DANS LA CLAUSE `WHERE`.**

    Mettre `state = 'active'` dans l'`UPDATE` aurait ete plus court, et aurait
    **perdu `last_used_at`** : un compte desactive qu'on continue de solliciter est
    exactement ce qu'un operateur veut voir.
    """
    parametres, _, compte = decor
    jeton, identifiant = _jeton(parametres, compte)
    with moteur(parametres).begin() as cx:
        cx.execute(
            text("UPDATE service_account SET state = 'disabled' WHERE id = :c"), {"c": compte}
        )
    verdict = _authentifier(parametres, jeton, "people:read")
    assert verdict.reussie is False
    assert verdict.motif == MOTIF_COMPTE_DESACTIVE
    with moteur(parametres).connect() as cx:
        derniere = cx.execute(
            text("SELECT last_used_at FROM service_token WHERE id = :i"), {"i": identifiant}
        ).scalar_one()
    assert derniere == INSTANT, "la trace a ete perdue : l'etat est dans la clause WHERE"


@pytest.mark.integration
def test_UN_JETON_INCONNU_produit_un_evenement_SANS_ACTEUR(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """Meme cas qu'un magic link demande pour une adresse inconnue.

    `ck_auth_event_un_seul_acteur` le permet expressement : les deux nuls restent
    autorises, et l'interdire casserait la reponse generique de `T3`.
    """
    parametres, _, _ = decor
    with moteur(parametres).connect() as cx:
        avant = cx.execute(
            text(
                "SELECT count(*) FROM auth_event WHERE person_id IS NULL "
                "  AND service_account_id IS NULL AND detail = :m"
            ),
            {"m": MOTIF_JETON_INCONNU},
        ).scalar_one()
    verdict = _authentifier(parametres, "ost_" + "z" * 43, "people:read")
    assert verdict.motif == MOTIF_JETON_INCONNU
    with moteur(parametres).connect() as cx:
        apres = cx.execute(
            text(
                "SELECT count(*) FROM auth_event WHERE person_id IS NULL "
                "  AND service_account_id IS NULL AND detail = :m"
            ),
            {"m": MOTIF_JETON_INCONNU},
        ).scalar_one()
    assert apres == avant + 1


@pytest.mark.integration
def test_UNE_VALEUR_QUI_N_EST_PAS_UN_JETON_ne_touche_PAS_la_base(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """La forme est verifiee AVANT toute requete : `token_hash` est unique, donc une
    requete par valeur arbitraire serait une sonde gratuite.
    """
    parametres, _, _ = decor
    assert _authentifier(parametres, "pas-un-jeton", "people:read").motif == MOTIF_JETON_MAL_FORME
    assert _authentifier(parametres, "", "people:read").motif == MOTIF_JETON_MAL_FORME


@pytest.mark.integration
def test_UNE_DUREE_AU_DELA_DU_PLAFOND_LEVE_et_n_ecrete_PAS(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """Ecreter en silence ferait qu'un appelant croirait avoir obtenu un an."""
    parametres, _, compte = decor
    with pytest.raises(DureeRefusee, match="depasse le plafond"), moteur(parametres).begin() as cx:
        creer_un_jeton(
            cx,
            compte=compte,
            scopes=("people:read",),
            instant=INSTANT,
            jours=PLAFOND + 1,
            jours_maximum=PLAFOND,
        )
    for mauvais in (0, -1):
        with pytest.raises(DureeRefusee, match="n'a pas de sens"), moteur(parametres).begin() as cx:
            creer_un_jeton(
                cx,
                compte=compte,
                scopes=("people:read",),
                instant=INSTANT,
                jours=mauvais,
                jours_maximum=PLAFOND,
            )


@pytest.mark.integration
def test_LE_JETON_N_EST_JAMAIS_EN_CLAIR_EN_BASE(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """Le §10.5 dit « un hash du jeton ». Verifie sur la colonne REELLE."""
    parametres, _, compte = decor
    jeton, identifiant = _jeton(parametres, compte)
    with moteur(parametres).connect() as cx:
        stocke = cx.execute(
            text("SELECT token_hash FROM service_token WHERE id = :i"), {"i": identifiant}
        ).scalar_one()
    assert stocke != jeton
    assert stocke == empreinte_de_jeton(jeton)
    assert re.fullmatch(r"[0-9a-f]{64}", stocke)


@pytest.mark.integration
def test_UN_EVENEMENT_NE_PEUT_PORTER_LES_DEUX_ACTEURS(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """`ck_auth_event_un_seul_acteur`, migration `0013`.

    Un evenement qui porterait a la fois une personne et un compte de service
    n'aurait pas de sens : on ne saurait pas qui a agi.
    """
    parametres, marqueur, compte = decor
    with moteur(parametres).connect() as cx:
        personne = cx.execute(
            text("SELECT id FROM person WHERE email_normalized LIKE :m"), {"m": f"{marqueur}%"}
        ).scalar_one()
    attendu = "ck_auth_event_un_seul_acteur"
    with pytest.raises(IntegrityError, match=attendu), moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "INSERT INTO auth_event (event_type, occurred_at, person_id, "
                " service_account_id) VALUES ('LOGIN_SUCCESS', :i, :p, :c)"
            ),
            {"i": INSTANT, "p": personne, "c": compte},
        )


# ===========================================================================
#  La dependance de route
# ===========================================================================


def _application(parametres: Parametres, scope: str) -> FastAPI:
    """Une application MINIMALE portant une route protegee par un scope.

    **AUCUNE ROUTE DE PRODUCTION N'EST INVENTEE.** Le §22 ne dit pas quelles routes
    un compte de service peut appeler, et aucune route metier n'existe -- le portail
    est le LOT 4. Cette application vit dans le test, et le residuel est nomme dans
    l'en-tete de `dependances.py`.
    """
    application = FastAPI()
    application.add_exception_handler(ErreurApplicative, gerer_erreur_applicative)
    #  **LA DEPENDANCE EST PASSEE PAR `dependencies=`, ET NON EN DEFAUT
    #  D'ARGUMENT.** `B008` interdit un appel de fonction dans un defaut, et il a
    #  raison : le defaut est evalue une fois a la definition. Ici la fabrique DOIT
    #  etre appelee une fois, mais l'exprimer en defaut le cache -- et c'est aussi
    #  la forme que les futures routes metier emploieront, puisqu'elles n'ont pas
    #  besoin du verdict lui-meme.
    garde = exiger_un_scope(parametres, scope)

    @application.get("/protege", dependencies=[Depends(garde)])
    def protege() -> dict[str, str]:
        return {"resultat": "ok"}

    return application


@pytest.mark.integration
def test_LA_DEPENDANCE_refuse_avec_UN_SEUL_GABARIT_pour_QUATRE_causes(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """**403 ET NON 401**, meme motif qu'en `T7` : un jeton valide auquel il manque
    un scope EST authentifie.

    Les quatre causes rendent la MEME reponse : les distinguer dirait a un appelant
    s'il s'est approche.
    """
    parametres, _, compte = decor
    sans_scope, _ = _jeton(parametres, compte, ("email:send",))
    revoque, identifiant = _jeton(parametres, compte, ("people:read",))
    with moteur(parametres).begin() as cx:
        revoquer_un_jeton(cx, identifiant=identifiant, instant=INSTANT)

    gabarits = set()
    with TestClient(_application(parametres, "people:read")) as client:
        for entetes in (
            {},  # en-tete absent
            {"Authorization": "Bearer pas-un-jeton"},  # forme invalide
            {"Authorization": f"Bearer {sans_scope}"},  # scope manquant
            {"Authorization": f"Bearer {revoque}"},  # revoque
        ):
            reponse = client.get("/protege", headers=entetes)
            assert reponse.status_code == 403, entetes
            corps = reponse.json()
            corps["erreur"]["identifiant_correlation"] = "IGNORE"
            gabarits.add(_json.dumps(corps, sort_keys=True))
    assert len(gabarits) == 1, f"les refus se distinguent : {gabarits}"


@pytest.mark.integration
def test_TEMOIN_la_dependance_ACCEPTE_avec_le_bon_scope(
    decor: tuple[Parametres, str, uuid.UUID],
) -> None:
    """Sans ce temoin, une dependance qui refuserait tout passerait le test ci-dessus."""
    parametres, _, compte = decor
    jeton, _ = _jeton(parametres, compte, ("people:read",))
    with TestClient(_application(parametres, "people:read")) as client:
        reponse = client.get("/protege", headers={"Authorization": f"Bearer {jeton}"})
    assert reponse.status_code == 200
    assert reponse.json() == {"resultat": "ok"}
