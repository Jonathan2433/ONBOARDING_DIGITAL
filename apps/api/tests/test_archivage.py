"""Archivage et restauration — LOT 5, `T8`, story `MVP-L05-US007`.

CE QUE CE FICHIER EPROUVE, ET CE QU'IL N'EPROUVE PAS

  La revocation elle-meme est deja prouvee par `test_revocation.py` -- LOT 3,
  `T9`, six controles de stack et le §30.22 classe `ACQUIS`. La redemontrer ici
  donnerait deux regles pour une seule (`DEC-466`).

  Ce fichier eprouve ce que `T8` AJOUTE, et cela seul :

      la GRILLE DE ROLES du §6.1, plus etroite que celle de l'ecriture ;
      la GRILLE D'ETAT derivee du §24.1, une par action ;
      le CHEMIN `Active --> Departed --> Archived`, et l'idempotence du second pas ;
      la QUATRIEME transition, `Archived --> Active` ;
      la concurrence optimiste du §18.4 sur les deux actes ;
      les deux refus que la BASE produit a la restauration ;
      la fiche d'un profil archive, et ce qu'elle ne filtre pas.

CHAQUE REFUS EST APPARIE, ET LE TEMOIN NE DIFFERE QUE PAR LA VALEUR EN CAUSE

  §7.39 et le defaut `T2-3` : une famille de refus indistinguables est satisfaite
  par une grille qui refuse TOUT. Les refus de ce fichier sont donc apparies :

    - `DSM` refuse a l'archivage / **le meme `DSM` autorise a l'ECRITURE sur la
      meme cible** -- le temoin le plus utile du fichier, parce qu'il prouve que
      le decor est bon et que seule la grille change ;
    - `active` refuse a la restauration / le meme decor en `archived` autorise ;
    - `relations_a_redonner` nomme quatre tables / le meme test avec un metier
      COURANT n'en nomme que trois.

LE TEMPS EST INJECTE, JAMAIS LU A L'HORLOGE

  Sauf pour les sessions, dont `ouvrir_une_session` verifie la date d'expiration
  contre l'horloge reelle -- meme reserve qu'en `T9` du LOT 3, et nommee la aussi.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.people.archivage import (
    CODE_ACTION_HORS_PERIMETRE,
    archiver_un_profil,
    restaurer_un_profil,
)
from app.people.ecriture import (
    CODE_ETAT_INCOMPATIBLE,
    CODE_PERIODE_INCOMPATIBLE,
    CODE_VALEUR_REFUSEE,
    CODE_VERSION_OBSOLETE,
)
from app.people.modeles import (
    ETATS_OCCUPANTS,
    TRANSITIONS_DU_CYCLE_DE_VIE,
    EtatAppartenance,
    SituationProfessionnelle,
    VisibiliteProfil,
)
from app.people.profil import lire_la_fiche, lire_la_fiche_archivee
from app.people.services import (
    RELATIONS_DE_L_APPARTENANCE,
    RELATIONS_DE_LA_PERSONNE,
)
from app.permissions.perimetre import (
    ETATS_ARCHIVABLES,
    ETATS_RESTAURABLES,
    ROLES_DU_CYCLE_DE_VIE,
    ActionDeCycleDeVie,
    PerimetreDuCycleDeVie,
    resoudre_le_cycle_de_vie,
    resoudre_le_perimetre,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

#  Le manifeste du contrat, source unique de `DEC-492` — lue par TypeScript ET
#  par Python. Le chemin est relatif a la racine du depot.
MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"

ANCRAGE = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
JOUR = dt.timedelta(days=1)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


# ---------------------------------------------------------------------------
#  Le decor. Local a ce fichier, comme celui de `T7` : aucun test du depot
#  n'importe le decor d'un autre, et chaque decor est taille a sa question.
# ---------------------------------------------------------------------------


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        #  **UN PARAMETRE PAR COLONNE.** `entity.code` est `character varying(64)`
        #  quand `display_name` et `city` sont `text` : un parametre lie PARTAGE
        #  rend « inconsistent types deduced for parameter $1 », et le message ne
        #  nomme ni la table ni la colonne. §7.25, rejoue en `T7`.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    """L'adresse est MISE EN MINUSCULES ici, et la base l'a exige.

    `ck_person_email_normalise_en_minuscules` porte l'invariant du §6.1 --
    « unicite INSENSIBLE A LA CASSE » rendue structurelle par une valeur
    STOCKEE deja normalisee. Trois de mes tests parametres formaient leur
    adresse depuis `role.value`, qui vaut `ESM`, `ADM-E` et `SUPER` : les
    trois sont tombes d'un coup, et le message nommait la contrainte.
    """
    adresse = adresse.lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Sujet', 'L5T8', 'active') RETURNING id"
        ),
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    *,
    etat: str = "active",
    visibilite: str = "published",
    arrivee: dt.date | None = None,
    depart: dt.date | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, :etat, 'consultant', :visibilite) RETURNING id"
        ),
        {
            "p": personne,
            "e": entite,
            "arrivee": arrivee or (ANCRAGE - 30 * JOUR).date(),
            "depart": depart,
            "etat": etat,
            "visibilite": visibilite,
        },
    ).scalar_one()


def _role_technique(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID | None, role: str
) -> None:
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, :r, :d)"
        ),
        {"p": personne, "e": entite, "r": role, "d": ANCRAGE - JOUR},
    )


def _responsabilite(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    type_resp: str,
    *,
    cercle: uuid.UUID | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :p, :d)"
        ),
        {"p": personne, "e": entite, "t": type_resp, "c": cercle, "d": ANCRAGE - JOUR},
    )


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _metier(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label) "
            "VALUES (:e, :code, :libelle) RETURNING id"
        ),
        {"e": entite, "code": code, "libelle": code},
    ).scalar_one()


def _affecter_le_metier(
    cx: Connection, cible: uuid.UUID, metier: uuid.UUID, entite: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_membership_id, entity_id, "
            "job_catalog_id, starts_at) VALUES (:c, :e, :m, :d)"
        ),
        {"c": cible, "e": entite, "m": metier, "d": ANCRAGE - 10 * JOUR},
    )


def _statut(cx: Connection, cible: uuid.UUID, entite: uuid.UUID) -> None:
    """Un statut `intercontract`, donc SANS client — la biconditionnelle du §30.5.

    `intercontract` plutot que `mission` : une mission exige un client **active
    dans cette entite**, donc un `client` et une ligne `entity_client`. Le statut
    n'est ici qu'une relation a clore, et le plus simple suffit.
    """
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_membership_id, entity_id, "
            "status, client_id, starts_at) VALUES (:c, :e, :s, NULL, :debut)"
        ),
        {
            "c": cible,
            "e": entite,
            "s": SituationProfessionnelle.INTERCONTRACT.value,
            "debut": ANCRAGE - 10 * JOUR,
        },
    )


def _rattacher_au_dsm(cx: Connection, cible: uuid.UUID, dsm: uuid.UUID, entite: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (consultant_membership_id, entity_id, dsm_person_id, "
            "starts_at) VALUES (:c, :e, :d, :debut)"
        ),
        {"c": cible, "e": entite, "d": dsm, "debut": ANCRAGE - 10 * JOUR},
    )


def _membre_de_cercle(
    cx: Connection, cible: uuid.UUID, cercle: uuid.UUID, entite: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_membership_id, entity_id, circle_id, "
            "membership_type, starts_at) VALUES (:c, :e, :cercle, 'principal', :debut)"
        ),
        {"c": cible, "e": entite, "cercle": cercle, "debut": ANCRAGE - 10 * JOUR},
    )


def _cycle(
    cx: Connection,
    entite: uuid.UUID,
    cible: uuid.UUID,
    roles: set[RoleDeLaMatrice],
) -> PerimetreDuCycleDeVie:
    return resoudre_le_cycle_de_vie(cx, entite=entite, cible=cible, roles=frozenset(roles))


def _tout_permis(cx: Connection, entite: uuid.UUID, cible: uuid.UUID) -> PerimetreDuCycleDeVie:
    return _cycle(cx, entite, cible, {RoleDeLaMatrice.ESM})


def _etat(cx: Connection, cible: uuid.UUID) -> tuple[str, dt.date | None, int]:
    ligne = cx.execute(
        text(
            "SELECT membership_state, departure_date, version FROM entity_membership WHERE id = :c"
        ),
        {"c": cible},
    ).one()
    return str(ligne[0]), ligne[1], int(ligne[2])


# ---------------------------------------------------------------------------
#  1. La grille de roles — matrice §6.1 et §6.2
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_LES_TROIS_ROLES_du_6_1_sont_exactement_ESM_ADM_E_et_SUPER() -> None:
    """§6.2 : « l'archivage […] est reserve a l'ESM, a l'administrateur d'entite et
    au super-administrateur ».

    **UNE EGALITE, PAS UNE INCLUSION.** Un test qui verifierait « l'ESM est
    dedans » passerait sur une grille qui contient les huit roles. Les cinq
    autres sont donc nommes comme ABSENTS -- et `DSM` et `BOOST` en particulier,
    qui portent tous deux un droit de modification.
    """
    #  Le nom local n'est pas cosmetique : `SIM300` lit une constante en capitales
    #  comme le membre CONSTANT d'une comparaison, et reclamerait de l'ecrire a
    #  droite -- ce qui inverserait la lecture. Nommer l'attendu resout les deux.
    attendus = {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
    assert attendus == ROLES_DU_CYCLE_DE_VIE
    absents = set(RoleDeLaMatrice) - ROLES_DU_CYCLE_DE_VIE
    assert RoleDeLaMatrice.DSM in absents
    assert RoleDeLaMatrice.BOOSTER in absents


def test_le_MANIFESTE_declare_la_MEME_grille_que_le_service() -> None:
    """`T11` — l'ecran doit savoir quand proposer les actions, sans les decider.

    **LE FRONTEND N'EST PAS L'AUTORITE**, et la matrice l'ecrit : « le frontend
    peut masquer ou afficher les ACTIONS pour ameliorer l'experience, mais l'API
    reste l'autorite finale ». Il lui faut neanmoins la grille, pour ne pas
    proposer un bouton dont il sait qu'il sera refuse.

    **`rolesCycleDeVie` EST DECLARE SEPAREMENT DE `rolesAdministration`, ET LES
    DEUX PORTENT AUJOURD'HUI LES MEMES TROIS ROLES.** C'est une **coincidence**,
    pas une derivation : le premier vient des trois lignes d'archivage du §6.1,
    le second du §20. Les fusionner parce qu'ils coincident ferait suivre l'un
    quand l'autre change, **en silence** -- et le §6.1 porte deux grilles, ce que
    `T8` a mesure en refusant a `DSM` et `BOOST` ce que l'ecriture leur donne.

    **CE TEST EST CE QUI EMPECHE LES DEUX DERIVATIONS DE DIVERGER** : le manifeste
    est la source unique de `DEC-492`, lue par TypeScript et par Python, et
    l'egalite est exigee **dans les deux sens**.
    """
    manifeste = json.loads(
        (pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT).read_text(
            encoding="utf-8"
        )
    )
    codes = manifeste["rolesCycleDeVie"]
    assert codes, "le manifeste ne declare aucun role de cycle de vie"
    #  La conversion ajoute une exigence utile : un code qui ne serait pas un role
    #  connu leve ICI, au lieu de rendre l'ecran inerte en silence.
    declares = {RoleDeLaMatrice(code) for code in codes}
    assert declares == ROLES_DU_CYCLE_DE_VIE

    #  **ET LES DEUX GRILLES RESTENT DEUX DECLARATIONS.** Ce test ne verifie pas
    #  qu'elles different -- elles ne different pas aujourd'hui -- mais que le
    #  manifeste les porte separement. Fusionner les cles ferait echouer ici.
    assert "rolesAdministration" in manifeste
    assert "rolesCycleDeVie" in manifeste


@pytest.mark.integration
@pytest.mark.parametrize(
    "role",
    [
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    ],
)
def test_les_trois_roles_autorises_ouvrent_l_archivage(
    cx: Connection, role: RoleDeLaMatrice
) -> None:
    """Le temoin POSITIF de la famille de refus qui suit."""
    entite = _entite(cx, f"T8-OK-{role.value}")
    cible = _appartenance(cx, _personne(cx, f"t8-ok-{role.value}@exalt-company.com"), entite)
    assert ActionDeCycleDeVie.ARCHIVER in _cycle(cx, entite, cible, {role}).actions


@pytest.mark.integration
def test_le_DSM_de_la_cible_est_REFUSE_a_l_archivage_ALORS_QU_IL_PEUT_LA_MODIFIER(
    cx: Connection,
) -> None:
    """**LE TEMOIN LE PLUS UTILE DU FICHIER, ET IL NE DIFFERE QUE PAR LA GRILLE.**

    Le §6.1 donne au `DSM` « Modifier les donnees organisationnelles | Consultants »
    et un TIRET sur « Archiver un profil ». Le meme acteur, la meme cible, le meme
    instant : l'ecriture est ouverte, l'archivage est refuse.

    Sans ce temoin, un refus d'archivage pourrait venir d'un decor incomplet --
    c'est exactement le defaut `T7-5`, ou cinq controles rendaient `403` parce que
    le DSM n'avait pas d'appartenance, et ou **la garde avait raison**.
    """
    entite = _entite(cx, "T8-DSM")
    dsm = _personne(cx, "t8-dsm-acteur@exalt-company.com")
    _appartenance(cx, dsm, entite)
    #  **LE DECLENCHEUR `dsm_responsabilite_active` EXIGE UNE RESPONSABILITE DSM
    #  DANS CETTE ENTITE**, et son message le disait en nommant la personne et
    #  l'entite : « le DSM designe n'a pas de responsabilite DSM active dans cette
    #  entite ». Le decor de `T7` la posait ; le mien l'avait oubliee.
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value)
    cible = _appartenance(cx, _personne(cx, "t8-dsm-cible@exalt-company.com"), entite)
    _rattacher_au_dsm(cx, cible, dsm, entite)

    roles = {RoleDeLaMatrice.DSM}
    assert _cycle(cx, entite, cible, roles).actions == frozenset()
    #  Le TEMOIN : la seule chose qui change est la grille consultee.
    ecriture = resoudre_le_perimetre(
        cx, entite=entite, acteur=dsm, cible=cible, roles=frozenset(roles), instant=ANCRAGE
    )
    assert ecriture.champs != frozenset()


@pytest.mark.integration
def test_le_BOOSTER_du_cercle_est_REFUSE_a_l_archivage_ALORS_QU_IL_PEUT_MODIFIER(
    cx: Connection,
) -> None:
    """Meme forme que le DSM : le §6.1 met `BOOST` a tiret sur les trois lignes."""
    entite = _entite(cx, "T8-BOOST")
    cercle = _cercle(cx, entite, "T8B")
    booster = _personne(cx, "t8-boost-acteur@exalt-company.com")
    _appartenance(cx, booster, entite)
    _responsabilite(cx, booster, entite, TypeResponsabilite.BOOSTER.value, cercle=cercle)
    cible = _appartenance(cx, _personne(cx, "t8-boost-cible@exalt-company.com"), entite)
    _membre_de_cercle(cx, cible, cercle, entite)

    roles = {RoleDeLaMatrice.BOOSTER}
    assert _cycle(cx, entite, cible, roles).actions == frozenset()
    ecriture = resoudre_le_perimetre(
        cx, entite=entite, acteur=booster, cible=cible, roles=frozenset(roles), instant=ANCRAGE
    )
    assert ecriture.champs != frozenset()


@pytest.mark.integration
def test_une_cible_d_une_AUTRE_entite_est_refusee(cx: Connection) -> None:
    """§25.3 : le couple `(id, entity_id)` porte l'isolation, pas un filtre d'entite."""
    ici, ailleurs = _entite(cx, "T8-ICI"), _entite(cx, "T8-AILLEURS")
    cible = _appartenance(cx, _personne(cx, "t8-iso@exalt-company.com"), ailleurs)
    assert _cycle(cx, ici, cible, {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}).actions == frozenset()


# ---------------------------------------------------------------------------
#  2. La grille d'etat — derivee du modele §24.1
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_les_deux_grilles_d_etat_PARTITIONNENT_les_transitions_du_24_1() -> None:
    """**LA DERIVATION EST EPROUVEE, PAS SUPPOSEE.**

    `ETATS_ARCHIVABLES` et `ETATS_RESTAURABLES` sont deux comprehensions sur la
    meme source. Ce test exige qu'elles soient DISJOINTES et que leur union
    couvre tous les etats de depart du §24.1 : une erreur de sens dans l'un des
    deux `if` les rendrait egales, et chacune prise seule paraitrait juste.
    """
    departs = {depuis for depuis, _ in TRANSITIONS_DU_CYCLE_DE_VIE}
    union = ETATS_ARCHIVABLES | ETATS_RESTAURABLES
    assert union == departs
    assert not ETATS_ARCHIVABLES & ETATS_RESTAURABLES
    #  Et les valeurs, nommees : le §24.1 est la source, et la lire vaut mieux
    #  que de faire confiance a deux comprehensions symetriques.
    archivables, restaurables = {"active", "future", "departed"}, {"archived"}
    assert archivables == ETATS_ARCHIVABLES
    assert restaurables == ETATS_RESTAURABLES


@pytest.mark.integration
@pytest.mark.parametrize(
    ("etat", "attendues"),
    [
        ("active", {ActionDeCycleDeVie.ARCHIVER}),
        ("future", {ActionDeCycleDeVie.ARCHIVER}),
        ("departed", {ActionDeCycleDeVie.ARCHIVER}),
        (
            "archived",
            {ActionDeCycleDeVie.RESTAURER, ActionDeCycleDeVie.CONSULTER_UN_ARCHIVE},
        ),
    ],
)
def test_chaque_etat_ouvre_EXACTEMENT_ses_actions(
    cx: Connection, etat: str, attendues: set[ActionDeCycleDeVie]
) -> None:
    """§23.2 : « une interdiction liee a l'ETAT prevaut sur le cumul des roles ».

    **UNE EGALITE, LA AUSSI.** Le role employe est `SUPER`, le plus large : si la
    grille d'etat ne s'appliquait pas a lui, les quatre lignes rendraient les
    trois actions et l'egalite echouerait. C'est le §23.2 rendu observable.
    """
    entite = _entite(cx, f"T8-ETAT-{etat}")
    cible = _appartenance(
        cx,
        _personne(cx, f"t8-etat-{etat}@exalt-company.com"),
        entite,
        etat=etat,
        #  **`ck_entity_membership_depart_date_si_departed` NE VAUT QUE POUR
        #  `departed`**, et c'est derive du §24.1 : « depart ENREGISTRE ». Un
        #  `archived` venu de `future` -- « arrivee annulee » -- n'en a aucune,
        #  et un `active` non plus.
        depart=(ANCRAGE - 2 * JOUR).date() if etat == "departed" else None,
    )
    actions = _cycle(cx, entite, cible, {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}).actions
    assert actions == frozenset(attendues)


# ---------------------------------------------------------------------------
#  3. L'archivage — le chemin du §24.1, et la revocation
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_LE_CRITERE_l_archivage_d_un_ACTIF_revoque_ET_cloture(cx: Connection) -> None:
    """« L'archivage revoque et cloture » — le critere de `T8`, en un test.

    **LE CHEMIN EST OBSERVABLE DANS LA REPONSE** : `etat_precedent` vaut `active`,
    et `revocations` porte DEUX entrees -- le depart puis l'archivage -- alors que
    le §6.1 n'a qu'une action.

    **ET LA SECONDE NE TROUVE RIEN, CE QUI EST LA PREUVE QUE LA PREMIERE A TOUT
    PRIS.** Un archivage qui aurait revoque seulement au second pas laisserait une
    fenetre pendant laquelle un parti garde sa session -- ce que le §7.4 et le
    §30.22 interdisent tous deux par le mot « immediatement ».
    """
    entite = _entite(cx, "T8-CRITERE")
    personne = _personne(cx, "t8-critere@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _affecter_le_metier(cx, cible, _metier(cx, entite, "T8M"), entite)
    _membre_de_cercle(cx, cible, _cercle(cx, entite, "T8C"), entite)
    #  L'ouverture de session lit l'horloge reelle pour son expiration : meme
    #  reserve qu'en `T9` du LOT 3, et le reste du test reste sur `ANCRAGE`.
    ouvrir_une_session(cx, personne=personne, instant=dt.datetime.now(tz=dt.UTC), jours_absolus=30)

    archivage = archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=personne,
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
    )

    assert archivage.etat_precedent == EtatAppartenance.ACTIVE.value
    assert len(archivage.revocations) == 2
    assert [r.etat_nouveau for r in archivage.revocations] == ["departed", "archived"]
    #  Revoque : une session, prise au PREMIER pas.
    assert archivage.sessions_revoquees == 1
    assert archivage.revocations[0].sessions_revoquees == 1
    assert archivage.revocations[1].sessions_revoquees == 0
    #  Cloture : les deux relations posees, nommees table par table.
    assert archivage.relations_closes == {
        "membership_job_assignment": 1,
        "circle_membership": 1,
    }
    etat, depart, version = _etat(cx, cible)
    assert etat == EtatAppartenance.ARCHIVED.value
    assert depart == ANCRAGE.date()
    assert version == 2
    assert archivage.version == 2


@pytest.mark.integration
def test_l_archivage_d_une_arrivee_FUTURE_n_enregistre_AUCUN_depart(cx: Connection) -> None:
    """§24.1 : `Future --> Archived` est libellee « arrivee ANNULEE », pas un depart.

    **LE TEMOIN QUI DISCRIMINE EST `departure_date`.** Forcer un depart depuis
    `future` daterait une sortie qui n'a jamais eu lieu, et la contrainte
    `depart_date_si_departed` ne l'aurait pas dit -- elle ne vaut que pour
    `departed`. Seule l'absence de date le prouve.
    """
    entite = _entite(cx, "T8-FUTUR")
    cible = _appartenance(cx, _personne(cx, "t8-futur@exalt-company.com"), entite, etat="future")
    archivage = archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=_personne(cx, "t8-futur-a@exalt-company.com"),
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
    )
    assert archivage.etat_precedent == EtatAppartenance.FUTURE.value
    assert len(archivage.revocations) == 1
    etat, depart, _ = _etat(cx, cible)
    assert etat == EtatAppartenance.ARCHIVED.value
    assert depart is None


@pytest.mark.integration
def test_la_date_de_depart_FOURNIE_est_celle_qui_est_ecrite(cx: Connection) -> None:
    """Le §2.1 range « date de depart » dans `entity_membership`. Temoin du refus suivant."""
    entite = _entite(cx, "T8-DATE-OK")
    cible = _appartenance(cx, _personne(cx, "t8-date-ok@exalt-company.com"), entite)
    voulue = (ANCRAGE - 7 * JOUR).date()
    archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=_personne(cx, "t8-date-ok-a@exalt-company.com"),
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
        date_de_depart=voulue,
    )
    _, depart, _ = _etat(cx, cible)
    assert depart == voulue


@pytest.mark.integration
def test_une_date_de_depart_AVANT_l_arrivee_est_refusee_par_la_base(cx: Connection) -> None:
    """`ck_entity_membership_depart_apres_arrivee` — traduit en `422`, §18.3.

    La base refuse, elle n'arbitre pas : ecrire la meme verification en Python
    donnerait une seconde regle, qui divergerait le jour ou le §25.2 changerait.
    """
    entite = _entite(cx, "T8-DATE-KO")
    cible = _appartenance(cx, _personne(cx, "t8-date-ko@exalt-company.com"), entite)
    with pytest.raises(ErreurApplicative) as capture:
        archiver_un_profil(
            cx,
            entite=entite,
            cible=cible,
            acteur=_personne(cx, "t8-date-ko-a@exalt-company.com"),
            version_attendue=1,
            perimetre=_tout_permis(cx, entite, cible),
            instant=ANCRAGE,
            date_de_depart=(ANCRAGE - 90 * JOUR).date(),
        )
    assert capture.value.code == CODE_VALEUR_REFUSEE
    assert capture.value.statut == 422


@pytest.mark.integration
def test_une_version_obsolete_refuse_l_archivage(cx: Connection) -> None:
    """§18.4 : « une version obsolete produit une reponse 409 sans ecrasement silencieux »."""
    entite = _entite(cx, "T8-VERSION")
    cible = _appartenance(cx, _personne(cx, "t8-version@exalt-company.com"), entite)
    with pytest.raises(ErreurApplicative) as capture:
        archiver_un_profil(
            cx,
            entite=entite,
            cible=cible,
            acteur=_personne(cx, "t8-version-a@exalt-company.com"),
            version_attendue=99,
            perimetre=_tout_permis(cx, entite, cible),
            instant=ANCRAGE,
        )
    assert capture.value.code == CODE_VERSION_OBSOLETE
    assert capture.value.statut == 409
    assert capture.value.details == {"version_actuelle": 1}
    #  Le TEMOIN : la version JUSTE passe, sur le meme decor.
    assert _etat(cx, cible)[0] == EtatAppartenance.ACTIVE.value


@pytest.mark.integration
def test_un_perimetre_vide_refuse_AVANT_toute_lecture_d_etat(cx: Connection) -> None:
    """§2.5, « refus par defaut » : le perimetre d'abord, comme en `T7`.

    L'action refusee est NOMMEE dans les details -- l'appelant vient de la
    demander, la taire l'obligerait a deviner.
    """
    entite = _entite(cx, "T8-VIDE")
    cible = _appartenance(cx, _personne(cx, "t8-vide@exalt-company.com"), entite)
    with pytest.raises(ErreurApplicative) as capture:
        archiver_un_profil(
            cx,
            entite=entite,
            cible=cible,
            acteur=_personne(cx, "t8-vide-a@exalt-company.com"),
            version_attendue=1,
            perimetre=PerimetreDuCycleDeVie(actions=frozenset()),
            instant=ANCRAGE,
        )
    assert capture.value.code == CODE_ACTION_HORS_PERIMETRE
    assert capture.value.statut == 403
    assert capture.value.details == {"action": "archiver"}


# ---------------------------------------------------------------------------
#  4. La restauration — `Archived --> Active`, §24.1
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_LE_CRITERE_la_restauration_remet_en_ACTIF_et_ROUVRE_LA_PERIODE(
    cx: Connection,
) -> None:
    """`Archived --> Active` — « reactivation explicite autorisee », §24.1.

    **`departure_date` EST DESAPPOSEE, ET C'EST LA MOITIE QUI COMPTE.** `period`
    est `GENERATED ALWAYS AS daterange(arrival_date, departure_date)` : la garder
    rendrait une appartenance `active` dont la periode est deja close, donc
    invisible a toutes les lectures en `period @> :instant` -- `T3`, `T4` et `T7`
    -- **en paraissant justes**. Un test qui n'aurait verifie que `membership_state`
    serait reste vert.
    """
    entite = _entite(cx, "T8-RESTAURE")
    cible = _appartenance(
        cx,
        _personne(cx, "t8-restaure@exalt-company.com"),
        entite,
        etat="archived",
        depart=(ANCRAGE - 5 * JOUR).date(),
    )
    restauration = restaurer_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=_personne(cx, "t8-restaure-a@exalt-company.com"),
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
    )
    assert restauration.etat_precedent == EtatAppartenance.ARCHIVED.value
    assert restauration.version == 2
    etat, depart, version = _etat(cx, cible)
    assert etat == EtatAppartenance.ACTIVE.value
    assert depart is None
    assert version == 2
    #  Et la periode est bien redevenue ouverte, lue comme les routes la lisent.
    assert (
        cx.execute(
            text("SELECT upper_inf(period) FROM entity_membership WHERE id = :c"), {"c": cible}
        ).scalar_one()
        is True
    )


def _profil_equipe(cx: Connection, entite: uuid.UUID, marqueur: str) -> uuid.UUID:
    """Une appartenance ACTIVE portant les CINQ relations que le decor peut poser.

    Metier, statut, cercle, DSM et une responsabilite `BOOSTER` : c'est ce qu'un
    profil reel porte, et c'est ce que l'archivage doit clore. Le sixieme,
    `technical_role_assignment`, est **volontairement absent** -- il sert de
    temoin au cas « la relation n'a JAMAIS existe ».
    """
    personne = _personne(cx, f"t8-{marqueur}@exalt-company.com")
    cible = _appartenance(cx, personne, entite)
    _affecter_le_metier(cx, cible, _metier(cx, entite, f"T8M-{marqueur}"), entite)
    _statut(cx, cible, entite)
    cercle = _cercle(cx, entite, f"T8C-{marqueur}")
    _membre_de_cercle(cx, cible, cercle, entite)
    dsm = _personne(cx, f"t8-{marqueur}-dsm@exalt-company.com")
    _appartenance(cx, dsm, entite)
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value)
    _rattacher_au_dsm(cx, cible, dsm, entite)
    _responsabilite(cx, personne, entite, TypeResponsabilite.BOOSTER.value, cercle=cercle)
    return cible


@pytest.mark.integration
def test_la_restauration_NE_ROUVRE_AUCUNE_AFFECTATION_et_le_DIT(cx: Connection) -> None:
    """Arbitrage du 10/09/2026 — §23.4, et la quatrieme idee du socle du LOT 2.

    **LE DECOR ARCHIVE UN PROFIL REELLEMENT EQUIPE**, et c'est indispensable :
    une appartenance creee directement en `archived` n'a jamais rien eu, et le
    rapport serait vide **a juste titre**. C'est l'archivage qui clot, donc c'est
    l'archivage qui doit avoir eu lieu.

    **CINQ RELATIONS, ET NON SIX** : `technical_role_assignment` n'a JAMAIS
    existe sur ce profil, et on ne redonne pas ce qui n'a pas ete donne. Ce
    temoin est la raison de la forme `bool_or` du service -- voir son en-tete.
    """
    entite = _entite(cx, "T8-CLOS")
    cible = _profil_equipe(cx, entite, "clos")
    acteur = _personne(cx, "t8-clos-a@exalt-company.com")

    archivage = archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
    )
    restauration = restaurer_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=archivage.version,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE + JOUR,
    )
    #  **CE QUI EST A REDONNER EST EXACTEMENT CE QUE L'ARCHIVAGE A CLOS**, et les
    #  deux ensembles sont mesures par deux chemins differents -- le service de
    #  revocation compte ses `UPDATE`, le rapport interroge les periodes.
    assert set(restauration.relations_a_redonner) == set(archivage.relations_closes)
    #  Et les deux familles du §25.2 y sont, dont les ROLES : `RIGHTS-019` dit
    #  que clore une responsabilite « revoque immediatement les permissions ». Un
    #  ESM qui restaure un Booster doit savoir que le cercle n'en a plus.
    assert "framework_responsibility_assignment" in restauration.relations_a_redonner
    assert "dsm_assignment" in restauration.relations_a_redonner
    #  **LE TEMOIN DU CAS « JAMAIS EXISTE »** : la sixieme relation n'est PAS
    #  nommee, parce que ce profil n'a jamais porte de role technique.
    assert "technical_role_assignment" not in restauration.relations_a_redonner
    assert set(restauration.relations_a_redonner) == (
        set(RELATIONS_DE_L_APPARTENANCE) | set(RELATIONS_DE_LA_PERSONNE)
    ) - {"technical_role_assignment"}


@pytest.mark.integration
def test_une_relation_encore_COURANTE_n_est_PAS_rapportee_comme_a_redonner(
    cx: Connection,
) -> None:
    """**LE TEMOIN DU RAPPORT PRECEDENT, ET IL EST INDISPENSABLE.**

    Sans lui, `relations_a_redonner` pourrait nommer toute relation ayant une
    ligne **quoi qu'il arrive** -- une condition inversee, un `bool_or` lu a
    l'envers -- et le test precedent resterait vert. Il ne differe que par une
    affectation metier **rouverte** entre l'archivage et la restauration.
    """
    entite = _entite(cx, "T8-COURANT")
    cible = _profil_equipe(cx, entite, "courant")
    acteur = _personne(cx, "t8-courant-a@exalt-company.com")

    archivage = archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
    )
    #  Une periode metier COURANTE, posee apres l'archivage : c'est la seule
    #  difference avec le test precedent.
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_membership_id, entity_id, "
            "job_catalog_id, starts_at) VALUES (:c, :e, :m, :d)"
        ),
        {
            "c": cible,
            "e": entite,
            "m": _metier(cx, entite, "T8M-rendu"),
            "d": ANCRAGE + dt.timedelta(hours=1),
        },
    )
    restauration = restaurer_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=archivage.version,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE + JOUR,
    )
    assert "membership_job_assignment" not in restauration.relations_a_redonner
    assert set(restauration.relations_a_redonner) == set(archivage.relations_closes) - {
        "membership_job_assignment"
    }


@pytest.mark.integration
def test_la_BASE_refuse_une_restauration_si_la_personne_OCCUPE_deja_ailleurs(
    cx: Connection,
) -> None:
    """`uq_entity_membership_person_id_occupante` — §25.1, traduit en `409`.

    **C'EST LA BASE QUI ARBITRE, ET LA CAUSE N'EST PAS NOMMEE** : elle porte sur
    une appartenance d'une AUTRE entite, que le §5.1 ne laisse pas lire a
    l'appelant. Elle est journalisee cote serveur.

    **LE TEMOIN EST LE TEST PRECEDENT** : meme code, meme etat archive, meme
    version -- la seule difference est l'existence de la seconde appartenance.
    """
    ici, ailleurs = _entite(cx, "T8-OCC-ICI"), _entite(cx, "T8-OCC-AILLEURS")
    personne = _personne(cx, "t8-occ@exalt-company.com")
    cible = _appartenance(
        cx,
        personne,
        ici,
        etat="archived",
        arrivee=(ANCRAGE - 400 * JOUR).date(),
        depart=(ANCRAGE - 300 * JOUR).date(),
    )
    #  La MEME personne, active ailleurs : c'est l'etat que le §25.1 borne.
    _appartenance(cx, personne, ailleurs, arrivee=(ANCRAGE - 200 * JOUR).date())

    with pytest.raises(ErreurApplicative) as capture:
        restaurer_un_profil(
            cx,
            entite=ici,
            cible=cible,
            acteur=_personne(cx, "t8-occ-a@exalt-company.com"),
            version_attendue=1,
            perimetre=_tout_permis(cx, ici, cible),
            instant=ANCRAGE,
        )
    #  **LA CAUSE MESUREE N'EST PAS CELLE QUE J'AVAIS PREVUE, ET LE DIRE VAUT
    #  MIEUX QUE DE CHANGER LE DECOR POUR AVOIR RAISON.** J'attendais
    #  `uq_entity_membership_person_id_occupante`. C'est l'EXCLUSION qui se
    #  declenche d'abord : desapposer `departure_date` rend la periode NON BORNEE,
    #  laquelle chevauche alors toute appartenance posterieure. Les deux refus
    #  sont legitimes, et la base choisit celui qu'elle rencontre en premier.
    assert capture.value.code == CODE_PERIODE_INCOMPATIBLE
    assert capture.value.statut == 409
    #  Et le message ne nomme ni l'autre entite, ni la contrainte.
    assert "T8-OCC-AILLEURS" not in capture.value.message
    assert "entity_membership" not in capture.value.message


@pytest.mark.integration
def test_la_BASE_refuse_une_restauration_par_l_UNICITE_DE_L_OCCUPATION(
    cx: Connection,
) -> None:
    """`uq_entity_membership_person_id_occupante` — §25.1, traduit en `409`.

    **CE TEST EXISTE PARCE QUE LE PRECEDENT NE L'ATTEIGNAIT PAS.** J'avais ecrit
    une seule epreuve en croyant qu'elle exercait l'index unique ; la mesure a dit
    que l'EXCLUSION se declenchait d'abord. La branche `UniqueViolation` du
    traducteur serait donc restee **du code jamais execute**, ce que rien n'aurait
    signale -- §7.25, « un temoin qui n'exerce pas un controle ne prouve rien de
    ce controle ».

    Pour l'atteindre, la seconde appartenance est ANTERIEURE a l'arrivee de celle
    qu'on restaure : la periode redevenue non bornee ne la chevauche donc pas, et
    seule l'unicite de l'occupation reste violee.
    """
    ici, ailleurs = _entite(cx, "T8-UQ-ICI"), _entite(cx, "T8-UQ-AILLEURS")
    personne = _personne(cx, "t8-uq@exalt-company.com")
    #  ACTIVE avec une periode CLOSE : rien ne l'interdit -- la contrainte
    #  `depart_date_si_departed` ne vaut que pour `departed` -- et c'est
    #  precisement ce qui permet d'isoler l'unicite de l'exclusion.
    _appartenance(
        cx,
        personne,
        ailleurs,
        arrivee=(ANCRAGE - 900 * JOUR).date(),
        depart=(ANCRAGE - 800 * JOUR).date(),
    )
    cible = _appartenance(
        cx,
        personne,
        ici,
        etat="archived",
        arrivee=(ANCRAGE - 400 * JOUR).date(),
        depart=(ANCRAGE - 300 * JOUR).date(),
    )
    with pytest.raises(ErreurApplicative) as capture:
        restaurer_un_profil(
            cx,
            entite=ici,
            cible=cible,
            acteur=_personne(cx, "t8-uq-a@exalt-company.com"),
            version_attendue=1,
            perimetre=_tout_permis(cx, ici, cible),
            instant=ANCRAGE,
        )
    assert capture.value.code == CODE_ETAT_INCOMPATIBLE
    assert capture.value.statut == 409
    assert "T8-UQ-AILLEURS" not in capture.value.message


@pytest.mark.integration
def test_la_restauration_est_refusee_sur_une_appartenance_ACTIVE(cx: Connection) -> None:
    """La grille d'etat, prise par le service et non seulement par la route.

    Ce module est appelable hors HTTP -- un script, un export -- et la grille et
    le service ne doivent pas se faire mutuellement confiance : c'est la lecon
    §7.37, ou la borne de taille de page vit AUSSI dans le service.
    """
    entite = _entite(cx, "T8-RESTAURE-KO")
    cible = _appartenance(cx, _personne(cx, "t8-restaure-ko@exalt-company.com"), entite)
    with pytest.raises(ErreurApplicative) as capture:
        restaurer_un_profil(
            cx,
            entite=entite,
            cible=cible,
            acteur=_personne(cx, "t8-restaure-ko-a@exalt-company.com"),
            version_attendue=1,
            #  Le perimetre est FORCE a « restaurer » : sans cela le refus
            #  viendrait du perimetre, et le garde-fou du service ne serait pas
            #  atteint -- un temoin qui n'exerce pas le controle ne prouve rien
            #  de ce controle (§7.25).
            perimetre=PerimetreDuCycleDeVie(actions=frozenset({ActionDeCycleDeVie.RESTAURER})),
            instant=ANCRAGE,
        )
    assert capture.value.code == CODE_ACTION_HORS_PERIMETRE
    assert capture.value.statut == 403


@pytest.mark.integration
def test_archiver_puis_restaurer_ramene_dans_les_etats_OCCUPANTS(cx: Connection) -> None:
    """L'aller-retour complet, et la version monte a chaque acte.

    Le §25.1 borne l'occupation ; ce test prouve que la restauration y RAMENE, ce
    qu'aucune des deux moitiees ne dit seule.
    """
    entite = _entite(cx, "T8-ALLER-RETOUR")
    personne = _personne(cx, "t8-ar@exalt-company.com")
    acteur = _personne(cx, "t8-ar-a@exalt-company.com")
    cible = _appartenance(cx, personne, entite)

    archivage = archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE,
    )
    assert _etat(cx, cible)[0] not in ETATS_OCCUPANTS

    restauration = restaurer_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=archivage.version,
        perimetre=_tout_permis(cx, entite, cible),
        instant=ANCRAGE + JOUR,
    )
    assert _etat(cx, cible)[0] in ETATS_OCCUPANTS
    assert restauration.version == archivage.version + 1


# ---------------------------------------------------------------------------
#  5. « Consulter un profil archive » — §6.1
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_la_fiche_ARCHIVEE_est_servie_la_quand_la_fiche_ORDINAIRE_rend_None(
    cx: Connection,
) -> None:
    """§6.1 : deux lignes distinctes, donc deux populations, donc deux fonctions.

    **ET LA FICHE ORDINAIRE N'EST PAS ASSOUPLIE.** Le test de `T4` qui exige le
    meme 404 pour un profil exclu reste vrai, et c'est son role -- un lot qui
    voudrait le contraire devrait le casser, donc le decider (§7.32).
    """
    entite = _entite(cx, "T8-FICHE")
    cible = _appartenance(cx, _personne(cx, "t8-fiche@exalt-company.com"), entite, etat="archived")
    assert lire_la_fiche(cx, entite=entite, appartenance=cible, instant=ANCRAGE) is None
    fiche = lire_la_fiche_archivee(cx, entite=entite, appartenance=cible, instant=ANCRAGE)
    assert fiche is not None
    assert fiche.id == cible


@pytest.mark.integration
def test_la_fiche_archivee_NE_FILTRE_PAS_la_visibilite(cx: Connection) -> None:
    """L'archivage ne touche pas `profile_visibility` : un archive peut etre `draft`.

    **LE TEMOIN EST LA FICHE ORDINAIRE**, qui rend `None` sur les deux : sans lui,
    le succes pourrait venir d'une requete qui ne filtre plus rien du tout.
    """
    entite = _entite(cx, "T8-VISIBILITE")
    for visibilite in VisibiliteProfil:
        cible = _appartenance(
            cx,
            _personne(cx, f"t8-vis-{visibilite.value}@exalt-company.com"),
            entite,
            etat="archived",
            visibilite=visibilite.value,
        )
        assert lire_la_fiche(cx, entite=entite, appartenance=cible, instant=ANCRAGE) is None
        assert (
            lire_la_fiche_archivee(cx, entite=entite, appartenance=cible, instant=ANCRAGE)
            is not None
        )


@pytest.mark.integration
def test_la_fiche_archivee_rend_None_sur_un_profil_NON_archive(cx: Connection) -> None:
    """Le quatrieme cas de `None` : l'appartenance existe et n'est pas archivee.

    Le refus est identique aux trois autres -- §2.5, « refus par defaut ».
    """
    entite = _entite(cx, "T8-FICHE-ACTIVE")
    cible = _appartenance(cx, _personne(cx, "t8-fiche-active@exalt-company.com"), entite)
    assert lire_la_fiche_archivee(cx, entite=entite, appartenance=cible, instant=ANCRAGE) is None
    #  Le TEMOIN : la fiche ORDINAIRE la sert, donc le decor est bon.
    assert lire_la_fiche(cx, entite=entite, appartenance=cible, instant=ANCRAGE) is not None


@pytest.mark.integration
def test_un_role_TECHNIQUE_global_ouvre_le_cycle_de_vie_partout(cx: Connection) -> None:
    """§5.1 : « la seule exception globale » est le super-administrateur.

    Le decor pose le role technique en base et laisse `resoudre_les_permissions`
    faire son travail : c'est le chemin reel, et non un ensemble de roles fourni a
    la main comme dans les tests de grille ci-dessus.
    """
    from app.permissions.services import resoudre_les_permissions

    entite = _entite(cx, "T8-GLOBAL")
    acteur = _personne(cx, "t8-global@exalt-company.com")
    #  `entity_id` est NULL, et c'est la base qui l'exige :
    #  `ck_technical_role_assignment_portee_selon_le_role`.
    _role_technique(cx, acteur, None, TypeRoleTechnique.SUPER_ADMIN.value)
    cible = _appartenance(cx, _personne(cx, "t8-global-c@exalt-company.com"), entite)

    permissions = resoudre_les_permissions(cx, acteur, entite, ANCRAGE)
    actions = _cycle(cx, entite, cible, set(permissions.roles)).actions
    assert ActionDeCycleDeVie.ARCHIVER in actions
