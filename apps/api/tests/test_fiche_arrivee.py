"""La fiche d'arrivee en lecture — LOT 7, `T2`, `MVP-L07-US001`.

LE TEMOIN LE PLUS IMPORTANT DE CE FICHIER N'EST PAS UN REFUS ORDINAIRE

  Matrice §7 : `DSM` est a TIRET sur « Consulter sa fiche non publiee » et
  « Consulter les informations preremplies », alors qu'il porte « Consultants »
  ailleurs dans la MEME annexe — §8.1, « Modifier les informations
  organisationnelles ». Un DSM authentique, rattache au bon consultant, DOIT
  quand meme recevoir un 403 ici : c'est le piege §2.1 de `fiche-lot-7.md`, et
  un test qui se contenterait d'un DSM SANS rattachement ne le prouverait pas
  — il prouverait « DSM » refuse « inconnu », pas « DSM » refuse « le sien ».

LA POPULATION EST PLUS LARGE QUE CELLE DU TROMBINOSCOPE, ET C'EST LE POINT

  Un nouvel arrivant est `future` avant son premier jour. `lire_la_fiche`
  (LOT 5) filtre par defaut sur `active`/`published` ; `T2` l'appelle avec
  `ETATS_OCCUPANTS` et les trois visibilites. Un membre `future` DOIT rester
  lisible — sinon la fiche que le cahier §9.4 demande avant l'arrivee
  n'existerait jamais.

AUCUNE LIGNE `arrival_profile` N'EST CREEE PAR UNE LECTURE

  `id` et `version` valent `null` tant que `T3` n'a rien ecrit. Un test le
  prouve, et prouve aussi que la lecture n'a RIEN ecrit — la ligne reste
  absente apres l'appel.
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

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.organization.modeles import TypeAppartenanceCercle, TypeResponsabilite
from app.people.modeles import EtatAppartenance
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN = "/api/v1/entities/{code}/people/{appartenance}/arrival-profile"

ANCRAGE = dt.datetime(2026, 9, 25, 9, 0, tzinfo=dt.UTC)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


def _personne(cx: Connection, marqueur: str, suffixe: str) -> uuid.UUID:
    adresse = f"{marqueur}-{suffixe}@exemple.test"
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO person (email, email_normalized, first_name, last_name, "
                    "account_state) VALUES (:a, :a, :prenom, 'T2', 'active') RETURNING id"
                ),
                {"a": adresse, "prenom": suffixe},
            ).scalar_one()
        )
    )


def _appartenance(
    cx: Connection,
    entite: uuid.UUID,
    personne: uuid.UUID,
    *,
    etat: str = EtatAppartenance.ACTIVE.value,
    arrivee: dt.date = dt.date(2026, 9, 1),
) -> uuid.UUID:
    return uuid.UUID(
        str(
            cx.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, :arrivee, :etat, 'consultant', 'draft') RETURNING id"
                ),
                {"p": personne, "e": entite, "arrivee": arrivee, "etat": etat},
            ).scalar_one()
        )
    )


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx,
            personne=personne,
            instant=dt.datetime.now(tz=dt.UTC),
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
    return jeton


def _appeler(parametres: Parametres, chemin: str, jeton: str) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite, un nouvel arrivant FUTURE, un DSM RATTACHE, un ESM, un EMP nu."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t2l7{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres}

    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-e", "nom": marqueur},
        ).scalar_one()
        r["entite"] = entite
        r["code"] = f"{marqueur}-e"

        autre = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Lille', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-a", "nom": f"{marqueur}-autre"},
        ).scalar_one()
        r["autre_entite"] = autre

        #  Le nouvel arrivant, FUTURE — la population que T2 ouvre.
        r["arrivant_personne"] = _personne(cx, marqueur, "arrivant")
        r["arrivant"] = _appartenance(
            cx,
            entite,
            r["arrivant_personne"],
            etat=EtatAppartenance.FUTURE.value,
            arrivee=dt.date(2026, 10, 15),
        )

        #  DEUX parametres distincts, jamais un seul reutilise : `code` est
        #  `character varying`, `name` est `text` — §7.25.
        r["cercle"] = cx.execute(
            text(
                "INSERT INTO circle (entity_id, code, name, display_order) "
                "VALUES (:e, :c, :n, 0) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-cercle", "n": f"{marqueur}-cercle"},
        ).scalar_one()
        #  Le Booster du cercle ci-dessus — pour le temoin positif du §7.
        #  **`resoudre_les_permissions` N'ACCORDE UN ROLE DE RESPONSABILITE QUE
        #  DANS L'ENTITE PRINCIPALE DE L'ACTEUR** — §5.1, `est_principale` dans
        #  `app/permissions/services.py`. Sans sa PROPRE appartenance ICI, le
        #  Booster n'a AUCUN role dans cette entite, quelle que soit sa
        #  responsabilite. Meme motif pour l'ESM et le DSM ci-dessous.
        r["booster_personne"] = _personne(cx, marqueur, "booster")
        _appartenance(cx, entite, r["booster_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, circle_id, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, :type, :c, :p, :d)"
            ),
            {
                "p": r["booster_personne"],
                "e": entite,
                "type": TypeResponsabilite.BOOSTER.value,
                "c": r["cercle"],
                "d": ANCRAGE - dt.timedelta(days=1),
            },
        )
        cx.execute(
            text(
                "INSERT INTO circle_membership (entity_id, entity_membership_id, circle_id, "
                "membership_type, starts_at) VALUES (:e, :m, :c, :type, :d)"
            ),
            {
                "e": entite,
                "m": r["arrivant"],
                "c": r["cercle"],
                "type": TypeAppartenanceCercle.PRINCIPAL.value,
                "d": dt.date(2026, 9, 1),
            },
        )

        #  Un DSM RATTACHE au nouvel arrivant — le temoin du piege §2.1 :
        #  meme rattache, il ne lit PAS cette fiche.
        r["dsm_personne"] = _personne(cx, marqueur, "dsm")
        _appartenance(cx, entite, r["dsm_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'DSM', :p, :d)"
            ),
            {"p": r["dsm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
        )
        cx.execute(
            text(
                "INSERT INTO dsm_assignment (consultant_membership_id, dsm_person_id, entity_id, "
                "starts_at) VALUES (:m, :p, :e, :d)"
            ),
            {
                "m": r["arrivant"],
                "p": r["dsm_personne"],
                "e": entite,
                "d": ANCRAGE - dt.timedelta(days=1),
            },
        )

        #  Un ESM de l'entite — le temoin positif de la portee « Entite ».
        r["esm_personne"] = _personne(cx, marqueur, "esm")
        _appartenance(cx, entite, r["esm_personne"])
        cx.execute(
            text(
                "INSERT INTO framework_responsibility_assignment (person_id, entity_id, "
                "responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, 'ESM', :p, :d)"
            ),
            {"p": r["esm_personne"], "e": entite, "d": ANCRAGE - dt.timedelta(days=1)},
        )

        #  Un employe NU — aucune responsabilite, aucun rattachement.
        r["emp_personne"] = _personne(cx, marqueur, "emp")
        _appartenance(cx, entite, r["emp_personne"])

        #  Le meme nouvel arrivant, dans l'AUTRE entite — pour le 404 croise.
        r["arrivant_ailleurs_personne"] = _personne(cx, marqueur, "ailleurs")
        r["arrivant_ailleurs"] = _appartenance(cx, autre, r["arrivant_ailleurs_personne"])

    yield r

    with moteur(parametres).begin() as menage:
        for requete in (
            "DELETE FROM auth_event WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM user_session WHERE person_id IN "
            "(SELECT id FROM person WHERE email LIKE :motif_personne)",
            "DELETE FROM arrival_profile WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM dsm_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM framework_responsibility_assignment WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM circle WHERE entity_id IN (SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM entity_membership WHERE entity_id IN "
            "(SELECT id FROM entity WHERE code LIKE :motif)",
            "DELETE FROM person WHERE email LIKE :motif_personne",
            "DELETE FROM entity WHERE code LIKE :motif",
        ):
            menage.execute(
                text(requete), {"motif": f"{marqueur}%", "motif_personne": f"{marqueur}%"}
            )


@pytest.mark.integration
def test_le_nouvel_arrivant_lit_SA_PROPRE_fiche(decor: dict[str, Any]) -> None:
    """`Soi` — §7. Le nouvel arrivant lit sa fiche, meme `future`."""
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["arrivant_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    fiche = reponse.json()
    assert fiche["state"] == "draft"
    assert fiche["id"] is None
    assert fiche["version"] is None
    assert fiche["dsm"] is not None  # la donnee organisationnelle est resolue


@pytest.mark.integration
def test_un_ESM_lit_la_fiche_d_un_AUTRE(decor: dict[str, Any]) -> None:
    """`Entite` — §7. Temoin positif de la portee la plus large."""
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_BOOSTER_lit_la_fiche_d_un_membre_de_SON_cercle(decor: dict[str, Any]) -> None:
    """`Cercle` — §7. Le nouvel arrivant est membre PRINCIPAL du cercle du Booster."""
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["booster_personne"]),
    )
    assert reponse.status_code == 200, reponse.text


@pytest.mark.integration
def test_un_DSM_MEME_RATTACHE_NE_LIT_PAS_la_fiche(decor: dict[str, Any]) -> None:
    """**LE TEMOIN CENTRAL DE CE FICHIER.** Voir l'en-tete du module.

    Le DSM du decor est explicitement rattache au nouvel arrivant par
    `dsm_assignment` — exactement ce qui lui donnerait « Consultants » sur
    d'autres lignes du §6.1/§8.1. Sur CETTE ligne du §7, la cellule est un
    tiret, et un rattachement reel ne doit rien y changer.
    """
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["dsm_personne"]),
    )
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["erreur"]["code"] == "fiche_arrivee_hors_perimetre"


@pytest.mark.integration
def test_un_EMPLOYE_NU_NE_LIT_PAS_la_fiche_d_un_AUTRE(decor: dict[str, Any]) -> None:
    """Aucune responsabilite, aucun rattachement : refus par defaut, §2.5."""
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["emp_personne"]),
    )
    assert reponse.status_code == 403, reponse.text


@pytest.mark.integration
def test_une_appartenance_d_une_AUTRE_entite_rend_404(decor: dict[str, Any]) -> None:
    """Le meme 404 qu'un code inconnu — §2.5, ne pas apprendre l'existence."""
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant_ailleurs"]),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 404, reponse.text


@pytest.mark.integration
def test_une_appartenance_inconnue_rend_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=str(uuid.uuid4())),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 404, reponse.text


@pytest.mark.integration
def test_un_code_d_entite_inconnu_rend_LE_MEME_404(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code="inconnue-xyz", appartenance=decor["arrivant"]),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 404, reponse.text


@pytest.mark.integration
def test_sans_session_la_reponse_est_401(decor: dict[str, Any]) -> None:
    parametres = decor["parametres"]
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        reponse = client.get(CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]))
    assert reponse.status_code == 401, reponse.text


@pytest.mark.integration
def test_la_lecture_N_ECRIT_RIEN(decor: dict[str, Any]) -> None:
    """`id`/`version` nuls, ET aucune ligne `arrival_profile` apres l'appel.

    Une lecture qui provisionnerait une ligne serait un effet de bord —
    voir l'en-tete du module `fiche_arrivee.py`.
    """
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["arrivant_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    with moteur(parametres).connect() as cx:
        compte = cx.execute(
            text("SELECT count(*) FROM arrival_profile WHERE entity_membership_id = :m"),
            {"m": decor["arrivant"]},
        ).scalar_one()
    assert compte == 0


@pytest.mark.integration
def test_les_donnees_organisationnelles_sont_celles_du_9_4(decor: dict[str, Any]) -> None:
    """Arrivee, DSM et cercle principal — trois des six champs du §10.2 que le

    decor renseigne reellement ; metier, statut et client restent `None` faute
    d'affectation dans ce decor, et c'est la valeur ATTENDUE — pas une absence
    de test.
    """
    parametres = decor["parametres"]
    reponse = _appeler(
        parametres,
        CHEMIN.format(code=decor["code"], appartenance=decor["arrivant"]),
        _session(parametres, decor["esm_personne"]),
    )
    assert reponse.status_code == 200, reponse.text
    fiche = reponse.json()
    assert fiche["arrival_date"] == "2026-10-15"
    assert fiche["dsm"] == "dsm T2"
    assert fiche["cercle_principal"]["code"].endswith("-cercle")
    assert fiche["metier"] is None
    assert fiche["statut"] is None
    assert fiche["client"] is None
