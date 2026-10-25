"""Rattacher des medias a un evenement — LOT 8, `T6`, matrice §11.

UNE GRILLE DE PLUS, ET ELLE REJOINT LA FORME « PERIMETRE » DU DSM

  « Ajouter une image ou vidéo » porte, pour le DSM, EXACTEMENT la meme
  cellule que « Publier »/« Annuler »/« Archiver » — « Perimetre », jamais
  « cree OU rattache ». Un DSM createur seul modifie un evenement de portee
  Entite qu'il a cree, mais ne peut pas y rattacher de media par cette seule
  voie — meme asymetrie que `T5`, mesuree une sixieme fois.

LA LISTE REMPLACE LA LISTE, ET L'ORDRE EST L'INDEX DU TABLEAU

  Meme motif que les cercles/bureaux de `T4` et les blocs de contenu du
  LOT 6 : les lignes retirees sont ARCHIVEES, jamais supprimees, et
  `display_order` vaut l'INDEX du tableau soumis — jamais un decalage
  calcule sur le nombre de lignes vivantes, piege deja mesure au LOT 6
  (`T8-1`, non deterministe). Archiver TOUTES les lignes avant de reinserer
  rend les rangs `0..n-1` contigus par construction.

SEUL UN MEDIA `ready` EST RATTACHABLE

  Reutilisation de `ETAT_AFFICHABLE` (`app/media/photo.py`, LOT 5) : la
  definition DEJA DECIDEE de ce qu'est un media affichable, pas une regle
  inventee pour cette seule sous-etape.
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
    CODE_DOUBLON_DANS_LA_LISTE,
    CODE_MEDIA_NON_PRET,
    CODE_RESSOURCE_INTROUVABLE,
    CODE_VERSION_OBSOLETE,
    EvenementMediasRemplaces,
    creer_un_evenement,
    gerer_les_medias_d_un_evenement,
)
from app.events.perimetre import (
    ActionEvenement,
    PorteeDeCreation,
    resoudre_le_perimetre_de_l_evenement,
)
from app.events.routes import DemandeDeGestionDesMediasDEvenement, MediaSoumis
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L8T6"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
DEBUT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 10, 10, 10, 0, tzinfo=dt.UTC)

# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================


def test_la_demande_porte_EXACTEMENT_version_et_medias() -> None:
    #  LOT 10, `T7` : plus `motif`, le motif conditionnel du §18.1 (`ECART-064`).
    assert set(DemandeDeGestionDesMediasDEvenement.model_fields) == {
        "version",
        "medias",
        "motif",
    }


def test_un_media_soumis_porte_EXACTEMENT_media_et_role() -> None:
    assert set(MediaSoumis.model_fields) == {"media", "role"}


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
            "VALUES (:email, :normalisee, 'Media', 'L8T6', 'active') RETURNING id"
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
    debut: dt.datetime = JANVIER,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, "
            " assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :type, :cercle, :par, :debut)"
        ),
        {
            "p": personne,
            "e": entite,
            "type": type_de_responsabilite,
            "cercle": cercle,
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


def _media(cx: Connection, entite: uuid.UUID, suffixe: str, *, state: str = "ready") -> uuid.UUID:
    personne = _personne(cx, f"up-{suffixe}")
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256) "
            "VALUES (:entite, :personne, :state, 'image', 'event.jpg', :cle, "
            "'image/jpeg', 1024, :empreinte) RETURNING id"
        ),
        {
            "entite": entite,
            "personne": personne,
            "state": state,
            "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            "empreinte": uuid.uuid4().hex * 2,
        },
    ).scalar_one()


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


def _gerer(
    cx: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    evenement: uuid.UUID,
    version: int,
    medias: list[tuple[uuid.UUID, str]],
) -> EvenementMediasRemplaces:
    return gerer_les_medias_d_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        evenement=evenement,
        version_attendue=version,
        medias=medias,
        instant=DEMAIN,
    )


def _lignes_vivantes(cx: Connection, evenement: uuid.UUID) -> list[tuple[uuid.UUID, int, str]]:
    return [
        (ligne[0], ligne[1], ligne[2])
        for ligne in cx.execute(
            text(
                "SELECT media_asset_id, display_order, display_role FROM event_media "
                "WHERE event_id = :e AND archived_at IS NULL ORDER BY display_order"
            ),
            {"e": evenement},
        ).all()
    ]


# ----------------------------------------------------------------------------
#  2.1 La grille « Perimetre » du DSM, asymetrie avec « Modifier »
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_DSM_NOMME_gere_les_medias_mais_un_DSM_CREATEUR_SEUL_ne_le_peut_pas(
    cx: Connection,
) -> None:
    entite = _entite(cx, "DSM1")
    dsm = _acteur(cx, entite, "dsm", responsabilite=TypeResponsabilite.DSM.value)
    media = _media(cx, entite, "m1")

    evenement_nomme = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.CONSULTANTS)
    assert ActionEvenement.GERER_LES_MEDIAS in _perimetre(
        cx, entite=entite, acteur=dsm, evenement=evenement_nomme
    )
    resultat = _gerer(
        cx,
        entite=entite,
        acteur=dsm,
        evenement=evenement_nomme,
        version=1,
        medias=[(media, "couverture")],
    )
    assert [(m.media_asset_id, m.role, m.ordre) for m in resultat.medias] == [
        (media, "couverture", 0)
    ]

    evenement_entite = _creer(cx, entite=entite, acteur=dsm, portee=PorteeDeCreation.ENTITE)
    perimetre_createur = _perimetre(cx, entite=entite, acteur=dsm, evenement=evenement_entite)
    assert ActionEvenement.MODIFIER in perimetre_createur
    assert ActionEvenement.GERER_LES_MEDIAS not in perimetre_createur


@pytest.mark.integration
def test_un_BOOSTER_gere_les_medias_de_SON_evenement(cx: Connection) -> None:
    entite = _entite(cx, "BST1")
    cercle = _cercle(cx, entite, "TECH")
    booster = _acteur(
        cx, entite, "booster", responsabilite=TypeResponsabilite.BOOSTER.value, cercle=cercle
    )
    media = _media(cx, entite, "m1")
    evenement = _creer(
        cx, entite=entite, acteur=booster, portee=PorteeDeCreation.CERCLE, cercle="TECH"
    )
    resultat = _gerer(
        cx,
        entite=entite,
        acteur=booster,
        evenement=evenement,
        version=1,
        medias=[(media, "galerie")],
    )
    assert resultat.version == 2


# ----------------------------------------------------------------------------
#  2.2 La liste remplace la liste, et l'ordre est l'INDEX du tableau
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_plusieurs_medias_sont_rattaches_DANS_L_ORDRE_fourni(cx: Connection) -> None:
    entite = _entite(cx, "ORD1")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    m1, m2, m3 = (_media(cx, entite, f"m{i}") for i in (1, 2, 3))

    resultat = _gerer(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=1,
        medias=[(m1, "couverture"), (m2, "galerie"), (m3, "galerie")],
    )
    assert [(m.media_asset_id, m.ordre, m.role) for m in resultat.medias] == [
        (m1, 0, "couverture"),
        (m2, 1, "galerie"),
        (m3, 2, "galerie"),
    ]
    assert _lignes_vivantes(cx, evenement) == [
        (m1, 0, "couverture"),
        (m2, 1, "galerie"),
        (m3, 2, "galerie"),
    ]


@pytest.mark.integration
def test_remplacer_la_liste_ARCHIVE_les_anciennes_lignes_jamais_ne_les_supprime(
    cx: Connection,
) -> None:
    entite = _entite(cx, "ORD2")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    ancien, nouveau = (_media(cx, entite, s) for s in ("ancien", "nouveau"))

    _gerer(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=1,
        medias=[(ancien, "couverture")],
    )
    _gerer(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=2,
        medias=[(nouveau, "couverture")],
    )

    assert _lignes_vivantes(cx, evenement) == [(nouveau, 0, "couverture")]
    #  L'ancienne ligne existe TOUJOURS, archivee — jamais supprimee.
    total = cx.execute(
        text("SELECT count(*) FROM event_media WHERE event_id = :e"), {"e": evenement}
    ).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_une_liste_VIDE_retire_tous_les_medias(cx: Connection) -> None:
    entite = _entite(cx, "ORD3")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    media = _media(cx, entite, "m1")

    _gerer(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=1,
        medias=[(media, "couverture")],
    )
    resultat = _gerer(cx, entite=entite, acteur=esm, evenement=evenement, version=2, medias=[])
    assert resultat.medias == []
    assert _lignes_vivantes(cx, evenement) == []


@pytest.mark.integration
def test_l_ordre_est_l_INDEX_du_tableau_JAMAIS_un_decalage_calcule(cx: Connection) -> None:
    """Le piege `T8-1` du LOT 6 : retirer le PREMIER media ne doit PAS laisser

    de trou. Les deux medias restants reçoivent les rangs `0` et `1`,
    contigus, jamais `1` et `2` (leur ancien rang moins un calcule a tort).
    """
    entite = _entite(cx, "ORD4")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    m1, m2, m3 = (_media(cx, entite, f"m{i}") for i in (1, 2, 3))

    _gerer(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=1,
        medias=[(m1, "a"), (m2, "b"), (m3, "c")],
    )
    #  Retire m1, garde m2 et m3 — dans cet ORDRE.
    _gerer(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version=2,
        medias=[(m2, "b"), (m3, "c")],
    )
    assert _lignes_vivantes(cx, evenement) == [(m2, 0, "b"), (m3, 1, "c")]


# ----------------------------------------------------------------------------
#  2.3 Les refus : media introuvable, hors entite, non pret, doublon
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_media_INEXISTANT_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "REF1")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    with pytest.raises(ErreurApplicative) as excinfo:
        _gerer(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=1,
            medias=[(uuid.uuid4(), "couverture")],
        )
    assert excinfo.value.code == CODE_RESSOURCE_INTROUVABLE


@pytest.mark.integration
def test_un_media_d_une_AUTRE_entite_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "REF2")
    autre_entite = _entite(cx, "REF2-AUTRE")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    media_etranger = _media(cx, autre_entite, "m1")
    with pytest.raises(ErreurApplicative) as excinfo:
        _gerer(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=1,
            medias=[(media_etranger, "couverture")],
        )
    assert excinfo.value.code == CODE_RESSOURCE_INTROUVABLE


@pytest.mark.integration
def test_un_media_ARCHIVE_au_sens_du_champ_generique_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "REF3")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    media = _media(cx, entite, "m1")
    cx.execute(
        text("UPDATE media_asset SET archived_at = :i WHERE id = :m"),
        {"i": DEMAIN, "m": media},
    )
    with pytest.raises(ErreurApplicative) as excinfo:
        _gerer(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=1,
            medias=[(media, "couverture")],
        )
    assert excinfo.value.code == CODE_RESSOURCE_INTROUVABLE


@pytest.mark.integration
def test_un_media_NON_PRET_est_refuse(cx: Connection) -> None:
    """TEMOIN §7.42 : un couple ready/non-ready, pas seulement le cas heureux."""
    entite = _entite(cx, "REF4")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    pret = _media(cx, entite, "pret", state="ready")
    en_cours = _media(cx, entite, "pending", state="pending")

    #  TEMOIN POSITIF : le media `ready` seul est accepte.
    resultat = _gerer(
        cx, entite=entite, acteur=esm, evenement=evenement, version=1, medias=[(pret, "a")]
    )
    assert resultat.version == 2

    with pytest.raises(ErreurApplicative) as excinfo:
        _gerer(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=2,
            medias=[(en_cours, "a")],
        )
    assert excinfo.value.code == CODE_MEDIA_NON_PRET


@pytest.mark.integration
def test_un_doublon_de_media_dans_la_meme_liste_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "REF5")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    media = _media(cx, entite, "m1")
    with pytest.raises(ErreurApplicative) as excinfo:
        _gerer(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=1,
            medias=[(media, "a"), (media, "b")],
        )
    assert excinfo.value.code == CODE_DOUBLON_DANS_LA_LISTE


@pytest.mark.integration
def test_gerer_les_medias_avec_une_version_obsolete_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "REF6")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    media = _media(cx, entite, "m1")
    with pytest.raises(ErreurApplicative) as excinfo:
        _gerer(
            cx,
            entite=entite,
            acteur=esm,
            evenement=evenement,
            version=99,
            medias=[(media, "a")],
        )
    assert excinfo.value.code == CODE_VERSION_OBSOLETE


@pytest.mark.integration
def test_un_evenement_ARCHIVE_n_offre_PAS_GERER_LES_MEDIAS(cx: Connection) -> None:
    entite = _entite(cx, "REF7")
    esm = _acteur(cx, entite, "esm", responsabilite=TypeResponsabilite.ESM.value)
    evenement = _creer(cx, entite=entite, acteur=esm, portee=PorteeDeCreation.ENTITE)
    cx.execute(
        text("UPDATE event SET archived_at = :i, archived_by_person_id = :a WHERE id = :e"),
        {"i": DEMAIN, "a": esm, "e": evenement},
    )
    assert ActionEvenement.GERER_LES_MEDIAS not in _perimetre(
        cx, entite=entite, acteur=esm, evenement=evenement
    )
