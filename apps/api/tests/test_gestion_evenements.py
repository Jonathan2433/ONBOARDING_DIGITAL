"""La lecture pour la gestion des evenements — LOT 8, `T10`.

UN TROU DEPUIS `T2`, MEME MOTIF QUE `/pages/gestion` AU LOT 6

  `GET …/events` (la consultation, `T2`) ne sert que `published`/`cancelled` :
  un brouillon tout juste cree, ou un evenement archive, n'etait lisible par
  AUCUNE route avant celle-ci. Un ecran de gestion doit pourtant retrouver les
  deux — le premier pour le publier, le second pour le restaurer — et
  `version`, dont toute ecriture a besoin pour la concurrence optimiste du
  §18.4, qu'aucune des deux reponses publiques ne porte.

DEUX ROUTES, DEUX GARDES

  `GET …/events/gestion` (le sommaire, tous etats) ne verifie qu'un role
  COARSE — un Booster y voit donc TOUS les evenements de son entite, memes
  ceux qu'il ne pourra pas ouvrir. `GET …/events/{evenement}/gestion` resout
  le PERIMETRE COMPLET sur CET evenement precisement, avec la MEME fonction
  que `PUT …/events/{evenement}` : un ensemble d'actions vide rend le MEME
  refus (`acces_refuse`, 403) que l'ecriture, jamais un gabarit different.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
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
from app.events.ecriture import (
    creer_un_evenement,
    gerer_les_medias_d_un_evenement,
    modifier_un_evenement,
)
from app.events.lecture import lire_un_evenement_pour_gestion, lister_les_evenements_pour_gestion
from app.events.perimetre import (
    ROLES_DE_CREATION_EVENEMENT,
    ROLES_DE_PORTEE_ENTITE,
    PorteeDeCreation,
)
from app.events.routes import ReponseDeLEvenementPourGestion, ReponseDesEvenementsPourGestion
from app.main import creer_application
from app.organization.modeles import TypeResponsabilite
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur

MARQUEUR = "L8T10"
JANVIER = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
DEMAIN = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
DEBUT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
FIN = dt.datetime(2026, 10, 10, 10, 0, tzinfo=dt.UTC)

# ============================================================================
#  1. Ce que la STRUCTURE tient, sans base
# ============================================================================


def test_la_reponse_de_liste_ne_porte_aucun_champ_de_nature_participant() -> None:
    suspects = {"participant", "inscription", "notification", "presence"}
    for nom in ReponseDesEvenementsPourGestion.model_fields:
        assert not any(s in nom.lower() for s in suspects)


def test_la_reponse_de_lecture_porte_version_cercles_bureaux_et_medias() -> None:
    """C'est precisement ce que la lecture publique de `T2` ne porte pas."""
    champs = set(ReponseDeLEvenementPourGestion.model_fields)
    for attendu in ("version", "cercles", "bureaux", "medias", "etat"):
        assert attendu in champs, f"`{attendu}` manque a l'ecran de gestion"


MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"


def _manifeste() -> dict[str, Any]:
    chemin = pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT
    donnees: dict[str, Any] = json.loads(chemin.read_text(encoding="utf-8"))
    return donnees


def test_le_MANIFESTE_declare_la_grille_COARSE_de_gestion_confrontee_au_code() -> None:
    """`rolesGestionDesEvenements` DOIT etre `ROLES_DE_CREATION_EVENEMENT` — DEC-492."""
    manifeste = _manifeste()
    codes = manifeste["rolesGestionDesEvenements"]
    assert codes, "le manifeste ne declare aucun role de gestion des evenements"
    assert {RoleDeLaMatrice(code) for code in codes} == ROLES_DE_CREATION_EVENEMENT


def test_le_MANIFESTE_declare_la_grille_de_restauration_SEPAREMENT_du_reste() -> None:
    """TROISIEME GRILLE DU PROJET A PORTER CES TROIS ROLES, ET CE N'EST PAS UNE FUSION.

    `rolesRestaurationDUnEvenement` porte les memes trois roles que
    `rolesCycleDeVie` (profils, LOT 5) et `rolesRestaurationDUnContenu`
    (contenus, LOT 6) — une coincidence, pas une derivation (§7.40 de la
    passation) : chacune vient d'une ligne distincte de la matrice, sur une
    ressource distincte. `rolesGestionDesEvenements` (DSM/ESM/BOOST/OFFICE/
    ADM-E/SUPER) est plus LARGE que celle-ci : DSM/BOOST/OFFICE creent,
    modifient, publient, annulent, archivent et gerent des medias, mais ne
    RESTAURENT jamais — `ARB-DROIT-003`.
    """
    manifeste = _manifeste()
    codes = manifeste["rolesRestaurationDUnEvenement"]
    assert codes, "le manifeste ne declare aucun role de restauration d'evenement"
    assert {RoleDeLaMatrice(code) for code in codes} == ROLES_DE_PORTEE_ENTITE
    for cle in ("rolesGestionDesEvenements", "rolesRestaurationDUnEvenement"):
        assert cle in manifeste, cle


def test_le_MANIFESTE_porte_les_DEUX_chemins_de_gestion() -> None:
    manifeste = _manifeste()
    par_cle = {e["cle"]: e for e in manifeste["endpoints"]}
    liste = par_cle["listeDesEvenementsPourGestion"]
    assert liste["chemin"] == "/api/v1/entities/{code}/events/gestion"
    assert liste["methode"] == "get"
    unique = par_cle["lectureDUnEvenementPourGestion"]
    assert unique["chemin"] == "/api/v1/entities/{code}/events/{evenement}/gestion"
    assert unique["methode"] == "get"
    assert 403 in unique["codesExploitables"]


# ============================================================================
#  2. Le service, sur une vraie connexion
# ============================================================================


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make residu-check`.")


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


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe}@exalt-company.com"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalisee, 'Gestion', 'L8T10', 'active') RETURNING id"
        ),
        {"email": adresse, "normalisee": adresse},
    ).scalar_one()


def _appartenance(cx: Connection, entite: uuid.UUID, personne: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft')"
        ),
        {"p": personne, "e": entite},
    )


def _esm(cx: Connection, entite: uuid.UUID, suffixe: str) -> uuid.UUID:
    personne = _personne(cx, suffixe)
    _appartenance(cx, entite, personne)
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, :type, :p, :debut)"
        ),
        {"p": personne, "e": entite, "type": TypeResponsabilite.ESM.value, "debut": JANVIER},
    )
    return personne


def _cercle(cx: Connection, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO circle (entity_id, code, name, display_order) "
            "VALUES (:e, :code, :nom, 1) RETURNING id"
        ),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _roles_esm(cx: Connection, *, acteur: uuid.UUID, entite: uuid.UUID) -> frozenset[Any]:
    return frozenset(resoudre_les_permissions(cx, acteur, entite, DEMAIN).roles)


@pytest.mark.integration
def test_la_liste_rend_les_QUATRE_etats_que_la_consultation_publique_refuse(
    cx: Connection,
) -> None:
    entite = _entite(cx, "LISTE")
    esm = _esm(cx, entite, "esm-liste")
    roles = _roles_esm(cx, acteur=esm, entite=entite)

    brouillon = creer_un_evenement(
        cx,
        entite=entite,
        acteur=esm,
        roles=roles,
        title="Brouillon",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=DEMAIN,
    ).identifiant

    cx.execute(
        text("UPDATE event SET state = 'archived', archived_at = :instant WHERE id = :e"),
        {"instant": DEMAIN, "e": brouillon},
    )

    resultat = lister_les_evenements_pour_gestion(cx, entite=entite)
    titres_et_etats = {(e.titre, e.etat) for e in resultat}
    assert titres_et_etats == {("Brouillon", "archived")}
    #  `version` est porte — la consultation publique ne le rend pas.
    assert all(e.version >= 1 for e in resultat)


@pytest.mark.integration
def test_la_liste_n_expose_jamais_l_evenement_d_une_autre_entite(cx: Connection) -> None:
    ici = _entite(cx, "ICI")
    ailleurs = _entite(cx, "AILLEURS")
    esm_ailleurs = _esm(cx, ailleurs, "esm-ailleurs")
    roles = _roles_esm(cx, acteur=esm_ailleurs, entite=ailleurs)
    creer_un_evenement(
        cx,
        entite=ailleurs,
        acteur=esm_ailleurs,
        roles=roles,
        title="Secret d ailleurs",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=DEMAIN,
    )
    assert lister_les_evenements_pour_gestion(cx, entite=ici) == ()


@pytest.mark.integration
def test_la_lecture_unique_rend_None_pour_un_evenement_inconnu_ou_d_une_autre_entite(
    cx: Connection,
) -> None:
    ici = _entite(cx, "SEUL1")
    ailleurs = _entite(cx, "SEUL2")
    assert lire_un_evenement_pour_gestion(cx, entite=ici, evenement=uuid.uuid4()) is None

    esm_ailleurs = _esm(cx, ailleurs, "esm-seul")
    roles = _roles_esm(cx, acteur=esm_ailleurs, entite=ailleurs)
    la_bas = creer_un_evenement(
        cx,
        entite=ailleurs,
        acteur=esm_ailleurs,
        roles=roles,
        title="Pas ici",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=DEMAIN,
    ).identifiant
    assert lire_un_evenement_pour_gestion(cx, entite=ici, evenement=la_bas) is None


@pytest.mark.integration
def test_la_lecture_unique_rend_les_cercles_les_bureaux_et_les_medias_EN_VIE(
    cx: Connection,
) -> None:
    """Rattachements ARCHIVES exclus, dans l'ordre fourni — meme discipline que l'ecriture."""
    entite = _entite(cx, "SCOPE")
    esm = _esm(cx, entite, "esm-scope")
    roles = _roles_esm(cx, acteur=esm, entite=entite)
    cercle_a = _cercle(cx, entite, "CERCLE-A")
    cercle_b = _cercle(cx, entite, "CERCLE-B")

    evenement = creer_un_evenement(
        cx,
        entite=entite,
        acteur=esm,
        roles=roles,
        title="Avec rattachements",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=DEMAIN,
    ).identifiant

    #  Rattache A et B, puis remplace par B seul — A doit devenir invisible.
    modifier_un_evenement(
        cx,
        entite=entite,
        acteur=esm,
        roles=roles,
        evenement=evenement,
        title="Avec rattachements",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        version_attendue=1,
        codes_de_cercle=["CERCLE-A", "CERCLE-B"],
        codes_de_bureau=None,
        instant=DEMAIN,
    )
    modifier_un_evenement(
        cx,
        entite=entite,
        acteur=esm,
        roles=roles,
        evenement=evenement,
        title="Avec rattachements",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        version_attendue=2,
        codes_de_cercle=["CERCLE-B"],
        codes_de_bureau=None,
        instant=DEMAIN,
    )

    media_asset = cx.execute(
        text(
            "INSERT INTO media_asset (entity_id, uploaded_by_person_id, state, media_type, "
            "original_filename, object_key, mime_declared, size_bytes, checksum_sha256) "
            "VALUES (:e, :p, 'ready', 'image', 'photo.jpg', :cle, 'image/jpeg', 10, :empreinte) "
            "RETURNING id"
        ),
        {
            "e": entite,
            "p": esm,
            "cle": f"{MARQUEUR}/{uuid.uuid4().hex}",
            "empreinte": uuid.uuid4().hex * 2,
        },
    ).scalar_one()
    gerer_les_medias_d_un_evenement(
        cx,
        entite=entite,
        acteur=esm,
        evenement=evenement,
        version_attendue=3,
        medias=[(media_asset, "Affiche")],
        instant=DEMAIN,
    )

    trouve = lire_un_evenement_pour_gestion(cx, entite=entite, evenement=evenement)
    assert trouve is not None
    assert trouve.cercles == ("CERCLE-B",)
    assert trouve.bureaux == ()
    assert [(m.media, m.role, m.ordre) for m in trouve.medias] == [(media_asset, "Affiche", 0)]
    assert trouve.version == 4
    assert cercle_a is not None and cercle_b is not None  # les deux existent bien


@pytest.mark.integration
def test_la_lecture_unique_rend_un_evenement_ARCHIVE_avec_sa_date(cx: Connection) -> None:
    entite = _entite(cx, "ARCH")
    esm = _esm(cx, entite, "esm-arch")
    roles = _roles_esm(cx, acteur=esm, entite=entite)
    evenement = creer_un_evenement(
        cx,
        entite=entite,
        acteur=esm,
        roles=roles,
        title="A archiver",
        description=None,
        starts_at=DEBUT,
        ends_at=FIN,
        location_text=None,
        portee=PorteeDeCreation.ENTITE,
        code_de_cercle=None,
        code_de_bureau=None,
        instant=DEMAIN,
    ).identifiant
    cx.execute(
        text(
            "UPDATE event SET state = 'archived', archived_at = :instant, "
            "archived_by_person_id = :acteur WHERE id = :e"
        ),
        {"instant": DEMAIN, "acteur": esm, "e": evenement},
    )
    trouve = lire_un_evenement_pour_gestion(cx, entite=entite, evenement=evenement)
    assert trouve is not None
    assert trouve.etat == "archived"
    assert trouve.archive_le == DEMAIN


# ============================================================================
#  3. La route, par HTTP
# ============================================================================

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_LISTE = "/api/v1/entities/{code}/events/gestion"
CHEMIN_UNIQUE = "/api/v1/entities/{code}/events/{evenement}/gestion"


@pytest.fixture
def decor_http(
    parametres_de_la_stack: Parametres,
) -> Iterator[dict[str, Any]]:
    """Donnees commises, car l'API ouvre sa propre connexion PostgreSQL."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"l8t10{uuid.uuid4().hex[:10]}"
    code = f"{marqueur}-e"
    maintenant = dt.datetime.now(tz=dt.UTC)
    adresse_esm = f"{marqueur}-esm@exemple.test"
    adresse_emp = f"{marqueur}-emp@exemple.test"

    with moteur(parametres).begin() as cx_http:
        entite = cx_http.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, "
                "timezone, activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', "
                "'Europe/Paris', now()) RETURNING id"
            ),
            {"code": code, "nom": marqueur, "ville": marqueur},
        ).scalar_one()
        esm = cx_http.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "account_state) VALUES (:a, :a, 'ESM', 'Gestion', 'active') RETURNING id"
            ),
            {"a": adresse_esm},
        ).scalar_one()
        emp = cx_http.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "account_state) VALUES (:a, :a, 'EMP', 'Gestion', 'active') RETURNING id"
            ),
            {"a": adresse_emp},
        ).scalar_one()
        for personne in (esm, emp):
            cx_http.execute(
                text(
                    "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                    "membership_state, professional_category, profile_visibility) "
                    "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft')"
                ),
                {"p": personne, "e": entite},
            )
        cx_http.execute(
            text(
                "INSERT INTO framework_responsibility_assignment "
                "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
                "VALUES (:p, :e, :type, :p, :debut)"
            ),
            {"p": esm, "e": entite, "type": TypeResponsabilite.ESM.value, "debut": JANVIER},
        )
        brouillon = cx_http.execute(
            text(
                "INSERT INTO event (entity_id, title, description, starts_at, ends_at, "
                "location_text, created_by_person_id) VALUES (:e, 'Brouillon HTTP', NULL, "
                ":debut, :fin, NULL, :acteur) RETURNING id"
            ),
            {
                "e": entite,
                "debut": maintenant + dt.timedelta(days=1),
                "fin": maintenant + dt.timedelta(days=1, hours=1),
                "acteur": esm,
            },
        ).scalar_one()
        jeton_esm, _ = ouvrir_une_session(
            cx_http,
            personne=esm,
            instant=maintenant,
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
        jeton_emp, _ = ouvrir_une_session(
            cx_http,
            personne=emp,
            instant=maintenant,
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )

    try:
        yield {
            "parametres": parametres,
            "code": code,
            "evenement": brouillon,
            "jeton_esm": jeton_esm,
            "jeton_emp": jeton_emp,
        }
    finally:
        with moteur(parametres).begin() as menage:
            menage.execute(
                text(
                    "DELETE FROM user_session WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized IN (:a, :b))"
                ),
                {"a": adresse_esm, "b": adresse_emp},
            )
            menage.execute(
                text(
                    "DELETE FROM framework_responsibility_assignment WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized IN (:a, :b))"
                ),
                {"a": adresse_esm, "b": adresse_emp},
            )
            menage.execute(
                text(
                    "DELETE FROM entity_membership WHERE person_id IN "
                    "(SELECT id FROM person WHERE email_normalized IN (:a, :b))"
                ),
                {"a": adresse_esm, "b": adresse_emp},
            )
            menage.execute(
                text(
                    "DELETE FROM event WHERE entity_id IN (SELECT id FROM entity WHERE code = :c)"
                ),
                {"c": code},
            )
            menage.execute(
                text("DELETE FROM person WHERE email_normalized IN (:a, :b)"),
                {"a": adresse_esm, "b": adresse_emp},
            )
            menage.execute(text("DELETE FROM entity WHERE code = :c"), {"c": code})


def _appeler(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


@pytest.mark.integration
def test_la_liste_exige_une_session(decor_http: dict[str, Any]) -> None:
    chemin = CHEMIN_LISTE.format(code=decor_http["code"])
    assert _appeler(decor_http["parametres"], chemin, None).status_code == 401


@pytest.mark.integration
def test_la_liste_refuse_un_EMP_sans_role_de_creation(decor_http: dict[str, Any]) -> None:
    chemin = CHEMIN_LISTE.format(code=decor_http["code"])
    reponse = _appeler(decor_http["parametres"], chemin, decor_http["jeton_emp"])
    assert reponse.status_code == 403


@pytest.mark.integration
def test_TEMOIN_la_liste_rend_le_BROUILLON_a_un_ESM(decor_http: dict[str, Any]) -> None:
    chemin = CHEMIN_LISTE.format(code=decor_http["code"])
    reponse = _appeler(decor_http["parametres"], chemin, decor_http["jeton_esm"])
    assert reponse.status_code == 200, reponse.text
    charge = reponse.json()
    assert [e["etat"] for e in charge["evenements"]] == ["draft"]
    assert set(charge["evenements"][0]) == {
        "identifiant",
        "titre",
        "etat",
        "commence_le",
        "finit_le",
        "version",
    }


@pytest.mark.integration
def test_la_lecture_unique_exige_une_session(decor_http: dict[str, Any]) -> None:
    chemin = CHEMIN_UNIQUE.format(code=decor_http["code"], evenement=decor_http["evenement"])
    assert _appeler(decor_http["parametres"], chemin, None).status_code == 401


@pytest.mark.integration
def test_la_lecture_unique_refuse_un_EMP_sans_role_de_creation(decor_http: dict[str, Any]) -> None:
    chemin = CHEMIN_UNIQUE.format(code=decor_http["code"], evenement=decor_http["evenement"])
    reponse = _appeler(decor_http["parametres"], chemin, decor_http["jeton_emp"])
    assert reponse.status_code == 403


@pytest.mark.integration
def test_la_lecture_unique_rend_LE_MEME_REFUS_pour_un_evenement_INCONNU(
    decor_http: dict[str, Any],
) -> None:
    """Un seul gabarit, meme discipline que l'ecriture — pas un 404 distinct.

    `resoudre_le_perimetre_de_l_evenement` rend un ensemble d'actions VIDE des
    qu'aucune ligne `(id, entite)` ne correspond — exactement ce qu'elle rend
    quand le role n'y porte rien. `PUT …/events/{evenement}` fait deja ce choix
    (`acces_refuse`, 403) pour la MEME cause ; cette route le reprend, plutot
    que d'inventer un gabarit different pour sa seule lecture.
    """
    chemin = CHEMIN_UNIQUE.format(code=decor_http["code"], evenement=uuid.uuid4())
    reponse = _appeler(decor_http["parametres"], chemin, decor_http["jeton_esm"])
    assert reponse.status_code == 403


@pytest.mark.integration
def test_TEMOIN_la_lecture_unique_rend_le_BROUILLON_a_un_ESM_avec_sa_VERSION(
    decor_http: dict[str, Any],
) -> None:
    """Ce que la consultation publique de `T2` ne rend JAMAIS : un brouillon, sa version."""
    chemin = CHEMIN_UNIQUE.format(code=decor_http["code"], evenement=decor_http["evenement"])
    reponse = _appeler(decor_http["parametres"], chemin, decor_http["jeton_esm"])
    assert reponse.status_code == 200, reponse.text
    charge = reponse.json()
    assert charge["etat"] == "draft"
    assert charge["version"] == 1
    assert charge["cercles"] == []
    assert charge["bureaux"] == []
    assert charge["medias"] == []
