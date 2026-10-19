"""Annuler, archiver et restaurer un evenement — LOT 8, `T5`, `MVP-L08-US004` (3 sur 3).

TROIS LIGNES DU §11, ET UNE SEULE GRILLE A DEUX FORMES

  « Annuler » et « Archiver » portent, pour le DSM, EXACTEMENT la meme
  cellule que « Publier » — « Perimetre », jamais « cree OU rattache ». Un
  DSM createur seul (non nomme par `event_dsm_scope`) peut MODIFIER un
  evenement de portee Entite qu'il a cree, mais ne peut ni le publier, ni
  l'annuler, ni l'archiver par cette seule voie — §7.45 de la passation,
  deja mesure au LOT 6.

  « Restaurer » n'a QU'UNE grille, et elle exclut DSM/BOOST/OFFICE en bloc,
  comme pour une page (LOT 6, `T7`) ou un parcours (LOT 7, `T11`).
  `ARB-DROIT-003` nomme explicitement « un evenement » parmi les cinq
  ressources que l'ESM restaure librement dans son entite : aucun
  `ECART-066` a rouvrir ici.

LES PRECONDITIONS D'ETAT, ET POURQUOI ELLES NE SONT PAS LAISSEES A LA GRILLE

  « Annuler » n'est offert qu'a un `published` — annuler un brouillon que
  personne n'a jamais vu contournerait la porte de publication. « Archiver »
  n'a pas de precondition au-dela de « pas deja archive » : brouillon,
  publie et annule sont tous les trois archivables. « Restaurer » rend
  TOUJOURS `draft`, jamais l'etat anterieur a l'archivage — restaurer n'est
  pas publier, `RIGHTS-001`.
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
    CODE_VERSION_OBSOLETE,
    EvenementAnnule,
    EvenementArchive,
    EvenementRestaure,
    annuler_un_evenement,
    archiver_un_evenement,
    creer_un_evenement,
    publier_un_evenement,
    restaurer_un_evenement,
)
from app.events.lecture import ClassementEvenement, lister_les_evenements
from app.events.perimetre import (
    ActionEvenement,
    PorteeDeCreation,
    resoudre_le_perimetre_de_l_evenement,
)
from app.events.routes import DemandeDAnnulationDEvenement, DemandeDeTransitionDEvenement
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L8T5"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
DEBUT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 10, 10, 10, 0, tzinfo=dt.UTC)

# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================


def test_la_demande_d_annulation_ne_porte_NI_etat_NI_archivage() -> None:
    champs = set(DemandeDAnnulationDEvenement.model_fields)
    assert champs == {"version", "motif"}


def test_la_demande_de_transition_ne_porte_QUE_la_version() -> None:
    """Archiver et restaurer partagent la meme forme — `version`, et le motif
    conditionnel du §18.1 (LOT 10 `T7`, `ECART-064`, obligatoire pour SUPER
    seulement)."""
    assert set(DemandeDeTransitionDEvenement.model_fields) == {"version", "motif"}


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
            "VALUES (:email, :normalisee, 'Annul', 'L8T5', 'active') RETURNING id"
        ),
        {"email": adresse, "normalisee": adresse},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
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
) -> uuid.UUID:
    personne = _personne(cx, suffixe)
    _appartenance(cx, entite, personne)
    if responsabilite is not None:
        _responsabilite(
            cx,
            entite=entite,
            personne=personne,
            type_de_responsabilite=responsabilite,
            cercle=cercle,
        )
    return personne


def _roles(cx: Connection, *, acteur: uuid.UUID, entite: uuid.UUID) -> frozenset[RoleDeLaMatrice]:
    return frozenset(resoudre_les_permissions(cx, acteur, entite, DEMAIN).roles)


def _creer(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    portee: PorteeDeCreation,
    cercle: str | None = None,
) -> uuid.UUID:
    return creer_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        roles=_roles(cx, acteur=acteur, entite=entite),
        title="Petit-dejeuner",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=portee,
        code_de_cercle=cercle,
        code_de_bureau=None,
        instant=DEMAIN,
    ).identifiant


def _perimetre(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, evenement: uuid.UUID
) -> frozenset[ActionEvenement]:
    return resoudre_le_perimetre_de_l_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        evenement=evenement,
        roles=_roles(cx, acteur=acteur, entite=entite),
        instant=DEMAIN,
    ).actions


def _publier(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, evenement: uuid.UUID, version: int
) -> None:
    publier_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=version,
        instant=DEMAIN,
    )


def _annuler(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    evenement: uuid.UUID,
    version: int,
    motif: str | None = None,
) -> EvenementAnnule:
    return annuler_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=version,
        motif=motif,
        instant=DEMAIN,
    )


def _archiver(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, evenement: uuid.UUID, version: int
) -> EvenementArchive:
    return archiver_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=version,
        instant=DEMAIN,
    )


def _restaurer(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, evenement: uuid.UUID, version: int
) -> EvenementRestaure:
    return restaurer_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=version,
        instant=DEMAIN,
    )


# ----------------------------------------------------------------------------
#  2.1 Le cycle complet, temoin principal de `T5`
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_le_cycle_complet_PUBLIE_ANNULE_ARCHIVE_RESTAURE(cx: Connection) -> None:
    """Un seul evenement traverse les quatre etats, dans cet ordre exact.

    C'est le temoin que la fiche de lot exige explicitement pour `T5` :
    « grilles distinctes ; restauration ESM fonctionnelle ; annulé toujours
    visible ».
    """
    entite = _entite(cx, "CYC1")
    esm = _acteur(cx, entite, "esm-cycle", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)

    _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)

    annule = _annuler(cx, entite=entite, acteur=esm, evenement=evenement, version=2, motif="Pluie")
    assert annule.etat == "cancelled"
    assert annule.annule_le is not None
    assert annule.motif_d_annulation == "Pluie"

    #  TEMOIN DE LA FICHE : un evenement annule reste visible (cahier §10.6).
    page = lister_les_evenements(
        cx,
        entite=entite,
        classement=ClassementEvenement.A_VENIR,
        page=1,
        taille=25,
        instant=DEMAIN,
    )
    assert any(e.id == evenement and e.state == "cancelled" for e in page.evenements)

    archive = _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=3)
    assert archive.etat == "archived"
    assert archive.archive_le is not None

    #  Une fois archive, l'evenement DISPARAIT de la consultation (`T2`).
    page_apres_archivage = lister_les_evenements(
        cx,
        entite=entite,
        classement=ClassementEvenement.A_VENIR,
        page=1,
        taille=25,
        instant=DEMAIN,
    )
    assert all(e.id != evenement for e in page_apres_archivage.evenements)

    #  `cancelled_at`/`cancellation_reason` SURVIVENT a l'archivage — un fait,
    #  pas un residu, meme parti que `published_at` pour une page (LOT 6).
    ligne = cx.execute(
        text("SELECT cancelled_at, cancellation_reason FROM event WHERE id = :e"),
        {"e": evenement},
    ).one()
    assert ligne[0] is not None
    assert ligne[1] == "Pluie"

    restaure = _restaurer(cx, entite=entite, acteur=esm, evenement=evenement, version=4)
    #  La restauration rend TOUJOURS `draft`, jamais l'etat anterieur.
    assert restaure.etat == "draft"

    #  `archived_at`/`archived_by_person_id` sont EFFACES par la restauration.
    ligne = cx.execute(
        text("SELECT archived_at, archived_by_person_id FROM event WHERE id = :e"),
        {"e": evenement},
    ).one()
    assert ligne[0] is None
    assert ligne[1] is None

    #  Un second geste, explicite, est requis pour republier.
    assert ActionEvenement.PUBLIER in _perimetre(cx, entite=entite, acteur=esm, evenement=evenement)


# ----------------------------------------------------------------------------
#  2.2 « Annuler » — meme grille « Perimetre » que « Publier »
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_evenement_BROUILLON_n_offre_PAS_ANNULER(cx: Connection) -> None:
    """Annuler un brouillon contournerait la porte de publication."""
    entite = _entite(cx, "ANN1")
    esm = _acteur(cx, entite, "esm-brouillon", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    assert ActionEvenement.ANNULER not in _perimetre(
        cx, entite=entite, acteur=esm, evenement=evenement
    )
    with pytest.raises(ErreurApplicative) as excinfo:
        _annuler(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    assert excinfo.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_un_DSM_NOMME_annule_mais_un_DSM_CREATEUR_SEUL_ne_le_peut_pas(cx: Connection) -> None:
    """`Perimetre` denote les CONSULTANTS NOMMES, jamais « cree par lui » seul."""
    entite = _entite(cx, "ANN2")
    dsm_nomme = _acteur(cx, entite, "dsm-nomme", responsabilite=TypeResponsabilite.DSM.value)
    dsm_etranger = _acteur(cx, entite, "dsm-etranger", responsabilite=TypeResponsabilite.DSM.value)

    #  Le DSM nomme : portee CONSULTANTS, donc lui-meme `event_dsm_scope.dsm_person_id`.
    evenement_nomme = _creer(
        cx, entite=entite, acteur=dsm_nomme, portee=PorteeDeCreation.CONSULTANTS
    )
    _publier(cx, entite=entite, acteur=dsm_nomme, evenement=evenement_nomme, version=1)
    assert ActionEvenement.ANNULER in _perimetre(
        cx, entite=entite, acteur=dsm_nomme, evenement=evenement_nomme
    )
    annule = _annuler(cx, entite=entite, acteur=dsm_nomme, evenement=evenement_nomme, version=2)
    assert annule.etat == "cancelled"

    #  Le DSM createur SEUL, portee ENTITE : il modifie, mais n'annule pas.
    evenement_entite = _creer(cx, entite=entite, acteur=dsm_nomme, portee=PorteeDeCreation.ENTITE)
    _publier(cx, entite=entite, acteur=dsm_nomme, evenement=evenement_entite, version=1)
    perimetre_createur = _perimetre(cx, entite=entite, acteur=dsm_nomme, evenement=evenement_entite)
    assert ActionEvenement.MODIFIER in perimetre_createur
    assert ActionEvenement.ANNULER not in perimetre_createur
    assert ActionEvenement.ARCHIVER not in perimetre_createur

    #  Et un DSM totalement etranger n'a rien du tout, sur aucun des deux.
    assert (
        _perimetre(cx, entite=entite, acteur=dsm_etranger, evenement=evenement_nomme) == frozenset()
    )


@pytest.mark.integration
def test_annuler_avec_une_version_obsolete_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "ANN3")
    esm = _acteur(cx, entite, "esm-version", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    with pytest.raises(ErreurApplicative) as excinfo:
        _annuler(cx, entite=entite, acteur=esm, evenement=evenement, version=99)
    assert excinfo.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_annuler_un_evenement_DEJA_annule_est_refuse(cx: Connection) -> None:
    """Idempotence refusee : la seconde annulation ne trouve plus `published`."""
    entite = _entite(cx, "ANN4")
    esm = _acteur(cx, entite, "esm-double", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    _annuler(cx, entite=entite, acteur=esm, evenement=evenement, version=2)
    with pytest.raises(ErreurApplicative) as excinfo:
        _annuler(cx, entite=entite, acteur=esm, evenement=evenement, version=3)
    assert excinfo.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_un_BOOSTER_annule_et_archive_SON_evenement_de_cercle(cx: Connection) -> None:
    entite = _entite(cx, "ANN5")
    cercle = _cercle(cx, entite, "TECH")
    booster = _acteur(
        cx, entite, "booster-ann", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=cercle
    )
    evenement = _creer(
        cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH"
    )
    _publier(cx, entite=entite, acteur=booster, evenement=evenement, version=1)
    annule = _annuler(cx, entite=entite, acteur=booster, evenement=evenement, version=2)
    assert annule.etat == "cancelled"
    archive = _archiver(cx, entite=entite, acteur=booster, evenement=evenement, version=3)
    assert archive.etat == "archived"


# ----------------------------------------------------------------------------
#  2.3 « Archiver » — depuis BROUILLON, PUBLIE ou ANNULE, sans precondition
# ----------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("depuis", ["draft", "published", "cancelled"])
def test_archiver_reussit_DEPUIS_les_trois_etats_non_archives(cx: Connection, depuis: str) -> None:
    entite = _entite(cx, f"ARC-{depuis[:3].upper()}")
    esm = _acteur(cx, entite, f"esm-{depuis}", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    version = 1
    if depuis in ("published", "cancelled"):
        _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=version)
        version += 1
    if depuis == "cancelled":
        _annuler(cx, entite=entite, acteur=esm, evenement=evenement, version=version)
        version += 1
    archive = _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=version)
    assert archive.etat == "archived"


@pytest.mark.integration
def test_archiver_un_evenement_DEJA_archive_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "ARC9")
    esm = _acteur(cx, entite, "esm-reatt", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    with pytest.raises(ErreurApplicative) as excinfo:
        _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=2)
    assert excinfo.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_un_evenement_ARCHIVE_n_offre_QUE_RESTAURER_a_l_ESM(cx: Connection) -> None:
    entite = _entite(cx, "ARC2")
    esm = _acteur(cx, entite, "esm-archive", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    assert _perimetre(cx, entite=entite, acteur=esm, evenement=evenement) == frozenset(
        {ActionEvenement.RESTAURER}
    )


# ----------------------------------------------------------------------------
#  2.4 « Restaurer » — ESM/ADM-E/SUPER seuls, DSM/BOOST/OFFICE a TIRET
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_ESM_restaure_un_evenement_ARCHIVE_de_son_entite(cx: Connection) -> None:
    entite = _entite(cx, "RES1")
    esm = _acteur(cx, entite, "esm-restaure", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    restaure = _restaurer(cx, entite=entite, acteur=esm, evenement=evenement, version=2)
    assert restaure.etat == "draft"


@pytest.mark.integration
def test_un_DSM_NOMME_un_BOOSTER_et_un_RESPONSABLE_DE_BUREAU_n_ont_RIEN_sur_un_ARCHIVE(
    cx: Connection,
) -> None:
    """§11 « Restaurer » met DSM/BOOST/OFFICE a TIRET, MEME s'ils ont archive eux-memes."""
    entite = _entite(cx, "RES2")
    cercle = _cercle(cx, entite, "TECH")
    dsm = _acteur(cx, entite, "dsm-res", responsabilite=TypeResponsabilite.DSM.value)
    booster = _acteur(
        cx, entite, "booster-res", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=cercle
    )

    evenement_dsm = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.CONSULTANTS)
    _archiver(cx, entite=entite, acteur=dsm, evenement=evenement_dsm, version=1)
    assert _perimetre(cx, entite=entite, acteur=dsm, evenement=evenement_dsm) == frozenset()

    evenement_booster = _creer(
        cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH"
    )
    _archiver(cx, entite=entite, acteur=booster, evenement=evenement_booster, version=1)
    assert _perimetre(cx, entite=entite, acteur=booster, evenement=evenement_booster) == frozenset()


@pytest.mark.integration
def test_restaurer_avec_une_version_obsolete_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "RES3")
    esm = _acteur(cx, entite, "esm-resver", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _archiver(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    with pytest.raises(ErreurApplicative) as excinfo:
        _restaurer(cx, entite=entite, acteur=esm, evenement=evenement, version=99)
    assert excinfo.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_restaurer_un_evenement_NON_archive_est_refuse(cx: Connection) -> None:
    """Le service revalide `archived_at IS NOT NULL` — meme si le role convient."""
    entite = _entite(cx, "RES4")
    esm = _acteur(cx, entite, "esm-nonarc", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    with pytest.raises(ErreurApplicative) as excinfo:
        _restaurer(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    assert excinfo.value.code == CODE_VERSION_OBSOLETE
