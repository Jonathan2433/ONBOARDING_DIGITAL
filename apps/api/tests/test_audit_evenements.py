"""Le cablage de l'audit generique sur les evenements — LOT 10, `T5`.

Stories `MVP-L10-US001`/`US002`, modele §21.1, `ARB-DATA-005`/`§30.20`.

CE QUE CE FICHIER PROUVE, ET DANS QUEL ORDRE

  1. chacune des sept fonctions d'ecriture deja posees par le LOT 8 — creer un
     evenement, le modifier, le publier, l'annuler, l'archiver, le restaurer,
     remplacer la liste de ses medias — ecrit AUSSI une ligne `audit_event`,
     dans la MEME transaction ;
  2. `action_code` REUTILISE `ActionEvenement` (§7.27) pour six des sept
     actions — celles que le §11 nomme comme lignes de permission — et
     n'invente un litteral (`"creer"`) que pour la creation, qu'aucune valeur
     de cette enumeration ne nomme (elle est scopee aux SIX lignes du §11, et
     « Creer » s'y regle par `PorteeDeCreation`, une structure distincte) ;
  3. `modifier_un_evenement` ecrit UN SEUL `audit_event` pour l'appel entier,
     meme quand il remplace AUSSI les listes de cercles/bureaux — meme
     principe que `remplacer_le_contenu` (`T4`) : un seul geste metier, un
     seul evenement, quel que soit le nombre d'ecritures SQL ;
  4. `gerer_les_medias_d_un_evenement` ecrit UN SEUL `audit_event` pour tout
     le remplacement de la liste, jamais un par media — ET, A LA DIFFERENCE DE
     `reordonner_les_liens` (`T4`), il en ecrit un MEME quand la liste soumise
     est VIDE : vider la galerie est une forme normale de ce geste, pas un
     retour anticipe avant toute ecriture ;
  5. le correlation token courant est repris ici aussi ;
  6. l'atomicite n'est pas qu'une affirmation : un echec survenant APRES
     l'ecriture d'un `audit_event`, dans la MEME transaction, annule aussi
     cette ecriture.

CE QUE CE FICHIER NE REPROUVE PAS

  Les regles METIER de chaque site (portees de creation, cercles/bureaux
  revalides un par un, concurrence optimiste, etats autorisant chaque
  transition) sont deja prouvees par leurs propres suites —
  `test_creation_evenements.py`, `test_modification_et_publication_evenements.py`,
  `test_annulation_archivage_et_restauration_evenements.py`,
  `test_medias_evenements.py`. Ce fichier ne porte que ce que `T5` ajoute : la
  ligne `audit_event` elle-meme — et c'est pourquoi chaque fonction est
  appelee avec `roles`/les codes minimaux qui la font simplement REUSSIR,
  jamais pour reprouver qui a le droit de l'appeler.
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
from app.events.ecriture import (
    annuler_un_evenement,
    archiver_un_evenement,
    creer_un_evenement,
    gerer_les_medias_d_un_evenement,
    modifier_un_evenement,
    publier_un_evenement,
    restaurer_un_evenement,
)
from app.events.perimetre import ActionEvenement, PorteeDeCreation
from app.permissions.services import RoleDeLaMatrice
from app.shared.correlation import definir_correlation, effacer_correlation
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 10, 18, 9, 0, tzinfo=dt.UTC)
PLUS_TARD = INSTANT + dt.timedelta(days=1)
DEBUT = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 11, 1, 10, 0, tzinfo=dt.UTC)
MARQUEUR = "T5L10"

#  `creer_un_evenement` recoit `roles` DIRECTEMENT, sans les relire en base —
#  `SUPER` porte la portee `ENTITE` dans la grille du §11, et c'est la seule
#  chose que ce fichier a besoin de faire REUSSIR.
_ROLES_SUPER: frozenset[RoleDeLaMatrice] = frozenset({RoleDeLaMatrice.SUPER_ADMINISTRATEUR})


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
#  Le decor. Local a ce fichier, comme ceux de `T2`, `T3` et `T4` : aucun test
#  du depot n'importe le decor d'un autre.
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
                    "VALUES (:affichage, :normalise, 'Test', 'T5L10', 'active') RETURNING id"
                ),
                {"affichage": adresse, "normalise": adresse.lower()},
            ).scalar_one()
        )
    )


def _cercle(connexion: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO circle (entity_id, code, name, display_order) "
                    "VALUES (:entite, :code, :nom, 1) RETURNING id"
                ),
                {"entite": entite, "code": code, "nom": code},
            ).scalar_one()
        )
    )


def _media(connexion: Connection, entite: uuid.UUID, acteur: uuid.UUID) -> uuid.UUID:
    return uuid.UUID(
        str(
            connexion.execute(
                text(
                    "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, "
                    "media_type, original_filename, object_key, mime_declared, size_bytes, "
                    "checksum_sha256) "
                    "VALUES (:entite, :acteur, 'ready', 'image', 'evenement.jpg', :cle, "
                    "'image/jpeg', 1024, :empreinte) RETURNING id"
                ),
                {
                    "entite": entite,
                    "acteur": acteur,
                    "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
                    "empreinte": uuid.uuid4().hex * 2,
                },
            ).scalar_one()
        )
    )


def _evenement(
    connexion: Connection, entite: uuid.UUID, acteur: uuid.UUID, *, titre: str
) -> uuid.UUID:
    return creer_un_evenement(
        connexion,
        entite=entite,
        acteur=acteur,
        roles=_ROLES_SUPER,
        title=titre,
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=INSTANT,
    ).identifiant


def _audit_events(
    connexion: Connection, *, action_code: str, resource_reference: uuid.UUID | None = None
) -> Sequence[RowMapping]:
    requete = "SELECT * FROM audit_event WHERE action_code = :code"
    parametres: dict[str, object] = {"code": action_code}
    if resource_reference is not None:
        requete += " AND resource_reference = :reference"
        parametres["reference"] = resource_reference
    return connexion.execute(text(requete), parametres).mappings().all()


# ===========================================================================
#  LA CREATION D'UN EVENEMENT
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_un_evenement_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-CREA")
    acteur = _personne(cx, f"acteur-crea-{uuid.uuid4().hex[:8]}@exalt-company.com")

    cree = creer_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        roles=_ROLES_SUPER,
        title="Petit-dejeuner d'equipe",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="creer", resource_reference=cree.identifiant)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "event"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == INSTANT
    assert ligne["retention_until"] == INSTANT + DUREE_DE_RETENTION
    assert ligne["correlation_token"]


# ===========================================================================
#  LA MODIFICATION D'UN EVENEMENT
# ===========================================================================


@pytest.mark.integration
def test_la_modification_d_un_evenement_ecrit_un_SEUL_audit_event(cx: Connection) -> None:
    """UN evenement d'audit pour l'appel entier, meme quand les cercles changent aussi.

    `modifier_un_evenement` ecrit les champs ET remplace la liste des cercles
    rattaches dans le MEME appel — plusieurs ecritures SQL, un seul geste
    metier, un seul `audit_event`, meme principe que `remplacer_le_contenu`
    (`T4`).
    """
    entite = _entite(cx, f"{MARQUEUR}-MODIF")
    acteur = _personne(cx, f"acteur-modif-{uuid.uuid4().hex[:8]}@exalt-company.com")
    _cercle(cx, entite, f"{MARQUEUR}-CERCLE")
    evenement = _evenement(cx, entite, acteur, titre="Ancien titre")

    modifier_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        roles=_ROLES_SUPER,
        evenement=evenement,
        title="Nouveau titre",
        description="Une description",
        starts_at=DEBUT,
        ends_at=FIN,
        location_text="Salle A",
        version_attendue=1,
        codes_de_cercle=[f"{MARQUEUR}-CERCLE"],
        codes_de_bureau=None,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.MODIFIER.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "event"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == PLUS_TARD
    assert ligne["new_values"]["title"] == "Nouveau titre"
    assert ligne["new_values"]["location_text"] == "Salle A"


# ===========================================================================
#  LE CYCLE DE VIE D'UN EVENEMENT
# ===========================================================================


@pytest.mark.integration
def test_la_publication_d_un_evenement_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-PUB")
    acteur = _personne(cx, f"acteur-pub-{uuid.uuid4().hex[:8]}@exalt-company.com")
    evenement = _evenement(cx, entite, acteur, titre="A publier")

    publier_un_evenement(
        cx, entite=entite, evenement=evenement, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.PUBLIER.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "event"
    assert lignes[0]["entity_id"] == entite


@pytest.mark.integration
def test_l_annulation_d_un_evenement_ecrit_un_audit_event_avec_son_motif(cx: Connection) -> None:
    """`motif` est le seul champ de ce module qui soit un vrai motif humain.

    Il est porte dans `reason`, jamais dans `summary` — meme discipline que
    `raison` pour la revocation de session (LOT 3) ou `motif` pour la
    categorie DG (LOT 2, `T3`).
    """
    entite = _entite(cx, f"{MARQUEUR}-ANNUL")
    acteur = _personne(cx, f"acteur-annul-{uuid.uuid4().hex[:8]}@exalt-company.com")
    evenement = _evenement(cx, entite, acteur, titre="A annuler")
    publier_un_evenement(
        cx, entite=entite, evenement=evenement, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    annuler_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=2,
        motif="Intervenant indisponible",
        instant=PLUS_TARD,
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.ANNULER.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    assert lignes[0]["reason"] == "Intervenant indisponible"


@pytest.mark.integration
def test_l_archivage_d_un_evenement_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-ARCH")
    acteur = _personne(cx, f"acteur-arch-{uuid.uuid4().hex[:8]}@exalt-company.com")
    evenement = _evenement(cx, entite, acteur, titre="A archiver")

    archiver_un_evenement(
        cx, entite=entite, evenement=evenement, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.ARCHIVER.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] == entite


@pytest.mark.integration
def test_la_restauration_d_un_evenement_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-REST")
    acteur = _personne(cx, f"acteur-rest-{uuid.uuid4().hex[:8]}@exalt-company.com")
    evenement = _evenement(cx, entite, acteur, titre="A restaurer")
    archivee = archiver_un_evenement(
        cx, entite=entite, evenement=evenement, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    restaurer_un_evenement(
        cx,
        entite=entite,
        evenement=evenement,
        acteur=acteur,
        version_attendue=archivee.version,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.RESTAURER.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    assert lignes[0]["occurred_at"] == PLUS_TARD


# ===========================================================================
#  LES MEDIAS D'UN EVENEMENT
# ===========================================================================


@pytest.mark.integration
def test_le_remplacement_des_medias_ecrit_un_SEUL_audit_event(cx: Connection) -> None:
    """UN evenement pour tout le remplacement de la liste, jamais un par media."""
    entite = _entite(cx, f"{MARQUEUR}-MEDIAS")
    acteur = _personne(cx, f"acteur-medias-{uuid.uuid4().hex[:8]}@exalt-company.com")
    evenement = _evenement(cx, entite, acteur, titre="Avec medias")
    premier = _media(cx, entite, acteur)
    second = _media(cx, entite, acteur)

    gerer_les_medias_d_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        evenement=evenement,
        version_attendue=1,
        medias=[(premier, "cover"), (second, "gallery")],
        instant=PLUS_TARD,
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.GERER_LES_MEDIAS.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["new_values"]["medias"] == [
        {"media_asset_id": str(premier), "role": "cover"},
        {"media_asset_id": str(second), "role": "gallery"},
    ]


@pytest.mark.integration
def test_le_remplacement_des_medias_a_vide_ecrit_QUAND_MEME_un_audit_event(
    cx: Connection,
) -> None:
    """A LA DIFFERENCE de `reordonner_les_liens` (`T4`) : pas de retour anticipe.

    Une liste vide VIDE la galerie — c'est une forme normale de ce geste, pas
    un cas qui court-circuite la fonction avant toute ecriture.
    """
    entite = _entite(cx, f"{MARQUEUR}-MEDIASVIDE")
    acteur = _personne(cx, f"acteur-mediasvide-{uuid.uuid4().hex[:8]}@exalt-company.com")
    evenement = _evenement(cx, entite, acteur, titre="Sans medias")

    gerer_les_medias_d_un_evenement(
        cx,
        entite=entite,
        acteur=acteur,
        evenement=evenement,
        version_attendue=1,
        medias=[],
        instant=INSTANT,
    )

    lignes = _audit_events(
        cx, action_code=ActionEvenement.GERER_LES_MEDIAS.value, resource_reference=evenement
    )
    assert len(lignes) == 1
    assert lignes[0]["new_values"] == {"medias": []}


# ===========================================================================
#  CORRELATION — REPRISE HORS DU CONTEXTE DE L'AUTHENTIFICATION AUSSI
# ===========================================================================


@pytest.mark.integration
def test_le_correlation_token_courant_est_REPRIS_pour_les_evenements(cx: Connection) -> None:
    identifiant = definir_correlation("une-correlation-de-test-t5")
    try:
        entite = _entite(cx, f"{MARQUEUR}-CORR")
        acteur = _personne(cx, f"acteur-corr-{uuid.uuid4().hex[:8]}@exalt-company.com")
        evenement = _evenement(cx, entite, acteur, titre="Correlation")
        archiver_un_evenement(
            cx,
            entite=entite,
            evenement=evenement,
            acteur=acteur,
            version_attendue=1,
            instant=INSTANT,
        )
        lignes = _audit_events(
            cx, action_code=ActionEvenement.ARCHIVER.value, resource_reference=evenement
        )
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
        evenement = _evenement(decor, entite, acteur, titre="Atomicite")
    try:
        with (
            pytest.raises(RuntimeError, match="echec force apres l'audit"),
            moteur(parametres_de_la_stack).begin() as transaction,
        ):
            archiver_un_evenement(
                transaction,
                entite=entite,
                evenement=evenement,
                acteur=acteur,
                version_attendue=1,
                instant=INSTANT,
            )
            #  A cet instant, `event.archived_at` ET `audit_event` portent deja
            #  la trace — mais la transaction N'A PAS COMMIT.
            raise RuntimeError("echec force apres l'audit, pour prouver l'atomicite")
        with moteur(parametres_de_la_stack).connect() as verification:
            #  Filtre sur `action_code` : le decor cree l'evenement via le
            #  SERVICE `creer_un_evenement`, lui-meme cable (`T5`) — son PROPRE
            #  `audit_event` de creation a deja COMMIT dans le decor, avec le
            #  MEME `resource_reference`. Sans ce filtre, cet evenement
            #  legitime masquerait l'absence de celui de l'archivage — meme
            #  confusion que `T4` a corrigee avant de l'ecrire ici.
            n_audit = verification.execute(
                text(
                    "SELECT count(*) FROM audit_event "
                    "WHERE resource_reference = :e AND action_code = :action"
                ),
                {"e": evenement, "action": ActionEvenement.ARCHIVER.value},
            ).scalar_one()
            archive_le = verification.execute(
                text("SELECT archived_at FROM event WHERE id = :e"), {"e": evenement}
            ).scalar_one()
            assert n_audit == 0, (
                "l'audit_event a SURVECU a l'echec : la transaction n'est pas atomique"
            )
            assert archive_le is None, "l'evenement a ete archive malgre l'echec force"
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
                    "DELETE FROM event WHERE entity_id IN "
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
