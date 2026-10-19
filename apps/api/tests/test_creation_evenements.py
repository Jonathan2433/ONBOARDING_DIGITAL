"""Creer un evenement, dans la portee resolue — LOT 8, `T3`, `MVP-L08-US004` (1/3).

`ECART-067`, INSTRUIT PUIS CLOS PAR L'ARBITRAGE DE JONATHAN (`DEC-622`)

  La matrice §11 donne au DSM deux portees de creation, « Entite ou
  consultants », que le modele §17.2 ne representait pas : aucune des trois
  portees stockables n'est « les consultants d'un DSM ». L'arbitrage retient une
  cinquieme table, `event_dsm_scope`, symetrique aux deux tables sœurs mais
  portant directement le DSM — jamais une liste de consultants figee a la
  creation. Les temoins de schema (isolation, unicite) sont dans
  `test_evenements.py` ; ce fichier prouve le SERVICE qui s'en sert.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. structure : aucun champ de la demande n'est de nature participant, et
     aucun ne permet de publier par la porte de la creation (meme motif que
     `T6` du LOT 6 pour les contenus) ;
  2. la grille complete de `peut_creer_un_evenement`, role par role, portee par
     portee — **chaque refus est apparie a son temoin positif**, sans quoi une
     fonction qui refuserait toujours passerait les refus (§7.39) ;
  3. le service `creer_un_evenement`, sur une vraie connexion : chaque role
     DANS sa portee reussit, chaque role HORS sa portee echoue au MEME refus
     qu'un role absent — et l'asymetrie entre DEUX porteurs du MEME role (deux
     Boosters, deux responsables de bureau) le confirme ;
  4. l'isolation inter-entites sur la resolution par CODE : un cercle ou un
     bureau valide ailleurs rend `ressource_introuvable`, jamais une fuite ;
  5. la fenetre temporelle d'une responsabilite — seul l'instant avance.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.events.ecriture import (
    CODE_ACCES_REFUSE,
    CODE_CHRONOLOGIE_INVALIDE,
    CODE_RATTACHEMENT_REQUIS,
    CODE_RESSOURCE_INTROUVABLE,
    EvenementCree,
    creer_un_evenement,
)
from app.events.perimetre import (
    ROLES_DE_CREATION_EVENEMENT,
    PorteeDeCreation,
    peut_creer_un_evenement,
)
from app.events.routes import DemandeDeCreationDEvenement
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L8T3"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
DEBUT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 10, 10, 10, 0, tzinfo=dt.UTC)

# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================


def test_aucun_champ_de_la_demande_n_est_de_nature_participant() -> None:
    """Critere de sortie n°1, prolonge aux modeles de requete — voir `T1`.

    Le perimetre est **derive des champs du modele** (§7.27) : un participant,
    une inscription ou une notification y entrerait sans qu'on ait pense a
    mettre ce test a jour.
    """
    suspects = {
        "participant",
        "inscription",
        "registration",
        "presence",
        "attendance",
        "notification",
        "recurrence",
        "occurrence",
    }
    for nom in DemandeDeCreationDEvenement.model_fields:
        minuscule = nom.lower()
        assert not any(s in minuscule for s in suspects), (
            f"DemandeDeCreationDEvenement.{nom} porte un nom de nature participant/notification"
        )


def test_la_demande_ne_porte_NI_etat_NI_date_de_publication() -> None:
    """§11 separe « Creer » de « Publier » (portee **Perimetre**, `T4`).

    Une demande qui porterait un etat permettrait de publier par la porte de
    la creation — meme motif que `DemandeDeCreationDePage` au LOT 6.
    """
    champs = set(DemandeDeCreationDEvenement.model_fields)
    for interdit in ("etat", "state", "publiee_le", "published_at", "publication", "cancelled"):
        assert interdit not in champs, (
            f"`{interdit}` permettrait d'agir par la porte de la creation"
        )


def test_EMP_seul_ne_porte_AUCUNE_portee_de_creation() -> None:
    """§11 : la colonne `EMP` est entierement a tiret sur la ligne « Creer »."""
    assert RoleDeLaMatrice.EMPLOYE not in ROLES_DE_CREATION_EVENEMENT
    for portee in PorteeDeCreation:
        assert not peut_creer_un_evenement(frozenset({RoleDeLaMatrice.EMPLOYE}), portee)


#  **LA GRILLE COMPLETE DU §11, ET CHAQUE CELLULE EST UN TEMOIN.** Un role qui
#  n'apparait pas en cle d'une portee n'y a AUCUN droit — c'est la portee du
#  dict `_PORTEES_AUTORISEES_PAR_ROLE`, et ce test la confronte a la matrice
#  telle qu'ELLE l'ecrit, pas telle que le code la redit.
_GRILLE_DU_11: dict[RoleDeLaMatrice, frozenset[PorteeDeCreation]] = {
    RoleDeLaMatrice.EMPLOYE: frozenset(),
    RoleDeLaMatrice.DSM: frozenset({PorteeDeCreation.ENTITE, PorteeDeCreation.CONSULTANTS}),
    RoleDeLaMatrice.ESM: frozenset({PorteeDeCreation.ENTITE}),
    RoleDeLaMatrice.BOOSTER: frozenset({PorteeDeCreation.CERCLE}),
    RoleDeLaMatrice.RESPONSABLE_DE_BUREAU: frozenset({PorteeDeCreation.BUREAU}),
    RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE: frozenset({PorteeDeCreation.ENTITE}),
    RoleDeLaMatrice.SUPER_ADMINISTRATEUR: frozenset({PorteeDeCreation.ENTITE}),
}


def test_peut_creer_un_evenement_suit_EXACTEMENT_la_matrice_11() -> None:
    """Chaque role, seul, contre les quatre portees — 28 cellules, pas une de moins.

    **UN SEUL ROLE A LA FOIS** : `peut_creer_un_evenement` prend un ENSEMBLE de
    roles parce qu'une personne peut en cumuler plusieurs (§23.1), mais la
    grille elle-meme se lit role par role, et un role glisse ici isole pour que
    le test attribue chaque refus a la bonne cause.
    """
    assert set(_GRILLE_DU_11) == set(RoleDeLaMatrice)
    for role, portees_attendues in _GRILLE_DU_11.items():
        for portee in PorteeDeCreation:
            attendu = portee in portees_attendues
            obtenu = peut_creer_un_evenement(frozenset({role}), portee)
            assert obtenu == attendu, f"{role} / {portee} : attendu {attendu}, obtenu {obtenu}"


def test_un_DSM_rattrape_PAR_cumul_de_role_garde_le_droit_du_role_cumule() -> None:
    """§23.1 : l'union des droits porte sur les COUPLES (role, portee).

    Un DSM qui est AUSSI Booster de son cercle peut y creer un evenement de
    portee `cercle`, non parce que `DSM` le permettrait seul, mais parce que
    l'ENSEMBLE cumule `{DSM, BOOST}` le permet.
    """
    assert not peut_creer_un_evenement(frozenset({RoleDeLaMatrice.DSM}), PorteeDeCreation.CERCLE)
    assert peut_creer_un_evenement(
        frozenset({RoleDeLaMatrice.DSM, RoleDeLaMatrice.BOOSTER}), PorteeDeCreation.CERCLE
    )


# ============================================================================
#  2. Le service, sur une vraie connexion
# ============================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


def _entite(cx: Connection, suffixe: str) -> uuid.UUID:
    code = f"{MARQUEUR}-{suffixe}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalisee, 'Creation', 'L8T3', 'active') RETURNING id"
        ),
        {"email": adresse, "normalisee": adresse},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    """Rend `entite` PRINCIPALE de `personne` — condition de `resoudre_les_permissions`."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_de_responsabilite: str,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, office_id, "
            " assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :type, :cercle, :bureau, :par, :debut)"
        ),
        {
            "p": personne,
            "e": entite,
            "type": type_de_responsabilite,
            "cercle": cercle,
            "bureau": bureau,
            "par": personne,
            "debut": debut,
        },
    )


def _acteur(
    cx: Connection,
    entite: uuid.UUID,
    suffixe: str,
    *,
    responsabilite: str | None = None,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
) -> uuid.UUID:
    """Une personne RATTACHEE a `entite`, avec une responsabilite optionnelle."""
    personne = _personne(cx, suffixe)
    _appartenance(cx, entite, personne)
    if responsabilite is not None:
        _responsabilite(
            cx,
            entite=entite,
            personne=personne,
            type_de_responsabilite=responsabilite,
            cercle=cercle,
            bureau=bureau,
            debut=debut,
        )
    return personne


def _roles(
    cx: Connection, *, acteur: uuid.UUID, entite: uuid.UUID, instant: dt.datetime = DEMAIN
) -> frozenset[RoleDeLaMatrice]:
    return frozenset(resoudre_les_permissions(cx, acteur, entite, instant).roles)


def _creer(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    portee: PorteeDeCreation,
    cercle: str | None = None,
    bureau: str | None = None,
    debut: dt.datetime = DEBUT,
    fin: dt.datetime = FIN,
    instant: dt.datetime = DEMAIN,
    motif: str | None = None,
) -> EvenementCree:
    #  LOT 10, `T7` : `motif` — obligatoire pour `SUPER` seulement (`ECART-064`).
    return creer_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        roles=_roles(cx, acteur=acteur, entite=entite, instant=instant),
        title="Petit-dejeuner",
        description=None,
        starts_at=debut,
        ends_at=fin,
        location_text=None,
        portee=portee,
        code_de_cercle=cercle,
        code_de_bureau=bureau,
        instant=instant,
        motif=motif,
    )


def _nombre_de_lignes_de_portee(cx: Connection, evenement: uuid.UUID) -> dict[str, int]:
    #  Les trois noms viennent d'un TUPLE LITTERAL ci-dessous, jamais d'une
    #  entree de requete : l'interpolation est sure.
    return {
        table: cx.execute(
            text(f"SELECT count(*) FROM {table} WHERE event_id = :e"),  # noqa: S608
            {"e": evenement},
        ).scalar_one()
        for table in ("event_circle_scope", "event_office_scope", "event_dsm_scope")
    }


# ----------------------------------------------------------------------------
#  2.1 Chaque role, DANS sa portee
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_ESM_cree_un_evenement_de_portee_ENTITE_sans_aucune_ligne_de_portee(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ESM1")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    cree = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    assert cree.etat == "draft"
    assert _nombre_de_lignes_de_portee(cx, cree.identifiant) == {
        "event_circle_scope": 0,
        "event_office_scope": 0,
        "event_dsm_scope": 0,
    }


@pytest.mark.integration
def test_un_ADM_E_cree_un_evenement_de_portee_ENTITE(cx: Connection) -> None:
    entite = _entite(cx, "ADME")
    adm_e = _acteur(cx, entite, "adme")
    #  `ADM-E` est un role TECHNIQUE, pas une responsabilite FRAMEWORK — pose
    #  par `technical_role_assignment`, comme ailleurs dans le projet.
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, "
            "starts_at) VALUES (:p, :e, 'ENTITY_ADMIN', :debut)"
        ),
        {"p": adm_e, "e": entite, "debut": JANVIER},
    )
    cree = _creer(cx, entite=entite, acteur=adm_e, portee=PorteeDeCreation.ENTITE)
    assert cree.etat == "draft"


@pytest.mark.integration
def test_un_SUPER_ADMINISTRATEUR_cree_un_evenement_de_portee_ENTITE(cx: Connection) -> None:
    """§11 : « Global » pour `SUPER` — la route est deja bornee a une entite."""
    entite = _entite(cx, "SUP1")
    super_admin = _personne(cx, "super")
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, "
            "starts_at) VALUES (:p, NULL, 'SUPER_ADMIN', :debut)"
        ),
        {"p": super_admin, "debut": JANVIER},
    )
    cree = _creer(
        cx, entite=entite, acteur=super_admin, portee=PorteeDeCreation.ENTITE, motif="Decor de test"
    )
    assert cree.etat == "draft"


@pytest.mark.integration
def test_un_DSM_cree_un_evenement_de_portee_ENTITE(cx: Connection) -> None:
    """§11 : le DSM porte AUSSI « Entite », pas seulement « consultants »."""
    entite = _entite(cx, "DSME")
    dsm = _acteur(cx, entite, "dsm-ent", responsabilite=TypeResponsabilite.DSM.value)
    cree = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.ENTITE)
    assert cree.etat == "draft"


@pytest.mark.integration
def test_un_DSM_cree_un_evenement_de_portee_CONSULTANTS_et_EST_LA_PORTEE(cx: Connection) -> None:
    """`ECART-067` : `event_dsm_scope.dsm_person_id` porte l'ACTEUR lui-meme."""
    entite = _entite(cx, "DSMC")
    dsm = _acteur(cx, entite, "dsm-cons", responsabilite=TypeResponsabilite.DSM.value)
    cree = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.CONSULTANTS)
    assert cree.etat == "draft"
    assert _nombre_de_lignes_de_portee(cx, cree.identifiant) == {
        "event_circle_scope": 0,
        "event_office_scope": 0,
        "event_dsm_scope": 1,
    }
    porteur = cx.execute(
        text("SELECT dsm_person_id FROM event_dsm_scope WHERE event_id = :e"),
        {"e": cree.identifiant},
    ).scalar_one()
    assert porteur == dsm


@pytest.mark.integration
def test_un_BOOSTER_cree_un_evenement_pour_SON_cercle(cx: Connection) -> None:
    entite = _entite(cx, "BST1")
    cercle = _cercle(cx, entite, "TECH")
    booster = _acteur(
        cx, entite, "booster", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=cercle
    )
    cree = _creer(cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH")
    assert cree.etat == "draft"
    cercle_pose = cx.execute(
        text("SELECT circle_id FROM event_circle_scope WHERE event_id = :e"),
        {"e": cree.identifiant},
    ).scalar_one()
    assert cercle_pose == cercle


@pytest.mark.integration
def test_un_responsable_de_BUREAU_cree_un_evenement_pour_SON_bureau(cx: Connection) -> None:
    entite = _entite(cx, "OFF1")
    bureau = _bureau(cx, entite, "BDX")
    responsable = _acteur(
        cx,
        entite,
        "office",
        responsabilite=TypeResponsabilite.OFFICE_MANAGER.value,
        bureau=bureau,
    )
    cree = _creer(
        cx, entite=entite, acteur=responsable, portee=PorteeDeCreation.BUREAU, bureau="BDX"
    )
    assert cree.etat == "draft"
    bureau_pose = cx.execute(
        text("SELECT office_id FROM event_office_scope WHERE event_id = :e"),
        {"e": cree.identifiant},
    ).scalar_one()
    assert bureau_pose == bureau


# ----------------------------------------------------------------------------
#  2.2 Chaque role, HORS sa portee — et l'ASYMETRIE entre deux porteurs du
#      MEME role
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_ESM_est_refuse_sur_la_portee_CERCLE(cx: Connection) -> None:
    entite = _entite(cx, "ESM2")
    esm = _acteur(cx, entite, "esm-refus", responsabilite=TypeResponsabilite.ESM.value)
    _cercle(cx, entite, "TECH")
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.CERCLE, cercle="TECH")
    assert echec.value.code == CODE_ACCES_REFUSE
    assert echec.value.statut == 403


@pytest.mark.integration
def test_un_DSM_est_refuse_sur_les_portees_CERCLE_et_BUREAU(cx: Connection) -> None:
    """§11 : le DSM n'a ni `Cercle` ni `Bureau` — seulement `Entite`/`consultants`."""
    entite = _entite(cx, "DSMR")
    dsm = _acteur(cx, entite, "dsm-refus", responsabilite=TypeResponsabilite.DSM.value)
    _cercle(cx, entite, "TECH")
    _bureau(cx, entite, "BDX")
    for portee, code in ((PorteeDeCreation.CERCLE, "TECH"), (PorteeDeCreation.BUREAU, "BDX")):
        with pytest.raises(ErreurApplicative) as echec:
            if portee is PorteeDeCreation.CERCLE:
                _creer(cx, entite=entite, acteur=dsm, portee=portee, cercle=code)
            else:
                _creer(cx, entite=entite, acteur=dsm, portee=portee, bureau=code)
        assert echec.value.code == CODE_ACCES_REFUSE


@pytest.mark.integration
def test_un_BOOSTER_est_refuse_sur_la_portee_ENTITE(cx: Connection) -> None:
    entite = _entite(cx, "BST2")
    cercle = _cercle(cx, entite, "TECH")
    booster = _acteur(
        cx, entite, "booster-ent", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=cercle
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=booster, portee=PorteeDeCreation.ENTITE)
    assert echec.value.code == CODE_ACCES_REFUSE


@pytest.mark.integration
def test_un_BOOSTER_est_refuse_sur_le_cercle_d_un_AUTRE_BOOSTER(cx: Connection) -> None:
    """L'ASYMETRIE DECISIVE : le role est identique, seule la CIBLE differe."""
    entite = _entite(cx, "BST3")
    mon_cercle = _cercle(cx, entite, "TECH")
    #  Le cercle d'AUTRUI n'a besoin que d'exister — son identifiant n'est pas
    #  relu, seul son CODE est nomme dans la demande de creation.
    _cercle(cx, entite, "DATA")
    booster = _acteur(
        cx,
        entite,
        "booster-asym",
        responsabilite=TypeResponsabilite.BOOSTER.value,
        cercle=mon_cercle,
    )
    #  Le TEMOIN, sans lequel une fonction toujours refusante passerait aussi :
    temoin = _creer(
        cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH"
    )
    assert temoin.etat == "draft"
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="DATA")
    assert echec.value.code == CODE_ACCES_REFUSE


@pytest.mark.integration
def test_un_responsable_de_BUREAU_est_refuse_sur_le_bureau_d_un_AUTRE_responsable(
    cx: Connection,
) -> None:
    entite = _entite(cx, "OFF2")
    mon_bureau = _bureau(cx, entite, "BDX")
    _bureau(cx, entite, "LIL")
    responsable = _acteur(
        cx,
        entite,
        "office-asym",
        responsabilite=TypeResponsabilite.OFFICE_MANAGER.value,
        bureau=mon_bureau,
    )
    assert (
        _creer(
            cx, entite=entite, acteur=responsable, portee=PorteeDeCreation.BUREAU, bureau="BDX"
        ).etat
        == "draft"
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=responsable, portee=PorteeDeCreation.BUREAU, bureau="LIL")
    assert echec.value.code == CODE_ACCES_REFUSE


@pytest.mark.integration
def test_un_EMPLOYE_SEUL_est_refuse_pour_TOUTE_portee(cx: Connection) -> None:
    entite = _entite(cx, "EMP1")
    employe = _acteur(cx, entite, "emp")
    for portee in PorteeDeCreation:
        with pytest.raises(ErreurApplicative) as echec:
            _creer(cx, entite=entite, acteur=employe, portee=portee)
        assert echec.value.code == CODE_ACCES_REFUSE


# ----------------------------------------------------------------------------
#  2.3 Isolation inter-entites sur la resolution par CODE
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_cercle_valide_dans_une_AUTRE_entite_rend_ressource_introuvable(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "ISO1"), _entite(cx, "ISO2")
    _cercle(cx, ailleurs, "TECH")
    #  La contrainte `ck_..._portee_selon_le_type` exige qu'une responsabilite
    #  BOOSTER porte un `circle_id` : celui-ci n'est pas le cercle NOMME dans la
    #  demande, seul son CODE compte pour le refus attendu.
    mon_cercle = _cercle(cx, ici, "SALES")
    booster = _acteur(
        cx, ici, "booster-iso", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=mon_cercle
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=ici, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH")
    assert echec.value.code == CODE_RESSOURCE_INTROUVABLE
    assert echec.value.statut == 422


@pytest.mark.integration
def test_un_bureau_valide_dans_une_AUTRE_entite_rend_ressource_introuvable(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "ISO3"), _entite(cx, "ISO4")
    _bureau(cx, ailleurs, "BDX")
    mon_bureau = _bureau(cx, ici, "LIL")
    responsable = _acteur(
        cx,
        ici,
        "office-iso",
        responsabilite=TypeResponsabilite.OFFICE_MANAGER.value,
        bureau=mon_bureau,
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=ici, acteur=responsable, portee=PorteeDeCreation.BUREAU, bureau="BDX")
    assert echec.value.code == CODE_RESSOURCE_INTROUVABLE


@pytest.mark.integration
def test_la_portee_CERCLE_exige_un_code_de_cercle(cx: Connection) -> None:
    entite = _entite(cx, "REQ1")
    cercle = _cercle(cx, entite, "TECH")
    booster = _acteur(
        cx, entite, "booster-req", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=cercle
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE)
    assert echec.value.code == CODE_RATTACHEMENT_REQUIS
    assert echec.value.statut == 422


@pytest.mark.integration
def test_la_portee_BUREAU_exige_un_code_de_bureau(cx: Connection) -> None:
    entite = _entite(cx, "REQ2")
    bureau = _bureau(cx, entite, "BDX")
    responsable = _acteur(
        cx,
        entite,
        "office-req",
        responsabilite=TypeResponsabilite.OFFICE_MANAGER.value,
        bureau=bureau,
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=responsable, portee=PorteeDeCreation.BUREAU)
    assert echec.value.code == CODE_RATTACHEMENT_REQUIS


# ----------------------------------------------------------------------------
#  2.4 Chronologie, et la fenetre temporelle d'une responsabilite
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_une_chronologie_invalide_est_refusee_EN_422_PAS_EN_500(cx: Connection) -> None:
    entite = _entite(cx, "CHR1")
    esm = _acteur(cx, entite, "esm-chrono", responsabilite=TypeResponsabilite.ESM.value)
    with pytest.raises(ErreurApplicative) as echec:
        _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE, debut=FIN, fin=DEBUT)
    assert echec.value.code == CODE_CHRONOLOGIE_INVALIDE
    assert echec.value.statut == 422


@pytest.mark.integration
def test_une_responsabilite_FUTURE_n_accorde_RIEN_et_SEUL_l_instant_change(
    cx: Connection,
) -> None:
    """`ECART-056` : une affectation future a elle aussi un `ends_at` nul.

    La compter comme active accorderait un droit qui n'existe pas encore. Le
    couple decisif ne differe QUE par l'instant.
    """
    entite = _entite(cx, "FUT1")
    cercle = _cercle(cx, entite, "TECH")
    booster = _acteur(
        cx,
        entite,
        "booster-futur",
        responsabilite=TypeResponsabilite.BOOSTER.value,
        cercle=cercle,
        debut=dt.datetime(2027, 1, 1, tzinfo=dt.UTC),
    )
    with pytest.raises(ErreurApplicative) as echec:
        _creer(
            cx,
            entite=entite,
            acteur=booster,
            portee=PorteeDeCreation.CERCLE,
            cercle="TECH",
            instant=DEMAIN,
        )
    assert echec.value.code == CODE_ACCES_REFUSE

    #  Le TEMOIN : la MEME responsabilite, APRES sa date de debut.
    cree = _creer(
        cx,
        entite=entite,
        acteur=booster,
        portee=PorteeDeCreation.CERCLE,
        cercle="TECH",
        instant=dt.datetime(2027, 2, 1, tzinfo=dt.UTC),
    )
    assert cree.etat == "draft"
