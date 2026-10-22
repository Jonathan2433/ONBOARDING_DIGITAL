"""Le suivi d'une demande de droit RGPD — LOT 10, `T14`, `MVP-L10-US008`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. `a_le_droit_de_traiter_les_demandes_rgpd` : pur, `ADM-E`/`SUPER` seuls,
     AUCUN plancher `Soi` — et contrairement aux alertes (`T13`), AUCUNE
     lecture partielle pour l'`ESM` (voir `app/privacy/perimetre.py`) ;
  2. `DSM`/`BOOST`/`OFFICE`/`ESM`/sans role sont refuses (403) sur TOUTES les
     routes, lecture comprise — une seule garde, jamais deux ;
  3. `ADM-E` est resolu dans N'IMPORTE QUELLE entite (temoin direct, meme
     motif que `T13`) ;
  4. reception d'une demande (POST) : la personne concernee doit exister
     (422 sinon), `due_at` vaut `received_at` + 30 jours (RGPD, article
     12§3), le `responsable` est TOUJOURS l'appelant ;
  5. verification d'identite : aucune precondition d'etat, IDEMPOTENTE ;
  6. cloture : valide SEULEMENT depuis `received`, 409 `transition_invalide`
     si deja cloturee ;
  7. la version perimee est un 409, jamais un ecrasement silencieux (§18.4),
     sur les deux routes d'ecriture ;
  8. AUCUN motif n'est jamais exige, meme pour `SUPER` — `ECART-064` ne
     s'applique jamais a une ressource sans entite (temoin positif) ;
  9. l'historique est la suite des `audit_event` de CETTE demande (reception,
     verification, cloture) ;
  10. `en_retard` est calcule a la lecture, jamais une colonne stockee ;
  11. le refus CSRF (negatif) est apparie a chaque succes (positif, §7.39).

Ce fichier n'importe aucune fonction d'un autre fichier de test — les lignes
de decor sont inserees DIRECTEMENT, meme discipline que
`test_traitement_alertes.py`.
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

from app.auth.csrf import EN_TETE_JETON, jeton_pour
from app.auth.sessions import empreinte_de_session, ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeResponsabilite, TypeRoleTechnique
from app.permissions.services import RoleDeLaMatrice
from app.privacy.perimetre import a_le_droit_de_traiter_les_demandes_rgpd
from app.privacy.traitement import DELAI_DE_REPONSE_RGPD, ETAT_CLOS, ETAT_RECU
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_LISTE = "/api/v1/data-subject-requests"
CHEMIN_UNE_DEMANDE = "/api/v1/data-subject-requests/{demande}"
CHEMIN_HISTORIQUE = "/api/v1/data-subject-requests/{demande}/historique"
CHEMIN_VERIFICATION = "/api/v1/data-subject-requests/{demande}/verification-identite"
CHEMIN_CLOTURE = "/api/v1/data-subject-requests/{demande}/cloture"

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
            "account_state) VALUES (:a, :a, :prenom, 'T14L10', 'active') RETURNING id"
        ),
        {"a": adresse, "prenom": suffixe},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> None:
    """Une appartenance OCCUPANTE — necessaire pour que `EMP` existe, pas pour
    `ADM-E`/`SUPER` ici (resolus sans dependre d'une appartenance occupante,
    voir `app/privacy/perimetre.py`)."""
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


def _demande_rgpd(
    cx: Connection,
    *,
    personne_concernee: uuid.UUID,
    responsable: uuid.UUID,
    request_type: str = "access",
    channel: str = "e-mail",
    state: str = ETAT_RECU,
    identity_verified: bool = False,
    response: str | None = None,
    closed_at: dt.datetime | None = None,
) -> uuid.UUID:
    """Une ligne `data_subject_request`, inseree DIRECTEMENT — meme
    discipline que `test_traitement_alertes.py::_alerte`."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO data_subject_request "
            "(data_subject_person_id, request_type, channel, received_at, "
            " identity_verified, responsible_person_id, due_at, state, response, closed_at) "
            "VALUES (:sujet, :type_demande, :canal, :recue, "
            " :verifiee, :responsable, :echeance, :etat, :reponse, :cloturee) "
            "RETURNING id"
        ),
        {
            "sujet": personne_concernee,
            "type_demande": request_type,
            "canal": channel,
            "recue": ANCRAGE,
            "verifiee": identity_verified,
            "responsable": responsable,
            "echeance": ANCRAGE + DELAI_DE_REPONSE_RGPD,
            "etat": state,
            "reponse": response,
            "cloturee": closed_at,
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


def _une_demande(parametres: Parametres, demande: uuid.UUID, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        _avec_jeton(client, parametres, jeton)
        return client.get(CHEMIN_UNE_DEMANDE.format(demande=demande))


def _historique(parametres: Parametres, demande: uuid.UUID, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        _avec_jeton(client, parametres, jeton)
        return client.get(CHEMIN_HISTORIQUE.format(demande=demande))


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


def _receptionner(
    parametres: Parametres,
    jeton: str | None,
    personne_concernee: uuid.UUID,
    *,
    type_demande: str = "access",
    canal: str = "e-mail",
    avec_csrf: bool = True,
) -> Any:
    return _poster(
        parametres,
        CHEMIN_LISTE,
        jeton,
        {
            "personne_concernee_id": str(personne_concernee),
            "type_demande": type_demande,
            "canal": canal,
        },
        avec_csrf=avec_csrf,
    )


def _verifier(
    parametres: Parametres,
    demande: uuid.UUID,
    jeton: str | None,
    version: int,
    *,
    avec_csrf: bool = True,
) -> Any:
    return _poster(
        parametres,
        CHEMIN_VERIFICATION.format(demande=demande),
        jeton,
        {"version": version},
        avec_csrf=avec_csrf,
    )


def _cloturer(
    parametres: Parametres,
    demande: uuid.UUID,
    jeton: str | None,
    version: int,
    reponse: str = "Export transmis par courrier.",
    *,
    avec_csrf: bool = True,
) -> Any:
    return _poster(
        parametres,
        CHEMIN_CLOTURE.format(demande=demande),
        jeton,
        {"version": version, "reponse": reponse},
        avec_csrf=avec_csrf,
    )


# ===========================================================================
#  `a_le_droit_de_traiter_les_demandes_rgpd` — pur
# ===========================================================================


@pytest.mark.parametrize(
    ("roles", "attendu"),
    [
        (frozenset(), False),
        (frozenset({RoleDeLaMatrice.DSM}), False),
        (frozenset({RoleDeLaMatrice.BOOSTER}), False),
        (frozenset({RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}), False),
        (frozenset({RoleDeLaMatrice.EMPLOYE}), False),
        #  A LA DIFFERENCE DES ALERTES (T13) : l'ESM ne recoit RIEN ici,
        #  aucune ligne de matrice ne lui donnant de lecture partielle sur
        #  une demande RGPD (voir `app/privacy/perimetre.py`).
        (frozenset({RoleDeLaMatrice.ESM}), False),
        (frozenset({RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE}), True),
        (frozenset({RoleDeLaMatrice.SUPER_ADMINISTRATEUR}), True),
        #  Cumul : un seul des deux roles habilites suffit.
        (
            frozenset({RoleDeLaMatrice.ESM, RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE}),
            True,
        ),
        (
            frozenset({RoleDeLaMatrice.DSM, RoleDeLaMatrice.SUPER_ADMINISTRATEUR}),
            True,
        ),
    ],
)
def test_resolution_du_droit_de_traiter(roles: frozenset[RoleDeLaMatrice], attendu: bool) -> None:
    assert a_le_droit_de_traiter_les_demandes_rgpd(roles=roles) is attendu


# ===========================================================================
#  Decor d'integration
# ===========================================================================


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t14l10{uuid.uuid4().hex[:10]}"
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

        #  La personne CONCERNEE par les demandes — aucun role, aucune
        #  appartenance necessaire : seule son existence compte (FK).
        r["sujet_personne"] = _personne(cx, marqueur, "sujet")

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

        r["demande_recue"] = _demande_rgpd(
            cx, personne_concernee=r["sujet_personne"], responsable=r["adm_e_personne"]
        )
        r["demande_cloturee"] = _demande_rgpd(
            cx,
            personne_concernee=r["sujet_personne"],
            responsable=r["adm_e_personne"],
            state=ETAT_CLOS,
            identity_verified=True,
            response="Export transmis par courrier recommande.",
            closed_at=ANCRAGE,
        )

    r["jetons"] = {
        role: _session(parametres, r[f"{role}_personne"])
        for role in ("dsm", "esm", "booster", "office", "adm_e", "super", "sans_role")
    }
    r["jetons"]["adm_e_entite_b"] = _session(parametres, r["adm_e_entite_b_personne"])

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM data_subject_request WHERE data_subject_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne) OR responsible_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
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
#  401/403 — session et perimetre, AUCUN plancher Soi
# ===========================================================================


@pytest.mark.integration
def test_sans_session_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    assert _lister(parametres, None).status_code == 401
    assert _une_demande(parametres, decor["demande_recue"], None).status_code == 401
    assert _historique(parametres, decor["demande_recue"], None).status_code == 401
    assert _verifier(parametres, decor["demande_recue"], None, version=1).status_code == 401


@pytest.mark.integration
@pytest.mark.parametrize("role", ["dsm", "esm", "booster", "office", "sans_role"])
def test_lecture_refusee_sans_plancher_soi(decor: dict[str, Any], role: str) -> None:
    """Aucune de ces cinq sessions n'a de porte derobee — pas meme l'`ESM`,
    a la difference des alertes (`T13`). Voir `app/privacy/perimetre.py`."""
    reponse = _lister(decor["parametres"], decor["jetons"][role])
    assert reponse.status_code == 403


@pytest.mark.integration
@pytest.mark.parametrize("role", ["dsm", "esm", "booster", "office", "sans_role"])
def test_reception_refusee_sans_plancher_soi(decor: dict[str, Any], role: str) -> None:
    reponse = _receptionner(decor["parametres"], decor["jetons"][role], decor["sujet_personne"])
    assert reponse.status_code == 403


# ===========================================================================
#  Lecture — ADM-E/SUPER seuls, ADM-E resolu n'importe ou
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("role", ["adm_e", "super"])
def test_adm_e_et_super_lisent(decor: dict[str, Any], role: str) -> None:
    reponse = _lister(decor["parametres"], decor["jetons"][role])
    assert reponse.status_code == 200
    identifiants = {d["identifiant"] for d in reponse.json()["demandes"]}
    assert str(decor["demande_recue"]) in identifiants


@pytest.mark.integration
def test_adm_e_lit_n_importe_ou_pas_seulement_dans_son_entite(decor: dict[str, Any]) -> None:
    """Temoin DIRECT : `adm_e_entite_b` tient `ENTITY_ADMIN` dans l'entite B
    SEULE, jamais dans l'entite A — et les demandes RGPD ne sont rattachees
    a AUCUNE entite. La resolution "n'importe ou" doit donc lui donner le
    MEME acces que `adm_e`."""
    reponse = _lister(decor["parametres"], decor["jetons"]["adm_e_entite_b"])
    assert reponse.status_code == 200
    identifiants = {d["identifiant"] for d in reponse.json()["demandes"]}
    assert str(decor["demande_recue"]) in identifiants


@pytest.mark.integration
def test_filtre_etat(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], decor["jetons"]["super"], etat=ETAT_CLOS)
    assert reponse.status_code == 200
    identifiants = {d["identifiant"] for d in reponse.json()["demandes"]}
    assert str(decor["demande_cloturee"]) in identifiants
    assert str(decor["demande_recue"]) not in identifiants


@pytest.mark.integration
def test_une_demande_introuvable_404(decor: dict[str, Any]) -> None:
    reponse = _une_demande(decor["parametres"], uuid.uuid4(), decor["jetons"]["super"])
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "demande_rgpd_introuvable"


@pytest.mark.integration
def test_en_retard_calcule_a_la_lecture(decor: dict[str, Any]) -> None:
    """Une demande recue il y a dix minutes, echeance a +30 jours, n'est pas
    en retard — `en_retard` est CALCULE, jamais une colonne stockee."""
    reponse = _une_demande(decor["parametres"], decor["demande_recue"], decor["jetons"]["super"])
    assert reponse.status_code == 200
    assert reponse.json()["en_retard"] is False


# ===========================================================================
#  Reception — POST /data-subject-requests
# ===========================================================================


@pytest.mark.integration
def test_reception_reussit_pour_adm_e(decor: dict[str, Any]) -> None:
    reponse = _receptionner(decor["parametres"], decor["jetons"]["adm_e"], decor["sujet_personne"])
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["etat"] == ETAT_RECU
    assert corps["identite_verifiee"] is False
    #  Le responsable est TOUJOURS l'appelant — aucune reassignation.
    with moteur(decor["parametres"]).begin() as cx:
        responsable = cx.execute(
            text("SELECT responsible_person_id FROM data_subject_request WHERE id = :d"),
            {"d": corps["identifiant"]},
        ).scalar_one()
    assert str(responsable) == str(decor["adm_e_personne"])


@pytest.mark.integration
def test_reception_calcule_l_echeance_a_30_jours(decor: dict[str, Any]) -> None:
    reponse = _receptionner(decor["parametres"], decor["jetons"]["super"], decor["sujet_personne"])
    assert reponse.status_code == 201
    corps = reponse.json()
    recue = dt.datetime.fromisoformat(corps["recue_le"])
    echeance = dt.datetime.fromisoformat(corps["echeance"])
    assert echeance - recue == DELAI_DE_REPONSE_RGPD


@pytest.mark.integration
def test_reception_personne_concernee_introuvable_422(decor: dict[str, Any]) -> None:
    reponse = _receptionner(decor["parametres"], decor["jetons"]["super"], uuid.uuid4())
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "personne_concernee_introuvable"


@pytest.mark.integration
def test_reception_refuse_csrf_sans_jeton(decor: dict[str, Any]) -> None:
    """Negatif, apparie au positif `test_reception_reussit_pour_adm_e` (§7.39)."""
    reponse = _receptionner(
        decor["parametres"], decor["jetons"]["super"], decor["sujet_personne"], avec_csrf=False
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_super_receptionne_sans_aucun_motif(decor: dict[str, Any]) -> None:
    """`ECART-064` ne s'applique jamais ici — contraste direct avec `T12`
    (signalements), ou `SUPER` doit fournir un motif."""
    reponse = _receptionner(decor["parametres"], decor["jetons"]["super"], decor["sujet_personne"])
    assert reponse.status_code == 201


# ===========================================================================
#  Verification d'identite — aucune precondition d'etat, IDEMPOTENTE
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("cle_demande", ["demande_recue", "demande_cloturee"])
def test_verification_reussit_a_n_importe_quel_etat(
    decor: dict[str, Any], cle_demande: str
) -> None:
    reponse = _verifier(
        decor["parametres"], decor[cle_demande], decor["jetons"]["adm_e"], version=1
    )
    assert reponse.status_code == 200
    assert reponse.json()["identite_verifiee"] is True


@pytest.mark.integration
def test_verification_idempotente_sur_une_demande_deja_verifiee(decor: dict[str, Any]) -> None:
    """`demande_cloturee` du decor est deja verifiee : aucune ecriture de
    plus, la version ne bouge pas (voir `app/privacy/traitement.py`)."""
    reponse = _verifier(
        decor["parametres"], decor["demande_cloturee"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 200
    assert reponse.json() == {"etat": ETAT_CLOS, "identite_verifiee": True, "version": 1}


@pytest.mark.integration
def test_verification_refusee_a_esm(decor: dict[str, Any]) -> None:
    reponse = _verifier(
        decor["parametres"], decor["demande_recue"], decor["jetons"]["esm"], version=1
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_verification_refuse_csrf_sans_jeton(decor: dict[str, Any]) -> None:
    reponse = _verifier(
        decor["parametres"],
        decor["demande_recue"],
        decor["jetons"]["super"],
        version=1,
        avec_csrf=False,
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_verification_version_obsolete(decor: dict[str, Any]) -> None:
    reponse = _verifier(
        decor["parametres"], decor["demande_recue"], decor["jetons"]["super"], version=99
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_verification_demande_introuvable_404(decor: dict[str, Any]) -> None:
    reponse = _verifier(decor["parametres"], uuid.uuid4(), decor["jetons"]["super"], version=1)
    assert reponse.status_code == 404


# ===========================================================================
#  Cloture — valide SEULEMENT depuis `received`
# ===========================================================================


@pytest.mark.integration
def test_cloture_reussit_pour_adm_e(decor: dict[str, Any]) -> None:
    reponse = _cloturer(
        decor["parametres"], decor["demande_recue"], decor["jetons"]["adm_e"], version=1
    )
    assert reponse.status_code == 200
    assert reponse.json()["etat"] == ETAT_CLOS
    with moteur(decor["parametres"]).begin() as cx:
        reponse_stockee = cx.execute(
            text("SELECT response, closed_at FROM data_subject_request WHERE id = :d"),
            {"d": decor["demande_recue"]},
        ).one()
    assert reponse_stockee.response == "Export transmis par courrier."
    assert reponse_stockee.closed_at is not None


@pytest.mark.integration
def test_cloture_refusee_a_esm(decor: dict[str, Any]) -> None:
    reponse = _cloturer(
        decor["parametres"], decor["demande_recue"], decor["jetons"]["esm"], version=1
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_cloture_echoue_transition_invalide_si_deja_cloturee(decor: dict[str, Any]) -> None:
    reponse = _cloturer(
        decor["parametres"], decor["demande_cloturee"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "transition_invalide"


@pytest.mark.integration
def test_cloture_version_obsolete(decor: dict[str, Any]) -> None:
    reponse = _cloturer(
        decor["parametres"], decor["demande_recue"], decor["jetons"]["super"], version=99
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_cloture_refuse_csrf_sans_jeton(decor: dict[str, Any]) -> None:
    reponse = _cloturer(
        decor["parametres"],
        decor["demande_recue"],
        decor["jetons"]["super"],
        version=1,
        avec_csrf=False,
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_super_cloture_sans_aucun_motif(decor: dict[str, Any]) -> None:
    """`ECART-064` ne s'applique jamais ici — contraste direct avec `T12`."""
    reponse = _cloturer(
        decor["parametres"], decor["demande_recue"], decor["jetons"]["super"], version=1
    )
    assert reponse.status_code == 200


# ===========================================================================
#  Historique — la suite des `audit_event` de cette demande
# ===========================================================================


@pytest.mark.integration
def test_historique_porte_la_reception_puis_la_cloture(decor: dict[str, Any]) -> None:
    reception = _receptionner(
        decor["parametres"], decor["jetons"]["adm_e"], decor["sujet_personne"]
    )
    assert reception.status_code == 201
    demande = reception.json()["identifiant"]

    cloture = _cloturer(decor["parametres"], demande, decor["jetons"]["adm_e"], version=1)
    assert cloture.status_code == 200

    reponse = _historique(decor["parametres"], demande, decor["jetons"]["super"])
    assert reponse.status_code == 200
    evenements = reponse.json()["evenements"]
    assert len(evenements) == 2
    #  Le plus recent d'abord : la cloture precede la reception.
    assert evenements[0]["nouvelles_valeurs"] == {"state": ETAT_CLOS}
    assert evenements[1]["nouvelles_valeurs"]["state"] == ETAT_RECU


@pytest.mark.integration
def test_historique_demande_introuvable_404(decor: dict[str, Any]) -> None:
    reponse = _historique(decor["parametres"], uuid.uuid4(), decor["jetons"]["super"])
    assert reponse.status_code == 404
