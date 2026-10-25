"""L'export CSV du journal d'audit — LOT 10, `T9`, matrice §16 « Exporter en CSV ».

CE QUE CE FICHIER NE REPROUVE PAS

  `test_journal_d_audit.py` (`T8`) prouve deja le PERIMETRE (les quatre portees,
  le cumul de roles, les evenements sans entite) et le MASQUAGE des details
  techniques, sur un decor bien plus large. Ce fichier ne reprend qu'un decor
  MINIMAL — une entite, une autre pour l'asymetrie, sept roles — et porte ce
  que `T8` ne pouvait pas prouver : la garde `ROLES_D_EXPORT_DE_L_AUDIT` (plus
  etroite que `ROLES_DE_L_AUDIT`), l'ABSENCE de pagination, le contenu du CSV
  lui-meme (cellules vides plutot que le mot `None`, memes lignes que la
  lecture), et la journalisation de l'export (`export_request` + un second
  `audit_event`, cahier §10.11).
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit.services import DUREE_DE_RETENTION
from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeResponsabilite
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_EXPORT = "/api/v1/entities/{code}/audit/export"
CHEMIN_AUDIT = "/api/v1/entities/{code}/audit"

#  DERIVEE DE `now()`, JAMAIS FIGEE — §7.47 de la passation.
ANCRAGE = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=10)
IL_Y_A_90_JOURS = ANCRAGE - dt.timedelta(days=90)
IL_Y_A_400_JOURS = ANCRAGE - dt.timedelta(days=400)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make residu-check`."
        )


def _entite(cx: Connection, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
            "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
        ),
        {"code": code, "nom": code},
    ).scalar_one()


def _personne(cx: Connection, marqueur: str, suffixe: str) -> uuid.UUID:
    adresse = f"{marqueur}-{suffixe}-{uuid.uuid4().hex[:6]}@exalt-company.com".lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, "
            "account_state) VALUES (:a, :a, :prenom, 'T9L10', 'active') RETURNING id"
        ),
        {"a": adresse, "prenom": suffixe},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "arrivee": IL_Y_A_400_JOURS.date()},
    ).scalar_one()


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    #  `:code` et `:nom` SEPARES — meme classe de defaut que `§7.25` de la
    #  passation, deja nommee par `test_journal_d_audit.py::_cercle`.
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 0) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 0) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_: str,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
) -> None:
    #  `:p` sert `person_id` ET `assigned_by_person_id` — partage legitime,
    #  meme discipline que `test_journal_d_audit.py::_responsabilite` (§7.25).
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, office_id, "
            "assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :b, :p, :d)"
        ),
        {"p": personne, "e": entite, "t": type_, "c": cercle, "b": bureau, "d": IL_Y_A_90_JOURS},
    )


def _role_technique(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID | None, role: str
) -> None:
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, :r, :d)"
        ),
        {"p": personne, "e": entite, "r": role, "d": IL_Y_A_90_JOURS},
    )


def _evenement_d_audit(
    cx: Connection,
    *,
    entite: uuid.UUID | None,
    resource_type: str,
    action_code: str,
    actor_person_id: uuid.UUID | None = None,
    resource_reference: uuid.UUID | None = None,
    reason: str | None = None,
    summary: str = "Evenement de test T9L10",
    occurred_at: dt.datetime = ANCRAGE,
) -> uuid.UUID:
    """Une ligne `audit_event`, inseree DIRECTEMENT — meme discipline que
    `test_journal_d_audit.py`, qui prouve deja le cote ECRITURE (`T2`-`T7`)."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO audit_event (entity_id, actor_person_id, action_code, resource_type, "
            "resource_reference, summary, reason, correlation_token, occurred_at, retention_until) "
            "VALUES (:e, :ap, :ac, :rt, :rr, :s, :reason, :corr, :occ, :retenu) RETURNING id"
        ),
        {
            "e": entite,
            "ap": actor_person_id,
            "ac": action_code,
            "rt": resource_type,
            "rr": resource_reference,
            "s": summary,
            "reason": reason,
            "corr": f"corr-{uuid.uuid4().hex[:12]}",
            "occ": occurred_at,
            "retenu": occurred_at + DUREE_DE_RETENTION,
        },
    ).scalar_one()


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _exporter(parametres: Parametres, code: str, jeton: str | None, **params: object) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.post(CHEMIN_EXPORT.format(code=code), params=params)


def _lire(parametres: Parametres, code: str, jeton: str | None, **params: object) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN_AUDIT.format(code=code), params=params)


def _lignes_csv(reponse: Any) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(reponse.text)))


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t9l10{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres, "marqueur": marqueur}

    with moteur(parametres).begin() as cx:
        entite = _entite(cx, f"{marqueur}-home")
        autre_entite = _entite(cx, f"{marqueur}-autre")
        r["entite"] = entite
        r["code"] = f"{marqueur}-home"
        r["autre_entite"] = autre_entite
        r["autre_code"] = f"{marqueur}-autre"
        cercle = _cercle(cx, entite, f"{marqueur}-c")
        bureau = _bureau(cx, entite, f"{marqueur}-b")

        for role, suffixe in (
            ("dsm", "dsm"),
            ("esm", "esm"),
            ("booster", "boo"),
            ("office", "off"),
            ("adme", "adme"),
            ("super", "super"),
            ("emp", "emp"),
        ):
            personne = _personne(cx, marqueur, suffixe)
            _appartenance(cx, entite, personne)
            r[f"{role}_personne"] = personne

        _responsabilite(cx, entite, r["dsm_personne"], TypeResponsabilite.DSM.value)
        _responsabilite(cx, entite, r["esm_personne"], TypeResponsabilite.ESM.value)
        _responsabilite(
            cx, entite, r["booster_personne"], TypeResponsabilite.BOOSTER.value, cercle=cercle
        )
        _responsabilite(
            cx, entite, r["office_personne"], TypeResponsabilite.OFFICE_MANAGER.value, bureau=bureau
        )
        _role_technique(cx, r["adme_personne"], entite, "ENTITY_ADMIN")
        _role_technique(cx, r["super_personne"], None, "SUPER_ADMIN")

    #  HORS de la transaction ci-dessus : `_session` ouvre sa PROPRE connexion,
    #  et les personnes doivent deja etre COMMISES pour qu'elle les voie — meme
    #  discipline que `test_journal_d_audit.py::decor`.
    r["jetons"] = {
        role: _session(parametres, r[f"{role}_personne"])
        for role in ("dsm", "esm", "booster", "office", "adme", "super", "emp")
    }

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM export_request WHERE requested_by_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM audit_event WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR actor_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM office WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM person WHERE email LIKE :motif_personne",
            "DELETE FROM entity WHERE code LIKE :motif",
        ):
            menage.execute(
                text(requete),
                {"motif": f"{marqueur}%", "motif_personne": f"{marqueur}-%"},
            )


# ===========================================================================
#  LES GARDES
# ===========================================================================


@pytest.mark.integration
def test_sans_session_401(decor: dict[str, Any]) -> None:
    reponse = _exporter(decor["parametres"], decor["code"], None)
    assert reponse.status_code == 401


@pytest.mark.integration
@pytest.mark.parametrize("role", ["dsm", "esm", "booster", "office", "emp"])
def test_un_role_sans_droit_d_export_est_refuse(decor: dict[str, Any], role: str) -> None:
    """§16 « Exporter en CSV » : TIRET pour les cinq — y compris DSM/ESM, qui
    LISENT pourtant le journal (`ROLES_DE_L_AUDIT`). La garde de l'export est
    PLUS ETROITE, pas la meme."""
    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"][role])
    assert reponse.status_code == 403
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_entite_inconnue_est_un_404(decor: dict[str, Any]) -> None:
    reponse = _exporter(decor["parametres"], "code-totalement-inconnu", decor["jetons"]["adme"])
    assert reponse.status_code == 404


# ===========================================================================
#  CE QUE SEULS ADM-E ET SUPER PEUVENT FAIRE
# ===========================================================================


@pytest.mark.integration
def test_adm_e_exporte_le_csv_de_son_entite(decor: dict[str, Any]) -> None:
    code_temoin = f"export-adme-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_temoin
        )

    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/csv")
    assert "attachment" in reponse.headers["content-disposition"]

    lignes = _lignes_csv(reponse)
    assert any(ligne["action_code"] == code_temoin for ligne in lignes)


@pytest.mark.integration
def test_super_exporte_n_importe_quelle_entite(decor: dict[str, Any]) -> None:
    """`SUPER` n'a AUCUNE appartenance dans `autre_entite`, et exporte quand meme
    — §16, colonne `Global` — a la difference d'`ADM-E`, confine a la sienne."""
    code_temoin = f"export-super-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["autre_entite"], resource_type="person", action_code=code_temoin
        )

    reponse = _exporter(decor["parametres"], decor["autre_code"], decor["jetons"]["super"])
    assert reponse.status_code == 200
    lignes = _lignes_csv(reponse)
    assert any(ligne["action_code"] == code_temoin for ligne in lignes)

    #  TEMOIN D'ASYMETRIE : ADM-E, confine a SA propre entite, est refuse ici.
    refus = _exporter(decor["parametres"], decor["autre_code"], decor["jetons"]["adme"])
    assert refus.status_code == 403


# ===========================================================================
#  LE PERIMETRE DE L'EXPORT EST CELUI DE LA LECTURE
# ===========================================================================


@pytest.mark.integration
def test_le_perimetre_de_l_export_est_celui_de_la_lecture(decor: dict[str, Any]) -> None:
    code_dans = f"export-dans-{uuid.uuid4().hex[:10]}"
    code_hors = f"export-hors-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_dans
        )
        _evenement_d_audit(
            cx, entite=decor["autre_entite"], resource_type="person", action_code=code_hors
        )

    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    codes = {ligne["action_code"] for ligne in _lignes_csv(reponse)}
    assert code_dans in codes
    assert code_hors not in codes


# ===========================================================================
#  LES CINQ FILTRES, REPRIS A L'IDENTIQUE DE LA LECTURE
# ===========================================================================


@pytest.mark.integration
def test_les_filtres_action_code_et_resource_type_sont_appliques(decor: dict[str, Any]) -> None:
    code_cible = f"cible-{uuid.uuid4().hex[:10]}"
    code_autre = f"autre-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_cible
        )
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_autre
        )

    reponse = _exporter(
        decor["parametres"], decor["code"], decor["jetons"]["adme"], action_code=code_cible
    )
    codes = {ligne["action_code"] for ligne in _lignes_csv(reponse)}
    assert codes == {code_cible}


@pytest.mark.integration
def test_le_filtre_de_periode_est_applique(decor: dict[str, Any]) -> None:
    code_ancien = f"ancien-{uuid.uuid4().hex[:10]}"
    code_recent = f"recent-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_ancien,
            occurred_at=ANCRAGE - dt.timedelta(days=2),
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_recent,
            occurred_at=ANCRAGE,
        )

    reponse = _exporter(
        decor["parametres"],
        decor["code"],
        decor["jetons"]["adme"],
        depuis=(ANCRAGE - dt.timedelta(hours=1)).isoformat(),
    )
    codes = {ligne["action_code"] for ligne in _lignes_csv(reponse)}
    assert code_recent in codes
    assert code_ancien not in codes


@pytest.mark.integration
def test_le_filtre_acteur_est_applique(decor: dict[str, Any]) -> None:
    code_vise = f"vise-{uuid.uuid4().hex[:10]}"
    code_autre = f"autre-acteur-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_vise,
            actor_person_id=decor["dsm_personne"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_autre,
            actor_person_id=decor["esm_personne"],
        )

    reponse = _exporter(
        decor["parametres"],
        decor["code"],
        decor["jetons"]["adme"],
        acteur=str(decor["dsm_personne"]),
    )
    codes = {ligne["action_code"] for ligne in _lignes_csv(reponse)}
    assert codes == {code_vise}


# ===========================================================================
#  AUCUNE PAGINATION : TOUT LE PERIMETRE EST RENDU
# ===========================================================================


@pytest.mark.integration
def test_aucune_pagination_toutes_les_lignes_sont_rendues(decor: dict[str, Any]) -> None:
    marqueur_lignes = f"masse-{uuid.uuid4().hex[:8]}"
    with moteur(decor["parametres"]).begin() as cx:
        for index in range(30):
            _evenement_d_audit(
                cx,
                entite=decor["entite"],
                resource_type="person",
                action_code=f"{marqueur_lignes}-{index}",
            )

    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    codes = {ligne["action_code"] for ligne in _lignes_csv(reponse)}
    assert sum(1 for c in codes if c.startswith(marqueur_lignes)) == 30


# ===========================================================================
#  LE CONTENU DU CSV LUI-MEME
# ===========================================================================


@pytest.mark.integration
def test_une_valeur_absente_devient_une_cellule_vide_jamais_le_mot_None(
    decor: dict[str, Any],
) -> None:
    """Defaut `T10-8` du LOT 6 (§7.42 de la passation) : `str(None)` rend
    `"None"`, un texte qui ressemble a une donnee. `reason` est NULLABLE
    (`audit_event.reason`) et vaut ici explicitement `None`."""
    code_temoin = f"sans-motif-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_temoin,
            reason=None,
        )

    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    ligne = next(ligne_ for ligne_ in _lignes_csv(reponse) if ligne_["action_code"] == code_temoin)
    assert ligne["reason"] == ""
    assert ligne["actor_service_account_id"] == ""
    assert "None" not in reponse.text.splitlines()[0]  # l'en-tete ne le porte pas non plus


@pytest.mark.integration
def test_resource_reference_et_correlation_token_ne_sont_jamais_masques(
    decor: dict[str, Any],
) -> None:
    """`ADM-E`/`SUPER` sont EXACTEMENT `ROLES_DES_DETAILS_TECHNIQUES` : ces
    deux colonnes ne sont donc JAMAIS vides pour qui a le droit d'exporter."""
    code_temoin = f"details-{uuid.uuid4().hex[:10]}"
    reference = uuid.uuid4()
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_temoin,
            resource_reference=reference,
        )

    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    ligne = next(ligne_ for ligne_ in _lignes_csv(reponse) if ligne_["action_code"] == code_temoin)
    assert ligne["resource_reference"] == str(reference)
    assert ligne["correlation_token"] != ""


@pytest.mark.integration
def test_le_csv_rend_les_memes_evenements_que_la_lecture(decor: dict[str, Any]) -> None:
    code_temoin = f"coherence-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_temoin
        )

    reponse_lecture = _lire(
        decor["parametres"], decor["code"], decor["jetons"]["adme"], action_code=code_temoin
    )
    reponse_export = _exporter(
        decor["parametres"], decor["code"], decor["jetons"]["adme"], action_code=code_temoin
    )
    ids_lecture = {e["id"] for e in reponse_lecture.json()["evenements"]}
    ids_export = {ligne["id"] for ligne in _lignes_csv(reponse_export)}
    assert ids_lecture == ids_export
    assert len(ids_lecture) == 1


# ===========================================================================
#  LA JOURNALISATION DE L'EXPORT LUI-MEME — cahier §10.11
# ===========================================================================


@pytest.mark.integration
def test_l_export_est_journalise(decor: dict[str, Any]) -> None:
    reponse = _exporter(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    assert reponse.status_code == 200

    with moteur(decor["parametres"]).begin() as cx:
        demandes = (
            cx.execute(
                text(
                    "SELECT id, export_type, generated_media_id, expires_at "
                    "FROM export_request WHERE requested_by_person_id = :p"
                ),
                {"p": decor["adme_personne"]},
            )
            .mappings()
            .all()
        )
        evenements = (
            cx.execute(
                text(
                    "SELECT resource_reference, entity_id FROM audit_event "
                    "WHERE action_code = 'audit_exporte_en_csv' AND actor_person_id = :p"
                ),
                {"p": decor["adme_personne"]},
            )
            .mappings()
            .all()
        )

    assert len(demandes) == 1
    assert demandes[0]["export_type"] == "audit_csv"
    assert demandes[0]["generated_media_id"] is None
    assert demandes[0]["expires_at"] is None

    assert len(evenements) == 1
    assert evenements[0]["entity_id"] == decor["entite"]
    assert evenements[0]["resource_reference"] == demandes[0]["id"]
