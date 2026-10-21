"""Le journal d'audit en LECTURE, filtrable par perimetre — LOT 10, `T8`.

Matrice §16, `US001`/`US002` (clot). La derivation complete est dans l'en-tete
d'`app/audit/perimetre.py` et d'`app/audit/lecture.py` — ce fichier prouve
qu'elle tient, sur la pile reelle, par la route HTTP.

CE QUE CE FICHIER NE REPROUVE PAS

  Les sept fichiers `test_audit_*.py` prouvent deja que chaque domaine ECRIT
  `audit_event` correctement (T2-T7). Ce fichier teste la LECTURE : la plupart
  des evenements sont donc INSERES DIRECTEMENT dans `audit_event`, avec un
  `action_code` UNIQUE par temoin — exactement le patron deja retenu par
  `test_suivi_onboarding.py`, qui insere directement dans
  `onboarding_instance_task` plutot que d'appeler `terminer_une_tache`.
  Seul le temoin du contenu interdit et de la correlation (§3) appelle un
  VRAI service d'ecriture : c'est le seul endroit ou la question posee est
  « le pipeline ecriture-puis-lecture tient-il bout a bout ? ».

  **UN `action_code` UNIQUE PAR LIGNE INJECTEE, JAMAIS `resource_reference`,
  POUR DECIDER SI UNE LIGNE EST VUE.** `resource_reference` est masque pour
  qui n'a pas les details techniques (§16) — un temoin qui s'y fierait serait
  aveugle pour DSM/ESM/BOOST/OFFICE. Seul le temoin dedie (§4) compare
  `resource_reference` lui-meme, en lisant la MEME ligne avec deux roles.
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

from app.audit.services import DUREE_DE_RETENTION
from app.auth.services import demander_un_magic_link
from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeResponsabilite
from app.shared.correlation import definir_correlation, effacer_correlation
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
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


# ===========================================================================
#  CONSTRUCTION DU DECOR — une fonction par table, meme patron que
#  `test_suivi_onboarding.py`/`test_bureaux.py`
# ===========================================================================


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
            "account_state) VALUES (:a, :a, :prenom, 'T8L10', 'active') RETURNING id"
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


def _cercle(cx: Connection, entite: uuid.UUID, code: str, rang: int) -> uuid.UUID:
    #  `:code` et `:nom` SEPARES — `circle.code` est `varchar`, `circle.name`
    #  est `text` : un parametre partage entre les deux serait exactement le
    #  defaut `§7.25` de la passation (« inconsistent types deduced »).
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, :r) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code, "r": rang},
    ).scalar_one()


def _bureau(cx: Connection, entite: uuid.UUID, code: str, rang: int) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO office (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, :r) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code, "r": rang},
    ).scalar_one()


def _cercle_membership(
    cx: Connection, entite: uuid.UUID, appartenance: uuid.UUID, cercle: uuid.UUID
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
            "membership_type, starts_at) VALUES (:e, :m, :c, 'principal', :d) RETURNING id"
        ),
        {"e": entite, "m": appartenance, "c": cercle, "d": IL_Y_A_90_JOURS},
    ).scalar_one()


def _dsm_assignment(
    cx: Connection, entite: uuid.UUID, consultant_membership: uuid.UUID, dsm_personne: uuid.UUID
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO dsm_assignment (entity_id, consultant_membership_id, "
            "dsm_person_id, starts_at) VALUES (:e, :c, :d, :date) RETURNING id"
        ),
        {"e": entite, "c": consultant_membership, "d": dsm_personne, "date": IL_Y_A_90_JOURS},
    ).scalar_one()


def _responsabilite(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    type_responsabilite: str,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
) -> uuid.UUID:
    """Une responsabilite Framework — DSM/ESM/BOOSTER/OFFICE_MANAGER.

    `:p` sert `person_id` ET `assigned_by_person_id` : un partage legitime,
    comme `test_bureaux.py::_responsable` le fait deja (§7.25).
    """
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
            "responsibility_type, circle_id, office_id, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :t, :c, :b, :p, :d) RETURNING id"
        ),
        {
            "p": personne,
            "e": entite,
            "t": type_responsabilite,
            "c": cercle,
            "b": bureau,
            "d": IL_Y_A_90_JOURS,
        },
    ).scalar_one()


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


def _page(
    cx: Connection,
    entite: uuid.UUID,
    *,
    cercle: uuid.UUID | None = None,
    bureau: uuid.UUID | None = None,
) -> uuid.UUID:
    type_de_page = "CIRCLE" if cercle is not None else "OFFICE" if bureau is not None else "GENERAL"
    slug = f"t8l10-{uuid.uuid4().hex[:10]}"
    #  `:titre` et `:slug` SEPARES — `title` est `text`, `slug` est
    #  `varchar(160)` : meme classe de defaut que `_cercle`/`_bureau`
    #  ci-dessus, deja nommee par `test_bureaux.py::_page`.
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO content_page (entity_id, page_type, circle_id, office_id, title, "
            "slug, state) VALUES (:e, :type, :c, :b, :titre, :slug, 'published') RETURNING id"
        ),
        {"e": entite, "type": type_de_page, "c": cercle, "b": bureau, "titre": slug, "slug": slug},
    ).scalar_one()


def _evenement_calendaire(cx: Connection, entite: uuid.UUID) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO event (entity_id, title, starts_at, ends_at, state) "
            "VALUES (:e, 'T8L10', :debut, :fin, 'draft') RETURNING id"
        ),
        {"e": entite, "debut": ANCRAGE, "fin": ANCRAGE + dt.timedelta(hours=1)},
    ).scalar_one()


def _portee_cercle_de_l_evenement(
    cx: Connection, entite: uuid.UUID, evenement: uuid.UUID, cercle: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO event_circle_scope (entity_id, event_id, circle_id) VALUES (:e, :ev, :c)"
        ),
        {"e": entite, "ev": evenement, "c": cercle},
    )


def _portee_bureau_de_l_evenement(
    cx: Connection, entite: uuid.UUID, evenement: uuid.UUID, bureau: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO event_office_scope (entity_id, event_id, office_id) VALUES (:e, :ev, :b)"
        ),
        {"e": entite, "ev": evenement, "b": bureau},
    )


def _portee_dsm_de_l_evenement(
    cx: Connection, entite: uuid.UUID, evenement: uuid.UUID, dsm_personne: uuid.UUID
) -> None:
    cx.execute(
        text(
            "INSERT INTO event_dsm_scope (entity_id, event_id, dsm_person_id) VALUES (:e, :ev, :d)"
        ),
        {"e": entite, "ev": evenement, "d": dsm_personne},
    )


def _modele_onboarding(
    cx: Connection,
    entite: uuid.UUID,
    *,
    scope_type: str,
    scope_circle: uuid.UUID | None = None,
    scope_person: uuid.UUID | None = None,
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO onboarding_template (entity_id, name, target_status, scope_type, "
            "scope_person_id, scope_circle_id) "
            "VALUES (:e, 'Modele T8L10', 'mission', :st, :sp, :sc) RETURNING id"
        ),
        {"e": entite, "st": scope_type, "sp": scope_person, "sc": scope_circle},
    ).scalar_one()


def _evenement_d_audit(
    cx: Connection,
    *,
    entite: uuid.UUID | None,
    resource_type: str,
    action_code: str,
    resource_reference: uuid.UUID | None = None,
    actor_person_id: uuid.UUID | None = None,
    actor_service_account_id: uuid.UUID | None = None,
    summary: str = "Evenement de test T8",
    occurred_at: dt.datetime = ANCRAGE,
) -> uuid.UUID:
    """Une ligne `audit_event`, inseree DIRECTEMENT — voir l'en-tete du fichier.

    `retention_until` est EXPLICITE, le MEME calcul que
    `app.audit.services.DUREE_DE_RETENTION` — jamais laisse au defaut serveur
    de la table, qui calculerait depuis `now()` et non depuis `occurred_at`
    (meme piege que celui que `app/audit/services.py` evite deja, voir son
    en-tete, §7.0 sixieme proposition)."""
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO audit_event (entity_id, actor_person_id, actor_service_account_id, "
            "action_code, resource_type, resource_reference, summary, correlation_token, "
            "occurred_at, retention_until) "
            "VALUES (:e, :ap, :asa, :ac, :rt, :rr, :s, :corr, :occ, :retenu) RETURNING id"
        ),
        {
            "e": entite,
            "ap": actor_person_id,
            "asa": actor_service_account_id,
            "ac": action_code,
            "rt": resource_type,
            "rr": resource_reference,
            "s": summary,
            "corr": f"corr-{uuid.uuid4().hex[:12]}",
            "occ": occurred_at,
            "retenu": occurred_at + DUREE_DE_RETENTION,
        },
    ).scalar_one()


def _compte_de_service(cx: Connection, entite: uuid.UUID | None, marqueur: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO service_account (name, entity_id, state, technical_owner_person_id) "
            "VALUES (:n, :e, 'active', :proprietaire) RETURNING id"
        ),
        {
            "n": f"{marqueur}-service",
            "e": entite,
            "proprietaire": _personne(cx, marqueur, "proprio"),
        },
    ).scalar_one()


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx, personne=personne, instant=ANCRAGE, jours_absolus=parametres.SESSION_ABSOLUTE_DAYS
        )
    return jeton


def _lire(parametres: Parametres, code: str, jeton: str | None, **params: object) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(CHEMIN_AUDIT.format(code=code), params=params)


def _codes_vus(reponse: Any) -> set[str]:
    return {e["action_code"] for e in reponse.json()["evenements"]}


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t8l10{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres, "marqueur": marqueur}

    with moteur(parametres).begin() as cx:
        #  Une seconde ligne GLOBALE, bornee dans le passe — §7.47, meme
        #  theatre que `test_analyse_import.py`. `make domaines-provision`
        #  seme `exalt-company.com` avec `starts_at = now()` AU MOMENT OU
        #  `make migrate` tourne en integration continue ; `ANCRAGE` est
        #  derive de `now()` AU MOMENT DE LA COLLECTE de ce module, souvent
        #  plus TARD. L'ecart entre les deux peut neanmoins depasser le
        #  tampon de 10 minutes d'`ANCRAGE` selon la duree des etapes qui
        #  precedent `residu-check` — auquel cas la ligne semee ne couvre
        #  pas encore `ANCRAGE`, et le temoin du §3 recevrait
        #  `domaine_non_autorise` au lieu de `lien_emis`. Une seconde ligne
        #  globale, sans fin et anterieure a toute date possible, ferme la
        #  question sans dependre de l'instant de demarrage de la stack.
        #  Capturee par identifiant pour n'effacer QUE celle-ci au menage.
        r["domaine_global_id"] = cx.execute(
            text(
                "INSERT INTO allowed_email_domain (domain, entity_id, starts_at) "
                "VALUES ('exalt-company.com', NULL, '2020-01-01T00:00:00+00:00') "
                "RETURNING id"
            )
        ).scalar_one()

        entite = _entite(cx, f"{marqueur}-home")
        autre_entite = _entite(cx, f"{marqueur}-autre")
        r["entite"] = entite
        r["code"] = f"{marqueur}-home"
        r["autre_entite"] = autre_entite
        r["autre_code"] = f"{marqueur}-autre"

        cercle_a = _cercle(cx, entite, f"{marqueur}-ca", 0)
        cercle_b = _cercle(cx, entite, f"{marqueur}-cb", 1)
        #  Un TROISIEME cercle, dedie au temoin de cumul : un seul Booster
        #  ACTIF par cercle (`uq_framework_responsibility_booster_actif_par_
        #  cercle`) interdit de reutiliser `cercle_a`, deja Booste par
        #  `booster_a_personne`.
        cercle_cumul = _cercle(cx, entite, f"{marqueur}-ccumul", 2)
        bureau_a = _bureau(cx, entite, f"{marqueur}-ba", 0)
        bureau_b = _bureau(cx, entite, f"{marqueur}-bb", 1)
        r["cercle_a"] = cercle_a
        r["cercle_b"] = cercle_b
        r["cercle_cumul"] = cercle_cumul
        r["bureau_a"] = bureau_a
        r["bureau_b"] = bureau_b

        for role, suffixe in (
            ("esm", "esm"),
            ("dsm", "dsm"),
            ("booster_a", "boo-a"),
            ("booster_b", "boo-b"),
            ("office_a", "off-a"),
            ("office_b", "off-b"),
            ("adme", "adme"),
            ("super", "super"),
            ("emp", "emp"),
            ("cumul", "cumul"),
        ):
            personne = _personne(cx, marqueur, suffixe)
            _appartenance(cx, entite, personne)
            r[f"{role}_personne"] = personne

        _responsabilite(cx, entite, r["esm_personne"], TypeResponsabilite.ESM.value)
        _responsabilite(cx, entite, r["dsm_personne"], TypeResponsabilite.DSM.value)
        r["fra_booster_a"] = _responsabilite(
            cx, entite, r["booster_a_personne"], TypeResponsabilite.BOOSTER.value, cercle=cercle_a
        )
        _responsabilite(
            cx, entite, r["booster_b_personne"], TypeResponsabilite.BOOSTER.value, cercle=cercle_b
        )
        r["fra_office_a"] = _responsabilite(
            cx,
            entite,
            r["office_a_personne"],
            TypeResponsabilite.OFFICE_MANAGER.value,
            bureau=bureau_a,
        )
        _responsabilite(
            cx,
            entite,
            r["office_b_personne"],
            TypeResponsabilite.OFFICE_MANAGER.value,
            bureau=bureau_b,
        )
        #  Cumul : DSM ET Booster du cercle A, pour la precedence du perimetre
        #  (CERCLE, le plus large des deux — voir `resoudre_le_perimetre_de_l_audit`).
        _responsabilite(cx, entite, r["cumul_personne"], TypeResponsabilite.DSM.value)
        _responsabilite(
            cx, entite, r["cumul_personne"], TypeResponsabilite.BOOSTER.value, cercle=cercle_cumul
        )
        _role_technique(cx, r["adme_personne"], entite, "ENTITY_ADMIN")
        _role_technique(cx, r["super_personne"], None, "SUPER_ADMIN")

        #  Un consultant du DSM, et un membre de chaque cercle — personnes
        #  DISTINCTES de l'acteur, pour que les temoins de perimetre portent
        #  sur la RESSOURCE et non sur l'acteur lui-meme.
        consultant_personne = _personne(cx, marqueur, "consultant")
        consultant_appartenance = _appartenance(cx, entite, consultant_personne)
        r["consultant_personne"] = consultant_personne
        r["dsm_assignment_id"] = _dsm_assignment(
            cx, entite, consultant_appartenance, r["dsm_personne"]
        )

        non_rattache_personne = _personne(cx, marqueur, "non-rattache")
        _appartenance(cx, entite, non_rattache_personne)
        r["non_rattache_personne"] = non_rattache_personne

        membre_cercle_a_personne = _personne(cx, marqueur, "membre-ca")
        membre_cercle_a_appartenance = _appartenance(cx, entite, membre_cercle_a_personne)
        r["membre_cercle_a_personne"] = membre_cercle_a_personne
        r["circle_membership_id"] = _cercle_membership(
            cx, entite, membre_cercle_a_appartenance, cercle_a
        )

        membre_cercle_b_personne = _personne(cx, marqueur, "membre-cb")
        membre_cercle_b_appartenance = _appartenance(cx, entite, membre_cercle_b_personne)
        r["membre_cercle_b_personne"] = membre_cercle_b_personne
        _cercle_membership(cx, entite, membre_cercle_b_appartenance, cercle_b)

        #  Contenu et evenements rattaches a CHAQUE cercle/bureau — pour les
        #  temoins d'extension du perimetre (arbitrage de Jonathan, §2).
        r["page_cercle_a"] = _page(cx, entite, cercle=cercle_a)
        r["page_bureau_a"] = _page(cx, entite, bureau=bureau_a)

        evenement_cercle = _evenement_calendaire(cx, entite)
        _portee_cercle_de_l_evenement(cx, entite, evenement_cercle, cercle_a)
        r["evenement_cercle_a"] = evenement_cercle

        evenement_bureau = _evenement_calendaire(cx, entite)
        _portee_bureau_de_l_evenement(cx, entite, evenement_bureau, bureau_a)
        r["evenement_bureau_a"] = evenement_bureau

        evenement_dsm = _evenement_calendaire(cx, entite)
        _portee_dsm_de_l_evenement(cx, entite, evenement_dsm, r["dsm_personne"])
        r["evenement_dsm"] = evenement_dsm

        r["modele_cercle_a"] = _modele_onboarding(
            cx, entite, scope_type="CIRCLE", scope_circle=cercle_a
        )
        r["modele_dsm"] = _modele_onboarding(
            cx, entite, scope_type="DSM", scope_person=r["dsm_personne"]
        )

        #  Un compte de service scope a l'entite — arbitrage Q1 etendu.
        r["compte_de_service"] = _compte_de_service(cx, entite, marqueur)

        #  Une personne dans l'AUTRE entite, pour le temoin d'asymetrie ENTITE.
        autre_personne = _personne(cx, marqueur, "autre-entite")
        _appartenance(cx, autre_entite, autre_personne)
        r["autre_entite_personne"] = autre_personne
        autre_esm = _personne(cx, marqueur, "autre-esm")
        _appartenance(cx, autre_entite, autre_esm)
        _responsabilite(cx, autre_entite, autre_esm, TypeResponsabilite.ESM.value)
        r["autre_esm_personne"] = autre_esm

    r["jetons"] = {
        role: _session(parametres, r[f"{role}_personne"])
        for role in (
            "esm",
            "dsm",
            "booster_a",
            "booster_b",
            "office_a",
            "office_b",
            "adme",
            "super",
            "emp",
            "cumul",
        )
    }
    r["jeton_autre_esm"] = _session(parametres, r["autre_esm_personne"])

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM allowed_email_domain WHERE id = :domaine_global_id",
            "DELETE FROM audit_event WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR actor_person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne) OR "
            "actor_service_account_id IN "
            "(SELECT id FROM service_account WHERE name LIKE :motif_service)",
            "DELETE FROM event_circle_scope WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM event_office_scope WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM event_dsm_scope WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM event WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM content_page WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM onboarding_template WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM dsm_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM technical_role_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif) OR person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            #  `demander_un_magic_link` (temoin du contenu interdit, §3) ecrit
            #  AUSSI dans `magic_link_request` — AVANT `person`, qu'elle
            #  reference.
            "DELETE FROM magic_link_request WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM service_account WHERE name LIKE :motif_service",
            "DELETE FROM office WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM person WHERE email LIKE :motif_personne",
            "DELETE FROM entity WHERE code LIKE :motif",
        ):
            menage.execute(
                text(requete),
                {
                    "motif": f"{marqueur}%",
                    "motif_personne": f"{marqueur}-%",
                    "motif_service": f"{marqueur}-service",
                    "domaine_global_id": r["domaine_global_id"],
                },
            )


# ===========================================================================
#  LES GARDES — session, role, entite
# ===========================================================================


@pytest.mark.integration
def test_sans_session_401(decor: dict[str, Any]) -> None:
    reponse = _lire(decor["parametres"], decor["code"], None)
    assert reponse.status_code == 401


@pytest.mark.integration
def test_role_sans_droit_d_audit_est_refuse(decor: dict[str, Any]) -> None:
    """`EMP` n'est dans AUCUN des six roles du §16 — refus 403, jamais 200
    vide : un refus et une liste vide donneraient la meme observation a un
    appelant qui ne lirait pas le code (§7.0)."""
    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["emp"])
    assert reponse.status_code == 403
    assert reponse.json()["erreur"]["code"] == "acces_refuse"


@pytest.mark.integration
def test_entite_inconnue_est_un_404(decor: dict[str, Any]) -> None:
    reponse = _lire(decor["parametres"], f"{decor['marqueur']}-fantome", decor["jetons"]["adme"])
    assert reponse.status_code == 404


# ===========================================================================
#  PERIMETRE ENTITE — ESM/ADM-E/SUPER, et l'arbitrage sur les evenements
#  sans entite (authentification)
# ===========================================================================


@pytest.mark.integration
def test_les_roles_de_portee_entite_voient_leur_entite_et_pas_une_autre(
    decor: dict[str, Any],
) -> None:
    code_temoin = f"entite-{uuid.uuid4().hex[:10]}"
    code_ailleurs = f"ailleurs-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_temoin
        )
        _evenement_d_audit(
            cx, entite=decor["autre_entite"], resource_type="person", action_code=code_ailleurs
        )

    for role in ("esm", "adme", "super"):
        reponse = _lire(decor["parametres"], decor["code"], decor["jetons"][role])
        assert reponse.status_code == 200, (role, reponse.text)
        vus = _codes_vus(reponse)
        assert code_temoin in vus, (role, vus)
        assert code_ailleurs not in vus, (role, vus)

    #  SUPER, lui, atteint AUSSI l'autre entite — `Global`, §16 — en appelant
    #  la MEME route pour ce code precis (meme mecanisme que le reporting du
    #  LOT 9 T5 : « Global » n'est jamais une route separee).
    reponse = _lire(decor["parametres"], decor["autre_code"], decor["jetons"]["super"])
    assert reponse.status_code == 200
    assert code_ailleurs in _codes_vus(reponse)


@pytest.mark.integration
def test_un_evenement_sans_entite_est_retrouve_par_l_entite_actuelle_de_l_acteur(
    decor: dict[str, Any],
) -> None:
    """Arbitrage de Jonathan : une connexion/magic link (`entity_id` NULL,
    T2) est retrouvee par le journal de l'entite ou l'acteur travaille
    AUJOURD'HUI — jamais par un simple `entity_id = :entite`."""
    code_temoin = f"sans-entite-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=None,
            resource_type="magic_link_request",
            action_code=code_temoin,
            actor_person_id=decor["non_rattache_personne"],
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["esm"])
    assert reponse.status_code == 200
    assert code_temoin in _codes_vus(reponse)


@pytest.mark.integration
def test_le_meme_evenement_sans_entite_est_absent_du_journal_d_une_autre_entite(
    decor: dict[str, Any],
) -> None:
    """Le temoin NEGATIF de l'arbitrage precedent : sans lui, un `entity_id`
    NULL pourrait etre lu comme « visible de partout » — ce qui serait une
    fuite inter-entites (§25.3 du cahier)."""
    code_temoin = f"sans-entite-ailleurs-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=None,
            resource_type="magic_link_request",
            action_code=code_temoin,
            actor_person_id=decor["non_rattache_personne"],
        )

    reponse = _lire(decor["parametres"], decor["autre_code"], decor["jeton_autre_esm"])
    assert reponse.status_code == 200
    assert code_temoin not in _codes_vus(reponse)


@pytest.mark.integration
def test_un_compte_de_service_sans_entite_est_retrouve_par_son_entite(
    decor: dict[str, Any],
) -> None:
    code_temoin = f"service-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=None,
            resource_type="service_account",
            action_code=code_temoin,
            actor_service_account_id=decor["compte_de_service"],
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["esm"])
    assert reponse.status_code == 200
    assert code_temoin in _codes_vus(reponse)


# ===========================================================================
#  PERIMETRE CONSULTANTS — DSM
# ===========================================================================


@pytest.mark.integration
def test_dsm_voit_son_consultant_mais_pas_une_personne_non_rattachee(
    decor: dict[str, Any],
) -> None:
    code_consultant = f"consultant-{uuid.uuid4().hex[:10]}"
    code_etranger = f"etranger-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_consultant,
            resource_reference=decor["consultant_personne"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_etranger,
            resource_reference=decor["non_rattache_personne"],
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["dsm"])
    assert reponse.status_code == 200
    vus = _codes_vus(reponse)
    assert code_consultant in vus
    assert code_etranger not in vus


@pytest.mark.integration
def test_dsm_voit_aussi_les_autres_ressources_de_son_perimetre(decor: dict[str, Any]) -> None:
    """Second arbitrage de Jonathan : le DSM n'est pas limite au domaine
    personnes — `dsm_assignment`, `event` (via `event_dsm_scope`, LOT 8 T3) et
    `onboarding_template` (`scope_type='DSM'`, LOT 7 T5) le designent aussi
    DIRECTEMENT."""
    code_assignation = f"assignation-{uuid.uuid4().hex[:10]}"
    code_evenement = f"evenement-dsm-{uuid.uuid4().hex[:10]}"
    code_modele = f"modele-dsm-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="dsm_assignment",
            action_code=code_assignation,
            resource_reference=decor["dsm_assignment_id"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="event",
            action_code=code_evenement,
            resource_reference=decor["evenement_dsm"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="onboarding_template",
            action_code=code_modele,
            resource_reference=decor["modele_dsm"],
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["dsm"])
    assert reponse.status_code == 200
    vus = _codes_vus(reponse)
    assert {code_assignation, code_evenement, code_modele} <= vus


# ===========================================================================
#  PERIMETRE CERCLE — Booster
# ===========================================================================


@pytest.mark.integration
def test_booster_voit_les_membres_de_son_cercle_mais_pas_d_un_autre_cercle(
    decor: dict[str, Any],
) -> None:
    code_cercle_a = f"membre-ca-{uuid.uuid4().hex[:10]}"
    code_cercle_b = f"membre-cb-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_cercle_a,
            resource_reference=decor["membre_cercle_a_personne"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_cercle_b,
            resource_reference=decor["membre_cercle_b_personne"],
        )

    reponse_a = _lire(decor["parametres"], decor["code"], decor["jetons"]["booster_a"])
    assert reponse_a.status_code == 200
    vus_a = _codes_vus(reponse_a)
    assert code_cercle_a in vus_a
    assert code_cercle_b not in vus_a

    reponse_b = _lire(decor["parametres"], decor["code"], decor["jetons"]["booster_b"])
    vus_b = _codes_vus(reponse_b)
    assert code_cercle_b in vus_b
    assert code_cercle_a not in vus_b


@pytest.mark.integration
def test_booster_voit_les_autres_ressources_de_son_cercle_mais_pas_de_l_autre(
    decor: dict[str, Any],
) -> None:
    """Le cercle lui-meme, l'appartenance a son cercle, la responsabilite
    Framework qui le designe, le contenu et l'evenement rattaches — fidele au
    mot choisi par la matrice (`Cercle`, pas `Consultants`, voir l'en-tete
    d'`app/audit/lecture.py`)."""
    code_cercle = f"cercle-lui-meme-{uuid.uuid4().hex[:10]}"
    code_appartenance = f"appartenance-ca-{uuid.uuid4().hex[:10]}"
    code_responsabilite = f"responsabilite-ca-{uuid.uuid4().hex[:10]}"
    code_page = f"page-ca-{uuid.uuid4().hex[:10]}"
    code_evenement = f"evenement-ca-{uuid.uuid4().hex[:10]}"
    code_modele = f"modele-ca-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="circle",
            action_code=code_cercle,
            resource_reference=decor["cercle_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="circle_membership",
            action_code=code_appartenance,
            resource_reference=decor["circle_membership_id"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="framework_responsibility_assignment",
            action_code=code_responsabilite,
            resource_reference=decor["fra_booster_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="content_page",
            action_code=code_page,
            resource_reference=decor["page_cercle_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="event",
            action_code=code_evenement,
            resource_reference=decor["evenement_cercle_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="onboarding_template",
            action_code=code_modele,
            resource_reference=decor["modele_cercle_a"],
        )

    attendus = {
        code_cercle,
        code_appartenance,
        code_responsabilite,
        code_page,
        code_evenement,
        code_modele,
    }
    reponse_a = _lire(decor["parametres"], decor["code"], decor["jetons"]["booster_a"])
    assert attendus <= _codes_vus(reponse_a)

    reponse_b = _lire(decor["parametres"], decor["code"], decor["jetons"]["booster_b"])
    assert attendus.isdisjoint(_codes_vus(reponse_b))


# ===========================================================================
#  PERIMETRE BUREAU — responsable de bureau
# ===========================================================================


@pytest.mark.integration
def test_responsable_de_bureau_voit_les_ressources_de_son_bureau_mais_pas_de_l_autre(
    decor: dict[str, Any],
) -> None:
    """Pas de `person` ni d'`entity_membership` ici — aucune table
    d'appartenance a un bureau n'existe (`ECART-059`/`DEC-576`, voir
    l'en-tete d'`app/audit/lecture.py`)."""
    code_bureau = f"bureau-lui-meme-{uuid.uuid4().hex[:10]}"
    code_responsabilite = f"responsabilite-ba-{uuid.uuid4().hex[:10]}"
    code_page = f"page-ba-{uuid.uuid4().hex[:10]}"
    code_evenement = f"evenement-ba-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="office",
            action_code=code_bureau,
            resource_reference=decor["bureau_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="framework_responsibility_assignment",
            action_code=code_responsabilite,
            resource_reference=decor["fra_office_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="content_page",
            action_code=code_page,
            resource_reference=decor["page_bureau_a"],
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="event",
            action_code=code_evenement,
            resource_reference=decor["evenement_bureau_a"],
        )

    attendus = {code_bureau, code_responsabilite, code_page, code_evenement}
    reponse_a = _lire(decor["parametres"], decor["code"], decor["jetons"]["office_a"])
    assert attendus <= _codes_vus(reponse_a)

    reponse_b = _lire(decor["parametres"], decor["code"], decor["jetons"]["office_b"])
    assert attendus.isdisjoint(_codes_vus(reponse_b))


@pytest.mark.integration
def test_responsable_de_bureau_ne_voit_jamais_les_evenements_sur_des_personnes(
    decor: dict[str, Any],
) -> None:
    code_temoin = f"personne-pour-bureau-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_temoin,
            resource_reference=decor["membre_cercle_a_personne"],
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["office_a"])
    assert code_temoin not in _codes_vus(reponse)


# ===========================================================================
#  CUMUL DE ROLES — la portee la plus large gagne
# ===========================================================================


@pytest.mark.integration
def test_cumul_dsm_et_booster_recoit_le_perimetre_cercle_le_plus_large(
    decor: dict[str, Any],
) -> None:
    """La personne `cumul` porte DSM ET Booster de son propre cercle — elle
    doit voir ce que Booster voit (Cercle), strictement plus large que
    Consultants."""
    code_cercle = f"cumul-cercle-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="circle",
            action_code=code_cercle,
            resource_reference=decor["cercle_cumul"],
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["cumul"])
    assert reponse.status_code == 200
    assert code_cercle in _codes_vus(reponse)


# ===========================================================================
#  DETAILS TECHNIQUES — §16, ADM-E/SUPER seuls
# ===========================================================================


@pytest.mark.integration
def test_seuls_adm_e_et_super_voient_les_details_techniques(decor: dict[str, Any]) -> None:
    """MEME ligne, deux lecteurs : `resource_reference`/`correlation_token`
    sont presents pour ADM-E et SUPER, `null` pour les quatre autres roles —
    jamais un champ absent de la colonne, une colonne masquee (§7.39)."""
    code_temoin = f"details-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_temoin,
            resource_reference=decor["consultant_personne"],
        )

    def _ligne(reponse: Any) -> dict[str, Any]:
        trouvees = [e for e in reponse.json()["evenements"] if e["action_code"] == code_temoin]
        assert len(trouvees) == 1
        return trouvees[0]  # type: ignore[no-any-return]

    for role in ("adme", "super"):
        ligne = _ligne(_lire(decor["parametres"], decor["code"], decor["jetons"][role]))
        assert ligne["resource_reference"] == str(decor["consultant_personne"])
        assert ligne["correlation_token"] is not None

    for role in ("esm", "dsm"):
        ligne = _ligne(_lire(decor["parametres"], decor["code"], decor["jetons"][role]))
        assert ligne["resource_reference"] is None
        assert ligne["correlation_token"] is None
        #  Les deux ont neanmoins le reste : le masquage est ETROIT, pas un
        #  refus deguise (§7.0, sixieme proposition : ne pas comparer ce qui
        #  n'est pas de la meme nature).
        assert ligne["summary"]
        assert ligne["action_code"] == code_temoin


# ===========================================================================
#  CONTENU INTERDIT ET CORRELATION — le VRAI pipeline ecriture-puis-lecture
# ===========================================================================


@pytest.mark.integration
def test_aucune_donnee_interdite_et_la_correlation_est_tracee(decor: dict[str, Any]) -> None:
    """Un VRAI magic link demande (`app.auth.services.demander_un_magic_link`,
    T2) : son `audit_event` ne porte jamais l'adresse ni de jeton (§16.2),
    MAIS porte un resume informatif et l'identifiant de correlation courant —
    critere de sortie 2 et 5 de la fiche."""
    identifiant = definir_correlation(f"correlation-t8-{uuid.uuid4().hex[:10]}")
    adresse = None
    try:
        with moteur(decor["parametres"]).begin() as cx:
            personne = decor["consultant_personne"]
            adresse = cx.execute(
                text("SELECT email FROM person WHERE id = :p"), {"p": personne}
            ).scalar_one()
            demander_un_magic_link(
                cx,
                adresse=adresse,
                instant=ANCRAGE,
                base_publique="https://app.onboarding.localhost",
            )

        reponse = _lire(
            decor["parametres"],
            decor["code"],
            decor["jetons"]["adme"],
            resource_type="magic_link_request",
        )
        assert reponse.status_code == 200
        lignes = [e for e in reponse.json()["evenements"] if e["actor_person_id"] == str(personne)]
        assert len(lignes) == 1, lignes
        ligne = lignes[0]

        brut = str(ligne)
        assert adresse not in brut
        assert "lien_emis" in ligne["summary"]
        assert ligne["correlation_token"] == identifiant
    finally:
        effacer_correlation()


@pytest.mark.integration
def test_retention_jusqua_est_un_an_apres_l_occurrence(decor: dict[str, Any]) -> None:
    code_temoin = f"retention-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx, entite=decor["entite"], resource_type="person", action_code=code_temoin
        )

    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["esm"])
    ligne = next(e for e in reponse.json()["evenements"] if e["action_code"] == code_temoin)
    occurred_at = dt.datetime.fromisoformat(ligne["occurred_at"])
    retention_until = dt.datetime.fromisoformat(ligne["retention_until"])
    assert (retention_until - occurred_at) == dt.timedelta(days=365)


# ===========================================================================
#  LES CINQ FILTRES DE RECHERCHE
# ===========================================================================


@pytest.mark.integration
def test_les_cinq_filtres_de_recherche(decor: dict[str, Any]) -> None:
    code_cible = f"cible-{uuid.uuid4().hex[:10]}"
    code_autre = f"autre-{uuid.uuid4().hex[:10]}"
    avant = ANCRAGE - dt.timedelta(days=2)
    with moteur(decor["parametres"]).begin() as cx:
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="person",
            action_code=code_cible,
            resource_reference=decor["consultant_personne"],
            actor_person_id=decor["esm_personne"],
            occurred_at=ANCRAGE,
        )
        _evenement_d_audit(
            cx,
            entite=decor["entite"],
            resource_type="circle",
            action_code=code_autre,
            resource_reference=decor["cercle_a"],
            actor_person_id=decor["booster_a_personne"],
            occurred_at=avant,
        )

    jeton = decor["jetons"]["adme"]
    code = decor["code"]
    parametres = decor["parametres"]

    #  action_code
    vus = _codes_vus(_lire(parametres, code, jeton, action_code=code_cible))
    assert vus == {code_cible}

    #  resource_type
    vus = _codes_vus(_lire(parametres, code, jeton, resource_type="circle"))
    assert code_autre in vus
    assert code_cible not in vus

    #  acteur
    vus = _codes_vus(_lire(parametres, code, jeton, acteur=str(decor["esm_personne"])))
    assert code_cible in vus
    assert code_autre not in vus

    #  depuis : exclut l'evenement d'AVANT-HIER
    vus = _codes_vus(
        _lire(parametres, code, jeton, depuis=(ANCRAGE - dt.timedelta(hours=1)).isoformat())
    )
    assert code_cible in vus
    assert code_autre not in vus

    #  jusqua : exclut l'evenement d'AUJOURD'HUI, garde celui d'avant-hier
    vus = _codes_vus(
        _lire(parametres, code, jeton, jusqua=(ANCRAGE - dt.timedelta(hours=1)).isoformat())
    )
    assert code_autre in vus
    assert code_cible not in vus


# ===========================================================================
#  PAGINATION — cahier §18.2, meme discipline que le suivi (LOT 7, T12)
# ===========================================================================


@pytest.mark.integration
def test_la_taille_hors_liste_est_refusee_422(decor: dict[str, Any]) -> None:
    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["adme"], taille=37)
    assert reponse.status_code == 422


@pytest.mark.integration
def test_la_page_invalide_est_refusee_422(decor: dict[str, Any]) -> None:
    reponse = _lire(decor["parametres"], decor["code"], decor["jetons"]["adme"], page=0)
    assert reponse.status_code == 422


@pytest.mark.integration
def test_la_pagination_rend_le_total_et_les_pages_corrects(decor: dict[str, Any]) -> None:
    code_commun = f"pagination-{uuid.uuid4().hex[:10]}"
    with moteur(decor["parametres"]).begin() as cx:
        for _ in range(3):
            _evenement_d_audit(
                cx, entite=decor["entite"], resource_type="person", action_code=code_commun
            )

    reponse = _lire(
        decor["parametres"],
        decor["code"],
        decor["jetons"]["adme"],
        action_code=code_commun,
        taille=25,
        page=1,
    )
    corps = reponse.json()
    assert corps["total"] == 3
    assert corps["pages"] == 1
    assert corps["page"] == 1
    assert corps["taille"] == 25
    assert len(corps["evenements"]) == 3
