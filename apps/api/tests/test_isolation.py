"""Isolation inter-entites — modele §2.5 et §25.3.

LOT 2, sous-etape `T11`, story `MVP-L02-US006`.

LE CRITERE DIT « LES TESTS DEMONTRENT L'ABSENCE DE FUITE », ET UNE ABSENCE NE SE
DEMONTRE PAS EN MONTRANT QU'UN CAS EST REFUSE.

  Il faut enumerer les chemins par lesquels une fuite serait possible, les COUVRIR
  tous, et **prouver que la liste est complete**. C'est la troisieme proposition du
  §7.0 de la passation.

  La liste des huit cles etrangeres composites est donc **DERIVEE DU CATALOGUE
  PostgreSQL** par `test_les_cles_composites_sont_toutes_couvertes`, et confrontee a
  la table `COUVERTURE` ci-dessous. **Une DIXIEME cle composite fera echouer ce
  test** jusqu'a ce qu'elle ait son propre test de refus -- plutot que d'etre
  ignoree en silence.

ET UN PIEGE QUI A COUTE UN TEST EN `T10`

  Les declencheurs `BEFORE ROW` s'executent AVANT la verification des cles
  etrangeres : un declencheur qui refuse la ligne pour une autre raison **masque la
  cle etrangere**. Chaque test ci-dessous construit donc une ligne que tous les
  declencheurs de sa table ACCEPTENT, pour que la cle etrangere soit bien ce qui
  parle. Le nom de la contrainte est verifie dans le message.
"""

from __future__ import annotations

import ast
import datetime as dt
import pathlib
import re
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.shared.database import moteur

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

#  Les huit chemins de fuite fermes par une cle etrangere composite, et le test
#  qui prouve chacun. Les CLES de ce dictionnaire sont confrontees au catalogue
#  PostgreSQL : recopier huit lignes serait un `ECART-021` en puissance, mais
#  **rattacher un chemin a son test est une interpretation**, declaree ici.
COUVERTURE: dict[tuple[str, str], str] = {
    ("circle_membership", "circle"): "test_un_cercle_d_une_autre_entite_est_refuse",
    (
        "circle_membership",
        "entity_membership",
    ): "test_une_appartenance_d_une_autre_entite_dans_un_cercle_est_refusee",
    ("dsm_assignment", "entity_membership"): "test_un_consultant_d_une_autre_entite_est_refuse",
    (
        "framework_responsibility_assignment",
        "circle",
    ): "test_un_BOOSTER_sur_un_cercle_d_une_autre_entite_est_refuse",
    (
        "framework_responsibility_assignment",
        "office",
    ): "test_un_OFFICE_MANAGER_sur_un_bureau_d_une_autre_entite_est_refuse",
    (
        "membership_job_assignment",
        "entity_membership",
    ): "test_un_metier_attribue_a_une_appartenance_d_une_autre_entite_est_refuse",
    ("membership_job_assignment", "job_catalog"): "test_un_metier_d_une_autre_entite_est_refuse",
    (
        "professional_status_assignment",
        "entity_membership",
    ): "test_une_situation_sur_une_appartenance_d_une_autre_entite_est_refusee",
    #  LOT 5, `T1` — la NEUVIEME cle composite. **Son test vit dans
    #  `test_medias.py`**, avec les autres refus des tables de media : le
    #  dupliquer ici serait deux exemplaires d'une meme preuve, ce que le §7.27
    #  refuse. Le garde-fou ci-dessous ne verifie pas l'existence du test nomme --
    #  `COUVERTURE` est une table d'etiquettes -- mais il exige que le NOMBRE de
    #  cles composites du catalogue egale le nombre d'entrees ici.
    (
        "media_variant",
        "media_asset",
    ): "test_une_variante_ne_peut_pas_pointer_l_actif_d_une_AUTRE_entite [test_medias.py]",
}


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


# ---------------------------------------------------------------------------
#  Fabriques
# ---------------------------------------------------------------------------


def _entite(connexion: Connection, code: str) -> uuid.UUID:
    #  UN PARAMETRE LIE PAR COLONNE, ET JAMAIS DEUX COLONNES SUR LE MEME.
    #  Reutiliser un parametre rend « inconsistent types deduced for parameter
    #  $1 » — defaut `T4-2`, rejoue en `T8-3`, et une TROISIEME fois ici. Le
    #  garde-fou est desormais mecanique :
    #  `test_aucune_fabrique_ne_reutilise_un_parametre_lie` relit ce fichier.
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:courriel, :normalise, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"courriel": adresse, "normalise": adresse},
    ).scalar_one()


def _appartenance(connexion: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, membership_state, "
            "professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": _personne(connexion, adresse), "e": entite},
    ).scalar_one()


def _cercle(connexion: Connection, entite: uuid.UUID, code: str = "TECH") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :c, :n) RETURNING id"),
        {"e": entite, "c": code, "n": code},
    ).scalar_one()


def _bureau(connexion: Connection, entite: uuid.UUID, code: str = "BDX1") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO office (entity_id, code, name) VALUES (:e, :c, :n) RETURNING id"),
        {"e": entite, "c": code, "n": code},
    ).scalar_one()


def _metier(connexion: Connection, entite: uuid.UUID, code: str = "DEV") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO job_catalog (entity_id, code, label) VALUES (:e, :c, :l) RETURNING id"),
        {"e": entite, "c": code, "l": code},
    ).scalar_one()


def _dsm_habilite(connexion: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    """Une personne portant une responsabilite `DSM` ACTIVE dans l'entite.

    Indispensable : le declencheur `dsm_responsabilite_active` de `T8` est un
    `BEFORE`, donc il **masquerait** la cle etrangere s'il refusait la ligne.
    """
    personne = _personne(connexion, adresse)
    connexion.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :d)"
        ),
        {"p": personne, "e": entite, "d": JANVIER},
    )
    return personne


def _deux_entites(connexion: Connection) -> tuple[uuid.UUID, uuid.UUID]:
    return _entite(connexion, "BORDEAUX"), _entite(connexion, "LILLE")


# ---------------------------------------------------------------------------
#  La liste des chemins est DERIVEE, pas declaree de confiance
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_les_cles_composites_sont_toutes_couvertes(cx: Connection) -> None:
    """Le catalogue PostgreSQL fait foi, et `COUVERTURE` doit l'egaler exactement.

    **CE TEST EST LE PLUS IMPORTANT DU FICHIER.** Sans lui, les huit tests
    suivants prouveraient huit refus sans rien dire du neuvieme chemin qu'une
    sous-etape ulterieure ouvrirait. Une cle composite ajoutee sans test le fera
    echouer ; une cle retiree aussi.
    """
    locales = {
        ligne[0]
        for ligne in cx.execute(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema='public' AND column_name='entity_id'"
            )
        )
    }
    reelles: set[tuple[str, str]] = set()
    for source, cible, colonnes in cx.execute(
        text(
            "SELECT c.conrelid::regclass::text, c.confrelid::regclass::text, "
            "(SELECT string_agg(a.attname, ',') FROM unnest(c.conkey) AS k(att) "
            "   JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.att) "
            "FROM pg_constraint c WHERE c.contype='f'"
        )
    ):
        if cible == "entity" or source not in locales or cible not in locales:
            continue
        if "entity_id" in colonnes.split(","):
            reelles.add((source, cible))

    manquants = reelles - set(COUVERTURE)
    disparus = set(COUVERTURE) - reelles
    assert not manquants, f"cle(s) composite(s) SANS test de refus : {sorted(manquants)}"
    assert not disparus, f"test(s) portant sur une cle composite disparue : {sorted(disparus)}"
    #  **HUIT AU LOT 2, NEUF DEPUIS `T1` DU LOT 5.** Le nombre est ecrit, et c'est
    #  delibere : sa mise a jour est ce qui force la decision. Une cle composite
    #  ajoutee sans test ferait echouer ce test, et c'est son objet.
    assert len(reelles) == len(COUVERTURE) == 9, f"{len(reelles)} chemins, 9 attendus"


# ---------------------------------------------------------------------------
#  Les huit refus, chacun avec son temoin
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_un_cercle_d_une_autre_entite_est_refuse(cx: Connection) -> None:
    bordeaux, lille = _deux_entites(cx)
    appartenance = _appartenance(cx, bordeaux, "a@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
                "membership_type, starts_at) VALUES (:e, :a, :c, 'principal', :d)"
            ),
            {"e": bordeaux, "a": appartenance, "c": _cercle(cx, lille), "d": JANVIER},
        )
    assert "fk_circle_membership_circle" in str(echec.value)


@pytest.mark.integration
def test_un_cercle_de_LA_MEME_entite_est_accepte(cx: Connection) -> None:
    """Temoin du precedent."""
    bordeaux, _ = _deux_entites(cx)
    cx.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :a, :c, 'principal', :d)"
        ),
        {
            "e": bordeaux,
            "a": _appartenance(cx, bordeaux, "a@exalt.com"),
            "c": _cercle(cx, bordeaux),
            "d": JANVIER,
        },
    )
    assert cx.execute(text("SELECT count(*) FROM circle_membership")).scalar_one() == 1


@pytest.mark.integration
def test_une_appartenance_d_une_autre_entite_dans_un_cercle_est_refusee(cx: Connection) -> None:
    bordeaux, lille = _deux_entites(cx)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
                "membership_type, starts_at) VALUES (:e, :a, :c, 'principal', :d)"
            ),
            {
                "e": bordeaux,
                "a": _appartenance(cx, lille, "a@exalt.com"),
                "c": _cercle(cx, bordeaux),
                "d": JANVIER,
            },
        )
    assert "fk_circle_membership_entity_membership" in str(echec.value)


@pytest.mark.integration
def test_un_consultant_d_une_autre_entite_est_refuse(cx: Connection) -> None:
    """Et le DSM est HABILITE dans l'entite, pour que la cle etrangere parle."""
    bordeaux, lille = _deux_entites(cx)
    dsm = _dsm_habilite(cx, bordeaux, "dsm@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
                "starts_at) VALUES (:e, :a, :d, :debut)"
            ),
            {
                "e": bordeaux,
                "a": _appartenance(cx, lille, "c@exalt.com"),
                "d": dsm,
                "debut": JANVIER,
            },
        )
    assert "fk_dsm_assignment_entity_membership" in str(echec.value)


@pytest.mark.integration
def test_un_consultant_de_LA_MEME_entite_est_accepte(cx: Connection) -> None:
    """Temoin : la meme insertion, le consultant etant de l'entite."""
    bordeaux, _ = _deux_entites(cx)
    cx.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at) VALUES (:e, :a, :d, :debut)"
        ),
        {
            "e": bordeaux,
            "a": _appartenance(cx, bordeaux, "c@exalt.com"),
            "d": _dsm_habilite(cx, bordeaux, "dsm@exalt.com"),
            "debut": JANVIER,
        },
    )
    assert cx.execute(text("SELECT count(*) FROM dsm_assignment")).scalar_one() == 1


@pytest.mark.integration
def test_un_BOOSTER_sur_un_cercle_d_une_autre_entite_est_refuse(cx: Connection) -> None:
    bordeaux, lille = _deux_entites(cx)
    personne = _personne(cx, "b@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'BOOSTER', :c, :p, :d)"
            ),
            {"p": personne, "e": bordeaux, "c": _cercle(cx, lille), "d": JANVIER},
        )
    assert "fk_framework_responsibility_circle" in str(echec.value)


@pytest.mark.integration
def test_un_OFFICE_MANAGER_sur_un_bureau_d_une_autre_entite_est_refuse(cx: Connection) -> None:
    bordeaux, lille = _deux_entites(cx)
    personne = _personne(cx, "om@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, office_id, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'OFFICE_MANAGER', :o, :p, :d)"
            ),
            {"p": personne, "e": bordeaux, "o": _bureau(cx, lille), "d": JANVIER},
        )
    assert "fk_framework_responsibility_office" in str(echec.value)


@pytest.mark.integration
def test_un_BOOSTER_sur_un_cercle_de_SA_entite_est_accepte(cx: Connection) -> None:
    """Temoin des deux precedents."""
    bordeaux, _ = _deux_entites(cx)
    personne = _personne(cx, "b@exalt.com")
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'BOOSTER', :c, :p, :d)"
        ),
        {"p": personne, "e": bordeaux, "c": _cercle(cx, bordeaux), "d": JANVIER},
    )
    total = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment")
    ).scalar_one()
    assert total == 1


@pytest.mark.integration
def test_un_metier_d_une_autre_entite_est_refuse(cx: Connection) -> None:
    """Un SEUL des deux bouts est croise, pour que la cle visee soit celle qui parle."""
    bordeaux, lille = _deux_entites(cx)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO membership_job_assignment (entity_id, entity_membership_id, "
                "job_catalog_id, starts_at) VALUES (:e, :a, :m, :d)"
            ),
            {
                "e": bordeaux,
                "a": _appartenance(cx, bordeaux, "a@exalt.com"),
                "m": _metier(cx, lille),
                "d": JANVIER,
            },
        )
    assert "fk_membership_job_assignment_job_catalog" in str(echec.value)


@pytest.mark.integration
def test_un_metier_attribue_a_une_appartenance_d_une_autre_entite_est_refuse(
    cx: Connection,
) -> None:
    bordeaux, lille = _deux_entites(cx)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO membership_job_assignment (entity_id, entity_membership_id, "
                "job_catalog_id, starts_at) VALUES (:e, :a, :m, :d)"
            ),
            {
                "e": bordeaux,
                "a": _appartenance(cx, lille, "a@exalt.com"),
                "m": _metier(cx, bordeaux),
                "d": JANVIER,
            },
        )
    assert "fk_membership_job_assignment_entity_membership" in str(echec.value)


@pytest.mark.integration
def test_un_metier_et_une_appartenance_de_LA_MEME_entite_sont_acceptes(cx: Connection) -> None:
    """Temoin des deux precedents."""
    bordeaux, _ = _deux_entites(cx)
    cx.execute(
        text(
            "INSERT INTO membership_job_assignment (entity_id, entity_membership_id, "
            "job_catalog_id, starts_at) VALUES (:e, :a, :m, :d)"
        ),
        {
            "e": bordeaux,
            "a": _appartenance(cx, bordeaux, "a@exalt.com"),
            "m": _metier(cx, bordeaux),
            "d": JANVIER,
        },
    )
    assert cx.execute(text("SELECT count(*) FROM membership_job_assignment")).scalar_one() == 1


@pytest.mark.integration
def test_une_situation_sur_une_appartenance_d_une_autre_entite_est_refusee(
    cx: Connection,
) -> None:
    """`intercontract` SANS client : aucun declencheur ne se reveille.

    Une ligne `mission` ferait parler `mission_client_actif_dans_l_entite`, pose en
    `T10`, **avant** la cle etrangere -- c'est l'ombrage du §7.21.
    """
    bordeaux, lille = _deux_entites(cx)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
                "status, starts_at) VALUES (:e, :a, 'intercontract', :d)"
            ),
            {"e": bordeaux, "a": _appartenance(cx, lille, "a@exalt.com"), "d": JANVIER},
        )
    assert "fk_professional_status_assignment_entity_membership" in str(echec.value)


@pytest.mark.integration
def test_une_situation_sur_une_appartenance_de_SA_entite_est_acceptee(cx: Connection) -> None:
    """Temoin du precedent."""
    bordeaux, _ = _deux_entites(cx)
    cx.execute(
        text(
            "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
            "status, starts_at) VALUES (:e, :a, 'intercontract', :d)"
        ),
        {"e": bordeaux, "a": _appartenance(cx, bordeaux, "a@exalt.com"), "d": JANVIER},
    )
    total = cx.execute(text("SELECT count(*) FROM professional_status_assignment")).scalar_one()
    assert total == 1


# ---------------------------------------------------------------------------
#  Ce que la cle etrangere ne peut PAS porter, et qui le porte
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_une_personne_d_une_autre_entite_reste_referencable_ET_C_EST_VOULU(
    cx: Connection,
) -> None:
    """`person` est GLOBALE — `ARB-DATA-001` — donc ce n'est PAS une fuite.

    Une personne n'appartient a aucune entite : c'est son APPARTENANCE qui est
    locale. Refuser une personne « d'une autre entite » n'aurait aucun sens, et
    poser une cle composite vers `person` serait impossible : elle ne porte pas
    d'`entity_id`.

    **Ce test existe pour que l'absence de contrainte soit un CHOIX LISIBLE**, et
    non un trou qu'on decouvrirait au LOT 3.
    """
    bordeaux, lille = _deux_entites(cx)
    personne = _personne(cx, "mobile@exalt.com")
    #  DEUX APPARTENANCES SEQUENTIELLES, et le sequentiel n'est pas un
    #  contournement : c'est le cas reel. L'exclusion `ex_entity_membership_sans_
    #  chevauchement` de `T4` porte sur `(person_id, period)` SANS clause `WHERE`,
    #  donc deux appartenances qui se CHEVAUCHENT sont refusees quelle que soit
    #  l'entite -- ce qui est la regle « une seule appartenance occupante » du
    #  §6.2. Ma premiere version laissait les deux periodes non bornees, donc
    #  toujours en chevauchement, et echouait sur un livrable conforme.
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "departure_date, membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2024-01-01', '2025-12-31', 'archived', 'consultant', 'draft')"
        ),
        {"p": personne, "e": bordeaux},
    )
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft')"
        ),
        {"p": personne, "e": lille},
    )
    entites = cx.execute(
        text("SELECT count(DISTINCT entity_id) FROM entity_membership WHERE person_id = :p"),
        {"p": personne},
    ).scalar_one()
    assert entites == 2, "une personne GLOBALE peut avoir appartenu a deux entites"


@pytest.mark.integration
def test_un_client_NON_ACTIVE_localement_est_refuse_par_un_DECLENCHEUR(cx: Connection) -> None:
    """`client` est GLOBALE : la cle etrangere ne peut rien dire de l'entite.

    Le chemin est ferme, mais **par le declencheur de `T10`**, pas par une cle
    composite. Ce test le montre pour que le rapport d'isolation dise vrai : neuf
    cles pointent vers une table globale, et celle-ci est la seule dont le modele
    exige une condition de meme entite (§6.5).
    """
    bordeaux, lille = _deux_entites(cx)
    appartenance = _appartenance(cx, bordeaux, "c@exalt.com")
    client = cx.execute(
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES ('acme', 'Acme', 'active') RETURNING id"
        )
    ).scalar_one()
    #  Active dans LILLE seulement.
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": lille, "c": client},
    )
    with pytest.raises(IntegrityError) as echec:
        cx.execute(
            text(
                "INSERT INTO professional_status_assignment (entity_id, entity_membership_id, "
                "status, client_id, starts_at) VALUES (:e, :a, 'mission', :c, :d)"
            ),
            {"e": bordeaux, "a": appartenance, "c": client, "d": JANVIER},
        )
    assert "une mission exige un client active dans cette entite" in str(echec.value)


# ---------------------------------------------------------------------------
#  Un garde-fou MECANIQUE contre une erreur commise trois fois
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_aucun_parametre_lie_ne_couvre_deux_colonnes_de_TYPES_DIFFERENTS(
    cx: Connection,
) -> None:
    """Defaut `T4-2`, rejoue en `T8-3`, puis une TROISIEME fois en `T11-2`.

    **UN PARAMETRE LIE PARTAGE PAR DEUX COLONNES DE TYPES DIFFERENTS REND
    « inconsistent types deduced for parameter $1 ».** L'erreur ne nomme ni la
    table ni la colonne : elle parle d'un numero de parametre.

    LE DISCRIMINANT EST LE TYPE, ET IL N'EST PAS DANS LE TEXTE SOURCE. Mesure du
    20/08/2026 : `entity.code` est `character varying(64)` quand `display_name` et
    `city` sont `text` -- d'ou l'echec. Mais `person.email` et `email_normalized`
    sont tous deux `character varying(320)`, et `person_id` et
    `assigned_by_person_id` tous deux `uuid` : ces reutilisations sont LEGITIMES.

    **DEUX VERSIONS SYNTAXIQUES DE CE GARDE-FOU ONT ECHOUE SUR DU CODE CONFORME**
    -- l'une se declenchait sur un commentaire, l'autre sur `:p` employe pour deux
    colonnes `uuid`. Un garde-fou a faux positifs est PIRE qu'aucun garde-fou : il
    apprend a passer outre, exactement comme l'avertissement faux de `make destroy`
    au §7.21. Une heuristique dans un controle est un defaut -- lecon `T9-2`.

    Ce test lit donc les TYPES dans le catalogue PostgreSQL, et n'echoue que sur la
    forme reellement fautive.
    """
    types: dict[tuple[str, str], str] = {
        (table, colonne): type_sql
        for table, colonne, type_sql in cx.execute(
            text(
                "SELECT table_name, column_name, data_type || "
                "coalesce('(' || character_maximum_length || ')', '') "
                "FROM information_schema.columns WHERE table_schema='public'"
            )
        )
    }
    assert len(types) > 100, f"{len(types)} colonnes lues, le schema en porte plus"

    #  `ast` PLUTOT QU'UN BALAYAGE DU FICHIER, et le motif est celui du §7.2 : la
    #  version precedente lisait tout le source et trouvait **son propre temoin**,
    #  une chaine deliberement fautive ecrite quelques lignes plus bas. `ast` ne
    #  rend que les chaines reellement passees a `text(...)` : ni la prose, ni les
    #  commentaires, ni le temoin n'y sont.
    arbre = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    requetes: list[str] = []
    for noeud in ast.walk(arbre):
        if not (isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name)):
            continue
        if noeud.func.id != "text":
            continue
        for argument in noeud.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                requetes.append(argument.value)
    assert len(requetes) >= 20, f"{len(requetes)} requetes trouvees, le fichier en porte plus"

    insertions: list[tuple[str, str, str]] = []
    for requete in requetes:
        insertions += re.findall(r"INSERT INTO (\w+) \(([^)]*)\)[^(]*VALUES \(([^)]*)\)", requete)
    assert len(insertions) >= 10, f"{len(insertions)} insertions trouvees, le fichier en porte plus"

    fautives: list[str] = []
    for table, colonnes_brutes, valeurs_brutes in insertions:
        colonnes = [c.strip() for c in colonnes_brutes.split(",")]
        valeurs = [v.strip() for v in valeurs_brutes.split(",")]
        if len(colonnes) != len(valeurs):
            continue  # une valeur composee, hors du perimetre de ce garde-fou
        par_parametre: dict[str, set[str]] = {}
        for colonne, valeur in zip(colonnes, valeurs, strict=True):
            if not valeur.startswith(":"):
                continue
            type_sql = types.get((table, colonne))
            if type_sql is not None:
                par_parametre.setdefault(valeur, set()).add(type_sql)
        for parametre, vus in par_parametre.items():
            if len(vus) > 1:
                fautives.append(f"{table} {parametre} couvre {sorted(vus)}")

    assert not fautives, (
        "parametre(s) lie(s) sur des colonnes de TYPES DIFFERENTS : "
        + "; ".join(fautives)
        + ". Donne un nom distinct par colonne."
    )

    #  TEMOIN : le controle sait-il voir la forme fautive ? Sans lui, un motif
    #  casse ferait passer ce test sur n'importe quel fichier.
    temoin = re.findall(
        r"INSERT INTO (\w+) \(([^)]*)\)[^(]*VALUES \(([^)]*)\)",
        "INSERT INTO entity (code, display_name) VALUES (:x, :x)",
    )
    assert temoin, "le motif ne reconnait plus une insertion"
    table_t, cols_t, vals_t = temoin[0]
    vus_t = {
        types[(table_t, c.strip())]
        for c, v in zip(cols_t.split(","), vals_t.split(","), strict=True)
        if v.strip() == ":x"
    }
    assert len(vus_t) > 1, (
        "le temoin devrait voir DEUX types pour `:x` — sans cela le controle ne discrimine rien"
    )
