"""Le cablage de l'audit generique sur les contenus et le Framework — LOT 10, `T4`.

Stories `MVP-L10-US001`/`US002`, modele §21.1, `ARB-DATA-005`/`§30.20`.

CE QUE CE FICHIER PROUVE, ET DANS QUEL ORDRE

  1. chacune des huit fonctions d'ecriture deja posees par le LOT 6 — creer une
     page, remplacer son contenu, la publier, l'archiver, la restaurer, creer
     un lien interne, le modifier, reordonner les liens — ecrit AUSSI une
     ligne `audit_event`, dans la MEME transaction ;
  2. `action_code` REUTILISE `ActionEditoriale` (§7.27) pour les cinq actions
     du cycle de vie d'une page, et n'invente un litteral que pour les liens
     internes, qu'aucune enumeration ne nomme encore ;
  3. `remplacer_le_contenu` ecrit UN SEUL `audit_event` pour l'appel entier —
     a la difference de `modifier_les_donnees_organisationnelles` (`T3`), ce
     n'est pas une fonction de diff par champ : elle archive et recree les
     blocs a chaque appel, donc un seul evenement couvre les trois ecritures
     SQL d'un seul geste metier ;
  4. `reordonner_les_liens` ecrit UN SEUL `audit_event` pour tout l'ensemble
     reordonne, jamais un par lien deplace — et n'en ecrit AUCUN quand il n'y
     a rien a reordonner (liste vide, retour anticipe avant toute ecriture) ;
  5. le correlation token courant est repris ici aussi ;
  6. l'atomicite n'est pas qu'une affirmation : un echec survenant APRES
     l'ecriture d'un `audit_event`, dans la MEME transaction, annule aussi
     cette ecriture.

CE QUE CE FICHIER NE REPROUVE PAS

  Les regles METIER de chaque site (permissions, concurrence optimiste,
  validation des types de bloc et des URL) sont deja prouvees par leurs
  propres suites — `test_ecriture_des_contenus.py`,
  `test_cycle_de_vie_des_contenus.py`, `test_liens_internes.py`. Ce fichier ne
  porte que ce que `T4` ajoute : la ligne `audit_event` elle-meme.
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
from app.content.cycle_de_vie import archiver_une_page, publier_une_page, restaurer_une_page
from app.content.ecriture import BlocDemande, creer_une_page, remplacer_le_contenu
from app.content.liens import creer_un_lien, modifier_un_lien, reordonner_les_liens
from app.content.perimetre import ActionEditoriale
from app.shared.correlation import definir_correlation, effacer_correlation
from app.shared.database import moteur

INSTANT = dt.datetime(2026, 10, 18, 9, 0, tzinfo=dt.UTC)
PLUS_TARD = INSTANT + dt.timedelta(days=1)
MARQUEUR = "T4L10"


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
#  Le decor. Local a ce fichier, comme ceux de `T2` et `T3` : aucun test du
#  depot n'importe le decor d'un autre.
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
                    "VALUES (:affichage, :normalise, 'Test', 'T4L10', 'active') RETURNING id"
                ),
                {"affichage": adresse, "normalise": adresse.lower()},
            ).scalar_one()
        )
    )


def _page(
    connexion: Connection,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    *,
    slug: str,
    titre: str = "Page de test",
) -> uuid.UUID:
    return creer_une_page(
        connexion,
        entite=entite,
        acteur=acteur,
        type_de_page="HOME",
        titre=titre,
        slug=slug,
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
#  LA CREATION D'UNE PAGE — `app.content.ecriture`
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_une_page_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-CREA")
    acteur = _personne(cx, f"acteur-crea-{uuid.uuid4().hex[:8]}@exalt-company.com")

    creee = creer_une_page(
        cx,
        entite=entite,
        acteur=acteur,
        type_de_page="HOME",
        titre="Accueil",
        slug=f"accueil-{uuid.uuid4().hex[:8]}",
        code_de_cercle=None,
        code_de_bureau=None,
        instant=INSTANT,
    )

    lignes = _audit_events(
        cx, action_code=ActionEditoriale.CREER.value, resource_reference=creee.identifiant
    )
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "content_page"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == INSTANT
    assert ligne["retention_until"] == INSTANT + DUREE_DE_RETENTION
    assert ligne["correlation_token"]


# ===========================================================================
#  LE REMPLACEMENT DU CONTENU — `app.content.ecriture`
# ===========================================================================


@pytest.mark.integration
def test_le_remplacement_du_contenu_ecrit_un_SEUL_audit_event(cx: Connection) -> None:
    """UN evenement pour l'appel entier, pas un par bloc archive ou insere.

    A la difference de `modifier_les_donnees_organisationnelles` (`T3`),
    `remplacer_le_contenu` n'est pas une fonction de diff par champ : elle
    archive puis recree les blocs a CHAQUE appel. Un seul `audit_event` couvre
    donc les trois ecritures SQL (archivage des anciens blocs, insertion des
    nouveaux, mise a jour du titre).
    """
    entite = _entite(cx, f"{MARQUEUR}-REMPL")
    acteur = _personne(cx, f"acteur-rempl-{uuid.uuid4().hex[:8]}@exalt-company.com")
    page = _page(cx, entite, acteur, slug=f"p-{uuid.uuid4().hex[:8]}", titre="Ancien titre")

    ecrit = remplacer_le_contenu(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=1,
        titre="Nouveau titre",
        blocs=(
            BlocDemande(type_de_bloc="TITLE", contenu={"texte": "Bienvenue"}),
            BlocDemande(type_de_bloc="RICH_TEXT", contenu={"texte": "Chez eXalt"}),
        ),
        instant=PLUS_TARD,
    )
    assert len(ecrit.blocs) == 2

    lignes = _audit_events(cx, action_code=ActionEditoriale.MODIFIER.value, resource_reference=page)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "content_page"
    assert ligne["entity_id"] == entite
    assert ligne["actor_person_id"] == acteur
    assert ligne["occurred_at"] == PLUS_TARD
    assert ligne["old_values"] == {"titre": "Ancien titre"}
    assert ligne["new_values"] == {"titre": "Nouveau titre"}


# ===========================================================================
#  LE CYCLE DE VIE D'UNE PAGE — `app.content.cycle_de_vie`
# ===========================================================================


@pytest.mark.integration
def test_la_publication_d_une_page_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-PUB")
    acteur = _personne(cx, f"acteur-pub-{uuid.uuid4().hex[:8]}@exalt-company.com")
    page = _page(cx, entite, acteur, slug=f"p-{uuid.uuid4().hex[:8]}")

    publier_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    lignes = _audit_events(cx, action_code=ActionEditoriale.PUBLIER.value, resource_reference=page)
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "content_page"
    assert lignes[0]["entity_id"] == entite
    assert lignes[0]["actor_person_id"] == acteur


@pytest.mark.integration
def test_l_archivage_d_une_page_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-ARCH")
    acteur = _personne(cx, f"acteur-arch-{uuid.uuid4().hex[:8]}@exalt-company.com")
    page = _page(cx, entite, acteur, slug=f"p-{uuid.uuid4().hex[:8]}")

    archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    lignes = _audit_events(cx, action_code=ActionEditoriale.ARCHIVER.value, resource_reference=page)
    assert len(lignes) == 1
    assert lignes[0]["entity_id"] == entite


@pytest.mark.integration
def test_la_restauration_d_une_page_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-REST")
    acteur = _personne(cx, f"acteur-rest-{uuid.uuid4().hex[:8]}@exalt-company.com")
    page = _page(cx, entite, acteur, slug=f"p-{uuid.uuid4().hex[:8]}")
    archivee = archiver_une_page(
        cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=INSTANT
    )

    restaurer_une_page(
        cx,
        entite=entite,
        page=page,
        acteur=acteur,
        version_attendue=archivee.version,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(
        cx, action_code=ActionEditoriale.RESTAURER.value, resource_reference=page
    )
    assert len(lignes) == 1
    assert lignes[0]["occurred_at"] == PLUS_TARD


# ===========================================================================
#  LES LIENS INTERNES — `app.content.liens`
# ===========================================================================


@pytest.mark.integration
def test_la_creation_d_un_lien_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-LIENCREA")
    acteur = _personne(cx, f"acteur-liencrea-{uuid.uuid4().hex[:8]}@exalt-company.com")

    cree = creer_un_lien(
        cx,
        entite=entite,
        acteur=acteur,
        libelle="Hub",
        url="https://hub.exemple.test/",
        type_de_lien="HUB",
        description=None,
        reference_d_icone=None,
        actif=True,
        instant=INSTANT,
    )

    lignes = _audit_events(cx, action_code="lien_cree", resource_reference=cree.identifiant)
    assert len(lignes) == 1
    assert lignes[0]["resource_type"] == "internal_link"
    assert lignes[0]["entity_id"] == entite
    assert lignes[0]["actor_person_id"] == acteur


@pytest.mark.integration
def test_la_modification_d_un_lien_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, f"{MARQUEUR}-LIENMODIF")
    acteur = _personne(cx, f"acteur-lienmodif-{uuid.uuid4().hex[:8]}@exalt-company.com")
    cree = creer_un_lien(
        cx,
        entite=entite,
        acteur=acteur,
        libelle="Hub",
        url="https://hub.exemple.test/",
        type_de_lien="HUB",
        description=None,
        reference_d_icone=None,
        actif=True,
        instant=INSTANT,
    )

    modifier_un_lien(
        cx,
        entite=entite,
        lien=cree.identifiant,
        acteur=acteur,
        version_attendue=cree.version,
        libelle="Hub eXalt",
        url="https://hub.exemple.test/",
        type_de_lien="HUB",
        description=None,
        reference_d_icone=None,
        actif=False,
        instant=PLUS_TARD,
    )

    lignes = _audit_events(cx, action_code="lien_modifie", resource_reference=cree.identifiant)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["occurred_at"] == PLUS_TARD
    #  `actif` figure dans `new_values` : c'est le SEUL moyen de retirer un
    #  lien (§19), et c'est donc la seule trace qui distingue un retrait d'une
    #  modification ordinaire.
    assert ligne["new_values"] == {
        "libelle": "Hub eXalt",
        "url": "https://hub.exemple.test/",
        "actif": False,
    }


@pytest.mark.integration
def test_le_reordonnancement_des_liens_ecrit_UN_SEUL_audit_event(cx: Connection) -> None:
    """UN evenement pour tout l'ensemble reordonne, jamais un par lien deplace."""
    entite = _entite(cx, f"{MARQUEUR}-LIENORDRE")
    acteur = _personne(cx, f"acteur-lienordre-{uuid.uuid4().hex[:8]}@exalt-company.com")
    premier = creer_un_lien(
        cx,
        entite=entite,
        acteur=acteur,
        libelle="A",
        url="https://a.exemple.test/",
        type_de_lien="HUB",
        description=None,
        reference_d_icone=None,
        actif=True,
        instant=INSTANT,
    ).identifiant
    second = creer_un_lien(
        cx,
        entite=entite,
        acteur=acteur,
        libelle="B",
        url="https://b.exemple.test/",
        type_de_lien="HUB",
        description=None,
        reference_d_icone=None,
        actif=True,
        instant=INSTANT,
    ).identifiant

    reordonner_les_liens(
        cx, entite=entite, acteur=acteur, ordre=(second, premier), instant=PLUS_TARD
    )

    lignes = _audit_events(cx, action_code="liens_reordonnes")
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne["resource_type"] == "internal_link"
    assert ligne["resource_reference"] is None
    assert ligne["entity_id"] == entite
    assert ligne["new_values"] == {"ordre": [str(second), str(premier)]}


@pytest.mark.integration
def test_le_reordonnancement_a_vide_n_ecrit_AUCUN_audit_event(cx: Connection) -> None:
    """Rien a reordonner : le retour anticipe precede toute ecriture, audit compris."""
    entite = _entite(cx, f"{MARQUEUR}-LIENVIDE")
    acteur = _personne(cx, f"acteur-lienvide-{uuid.uuid4().hex[:8]}@exalt-company.com")

    resultat = reordonner_les_liens(cx, entite=entite, acteur=acteur, ordre=(), instant=INSTANT)

    assert resultat == ()
    assert len(_audit_events(cx, action_code="liens_reordonnes")) == 0


# ===========================================================================
#  CORRELATION — REPRISE HORS DU CONTEXTE DE L'AUTHENTIFICATION AUSSI
# ===========================================================================


@pytest.mark.integration
def test_le_correlation_token_courant_est_REPRIS_pour_les_contenus(cx: Connection) -> None:
    identifiant = definir_correlation("une-correlation-de-test-t4")
    try:
        entite = _entite(cx, f"{MARQUEUR}-CORR")
        acteur = _personne(cx, f"acteur-corr-{uuid.uuid4().hex[:8]}@exalt-company.com")
        page = _page(cx, entite, acteur, slug=f"p-{uuid.uuid4().hex[:8]}")
        archiver_une_page(
            cx, entite=entite, page=page, acteur=acteur, version_attendue=1, instant=INSTANT
        )
        lignes = _audit_events(
            cx, action_code=ActionEditoriale.ARCHIVER.value, resource_reference=page
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
        page = _page(decor, entite, acteur, slug=f"p-{uuid.uuid4().hex[:8]}")
    try:
        with (
            pytest.raises(RuntimeError, match="echec force apres l'audit"),
            moteur(parametres_de_la_stack).begin() as transaction,
        ):
            archiver_une_page(
                transaction,
                entite=entite,
                page=page,
                acteur=acteur,
                version_attendue=1,
                instant=INSTANT,
            )
            #  A cet instant, `content_page.archived_at` ET `audit_event`
            #  portent deja la trace — mais la transaction N'A PAS COMMIT.
            raise RuntimeError("echec force apres l'audit, pour prouver l'atomicite")
        with moteur(parametres_de_la_stack).connect() as verification:
            #  Filtre sur `action_code` : le decor cree la page via le SERVICE
            #  `creer_une_page`, lui-meme cable (`T4`) — son PROPRE
            #  `audit_event` de creation a deja COMMIT dans le decor, avec le
            #  MEME `resource_reference`. Sans ce filtre, cet evenement
            #  legitime masquerait l'absence de celui de l'archivage.
            n_audit = verification.execute(
                text(
                    "SELECT count(*) FROM audit_event "
                    "WHERE resource_reference = :p AND action_code = :action"
                ),
                {"p": page, "action": ActionEditoriale.ARCHIVER.value},
            ).scalar_one()
            archivee_le = verification.execute(
                text("SELECT archived_at FROM content_page WHERE id = :p"), {"p": page}
            ).scalar_one()
            assert n_audit == 0, (
                "l'audit_event a SURVECU a l'echec : la transaction n'est pas atomique"
            )
            assert archivee_le is None, "la page a ete archivee malgre l'echec force"
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
                    "DELETE FROM content_page WHERE entity_id IN "
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
