"""Les alertes operationnelles — LOT 10, `T13`, matrice §17, `MVP-L10-US007`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. `resoudre_le_perimetre_des_alertes`/`a_la_lecture_complete` : purs,
     aucun plancher `Soi` (a la difference des signalements, `T12`) ;
  2. `ESM` lit TOUTES les alertes (ressource GLOBALE) en « Limite fonctionnel »
     — `source`/`empreinte` masques, jamais les colonnes metier ;
  3. `ADM-E` et `SUPER` lisent en detail complet — ET `ADM-E` y arrive en
     tenant son role dans N'IMPORTE QUELLE entite, pas seulement celle ou il
     a ete octroye (temoin direct de la resolution "n'importe ou") ;
  4. `DSM`/`BOOST`/`OFFICE` sont refuses (403) — AUCUN plancher Soi ;
  5. seuls `ADM-E`/`SUPER` acquittent, commentent et resolvent — `ESM` est
     refuse malgre sa lecture ;
  6. le cycle restreint deux transitions (acquittement depuis `open` SEUL,
     resolution depuis `open`/`acknowledged`) et n'en restreint PAS une
     troisieme (commenter, a tout etat) ;
  7. la version perimee est un 409, jamais un ecrasement silencieux (§18.4) ;
  8. AUCUN motif n'est jamais exige, meme pour `SUPER` — `ECART-064` ne
     s'applique jamais a une ressource sans entite (temoin positif, contraste
     direct avec `T12`) ;
  9. `lever_une_alerte` cree, est un no-op sur une alerte deja `open`, et
     ROUVRE (meme ligne, horodatages remis a `NULL`) une alerte recurrente —
     la demonstration du cahier Annexe C : « resolution puis reouverture
     automatique d'une alerte recurrente » ;
  10. le commentaire vit dans `alert_comment`, JAMAIS duplique dans
      `audit_event.reason` ;
  11. le refus CSRF (negatif) est apparie a chaque succes (positif, §7.39).

Ce fichier n'importe aucune fonction d'un autre fichier de test — les lignes
de decor sont inserees DIRECTEMENT, meme discipline que
`test_traitement_signalements.py`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit.modeles import EtatAlerte
from app.auth.csrf import EN_TETE_JETON, jeton_pour
from app.auth.sessions import empreinte_de_session, ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.support.perimetre_alertes import (
    PerimetreDesAlertes,
    a_la_lecture_complete,
    resoudre_le_perimetre_des_alertes,
)
from app.support.traitement_alertes import lever_une_alerte, resoudre_une_alerte

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_LISTE = "/api/v1/alerts"
CHEMIN_UNE_ALERTE = "/api/v1/alerts/{alerte}"
CHEMIN_COMMENTAIRES = "/api/v1/alerts/{alerte}/commentaires"
CHEMIN_ACQUITTEMENT = "/api/v1/alerts/{alerte}/acquittement"
CHEMIN_RESOLUTION = "/api/v1/alerts/{alerte}/resolution"

#  DERIVEE DE `now()`, JAMAIS FIGEE — §7.47 de la passation.
ANCRAGE = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=10)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


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
            "account_state) VALUES (:a, :a, :prenom, 'T13L10', 'active') RETURNING id"
        ),
        {"a": adresse, "prenom": suffixe},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> None:
    """Une appartenance OCCUPANTE — necessaire pour que `EMP` existe, pas pour
    `ADM-E`/`ESM`/`SUPER` ici (voir `app/support/perimetre_alertes.py` : les
    trois sont resolus SANS dependre d'une appartenance occupante)."""
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, :arrivee, 'active', 'consultant', 'draft')"
        ),
        {"p": personne, "e": entite, "arrivee": ANCRAGE.date()},
    )


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
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


def _role_technique(
    cx: Connection, personne: uuid.UUID, entite: uuid.UUID | None, role: str
) -> None:
    cx.execute(
        text(
            "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at) "
            "VALUES (:p, :e, :r, :d)"
        ),
        {"p": personne, "e": entite, "r": role, "d": ANCRAGE},
    )


def _responsabilite(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_: str,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, circle_id, office_id, "
            "assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :b, :p, :d)"
        ),
        {"p": personne, "e": entite, "t": type_, "c": cercle, "b": bureau, "d": ANCRAGE},
    )


def _alerte(
    cx: Connection,
    *,
    empreinte: str,
    severity: str = "ERROR",
    source: str = "worker",
    state: str = "open",
    acknowledged_at: dt.datetime | None = None,
    resolved_at: dt.datetime | None = None,
) -> uuid.UUID:
    """Une ligne `operational_alert`, inseree DIRECTEMENT — meme discipline
    que `test_traitement_signalements.py::_signalement`."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO operational_alert "
            "(severity, source, state, fingerprint, opened_at, acknowledged_at, resolved_at) "
            "VALUES (:sev, :src, :etat, :empreinte, :ouverte, :acquittee, :resolue) "
            "RETURNING id"
        ),
        {
            "sev": severity,
            "src": source,
            "etat": state,
            "empreinte": empreinte,
            "ouverte": ANCRAGE,
            "acquittee": acknowledged_at,
            "resolue": resolved_at,
        },
    ).scalar_one()


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _avec_jeton(client: TestClient, parametres: Parametres, jeton: str | None) -> None:
    if jeton is not None:
        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)


def _lister(parametres: Parametres, jeton: str | None, **params: object) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        _avec_jeton(client, parametres, jeton)
        return client.get(CHEMIN_LISTE, params=params)


def _une_alerte(parametres: Parametres, alerte: uuid.UUID, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        _avec_jeton(client, parametres, jeton)
        return client.get(CHEMIN_UNE_ALERTE.format(alerte=alerte))


def _commentaires(parametres: Parametres, alerte: uuid.UUID, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        _avec_jeton(client, parametres, jeton)
        return client.get(CHEMIN_COMMENTAIRES.format(alerte=alerte))


def _poster(
    parametres: Parametres,
    chemin: str,
    jeton: str | None,
    corps: dict[str, Any],
    *,
    avec_csrf: bool = True,
) -> Any:
    parametres_csrf = parametres.model_copy(update={"PUBLIC_BASE_URL": ORIGINE_DE_TEST})
    with TestClient(creer_application(parametres_csrf), base_url=ORIGINE_DE_TEST) as client:
        entetes: dict[str, str] = {}
        if avec_csrf:
            entetes["Origin"] = ORIGINE_DE_TEST
        if jeton is not None:
            client.cookies.set(parametres_csrf.SESSION_COOKIE_NAME, jeton)
            if avec_csrf:
                entetes[EN_TETE_JETON] = jeton_pour(
                    empreinte_de_session(jeton), parametres_csrf.APP_SECRET_KEY
                )
        return client.post(chemin, json=corps, headers=entetes)


def _acquitter(
    parametres: Parametres,
    alerte: uuid.UUID,
    jeton: str | None,
    version: int,
    *,
    avec_csrf: bool = True,
) -> Any:
    return _poster(
        parametres,
        CHEMIN_ACQUITTEMENT.format(alerte=alerte),
        jeton,
        {"version": version},
        avec_csrf=avec_csrf,
    )


def _commenter(
    parametres: Parametres,
    alerte: uuid.UUID,
    jeton: str | None,
    contenu: str,
    *,
    avec_csrf: bool = True,
) -> Any:
    return _poster(
        parametres,
        CHEMIN_COMMENTAIRES.format(alerte=alerte),
        jeton,
        {"contenu": contenu},
        avec_csrf=avec_csrf,
    )


def _resoudre(
    parametres: Parametres,
    alerte: uuid.UUID,
    jeton: str | None,
    version: int,
    commentaire: str | None = None,
    *,
    avec_csrf: bool = True,
) -> Any:
    corps: dict[str, Any] = {"version": version}
    if commentaire is not None:
        corps["commentaire"] = commentaire
    return _poster(
        parametres, CHEMIN_RESOLUTION.format(alerte=alerte), jeton, corps, avec_csrf=avec_csrf
    )


# ===========================================================================
#  `resoudre_le_perimetre_des_alertes`/`a_la_lecture_complete` — purs
# ===========================================================================


@pytest.mark.parametrize(
    ("roles", "attendu"),
    [
        (frozenset(), None),
        (frozenset({RoleDeLaMatrice.DSM}), None),
        (frozenset({RoleDeLaMatrice.BOOSTER}), None),
        (frozenset({RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}), None),
        (frozenset({RoleDeLaMatrice.EMPLOYE}), None),
        (frozenset({RoleDeLaMatrice.ESM}), PerimetreDesAlertes.LIMITE),
        (frozenset({RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE}), PerimetreDesAlertes.COMPLET),
        (frozenset({RoleDeLaMatrice.SUPER_ADMINISTRATEUR}), PerimetreDesAlertes.COMPLET),
        #  Cumul : le traitement l'emporte sur la lecture limitee.
        (
            frozenset({RoleDeLaMatrice.ESM, RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE}),
            PerimetreDesAlertes.COMPLET,
        ),
        (
            frozenset({RoleDeLaMatrice.DSM, RoleDeLaMatrice.SUPER_ADMINISTRATEUR}),
            PerimetreDesAlertes.COMPLET,
        ),
    ],
)
def test_resolution_du_perimetre(
    roles: frozenset[RoleDeLaMatrice], attendu: PerimetreDesAlertes | None
) -> None:
    assert resoudre_le_perimetre_des_alertes(roles=roles) is attendu


def test_seul_le_complet_montre_source_et_empreinte() -> None:
    assert a_la_lecture_complete(perimetre=PerimetreDesAlertes.COMPLET) is True
    assert a_la_lecture_complete(perimetre=PerimetreDesAlertes.LIMITE) is False


# ===========================================================================
#  Decor d'integration
# ===========================================================================


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t13l10{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres, "marqueur": marqueur}

    with moteur(parametres).begin() as cx:
        entite_a = _entite(cx, f"{marqueur}-a")
        entite_b = _entite(cx, f"{marqueur}-b")
        r["entite_a"] = entite_a
        r["entite_b"] = entite_b

        for role, suffixe in (
            ("dsm", "dsm"),
            ("esm", "esm"),
            ("booster", "boo"),
            ("office", "off"),
            ("adm_e", "adme"),
            ("super", "super"),
            ("sans_role", "none"),
        ):
            personne = _personne(cx, marqueur, suffixe)
            _appartenance(cx, entite_a, personne)
            r[f"{role}_personne"] = personne

        #  ADM-E octroye dans l'entite B SEULE — temoin que la resolution
        #  "n'importe ou" ne depend pas de l'entite A.
        r["adm_e_entite_b_personne"] = _personne(cx, marqueur, "admeb")

        cercle = _cercle(cx, entite_a, f"{marqueur}-c")
        bureau = _bureau(cx, entite_a, f"{marqueur}-b")

        _responsabilite(cx, entite_a, r["dsm_personne"], TypeResponsabilite.DSM.value)
        _responsabilite(cx, entite_a, r["esm_personne"], TypeResponsabilite.ESM.value)
        _responsabilite(
            cx, entite_a, r["booster_personne"], TypeResponsabilite.BOOSTER.value, cercle=cercle
        )
        _responsabilite(
            cx,
            entite_a,
            r["office_personne"],
            TypeResponsabilite.OFFICE_MANAGER.value,
            bureau=bureau,
        )
        _role_technique(cx, r["adm_e_personne"], entite_a, TypeRoleTechnique.ENTITY_ADMIN.value)
        _role_technique(cx, r["super_personne"], None, TypeRoleTechnique.SUPER_ADMIN.value)
        _role_technique(
            cx, r["adm_e_entite_b_personne"], entite_b, TypeRoleTechnique.ENTITY_ADMIN.value
        )

        r["alerte_ouverte"] = _alerte(cx, empreinte=f"{marqueur}-ouverte")
        r["alerte_acquittee"] = _alerte(
            cx, empreinte=f"{marqueur}-acquittee", state="acknowledged", acknowledged_at=ANCRAGE
        )
        r["alerte_resolue"] = _alerte(
            cx,
            empreinte=f"{marqueur}-resolue",
            state="resolved",
            acknowledged_at=ANCRAGE,
            resolved_at=ANCRAGE,
        )

    r["jetons"] = {
        role: _session(parametres, r[f"{role}_personne"])
        for role in ("dsm", "esm", "booster", "office", "adm_e", "super", "sans_role")
    }
    r["jetons"]["adm_e_entite_b"] = _session(parametres, r["adm_e_entite_b_personne"])

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM alert_comment WHERE operational_alert_id IN "
            "(SELECT id FROM operational_alert WHERE fingerprint LIKE :motif)",
            "DELETE FROM operational_alert WHERE fingerprint LIKE :motif",
            "DELETE FROM audit_event WHERE actor_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR person_id IN "
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
#  401/403 — session et perimetre
# ===========================================================================


@pytest.mark.integration
def test_sans_session_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    assert _lister(parametres, None).status_code == 401
    assert _une_alerte(parametres, decor["alerte_ouverte"], None).status_code == 401
    assert _commentaires(parametres, decor["alerte_ouverte"], None).status_code == 401
    assert _acquitter(parametres, decor["alerte_ouverte"], None, version=1).status_code == 401


@pytest.mark.integration
@pytest.mark.parametrize("role", ["dsm", "booster", "office", "sans_role"])
def test_lecture_refusee_sans_plancher_soi(decor: dict[str, Any], role: str) -> None:
    """A la difference des signalements (`Soi`), aucune de ces quatre
    sessions n'a de porte derobee — voir l'en-tete d'`app/support/
    perimetre_alertes.py`."""
    reponse = _lister(decor["parametres"], decor["jetons"][role])
    assert reponse.status_code == 403


# ===========================================================================
#  Lecture — Limite fonctionnel (ESM) contre Complet (ADM-E/SUPER)
# ===========================================================================


@pytest.mark.integration
def test_esm_lit_toutes_les_alertes_sans_source_ni_empreinte(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], decor["jetons"]["esm"])
    assert reponse.status_code == 200
    corps = reponse.json()
    identifiants = {a["identifiant"] for a in corps["alertes"]}
    assert str(decor["alerte_ouverte"]) in identifiants
    for ligne in corps["alertes"]:
        assert ligne["source"] is None
        assert ligne["empreinte"] is None
        #  Les colonnes METIER restent visibles.
        assert ligne["gravite"] is not None
        assert ligne["etat"] is not None


@pytest.mark.integration
@pytest.mark.parametrize("role", ["adm_e", "super"])
def test_adm_e_et_super_lisent_en_detail_complet(decor: dict[str, Any], role: str) -> None:
    reponse = _lister(decor["parametres"], decor["jetons"][role])
    assert reponse.status_code == 200
    ligne = next(
        a for a in reponse.json()["alertes"] if a["identifiant"] == str(decor["alerte_ouverte"])
    )
    assert ligne["source"] == "worker"
    assert ligne["empreinte"] is not None


@pytest.mark.integration
def test_adm_e_lit_n_importe_ou_pas_seulement_dans_son_entite(decor: dict[str, Any]) -> None:
    """Temoin DIRECT : `adm_e_entite_b` tient `ENTITY_ADMIN` dans l'entite B
    SEULE, jamais dans l'entite A — et les alertes ne sont rattachees a
    AUCUNE entite. La resolution "n'importe ou" (`app/support/perimetre_
    alertes.py`) doit donc lui donner le MEME acces complet que `adm_e`."""
    reponse = _lister(decor["parametres"], decor["jetons"]["adm_e_entite_b"])
    assert reponse.status_code == 200
    ligne = next(
        a for a in reponse.json()["alertes"] if a["identifiant"] == str(decor["alerte_ouverte"])
    )
    assert ligne["source"] == "worker"


@pytest.mark.integration
def test_filtre_etat(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], decor["jetons"]["super"], etat=EtatAlerte.RESOLVED.value)
    assert reponse.status_code == 200
    identifiants = {a["identifiant"] for a in reponse.json()["alertes"]}
    assert str(decor["alerte_resolue"]) in identifiants
    assert str(decor["alerte_ouverte"]) not in identifiants


@pytest.mark.integration
def test_une_alerte_introuvable_404(decor: dict[str, Any]) -> None:
    reponse = _une_alerte(decor["parametres"], uuid.uuid4(), decor["jetons"]["super"])
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "alerte_introuvable"


@pytest.mark.integration
def test_commentaires_d_une_alerte_introuvable_404(decor: dict[str, Any]) -> None:
    reponse = _commentaires(decor["parametres"], uuid.uuid4(), decor["jetons"]["super"])
    assert reponse.status_code == 404


# ===========================================================================
#  Ecriture — ADM-E/SUPER seulement, ESM refuse malgre sa lecture
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("role", ["esm", "dsm", "booster", "office", "sans_role"])
def test_acquittement_refuse_aux_roles_sans_droit_de_traitement(
    decor: dict[str, Any], role: str
) -> None:
    reponse = _acquitter(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"][role], version=1
    )
    assert reponse.status_code == 403


@pytest.mark.integration
@pytest.mark.parametrize("role", ["adm_e", "super"])
def test_acquittement_reussit_pour_adm_e_ou_super(decor: dict[str, Any], role: str) -> None:
    reponse = _acquitter(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"][role], version=1
    )
    assert reponse.status_code == 200
    assert reponse.json() == {"etat": "acknowledged", "version": 2}


@pytest.mark.integration
def test_acquittement_refuse_csrf_sans_jeton(decor: dict[str, Any]) -> None:
    """Negatif, apparie au positif ci-dessus (§7.39)."""
    reponse = _acquitter(
        decor["parametres"],
        decor["alerte_ouverte"],
        decor["jetons"]["super"],
        version=1,
        avec_csrf=False,
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_acquittement_echoue_transition_invalide_si_deja_acquittee(decor: dict[str, Any]) -> None:
    reponse = _acquitter(
        decor["parametres"], decor["alerte_acquittee"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "transition_invalide"


@pytest.mark.integration
def test_acquittement_echoue_transition_invalide_si_deja_resolue(decor: dict[str, Any]) -> None:
    reponse = _acquitter(
        decor["parametres"], decor["alerte_resolue"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "transition_invalide"


@pytest.mark.integration
def test_acquittement_echoue_version_obsolete(decor: dict[str, Any]) -> None:
    reponse = _acquitter(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["super"], version=99
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_acquittement_alerte_introuvable(decor: dict[str, Any]) -> None:
    reponse = _acquitter(decor["parametres"], uuid.uuid4(), decor["jetons"]["super"], version=1)
    assert reponse.status_code == 404


# ===========================================================================
#  Commenter — aucune precondition d'etat
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("cle_alerte", ["alerte_ouverte", "alerte_acquittee", "alerte_resolue"])
def test_commenter_reussit_a_n_importe_quel_etat(decor: dict[str, Any], cle_alerte: str) -> None:
    reponse = _commenter(
        decor["parametres"], decor[cle_alerte], decor["jetons"]["adm_e"], "Investigation en cours."
    )
    assert reponse.status_code == 201
    assert "identifiant" in reponse.json()


@pytest.mark.integration
def test_commenter_refuse_a_esm(decor: dict[str, Any]) -> None:
    reponse = _commenter(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["esm"], "Note."
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_commenter_refuse_csrf_sans_jeton(decor: dict[str, Any]) -> None:
    reponse = _commenter(
        decor["parametres"],
        decor["alerte_ouverte"],
        decor["jetons"]["super"],
        "Note.",
        avec_csrf=False,
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_commentaire_vit_dans_alert_comment_jamais_dans_audit_event_reason(
    decor: dict[str, Any],
) -> None:
    contenu = f"commentaire-temoin-{uuid.uuid4().hex[:8]}"
    reponse = _commenter(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["adm_e"], contenu
    )
    assert reponse.status_code == 201
    with moteur(decor["parametres"]).begin() as cx:
        lignes = (
            cx.execute(
                text("SELECT content FROM alert_comment WHERE operational_alert_id = :a"),
                {"a": decor["alerte_ouverte"]},
            )
            .scalars()
            .all()
        )
        assert contenu in lignes
        evenement = cx.execute(
            text(
                "SELECT reason FROM audit_event WHERE resource_type = 'operational_alert' "
                "AND resource_reference = :a AND action_code = 'alerte_commentee' "
                "ORDER BY occurred_at DESC LIMIT 1"
            ),
            {"a": decor["alerte_ouverte"]},
        ).scalar_one()
        #  Jamais duplique : le contenu vit UNE SEULE FOIS, dans `alert_comment`.
        assert evenement is None


# ===========================================================================
#  Resoudre — depuis open OU acknowledged, jamais depuis resolved
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("cle_alerte", ["alerte_ouverte", "alerte_acquittee"])
def test_resoudre_reussit_depuis_open_ou_acknowledged(
    decor: dict[str, Any], cle_alerte: str
) -> None:
    reponse = _resoudre(decor["parametres"], decor[cle_alerte], decor["jetons"]["adm_e"], version=1)
    assert reponse.status_code == 200
    assert reponse.json()["etat"] == "resolved"


@pytest.mark.integration
def test_resoudre_refuse_a_esm(decor: dict[str, Any]) -> None:
    reponse = _resoudre(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["esm"], version=1
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_resoudre_refuse_csrf_sans_jeton(decor: dict[str, Any]) -> None:
    reponse = _resoudre(
        decor["parametres"],
        decor["alerte_ouverte"],
        decor["jetons"]["super"],
        version=1,
        avec_csrf=False,
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_resoudre_echoue_si_deja_resolue(decor: dict[str, Any]) -> None:
    reponse = _resoudre(
        decor["parametres"], decor["alerte_resolue"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "transition_invalide"


@pytest.mark.integration
def test_resoudre_version_obsolete(decor: dict[str, Any]) -> None:
    reponse = _resoudre(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["super"], version=42
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_resoudre_avec_commentaire_cree_aussi_une_ligne_alert_comment(
    decor: dict[str, Any],
) -> None:
    contenu = f"resolu-{uuid.uuid4().hex[:8]}"
    reponse = _resoudre(
        decor["parametres"],
        decor["alerte_ouverte"],
        decor["jetons"]["adm_e"],
        version=1,
        commentaire=contenu,
    )
    assert reponse.status_code == 200
    with moteur(decor["parametres"]).begin() as cx:
        lignes = (
            cx.execute(
                text("SELECT content FROM alert_comment WHERE operational_alert_id = :a"),
                {"a": decor["alerte_ouverte"]},
            )
            .scalars()
            .all()
        )
        assert contenu in lignes


@pytest.mark.integration
def test_resoudre_sans_commentaire_ne_cree_aucune_ligne(decor: dict[str, Any]) -> None:
    reponse = _resoudre(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 200
    with moteur(decor["parametres"]).begin() as cx:
        total = cx.execute(
            text("SELECT count(*) FROM alert_comment WHERE operational_alert_id = :a"),
            {"a": decor["alerte_ouverte"]},
        ).scalar_one()
        assert total == 0


# ===========================================================================
#  AUCUN MOTIF — contraste direct avec `T12`
# ===========================================================================


@pytest.mark.integration
def test_super_acquitte_sans_aucun_motif(decor: dict[str, Any]) -> None:
    """A la difference de `modifier_l_etat_d_un_signalement` (T12), ni
    `DemandeDAcquittement` ni `DemandeDeResolution` ne portent de champ
    `motif` : la version SEULE suffit, meme pour `SUPER` (voir `app/support/
    perimetre_alertes.py` — `ECART-064` ne s'applique jamais a une ressource
    globale)."""
    reponse = _acquitter(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 200


@pytest.mark.integration
def test_super_resout_sans_commentaire_ni_motif(decor: dict[str, Any]) -> None:
    reponse = _resoudre(
        decor["parametres"], decor["alerte_ouverte"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 200
    assert reponse.json()["etat"] == "resolved"


# ===========================================================================
#  `lever_une_alerte` — creation, no-op, reouverture automatique
# ===========================================================================


@pytest.mark.integration
def test_lever_une_alerte_cree_une_ligne_et_un_audit_event(
    parametres_de_la_stack: Parametres,
) -> None:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    empreinte = f"t13-leve-{uuid.uuid4().hex[:8]}"
    try:
        with moteur(parametres).begin() as cx:
            resultat = lever_une_alerte(
                cx, severity="CRITICAL", source="worker", fingerprint=empreinte, instant=ANCRAGE
            )
            assert resultat.state == "open"
            assert resultat.reouverture is False
            action = cx.execute(
                text(
                    "SELECT action_code FROM audit_event WHERE resource_type = 'operational_alert' "
                    "AND resource_reference = :a"
                ),
                {"a": resultat.id},
            ).scalar_one()
            assert action == "alerte_levee"
    finally:
        with moteur(parametres).begin() as cx:
            cx.execute(
                text("DELETE FROM audit_event WHERE resource_reference = :a"), {"a": resultat.id}
            )
            cx.execute(text("DELETE FROM operational_alert WHERE id = :a"), {"a": resultat.id})


@pytest.mark.integration
def test_lever_une_alerte_est_un_no_op_si_deja_ouverte(
    parametres_de_la_stack: Parametres,
) -> None:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    empreinte = f"t13-noop-{uuid.uuid4().hex[:8]}"
    try:
        with moteur(parametres).begin() as cx:
            premier = lever_une_alerte(
                cx, severity="ERROR", source="api", fingerprint=empreinte, instant=ANCRAGE
            )
        with moteur(parametres).begin() as cx:
            second = lever_une_alerte(
                cx,
                severity="ERROR",
                source="api",
                fingerprint=empreinte,
                instant=ANCRAGE + dt.timedelta(minutes=1),
            )
            assert second.id == premier.id
            assert second.version == premier.version
            assert second.reouverture is False
            total_evenements = cx.execute(
                text(
                    "SELECT count(*) FROM audit_event WHERE resource_type = 'operational_alert' "
                    "AND resource_reference = :a"
                ),
                {"a": premier.id},
            ).scalar_one()
            assert total_evenements == 1
    finally:
        with moteur(parametres).begin() as cx:
            cx.execute(
                text("DELETE FROM audit_event WHERE resource_reference = :a"), {"a": premier.id}
            )
            cx.execute(text("DELETE FROM operational_alert WHERE id = :a"), {"a": premier.id})


@pytest.mark.integration
def test_lever_une_alerte_rouvre_apres_resolution(parametres_de_la_stack: Parametres) -> None:
    """La demonstration du cahier Annexe C : « resolution puis reouverture
    automatique d'une alerte recurrente »."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    empreinte = f"t13-rouvre-{uuid.uuid4().hex[:8]}"
    marqueur = f"t13l10rouvre{uuid.uuid4().hex[:8]}"
    with moteur(parametres).begin() as cx:
        acteur = _personne(cx, marqueur, "acteur")
    try:
        with moteur(parametres).begin() as cx:
            leve = lever_une_alerte(
                cx, severity="WARNING", source="backup", fingerprint=empreinte, instant=ANCRAGE
            )
        with moteur(parametres).begin() as cx:
            resoudre_une_alerte(
                cx,
                alerte=leve.id,
                version_attendue=leve.version,
                commentaire=None,
                acteur=acteur,
                instant=ANCRAGE + dt.timedelta(minutes=5),
            )
        with moteur(parametres).begin() as cx:
            etat_avant = cx.execute(
                text("SELECT state FROM operational_alert WHERE id = :a"), {"a": leve.id}
            ).scalar_one()
            assert etat_avant == "resolved"

            recidive = lever_une_alerte(
                cx,
                severity="WARNING",
                source="backup",
                fingerprint=empreinte,
                instant=ANCRAGE + dt.timedelta(minutes=10),
            )
            assert recidive.id == leve.id
            assert recidive.state == "open"
            assert recidive.reouverture is True

            ligne = cx.execute(
                text(
                    "SELECT state, acknowledged_at, resolved_at "
                    "FROM operational_alert WHERE id = :a"
                ),
                {"a": leve.id},
            ).one()
            assert ligne.state == "open"
            assert ligne.acknowledged_at is None
            assert ligne.resolved_at is None

            dernier_evenement = cx.execute(
                text(
                    "SELECT action_code, old_values, new_values FROM audit_event "
                    "WHERE resource_type = 'operational_alert' AND resource_reference = :a "
                    "ORDER BY occurred_at DESC, id DESC LIMIT 1"
                ),
                {"a": leve.id},
            ).one()
            assert dernier_evenement.action_code == "alerte_rouverte"
            assert dernier_evenement.old_values == {"state": "resolved"}
            assert dernier_evenement.new_values == {"state": "open"}
    finally:
        with moteur(parametres).begin() as cx:
            cx.execute(
                text("DELETE FROM audit_event WHERE resource_reference = :a"), {"a": leve.id}
            )
            cx.execute(text("DELETE FROM operational_alert WHERE id = :a"), {"a": leve.id})
            cx.execute(text("DELETE FROM person WHERE id = :a"), {"a": acteur})
