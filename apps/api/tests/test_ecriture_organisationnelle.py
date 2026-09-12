"""L'ecriture dans son perimetre — LOT 5, `T7`, story `MVP-L05-US006`.

CE QUE CE FICHIER EPROUVE, ET POURQUOI CHAQUE REFUS EST APPARIE

  Le critere de `T7` est « un DSM modifie SON consultant · REFUSE sur un autre ·
  `OFFICE` REFUSE partout ». **Deux des trois sont des refus**, et le §7.39 le
  dit : cinq refus indistinguables laissent passer un `WHERE` faux, qui refuse
  tout et les garde tous verts -- c'est le defaut `T2-3`, huit refus verts pour
  la mauvaise raison.

  Chaque refus est donc apparie a un temoin qui ne differe QUE par la valeur en
  cause : le meme acteur sur une cible rattachee, le meme role sur la meme cible,
  ou -- le plus utile -- **le meme decor ou seul l'INSTANT avance**.

LE TEMPS EST INJECTE, ET C'EST CE QUI REND LE TEMOIN FUTUR POSSIBLE

  `resoudre_le_perimetre` prend son instant en argument. Le rattachement DSM
  FUTUR est donc eprouve sans attendre : meme ligne, meme acteur, meme cible, et
  le perimetre passe de vide a six champs quand l'instant franchit `starts_at`.
  Sans ce temoin, le refus mesure pourrait venir de n'importe quel filtre trop
  large.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite, TypeRoleTechnique
from app.organization.services import responsabilite_dsm_active
from app.people.ecriture import (
    CODE_CHAMP_HORS_PERIMETRE,
    CODE_PERIODE_INCOMPATIBLE,
    CODE_VALEUR_REFUSEE,
    CODE_VERSION_OBSOLETE,
    modifier_les_donnees_organisationnelles,
)
from app.people.modeles import SituationProfessionnelle
from app.permissions.perimetre import (
    CHAMPS_DU_BOOSTER,
    ROLES_D_ECRITURE,
    TOUS_LES_CHAMPS,
    ChampOrganisationnel,
    PerimetreDEcriture,
    resoudre_le_perimetre,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

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
#  Le decor. Chaque aide est locale a ce fichier : aucun test du depot n'importe
#  d'un autre, et chaque decor est taille a sa question.
# ---------------------------------------------------------------------------


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        #  **TROIS PARAMETRES DISTINCTS POUR UNE SEULE VALEUR, ET C'EST NECESSAIRE.**
        #  `entity.code` est `character varying(64)` quand `display_name` et `city`
        #  sont `text` : un parametre lie PARTAGE rend « inconsistent types deduced
        #  for parameter $1 », et le message ne nomme ni la table ni la colonne.
        #  §7.25 -- et j'ai rejoue cette lecon en reunissant les trois, ce qui a
        #  fait tomber SEIZE tests d'un coup sur la meme cause.
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, adresse: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Sujet', 'L5T7', 'active') RETURNING id"
        ),
        #  `email` et `email_normalized` sont TOUS DEUX `character varying(320)`,
        #  donc un parametre partage serait legitime ici -- le §7.25 le mesure. Deux
        #  noms quand meme : le discriminant est le TYPE, que le lecteur n'a pas
        #  sous les yeux.
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID, *, etat: str = "active"
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'published') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": (ANCRAGE - 30 * JOUR).date(), "etat": etat},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    type_resp: str,
    *,
    debut: dt.datetime,
    cercle: uuid.UUID | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :p, :d)"
        ),
        {"p": personne, "e": entite, "t": type_resp, "c": cercle, "d": debut},
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


def _client(cx: Connection, nom: str, entite: uuid.UUID) -> uuid.UUID:
    """Un client, ET sa liaison a l'entite — sans quoi un declencheur refuse la mission.

    **C'EST LA BASE QUI ME L'A APPRIS, ET SON MESSAGE ETAIT EXCELLENT** :
    « professional_status_assignment : une mission exige un client active dans
    cette entite (client …, entite …) ». Un declencheur, pas un `CHECK`, et il
    nomme la regle ET les identifiants -- le diagnostic a pris une lecture.

    `canonical_name` est en MINUSCULES : `ck_client_canonical_name_en_minuscules`
    l'exige, et c'est tout l'objet des deux colonnes -- le canonique est la forme
    normalisee, l'affichage garde la casse saisie.
    """
    client = cx.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affichage, 'active') RETURNING id"
        ),
        {"canonique": nom.lower(), "affichage": nom},
    ).scalar_one()
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )
    return client  # type: ignore[no-any-return]


def _rattacher_au_dsm(
    cx: Connection,
    cible: uuid.UUID,
    dsm: uuid.UUID,
    entite: uuid.UUID,
    *,
    debut: dt.datetime,
) -> None:
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (consultant_membership_id, entity_id, dsm_person_id, "
            "starts_at) VALUES (:c, :e, :d, :debut)"
        ),
        {"c": cible, "e": entite, "d": dsm, "debut": debut},
    )


def _membre_de_cercle(
    cx: Connection,
    cible: uuid.UUID,
    cercle: uuid.UUID,
    entite: uuid.UUID,
    *,
    type_appartenance: str,
    debut: dt.datetime,
) -> None:
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_membership_id, entity_id, circle_id, "
            "membership_type, starts_at) VALUES (:c, :e, :cercle, :type, :debut)"
        ),
        {"c": cible, "e": entite, "cercle": cercle, "type": type_appartenance, "debut": debut},
    )


def _statut(
    cx: Connection,
    cible: uuid.UUID,
    entite: uuid.UUID,
    *,
    statut: str,
    client: uuid.UUID | None,
    debut: dt.datetime,
) -> None:
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_membership_id, entity_id, "
            "status, client_id, starts_at) VALUES (:c, :e, :s, :cl, :debut)"
        ),
        {"c": cible, "e": entite, "s": statut, "cl": client, "debut": debut},
    )


def _perimetre(
    cx: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible: uuid.UUID,
    roles: set[RoleDeLaMatrice],
    instant: dt.datetime = ANCRAGE,
) -> PerimetreDEcriture:
    return resoudre_le_perimetre(
        cx, entite=entite, acteur=acteur, cible=cible, roles=frozenset(roles), instant=instant
    )


# ---------------------------------------------------------------------------
#  1. Le perimetre — la matrice §6.1, §6.2 et §23.1
# ---------------------------------------------------------------------------


def test_les_six_champs_sont_ceux_du_cahier_10_2() -> None:
    """La liste est ECRITE dans le corpus, pas choisie dans le code."""
    assert [c.value for c in ChampOrganisationnel] == [
        "date_d_arrivee",
        "metier",
        "statut",
        "client",
        "dsm",
        "cercle_principal",
    ]


def test_EMP_NEW_et_OFFICE_ne_sont_PAS_des_roles_d_ecriture() -> None:
    """§6.1 : la colonne `OFFICE` est ENTIEREMENT a tiret, et le §6.2 le redit."""
    assert RoleDeLaMatrice.RESPONSABLE_DE_BUREAU not in ROLES_D_ECRITURE
    assert RoleDeLaMatrice.EMPLOYE not in ROLES_D_ECRITURE
    assert {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    } == ROLES_D_ECRITURE


def test_le_BOOSTER_est_prive_du_SEUL_champ_DSM() -> None:
    """§6.1 : « Cercle, HORS CHANGEMENT DE DSM ». Un seul champ, et c'est celui-la."""
    assert {ChampOrganisationnel.DSM} == TOUS_LES_CHAMPS - CHAMPS_DU_BOOSTER


@pytest.mark.integration
def test_un_DSM_a_les_six_champs_sur_SON_consultant_et_AUCUN_sur_un_autre(cx: Connection) -> None:
    """§6.2 : « un DSM ne peut modifier que les consultants ayant un rattachement ACTIF vers lui ».

    **LE REFUS ET SON TEMOIN NE DIFFERENT QUE PAR LE RATTACHEMENT.** Meme acteur,
    meme entite, meme instant, deux cibles : un `WHERE` trop large les rendrait
    toutes deux autorisees, un `WHERE` faux toutes deux refusees.
    """
    entite = _entite(cx, "T7-DSM")
    dsm = _personne(cx, "t7-dsm@exalt-company.com")
    _appartenance(cx, dsm, entite)
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value, debut=ANCRAGE - JOUR)

    a_lui = _appartenance(cx, _personne(cx, "t7-alui@exalt-company.com"), entite)
    _rattacher_au_dsm(cx, a_lui, dsm, entite, debut=ANCRAGE - JOUR)
    a_un_autre = _appartenance(cx, _personne(cx, "t7-autre@exalt-company.com"), entite)

    assert _perimetre(cx, entite, dsm, a_lui, {RoleDeLaMatrice.DSM}).champs == TOUS_LES_CHAMPS
    assert _perimetre(cx, entite, dsm, a_un_autre, {RoleDeLaMatrice.DSM}).champs == frozenset()


@pytest.mark.integration
def test_un_rattachement_DSM_FUTUR_n_accorde_RIEN_et_SEUL_l_instant_change(cx: Connection) -> None:
    """Le temoin le plus utile du fichier : **seul l'instant avance**.

    `ends_at IS NULL` seul aurait rendu ce rattachement actif. C'est le piege du
    §7.32, et `ECART-056` l'a trouve dans `responsabilite_dsm_active`.
    """
    entite = _entite(cx, "T7-FUTUR")
    dsm = _personne(cx, "t7-futur-dsm@exalt-company.com")
    _appartenance(cx, dsm, entite)
    _responsabilite(cx, dsm, entite, TypeResponsabilite.DSM.value, debut=ANCRAGE - JOUR)
    cible = _appartenance(cx, _personne(cx, "t7-futur-c@exalt-company.com"), entite)
    #  Le rattachement commence DEMAIN, et son `ends_at` est nul.
    _rattacher_au_dsm(cx, cible, dsm, entite, debut=ANCRAGE + JOUR)

    avant = _perimetre(cx, entite, dsm, cible, {RoleDeLaMatrice.DSM}, instant=ANCRAGE)
    apres = _perimetre(cx, entite, dsm, cible, {RoleDeLaMatrice.DSM}, instant=ANCRAGE + 2 * JOUR)
    assert avant.champs == frozenset(), "un rattachement FUTUR ne doit rien accorder"
    assert apres.champs == TOUS_LES_CHAMPS, "le meme rattachement, l'instant franchi, accorde tout"


@pytest.mark.integration
def test_OFFICE_est_refuse_et_le_TEMOIN_est_ESM_sur_la_MEME_cible(cx: Connection) -> None:
    """« `OFFICE` refuse partout », et le temoin prouve que la cible est modifiable."""
    entite = _entite(cx, "T7-OFFICE")
    acteur = _personne(cx, "t7-office@exalt-company.com")
    _appartenance(cx, acteur, entite)
    cible = _appartenance(cx, _personne(cx, "t7-office-c@exalt-company.com"), entite)

    assert (
        _perimetre(cx, entite, acteur, cible, {RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}).champs
        == frozenset()
    )
    assert _perimetre(cx, entite, acteur, cible, {RoleDeLaMatrice.EMPLOYE}).champs == frozenset()
    #  Le TEMOIN : la meme cible, un role d'entite, et les six champs s'ouvrent.
    assert _perimetre(cx, entite, acteur, cible, {RoleDeLaMatrice.ESM}).champs == TOUS_LES_CHAMPS


@pytest.mark.integration
def test_un_BOOSTER_a_CINQ_champs_sur_un_membre_PRINCIPAL_et_AUCUN_sur_un_SECONDAIRE(
    cx: Connection,
) -> None:
    """§6.2, et la roadmap le confirme dans sa demonstration attendue.

    « Pour un membre SECONDAIRE, ses actions doivent rester limitees aux donnees
    du cercle et ne pas permettre de modifier un autre cercle principal » -- or
    aucun des six champs n'est une donnee du cercle, sauf `cercle_principal` que
    la phrase exclut. La roadmap : « IMPOSSIBILITE pour le Booster de modifier
    son cercle principal ou son client ».
    """
    entite = _entite(cx, "T7-BOOST")
    cercle = _cercle(cx, entite, "T7-DATA")
    booster = _personne(cx, "t7-boost@exalt-company.com")
    _appartenance(cx, booster, entite)
    _responsabilite(
        cx, booster, entite, TypeResponsabilite.BOOSTER.value, debut=ANCRAGE - JOUR, cercle=cercle
    )

    principal = _appartenance(cx, _personne(cx, "t7-boost-p@exalt-company.com"), entite)
    _membre_de_cercle(
        cx,
        principal,
        cercle,
        entite,
        type_appartenance=TypeAppartenanceCercle.PRINCIPAL.value,
        debut=ANCRAGE - JOUR,
    )
    secondaire = _appartenance(cx, _personne(cx, "t7-boost-s@exalt-company.com"), entite)
    _membre_de_cercle(
        cx,
        secondaire,
        cercle,
        entite,
        type_appartenance=TypeAppartenanceCercle.SECONDARY.value,
        debut=ANCRAGE - JOUR,
    )
    hors_cercle = _appartenance(cx, _personne(cx, "t7-boost-h@exalt-company.com"), entite)

    sur_principal = _perimetre(cx, entite, booster, principal, {RoleDeLaMatrice.BOOSTER}).champs
    assert sur_principal == CHAMPS_DU_BOOSTER
    assert ChampOrganisationnel.DSM not in sur_principal, "§6.1 : hors changement de DSM"
    assert (
        _perimetre(cx, entite, booster, secondaire, {RoleDeLaMatrice.BOOSTER}).champs == frozenset()
    )
    assert (
        _perimetre(cx, entite, booster, hors_cercle, {RoleDeLaMatrice.BOOSTER}).champs
        == frozenset()
    )


@pytest.mark.integration
def test_le_CUMUL_de_BOOST_et_ESM_rend_le_DSM_modifiable(cx: Connection) -> None:
    """§23.1 : « les droits de plusieurs responsabilites se cumulent ».

    « Hors changement de DSM » est une restriction de ROLE, non de ressource : le
    §23.2 ne la fait donc PAS survivre au cumul. Ce n'est pas un trou, c'est la
    lecture des deux sections ensemble -- et le dire vaut mieux que de laisser
    croire qu'un Booster-ESM reste borne.
    """
    entite = _entite(cx, "T7-CUMUL")
    cercle = _cercle(cx, entite, "T7-CUMUL-C")
    acteur = _personne(cx, "t7-cumul@exalt-company.com")
    _appartenance(cx, acteur, entite)
    _responsabilite(
        cx, acteur, entite, TypeResponsabilite.BOOSTER.value, debut=ANCRAGE - JOUR, cercle=cercle
    )
    cible = _appartenance(cx, _personne(cx, "t7-cumul-c@exalt-company.com"), entite)
    _membre_de_cercle(
        cx,
        cible,
        cercle,
        entite,
        type_appartenance=TypeAppartenanceCercle.PRINCIPAL.value,
        debut=ANCRAGE - JOUR,
    )

    seul = _perimetre(cx, entite, acteur, cible, {RoleDeLaMatrice.BOOSTER}).champs
    cumule = _perimetre(
        cx, entite, acteur, cible, {RoleDeLaMatrice.BOOSTER, RoleDeLaMatrice.ESM}
    ).champs
    assert ChampOrganisationnel.DSM not in seul
    assert cumule == TOUS_LES_CHAMPS


@pytest.mark.integration
def test_une_appartenance_ARCHIVEE_est_refusee_MEME_au_SUPER_ADMINISTRATEUR(
    cx: Connection,
) -> None:
    """§23.2 : « une interdiction liee a l'ETAT prevaut sur le cumul des roles ».

    Le §6.1 traite separement « consulter un profil archive » et « reactiver un
    profil archive », tous deux restreints, et l'archivage est `T8`. La grille
    d'etat s'applique donc a tous les roles, `SUPER` compris.
    """
    entite = _entite(cx, "T7-ARCHIVE")
    acteur = _personne(cx, "t7-archive-a@exalt-company.com")
    _appartenance(cx, acteur, entite)
    archivee = _appartenance(
        cx, _personne(cx, "t7-archive-c@exalt-company.com"), entite, etat="archived"
    )
    active = _appartenance(cx, _personne(cx, "t7-archive-v@exalt-company.com"), entite)

    roles = {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}
    assert _perimetre(cx, entite, acteur, archivee, roles).champs == frozenset()
    #  Le TEMOIN : la seule difference est l'etat.
    assert _perimetre(cx, entite, acteur, active, roles).champs == TOUS_LES_CHAMPS


@pytest.mark.integration
def test_une_cible_d_une_AUTRE_entite_est_refusee(cx: Connection) -> None:
    """§25.3 : le couple `(id, entity_id)` porte l'isolation, pas un filtre sur l'entite seule."""
    ici, ailleurs = _entite(cx, "T7-ICI"), _entite(cx, "T7-AILLEURS")
    acteur = _personne(cx, "t7-iso-a@exalt-company.com")
    _appartenance(cx, acteur, ici)
    cible_ailleurs = _appartenance(cx, _personne(cx, "t7-iso-c@exalt-company.com"), ailleurs)

    roles = {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}
    assert _perimetre(cx, ici, acteur, cible_ailleurs, roles).champs == frozenset()


# ---------------------------------------------------------------------------
#  2. L'ecriture — clore puis ouvrir, §18.4 et §23.4
# ---------------------------------------------------------------------------


def _tout(cx: Connection, entite: uuid.UUID, cible: uuid.UUID) -> PerimetreDEcriture:
    return PerimetreDEcriture(champs=TOUS_LES_CHAMPS)


def _periodes_de_statut(cx: Connection, cible: uuid.UUID) -> list[dict[str, Any]]:
    return [
        dict(ligne)
        for ligne in cx.execute(
            text(
                "SELECT status, client_id, starts_at, ends_at "
                "FROM professional_status_assignment WHERE entity_membership_id = :c "
                "ORDER BY starts_at"
            ),
            {"c": cible},
        ).mappings()
    ]


@pytest.mark.integration
def test_une_modification_CLOTURE_la_periode_et_en_OUVRE_une_autre(cx: Connection) -> None:
    """Critere de sortie n°6 : « les affectations structurantes ne sont JAMAIS ecrasees ».

    §23.4 : « la suppression d'un role actif CLOTURE la relation au lieu d'effacer
    l'historique ». Les DEUX periodes doivent rester lisibles apres l'ecriture.
    """
    entite = _entite(cx, "T7-CLORE")
    acteur = _personne(cx, "t7-clore-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-clore-c@exalt-company.com"), entite)
    client = _client(cx, "T7-CLORE-CLIENT", entite)
    _statut(
        cx,
        cible,
        entite,
        statut=SituationProfessionnelle.MISSION.value,
        client=client,
        debut=ANCRAGE - 10 * JOUR,
    )

    modification = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.STATUT: SituationProfessionnelle.INTERCONTRACT.value},
        perimetre=_tout(cx, entite, cible),
        instant=ANCRAGE,
    )

    periodes = _periodes_de_statut(cx, cible)
    assert len(periodes) == 2, "l'ancienne periode doit SUBSISTER, non etre ecrasee"
    assert periodes[0]["ends_at"] == ANCRAGE, "la premiere est CLOSE a l'instant"
    assert periodes[0]["status"] == SituationProfessionnelle.MISSION.value
    assert periodes[0]["client_id"] == client, "l'historique garde le client de la mission"
    assert periodes[1]["starts_at"] == ANCRAGE, "la seconde OUVRE au meme instant"
    assert periodes[1]["ends_at"] is None
    assert modification.champs == {ChampOrganisationnel.STATUT}


@pytest.mark.integration
def test_passer_en_INTERCONTRACT_retire_le_client_sans_qu_on_le_nomme(cx: Connection) -> None:
    """§30.5 : « un intercontrat n'a pas de client », et le `CHECK` est une BICONDITIONNELLE.

    Reporter le client courant ferait refuser une demande parfaitement claire.
    """
    entite = _entite(cx, "T7-INTER")
    acteur = _personne(cx, "t7-inter-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-inter-c@exalt-company.com"), entite)
    _statut(
        cx,
        cible,
        entite,
        statut=SituationProfessionnelle.MISSION.value,
        client=_client(cx, "T7-INTER-CLIENT", entite),
        debut=ANCRAGE - 10 * JOUR,
    )

    modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.STATUT: SituationProfessionnelle.INTERCONTRACT.value},
        perimetre=_tout(cx, entite, cible),
        instant=ANCRAGE,
    )
    courante = _periodes_de_statut(cx, cible)[-1]
    assert courante["status"] == SituationProfessionnelle.INTERCONTRACT.value
    assert courante["client_id"] is None


@pytest.mark.integration
def test_un_CLIENT_seul_REPORTE_le_statut_courant(cx: Connection) -> None:
    """Statut et client sont UNE seule periode : la valeur non demandee est reportee."""
    entite = _entite(cx, "T7-REPORT")
    acteur = _personne(cx, "t7-report-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-report-c@exalt-company.com"), entite)
    _statut(
        cx,
        cible,
        entite,
        statut=SituationProfessionnelle.MISSION.value,
        client=_client(cx, "T7-REPORT-A", entite),
        debut=ANCRAGE - 10 * JOUR,
    )
    nouveau = _client(cx, "T7-REPORT-B", entite)

    modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.CLIENT: nouveau},
        perimetre=_tout(cx, entite, cible),
        instant=ANCRAGE,
    )
    courante = _periodes_de_statut(cx, cible)[-1]
    assert courante["client_id"] == nouveau
    assert courante["status"] == SituationProfessionnelle.MISSION.value, "le statut est REPORTE"


@pytest.mark.integration
def test_une_version_OBSOLETE_rend_409_sans_rien_ecrire(cx: Connection) -> None:
    """§18.4 : « une version obsolete produit une reponse 409 SANS ECRASEMENT SILENCIEUX »."""
    entite = _entite(cx, "T7-VERSION")
    acteur = _personne(cx, "t7-version-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-version-c@exalt-company.com"), entite)
    metier = _metier(cx, entite, "T7-VERSION-M")

    with pytest.raises(ErreurApplicative) as refus:
        modifier_les_donnees_organisationnelles(
            cx,
            entite=entite,
            cible=cible,
            acteur=acteur,
            version_attendue=99,
            demande={ChampOrganisationnel.METIER: metier},
            perimetre=_tout(cx, entite, cible),
            instant=ANCRAGE,
        )
    assert refus.value.code == CODE_VERSION_OBSOLETE
    assert refus.value.statut == 409
    reste = cx.execute(
        text("SELECT count(*) FROM membership_job_assignment WHERE entity_membership_id = :c"),
        {"c": cible},
    ).scalar_one()
    assert reste == 0, "rien ne doit avoir ete ecrit"


@pytest.mark.integration
def test_la_version_MONTE_quand_un_champ_change_et_PAS_sinon(cx: Connection) -> None:
    """Une demande sans effet ne doit pas faire echouer la suivante."""
    entite = _entite(cx, "T7-IDEM")
    acteur = _personne(cx, "t7-idem-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-idem-c@exalt-company.com"), entite)
    metier = _metier(cx, entite, "T7-IDEM-M")

    premiere = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.METIER: metier},
        perimetre=_tout(cx, entite, cible),
        instant=ANCRAGE,
    )
    assert premiere.version == 2
    assert premiere.champs == {ChampOrganisationnel.METIER}

    seconde = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=2,
        demande={ChampOrganisationnel.METIER: metier},
        perimetre=_tout(cx, entite, cible),
        instant=ANCRAGE + JOUR,
    )
    assert seconde.version == 2, "aucun champ change, donc aucune version consommee"
    assert seconde.champs == frozenset()
    periodes = cx.execute(
        text("SELECT count(*) FROM membership_job_assignment WHERE entity_membership_id = :c"),
        {"c": cible},
    ).scalar_one()
    assert periodes == 1, "l'historique ne doit pas se remplir de periodes nulles"


@pytest.mark.integration
def test_une_periode_FUTURE_fait_REFUSER_la_modification(cx: Connection) -> None:
    """La contrainte d'EXCLUSION refuse, et ce module traduit son refus en 409.

    Ecrire par-dessus reecrirait un avenir decide ailleurs. La base arbitre, pas
    ce module -- et c'est ce qui rend le critere n°6 STRUCTUREL.
    """
    entite = _entite(cx, "T7-FUTUR-P")
    acteur = _personne(cx, "t7-futurp-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-futurp-c@exalt-company.com"), entite)
    metier = _metier(cx, entite, "T7-FUTURP-M")
    autre = _metier(cx, entite, "T7-FUTURP-N")
    #  Une affectation qui commence DEMAIN et ne finit pas.
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_membership_id, entity_id, "
            "job_catalog_id, starts_at) VALUES (:c, :e, :m, :debut)"
        ),
        {"c": cible, "e": entite, "m": metier, "debut": ANCRAGE + JOUR},
    )

    with pytest.raises(ErreurApplicative) as refus:
        modifier_les_donnees_organisationnelles(
            cx,
            entite=entite,
            cible=cible,
            acteur=acteur,
            version_attendue=1,
            demande={ChampOrganisationnel.METIER: autre},
            perimetre=_tout(cx, entite, cible),
            instant=ANCRAGE,
        )
    assert refus.value.code == CODE_PERIODE_INCOMPATIBLE
    assert refus.value.statut == 409


@pytest.mark.integration
def test_un_champ_HORS_PERIMETRE_rend_403_et_les_nomme(cx: Connection) -> None:
    """Le perimetre est controle AVANT toute lecture d'etat — §2.5, refus par defaut."""
    entite = _entite(cx, "T7-HORS")
    acteur = _personne(cx, "t7-hors-a@exalt-company.com")
    cible = _appartenance(cx, _personne(cx, "t7-hors-c@exalt-company.com"), entite)

    with pytest.raises(ErreurApplicative) as refus:
        modifier_les_donnees_organisationnelles(
            cx,
            entite=entite,
            cible=cible,
            acteur=acteur,
            version_attendue=1,
            demande={ChampOrganisationnel.DSM: acteur},
            perimetre=PerimetreDEcriture(champs=CHAMPS_DU_BOOSTER),
            instant=ANCRAGE,
        )
    assert refus.value.code == CODE_CHAMP_HORS_PERIMETRE
    assert refus.value.statut == 403
    assert refus.value.details == {"champs": ["dsm"]}


# ---------------------------------------------------------------------------
#  3. `ECART-056` — le defaut latent que `T7` allait consommer
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_responsabilite_dsm_active_IGNORE_une_affectation_FUTURE(cx: Connection) -> None:
    """`ECART-056`. Le test qui MANQUAIT : les deux seuls existants ne voyaient que l'entite.

    Avec `ends_at IS NULL` seul, cette fonction rendait un identifiant pour une
    responsabilite qui n'a pas commence -- et `attribuer_la_categorie_dg` SAUTAIT
    alors la creation de la responsabilite que le §8.4 exige.

    **AUCUNE CONTRAINTE N'INTERDIT UN `starts_at` FUTUR**, mesure le 09/09/2026 :
    les deux seuls `CHECK` de la table portent sur le type et sur la portee.
    """
    entite = _entite(cx, "T7-E56")
    personne = _personne(cx, "t7-e56@exalt-company.com")
    _appartenance(cx, personne, entite)
    #  Une responsabilite DSM qui commence dans un an, `ends_at` nul.
    _responsabilite(cx, personne, entite, TypeResponsabilite.DSM.value, debut=ANCRAGE + 365 * JOUR)

    assert responsabilite_dsm_active(cx, entite=entite, personne=personne) is None, (
        "une responsabilite FUTURE ne doit pas etre rendue comme active"
    )

    #  Le TEMOIN : la meme table, une responsabilite qui a commence.
    autre = _personne(cx, "t7-e56-bis@exalt-company.com")
    _appartenance(cx, autre, entite)
    _responsabilite(cx, autre, entite, TypeResponsabilite.DSM.value, debut=ANCRAGE - 365 * JOUR)
    assert responsabilite_dsm_active(cx, entite=entite, personne=autre) is not None


@pytest.mark.integration
def test_un_role_technique_SUPER_ouvre_les_six_champs(cx: Connection) -> None:
    """Le role technique du §8.6 passe par la meme resolution que les responsabilites."""
    entite = _entite(cx, "T7-TECH")
    acteur = _personne(cx, "t7-tech-a@exalt-company.com")
    _appartenance(cx, acteur, entite)
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, NULL, :r, :d)"
        ),
        {"p": acteur, "r": TypeRoleTechnique.SUPER_ADMIN.value, "d": ANCRAGE - JOUR},
    )
    cible = _appartenance(cx, _personne(cx, "t7-tech-c@exalt-company.com"), entite)
    assert (
        _perimetre(cx, entite, acteur, cible, {RoleDeLaMatrice.SUPER_ADMINISTRATEUR}).champs
        == TOUS_LES_CHAMPS
    )


# ---------------------------------------------------------------------------
#  Ajout de `T8` du LOT 5 : un refus que `T7` rendait en 500
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_une_DATE_D_ARRIVEE_posterieure_au_depart_rend_422_et_NON_500(
    cx: Connection,
) -> None:
    """**DEFAUT DE `T7`, TROUVE PAR `T8` LE 10/09/2026. `ECART-058`.**

    `period` est `GENERATED ALWAYS AS daterange(arrival_date, departure_date)` :
    une colonne GENEREE peut refuser une valeur **avant** toute contrainte, et
    elle leve alors « range lower bound must be less than or equal to range upper
    bound » -- une `DataException`, donc un `sqlalchemy.exc.DataError`.

    Or `modifier_les_donnees_organisationnelles` ne capturait que
    `IntegrityError`. **La route sortait en 500**, mesure a l'appui, sur un etat
    parfaitement atteignable : une appartenance `active` PEUT porter une
    `departure_date`, la contrainte `depart_date_si_departed` ne contraignant que
    l'etat `departed`.

    **CE N'EST PAS `T8` QUI L'A INTRODUIT, ET C'EST LA LECON.** `T8` a rencontre
    le meme refus sur SA date de depart, a vu qu'il n'etait pas traduit, puis a
    demande *quel autre code porte la meme exigence* -- la moitie du §7.38 qui
    avait ete oubliee en `T3` et payee deux semaines plus tard par `ECART-055`.
    """
    entite = _entite(cx, "T7-PLAGE")
    acteur = _personne(cx, "t7-plage-a@exalt-company.com")
    _appartenance(cx, acteur, entite)
    #  ACTIVE **avec** une date de depart : le schema l'autorise.
    cible = cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, 'active', 'consultant', 'published') RETURNING id"
        ),
        {
            "p": _personne(cx, "t7-plage-c@exalt-company.com"),
            "e": entite,
            "arrivee": (ANCRAGE - 60 * JOUR).date(),
            "depart": (ANCRAGE - 30 * JOUR).date(),
        },
    ).scalar_one()

    with pytest.raises(ErreurApplicative) as capture:
        modifier_les_donnees_organisationnelles(
            cx,
            entite=entite,
            cible=cible,
            acteur=acteur,
            version_attendue=1,
            demande={ChampOrganisationnel.DATE_D_ARRIVEE: (ANCRAGE - 10 * JOUR).date()},
            perimetre=_tout(cx, entite, cible),
            instant=ANCRAGE,
        )
    assert capture.value.statut == 422
    assert capture.value.code == CODE_VALEUR_REFUSEE


@pytest.mark.integration
def test_une_DATE_D_ARRIVEE_ANTERIEURE_au_depart_passe(cx: Connection) -> None:
    """**LE TEMOIN DU TEST PRECEDENT, ET IL EST UN TEST A PART.**

    Il ne peut pas vivre dans le meme : un ordre refuse par PostgreSQL **avorte
    la transaction entiere** -- « current transaction is aborted, commands
    ignored until end of transaction block » -- et le decor de ce fichier est une
    seule transaction annulee a la fin. Le temoin mesure ici est donc separe, et
    il ne differe du refus que par la date demandee.
    """
    entite = _entite(cx, "T7-PLAGE-OK")
    acteur = _personne(cx, "t7-plage-ok-a@exalt-company.com")
    _appartenance(cx, acteur, entite)
    cible = cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, departure_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, :depart, 'active', 'consultant', 'published') RETURNING id"
        ),
        {
            "p": _personne(cx, "t7-plage-ok-c@exalt-company.com"),
            "e": entite,
            "arrivee": (ANCRAGE - 60 * JOUR).date(),
            "depart": (ANCRAGE - 30 * JOUR).date(),
        },
    ).scalar_one()
    modification = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.DATE_D_ARRIVEE: (ANCRAGE - 50 * JOUR).date()},
        perimetre=_tout(cx, entite, cible),
        instant=ANCRAGE,
    )
    assert modification.champs == frozenset({ChampOrganisationnel.DATE_D_ARRIVEE})
