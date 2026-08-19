"""Cercles, bureaux et appartenance aux cercles — modele §8.1 a §8.3.

LOT 2, sous-etape `T7`, stories `MVP-L02-US001` et `US003`.

LE PIEGE DE CETTE SOUS-ETAPE EST UN CONTRESENS POSSIBLE, ET DEUX TESTS L'ECARTENT.
Le §8.2 autorise « plusieurs cercles secondaires actifs ». Une contrainte
d'exclusion posee sans clause `WHERE` les interdirait tous sauf un, et le livrable
paraitrait correct : il refuserait quelque chose, simplement pas ce qu'il faut.
`test_plusieurs_cercles_SECONDAIRES_actifs_sont_autorises` est ce qui l'attrape.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import Parametres
from app.organization import TYPES_APPARTENANCE_CERCLE
from app.shared.database import moteur

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
MARS = dt.datetime(2026, 3, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)


def test_les_deux_types_du_modele() -> None:
    """§8.2 : « `membership_type` | `principal` ou `secondary` »."""
    assert TYPES_APPARTENANCE_CERCLE == ("principal", "secondary")


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
            "VALUES (:a, :b, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"a": adresse, "b": adresse},
    ).scalar_one()
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _cercle(connexion: Connection, entite: uuid.UUID, code: str = "TECH") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, color_token) "
            "VALUES (:e, :code, :nom, 'marque.bleu') RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code.title()},
    ).scalar_one()


def _bureau(connexion: Connection, entite: uuid.UUID, code: str = "BDX1") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO office (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code.title()},
    ).scalar_one()


def _rattacher(
    connexion: Connection,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    cercle: uuid.UUID,
    *,
    type_: str = "principal",
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at, ends_at) VALUES (:e, :a, :c, :t, :debut, :fin)"
        ),
        {"e": entite, "a": appartenance, "c": cercle, "t": type_, "debut": debut, "fin": fin},
    )


# ----------------------------------------------------------------------------
#  §8.1 et §8.3 — cercles et bureaux
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_cercle_et_un_bureau_se_creent(cx: Connection) -> None:
    entite = _entite(cx)
    _cercle(cx, entite)
    _bureau(cx, entite)
    cercle = cx.execute(text("SELECT code, color_token, display_order FROM circle")).one()
    assert cercle.code == "TECH"
    assert cercle.color_token == "marque.bleu", (
        "une REFERENCE de couleur, non une valeur hexadecimale : le design system "
        "de packages/ui porte les couleurs et leurs contrastes mesures"
    )
    assert cercle.display_order == 0
    assert cx.execute(text("SELECT location_text FROM office")).scalar_one() is None


@pytest.mark.integration
def test_le_code_de_cercle_et_de_bureau_est_unique_dans_l_entite(cx: Connection) -> None:
    entite = _entite(cx)
    _cercle(cx, entite, "TECH")
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _cercle(cx, entite, "TECH")
    assert "uq_circle_entity_id_code_non_archive" in str(echec.value)
    _bureau(cx, entite, "BDX1")
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _bureau(cx, entite, "BDX1")
    assert "uq_office_entity_id_code_non_archive" in str(echec.value)


@pytest.mark.integration
def test_le_meme_code_existe_dans_DEUX_entites(cx: Connection) -> None:
    """Temoin : cercles et bureaux sont LOCAUX, l'unicite porte sur le couple."""
    _cercle(cx, _entite(cx, "BORDEAUX"), "TECH")
    _cercle(cx, _entite(cx, "LILLE"), "TECH")
    assert cx.execute(text("SELECT count(*) FROM circle")).scalar_one() == 2


@pytest.mark.integration
def test_un_cercle_archive_libere_son_code(cx: Connection) -> None:
    """§25.1 : l'index est PARTIEL, `WHERE archived_at IS NULL`."""
    entite = _entite(cx)
    premier = _cercle(cx, entite, "TECH")
    cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": premier})
    _cercle(cx, entite, "TECH")
    assert cx.execute(text("SELECT count(*) FROM circle")).scalar_one() == 2


# ----------------------------------------------------------------------------
#  §8.2 — LE PIEGE : un seul principal, mais PLUSIEURS secondaires
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_seul_cercle_PRINCIPAL_actif(cx: Connection) -> None:
    """§25.1 : `WHERE membership_type='principal' AND ends_at IS NULL`."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _rattacher(cx, entite, appartenance, _cercle(cx, entite, "TECH"))
    with pytest.raises(IntegrityError) as echec:
        _rattacher(cx, entite, appartenance, _cercle(cx, entite, "DATA"))
    #  Le refus vient de l'exclusion PARTIELLE ou de l'index, les deux couvrant ce
    #  cas -- l'index etant ombrage. Ce qui compte est qu'une des DEUX regles du
    #  cercle principal refuse, et non une autre contrainte.
    message = str(echec.value)
    assert (
        "uq_circle_membership_principal_actif" in message
        or "ex_circle_membership_principal_sans_chevauchement" in message
    ), f"refus attendu du cercle principal, obtenu : {message[:200]}"


@pytest.mark.integration
def test_plusieurs_cercles_SECONDAIRES_actifs_sont_autorises(cx: Connection) -> None:
    """§8.2, litteralement : « plusieurs cercles secondaires actifs autorises ».

    **C'EST LE TEST QUI ECARTE LE CONTRESENS DE CETTE SOUS-ETAPE.** Une contrainte
    d'exclusion posee sans clause `WHERE` sur `(entity_membership_id, period)` les
    interdirait tous sauf un -- et le livrable paraitrait correct, puisqu'il
    refuserait bien quelque chose. Simplement pas ce qu'il faut.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _rattacher(cx, entite, appartenance, _cercle(cx, entite, "TECH"), type_="principal")
    for code in ("DATA", "CLOUD", "IA"):
        _rattacher(cx, entite, appartenance, _cercle(cx, entite, code), type_="secondary")
    total = cx.execute(text("SELECT count(*) FROM circle_membership")).scalar_one()
    assert total == 4, "un principal et TROIS secondaires, tous actifs"


@pytest.mark.integration
def test_deux_relations_actives_au_MEME_cercle_sont_refusees(cx: Connection) -> None:
    """§8.2 : « une meme personne ne peut pas avoir deux relations actives identiques ».

    Regle DISTINCTE des deux precedentes, et elle vaut pour les DEUX types : ici
    deux relations `secondary` au meme cercle.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    cercle = _cercle(cx, entite, "DATA")
    _rattacher(cx, entite, appartenance, cercle, type_="secondary")
    with pytest.raises(IntegrityError) as echec:
        _rattacher(cx, entite, appartenance, cercle, type_="secondary")
    assert "uq_circle_membership_cercle_actif" in str(echec.value)


@pytest.mark.integration
def test_un_cercle_principal_CLOS_coexiste_avec_un_nouveau(cx: Connection) -> None:
    """Temoin : le §2.3 veut l'historisation, pas l'ecrasement."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _rattacher(cx, entite, appartenance, _cercle(cx, entite, "TECH"), debut=JANVIER, fin=JUIN)
    _rattacher(cx, entite, appartenance, _cercle(cx, entite, "DATA"), debut=JUIN, fin=None)
    assert cx.execute(text("SELECT count(*) FROM circle_membership")).scalar_one() == 2


@pytest.mark.integration
def test_deux_periodes_de_cercle_PRINCIPAL_qui_se_chevauchent_sont_refusees(
    cx: Connection,
) -> None:
    """§25.2, « cercle principal ». L'exclusion PARTIELLE."""
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _rattacher(cx, entite, appartenance, _cercle(cx, entite, "TECH"), debut=JANVIER, fin=JUIN)
    with pytest.raises(IntegrityError) as echec:
        _rattacher(cx, entite, appartenance, _cercle(cx, entite, "DATA"), debut=MARS, fin=DECEMBRE)
    assert "ex_circle_membership_principal_sans_chevauchement" in str(echec.value)


@pytest.mark.integration
def test_deux_periodes_SECONDAIRES_qui_se_chevauchent_sont_ACCEPTEES(cx: Connection) -> None:
    """Second temoin du contresens : l'exclusion ne touche PAS les secondaires.

    Sans la clause `WHERE` de l'exclusion, ce test echouerait -- et c'est ce qui le
    rend utile.
    """
    entite = _entite(cx)
    appartenance = _appartenance(cx, entite, "jean@exalt.com")
    _rattacher(
        cx,
        entite,
        appartenance,
        _cercle(cx, entite, "DATA"),
        type_="secondary",
        debut=JANVIER,
        fin=JUIN,
    )
    _rattacher(
        cx,
        entite,
        appartenance,
        _cercle(cx, entite, "CLOUD"),
        type_="secondary",
        debut=MARS,
        fin=DECEMBRE,
    )
    assert cx.execute(text("SELECT count(*) FROM circle_membership")).scalar_one() == 2


@pytest.mark.integration
def test_un_cercle_d_une_AUTRE_entite_est_refuse(cx: Connection) -> None:
    """§8.2 : « le cercle de la MEME entite ». Cle composite du §25.3."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    appartenance = _appartenance(cx, bordeaux, "jean@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        _rattacher(cx, bordeaux, appartenance, _cercle(cx, lille, "TECH"))
    assert "fk_circle_membership_circle" in str(echec.value)


@pytest.mark.integration
def test_un_type_hors_liste_est_refuse(cx: Connection) -> None:
    entite = _entite(cx)
    with pytest.raises(IntegrityError) as echec:
        _rattacher(
            cx,
            entite,
            _appartenance(cx, entite, "jean@exalt.com"),
            _cercle(cx, entite),
            type_="referent",
        )
    assert "membership_type_valide" in str(echec.value)


# ----------------------------------------------------------------------------
#  §8.1 et §25.4 — l'archivage d'un cercle, et son residuel nomme
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_archiver_un_cercle_a_MEMBRES_ACTIFS_est_refuse(cx: Connection) -> None:
    """§8.1 et §25.4. Regle INTER-TABLES, donc portee par declencheur."""
    entite = _entite(cx)
    cercle = _cercle(cx, entite, "TECH")
    _rattacher(cx, entite, _appartenance(cx, entite, "jean@exalt.com"), cercle)
    with pytest.raises(IntegrityError) as echec:
        cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": cercle})
    assert "impossible d'archiver un cercle comportant des membres actifs" in str(echec.value)


@pytest.mark.integration
def test_archiver_un_cercle_SANS_membre_actif_est_permis(cx: Connection) -> None:
    """Premier temoin : le declencheur ne refuse pas tout archivage."""
    entite = _entite(cx)
    cercle = _cercle(cx, entite, "TECH")
    cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": cercle})
    assert cx.execute(text("SELECT archived_at FROM circle")).scalar_one() is not None


@pytest.mark.integration
def test_archiver_un_cercle_aux_membres_CLOS_est_permis(cx: Connection) -> None:
    """Second temoin : « actif » se lit « sans fin », pas « a jamais existe »."""
    entite = _entite(cx)
    cercle = _cercle(cx, entite, "TECH")
    _rattacher(
        cx,
        entite,
        _appartenance(cx, entite, "jean@exalt.com"),
        cercle,
        debut=JANVIER,
        fin=JUIN,
    )
    cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": cercle})
    assert cx.execute(text("SELECT archived_at FROM circle")).scalar_one() is not None


@pytest.mark.integration
def test_le_RESIDUEL_est_nomme_ajouter_un_membre_a_un_cercle_archive(cx: Connection) -> None:
    """CE TEST DOCUMENTE UNE LIMITE, IL NE CELEBRE PAS UN SUCCES.

    Le §8.1 enonce la regle dans UN SEUL SENS : on ne peut pas archiver un cercle
    qui a des membres actifs. Il ne dit PAS qu'on ne peut pas ajouter un membre
    actif a un cercle DEJA archive. L'invariant « archive implique aucun membre
    actif » n'est donc pas globalement garanti, et ce test le MONTRE.

    **L'asymetrie est probablement deliberee** : pour `entity`, le §5.1 enonce
    explicitement les DEUX sens -- « une entite archivee ne recoit plus de nouveaux
    membres » -- et `DEC-506` l'applique. Le modele sait exprimer le sens inverse
    quand il le veut ; poser ici une regle qu'il n'ecrit pas serait inventer.

    **Si ce test se met un jour a echouer, c'est que quelqu'un a comble le
    residuel.** Il faudra alors le remplacer par son inverse ET tracer la decision,
    pas le supprimer.
    """
    entite = _entite(cx)
    cercle = _cercle(cx, entite, "TECH")
    cx.execute(text("UPDATE circle SET archived_at = now() WHERE id = :i"), {"i": cercle})

    _rattacher(cx, entite, _appartenance(cx, entite, "jean@exalt.com"), cercle)

    actifs = cx.execute(
        text(
            "SELECT count(*) FROM circle_membership cm JOIN circle c ON c.id = cm.circle_id "
            "WHERE c.archived_at IS NOT NULL AND cm.ends_at IS NULL"
        )
    ).scalar_one()
    assert actifs == 1, (
        "residuel nomme : un membre actif peut etre ajoute a un cercle archive. "
        "Le §8.1 n'enonce la regle que dans l'autre sens."
    )
