"""Responsabilites Framework, DSM et roles techniques — modele §8.4 a §8.6.

LOT 2, sous-etape `T8`, story `MVP-L02-US004`.

DEUX PERMISSIONS ET DEUX INTERDICTIONS VOISINES, ET LES CONFONDRE SERAIT INVISIBLE.

  permission    « une personne peut etre Booster de PLUSIEURS CERCLES d'une meme
                entite » (§8.4)
  interdiction  « une personne ne peut pas etre Booster active dans PLUSIEURS
                ENTITES simultanement » (§8.4)
  permission    « un DSM peut suivre PLUSIEURS CONSULTANTS » (§8.5)
  interdiction  « un consultant actif possede un seul DSM actif » (§8.5)

Un index unique naif sur `person_id` casserait les deux permissions, et le livrable
paraitrait correct puisqu'il refuserait bien quelque chose.

ET UN TEST PROUVE LA CORRECTION D'UN DEFAUT PLUS SUBTIL :
`test_deux_responsabilites_DSM_qui_se_chevauchent_sont_refusees`. Ma premiere
version mettait `circle_id` dans une exclusion unique -- or il est NUL pour un
`DSM`, et l'operateur `=` ne rapproche jamais deux NULL. La contrainte existait
sans rien garantir sur trois types sur quatre.
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
from app.organization import TYPES_RESPONSABILITE, TYPES_ROLE_TECHNIQUE
from app.shared.database import moteur

JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
JUIN = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
MARS = dt.datetime(2026, 3, 1, tzinfo=dt.UTC)
DECEMBRE = dt.datetime(2026, 12, 1, tzinfo=dt.UTC)


def test_les_enumerations_du_modele_en_MAJUSCULES() -> None:
    """§8.4 et §8.6 les ecrivent en majuscules, contrairement au reste du lot.

    La casse est une DECISION DU MODELE, et le §25.1 les cite ainsi :
    `responsibility_type = 'BOOSTER'`. Le motif de validation du socle a du etre
    elargi en `T8` : il exigeait des minuscules, ce qui etait juste pour `T2` a
    `T7` et faux ici. Son objet n'a jamais ete la casse mais la surete du SQL.
    """
    assert TYPES_RESPONSABILITE == ("DSM", "ESM", "BOOSTER", "OFFICE_MANAGER")
    assert TYPES_ROLE_TECHNIQUE == ("ENTITY_ADMIN", "SUPER_ADMIN")


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


def _personne(connexion: Connection, adresse: str) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:a, :b, 'Jean', 'Dupont', 'active') RETURNING id"
        ),
        {"a": adresse, "b": adresse},
    ).scalar_one()


def _appartenance(connexion: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _cercle(connexion: Connection, entite: uuid.UUID, code: str = "TECH") -> uuid.UUID:
    """UN PARAMETRE PAR COLONNE, et j'ai rejoue le defaut `T4-2` avant de le corriger.

    `code` est un `varchar(64)`, `name` un `text` : reutiliser `:c` pour les deux
    fait echouer PostgreSQL sur « inconsistent types deduced for parameter $2 ».
    **Le piege etait deja documente en `T4`, et je l'ai refait** -- ce qui confirme
    le §12 de la passation : un piege documente n'est pas un piege desarme.
    """
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(connexion: Connection, entite: uuid.UUID, code: str = "BDX1") -> uuid.UUID:
    return connexion.execute(  # type: ignore[no-any-return]
        text("INSERT INTO office (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _responsabilite(
    connexion: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_: str,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
    par: uuid.UUID | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, office_id, assigned_by_person_id, "
            "starts_at, ends_at) VALUES (:p, :e, :t, :c, :b, :par, :debut, :fin)"
        ),
        {
            "p": personne,
            "e": entite,
            "t": type_,
            "c": cercle,
            "b": bureau,
            "par": par or personne,
            "debut": debut,
            "fin": fin,
        },
    )


def _dsm(
    connexion: Connection,
    entite: uuid.UUID,
    consultant: uuid.UUID,
    dsm: uuid.UUID,
    *,
    debut: dt.datetime = JANVIER,
    fin: dt.datetime | None = None,
) -> None:
    connexion.execute(
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, dsm_person_id, "
            "starts_at, ends_at) VALUES (:e, :c, :d, :debut, :fin)"
        ),
        {"e": entite, "c": consultant, "d": dsm, "debut": debut, "fin": fin},
    )


# ----------------------------------------------------------------------------
#  §8.4 — les trois regles de portee
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_la_portee_est_imposee_par_le_type(cx: Connection) -> None:
    """§8.4 : trois règles de portée, en une contrainte."""
    entite = _entite(cx)
    personne = _personne(cx, "resp@exalt.com")
    cercle, bureau = _cercle(cx, entite), _bureau(cx, entite)
    fautifs = (
        ("BOOSTER", None, None),
        ("BOOSTER", cercle, bureau),
        ("OFFICE_MANAGER", None, None),
        ("OFFICE_MANAGER", cercle, None),
        ("DSM", cercle, None),
        ("ESM", None, bureau),
    )
    for type_, c, b in fautifs:
        with pytest.raises(IntegrityError) as echec, cx.begin_nested():
            _responsabilite(cx, entite, personne, type_, cercle=c, bureau=b)
        assert "portee_selon_le_type" in str(echec.value), f"attendu un refus pour {type_}"


@pytest.mark.integration
def test_les_quatre_portees_valides_sont_acceptees(cx: Connection) -> None:
    """Temoin : les quatre formes legitimes du §8.4 passent."""
    entite = _entite(cx)
    valides = (
        ("DSM", None, None),
        ("ESM", None, None),
        ("BOOSTER", _cercle(cx, entite, "TECH"), None),
        ("OFFICE_MANAGER", None, _bureau(cx, entite, "BDX1")),
    )
    for indice, (type_, c, b) in enumerate(valides):
        _responsabilite(
            cx, entite, _personne(cx, f"r{indice}@exalt.com"), type_, cercle=c, bureau=b
        )
    total = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment")
    ).scalar_one()
    assert total == 4


# ----------------------------------------------------------------------------
#  §8.4 — Booster : une PERMISSION et une INTERDICTION voisines
# ----------------------------------------------------------------------------


@pytest.mark.integration
def test_un_cercle_a_un_SEUL_Booster_actif(cx: Connection) -> None:
    """§25.1, écrit littéralement, sur deux conditions."""
    entite = _entite(cx)
    cercle = _cercle(cx, entite)
    _responsabilite(cx, entite, _personne(cx, "a@exalt.com"), "BOOSTER", cercle=cercle)
    with pytest.raises(IntegrityError) as echec:
        _responsabilite(cx, entite, _personne(cx, "b@exalt.com"), "BOOSTER", cercle=cercle)
    assert "uq_framework_responsibility_booster_actif_par_cercle" in str(echec.value)


@pytest.mark.integration
def test_une_personne_PEUT_etre_Booster_de_plusieurs_cercles_d_une_MEME_entite(
    cx: Connection,
) -> None:
    """§8.4, litteralement : c'est une PERMISSION.

    Un index unique sur `person_id WHERE responsibility_type='BOOSTER' AND ends_at
    IS NULL` l'interdirait -- et le livrable paraitrait correct.
    """
    entite = _entite(cx)
    personne = _personne(cx, "booster@exalt.com")
    for code in ("TECH", "DATA", "CLOUD"):
        _responsabilite(cx, entite, personne, "BOOSTER", cercle=_cercle(cx, entite, code))
    total = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment")
    ).scalar_one()
    assert total == 3, "trois cercles, une seule personne, une seule entite"


@pytest.mark.integration
def test_une_personne_ne_peut_PAS_etre_Booster_dans_DEUX_entites(cx: Connection) -> None:
    """§8.4 : l'interdiction voisine, portee par DECLENCHEUR.

    **Un index unique ne sait pas l'exprimer** : il dirait « au plus une ligne »,
    alors que la regle dit « au plus une ENTITE distincte ».
    """
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    personne = _personne(cx, "booster@exalt.com")
    _responsabilite(cx, bordeaux, personne, "BOOSTER", cercle=_cercle(cx, bordeaux, "TECH"))
    with pytest.raises(IntegrityError) as echec:
        _responsabilite(cx, lille, personne, "BOOSTER", cercle=_cercle(cx, lille, "TECH"))
    assert "Booster active dans plusieurs entites" in str(echec.value)


@pytest.mark.integration
def test_un_Booster_CLOS_dans_une_entite_permet_un_nouveau_dans_une_autre(
    cx: Connection,
) -> None:
    """Temoin : le declencheur ne regarde que les responsabilites ACTIVES."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    personne = _personne(cx, "booster@exalt.com")
    _responsabilite(
        cx,
        bordeaux,
        personne,
        "BOOSTER",
        cercle=_cercle(cx, bordeaux, "TECH"),
        debut=JANVIER,
        fin=JUIN,
    )
    _responsabilite(cx, lille, personne, "BOOSTER", cercle=_cercle(cx, lille, "TECH"), debut=JUIN)
    total = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment")
    ).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_deux_responsabilites_DSM_qui_se_chevauchent_sont_refusees(cx: Connection) -> None:
    """CE TEST PROUVE LA CORRECTION D'UN DEFAUT QUI VALAIT TROIS TYPES SUR QUATRE.

    Ma premiere version posait UNE exclusion incluant `circle_id`. Or `circle_id`
    est NUL pour un `DSM`, et **l'operateur `=` ne rapproche jamais deux NULL** :
    deux `DSM` de la meme personne aux periodes qui se chevauchent n'auraient PAS
    ete detectes. La contrainte existait sans rien garantir.

    Trois exclusions PARTIELLES la remplacent, chacune sur une cle sans colonne
    nullable.
    """
    entite = _entite(cx)
    personne = _personne(cx, "dsm@exalt.com")
    _responsabilite(cx, entite, personne, "DSM", debut=JANVIER, fin=JUIN)
    with pytest.raises(IntegrityError) as echec:
        _responsabilite(cx, entite, personne, "DSM", debut=MARS, fin=DECEMBRE)
    assert "ex_framework_responsibility_assignment_sans_portee" in str(echec.value)


@pytest.mark.integration
def test_une_personne_peut_etre_DSM_ET_ESM_en_meme_temps(cx: Connection) -> None:
    """Temoin : l'exclusion porte sur le couple (personne, TYPE).

    Le §8.4 n'interdit pas de cumuler deux types differents. Une exclusion sur la
    seule personne l'aurait interdit.
    """
    entite = _entite(cx)
    personne = _personne(cx, "cumul@exalt.com")
    _responsabilite(cx, entite, personne, "DSM")
    _responsabilite(cx, entite, personne, "ESM")
    total = cx.execute(
        text("SELECT count(*) FROM framework_responsibility_assignment")
    ).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_un_cercle_d_une_AUTRE_entite_est_refuse(cx: Connection) -> None:
    """§25.3 : cle composite, meme si la colonne de portee est nullable."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    with pytest.raises(IntegrityError) as echec:
        _responsabilite(
            cx,
            bordeaux,
            _personne(cx, "a@exalt.com"),
            "BOOSTER",
            cercle=_cercle(cx, lille, "TECH"),
        )
    assert "fk_framework_responsibility_circle" in str(echec.value)


# ----------------------------------------------------------------------------
#  §8.5 — dsm_assignment
# ----------------------------------------------------------------------------


def _dsm_habilite(connexion: Connection, entite: uuid.UUID, adresse: str) -> uuid.UUID:
    """Une personne AVEC une responsabilite DSM active dans l'entite."""
    personne = _personne(connexion, adresse)
    _responsabilite(connexion, entite, personne, "DSM")
    return personne


@pytest.mark.integration
def test_le_DSM_doit_avoir_une_responsabilite_DSM_ACTIVE(cx: Connection) -> None:
    """§8.5, et « verification du role actif du DSM cible » du §25.4."""
    entite = _entite(cx)
    consultant = _appartenance(cx, entite, _personne(cx, "consultant@exalt.com"))
    sans_responsabilite = _personne(cx, "quelconque@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        _dsm(cx, entite, consultant, sans_responsabilite)
    assert "n'a pas de responsabilite DSM active dans cette entite" in str(echec.value)


@pytest.mark.integration
def test_un_DSM_habilite_est_accepte(cx: Connection) -> None:
    """Temoin du precedent."""
    entite = _entite(cx)
    consultant = _appartenance(cx, entite, _personne(cx, "consultant@exalt.com"))
    _dsm(cx, entite, consultant, _dsm_habilite(cx, entite, "dsm@exalt.com"))
    assert cx.execute(text("SELECT count(*) FROM dsm_assignment")).scalar_one() == 1


@pytest.mark.integration
def test_un_DSM_habilite_dans_une_AUTRE_entite_est_refuse(cx: Connection) -> None:
    """Second temoin : le declencheur verifie l'entite, pas seulement le role."""
    bordeaux, lille = _entite(cx, "BORDEAUX"), _entite(cx, "LILLE")
    consultant = _appartenance(cx, bordeaux, _personne(cx, "consultant@exalt.com"))
    dsm_de_lille = _dsm_habilite(cx, lille, "dsm@exalt.com")
    with pytest.raises(IntegrityError) as echec:
        _dsm(cx, bordeaux, consultant, dsm_de_lille)
    assert "n'a pas de responsabilite DSM active dans cette entite" in str(echec.value)


@pytest.mark.integration
def test_un_consultant_a_un_SEUL_DSM_actif(cx: Connection) -> None:
    """§25.1 et §8.5."""
    entite = _entite(cx)
    consultant = _appartenance(cx, entite, _personne(cx, "consultant@exalt.com"))
    _dsm(cx, entite, consultant, _dsm_habilite(cx, entite, "d1@exalt.com"))
    with pytest.raises(IntegrityError) as echec:
        _dsm(cx, entite, consultant, _dsm_habilite(cx, entite, "d2@exalt.com"))
    message = str(echec.value)
    assert (
        "uq_dsm_assignment_consultant_actif" in message
        or "ex_dsm_assignment_sans_chevauchement" in message
    ), f"refus attendu du consultant, obtenu : {message[:200]}"


@pytest.mark.integration
def test_un_DSM_PEUT_suivre_plusieurs_consultants(cx: Connection) -> None:
    """§8.5, litteralement : c'est une PERMISSION.

    Une unicite sur `dsm_person_id` l'aurait interdite.
    """
    entite = _entite(cx)
    dsm = _dsm_habilite(cx, entite, "dsm@exalt.com")
    for indice in range(3):
        consultant = _appartenance(cx, entite, _personne(cx, f"c{indice}@exalt.com"))
        _dsm(cx, entite, consultant, dsm)
    assert cx.execute(text("SELECT count(*) FROM dsm_assignment")).scalar_one() == 3


@pytest.mark.integration
def test_une_succession_de_DSM_est_acceptee(cx: Connection) -> None:
    """Temoin : le §2.3 veut l'historisation, pas l'ecrasement."""
    entite = _entite(cx)
    consultant = _appartenance(cx, entite, _personne(cx, "consultant@exalt.com"))
    _dsm(cx, entite, consultant, _dsm_habilite(cx, entite, "d1@exalt.com"), debut=JANVIER, fin=JUIN)
    _dsm(cx, entite, consultant, _dsm_habilite(cx, entite, "d2@exalt.com"), debut=JUIN)
    assert cx.execute(text("SELECT count(*) FROM dsm_assignment")).scalar_one() == 2


# ----------------------------------------------------------------------------
#  §8.6 — roles techniques
# ----------------------------------------------------------------------------


def _role(connexion: Connection, personne: uuid.UUID, role: str, entite: uuid.UUID | None) -> None:
    connexion.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, :r, now())"
        ),
        {"p": personne, "e": entite, "r": role},
    )


@pytest.mark.integration
def test_ENTITY_ADMIN_exige_une_entite_et_SUPER_ADMIN_l_interdit(cx: Connection) -> None:
    """§8.6, litteralement : `SUPER_ADMIN` est « globale, `entity_id` nul »."""
    entite = _entite(cx)
    personne = _personne(cx, "admin@exalt.com")
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _role(cx, personne, "ENTITY_ADMIN", None)
    assert "portee_selon_le_role" in str(echec.value)
    with pytest.raises(IntegrityError) as echec, cx.begin_nested():
        _role(cx, personne, "SUPER_ADMIN", entite)
    assert "portee_selon_le_role" in str(echec.value)


@pytest.mark.integration
def test_les_deux_roles_bien_formes_sont_acceptes(cx: Connection) -> None:
    """Temoin du precedent."""
    entite = _entite(cx)
    _role(cx, _personne(cx, "a@exalt.com"), "ENTITY_ADMIN", entite)
    _role(cx, _personne(cx, "b@exalt.com"), "SUPER_ADMIN", None)
    assert cx.execute(text("SELECT count(*) FROM technical_role_assignment")).scalar_one() == 2


@pytest.mark.integration
def test_une_personne_peut_administrer_DEUX_entites(cx: Connection) -> None:
    """`entity_id` entre dans la cle d'exclusion : le §8.6 ne l'interdit pas."""
    personne = _personne(cx, "admin@exalt.com")
    _role(cx, personne, "ENTITY_ADMIN", _entite(cx, "BORDEAUX"))
    _role(cx, personne, "ENTITY_ADMIN", _entite(cx, "LILLE"))
    assert cx.execute(text("SELECT count(*) FROM technical_role_assignment")).scalar_one() == 2
