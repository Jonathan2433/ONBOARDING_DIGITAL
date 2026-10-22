"""Le traitement des signalements — LOT 10, `T12`, matrice §17, `MVP-L10-US006`.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. `Soi` : `DSM`/`BOOST`/`OFFICE` ne voient que LEURS PROPRES signalements,
     avec le contexte technique complet (ce sont leurs propres donnees) ;
  2. `ESM` voit TOUTE l'entite mais en « lecture fonctionnelle » — les quatre
     colonnes techniques sont masquees, meme pour un signalement qu'il n'a
     pas lui-meme soumis ;
  3. `ADM-E` voit toute l'entite EN DETAIL COMPLET, `SUPER` voit n'importe
     quelle entite en detail complet — deux temoins d'isolation entre
     entites, dans les deux sens ;
  4. le filtre `etat` sert le « compteur back-office » du backlog, sans route
     separee ;
  5. l'historique d'un signalement suit le MEME perimetre que sa lecture —
     jamais celui, plus large, de l'audit generique (`T8`) ;
  6. seuls `ADM-E`/`SUPER` modifient l'etat — les cinq autres roles sont
     refuses en 403 ;
  7. le motif est obligatoire quand `SUPER` autorise l'appel (`ECART-064`),
     jamais quand seul `ADM-E` l'autorise (temoin negatif ET positif, §7.39) ;
  8. la version perimee est un 409, jamais un ecrasement silencieux (§18.4) ;
  9. l'isolation inter-entites tient aussi sur le changement d'etat (404) ;
  10. l'`audit_event` ecrit porte `old_values`/`new_values`/`reason` exacts —
      c'est l'historique et les « commentaires » du backlog, pas une table
      separee.

Ce fichier ne reteste PAS la creation d'un signalement (`test_signalement.py`,
`T11`) : les lignes de decor sont inserees DIRECTEMENT, meme discipline que
`test_export_audit.py`.
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
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.support.perimetre import (
    PerimetreDesSignalements,
    a_la_lecture_complete,
    resoudre_le_perimetre_des_signalements,
)

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_LISTE = "/api/v1/entities/{code}/bug-reports"
CHEMIN_HISTORIQUE = "/api/v1/entities/{code}/bug-reports/{signalement}/historique"
CHEMIN_ETAT = "/api/v1/entities/{code}/bug-reports/{signalement}/etat"

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
            "account_state) VALUES (:a, :a, :prenom, 'T12L10', 'active') RETURNING id"
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
        {"p": personne, "e": entite, "arrivee": ANCRAGE.date()},
    ).scalar_one()


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


def _signalement(
    cx: Connection,
    *,
    entite: uuid.UUID,
    rapporteur: uuid.UUID,
    description: str = "Un bug.",
    state: str = "new",
) -> uuid.UUID:
    """Une ligne `bug_report`, inseree DIRECTEMENT — meme discipline que
    `test_export_audit.py::_evenement_d_audit`, cote lecture plutot qu'ecriture."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO bug_report "
            "(entity_id, reported_by_person_id, state, description, page_path, "
            " application_version, environment, browser_summary, correlation_token) "
            "VALUES (:e, :p, :etat, :d, '/entites/x', '0.10.0-test', 'development', "
            " 'NavigateurDeTest/1.0', 'corr-t12-temoin') "
            "RETURNING id"
        ),
        {"e": entite, "p": rapporteur, "etat": state, "d": description},
    ).scalar_one()


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _lister(parametres: Parametres, code: str, jeton: str | None, **params: object) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN_LISTE.format(code=code), params=params)


def _historique(
    parametres: Parametres, code: str, signalement: uuid.UUID, jeton: str | None
) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN_HISTORIQUE.format(code=code, signalement=signalement))


def _modifier_l_etat(
    parametres: Parametres,
    code: str,
    signalement: uuid.UUID,
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
        return client.post(
            CHEMIN_ETAT.format(code=code, signalement=signalement), json=corps, headers=entetes
        )


# ===========================================================================
#  `resoudre_le_perimetre_des_signalements`/`a_la_lecture_complete` — purs
# ===========================================================================


@pytest.mark.parametrize(
    ("roles", "attendu"),
    [
        (frozenset(), PerimetreDesSignalements.SOI),
        (frozenset({RoleDeLaMatrice.DSM}), PerimetreDesSignalements.SOI),
        (frozenset({RoleDeLaMatrice.BOOSTER}), PerimetreDesSignalements.SOI),
        (frozenset({RoleDeLaMatrice.RESPONSABLE_DE_BUREAU}), PerimetreDesSignalements.SOI),
        (frozenset({RoleDeLaMatrice.ESM}), PerimetreDesSignalements.ENTITE_FONCTIONNELLE),
        (
            frozenset({RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE}),
            PerimetreDesSignalements.ENTITE_COMPLETE,
        ),
        (frozenset({RoleDeLaMatrice.SUPER_ADMINISTRATEUR}), PerimetreDesSignalements.GLOBAL),
        #  Cumul : le plus large gagne, meme motif que `PerimetreDuSuivi` (LOT 7).
        (
            frozenset({RoleDeLaMatrice.DSM, RoleDeLaMatrice.SUPER_ADMINISTRATEUR}),
            PerimetreDesSignalements.GLOBAL,
        ),
    ],
)
def test_resolution_du_perimetre(
    roles: frozenset[RoleDeLaMatrice], attendu: PerimetreDesSignalements
) -> None:
    assert resoudre_le_perimetre_des_signalements(roles=roles) is attendu


def test_seule_l_entite_fonctionnelle_masque_le_contexte_technique() -> None:
    for perimetre in PerimetreDesSignalements:
        attendu = perimetre is not PerimetreDesSignalements.ENTITE_FONCTIONNELLE
        assert a_la_lecture_complete(perimetre=perimetre) is attendu


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t12l10{uuid.uuid4().hex[:10]}"
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

        #  Une personne de L'AUTRE entite, pour les temoins d'isolation.
        autre_personne = _personne(cx, marqueur, "autre")
        _appartenance(cx, autre_entite, autre_personne)
        r["autre_personne"] = autre_personne

        #  Les signalements : un du DSM, un de l'ESM, un de l'autre entite.
        r["sig_dsm"] = _signalement(cx, entite=entite, rapporteur=r["dsm_personne"])
        r["sig_esm"] = _signalement(cx, entite=entite, rapporteur=r["esm_personne"])
        r["sig_autre"] = _signalement(cx, entite=autre_entite, rapporteur=autre_personne)

    r["jetons"] = {
        role: _session(parametres, r[f"{role}_personne"])
        for role in ("dsm", "esm", "booster", "office", "adme", "super", "emp")
    }

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM audit_event WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR actor_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM bug_report WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
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
#  LA LISTE — `GET /entities/{code}/bug-reports`
# ===========================================================================


@pytest.mark.integration
def test_liste_sans_session_401(decor: dict[str, Any]) -> None:
    assert _lister(decor["parametres"], decor["code"], None).status_code == 401


@pytest.mark.integration
def test_entite_inconnue_est_un_404(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], "code-totalement-inconnu", decor["jetons"]["adme"])
    assert reponse.status_code == 404


@pytest.mark.integration
def test_dsm_ne_voit_que_son_propre_signalement_en_detail_complet(decor: dict[str, Any]) -> None:
    """§17 « Consulter ses signalements | Soi » — jamais celui de l'ESM."""
    reponse = _lister(decor["parametres"], decor["code"], decor["jetons"]["dsm"])
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 1
    (ligne,) = corps["signalements"]
    assert ligne["identifiant"] == str(decor["sig_dsm"])
    #  Son PROPRE signalement : le contexte technique n'est jamais masque.
    assert ligne["version_application"] == "0.10.0-test"
    assert ligne["resume_navigateur"] == "NavigateurDeTest/1.0"


@pytest.mark.integration
def test_esm_voit_toute_l_entite_sans_le_contexte_technique(decor: dict[str, Any]) -> None:
    """§17 « Consulter les signalements de l'entite | Lecture fonctionnelle »."""
    reponse = _lister(decor["parametres"], decor["code"], decor["jetons"]["esm"])
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 2
    identifiants = {ligne["identifiant"] for ligne in corps["signalements"]}
    assert identifiants == {str(decor["sig_dsm"]), str(decor["sig_esm"])}
    for ligne in corps["signalements"]:
        assert ligne["version_application"] is None
        assert ligne["environnement"] is None
        assert ligne["resume_navigateur"] is None
        assert ligne["jeton_de_correlation"] is None
        #  Les colonnes METIER, elles, restent visibles.
        assert ligne["description"] == "Un bug."


@pytest.mark.integration
def test_adme_voit_toute_l_entite_en_detail_complet(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 2
    for ligne in corps["signalements"]:
        assert ligne["version_application"] == "0.10.0-test"


@pytest.mark.integration
def test_super_voit_n_importe_quelle_entite_en_detail_complet(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], decor["autre_code"], decor["jetons"]["super"])
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 1
    assert corps["signalements"][0]["identifiant"] == str(decor["sig_autre"])
    assert corps["signalements"][0]["version_application"] == "0.10.0-test"


@pytest.mark.integration
def test_isolation_un_adme_ne_voit_jamais_l_autre_entite(decor: dict[str, Any]) -> None:
    reponse = _lister(decor["parametres"], decor["code"], decor["jetons"]["adme"])
    assert reponse.status_code == 200, reponse.text
    identifiants = {ligne["identifiant"] for ligne in reponse.json()["signalements"]}
    assert str(decor["sig_autre"]) not in identifiants


@pytest.mark.integration
def test_le_filtre_etat_sert_de_compteur_back_office(decor: dict[str, Any]) -> None:
    with moteur(decor["parametres"]).begin() as cx:
        _signalement(
            cx,
            entite=decor["entite"],
            rapporteur=decor["dsm_personne"],
            description="Deja corrige.",
            state="fixed",
        )
    reponse = _lister(decor["parametres"], decor["code"], decor["jetons"]["adme"], etat="new")
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["total"] == 2
    assert all(ligne["etat"] == "new" for ligne in corps["signalements"])


# ===========================================================================
#  L'HISTORIQUE — `GET .../bug-reports/{signalement}/historique`
# ===========================================================================


@pytest.mark.integration
def test_historique_sans_session_401(decor: dict[str, Any]) -> None:
    reponse = _historique(decor["parametres"], decor["code"], decor["sig_dsm"], None)
    assert reponse.status_code == 401


@pytest.mark.integration
def test_historique_est_vide_avant_tout_traitement(decor: dict[str, Any]) -> None:
    reponse = _historique(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"]["dsm"]
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["evenements"] == []


@pytest.mark.integration
def test_historique_hors_du_perimetre_soi_est_un_404(decor: dict[str, Any]) -> None:
    """Le DSM ne voit que SES signalements (`Soi`) — celui de l'ESM lui est
    invisible, meme pour l'historique, meme discipline que la liste."""
    reponse = _historique(
        decor["parametres"], decor["code"], decor["sig_esm"], decor["jetons"]["dsm"]
    )
    assert reponse.status_code == 404


@pytest.mark.integration
def test_historique_isolation_entre_entites(decor: dict[str, Any]) -> None:
    reponse = _historique(
        decor["parametres"], decor["code"], decor["sig_autre"], decor["jetons"]["adme"]
    )
    assert reponse.status_code == 404


@pytest.mark.integration
def test_historique_reflete_les_changements_d_etat(decor: dict[str, Any]) -> None:
    modification = _modifier_l_etat(
        decor["parametres"],
        decor["code"],
        decor["sig_dsm"],
        decor["jetons"]["adme"],
        {"nouvel_etat": "investigating", "version": 1, "commentaire": "Pris en compte."},
    )
    assert modification.status_code == 200, modification.text

    #  Visible par l'ESM (lecture fonctionnelle de l'entite) ET par le DSM
    #  (son propre signalement) — deux perimetres differents, meme contenu.
    for role in ("esm", "dsm"):
        reponse = _historique(
            decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"][role]
        )
        assert reponse.status_code == 200, reponse.text
        (evenement,) = reponse.json()["evenements"]
        assert evenement["ancien_etat"] == "new"
        assert evenement["nouvel_etat"] == "investigating"
        assert evenement["commentaire"] == "Pris en compte."
        assert evenement["acteur_id"] == str(decor["adme_personne"])


# ===========================================================================
#  LE CHANGEMENT D'ETAT — `POST .../bug-reports/{signalement}/etat`
# ===========================================================================


@pytest.mark.integration
def test_etat_sans_session_401(decor: dict[str, Any]) -> None:
    corps = {"nouvel_etat": "investigating", "version": 1}
    reponse = _modifier_l_etat(decor["parametres"], decor["code"], decor["sig_dsm"], None, corps)
    assert reponse.status_code == 401


@pytest.mark.integration
@pytest.mark.parametrize("role", ["dsm", "esm", "booster", "office", "emp"])
def test_un_role_sans_droit_de_traitement_est_refuse(decor: dict[str, Any], role: str) -> None:
    """§17 « Modifier l'etat d'un signalement » : TIRET pour les cinq — y
    compris l'ESM, qui lit pourtant l'entite entiere (ligne du dessus)."""
    corps = {"nouvel_etat": "investigating", "version": 1}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"][role], corps
    )
    assert reponse.status_code == 403
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_le_refus_csrf_sans_origine_ni_jeton(decor: dict[str, Any]) -> None:
    """Temoin NEGATIF — le positif est chaque autre test de cette section (§7.39)."""
    corps = {"nouvel_etat": "investigating", "version": 1, "commentaire": "x"}
    reponse = _modifier_l_etat(
        decor["parametres"],
        decor["code"],
        decor["sig_dsm"],
        decor["jetons"]["adme"],
        corps,
        avec_csrf=False,
    )
    assert reponse.status_code == 403


@pytest.mark.integration
def test_adme_modifie_l_etat_sans_commentaire_obligatoire(decor: dict[str, Any]) -> None:
    """`ECART-064` ne s'applique qu'a `SUPER` : seul lui agit « dans une
    entite » au sens du §18.1 — l'ADM-E agit dans LA SIENNE."""
    corps = {"nouvel_etat": "fixed", "version": 1}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"]["adme"], corps
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json() == {"etat": "fixed", "version": 2}


@pytest.mark.integration
def test_super_sans_commentaire_rend_motif_obligatoire(decor: dict[str, Any]) -> None:
    corps = {"nouvel_etat": "rejected", "version": 1}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"]["super"], corps
    )
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "motif_obligatoire"


@pytest.mark.integration
def test_super_avec_commentaire_modifie_l_etat(decor: dict[str, Any]) -> None:
    """Temoin POSITIF appariee au precedent (§7.39) — meme appel, motif fourni."""
    corps = {"nouvel_etat": "rejected", "version": 1, "commentaire": "Non reproductible."}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"]["super"], corps
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json() == {"etat": "rejected", "version": 2}


@pytest.mark.integration
def test_version_perimee_rend_409_sans_ecrasement_silencieux(decor: dict[str, Any]) -> None:
    corps = {"nouvel_etat": "investigating", "version": 999, "commentaire": "x"}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"]["adme"], corps
    )
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "version_obsolete"


@pytest.mark.integration
def test_isolation_un_adme_ne_peut_pas_modifier_l_autre_entite(decor: dict[str, Any]) -> None:
    corps = {"nouvel_etat": "investigating", "version": 1, "commentaire": "x"}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_autre"], decor["jetons"]["adme"], corps
    )
    assert reponse.status_code == 404


@pytest.mark.integration
def test_l_audit_event_porte_les_valeurs_exactes(decor: dict[str, Any]) -> None:
    corps = {"nouvel_etat": "investigating", "version": 1, "commentaire": "Pris en compte."}
    reponse = _modifier_l_etat(
        decor["parametres"], decor["code"], decor["sig_dsm"], decor["jetons"]["adme"], corps
    )
    assert reponse.status_code == 200, reponse.text

    with moteur(decor["parametres"]).connect() as cx:
        ligne = (
            cx.execute(
                text(
                    "SELECT entity_id, actor_person_id, action_code, resource_type, "
                    "resource_reference, old_values, new_values, reason "
                    "FROM audit_event WHERE resource_type = 'bug_report' "
                    "AND resource_reference = :sig"
                ),
                {"sig": decor["sig_dsm"]},
            )
            .mappings()
            .one()
        )
    assert ligne["entity_id"] == decor["entite"]
    assert ligne["actor_person_id"] == decor["adme_personne"]
    assert ligne["action_code"] == "etat_de_signalement_modifie"
    assert ligne["resource_reference"] == decor["sig_dsm"]
    assert ligne["old_values"] == {"state": "new"}
    assert ligne["new_values"] == {"state": "investigating"}
    assert ligne["reason"] == "Pris en compte."
