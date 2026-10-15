"""Le cablage de l'audit generique sur les personnes et l'organisation — LOT 10, `T3`.

Stories `MVP-L10-US001`/`US002`, modele §21.1, `ARB-DATA-005`/`§30.20`.

CE QUE CE FICHIER PROUVE, ET DANS QUEL ORDRE

  1. chacun des sites d'ecriture deja poses par les LOTS 2/5/9 — creer un
     collaborateur, modifier ses donnees organisationnelles, le transferer
     d'entite, archiver/restaurer son profil, archiver/restaurer un cercle ou
     un bureau, creer une entite, attribuer la categorie `dg` — ecrit AUSSI
     une ligne `audit_event`, dans la MEME transaction ;
  2. `action_code` REUTILISE le vocabulaire du domaine quand il existe deja
     (`ChampOrganisationnel`, `ActionDeCycleDeVie`) et n'en invente un second
     que pour les actions qu'aucune enumeration ne nomme encore (§7.27) ;
  3. `modifier_les_donnees_organisationnelles` ecrit UN `audit_event` PAR
     CHAMP REELLEMENT MODIFIE, jamais un seul pour l'appel entier — et
     n'en ecrit AUCUN pour un champ redonne sa valeur courante ;
  4. le correlation token courant est repris hors du contexte de
     l'authentification aussi ;
  5. l'atomicite n'est pas qu'une affirmation : un echec survenant APRES
     l'ecriture d'un `audit_event`, dans la MEME transaction, annule aussi
     cette ecriture.

CE QUE CE FICHIER NE REPROUVE PAS

  Les regles METIER de chaque site (permissions, concurrence optimiste,
  transitions d'etat) sont deja prouvees par leurs propres suites —
  `test_creation_collaborateurs.py`, `test_ecriture_organisationnelle.py`,
  `test_transfert_collaborateurs.py`, `test_archivage.py`,
  `test_cycle_de_vie_organisation.py`, `test_creation_entite.py`,
  `test_depots_et_services.py`. Ce fichier ne porte que ce que `T3` ajoute :
  la ligne `audit_event` elle-meme.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator, Sequence

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping

from app.audit.services import DUREE_DE_RETENTION
from app.configuration.settings import Parametres
from app.entities.creation import DemandeDeCreationDEntite, creer_une_entite
from app.organization.cycle_de_vie import (
    archiver_un_bureau,
    archiver_un_cercle,
    restaurer_un_bureau,
    restaurer_un_cercle,
)
from app.organization.services import attribuer_la_categorie_dg
from app.people.archivage import archiver_un_profil, restaurer_un_profil
from app.people.creation import DemandeDAppartenance, DemandeDeCollaborateur, creer_un_collaborateur
from app.people.ecriture import modifier_les_donnees_organisationnelles
from app.people.modeles import EtatAppartenance, SituationProfessionnelle
from app.people.transfert import changer_d_entite
from app.permissions.perimetre import (
    TOUS_LES_CHAMPS,
    ActionDeCycleDeVie,
    ChampOrganisationnel,
    PerimetreDEcriture,
    PerimetreDuCycleDeVie,
)
from app.shared.correlation import definir_correlation, effacer_correlation
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 10, 15, 9, 0, tzinfo=dt.UTC)
PLUS_TARD = INSTANT + dt.timedelta(days=1)
MARQUEUR = "T3L10"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion en ROLLBACK : aucun test ne laisse de ligne derriere lui."""
    _exiger_postgresql(parametres_de_la_stack)
    connexion = moteur(parametres_de_la_stack).connect()
    transaction = connexion.begin()
    try:
        yield connexion
    finally:
        transaction.rollback()
        connexion.close()


# ---------------------------------------------------------------------------
#  Le decor. Local a ce fichier, comme celui de `T2` : aucun test du depot
#  n'importe le decor d'un autre, et chaque decor est taille a sa question.
# ---------------------------------------------------------------------------


def _entite(connexion: Connection, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO entity (code, display_name, city, country_code, status, "
                    "timezone, activated_at) "
                    "VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
                    "RETURNING id"
                ),
                {"code": code, "nom": code, "ville": code},
            ).scalar_one()
        )
    )


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO person "
                    "(email, email_normalized, first_name, last_name, account_state) "
                    "VALUES (:affichage, :normalise, 'Test', 'T3L10', 'active') RETURNING id"
                ),
                {"affichage": adresse, "normalise": adresse.lower()},
            ).scalar_one()
        )
    )


def _appartenance(
    connexion: Connection,
    personne: uuid.UUID,
    entite: uuid.UUID,
    *,
    etat: str = EtatAppartenance.ACTIVE.value,
) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'draft') RETURNING id"
                ),
                {
                    "p": personne,
                    "e": entite,
                    "arrivee": (INSTANT - dt.timedelta(days=30)).date(),
                    "etat": etat,
                },
            ).scalar_one()
        )
    )


def _metier(connexion: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO job_catalog (entity_id, code, label) "
                    "VALUES (:e, :code, :libelle) RETURNING id"
                ),
                {"e": entite, "code": code, "libelle": code},
            ).scalar_one()
        )
    )


def _cercle(connexion: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO circle (entity_id, code, name, display_order) "
                    "VALUES (:e, :code, :nom, 1) RETURNING id"
                ),
                {"e": entite, "code": code, "nom": code},
            ).scalar_one()
        )
    )


def _bureau(connexion: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO office (entity_id, code, name, display_order) "
                    "VALUES (:e, :code, :nom, 1) RETURNING id"
                ),
                {"e": entite, "code": code, "nom": code},
            ).scalar_one()
        )
    )


def _affecter_le_metier(
    connexion: Connection, cible: uuid.UUID, metier: uuid.UUID, entite: uuid.UUID
) -> None:
    connexion.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_membership_id, entity_id, "
            "job_catalog_id, starts_at) VALUES (:c, :e, :m, :d)"
        ),
        {"c": cible, "e": entite, "m": metier, "d": INSTANT - dt.timedelta(days=30)},
    )


def _membre_de_cercle(
    connexion: Connection, cible: uuid.UUID, cercle: uuid.UUID, entite: uuid.UUID
) -> None:
    connexion.execute(
        text(
            "INSERT INTO circle_membership (entity_membership_id, entity_id, circle_id, "
            "membership_type, starts_at) VALUES (:c, :e, :cr, 'principal', :d)"
        ),
        {"c": cible, "e": entite, "cr": cercle, "d": INSTANT - dt.timedelta(days=30)},
    )


def _super_administrateur(connexion: Connection, adresse: str) -> uuid.UUID:
    """Une personne `SUPER_ADMIN`, GLOBALE — `entity_id` nul, §8.6."""
    personne = _personne(connexion, adresse)
    connexion.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, NULL, 'SUPER_ADMIN', :debut)"
        ),
        {"p": personne, "debut": INSTANT - dt.timedelta(days=30)},
    )
    return personne


def _audit_events(
    connexion: Connection, *, action_code: str, resource_reference: uuid.UUID | None = None
) -> Sequence[RowMapping]:
    requete = "SELECT * FROM audit_event WHERE action_code = :code"
    parametres: dict[str, object] = {"code": action_code}
    if resource_reference is not None:
        requete += " AND resource_reference = :reference"
        parametres["reference"] = resource_reference
    return connexion.execute(text(requete), parametres).mappings().all()


def _demande_appartenance(
    *,
    metier: uuid.UUID,
    cercle: uuid.UUID,
    arrivee: dt.date | None = None,
) -> DemandeDAppartenance:
    return DemandeDAppartenance(
        arrival_date=arrivee or (INSTANT - dt.timedelta(days=1)).date(),
        job_catalog_id=metier,
        status=SituationProfessionnelle.INTERCONTRACT,
        client_id=None,
        dsm_person_id=None,
        circle_id=cercle,
    )


# ===========================================================================
#  LA CREATION D'UN COLLABORATEUR — `app.people.creation`
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_un_collaborateur_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-CREA")
    acteur = _personne(cx, f"acteur-crea-{uuid.uuid4().hex[:8]}@exalt-company.com")
    metier = _metier(cx, entite, f"M-{uuid.uuid4().hex[:6]}")
    cercle = _cercle(cx, entite, f"C-{uuid.uuid4().hex[:6]}")

    cree = creer_un_collaborateur(
        cx,
        entite=entite,
        acteur=acteur,
        demande=DemandeDeCollaborateur(
            email=f"nouveau-{uuid.uuid4().hex[:8]}@exalt-company.com",
            first_name="Nouveau",
            last_name="Collaborateur",
            preferred_name=None,
            appartenance=_demande_appartenance(metier=metier, cercle=cercle),
        ),
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="collaborateur_cree")
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "person"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == INSTANT
    assert ligne["retention_until"] == INSTANT + DUREE_DE_RETENTION
    assert ligne["correlation_token"]
    #  `resource_reference` est la PERSONNE creee, jamais l'appartenance :
    #  l'appartenance a sa propre ligne possible, cf. le test suivant.
    personne = cx.execute(
        text("SELECT person_id FROM entity_membership WHERE id = :a"),
        {"a": cree.appartenance},
    ).scalar_one()
    assert ligne["resource_reference"] == personne


# ===========================================================================
#  LA MODIFICATION DES DONNEES ORGANISATIONNELLES — `app.people.ecriture`
# ===========================================================================


@pytest.mark.integration
def test_la_modification_de_PLUSIEURS_champs_ecrit_un_audit_event_PAR_champ(
    cx: Connection,
) -> None:
    """Un `audit_event` PAR CHAMP REELLEMENT ecrit, jamais un seul pour l'appel."""
    entite = _entite(cx, f"{MARQUEUR}-MODIF")
    acteur = _personne(cx, f"acteur-modif-{uuid.uuid4().hex[:8]}@exalt-company.com")
    cible = _appartenance(
        cx, _personne(cx, f"cible-modif-{uuid.uuid4().hex[:8]}@exalt-company.com"), entite
    )
    ancien_metier = _metier(cx, entite, f"M-ANCIEN-{uuid.uuid4().hex[:6]}")
    ancien_cercle = _cercle(cx, entite, f"C-ANCIEN-{uuid.uuid4().hex[:6]}")
    _affecter_le_metier(cx, cible, ancien_metier, entite)
    _membre_de_cercle(cx, cible, ancien_cercle, entite)
    nouveau_metier = _metier(cx, entite, f"M-NOUVEAU-{uuid.uuid4().hex[:6]}")
    nouveau_cercle = _cercle(cx, entite, f"C-NOUVEAU-{uuid.uuid4().hex[:6]}")

    modification = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={
            ChampOrganisationnel.METIER: nouveau_metier,
            ChampOrganisationnel.CERCLE_PRINCIPAL: nouveau_cercle,
        },
        perimetre=PerimetreDEcriture(champs=TOUS_LES_CHAMPS),
        instant=PLUS_TARD,
    )
    assert modification.champs == {
        ChampOrganisationnel.METIER,
        ChampOrganisationnel.CERCLE_PRINCIPAL,
    }

    lignes_metier = _audit_events(cx, action_code="metier", resource_reference=cible)
    assert len(lignes_metier) == 1
    assert lignes_metier[0]["entity_id"] == entite
    assert lignes_metier[0]["actor_person_id"] == acteur
    assert lignes_metier[0]["old_values"] == {"valeur": str(ancien_metier)}
    assert lignes_metier[0]["new_values"] == {"valeur": str(nouveau_metier)}

    lignes_cercle = _audit_events(cx, action_code="cercle_principal", resource_reference=cible)
    assert len(lignes_cercle) == 1
    assert lignes_cercle[0]["old_values"] == {"valeur": str(ancien_cercle)}
    assert lignes_cercle[0]["new_values"] == {"valeur": str(nouveau_cercle)}

    #  Les deux ecritures partagent le MEME instant metier — une seule ancre.
    assert lignes_metier[0]["occurred_at"] == PLUS_TARD
    assert lignes_cercle[0]["occurred_at"] == PLUS_TARD


@pytest.mark.integration
def test_un_champ_REDONNE_sa_valeur_courante_n_ecrit_AUCUN_audit_event(cx: Connection) -> None:
    """`Modification.champs` ne nomme que ce qui a REELLEMENT change — l'audit suit."""
    entite = _entite(cx, f"{MARQUEUR}-SANSCHANGEMENT")
    acteur = _personne(cx, f"acteur-sc-{uuid.uuid4().hex[:8]}@exalt-company.com")
    cible = _appartenance(
        cx, _personne(cx, f"cible-sc-{uuid.uuid4().hex[:8]}@exalt-company.com"), entite
    )
    metier = _metier(cx, entite, f"M-{uuid.uuid4().hex[:6]}")
    _affecter_le_metier(cx, cible, metier, entite)

    modification = modifier_les_donnees_organisationnelles(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        demande={ChampOrganisationnel.METIER: metier},  # la MEME valeur
        perimetre=PerimetreDEcriture(champs=TOUS_LES_CHAMPS),
        instant=PLUS_TARD,
    )
    assert modification.champs == frozenset()
    assert len(_audit_events(cx, action_code="metier", resource_reference=cible)) == 0


# ===========================================================================
#  LE CHANGEMENT D'ENTITE — `app.people.transfert`
# ===========================================================================


@pytest.mark.integration
def test_le_changement_d_entite_ecrit_un_audit_event_avec_les_DEUX_entites(
    cx: Connection,
) -> None:
    source = _entite(cx, f"{MARQUEUR}-TRANSF-SRC")
    destination = _entite(cx, f"{MARQUEUR}-TRANSF-DST")
    acteur = _personne(cx, f"acteur-transf-{uuid.uuid4().hex[:8]}@exalt-company.com")
    personne = _personne(cx, f"cible-transf-{uuid.uuid4().hex[:8]}@exalt-company.com")
    ancienne = _appartenance(cx, personne, source)
    metier_src = _metier(cx, source, f"M-{uuid.uuid4().hex[:6]}")
    cercle_src = _cercle(cx, source, f"C-{uuid.uuid4().hex[:6]}")
    _affecter_le_metier(cx, ancienne, metier_src, source)
    _membre_de_cercle(cx, ancienne, cercle_src, source)
    metier_dst = _metier(cx, destination, f"M-{uuid.uuid4().hex[:6]}")
    cercle_dst = _cercle(cx, destination, f"C-{uuid.uuid4().hex[:6]}")

    transfert = changer_d_entite(
        cx,
        entite_source=source,
        entite_destination=destination,
        cible=ancienne,
        acteur=acteur,
        version_attendue=1,
        #  `arrivee` NE PEUT PAS PRECEDER le depart de l'ancienne — l'une et
        #  l'autre sont la MEME personne, et `ex_entity_membership_sans_
        #  chevauchement` ne porte aucune clause `WHERE` (§25.2) : une arrivee
        #  posee avant l'instant du transfert chevaucherait la periode qui
        #  vient de se fermer CE MEME JOUR.
        demande=_demande_appartenance(metier=metier_dst, cercle=cercle_dst, arrivee=INSTANT.date()),
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="collaborateur_transfere")
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "entity_membership"
    assert ligne["resource_reference"] == transfert.nouvelle_appartenance
    assert ligne["entity_id"] == destination
    assert ligne["actor_person_id"] == acteur
    assert ligne["old_values"] == {"entite": str(source)}
    assert ligne["new_values"] == {"entite": str(destination)}


# ===========================================================================
#  L'ARCHIVAGE ET LA RESTAURATION D'UN PROFIL — `app.people.archivage`
# ===========================================================================


@pytest.mark.integration
def test_l_archivage_d_un_profil_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-ARCHPROFIL")
    acteur = _personne(cx, f"acteur-arch-{uuid.uuid4().hex[:8]}@exalt-company.com")
    cible = _appartenance(
        cx, _personne(cx, f"cible-arch-{uuid.uuid4().hex[:8]}@exalt-company.com"), entite
    )

    archiver_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        perimetre=PerimetreDuCycleDeVie(
            actions=frozenset({ActionDeCycleDeVie.ARCHIVER, ActionDeCycleDeVie.RESTAURER})
        ),
        instant=INSTANT,
    )

    lignes = _audit_events(
        cx, action_code=ActionDeCycleDeVie.ARCHIVER.value, resource_reference=cible
    )
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "entity_membership"
    assert lignes[0]["entity_id"] == entite
    assert lignes[0]["actor_person_id"] == acteur


@pytest.mark.integration
def test_la_restauration_d_un_profil_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-RESTPROFIL")
    acteur = _personne(cx, f"acteur-rest-{uuid.uuid4().hex[:8]}@exalt-company.com")
    cible = _appartenance(
        cx,
        _personne(cx, f"cible-rest-{uuid.uuid4().hex[:8]}@exalt-company.com"),
        entite,
        etat=EtatAppartenance.ARCHIVED.value,
    )
    perimetre = PerimetreDuCycleDeVie(
        actions=frozenset({ActionDeCycleDeVie.ARCHIVER, ActionDeCycleDeVie.RESTAURER})
    )

    restaurer_un_profil(
        cx,
        entite=entite,
        cible=cible,
        acteur=acteur,
        version_attendue=1,
        perimetre=perimetre,
        instant=INSTANT,
    )

    lignes = _audit_events(
        cx, action_code=ActionDeCycleDeVie.RESTAURER.value, resource_reference=cible
    )
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] == entite


# ===========================================================================
#  L'ARCHIVAGE ET LA RESTAURATION D'UN CERCLE OU D'UN BUREAU —
#  `app.organization.cycle_de_vie`
# ===========================================================================


@pytest.mark.integration
def test_l_archivage_et_la_restauration_d_un_cercle_ecrivent_des_audit_event(
    cx: Connection,
) -> None:
    entite = _entite(cx, f"{MARQUEUR}-CERCLE")
    acteur = _personne(cx, f"acteur-cercle-{uuid.uuid4().hex[:8]}@exalt-company.com")
    cercle = _cercle(cx, entite, f"C-{uuid.uuid4().hex[:6]}")

    archive = archiver_un_cercle(
        cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=1, instant=INSTANT
    )
    lignes_archive = _audit_events(cx, action_code="cercle_archive", resource_reference=cercle)
    assert len(lignes_archive) == 1
    assert lignes_archive[0]["resource_type"] == "circle"
    assert lignes_archive[0]["entity_id"] == entite

    restaurer_un_cercle(
        cx,
        entite=entite,
        cercle=cercle,
        acteur=acteur,
        version_attendue=archive.version,
        instant=PLUS_TARD,
    )
    lignes_restaure = _audit_events(cx, action_code="cercle_restaure", resource_reference=cercle)
    assert len(lignes_restaure) == 1
    assert lignes_restaure[0]["occurred_at"] == PLUS_TARD


@pytest.mark.integration
def test_l_archivage_et_la_restauration_d_un_bureau_ecrivent_des_audit_event(
    cx: Connection,
) -> None:
    entite = _entite(cx, f"{MARQUEUR}-BUREAU")
    acteur = _personne(cx, f"acteur-bureau-{uuid.uuid4().hex[:8]}@exalt-company.com")
    bureau = _bureau(cx, entite, f"B-{uuid.uuid4().hex[:6]}")

    archive = archiver_un_bureau(
        cx, entite=entite, bureau=bureau, acteur=acteur, version_attendue=1, instant=INSTANT
    )
    lignes_archive = _audit_events(cx, action_code="bureau_archive", resource_reference=bureau)
    assert len(lignes_archive) == 1
    assert lignes_archive[0]["resource_type"] == "office"

    restaurer_un_bureau(
        cx,
        entite=entite,
        bureau=bureau,
        acteur=acteur,
        version_attendue=archive.version,
        instant=PLUS_TARD,
    )
    assert len(_audit_events(cx, action_code="bureau_restaure", resource_reference=bureau)) == 1


# ===========================================================================
#  LA CREATION D'UNE ENTITE — `app.entities.creation`
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_une_entite_ecrit_un_audit_event(cx: Connection) -> None:
    acteur = _super_administrateur(cx, f"super-crea-{uuid.uuid4().hex[:8]}@exalt-company.com")
    administrateur = _personne(cx, f"admin-crea-{uuid.uuid4().hex[:8]}@exalt-company.com")
    code = f"{MARQUEUR}-{uuid.uuid4().hex[:8]}"

    cree = creer_une_entite(
        cx,
        demande=DemandeDeCreationDEntite(
            code=code,
            display_name=f"Entite {code}",
            city="Lyon",
            country_code="FR",
            timezone="Europe/Paris",
            premier_administrateur=administrateur,
        ),
        acteur=acteur,
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="entite_creee", resource_reference=cree.id)
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "entity"
    assert lignes[0]["entity_id"] == cree.id
    assert lignes[0]["actor_person_id"] == acteur


# ===========================================================================
#  L'ATTRIBUTION DE LA CATEGORIE `dg` — `app.organization.services`
# ===========================================================================


@pytest.mark.integration
def test_l_attribution_de_la_categorie_dg_ecrit_un_audit_event(cx: Connection) -> None:
    """Le motif figure dans `reason`, et l'instant NE DIVERGE PAS de `starts_at`.

    **Defaut trouve en cablant l'audit** : la fonction calculait
    `dt.datetime.now(tz=dt.UTC)` DEUX FOIS independamment quand `debut` est
    omis — une pour `starts_at` de la responsabilite DSM, une pour
    `occurred_at` de l'audit. Corrige en resolvant l'instant UNE SEULE fois
    (§7.0 sixieme proposition, §7.47).
    """
    entite = _entite(cx, f"{MARQUEUR}-DG")
    acteur = _super_administrateur(cx, f"super-dg-{uuid.uuid4().hex[:8]}@exalt-company.com")
    appartenance = _appartenance(
        cx, _personne(cx, f"dg-{uuid.uuid4().hex[:8]}@exalt-company.com"), entite
    )

    attribuer_la_categorie_dg(
        cx,
        entite=entite,
        appartenance=appartenance,
        attribue_par=acteur,
        motif="promotion en direction generale",
    )

    lignes = _audit_events(
        cx, action_code="categorie_dg_attribuee", resource_reference=appartenance
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["reason"] == "promotion en direction generale"
    assert "responsabilite DSM" in ligne["summary"]

    debut_de_la_responsabilite = cx.execute(
        text(
            "SELECT starts_at FROM framework_responsibility_assignment "
            "WHERE person_id = (SELECT person_id FROM entity_membership WHERE id = :a) "
            "  AND entity_id = :e AND responsibility_type = 'DSM'"
        ),
        {"a": appartenance, "e": entite},
    ).scalar_one()
    assert ligne["occurred_at"] == debut_de_la_responsabilite


@pytest.mark.integration
def test_l_attribution_de_la_categorie_dg_SANS_nouvelle_responsabilite_le_dit(
    cx: Connection,
) -> None:
    """Quand la responsabilite DSM existait DEJA, le resume ne pretend pas la creer."""
    entite = _entite(cx, f"{MARQUEUR}-DGEXISTE")
    acteur = _super_administrateur(cx, f"super-dgex-{uuid.uuid4().hex[:8]}@exalt-company.com")
    personne = _personne(cx, f"dgex-{uuid.uuid4().hex[:8]}@exalt-company.com")
    appartenance = _appartenance(cx, personne, entite)
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :debut)"
        ),
        {"p": personne, "e": entite, "debut": INSTANT - dt.timedelta(days=60)},
    )

    attribuer_la_categorie_dg(cx, entite=entite, appartenance=appartenance, attribue_par=acteur)

    lignes = _audit_events(
        cx, action_code="categorie_dg_attribuee", resource_reference=appartenance
    )
    assert len(lignes) == 1
    assert "responsabilite DSM" not in lignes[0]["summary"]


# ===========================================================================
#  CORRELATION — REPRISE HORS DU CONTEXTE DE L'AUTHENTIFICATION AUSSI
# ===========================================================================


@pytest.mark.integration
def test_le_correlation_token_courant_est_REPRIS_hors_authentification(cx: Connection) -> None:
    identifiant = definir_correlation("une-correlation-de-test-t3")
    try:
        entite = _entite(cx, f"{MARQUEUR}-CORR")
        acteur = _personne(cx, f"acteur-corr-{uuid.uuid4().hex[:8]}@exalt-company.com")
        cercle = _cercle(cx, entite, f"C-{uuid.uuid4().hex[:6]}")
        archiver_un_cercle(
            cx, entite=entite, cercle=cercle, acteur=acteur, version_attendue=1, instant=INSTANT
        )
        lignes = _audit_events(cx, action_code="cercle_archive", resource_reference=cercle)
        assert lignes[0]["correlation_token"] == identifiant
    finally:
        effacer_correlation()


# ===========================================================================
#  ATOMICITE — ARB-DATA-005/§30.20 : un echec APRES l'ecriture annule TOUT
# ===========================================================================


@pytest.mark.integration
def test_un_echec_APRES_l_ecriture_annule_AUSSI_l_audit_event(
    parametres_de_la_stack: Parametres,
) -> None:
    _exiger_postgresql(parametres_de_la_stack)
    code = f"{MARQUEUR}-ATOMIQUE-{uuid.uuid4().hex[:8]}"
    with moteur(parametres_de_la_stack).begin() as decor:
        entite = _entite(decor, code)
        acteur = _personne(decor, f"atomique-{uuid.uuid4().hex[:8]}@exalt-company.com")
        cercle = _cercle(decor, entite, f"C-{uuid.uuid4().hex[:6]}")
    try:
        with (
            pytest.raises(RuntimeError, match="echec force apres l'audit"),
            moteur(parametres_de_la_stack).begin() as transaction,
        ):
            archiver_un_cercle(
                transaction,
                entite=entite,
                cercle=cercle,
                acteur=acteur,
                version_attendue=1,
                instant=INSTANT,
            )
            #  A cet instant, `circle.archived_at` ET `audit_event` portent deja
            #  la trace — mais la transaction N'A PAS ENCORE COMMIT.
            raise RuntimeError("echec force apres l'audit, pour prouver l'atomicite")
        with moteur(parametres_de_la_stack).connect() as verification:
            n_audit = verification.execute(
                text("SELECT count(*) FROM audit_event WHERE resource_reference = :c"),
                {"c": cercle},
            ).scalar_one()
            archive_le = verification.execute(
                text("SELECT archived_at FROM circle WHERE id = :c"), {"c": cercle}
            ).scalar_one()
            assert n_audit == 0, (
                "l'audit_event a SURVECU a l'echec : la transaction n'est pas atomique"
            )
            assert archive_le is None, "le cercle a ete archive malgre l'echec force"
    finally:
        with moteur(parametres_de_la_stack).begin() as menage:
            menage.execute(
                text(
                    "DELETE FROM audit_event WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :code)"
                ),
                {"code": code},
            )
            menage.execute(
                text(
                    "DELETE FROM circle WHERE entity_id IN "
                    "(SELECT id FROM entity WHERE code = :code)"
                ),
                {"code": code},
            )
            menage.execute(
                text(
                    "DELETE FROM audit_event WHERE actor_person_id IN "
                    "(SELECT id FROM person WHERE email_normalized LIKE :motif)"
                ),
                {"motif": "atomique-%"},
            )
            menage.execute(
                text("DELETE FROM person WHERE email_normalized LIKE :motif"),
                {"motif": "atomique-%"},
            )
            menage.execute(text("DELETE FROM entity WHERE code = :code"), {"code": code})
