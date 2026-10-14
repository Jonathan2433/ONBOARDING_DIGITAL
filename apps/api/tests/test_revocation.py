"""Revocation au depart — story `MVP-L03-US006`, cahier §6.2, §7.4, §30.22.

LOT 3, sous-etape `T9`.

CE FICHIER PROUVE QUATRE CHOSES, ET LA DEUXIEME EST CELLE QU'ON OUBLIE

  1. **la revocation a lieu au DEPART**, non au seul archivage. Le §24.1 n'a
     aucune transition `Active --> Archived` : si la revocation ne tenait qu'a
     l'archivage, une session resterait active entre les deux ;
  2. **elle est ATOMIQUE avec le changement d'etat.** Un `rollback` ne doit
     laisser ni l'un ni l'autre -- c'est le critere litteral, et un test qui
     verifierait seulement « la session est revoquee » ne le dit pas ;
  3. **une session revoquee NE REPOND PLUS**, mesure par un aller-retour HTTP
     reel et non deduit de l'ecriture de `revoked_at` ;
  4. **ce qui est rapporte n'est pas traite en silence** : role global conserve,
     autre appartenance active, relation future, consultant orphelin de DSM.

ET UN CAS QUI N'AURAIT ECHOUE QU'EN PRODUCTION

  Le depart d'un **DG**. `fn_dg_implique_dsm_local` exige une responsabilite DSM
  active des que la categorie vaut `dg`, sans regarder l'etat : clore les roles
  avant le changement d'etat fait echouer le depart, avec un message qui parle de
  categorie et non de revocation. Le test l'eprouve.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.auth.sessions import (
    REVOCATION_DEPART,
    ouvrir_une_session,
    revoquer_toutes_les_sessions,
)
from app.configuration.settings import Parametres
from app.main import creer_application
from app.people.modeles import EtatAppartenance
from app.people.services import (
    RELATIONS_DE_L_APPARTENANCE,
    RELATIONS_DE_LA_PERSONNE,
    TRANSITIONS_AUTORISEES,
    Revocation,
    TransitionRefusee,
    archiver_une_appartenance,
    enregistrer_un_depart,
)
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
INSTANT = dt.datetime(2026, 8, 22, 10, 0, tzinfo=dt.UTC)
MODELE = Path(__file__).resolve().parents[3] / "docs/architecture/MODELE_DONNEES_EXALT.md"


# ===========================================================================
#  Les listes declarees, CONFRONTEES au modele
# ===========================================================================


def _relations_du_modele() -> set[str]:
    """Les libelles de relation historisee enumeres par le §25.2, lus dans le modele."""
    texte = MODELE.read_text(encoding="utf-8")
    debut = texte.index("## 25.2 Contraintes temporelles")
    section = texte[debut : texte.index("## 25.3", debut)]
    apres = section.index("Relations concernées :")
    libelles = set()
    for ligne in section[apres:].splitlines()[1:]:
        depouillee = ligne.strip()
        if not depouillee:
            continue
        if not depouillee.startswith("-"):
            break
        libelles.add(depouillee.lstrip("- ").rstrip(" ;."))
    return libelles


def test_les_relations_A_CLORE_couvrent_le_25_2_MOINS_l_appartenance() -> None:
    """**LE CONTROLE ANTI-`ECART-021`, ET IL PORTE SUR MA PROPRE LISTE.**

    Le §25.2 enumere SEPT relations historisees. `entity_membership` est celle
    qu'on archive ; les six autres doivent etre closes. Une septieme relation
    ajoutee au modele fera echouer ce test — c'est son objet, exactement comme
    `TABLES_DECLAREES` du socle.
    """
    declarees = set(RELATIONS_DE_L_APPARTENANCE) | set(RELATIONS_DE_LA_PERSONNE)
    assert len(declarees) == len(_relations_du_modele()) - 1, (
        f"{len(declarees)} relations declarees pour "
        f"{len(_relations_du_modele())} du §25.2 moins l'appartenance"
    )


def test_les_transitions_sont_CELLES_du_24_1_lu_dans_le_modele() -> None:
    """**LE §24.1 N'A AUCUNE TRANSITION `Active --> Archived`**, et tout en decoule.

    Ce test relit le diagramme plutot que de recopier sa lecture : si le modele
    ajoutait un raccourci, la suite echouerait au lieu de passer en silence.
    """
    texte = MODELE.read_text(encoding="utf-8")
    section = texte[texte.index("## 24.1") : texte.index("## 24.2")]
    fleches = {
        (depuis.strip().lower(), vers.strip().lower())
        for depuis, vers in re.findall(r"^\s*(\w+) --> (\w+)", section, re.MULTILINE)
    }
    assert ("active", "archived") not in fleches, (
        "le modele declare desormais `Active --> Archived` : la revocation au "
        "depart n'est plus la seule voie, et ce module doit etre relu"
    )
    for depuis, vers in TRANSITIONS_AUTORISEES:
        assert (depuis, vers) in fleches, f"{depuis} -> {vers} absente du §24.1"


def test_les_reserves_sont_distinguees_d_un_succes_sans_reserve() -> None:
    """Sans cette propriete, un appelant devrait tester quatre champs et en oublier un."""
    net = Revocation(
        appartenance=uuid.uuid4(),
        etat_precedent="active",
        etat_nouveau="departed",
        sessions_revoquees=2,
        liens_invalides=1,
    )
    assert net.a_des_reserves is False

    def sans_reserve() -> Revocation:
        return Revocation(
            appartenance=net.appartenance,
            etat_precedent="active",
            etat_nouveau="departed",
            sessions_revoquees=0,
            liens_invalides=0,
        )

    #  Les trois reserves, une par une : sans l'enumeration, ce test pourrait
    #  n'en avoir exerce qu'une. Trois constructions explicites plutot qu'un
    #  `**dict` : en mode strict, mypy ne peut pas typer un dictionnaire dont les
    #  valeurs sont heterogenes, et le contourner par `Any` retirerait le controle
    #  que ce test est cense avoir.
    from dataclasses import replace

    assert replace(sans_reserve(), roles_globaux_conserves=1).a_des_reserves
    assert replace(sans_reserve(), relations_futures_conservees={"circle": 1}).a_des_reserves
    assert replace(sans_reserve(), consultants_sans_dsm=(uuid.uuid4(),)).a_des_reserves


# ===========================================================================
#  Le decor reel
# ===========================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`.")


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity (code, display_name, city, country_code, status, "
                    " timezone) VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', "
                    " 'Europe/Paris') RETURNING id"
                ),
                {"code": code, "nom": f"Entite {code}"},
            ).scalar_one()
        )
    )


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    " account_state) VALUES (:a, :a, 'Revoc', 'T9', 'active') RETURNING id"
                ),
                {"a": adresse},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    *,
    etat: str = "active",
    categorie: str = "consultant",
    arrivee: dt.date | None = None,
    depart: dt.date | None = None,
) -> uuid.UUID:
    """Une appartenance. **LES DATES SONT PARAMETRABLES, ET C'EST UN CORRECTIF.**

    `ex_entity_membership_sans_chevauchement` est
    `EXCLUDE USING gist (person_id WITH =, period WITH &&)`, **sans predicat
    partiel** : deux appartenances d'une meme personne ne peuvent pas se
    chevaucher, quelle que soit l'entite et quel que soit l'etat. Une seconde
    appartenance n'est donc possible que si la premiere porte deja une
    `departure_date` -- sans quoi sa plage est infinie a droite.

    Je l'ai decouvert en voyant ce test echouer, et c'est la base qui avait
    raison : mon scenario « une autre appartenance active » etait **impossible
    par construction**. Le scenario reel est une arrivee FUTURE dans une autre
    entite, apres une date de depart connue.
    """
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    " departure_date, membership_state, professional_category, "
                    " profile_visibility) VALUES (:p, :e, :arrivee, :depart, :etat, "
                    " :cat, 'draft') RETURNING id"
                ),
                {
                    "p": personne,
                    "e": entite,
                    "etat": etat,
                    "cat": categorie,
                    "arrivee": arrivee or (INSTANT.date() - dt.timedelta(days=30)),
                    "depart": depart,
                },
            ).scalar_one()
        )
    )


def _responsabilite(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    type_: str = "DSM",
    *,
    debut: dt.datetime | None = None,
) -> uuid.UUID:
    """Une responsabilite Framework. **`assigned_by_person_id` EST `NOT NULL`.**

    C'est la quatrieme idee du socle du LOT 2 : le modele decrit une ACTION, et
    une action a un auteur. L'omettre a fait echouer trois de mes tests, et la
    base avait raison -- une trace d'audit sans attributeur serait fausse. La
    personne s'attribue ici elle-meme, ce qui est sans portee dans un decor.
    """
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO framework_responsibility_assignment "
                    "(person_id, entity_id, responsibility_type, assigned_by_person_id, "
                    " starts_at, ends_at) VALUES (:p, :e, :t, :p, :debut, NULL) RETURNING id"
                ),
                {
                    "p": personne,
                    "e": entite,
                    "t": type_,
                    "debut": debut or INSTANT - dt.timedelta(days=10),
                },
            ).scalar_one()
        )
    )


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[tuple[Parametres, str]]:
    """Un marqueur, et un nettoyage qui couvre TOUT ce que `T9` ecrit.

    **LE NETTOYAGE EST LA DIFFICULTE, ET CE LOT L'A MONTRE CINQ FOIS.** Chaque
    sous-etape qui ajoute une table rend incomplets les nettoyages ecrits avant
    elle, et une cle etrangere transforme un nettoyage incomplet en residu, puis
    un residu en echec de tests SANS RAPPORT. Les tables sont donc supprimees
    dans l'ordre des dependances, et la trace sans personne est bornee dans le
    temps -- seule facon de l'atteindre.
    """
    _exiger_postgresql(parametres_de_la_stack)
    marqueur = f"t9api{uuid.uuid4().hex[:10]}"
    with moteur(parametres_de_la_stack).connect() as horloge:
        debut = horloge.execute(text("SELECT now()")).scalar_one()
    try:
        yield (
            parametres_de_la_stack.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST}),
            marqueur,
        )
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            for requete in (
                "DELETE FROM auth_event WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM user_session WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM magic_link_request WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM dsm_assignment WHERE consultant_membership_id IN "
                "(SELECT m.id FROM entity_membership m JOIN person p ON p.id = m.person_id "
                " WHERE p.email_normalized LIKE :motif) OR dsm_person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM circle_membership WHERE entity_membership_id IN "
                "(SELECT m.id FROM entity_membership m JOIN person p ON p.id = m.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM membership_job_assignment WHERE entity_membership_id IN "
                "(SELECT m.id FROM entity_membership m JOIN person p ON p.id = m.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM professional_status_assignment WHERE entity_membership_id IN "
                "(SELECT m.id FROM entity_membership m JOIN person p ON p.id = m.person_id "
                " WHERE p.email_normalized LIKE :motif)",
                "DELETE FROM framework_responsibility_assignment WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM technical_role_assignment WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM entity_membership WHERE person_id IN "
                "(SELECT id FROM person WHERE email_normalized LIKE :motif)",
                "DELETE FROM person WHERE email_normalized LIKE :motif",
                "DELETE FROM entity WHERE code LIKE :code",
                "DELETE FROM auth_event WHERE person_id IS NULL AND created_at >= :debut",
            ):
                menage.execute(
                    text(requete),
                    {"motif": f"{marqueur}%", "code": f"T9-{marqueur}%", "debut": debut},
                )


def _client(parametres: Parametres) -> TestClient:
    return TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST)


def _profil(
    parametres: Parametres,
    marqueur: str,
    *,
    categorie: str = "consultant",
    maintenant: bool = False,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, str]:
    """Une entite, une personne, une appartenance ACTIVE, et une session ouverte.

    Args:
        maintenant: ouvrir la session a l'instant REEL plutot qu'a `INSTANT`.
            Necessaire au seul test qui passe par la vraie route HTTP.
    """
    adresse = f"{marqueur}.{categorie}@exalt-t9.test"
    ouverture = dt.datetime.now(tz=dt.UTC) if maintenant else INSTANT
    with moteur(parametres).begin() as cx:
        entite = _entite(cx, f"T9-{marqueur}-{categorie[:3]}")
        personne = _personne(cx, adresse)
        if categorie == "dg":
            #  La categorie `dg` EXIGE une responsabilite DSM active dans la meme
            #  entite : `fn_dg_implique_dsm_local` refuse l'insertion sinon.
            _responsabilite(cx, personne, entite, "DSM")
        appartenance = _appartenance(cx, personne, entite, categorie=categorie)
        jeton, _ = ouvrir_une_session(cx, personne=personne, instant=ouverture, jours_absolus=30)
    return entite, personne, appartenance, jeton, adresse


def _sessions_actives(parametres: Parametres, personne: uuid.UUID) -> int:
    with moteur(parametres).connect() as cx:
        return int(
            cx.execute(
                text(
                    "SELECT count(*) FROM user_session WHERE person_id = :p AND revoked_at IS NULL"
                ),
                {"p": personne},
            ).scalar_one()
        )


# ===========================================================================
#  LE CRITERE : le depart revoque, et la session ne repond plus
# ===========================================================================


@pytest.mark.integration
def test_LE_DEPART_revoque_les_sessions(decor: tuple[Parametres, str]) -> None:
    """§30.22 : « le depart revoque **immediatement** les sessions et roles ».

    Le depart, non l'archivage : le §24.1 n'a pas de transition
    `Active --> Archived`, donc attendre l'archivage laisserait une fenetre.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    assert _sessions_actives(parametres, personne) == 1

    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)

    assert resultat.etat_nouveau == EtatAppartenance.DEPARTED.value
    assert resultat.sessions_revoquees == 1
    assert _sessions_actives(parametres, personne) == 0


@pytest.mark.integration
def test_UNE_SESSION_REVOQUEE_NE_REPOND_PLUS_mesure_en_HTTP(
    decor: tuple[Parametres, str],
) -> None:
    """**MESURE, ET NON DEDUITE DE L'ECRITURE DE `revoked_at`.**

    C'est le critere litteral de la fiche : « une session revoquee ne repond plus,
    **mesure** ». Verifier la colonne prouverait l'ecriture, pas le refus -- et
    c'est la quatrieme proposition du §7.0 : l'echec produirait la meme
    observation que le succes si le filtre du service etait absent.
    """
    parametres, marqueur = decor
    #  **LE TEMPS REEL, ET NON `INSTANT`.** Ce test passe par la VRAIE route, qui
    #  rafraichit `last_activity_at` avec `now()`. Une session creee a un instant
    #  futur violerait `ck_user_session_activite_apres_creation` des le premier
    #  appel -- et le message parlerait d'une contrainte, non de la revocation.
    _, _, appartenance, jeton, _ = _profil(parametres, marqueur, maintenant=True)
    with _client(parametres) as client:
        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        avant = client.get(f"{parametres.API_PREFIX}/auth/session")
        assert avant.status_code == 200, "TEMOIN : la session doit repondre AVANT le depart"

        with moteur(parametres).begin() as cx:
            enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)

        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        apres = client.get(f"{parametres.API_PREFIX}/auth/session")
    assert apres.status_code == 401


@pytest.mark.integration
def test_LES_LIENS_ACTIFS_sont_invalides_et_les_CONSOMMES_conserves(
    decor: tuple[Parametres, str],
) -> None:
    """`US006` : « … et futurs magic links ».

    **UN LIEN DEJA CONSOMME N'EST PAS TOUCHE**, et c'est un choix : `used_at` est
    une trace, et poser `invalidated_at` par-dessus reecrirait l'histoire.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    with moteur(parametres).begin() as cx:
        for consomme in (False, True):
            cx.execute(
                text(
                    "INSERT INTO magic_link_request (person_id, token_hash, requested_at, "
                    " expires_at, used_at) VALUES (:p, :h, :q, :x, :u)"
                ),
                {
                    "p": personne,
                    "h": uuid.uuid4().hex + uuid.uuid4().hex,
                    "q": INSTANT,
                    "x": INSTANT + dt.timedelta(minutes=15),
                    "u": INSTANT if consomme else None,
                },
            )
    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)
    assert resultat.liens_invalides == 1
    with moteur(parametres).connect() as cx:
        consommes = cx.execute(
            text(
                "SELECT count(*) FROM magic_link_request "
                "WHERE person_id = :p AND used_at IS NOT NULL AND invalidated_at IS NULL"
            ),
            {"p": personne},
        ).scalar_one()
    assert consommes == 1, "un lien deja consomme a ete invalide : la trace est reecrite"


@pytest.mark.integration
def test_LE_DEPART_D_UN_DG_REUSSIT_malgre_le_declencheur(decor: tuple[Parametres, str]) -> None:
    """**LE CAS QUI N'AURAIT ECHOUE QU'EN PRODUCTION.**

    `fn_dg_implique_dsm_local` exige une responsabilite DSM active des que la
    categorie vaut `dg`, **sans regarder l'etat**. Clore les roles avant le
    changement d'etat fait echouer le depart, et le message parle de categorie
    `dg` -- pas de revocation. L'ordre est donc impose, et ce test le garde.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur, categorie="dg")
    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)
    assert resultat.etat_nouveau == EtatAppartenance.DEPARTED.value
    assert resultat.relations_closes.get("framework_responsibility_assignment") == 1
    assert _sessions_actives(parametres, personne) == 0


@pytest.mark.integration
def test_L_ARCHIVAGE_est_IDEMPOTENT_apres_un_depart(decor: tuple[Parametres, str]) -> None:
    """`US006` est satisfaite SANS creer la fenetre que le §7.4 interdit.

    L'archivage rejoue la revocation, ne trouve plus rien, et rend zero.
    """
    parametres, marqueur = decor
    _, _, appartenance, _, _ = _profil(parametres, marqueur)
    with moteur(parametres).begin() as cx:
        premier = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)
    with moteur(parametres).begin() as cx:
        second = archiver_une_appartenance(cx, appartenance=appartenance, instant=INSTANT)
    assert premier.sessions_revoquees == 1
    assert second.etat_nouveau == EtatAppartenance.ARCHIVED.value
    assert second.sessions_revoquees == 0
    assert second.liens_invalides == 0


@pytest.mark.integration
def test_UNE_ARRIVEE_ANNULEE_revoque_POUR_DE_BON(decor: tuple[Parametres, str]) -> None:
    """`Future --> Archived` — « arrivee annulee », §24.1. Aucun depart n'a eu lieu."""
    parametres, marqueur = decor
    adresse = f"{marqueur}.future@exalt-t9.test"
    with moteur(parametres).begin() as cx:
        entite = _entite(cx, f"T9-{marqueur}-fut")
        personne = _personne(cx, adresse)
        appartenance = _appartenance(cx, personne, entite, etat=EtatAppartenance.FUTURE.value)
        ouvrir_une_session(cx, personne=personne, instant=INSTANT, jours_absolus=30)
    with moteur(parametres).begin() as cx:
        resultat = archiver_une_appartenance(cx, appartenance=appartenance, instant=INSTANT)
    assert resultat.etat_precedent == EtatAppartenance.FUTURE.value
    assert resultat.sessions_revoquees == 1


@pytest.mark.integration
def test_UNE_TRANSITION_HORS_24_1_est_REFUSEE(decor: tuple[Parametres, str]) -> None:
    """**LE TEMOIN DU §24.1.** `Active --> Archived` n'existe pas dans le diagramme.

    Sans ce refus, un appelant pourrait archiver directement et sauter le depart --
    ce que le modele n'autorise pas, et qui rendrait l'etat `departed` optionnel.
    """
    parametres, marqueur = decor
    _, _, appartenance, _, _ = _profil(parametres, marqueur)
    attendu = re.escape("§24.1")
    with moteur(parametres).begin() as cx, pytest.raises(TransitionRefusee, match=attendu):
        archiver_une_appartenance(cx, appartenance=appartenance, instant=INSTANT)


@pytest.mark.integration
def test_LA_REVOCATION_EST_ATOMIQUE_avec_le_changement_d_etat(
    decor: tuple[Parametres, str],
) -> None:
    """**LE CRITERE LITTERAL : « la revocation est ATOMIQUE avec l'archivage ».**

    Un `rollback` ne doit laisser ni le changement d'etat ni la revocation. Un
    test qui verifierait seulement « la session est revoquee » ne dirait rien de
    l'atomicite : les deux ecritures pourraient etre dans deux transactions.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    connexion = moteur(parametres).connect()
    try:
        transaction = connexion.begin()
        resultat = enregistrer_un_depart(connexion, appartenance=appartenance, instant=INSTANT)
        assert resultat.sessions_revoquees == 1
        transaction.rollback()
    finally:
        connexion.close()

    with moteur(parametres).connect() as cx:
        etat = cx.execute(
            text("SELECT membership_state FROM entity_membership WHERE id = :a"),
            {"a": appartenance},
        ).scalar_one()
    assert etat == EtatAppartenance.ACTIVE.value, "le changement d'etat a survecu au rollback"
    assert _sessions_actives(parametres, personne) == 1, "la revocation a survecu au rollback"


@pytest.mark.integration
def test_UN_EVENEMENT_PAR_SESSION_avec_le_motif_du_depart(
    decor: tuple[Parametres, str],
) -> None:
    """Le §10.6 declare « session revoquee » au singulier : l'audit doit compter.

    Et `revoke_reason` distingue une deconnexion volontaire d'une revocation
    administrative — ce que `T6` avait laisse a `T9`.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    with moteur(parametres).begin() as cx:
        ouvrir_une_session(cx, personne=personne, instant=INSTANT, jours_absolus=30)
    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)
    assert resultat.sessions_revoquees == 2
    with moteur(parametres).connect() as cx:
        evenements = cx.execute(
            text(
                "SELECT count(*) FROM auth_event WHERE person_id = :p "
                "  AND event_type = 'SESSION_REVOKED' AND detail = :motif"
            ),
            {"p": personne, "motif": REVOCATION_DEPART},
        ).scalar_one()
        motifs = (
            cx.execute(
                text("SELECT DISTINCT revoke_reason FROM user_session WHERE person_id = :p"),
                {"p": personne},
            )
            .scalars()
            .all()
        )
    assert evenements == 2, "un evenement par session, non un seul pour le lot"
    assert motifs == [REVOCATION_DEPART]


# ===========================================================================
#  Ce qui est RAPPORTE plutot que decide — §7.20
# ===========================================================================


@pytest.mark.integration
def test_AUCUNE_TABLE_INVITATION_N_EXISTE_A_INVALIDER(
    parametres_de_la_stack: Parametres,
) -> None:
    """**FERME `ECART-035`, LOT 9 `T13` — PAR CONSTAT, PAS PAR CODE.**

    Le backlog `US006` nomme trois objets a invalider au depart : sessions,
    invitations, futurs magic links. `invitation` n'a jamais existe comme objet
    de donnees -- 0 occurrence dans le modele et la matrice -- et l'ecart
    recommandait de reprendre la question au LOT 9, « ou le back-office creera
    les invitations ». Les seize sous-etapes validees du LOT 9 ne creent AUCUN
    objet de ce nom : `T12` nomme un administrateur par une simple affectation
    de role technique, et `T14` a `T16` sont des ecrans et des controles, pas un
    nouveau modele de donnees.

    **Ce test rend la fermeture FALSIFIABLE plutot qu'affirmee en prose** (§7.32) :
    il interroge le catalogue reel, jamais une liste ecrite a la main qui
    vieillirait au premier ajout (§7.27). Si un lot futur pose une table dont le
    nom contient « invitation », CE TEST ECHOUE -- et celui qui l'a posee saura
    qu'il doit relire `app.people.services._appliquer` pour y ajouter la ligne de
    revocation que cet ecart promettait.
    """
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as cx:
        tables = [
            str(ligne[0])
            for ligne in cx.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name ILIKE '%invitation%'"
                )
            )
        ]
    assert tables == []


@pytest.mark.integration
def test_UNE_SECONDE_APPARTENANCE_OCCUPANTE_est_REFUSEE_par_la_base(
    decor: tuple[Parametres, str],
) -> None:
    """**CE TEST A REMPLACE UNE GARDE QUE J'AVAIS ECRITE POUR RIEN.**

    J'avais code une defense : ne pas revoquer les sessions si la personne garde
    une appartenance active ou future ailleurs. **Cet etat est impossible.**
    `uq_entity_membership_person_id_occupante` est un index unique PARTIEL sur
    `person_id` seul, restreint aux etats `future` et `active` -- §25.1.

    Ecrire une defense contre un etat que la base interdit est du code mort, et
    un champ de rapport qui ne peut jamais etre vrai apprend a ne pas le lire.
    **Ce test le remplace, et il est plus fort** : si un lot ulterieur relachait
    cet index pour autoriser l'appartenance multi-entites, il echouerait -- et
    celui qui le relache saurait qu'il doit relire la revocation.

    Le refus est exige sur son NOM de contrainte, non sur « une erreur a eu
    lieu » : n'importe quel autre defaut du decor produirait aussi une erreur.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    depart_connu = INSTANT.date() + dt.timedelta(days=30)
    with moteur(parametres).begin() as cx:
        #  Meme sans chevauchement de PERIODE -- la premiere appartenance porte
        #  desormais une date de depart -- l'index partiel refuse une seconde
        #  appartenance occupante.
        cx.execute(
            text("UPDATE entity_membership SET departure_date = :d WHERE id = :a"),
            {"d": depart_connu, "a": appartenance},
        )
        seconde_entite = _entite(cx, f"T9-{marqueur}-bis")
    attendu = "uq_entity_membership_person_id_occupante"
    with pytest.raises(IntegrityError, match=attendu), moteur(parametres).begin() as cx:
        _appartenance(
            cx,
            personne,
            seconde_entite,
            etat=EtatAppartenance.FUTURE.value,
            arrivee=depart_connu + dt.timedelta(days=1),
        )


@pytest.mark.integration
def test_UN_ROLE_GLOBAL_est_CONSERVE_et_rapporte(decor: tuple[Parametres, str]) -> None:
    """Le §8.6 rend `entity_id` nullable pour `SUPER_ADMIN`.

    Quitter une entite ne retire pas un role global, et le retirer depasserait le
    §30.22. Il est donc **compte et rendu**.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    with moteur(parametres).begin() as cx:
        cx.execute(
            text(
                "INSERT INTO technical_role_assignment "
                "(person_id, entity_id, role_type, starts_at, ends_at) "
                "VALUES (:p, NULL, 'SUPER_ADMIN', :debut, NULL)"
            ),
            {"p": personne, "debut": INSTANT - dt.timedelta(days=5)},
        )
    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)
    assert resultat.roles_globaux_conserves == 1
    with moteur(parametres).connect() as cx:
        encore = cx.execute(
            text(
                "SELECT count(*) FROM technical_role_assignment "
                "WHERE person_id = :p AND entity_id IS NULL AND ends_at IS NULL"
            ),
            {"p": personne},
        ).scalar_one()
    assert encore == 1


@pytest.mark.integration
def test_UNE_RELATION_FUTURE_est_CONSERVEE_et_rapportee(decor: tuple[Parametres, str]) -> None:
    """**`period` EST `GENERATED ALWAYS`**, donc `ends_at < starts_at` serait refuse.

    Ce qu'il faut faire d'une relation qui n'a pas commence -- annuler, decaler --
    n'est ecrit nulle part. Elle est comptee et laissee.
    """
    parametres, marqueur = decor
    _, personne, appartenance, _, _ = _profil(parametres, marqueur)
    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text("SELECT entity_id FROM entity_membership WHERE id = :a"),
            {"a": appartenance},
        ).scalar_one()
        _responsabilite_future = _responsabilite(
            #  `ESM` et non `BOOSTER` : la contrainte
            #  `ck_..._portee_selon_le_type` exige un `circle_id` pour un Booster.
            cx,
            personne,
            entite,
            "ESM",
            debut=INSTANT + dt.timedelta(days=7),
        )
    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance, instant=INSTANT)
    assert resultat.relations_futures_conservees == {"framework_responsibility_assignment": 1}
    assert resultat.a_des_reserves is True
    with moteur(parametres).connect() as cx:
        toujours_ouverte = cx.execute(
            text(
                "SELECT count(*) FROM framework_responsibility_assignment "
                "WHERE id = :id AND ends_at IS NULL"
            ),
            {"id": _responsabilite_future},
        ).scalar_one()
    assert toujours_ouverte == 1


@pytest.mark.integration
def test_LES_CONSULTANTS_DU_DSM_PARTANT_sont_RAPPORTES(decor: tuple[Parametres, str]) -> None:
    """**LES PERMISSIONS SONT REVOQUEES, LE LIEN HISTORIQUE EST CONSERVE.**

    `RIGHTS-019` exige que la cloture d'une responsabilite revoque les
    permissions : la responsabilite DSM du partant EST close. Mais designer le
    remplacant est une decision humaine -- le §30.4 est classe `PARTIEL`
    precisement parce que cette existence « ne peut pas etre acquise en base ».

    Les consultants concernes sont donc **nommes**, pour qu'un humain agisse.
    """
    parametres, marqueur = decor
    entite, dsm, appartenance_dsm, _, _ = _profil(parametres, marqueur, categorie="dg")
    with moteur(parametres).begin() as cx:
        consultant = _personne(cx, f"{marqueur}.suivi@exalt-t9.test")
        appartenance_c = _appartenance(cx, consultant, entite)
        cx.execute(
            text(
                "INSERT INTO dsm_assignment "
                "(consultant_membership_id, dsm_person_id, entity_id, starts_at, ends_at) "
                "VALUES (:c, :d, :e, :debut, NULL)"
            ),
            {
                "c": appartenance_c,
                "d": dsm,
                "e": entite,
                "debut": INSTANT - dt.timedelta(days=3),
            },
        )
    with moteur(parametres).begin() as cx:
        resultat = enregistrer_un_depart(cx, appartenance=appartenance_dsm, instant=INSTANT)
    assert resultat.consultants_sans_dsm == (consultant,)
    assert resultat.a_des_reserves is True
    #  Le lien est CONSERVE : la responsabilite est close, pas l'historique.
    with moteur(parametres).connect() as cx:
        lien = cx.execute(
            text(
                "SELECT count(*) FROM dsm_assignment WHERE dsm_person_id = :d AND ends_at IS NULL"
            ),
            {"d": dsm},
        ).scalar_one()
    assert lien == 1


@pytest.mark.integration
def test_revoquer_toutes_les_sessions_EXIGE_un_motif(decor: tuple[Parametres, str]) -> None:
    """Une revocation en masse sans motif serait illisible dans l'audit.

    Le parametre n'a donc pas de defaut : l'oublier est une erreur de typage, pas
    un evenement muet en base.
    """
    parametres, marqueur = decor
    _, personne, _, _, _ = _profil(parametres, marqueur)
    with moteur(parametres).begin() as cx:
        assert (
            revoquer_toutes_les_sessions(
                cx, personne=personne, instant=INSTANT, raison=REVOCATION_DEPART
            )
            == 1
        )
        #  Idempotente : plus rien a revoquer.
        assert (
            revoquer_toutes_les_sessions(
                cx, personne=personne, instant=INSTANT, raison=REVOCATION_DEPART
            )
            == 0
        )
