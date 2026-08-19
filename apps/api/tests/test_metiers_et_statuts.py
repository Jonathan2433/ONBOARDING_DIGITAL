"""Metiers, affectations et situations professionnelles — modele §6.3 a §6.5.

LOT 2, sous-etape `T5`, story `MVP-L02-US003`.

LE TEST LE PLUS IMPORTANT DE CE FICHIER EST CELUI DE LA CLE COMPOSITE. Le §6.4
exige que « le metier appartienne a la meme entite que l'appartenance », et le
§25.3 y repond par un couple `(id, entity_id)`. Une paire de cles SIMPLES vers
`entity_membership(id)` et `job_catalog(id)` laisserait affecter un metier de
Lille a une appartenance de Bordeaux, et rien ne le signalerait. Le test le
verifie sur des entites REELLEMENT differentes.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import Column, Integer, MetaData, Table, UniqueConstraint, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.modeles import metadonnees
from app.people import SITUATIONS_PROFESSIONNELLES, SituationProfessionnelle
from app.shared.database import moteur
from app.shared.modele import (
    CONVENTION_DE_NOMMAGE,
    noms_d_index_en_collision,
    noms_de_contraintes_trop_longs,
)

# ============================================================================
#  1. Unitaires
# ============================================================================


def test_la_situation_professionnelle_est_ecrite_en_ANGLAIS() -> None:
    """§6.5 : « `status` | `mission` ou `intercontract` ».

    MESURE DU 19/08/2026. Le modele emploie les DEUX orthographes, et elles ne
    sont pas interchangeables : `intercontract` aux lignes 352, 361 et 770,
    TOUJOURS entre accents graves, donc la ou il specifie une VALEUR ;
    `intercontrat` aux lignes 48, 69, 353, 915 et 1710, en PROSE.

    `ECART-012` citait la forme francaise dans son champ Source : corrige. Ce
    test existe pour que la confusion ne revienne pas -- quelqu'un lisant l'ecart
    plutot que le modele stockerait une valeur que rien ne reconnaitrait.
    """
    assert SITUATIONS_PROFESSIONNELLES == ("mission", "intercontract")
    assert "intercontrat" not in SITUATIONS_PROFESSIONNELLES, (
        "la forme FRANCAISE est celle de la prose du modele, jamais celle de la valeur"
    )


def test_aucune_collision_de_nom_d_index_dans_le_modele() -> None:
    """Deux collisions se sont produites : `T4` sur une exclusion, `T5` sur un UNIQUE.

    PostgreSQL implemente les cles primaires, les contraintes UNIQUE et les
    exclusions par des INDEX, et **les noms d'index sont uniques a l'echelle du
    SCHEMA**. Ce controle compare les noms entre eux -- ce que PostgreSQL fera de
    toute facon -- plutot que de verifier un prefixe.
    """
    assert noms_d_index_en_collision() == []


def test_le_controle_de_collision_DETECTE_deux_noms_identiques() -> None:
    """Temoin : sans lui, le test precedent passerait meme si le controle etait casse."""
    essai = MetaData(naming_convention=CONVENTION_DE_NOMMAGE)
    for nom_table in ("essai_a", "essai_b"):
        Table(
            nom_table,
            essai,
            Column("id", Integer, primary_key=True),
            Column("couple", Integer, nullable=False),
            UniqueConstraint("couple", name="meme_nom_partout"),
        )
    assert noms_d_index_en_collision(essai) == [("meme_nom_partout", ["essai_a", "essai_b"])]


def test_aucun_nom_de_contrainte_ne_depasse_la_limite() -> None:
    """DESORMAIS NON CREUX, et il a servi.

    Trois cles etrangeres COMPOSITES depassaient les 63 octets de PostgreSQL --
    77, 65 et 82 caracteres -- parce que la convention concatene toutes les
    colonnes. Ce controle, ecrit en `T1`, les a attrapees quatre sous-etapes plus
    tard.
    """
    noms = {c.name for t in metadonnees.tables.values() for c in t.constraints if c.name}
    assert len(noms) > 20, "le modele doit declarer assez de contraintes pour que ce test morde"
    assert noms_de_contraintes_trop_longs() == []


# ============================================================================
#  2. Integration
# ============================================================================

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
MARS = dt.datetime(2026, 3, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
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


def _entite(connexion: Connection, code: str = "BORDEAUX") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _appartenance(connexion: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    personne = connexion.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:affichage, :normalise, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"affichage": adresse, "normalise": adresse},
    ).scalar_one()
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _metier(
    connexion: Connection, entite: uuid.UUID, code: str = "DEV", *, archive: bool = False
) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label, archived_at) "
            "VALUES (:e, :code, :label, CASE WHEN :archive THEN now() ELSE NULL END) RETURNING id"
        ),
        {"e": entite, "code": code, "label": code.title(), "archive": archive},
    ).scalar_one()


def _affecter_metier(
    connexion: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    metier: uuid.UUID,
    *,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_id, entity_membership_id, "
            "job_catalog_id, starts_at, ends_at) VALUES (:e, :a, :m, :debut, :fin)"
        ),
        {"e": entite, "a": appartenance, "m": metier, "debut": debut, "fin": fin},
    )


def _client(connexion: Connection, nom: str | None = None) -> uuid.UUID:
    """Creer un client REEL, et le motif est une lecon.

    **AJOUTEE EN `T6`.** Ces tests passaient `uuid.uuid4()` comme identifiant de
    client, ce qui marchait en `T5` : la colonne etait un `uuid` SANS cle
    etrangere, `client` n'existant pas encore.

    `T6` a ajoute la cle -- c'etait une dette explicite, annoncee dans l'en-tete de
    la migration `0006` -- et trois tests de `T5` sont passes au rouge. Ils etaient
    JUSTES quand ils ont ete ecrits ; c'est `T6` qui les a rendus faux. C'est le
    §7.21 de la passation, et la bonne reaction est de les mettre a jour en disant
    pourquoi, jamais de contourner la cle.

    Le nom est engendre par defaut : `client.canonical_name` est unique, et
    plusieurs appels dans un meme test doivent produire des clients distincts.
    """
    canonique = nom or f"client {uuid.uuid4().hex[:8]}"
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:nom, :affiche, 'active') RETURNING id"
        ),
        {"nom": canonique, "affiche": canonique.title()},
    ).scalar_one()


def _situation(
    connexion: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    *,
    status: str = "intercontract",
    client: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, client_id, starts_at, ends_at) VALUES (:e, :a, :s, :c, :debut, :fin)"
        ),
        {"e": entite, "a": appartenance, "s": status, "c": client, "debut": debut, "fin": fin},
    )


# ----------------------------------------------------------------------------
#  §6.3 — job_catalog
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_metier_se_cree_avec_ses_defauts(cx: Connection) -> None:
    _metier(cx, _entite(cx))
    ligne = cx.execute(text("SELECT code, display_order, active FROM job_catalog")).one()
    assert ligne.code == "DEV"
    assert ligne.display_order == 0
    assert ligne.active is True


@pytest.mark.integration
def test_le_code_de_metier_est_unique_dans_une_entite(cx: Connection) -> None:
    entite = _entite(cx)
    _metier(cx, entite, "DEV")
    with pytest.raises(IntegrityError) as echec:
        _metier(cx, entite, "DEV")
    assert "uq_job_catalog_entity_id_code_non_archive" in str(echec.value)


@pytest.mark.integration
def test_un_metier_ARCHIVE_libere_son_code(cx: Connection) -> None:
    """§25.1 : l'index est PARTIEL, `WHERE archived_at IS NULL`.

    Difference assumee avec `entity(code)`, dont l'unicite n'est pas partielle :
    un code d'entite est cite dans les journaux d'audit, un code de metier est une
    donnee de configuration locale.
    """
    entite = _entite(cx)
    _metier(cx, entite, "DEV", archive=True)
    _metier(cx, entite, "DEV")
    assert cx.execute(text("SELECT count(*) FROM job_catalog")).scalar_one() == 2


@pytest.mark.integration
def test_le_meme_code_de_metier_existe_dans_DEUX_entites(cx: Connection) -> None:
    """Temoin : l'unicite porte sur le couple, le catalogue etant local (§6.3)."""
    _metier(cx, _entite(cx, "BORDEAUX"), "DEV")
    _metier(cx, _entite(cx, "LILLE"), "DEV")
    assert cx.execute(text("SELECT count(*) FROM job_catalog")).scalar_one() == 2


# ----------------------------------------------------------------------------
#  §6.4 — LA CLE COMPOSITE, et c'est le test central de cette sous-etape
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_metier_d_une_AUTRE_entite_est_REFUSE(cx: Connection) -> None:
    """§6.4 : « le metier appartient a la meme entite que l'appartenance ».

    C'EST LE TEST QUI PROUVE QUE LES CLES COMPOSITES SERVENT. Avec deux cles
    SIMPLES vers `entity_membership(id)` et `job_catalog(id)`, cette insertion
    passerait : les deux identifiants existent. Rien ne relierait les entites.
    """
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance = _appartenance(cx, bordeaux, "jean@exalt.com")
    metier_de_lille = _metier(cx, lille, "DEV")
    with pytest.raises(IntegrityError) as echec:
        _affecter_metier(cx, bordeaux, appartenance, metier_de_lille)
    assert "fk_membership_job_assignment_job_catalog" in str(echec.value), (
        "le refus doit venir de la cle etrangere COMPOSITE vers job_catalog"
    )


@pytest.mark.integration
def test_un_metier_de_la_MEME_entite_est_accepte(cx: Connection) -> None:
    """Temoin : la cle composite ne refuse pas toute affectation."""
    entite = _entite(cx)
    _affecter_metier(cx, entite, _appartenance(cx, entite, "jean@exalt.com"), _metier(cx, entite))
    assert cx.execute(text("SELECT count(*) FROM membership_job_assignment")).scalar_one() == 1


@pytest.mark.integration
def test_une_appartenance_d_une_AUTRE_entite_est_REFUSEE(cx: Connection) -> None:
    """L'autre moitie de la regle : la cle composite vers `entity_membership`."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance_de_lille = _appartenance(cx, lille, "jean@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        _affecter_metier(cx, bordeaux, appartenance_de_lille, _metier(cx, bordeaux))
    assert "fk_membership_job_assignment_entity_membership" in str(echec.value)


@pytest.mark.integration
def test_une_seule_affectation_metier_ACTIVE(cx: Connection) -> None:
    """§6.4 : « une seule affectation metier active ».

    LE REFUS VIENT DE L'EXCLUSION, ET C'EST LA MESURE QUI L'A DIT. J'attendais un
    index unique partiel `WHERE ends_at IS NULL`. Il ne peut JAMAIS se declencher :
    deux affectations actives ont toutes deux `ends_at` a NULL, donc deux plages
    NON BORNEES, qui se chevauchent toujours. L'exclusion les refuse la premiere.

    L'index a donc ete retire du modele -- il n'etait pas dans le §25.1, c'etait
    ma derivation, et elle etait inutile. Ce test porte sur le mecanisme reel.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _affecter_metier(cx, entite, appartenance, _metier(cx, entite, "DEV"), fin=None)
    with pytest.raises(IntegrityError) as echec:
        _affecter_metier(
            cx, entite, appartenance, _metier(cx, entite, "LEAD"), debut=DECEMBRE, fin=None
        )
    assert "ex_membership_job_assignment_sans_chevauchement" in str(echec.value)


@pytest.mark.integration
def test_une_affectation_CLOSE_coexiste_avec_une_active(cx: Connection) -> None:
    """Temoin : l'historisation du §2.3, « historisation plutot qu'ecrasement »."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _affecter_metier(cx, entite, appartenance, _metier(cx, entite, "DEV"), debut=JANVIER, fin=JUIN)
    _affecter_metier(cx, entite, appartenance, _metier(cx, entite, "LEAD"), debut=JUIN, fin=None)
    assert cx.execute(text("SELECT count(*) FROM membership_job_assignment")).scalar_one() == 2


@pytest.mark.integration
def test_deux_affectations_metier_qui_se_chevauchent_sont_refusees(cx: Connection) -> None:
    """§6.4 et §25.2 : « les periodes ne se chevauchent pas »."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _affecter_metier(cx, entite, appartenance, _metier(cx, entite, "DEV"), debut=JANVIER, fin=JUIN)
    with pytest.raises(IntegrityError) as echec:
        _affecter_metier(
            cx, entite, appartenance, _metier(cx, entite, "LEAD"), debut=MARS, fin=DECEMBRE
        )
    assert "ex_membership_job_assignment_sans_chevauchement" in str(echec.value)


# ----------------------------------------------------------------------------
#  §6.5 — situation professionnelle
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_une_MISSION_exige_un_client(cx: Connection) -> None:
    """§6.5 : « `client_id` obligatoire en mission »."""
    entite = _entite(cx)
    with pytest.raises(IntegrityError) as echec:
        _situation(
            cx, entite, _appartenance(cx, entite, "jean@exalt.com"), status="mission", client=None
        )
    assert "client_selon_le_statut" in str(echec.value)


@pytest.mark.integration
def test_un_INTERCONTRACT_interdit_un_client(cx: Connection) -> None:
    """§6.5 : « nul en intercontrat ». L'autre sens de la meme regle."""
    entite = _entite(cx)
    with pytest.raises(IntegrityError) as echec:
        _situation(
            cx,
            entite,
            _appartenance(cx, entite, "jean@exalt.com"),
            status="intercontract",
            #  Un client REEL, meme pour un test de refus : depuis que la cle
            #  etrangere existe (`T6`), un identifiant fictif ferait echouer la
            #  cle plutot que la contrainte visee. Le test ne prouverait plus ce
            #  qu'il annonce.
            client=_client(cx),
        )
    assert "client_selon_le_statut" in str(echec.value)


@pytest.mark.integration
def test_les_deux_situations_bien_formees_sont_acceptees(cx: Connection) -> None:
    """Temoin : la contrainte ne refuse pas les deux cas legitimes.

    `client_id` porte un identifiant quelconque : **la cle etrangere vers
    `client` n'existe pas encore**, cette table arrivant en `T6`. C'est dit dans
    la migration `0006`, et la contrainte y sera ajoutee.
    """
    entite = _entite(cx)
    _situation(
        cx,
        entite,
        _appartenance(cx, entite, "a@exalt.com"),
        status="mission",
        client=_client(cx),
    )
    _situation(
        cx, entite, _appartenance(cx, entite, "b@exalt.com"), status="intercontract", client=None
    )
    assert cx.execute(text("SELECT count(*) FROM professional_status_assignment")).scalar_one() == 2


@pytest.mark.integration
def test_un_statut_hors_liste_est_refuse(cx: Connection) -> None:
    entite = _entite(cx)
    with pytest.raises(IntegrityError) as echec:
        _situation(cx, entite, _appartenance(cx, entite, "jean@exalt.com"), status="intercontrat")
    assert "status_valide" in str(echec.value), (
        "la forme FRANCAISE `intercontrat` doit etre refusee : la valeur du modele "
        "est `intercontract`. Voir ECART-012 et le test unitaire d'orthographe."
    )


@pytest.mark.integration
def test_une_seule_situation_ACTIVE_par_appartenance(cx: Connection) -> None:
    """§6.5 : « une seule situation active par appartenance ».

    Meme mecanisme que pour le metier : l'exclusion suffit, un index partiel
    `WHERE ends_at IS NULL` serait inatteignable.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _situation(cx, entite, appartenance, fin=None)
    with pytest.raises(IntegrityError) as echec:
        _situation(cx, entite, appartenance, debut=DECEMBRE, fin=None)
    assert "ex_professional_status_assignment_sans_chevauchement" in str(echec.value)


@pytest.mark.integration
def test_deux_situations_qui_se_chevauchent_sont_refusees(cx: Connection) -> None:
    """§25.2 : « statut professionnel » figure dans la liste des relations temporelles."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _situation(cx, entite, appartenance, debut=JANVIER, fin=JUIN)
    with pytest.raises(IntegrityError) as echec:
        _situation(cx, entite, appartenance, debut=MARS, fin=DECEMBRE)
    assert "ex_professional_status_assignment_sans_chevauchement" in str(echec.value)


@pytest.mark.integration
def test_une_succession_de_situations_est_acceptee(cx: Connection) -> None:
    """Temoin : le §2.3 veut l'historisation, pas l'ecrasement."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _situation(cx, entite, appartenance, status="intercontract", debut=JANVIER, fin=JUIN)
    _situation(
        cx,
        entite,
        appartenance,
        status="mission",
        client=_client(cx),
        debut=JUIN,
        fin=None,
    )
    etats = (
        cx.execute(text("SELECT status FROM professional_status_assignment ORDER BY starts_at"))
        .scalars()
        .all()
    )
    assert list(etats) == ["intercontract", "mission"]


@pytest.mark.integration
def test_une_situation_d_une_AUTRE_entite_est_refusee(cx: Connection) -> None:
    """La cle composite vaut aussi pour la situation professionnelle."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    with pytest.raises(IntegrityError) as echec:
        _situation(cx, bordeaux, _appartenance(cx, lille, "jean@exalt.com"))
    assert "fk_professional_status_assignment_entity_membership" in str(echec.value)


@pytest.mark.integration
def test_toutes_les_situations_declarees_sont_acceptees(cx: Connection) -> None:
    """Temoin de l'enumeration."""
    entite = _entite(cx)
    for indice, situation in enumerate(SituationProfessionnelle):
        _situation(
            cx,
            entite,
            _appartenance(cx, entite, f"p{indice}@exalt.com"),
            status=situation.value,
            client=_client(cx) if situation is SituationProfessionnelle.MISSION else None,
        )
    total = cx.execute(text("SELECT count(*) FROM professional_status_assignment")).scalar_one()
    assert total == len(SITUATIONS_PROFESSIONNELLES)
