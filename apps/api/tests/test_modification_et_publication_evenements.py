"""Modifier et publier un evenement — LOT 8, `T4`, `MVP-L08-US004` (2 sur 3).

DEUX LIGNES VOISINES DU §11, ET UNE SEULE CELLULE DIFFERE

  « Modifier » et « Publier » portent EXACTEMENT la meme grille pour
  `ESM`/`ADM-E`/`SUPER`/`BOOST`/`OFFICE`. Seul le DSM diverge : « Modifier »
  accepte « cree OU rattache a son perimetre », « Publier » n'accepte QUE
  « Perimetre » — et `Perimetre`, lu par le §3 pour CE role, denote ses
  CONSULTANTS NOMMES (`event_dsm_scope`), jamais « l'evenement qu'il a cree »
  seul. C'est le §7.45 de la passation, deja mesure au LOT 6 pour l'ESM (ou
  les deux mots coincident) — ici ils NE coincident PAS.

LES RATTACHEMENTS MULTIPLES, ET LEUR REVALIDATION INDEPENDANTE

  Un evenement peut recevoir PLUSIEURS cercles ou PLUSIEURS bureaux a la fois
  (modele §17.2, « un ou plusieurs »). Mais le droit de MODIFIER cet evenement
  et le droit d'y ATTACHER tel cercle precis sont deux questions distinctes
  (§23.1) : un Booster autorise a modifier (par SON cercle) ne peut pas pour
  autant y attacher le cercle d'un AUTRE Booster. Chaque code est donc revalide
  individuellement.
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
    CODE_DOUBLON_DANS_LA_LISTE,
    CODE_RESSOURCE_INTROUVABLE,
    CODE_VERSION_OBSOLETE,
    EvenementModifie,
    creer_un_evenement,
    modifier_un_evenement,
    publier_un_evenement,
)
from app.events.perimetre import (
    ActionEvenement,
    PorteeDeCreation,
    resoudre_le_perimetre_de_l_evenement,
)
from app.events.routes import DemandeDeModificationDEvenement, DemandeDePublicationDEvenement
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L8T4"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
DEBUT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 10, 10, 10, 0, tzinfo=dt.UTC)
PLUS_TARD_DEBUT = dt.datetime(2026, 11, 10, 9, 0, tzinfo=dt.UTC)
PLUS_TARD_FIN = dt.datetime(2026, 11, 10, 10, 0, tzinfo=dt.UTC)

# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================


def test_la_demande_de_modification_ne_porte_NI_etat_NI_publication() -> None:
    """§11 separe « Modifier » de « Publier » — meme motif que `T3`."""
    champs = set(DemandeDeModificationDEvenement.model_fields)
    for interdit in ("etat", "state", "publiee_le", "published_at", "publication", "cancelled"):
        assert interdit not in champs, f"`{interdit}` permettrait de publier par la modification"


def test_la_demande_de_publication_ne_porte_QUE_la_version() -> None:
    """Publier est immediat, en un clic : aucun autre champ n'a de sens ici."""
    assert set(DemandeDePublicationDEvenement.model_fields) == {"version"}


def test_cercles_et_bureaux_n_ont_aucun_champ_de_nature_participant() -> None:
    suspects = {"participant", "inscription", "notification", "presence"}
    for nom in DemandeDeModificationDEvenement.model_fields:
        assert not any(s in nom.lower() for s in suspects)


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
            "VALUES (:email, :normalisee, 'Modif', 'L8T4', 'active') RETURNING id"
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
            bureau=bureau,
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
    bureau: str | None = None,
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
        code_de_bureau=bureau,
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


def _modifier(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    evenement: uuid.UUID,
    version: int,
    cercles: list[str] | None = None,
    bureaux: list[str] | None = None,
    titre: str = "Petit-dejeuner modifie",
) -> EvenementModifie:
    return modifier_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        roles=_roles(cx, acteur=acteur, entite=entite),
        evenement=evenement,
        title=titre,
        description=None,
        starts_at=PLUS_TARD_DEBUT,
        ends_at=PLUS_TARD_FIN,
        location_text=None,
        version_attendue=version,
        codes_de_cercle=cercles,
        codes_de_bureau=bureaux,
        instant=DEMAIN,
    )


def _publier(
    cx: Connection, *, entite: uuid.UUID, acteur: uuid.UUID, evenement: uuid.UUID, version: int
) -> EvenementModifie:
    return publier_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=version,
        instant=DEMAIN,
    )


# ----------------------------------------------------------------------------
#  2.1 La grille « Modifier »/« Publier » pour les roles de portee ENTITE
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_ESM_modifie_PUIS_publie_un_evenement_de_portee_ENTITE(cx: Connection) -> None:
    entite = _entite(cx, "ESM1")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)

    assert _perimetre(cx, entite=entite, acteur=esm, evenement=evenement) == frozenset(
        {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}
    )

    modifie = _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    assert modifie.title == "Petit-dejeuner modifie"
    assert modifie.version == 2

    publie = _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=2)
    assert publie.etat == "published"
    assert publie.version == 3


@pytest.mark.integration
def test_un_ESM_rattache_PLUSIEURS_cercles_ET_bureaux_a_un_evenement_ENTITE(
    cx: Connection,
) -> None:
    """La rattachement multiple decisif : DEUX cercles, UN bureau, en un seul geste."""
    entite = _entite(cx, "ESM2")
    esm = _acteur(cx, entite, "esm-multi", responsabilite=TypeResponsabilite.ESM.value)
    tech, data = _cercle(cx, entite, "TECH"), _cercle(cx, entite, "DATA")
    bdx = _bureau(cx, entite, "BDX")
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)

    _modifier(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=1,
        cercles=["TECH", "DATA"],
        bureaux=["BDX"],
    )

    cercles_poses = set(
        cx.execute(
            text(
                "SELECT circle_id FROM event_circle_scope "
                "WHERE event_id = :e AND archived_at IS NULL"
            ),
            {"e": evenement},
        ).scalars()
    )
    bureaux_poses = set(
        cx.execute(
            text(
                "SELECT office_id FROM event_office_scope "
                "WHERE event_id = :e AND archived_at IS NULL"
            ),
            {"e": evenement},
        ).scalars()
    )
    assert cercles_poses == {tech, data}
    assert bureaux_poses == {bdx}


@pytest.mark.integration
def test_remplacer_la_liste_des_cercles_ARCHIVE_l_ancienne_ET_pose_la_nouvelle(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ESM3")
    esm = _acteur(cx, entite, "esm-remp", responsabilite=TypeResponsabilite.ESM.value)
    tech = _cercle(cx, entite, "TECH")
    data = _cercle(cx, entite, "DATA")
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)

    _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=1, cercles=["TECH"])
    _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=2, cercles=["DATA"])

    actifs = set(
        cx.execute(
            text(
                "SELECT circle_id FROM event_circle_scope "
                "WHERE event_id = :e AND archived_at IS NULL"
            ),
            {"e": evenement},
        ).scalars()
    )
    tous = cx.execute(
        text("SELECT count(*) FROM event_circle_scope WHERE event_id = :e"), {"e": evenement}
    ).scalar_one()
    assert actifs == {data}
    assert tous == 2, "TECH doit etre ARCHIVE, pas supprime"
    assert tech not in actifs


@pytest.mark.integration
def test_une_liste_VIDE_VIDE_la_dimension(cx: Connection) -> None:
    entite = _entite(cx, "ESM4")
    esm = _acteur(cx, entite, "esm-vide", responsabilite=TypeResponsabilite.ESM.value)
    _cercle(cx, entite, "TECH")
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=1, cercles=["TECH"])
    _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=2, cercles=[])
    actifs = cx.execute(
        text("SELECT count(*) FROM event_circle_scope WHERE event_id = :e AND archived_at IS NULL"),
        {"e": evenement},
    ).scalar_one()
    assert actifs == 0


# ----------------------------------------------------------------------------
#  2.2 L'asymetrie du Booster et du responsable de bureau
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_BOOSTER_modifie_SON_evenement_mais_n_attache_PAS_le_cercle_d_un_AUTRE(
    cx: Connection,
) -> None:
    entite = _entite(cx, "BST1")
    mon_cercle = _cercle(cx, entite, "TECH")
    cercle_d_autrui = _cercle(cx, entite, "DATA")
    booster = _acteur(
        cx, entite, "booster", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=mon_cercle
    )
    evenement = _creer(
        cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH"
    )

    assert _perimetre(cx, entite=entite, acteur=booster, evenement=evenement) == frozenset(
        {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}
    )

    #  TEMOIN : il modifie sans toucher aux cercles — reussit.
    modifie = _modifier(cx, entite=entite, acteur=booster, evenement=evenement, version=1)
    assert modifie.version == 2

    #  REFUS : il tente d'y attacher AUSSI le cercle d'un autre Booster.
    with pytest.raises(ErreurApplicative) as echec:
        _modifier(
            cx,
            entite=entite,
            acteur=booster,
            evenement=evenement,
            version=2,
            cercles=["TECH", "DATA"],
        )
    assert echec.value.code == CODE_ACCES_REFUSE
    assert cercle_d_autrui is not None  # nomme, pour la lisibilite du refus


@pytest.mark.integration
def test_un_BOOSTER_d_un_AUTRE_cercle_n_a_AUCUN_droit_sur_l_evenement(cx: Connection) -> None:
    entite = _entite(cx, "BST2")
    cercle_de_l_evenement = _cercle(cx, entite, "TECH")
    mon_cercle = _cercle(cx, entite, "DATA")
    createur = _acteur(
        cx,
        entite,
        "booster-tech",
        responsabilite=TypeResponsabilite.BOOSTER.value,
        cercle=cercle_de_l_evenement,
    )
    autre_booster = _acteur(
        cx,
        entite,
        "booster-data",
        responsabilite=TypeResponsabilite.BOOSTER.value,
        cercle=mon_cercle,
    )
    evenement = _creer(
        cx, entite=entite, acteur=createur, portee=PorteeDeCreation.CERCLE, cercle="TECH"
    )
    assert _perimetre(cx, entite=entite, acteur=autre_booster, evenement=evenement) == frozenset()


@pytest.mark.integration
def test_un_responsable_de_BUREAU_modifie_SON_evenement_mais_PAS_celui_d_un_AUTRE(
    cx: Connection,
) -> None:
    entite = _entite(cx, "OFF1")
    mon_bureau = _bureau(cx, entite, "BDX")
    bureau_d_autrui = _bureau(cx, entite, "LIL")
    responsable = _acteur(
        cx,
        entite,
        "office",
        responsabilite=TypeResponsabilite.OFFICE_MANAGER.value,
        bureau=mon_bureau,
    )
    evenement = _creer(
        cx, entite=entite, acteur=responsable, portee=PorteeDeCreation.BUREAU, bureau="BDX"
    )
    modifie = _modifier(cx, entite=entite, acteur=responsable, evenement=evenement, version=1)
    assert modifie.version == 2
    with pytest.raises(ErreurApplicative) as echec:
        _modifier(
            cx,
            entite=entite,
            acteur=responsable,
            evenement=evenement,
            version=2,
            bureaux=["BDX", "LIL"],
        )
    assert echec.value.code == CODE_ACCES_REFUSE
    assert bureau_d_autrui is not None


# ----------------------------------------------------------------------------
#  2.3 Le DSM : deux grilles distinctes pour Modifier et Publier
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_DSM_MODIFIE_un_evenement_ENTITE_qu_il_a_CREE_mais_ne_le_PUBLIE_PAS(
    cx: Connection,
) -> None:
    """§3 : « Perimetre » pour le DSM denote SES CONSULTANTS, jamais l'entite.

    Un evenement de portee ENTITE cree par un DSM n'est pas « son perimetre » :
    il peut le MODIFIER (il l'a cree) mais ne peut PAS le PUBLIER.
    """
    entite = _entite(cx, "DSM1")
    dsm = _acteur(cx, entite, "dsm-ent", responsabilite=TypeResponsabilite.DSM.value)
    evenement = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.ENTITE)

    assert _perimetre(cx, entite=entite, acteur=dsm, evenement=evenement) == frozenset(
        {ActionEvenement.MODIFIER}
    )

    modifie = _modifier(cx, entite=entite, acteur=dsm, evenement=evenement, version=1)
    assert modifie.version == 2

    #  **LE REFUS DE PUBLIER NE VIT PAS DANS LE SERVICE, MAIS DANS LA GRILLE.**
    #  `publier_un_evenement` ne rejuge pas le perimetre — meme repartition que
    #  `publier_une_page` au LOT 6, ou le service suppose le droit deja prouve.
    #  C'est la route qui refuse, en lisant `ActionEvenement.PUBLIER not in
    #  perimetre.actions` : l'assertion ci-dessus, qui exclut PUBLIER de
    #  l'ensemble rendu, EST la preuve que ce refus aura lieu.


@pytest.mark.integration
def test_un_DSM_MODIFIE_ET_PUBLIE_un_evenement_de_portee_CONSULTANTS(cx: Connection) -> None:
    """Le MEME DSM, sur SA portee consultants : les deux droits s'ouvrent."""
    entite = _entite(cx, "DSM2")
    dsm = _acteur(cx, entite, "dsm-cons", responsabilite=TypeResponsabilite.DSM.value)
    evenement = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.CONSULTANTS)

    assert _perimetre(cx, entite=entite, acteur=dsm, evenement=evenement) == frozenset(
        {ActionEvenement.MODIFIER, ActionEvenement.PUBLIER}
    )

    _modifier(cx, entite=entite, acteur=dsm, evenement=evenement, version=1)
    publie = _publier(cx, entite=entite, acteur=dsm, evenement=evenement, version=2)
    assert publie.etat == "published"


@pytest.mark.integration
def test_un_DSM_SANS_LIEN_avec_l_evenement_n_a_AUCUN_droit(cx: Connection) -> None:
    entite = _entite(cx, "DSM3")
    createur = _acteur(cx, entite, "dsm-createur", responsabilite=TypeResponsabilite.DSM.value)
    autre_dsm = _acteur(cx, entite, "dsm-etranger", responsabilite=TypeResponsabilite.DSM.value)
    evenement = _creer(cx, entite=entite, acteur=createur, portee=PorteeDeCreation.CONSULTANTS)
    assert _perimetre(cx, entite=entite, acteur=autre_dsm, evenement=evenement) == frozenset()


# ----------------------------------------------------------------------------
#  2.4 Concurrence optimiste, chronologie, doublons, isolation
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_une_VERSION_obsolete_refuse_la_modification_SANS_rien_ecrire(cx: Connection) -> None:
    entite = _entite(cx, "VER1")
    esm = _acteur(cx, entite, "esm-ver", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    with pytest.raises(ErreurApplicative) as echec:
        _modifier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    assert echec.value.code == CODE_VERSION_OBSOLETE
    assert echec.value.statut == 409
    titre = cx.execute(text("SELECT title FROM event WHERE id = :e"), {"e": evenement}).scalar_one()
    assert titre == "Petit-dejeuner modifie"


@pytest.mark.integration
def test_PUBLIER_une_SECONDE_fois_est_refuse_SANS_republication(cx: Connection) -> None:
    entite = _entite(cx, "VER2")
    esm = _acteur(cx, entite, "esm-pub2", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    publie = _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=1)
    assert publie.etat == "published"
    with pytest.raises(ErreurApplicative) as echec:
        _publier(cx, entite=entite, acteur=esm, evenement=evenement, version=2)
    assert echec.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_un_cercle_EN_DOUBLE_dans_la_liste_est_refuse_en_422(cx: Connection) -> None:
    entite = _entite(cx, "DBL1")
    esm = _acteur(cx, entite, "esm-dbl", responsabilite=TypeResponsabilite.ESM.value)
    _cercle(cx, entite, "TECH")
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    with pytest.raises(ErreurApplicative) as echec:
        _modifier(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=1,
            cercles=["TECH", "TECH"],
        )
    assert echec.value.code == CODE_DOUBLON_DANS_LA_LISTE
    assert echec.value.statut == 422


@pytest.mark.integration
def test_un_cercle_valide_dans_une_AUTRE_entite_rend_ressource_introuvable(
    cx: Connection,
) -> None:
    ici, ailleurs = _entite(cx, "ISO1"), _entite(cx, "ISO2")
    _cercle(cx, ailleurs, "TECH")
    esm = _acteur(cx, ici, "esm-iso", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=ici, acteur=esm, portee=PorteeDeCreation.ENTITE)
    with pytest.raises(ErreurApplicative) as echec:
        _modifier(cx, entite=ici, acteur=esm, evenement=evenement, version=1, cercles=["TECH"])
    assert echec.value.code == CODE_RESSOURCE_INTROUVABLE


@pytest.mark.integration
def test_une_chronologie_invalide_est_refusee_en_422(cx: Connection) -> None:
    entite = _entite(cx, "CHR1")
    esm = _acteur(cx, entite, "esm-chrono", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    with pytest.raises(ErreurApplicative) as echec:
        modifier_un_evenement(
            cx,
            entite=entite,
            acteur=esm,
            roles=_roles(cx, acteur=esm, entite=entite),
            evenement=evenement,
            title="x",
            description=None,
            starts_at=FIN,
            ends_at=DEBUT,
            location_text=None,
            version_attendue=1,
            codes_de_cercle=None,
            codes_de_bureau=None,
            instant=DEMAIN,
        )
    assert echec.value.statut == 422


@pytest.mark.integration
def test_un_evenement_INEXISTANT_rend_un_perimetre_VIDE(cx: Connection) -> None:
    entite = _entite(cx, "ABS1")
    esm = _acteur(cx, entite, "esm-abs", responsabilite=TypeResponsabilite.ESM.value)
    assert _perimetre(cx, entite=entite, acteur=esm, evenement=uuid.uuid4()) == frozenset()


@pytest.mark.integration
def test_un_evenement_ARCHIVE_n_offre_PLUS_RIEN(cx: Connection) -> None:
    """Defensif : aucune route de `T4` n'archive, mais `resoudre_le_perimetre`

    ne doit jamais rouvrir un droit sur une ligne qui ne devrait plus en
    porter — meme §7.0, quatrieme proposition, que partout ailleurs.
    """
    entite = _entite(cx, "ARC1")
    esm = _acteur(cx, entite, "esm-arc", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    cx.execute(
        text("UPDATE event SET archived_at = :i, archived_by_person_id = :a WHERE id = :e"),
        {"i": DEMAIN, "a": esm, "e": evenement},
    )
    assert _perimetre(cx, entite=entite, acteur=esm, evenement=evenement) == frozenset()
