"""Creer un cercle/bureau et attribuer un Booster/responsable de bureau — LOT 11, `T3`.

Hors backlog (`docs/operations/fiche-lot-11.md` §1.2). Voir l'en-tete
d'`app/organization/creation.py` pour les arbitrages (remplacement du Booster,
ajout sans remplacement pour un responsable de bureau, borne « un a trois » qui
ne mord pas a l'attribution).

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. les TEMOINS positifs : un cercle et un bureau se creent, un Booster et un
     responsable de bureau s'attribuent ;
  2. le conflit de code a la creation (§25.1) ;
  3. le REMPLACEMENT du Booster : l'actif est ferme (`ends_at` pose), le
     nouveau est actif, et designer la personne DEJA Booster est un NO-OP —
     aucune ligne de plus ;
  4. « une personne ne peut pas etre Booster active dans plusieurs entites »
     (declencheur `fn_booster_une_seule_entite`, modele §8.4) ;
  5. l'ATTRIBUTION d'un responsable de bureau AJOUTE, ne ferme JAMAIS un
     responsable existant — deux actifs simultanes sur le MEME bureau ;
  6. le refus d'un doublon exact (meme personne, meme bureau) ;
  7. la borne « un a trois » du §25.2/`DEC-583` NE MORD PAS a l'ecriture — un
     QUATRIEME responsable est accepte, temoin explicite plutot qu'un silence
     qui laisserait croire a une limite inventee (§6.5) ;
  8. le retrait, pour les deux types, et son refus quand rien n'est actif ou
     que l'identifiant ne designe pas la bonne ressource (§2.5, refus par
     defaut) ;
  9. chaque action ecrit EXACTEMENT un `audit_event`, avec le bon
     `action_code`/`resource_type`/`entity_id`, et le motif voyage dans
     `reason` — jamais dans `assignment_reason`, qui reste NULL (`ECART-064`).

Ce fichier ne reteste PAS `exiger_un_role_dans_l_entite` ni
`resoudre_les_permissions` : des briques generiques, deja prouvees ailleurs.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping

from app.configuration.settings import Parametres
from app.organization.creation import (
    CODE_AFFECTATION_INTROUVABLE,
    CODE_BOOSTER_ACTIF_AILLEURS,
    CODE_DEJA_RESPONSABLE,
    attribuer_le_booster,
    attribuer_un_responsable_de_bureau,
    creer_un_bureau,
    creer_un_cercle,
    retirer_le_booster,
    retirer_un_responsable_de_bureau,
)
from app.organization.cycle_de_vie import CODE_CODE_DEJA_PRIS
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L11T3"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
FEVRIER = dt.datetime(2026, 2, 1, tzinfo=dt.UTC)


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


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Creation', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": adresse, "s": suffixe},
    ).scalar_one()


def _evenement_d_audit(cx: Connection, *, resource_reference: uuid.UUID) -> RowMapping:
    return (
        cx.execute(
            text(
                "SELECT action_code, resource_type, entity_id, reason FROM audit_event "
                "WHERE resource_reference = :r"
            ),
            {"r": resource_reference},
        )
        .mappings()
        .one()
    )


# ===========================================================================
#  CREATION D'UN CERCLE / D'UN BUREAU
# ===========================================================================


@pytest.mark.integration
def test_TEMOIN_un_cercle_se_cree(cx: Connection) -> None:
    entite = _entite(cx, "C1")
    acteur = _personne(cx, "ESM1")

    cree = creer_un_cercle(
        cx,
        entite=entite,
        code="DATA",
        nom="Data",
        jeton_de_couleur="bleu",
        description="Le cercle Data",
        ordre_d_affichage=1,
        acteur=acteur,
        instant=JANVIER,
    )
    assert cree.code == "DATA"
    assert cree.version == 1

    ligne = cx.execute(
        text("SELECT code, name, color_token FROM circle WHERE id = :c"), {"c": cree.id}
    ).one()
    assert ligne == ("DATA", "Data", "bleu")

    evenement = _evenement_d_audit(cx, resource_reference=cree.id)
    assert evenement["action_code"] == "cercle_cree"
    assert evenement["resource_type"] == "circle"
    assert evenement["entity_id"] == entite
    assert evenement["reason"] is None


@pytest.mark.integration
def test_creer_un_cercle_avec_un_code_deja_pris_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "C2")
    acteur = _personne(cx, "ESM2")
    creer_un_cercle(
        cx,
        entite=entite,
        code="DOUBLON",
        nom="Un",
        jeton_de_couleur=None,
        description=None,
        ordre_d_affichage=0,
        acteur=acteur,
        instant=JANVIER,
    )

    with pytest.raises(ErreurApplicative) as excinfo:
        creer_un_cercle(
            cx,
            entite=entite,
            code="DOUBLON",
            nom="Deux",
            jeton_de_couleur=None,
            description=None,
            ordre_d_affichage=0,
            acteur=acteur,
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_CODE_DEJA_PRIS
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_TEMOIN_un_bureau_se_cree(cx: Connection) -> None:
    entite = _entite(cx, "B1")
    acteur = _personne(cx, "ESM3")

    cree = creer_un_bureau(
        cx,
        entite=entite,
        code="BDS",
        nom="BDS",
        description=None,
        localisation="Rue Sainte-Catherine",
        ordre_d_affichage=1,
        acteur=acteur,
        instant=JANVIER,
    )
    assert cree.code == "BDS"

    evenement = _evenement_d_audit(cx, resource_reference=cree.id)
    assert evenement["action_code"] == "bureau_cree"
    assert evenement["resource_type"] == "office"


@pytest.mark.integration
def test_creer_un_bureau_avec_un_code_deja_pris_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "B2")
    acteur = _personne(cx, "ESM4")
    creer_un_bureau(
        cx,
        entite=entite,
        code="DOUBLON-B",
        nom="Un",
        description=None,
        localisation=None,
        ordre_d_affichage=0,
        acteur=acteur,
        instant=JANVIER,
    )

    with pytest.raises(ErreurApplicative) as excinfo:
        creer_un_bureau(
            cx,
            entite=entite,
            code="DOUBLON-B",
            nom="Deux",
            description=None,
            localisation=None,
            ordre_d_affichage=0,
            acteur=acteur,
            instant=JANVIER,
        )
    assert excinfo.value.code == CODE_CODE_DEJA_PRIS
    assert excinfo.value.statut == 409


# ===========================================================================
#  ATTRIBUTION ET RETRAIT DU BOOSTER — TOUJOURS UN REMPLACEMENT
# ===========================================================================


@pytest.mark.integration
def test_TEMOIN_le_premier_booster_s_attribue(cx: Connection) -> None:
    entite = _entite(cx, "BO1")
    cercle = _cercle(cx, entite, "CERCLE-BO1")
    acteur = _personne(cx, "ESM-BO1")
    booster = _personne(cx, "BOOSTER1")

    attribue = attribuer_le_booster(
        cx, entite=entite, cercle=cercle, personne=booster, acteur=acteur, instant=JANVIER
    )
    assert attribue.remplace is False

    ligne = cx.execute(
        text("SELECT person_id, ends_at FROM framework_responsibility_assignment WHERE id = :a"),
        {"a": attribue.affectation},
    ).one()
    assert ligne == (booster, None)

    evenement = _evenement_d_audit(cx, resource_reference=attribue.affectation)
    assert evenement["action_code"] == "booster_attribue"
    assert evenement["resource_type"] == "framework_responsibility_assignment"
    assert evenement["entity_id"] == entite


@pytest.mark.integration
def test_attribuer_le_booster_a_la_MEME_personne_est_un_no_op(cx: Connection) -> None:
    entite = _entite(cx, "BO2")
    cercle = _cercle(cx, entite, "CERCLE-BO2")
    acteur = _personne(cx, "ESM-BO2")
    booster = _personne(cx, "BOOSTER2")

    premiere = attribuer_le_booster(
        cx, entite=entite, cercle=cercle, personne=booster, acteur=acteur, instant=JANVIER
    )
    seconde = attribuer_le_booster(
        cx, entite=entite, cercle=cercle, personne=booster, acteur=acteur, instant=FEVRIER
    )
    assert seconde.affectation == premiere.affectation
    assert seconde.remplace is False

    #  Une seule ligne active, aucune de plus : pas de periode d'une microseconde.
    total = cx.execute(
        text(
            "SELECT count(*) FROM framework_responsibility_assignment "
            "WHERE circle_id = :c AND responsibility_type = 'BOOSTER'"
        ),
        {"c": cercle},
    ).scalar_one()
    assert total == 1


@pytest.mark.integration
def test_attribuer_le_booster_REMPLACE_l_actif(cx: Connection) -> None:
    entite = _entite(cx, "BO3")
    cercle = _cercle(cx, entite, "CERCLE-BO3")
    acteur = _personne(cx, "ESM-BO3")
    ancien = _personne(cx, "ANCIEN-BOOSTER")
    nouveau = _personne(cx, "NOUVEAU-BOOSTER")

    premiere = attribuer_le_booster(
        cx, entite=entite, cercle=cercle, personne=ancien, acteur=acteur, instant=JANVIER
    )
    seconde = attribuer_le_booster(
        cx, entite=entite, cercle=cercle, personne=nouveau, acteur=acteur, instant=FEVRIER
    )
    assert seconde.remplace is True
    assert seconde.affectation != premiere.affectation

    fermee = cx.execute(
        text("SELECT ends_at FROM framework_responsibility_assignment WHERE id = :a"),
        {"a": premiere.affectation},
    ).scalar_one()
    assert fermee == FEVRIER

    active = cx.execute(
        text(
            "SELECT person_id FROM framework_responsibility_assignment "
            "WHERE circle_id = :c AND responsibility_type = 'BOOSTER' AND ends_at IS NULL"
        ),
        {"c": cercle},
    ).scalar_one()
    assert active == nouveau


@pytest.mark.integration
def test_une_personne_deja_booster_actif_AILLEURS_est_refusee_en_409(cx: Connection) -> None:
    entite_a = _entite(cx, "BO4A")
    entite_b = _entite(cx, "BO4B")
    cercle_a = _cercle(cx, entite_a, "CERCLE-A")
    cercle_b = _cercle(cx, entite_b, "CERCLE-B")
    acteur = _personne(cx, "ESM-BO4")
    booster = _personne(cx, "BOOSTER-NOMADE")

    attribuer_le_booster(
        cx, entite=entite_a, cercle=cercle_a, personne=booster, acteur=acteur, instant=JANVIER
    )

    with pytest.raises(ErreurApplicative) as excinfo:
        attribuer_le_booster(
            cx, entite=entite_b, cercle=cercle_b, personne=booster, acteur=acteur, instant=JANVIER
        )
    assert excinfo.value.code == CODE_BOOSTER_ACTIF_AILLEURS
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_retirer_le_booster_ferme_l_actif(cx: Connection) -> None:
    entite = _entite(cx, "BO5")
    cercle = _cercle(cx, entite, "CERCLE-BO5")
    acteur = _personne(cx, "ESM-BO5")
    booster = _personne(cx, "BOOSTER5")

    attribue = attribuer_le_booster(
        cx, entite=entite, cercle=cercle, personne=booster, acteur=acteur, instant=JANVIER
    )
    retire = retirer_le_booster(cx, entite=entite, cercle=cercle, acteur=acteur, instant=FEVRIER)
    assert retire == attribue.affectation

    ends_at = cx.execute(
        text("SELECT ends_at FROM framework_responsibility_assignment WHERE id = :a"),
        {"a": attribue.affectation},
    ).scalar_one()
    assert ends_at == FEVRIER

    #  DEUX evenements existent desormais pour cette ligne : attribution ET
    #  retrait partagent la MEME `resource_reference` — `_evenement_d_audit`
    #  (`.one()`) leverait donc une erreur ici. On verifie le COMPTE et le
    #  DERNIER plutot.
    action_codes = [
        ligne[0]
        for ligne in cx.execute(
            text(
                "SELECT action_code FROM audit_event WHERE resource_reference = :r "
                "ORDER BY occurred_at ASC"
            ),
            {"r": attribue.affectation},
        ).all()
    ]
    assert action_codes == ["booster_attribue", "booster_retire"]


@pytest.mark.integration
def test_retirer_le_booster_SANS_actif_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "BO6")
    cercle = _cercle(cx, entite, "CERCLE-BO6")
    acteur = _personne(cx, "ESM-BO6")

    with pytest.raises(ErreurApplicative) as excinfo:
        retirer_le_booster(cx, entite=entite, cercle=cercle, acteur=acteur, instant=JANVIER)
    assert excinfo.value.code == CODE_AFFECTATION_INTROUVABLE
    assert excinfo.value.statut == 409


# ===========================================================================
#  ATTRIBUTION ET RETRAIT D'UN RESPONSABLE DE BUREAU — AJOUTE, NE REMPLACE JAMAIS
# ===========================================================================


@pytest.mark.integration
def test_TEMOIN_un_responsable_de_bureau_s_attribue(cx: Connection) -> None:
    entite = _entite(cx, "RE1")
    bureau = _bureau(cx, entite, "BUREAU-RE1")
    acteur = _personne(cx, "ESM-RE1")
    responsable = _personne(cx, "RESPONSABLE1")

    attribue = attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau, personne=responsable, acteur=acteur, instant=JANVIER
    )

    ligne = cx.execute(
        text("SELECT person_id, ends_at FROM framework_responsibility_assignment WHERE id = :a"),
        {"a": attribue.affectation},
    ).one()
    assert ligne == (responsable, None)

    evenement = _evenement_d_audit(cx, resource_reference=attribue.affectation)
    assert evenement["action_code"] == "responsable_de_bureau_attribue"


@pytest.mark.integration
def test_deux_responsables_actifs_coexistent_sur_le_MEME_bureau(cx: Connection) -> None:
    entite = _entite(cx, "RE2")
    bureau = _bureau(cx, entite, "BUREAU-RE2")
    acteur = _personne(cx, "ESM-RE2")
    premier = _personne(cx, "RESPONSABLE-A")
    second = _personne(cx, "RESPONSABLE-B")

    attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau, personne=premier, acteur=acteur, instant=JANVIER
    )
    attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau, personne=second, acteur=acteur, instant=JANVIER
    )

    total = cx.execute(
        text(
            "SELECT count(*) FROM framework_responsibility_assignment "
            "WHERE office_id = :b AND responsibility_type = 'OFFICE_MANAGER' AND ends_at IS NULL"
        ),
        {"b": bureau},
    ).scalar_one()
    assert total == 2


@pytest.mark.integration
def test_un_QUATRIEME_responsable_de_bureau_est_ACCEPTE(cx: Connection) -> None:
    """La borne « un a trois » ne mord pas a l'ecriture — `DEC-583`, voir l'en-tete."""
    entite = _entite(cx, "RE3")
    bureau = _bureau(cx, entite, "BUREAU-RE3")
    acteur = _personne(cx, "ESM-RE3")

    for suffixe in ("A", "B", "C", "D"):
        attribuer_un_responsable_de_bureau(
            cx,
            entite=entite,
            bureau=bureau,
            personne=_personne(cx, f"RESP-{suffixe}"),
            acteur=acteur,
            instant=JANVIER,
        )

    total = cx.execute(
        text(
            "SELECT count(*) FROM framework_responsibility_assignment "
            "WHERE office_id = :b AND responsibility_type = 'OFFICE_MANAGER' AND ends_at IS NULL"
        ),
        {"b": bureau},
    ).scalar_one()
    assert total == 4


@pytest.mark.integration
def test_attribuer_un_responsable_DEJA_actif_est_refuse_en_409(cx: Connection) -> None:
    entite = _entite(cx, "RE4")
    bureau = _bureau(cx, entite, "BUREAU-RE4")
    acteur = _personne(cx, "ESM-RE4")
    responsable = _personne(cx, "RESPONSABLE4")

    attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau, personne=responsable, acteur=acteur, instant=JANVIER
    )
    with pytest.raises(ErreurApplicative) as excinfo:
        attribuer_un_responsable_de_bureau(
            cx, entite=entite, bureau=bureau, personne=responsable, acteur=acteur, instant=JANVIER
        )
    assert excinfo.value.code == CODE_DEJA_RESPONSABLE
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_retirer_un_responsable_de_bureau_ferme_la_bonne_ligne(cx: Connection) -> None:
    entite = _entite(cx, "RE5")
    bureau = _bureau(cx, entite, "BUREAU-RE5")
    acteur = _personne(cx, "ESM-RE5")
    premier = _personne(cx, "RESP-GARDE")
    second = _personne(cx, "RESP-RETIRE")

    garde = attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau, personne=premier, acteur=acteur, instant=JANVIER
    )
    retire = attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau, personne=second, acteur=acteur, instant=JANVIER
    )

    fermee = retirer_un_responsable_de_bureau(
        cx,
        entite=entite,
        bureau=bureau,
        affectation=retire.affectation,
        acteur=acteur,
        instant=FEVRIER,
    )
    assert fermee == retire.affectation

    lignes = cx.execute(
        text("SELECT id, ends_at FROM framework_responsibility_assignment WHERE id = ANY(:ids)"),
        {"ids": [garde.affectation, retire.affectation]},
    ).all()
    etats: dict[uuid.UUID, dt.datetime | None] = {ligne[0]: ligne[1] for ligne in lignes}
    assert etats[garde.affectation] is None
    assert etats[retire.affectation] == FEVRIER


@pytest.mark.integration
def test_retirer_un_responsable_D_UN_AUTRE_bureau_est_refuse_en_409(cx: Connection) -> None:
    """§2.5, refus par defaut : un identifiant d'une AUTRE ressource n'est pas accepte."""
    entite = _entite(cx, "RE6")
    bureau_a = _bureau(cx, entite, "BUREAU-RE6A")
    bureau_b = _bureau(cx, entite, "BUREAU-RE6B")
    acteur = _personne(cx, "ESM-RE6")
    responsable = _personne(cx, "RESP-CROISE")

    attribue = attribuer_un_responsable_de_bureau(
        cx, entite=entite, bureau=bureau_a, personne=responsable, acteur=acteur, instant=JANVIER
    )

    with pytest.raises(ErreurApplicative) as excinfo:
        retirer_un_responsable_de_bureau(
            cx,
            entite=entite,
            bureau=bureau_b,
            affectation=attribue.affectation,
            acteur=acteur,
            instant=FEVRIER,
        )
    assert excinfo.value.code == CODE_AFFECTATION_INTROUVABLE
    assert excinfo.value.statut == 409


@pytest.mark.integration
def test_le_motif_voyage_dans_l_audit_jamais_dans_assignment_reason(cx: Connection) -> None:
    """`ECART-064`, `DEC-661` : meme discipline que toute route depuis LOT 10 `T7`."""
    entite = _entite(cx, "MOT1")
    cercle = _cercle(cx, entite, "CERCLE-MOT1")
    acteur = _personne(cx, "SUPER-MOT1")
    booster = _personne(cx, "BOOSTER-MOT1")

    attribue = attribuer_le_booster(
        cx,
        entite=entite,
        cercle=cercle,
        personne=booster,
        acteur=acteur,
        instant=JANVIER,
        motif="Intervention du super-administrateur, demande de Jonathan",
    )

    assignment_reason = cx.execute(
        text("SELECT assignment_reason FROM framework_responsibility_assignment WHERE id = :a"),
        {"a": attribue.affectation},
    ).scalar_one()
    assert assignment_reason is None

    reason = cx.execute(
        text("SELECT reason FROM audit_event WHERE resource_reference = :r"),
        {"r": attribue.affectation},
    ).scalar_one()
    assert reason == "Intervention du super-administrateur, demande de Jonathan"
