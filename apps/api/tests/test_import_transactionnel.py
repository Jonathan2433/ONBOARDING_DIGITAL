"""Import transactionnel des lignes valides — LOT 9, `T9`, `MVP-L09-US006` (1/2).

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. `app.imports.organisation` : un echantillon representatif du referentiel
     restant — identite, entite, dates, categorie, metier, situation,
     cercles, DSM, responsabilites Framework, roles techniques, photo — pas
     les 68 codes un par un, mais au moins un E/D/W par domaine touche ;
  2. la CREATION complete d'un collaborateur valide, avec toutes les
     ecritures secondaires (dg -> DSM automatique, responsabilites, role
     technique, cercles secondaires, presentation/fun fact, DSM resolu
     DANS LE FICHIER) ;
  3. la MISE A JOUR par e-mail (`person_merge`) et la REACTIVATION
     (`profile_reactivation`, confirmation explicite) ;
  4. `W-DEPART-001` : le profil est importe PUIS archive, sans acces ;
  5. l'atomicite PAR LIGNE : une ligne en echec n'affecte pas les autres ;
  6. la revalidation FRAICHE au moment de l'import (un metier cree ENTRE
     la previsualisation et le lancement passe desormais) ;
  7. la grille de roles de « Lancer l'import » (meme que « Charger un CSV ») ;
  8. le defaut corrige dans `app.imports.decisions` : un DSM ne peut PLUS
     enregistrer `person_merge`/`profile_reactivation` ;
  9. l'etat du lot : `preview_ready -> completed`, refus si deja lance.

Ce fichier ne reteste PAS l'e-mail, les doublons de personne ni le
rapprochement client (`test_analyse_import.py`, `test_rapprochement_clients.py`).
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.imports.decisions import CODE_PORTEE_DSM_REFUSEE, enregistrer_une_decision
from app.imports.depot import LotDepose, deposer_un_csv
from app.imports.execution import (
    CODE_ETAT_NON_LANCABLE,
    CODE_LOT_INTROUVABLE,
    lancer_l_import,
)
from app.imports.modeles import EtatLigneImport, EtatLotImport, TypeDeDecisionImport
from app.imports.organisation import (
    CODE_CATEGORIE_ABSENTE,
    CODE_CERCLE_PRINCIPAL_ABSENT,
    CODE_CERCLE_PRINCIPAL_ABSENT_DSM,
    CODE_DATE_ARRIVEE_ABSENTE,
    CODE_DSM_ABSENT,
    CODE_ENTITE_ABSENTE,
    CODE_IDENT_NOM_ABSENT,
    CODE_METIER_INCONNU_DU_CATALOGUE,
    CODE_PHOTO_INCONNUE,
    CODE_PRESENTATION_ABSENTE,
    CODE_RESP_BOOSTER_CONFLIT,
    CODE_SITUATION_ABSENTE,
)
from app.imports.perimetre import ROLES_DE_DEPOT_DE_L_IMPORT
from app.media.objets import client_s3
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T9"
INSTANT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
EMAIL_DOMAINE = "exalt-company.com"
ROLES_ESM: frozenset[RoleDeLaMatrice] = frozenset({RoleDeLaMatrice.ESM})


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


@dataclasses.dataclass(frozen=True, slots=True)
class _Entite:
    identifiant: uuid.UUID
    code: str


def _entite(cx: Connection, suffixe: str) -> _Entite:
    code = f"{MARQUEUR}-{suffixe}"
    identifiant = cx.execute(
        text(
            "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
            "activated_at) VALUES (:code, :nom, :ville, 'FR', 'active', 'Europe/Paris', now()) "
            "RETURNING id"
        ),
        {"code": code, "nom": code, "ville": code},
    ).scalar_one()
    return _Entite(identifiant=uuid.UUID(str(identifiant)), code=code)


def _domaine_local(cx: Connection, *, entite: uuid.UUID, domaine: str = EMAIL_DOMAINE) -> None:
    """Autoriser `domaine` pour `entite` — borne dans le PASSE, jamais `now()`.

    §7.47 : `INSTANT` ci-dessus est une date FIXE (2026-10-10). `starts_at =
    now()` etait juste tant que le calendrier reel n'avait pas depasse cette
    date ; une fois que si, la periode de la ligne commence APRES `INSTANT` et
    `period @> :instant` devient faux — chaque ligne de ce domaine est
    refusee (`E-EMAIL-003`), mesure le 12/10/2026 en integration continue. Une
    borne fixe et ANTERIEURE a tout `INSTANT` du fichier ferme la question
    sans dependre du jour ou le test s'execute.
    """
    cx.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, starts_at) "
            "VALUES (:domaine, :entite, '2020-01-01T00:00:00+00:00') ON CONFLICT DO NOTHING"
        ),
        {"domaine": domaine, "entite": entite},
    )


def _personne(cx: Connection, suffixe: str, *, email: str | None = None) -> uuid.UUID:
    adresse = (
        email or f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@{EMAIL_DOMAINE}"
    )
    normalise = adresse.strip().lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Existant', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": normalise, "s": suffixe},
    ).scalar_one()


def _appartenance(
    cx: Connection, *, personne: uuid.UUID, entite: uuid.UUID, etat: str
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2020-01-01', :etat, 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite, "etat": etat},
    ).scalar_one()


def _metier(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    #  **DEUX PARAMETRES DISTINCTS POUR LA MEME VALEUR, JAMAIS UN SEUL
    #  PARTAGE** : `code` est `character varying(64)`, `label` est `text` —
    #  un seul `:code` reutilise pour les deux produirait
    #  `AmbiguousParameter`, classe §7.25 deja rencontree quatre fois dans ce
    #  projet (et rejouee ici, dans mon propre decor de test).
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label) "
            "VALUES (:e, :code, :libelle) RETURNING id"
        ),
        {"e": entite, "code": code, "libelle": code},
    ).scalar_one()


def _cercle(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _office(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO office (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _responsabilite_dsm(cx: Connection, *, entite: uuid.UUID, personne: uuid.UUID) -> None:
    #  `:instant` (l'ancre FIXE du fichier), JAMAIS `now()` : la requete de
    #  resolution DSM compare `period @> :instant` a CETTE MEME ancre, et une
    #  periode ouverte APRES elle ne la couvrirait pas — §7.47, « une date
    #  absolue dans un test est une bombe a retardement datee », rejouee ici
    #  avec `now()` au lieu d'une date absolue.
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :instant)"
        ),
        {"p": personne, "e": entite, "instant": INSTANT},
    )


def _responsabilite_esm(cx: Connection, *, entite: uuid.UUID, personne: uuid.UUID) -> None:
    """`attribuer_la_categorie_dg` (`RIGHTS-005`) verifie l'ESM EN BASE, pas
    le `roles` passe a `lancer_l_import` — son propre controle interne,
    §8.4. Une periode tres large couvre a la fois `INSTANT` et l'instant
    REEL d'execution du test (la fonction lit `now()`, pas `INSTANT`).
    """
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'ESM', :p, '2020-01-01')"
        ),
        {"p": personne, "e": entite},
    )


def _dsm_existant(cx: Connection, *, entite: uuid.UUID, suffixe: str) -> str:
    """Une personne DEJA DSM active (en base) — rend son e-mail, pour `F16`.

    `E-DSM-001` frappe tout consultant ACTIF (arrivee passee) sans DSM
    renseigne (codes-erreurs-import.md §3.9) : presque toute ligne « active »
    de cette suite en a besoin pour ne pas etre rejetee par un domaine HORS
    SUJET du test.
    """
    email = f"{MARQUEUR.lower()}-dsm-{suffixe.lower()}@{EMAIL_DOMAINE}"
    personne = _personne(cx, f"dsm-{suffixe}", email=email)
    _responsabilite_dsm(cx, entite=entite, personne=personne)
    return email


def _ligne_complete(
    *,
    email: str,
    nom: str = "EXEMPLE",
    prenom: str = "Prenom",
    entite: str,
    date_arrivee: str = "2026-10-01",
    date_depart: str = "",
    categorie: str = "consultant",
    situation: str = "intercontrat",
    client: str = "",
    cercle_principal: str,
    cercles_secondaires: str = "",
    email_dsm: str = "",
    responsabilites: str = "",
    roles_techniques: str = "",
    autorisation_photo: str = "",
    metier: str = "",
) -> str:
    """Une ligne CSV PORTANT TOUS LES CHAMPS F01-F19 sauf F04/F09/F10.

    Chaque test NE PARAMETRE QUE ce qui l'interesse : les defauts rendent une
    ligne entierement VALIDE (intercontrat, sans client, sans DSM) pour ne
    pas faire porter aux autres domaines la responsabilite du test en cours.
    """
    return (
        f"{email},{nom},{prenom},{entite},{date_arrivee},{date_depart},{categorie},"
        f"{metier},{situation},{client},{cercle_principal},{cercles_secondaires},"
        f"{email_dsm},{responsabilites},{roles_techniques},{autorisation_photo}"
    )


ENTETE_COMPLET = (
    "email,nom,prenom,entite,date_arrivee,date_depart,categorie_professionnelle,"
    "metier,situation,client,cercle_principal,cercles_secondaires,email_dsm,"
    "responsabilites_framework,roles_techniques,autorisation_photo"
)


def _deposer_ou_sauter(
    cx: Connection, parametres: Parametres, *, entite: uuid.UUID, acteur: uuid.UUID, contenu: str
) -> LotDepose:
    try:
        return deposer_un_csv(
            cx,
            parametres,
            entite=entite,
            acteur=acteur,
            nom_de_fichier="fichier.csv",
            contenu=contenu.encode(),
            instant=INSTANT,
        )
    except Exception as erreur:  # pragma: no cover — diagnostic de decor
        pytest.skip(f"MinIO injoignable : {type(erreur).__name__}")
        raise  # pragma: no cover


def _nettoyer_le_lot(parametres: Parametres, *, entite: uuid.UUID, lot: uuid.UUID) -> None:
    client = client_s3(parametres)
    with contextlib.suppress(Exception):
        client.delete_object(  # type: ignore[attr-defined]
            Bucket=parametres.MINIO_BUCKET, Key=f"imports/{entite}/{lot}.csv"
        )


@dataclasses.dataclass(frozen=True, slots=True)
class _LigneVue:
    id: uuid.UUID
    state: str
    error_codes: list[str]
    target_person_id: uuid.UUID | None
    target_membership_id: uuid.UUID | None


def _ligne(cx: Connection, lot: uuid.UUID, numero: int) -> _LigneVue:
    ligne = cx.execute(
        text(
            "SELECT id, state, error_codes, target_person_id, target_membership_id "
            "FROM import_row WHERE import_batch_id = :lot AND row_number = :n"
        ),
        {"lot": lot, "n": numero},
    ).one()
    return _LigneVue(
        id=ligne.id,
        state=ligne.state,
        error_codes=ligne.error_codes,
        target_person_id=ligne.target_person_id,
        target_membership_id=ligne.target_membership_id,
    )


# ---------------------------------------------------------------------------
#  1. `app.imports.organisation` — un echantillon representatif
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_une_ligne_entierement_valide_ne_porte_aucun_code(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T1")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a1")
    cercle = _cercle(cx, entite=entite.identifiant, code="DATA")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"valide1@{EMAIL_DOMAINE}", entite=entite.code, cercle_principal="DATA"
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.error_codes == []
    assert ligne.state == EtatLigneImport.VALID.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
    _ = cercle


@pytest.mark.integration
def test_identite_entite_dates_categorie_situation_cercle_absents(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Une ligne presque vide porte un code par domaine manquant — E uniquement.

    `app.imports.organisation` n'est appele qu'a `lancer_l_import` — JAMAIS a
    la previsualisation (voir l'en-tete d'`app.imports.analyse`) : il faut
    donc LANCER le lot pour observer ses codes, pas se contenter du depot.
    """
    acteur = _personne(cx, "a2")
    entite = _entite(cx, "T2")
    _domaine_local(cx, entite=entite.identifiant)
    contenu = ENTETE_COMPLET + f"\nvalide2@{EMAIL_DOMAINE},,Prenom,,,,,,,,,,,,,\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.state == EtatLigneImport.REJECTED.value
    for code in (
        CODE_IDENT_NOM_ABSENT,
        CODE_ENTITE_ABSENTE,
        CODE_DATE_ARRIVEE_ABSENTE,
        CODE_CATEGORIE_ABSENTE,
        CODE_SITUATION_ABSENTE,
        CODE_CERCLE_PRINCIPAL_ABSENT,
    ):
        assert code in ligne.error_codes, f"{code} attendu dans {ligne.error_codes}"
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_metier_inconnu_du_catalogue_est_une_decision(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T3")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a3")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"valide3@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal="",
            metier="CODE-INCONNU",
        )
        + "\n"
    )
    #  Sans cercle NI DSM : la ligne porte aussi `CODE_CERCLE_PRINCIPAL_ABSENT`
    #  (E), ce qui est attendu — seul le METIER nous interesse ici, et c'est
    #  precisement le E qui fait primer `rejected` sur le D du metier.

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.state == EtatLigneImport.REJECTED.value
    assert CODE_METIER_INCONNU_DU_CATALOGUE in ligne.error_codes
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_un_metier_absent_pour_un_profil_actif_est_importe_quand_meme(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """`DEC-675` (LOT 11 `T5`) : `E-METIER-001` est retire, meme pour un actif.

    Temoin negatif apparie a `test_metier_inconnu_du_catalogue_est_une_decision`
    (§7.39) : AVANT ce retrait, cette meme ligne — un profil actif
    (`date_arrivee` par defaut, anterieure a `INSTANT`), sans `F11` — aurait
    ete rejetee par `CODE_METIER_ABSENT`. Elle est desormais `IMPORTED`, et
    AUCUNE ligne `membership_job_assignment` n'est posee pour elle.
    """
    entite = _entite(cx, "T3-SANSMETIER")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a3-sansmetier")
    cercle = _cercle(cx, entite=entite.identifiant, code="DATA")
    #  `E-DSM-001` frappe tout consultant ACTIF sans DSM — hors sujet de ce
    #  test, un DSM deja existant l'evite (voir `_dsm_existant`).
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="sansmetier3")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"sansmetier3@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal="DATA",
            email_dsm=email_dsm,
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_importees == 1
    ligne = _ligne(cx, lot.identifiant, 1)
    assert ligne.state == EtatLigneImport.IMPORTED.value
    #  Des AVERTISSEMENTS subsistent (nom en majuscules, presentation absente,
    #  hors sujet de ce test) : seule l'ABSENCE de tout code E/D lie au
    #  metier compte ici — `CODE_METIER_ABSENT` n'existe plus du tout (§
    #  en-tete d'`app.imports.organisation`).
    assert "E-METIER-001" not in ligne.error_codes
    assert CODE_METIER_INCONNU_DU_CATALOGUE not in ligne.error_codes

    total = cx.execute(
        text("SELECT count(*) FROM membership_job_assignment WHERE entity_membership_id = :m"),
        {"m": ligne.target_membership_id},
    ).scalar_one()
    assert total == 0
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
    _ = cercle


@pytest.mark.integration
def test_dsm_absent_pour_un_consultant_actif_mais_tolere_pour_un_dsm(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T4")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a4")
    cercle = _cercle(cx, entite=entite.identifiant, code="DATA")
    _metier(cx, entite=entite.identifiant, code="DEV")
    #  Un DSM DEJA EN BASE : la ligne « DSM » du fichier a elle-meme besoin
    #  d'un DSM renseigne (`E-DSM-001` n'exempte QUE la categorie `dg` —
    #  porter la responsabilite DSM via `F17` n'en dispense pas).
    email_dsm_existant = _dsm_existant(cx, entite=entite.identifiant, suffixe="t4")
    #  Consultant actif, intercontrat, cercle present, AUCUN DSM.
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"valide4@{EMAIL_DOMAINE}",
            prenom="Novembre",
            entite=entite.code,
            metier="DEV",
            cercle_principal="DATA",
        )
        + "\n"
    )
    #  Un DSM (F17=DSM), sans cercle principal : W-CERCLE-001, pas d'erreur.
    #  `E-METIER-001` n'exempte PAS les DSM (le referentiel ne le dit nulle
    #  part) : un metier reste necessaire pour que cette ligne s'importe.
    #  Prenom DIFFERENT de la ligne precedente : meme nom/prenom identiques
    #  sur deux lignes a e-mails distincts declenche `D-PERSONNE-003`
    #  (homonymie), hors sujet de CE test.
    contenu += (
        _ligne_complete(
            email=f"valide4dsm@{EMAIL_DOMAINE}",
            prenom="Oscar",
            entite=entite.code,
            metier="DEV",
            cercle_principal="",
            email_dsm=email_dsm_existant,
            responsabilites="DSM",
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    consultant, dsm = _ligne(cx, lot.identifiant, 1), _ligne(cx, lot.identifiant, 2)

    assert CODE_DSM_ABSENT in consultant.error_codes
    #  `W-CERCLE-001` est un AVERTISSEMENT, pas une erreur : la ligne reste
    #  IMPORTABLE (codes-erreurs-import.md §4), et le code est CONSERVE au
    #  rapport meme une fois la ligne importee — jamais perdu en silence.
    assert CODE_CERCLE_PRINCIPAL_ABSENT_DSM in dsm.error_codes
    assert dsm.state == EtatLigneImport.IMPORTED.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
    _ = cercle


@pytest.mark.integration
def test_presentation_absente_et_photo_inconnue_sont_des_avertissements(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T5")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a5")
    cercle = _cercle(cx, entite=entite.identifiant, code="DATA")
    _metier(cx, entite=entite.identifiant, code="DEV")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t5")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"valide5@{EMAIL_DOMAINE}",
            entite=entite.code,
            metier="DEV",
            cercle_principal="DATA",
            email_dsm=email_dsm,
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert CODE_PRESENTATION_ABSENTE in ligne.error_codes
    assert CODE_PHOTO_INCONNUE in ligne.error_codes
    assert ligne.state == EtatLigneImport.IMPORTED.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
    _ = cercle


@pytest.mark.integration
def test_conflit_de_booster_dans_le_fichier_rejette_les_deux_lignes(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T6")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a6")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    contenu = ENTETE_COMPLET + "\n"
    #  Prenoms DIFFERENTS sur les deux lignes : memes nom/prenom sur deux
    #  e-mails distincts declencherait `D-PERSONNE-003` (homonymie), hors
    #  sujet de ce test sur les Boosters.
    for suffixe, prenom in (("a", "Alpha"), ("b", "Bravo")):
        contenu += (
            _ligne_complete(
                email=f"booster-{suffixe}@{EMAIL_DOMAINE}",
                prenom=prenom,
                entite=entite.code,
                cercle_principal="DATA",
                responsabilites="BOOSTER:DATA",
            )
            + "\n"
        )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    premiere, seconde = _ligne(cx, lot.identifiant, 1), _ligne(cx, lot.identifiant, 2)

    assert CODE_RESP_BOOSTER_CONFLIT in premiere.error_codes
    assert CODE_RESP_BOOSTER_CONFLIT in seconde.error_codes
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  2. La CREATION complete d'un collaborateur
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_creation_complete_dg_responsabilites_roles_cercles_secondaires(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Une seule ligne `dg`, Booster d'un second cercle, `ENTITY_ADMIN`, deux secondaires."""
    entite = _entite(cx, "T7")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a7")
    #  `RIGHTS-005` (dg -> DSM automatique) exige un acteur ESM EN BASE —
    #  voir l'en-tete de `_responsabilite_esm`.
    _responsabilite_esm(cx, entite=entite.identifiant, personne=acteur)
    _metier(cx, entite=entite.identifiant, code="DEV")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    cercle_booste = _cercle(cx, entite=entite.identifiant, code="CLOUD")
    secondaire_un = _cercle(cx, entite=entite.identifiant, code="SEC1")
    secondaire_deux = _cercle(cx, entite=entite.identifiant, code="SEC2")

    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"dg7@{EMAIL_DOMAINE}",
            entite=entite.code,
            categorie="dg",
            metier="DEV",
            cercle_principal="DATA",
            cercles_secondaires="SEC1|SEC2",
            responsabilites="BOOSTER:CLOUD",
            roles_techniques="ENTITY_ADMIN",
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_importees == 1
    assert rapport.etat == EtatLotImport.COMPLETED.value

    ligne = _ligne(cx, lot.identifiant, 1)
    assert ligne.state == EtatLigneImport.IMPORTED.value
    personne = ligne.target_person_id
    assert personne is not None

    categorie = cx.execute(
        text("SELECT professional_category FROM entity_membership WHERE id = :m"),
        {"m": ligne.target_membership_id},
    ).scalar_one()
    assert categorie == "dg"

    a_la_dsm = cx.execute(
        text(
            "SELECT 1 FROM framework_responsibility_assignment WHERE person_id = :p "
            "AND entity_id = :e AND responsibility_type = 'DSM' AND archived_at IS NULL "
            "AND ends_at IS NULL"
        ),
        {"p": personne, "e": entite.identifiant},
    ).first()
    assert a_la_dsm is not None, "RIGHTS-005 : un dg recoit automatiquement la responsabilite DSM"

    est_booster = cx.execute(
        text(
            "SELECT 1 FROM framework_responsibility_assignment WHERE person_id = :p "
            "AND circle_id = :c AND responsibility_type = 'BOOSTER' AND ends_at IS NULL"
        ),
        {"p": personne, "c": cercle_booste},
    ).first()
    assert est_booster is not None

    a_le_role_technique = cx.execute(
        text(
            "SELECT 1 FROM technical_role_assignment WHERE person_id = :p AND entity_id = :e "
            "AND role_type = 'ENTITY_ADMIN' AND ends_at IS NULL"
        ),
        {"p": personne, "e": entite.identifiant},
    ).first()
    assert a_le_role_technique is not None

    secondaires = {
        row.circle_id
        for row in cx.execute(
            text(
                "SELECT circle_id FROM circle_membership WHERE entity_membership_id = :m "
                "AND membership_type = 'secondary' AND ends_at IS NULL"
            ),
            {"m": ligne.target_membership_id},
        )
    }
    assert secondaires == {secondaire_un, secondaire_deux}
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_dsm_resolu_dans_le_fichier_pour_un_nouveau_consultant(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """`F16` designe une personne CREEE PAR CE MEME LOT, pas encore en base."""
    entite = _entite(cx, "T8")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a8")
    _metier(cx, entite=entite.identifiant, code="DEV")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    #  Le NOUVEAU DSM reste categorie `consultant` : `E-DSM-001` s'applique
    #  aussi a LUI (seul `dg` en est exempt) — il designe donc, a son tour,
    #  un DSM DEJA EN BASE. Le point du test porte sur la ligne SUIVANTE.
    email_dsm_racine = _dsm_existant(cx, entite=entite.identifiant, suffixe="t8")
    email_dsm = f"nouveaudsm8@{EMAIL_DOMAINE}"

    contenu = ENTETE_COMPLET + "\n"
    contenu += (
        _ligne_complete(
            email=email_dsm,
            prenom="Delta",
            entite=entite.code,
            metier="DEV",
            cercle_principal="",
            email_dsm=email_dsm_racine,
            responsabilites="DSM",
        )
        + "\n"
    )
    contenu += (
        _ligne_complete(
            email=f"consultant8@{EMAIL_DOMAINE}",
            prenom="Echo",
            entite=entite.code,
            metier="DEV",
            cercle_principal="DATA",
            email_dsm=email_dsm,
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_importees == 2

    ligne_dsm, ligne_consultant = _ligne(cx, lot.identifiant, 1), _ligne(cx, lot.identifiant, 2)
    lien = cx.execute(
        text(
            "SELECT dsm_person_id FROM dsm_assignment "
            "WHERE consultant_membership_id = :m AND ends_at IS NULL"
        ),
        {"m": ligne_consultant.target_membership_id},
    ).scalar_one()
    assert lien == ligne_dsm.target_person_id
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  3. Mise a jour par e-mail, et reactivation avec confirmation explicite
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_mise_a_jour_par_e_mail_apres_une_decision_person_merge(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T9")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a9")
    email_existant = f"existant9@{EMAIL_DOMAINE}"
    personne = _personne(cx, "existant9", email=email_existant)
    _appartenance(cx, personne=personne, entite=entite.identifiant, etat="active")
    nouveau_cercle = _cercle(cx, entite=entite.identifiant, code="CLOUD")
    _metier(cx, entite=entite.identifiant, code="DEV")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t9")

    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=email_existant,
            entite=entite.code,
            metier="DEV",
            cercle_principal="CLOUD",
            email_dsm=email_dsm,
        )
        + "\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne_avant = _ligne(cx, lot.identifiant, 1)
    assert ligne_avant.state == EtatLigneImport.NEEDS_DECISION.value

    enregistrer_une_decision(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        ligne=ligne_avant.id,
        acteur=acteur,
        roles=ROLES_ESM,
        type_de_decision=TypeDeDecisionImport.PERSON_MERGE.value,
        personne_cible=personne,
        client_cible=None,
        motif=None,
        instant=INSTANT,
    )

    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_mises_a_jour == 1

    ligne_apres = _ligne(cx, lot.identifiant, 1)
    assert ligne_apres.state == EtatLigneImport.UPDATED.value
    assert ligne_apres.target_person_id == personne
    cercle_courant = cx.execute(
        text(
            "SELECT circle_id FROM circle_membership WHERE entity_membership_id = :m "
            "AND membership_type = 'principal' AND ends_at IS NULL"
        ),
        {"m": ligne_apres.target_membership_id},
    ).scalar_one()
    assert cercle_courant == nouveau_cercle
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_reactivation_d_un_profil_archive_avec_confirmation_explicite(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T10")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a10")
    email_existant = f"archive10@{EMAIL_DOMAINE}"
    personne = _personne(cx, "archive10", email=email_existant)
    _appartenance(cx, personne=personne, entite=entite.identifiant, etat="archived")
    _metier(cx, entite=entite.identifiant, code="DEV")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t10")

    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=email_existant,
            entite=entite.code,
            metier="DEV",
            cercle_principal="DATA",
            email_dsm=email_dsm,
        )
        + "\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne_avant = _ligne(cx, lot.identifiant, 1)
    assert ligne_avant.state == EtatLigneImport.NEEDS_DECISION.value

    enregistrer_une_decision(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        ligne=ligne_avant.id,
        acteur=acteur,
        roles=ROLES_ESM,
        type_de_decision=TypeDeDecisionImport.PROFILE_REACTIVATION.value,
        personne_cible=personne,
        client_cible=None,
        motif="Reembauche confirmee par l'ESM",
        instant=INSTANT,
    )

    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_mises_a_jour == 1

    etat_appartenance = cx.execute(
        text(
            "SELECT membership_state FROM entity_membership WHERE person_id = :p AND entity_id = :e"
        ),
        {"p": personne, "e": entite.identifiant},
    ).scalar_one()
    assert etat_appartenance == "active"
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_un_dsm_ne_peut_plus_enregistrer_une_reactivation(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Defaut corrige avant commit : matrice §14, DSM a TIRET sur cette ligne."""
    entite = _entite(cx, "T11")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a11")
    email_existant = f"archive11@{EMAIL_DOMAINE}"
    personne = _personne(cx, "archive11", email=email_existant)
    _appartenance(cx, personne=personne, entite=entite.identifiant, etat="archived")
    email_dsm_acteur = f"dsm11@{EMAIL_DOMAINE}"
    acteur_dsm = _personne(cx, "dsm11", email=email_dsm_acteur)

    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=email_existant,
            entite=entite.code,
            cercle_principal="",
            email_dsm=email_dsm_acteur,
        )
        + "\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite.identifiant,
            lot=lot.identifiant,
            ligne=ligne.id,
            acteur=acteur_dsm,
            roles=frozenset({RoleDeLaMatrice.DSM}),
            type_de_decision=TypeDeDecisionImport.PROFILE_REACTIVATION.value,
            personne_cible=personne,
            client_cible=None,
            motif=None,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_PORTEE_DSM_REFUSEE
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  4. `W-DEPART-001`
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_un_depart_deja_passe_importe_puis_archive_sans_acces(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T12")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a12")
    _metier(cx, entite=entite.identifiant, code="DEV")
    _cercle(cx, entite=entite.identifiant, code="DATA")

    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"parti12@{EMAIL_DOMAINE}",
            entite=entite.code,
            date_arrivee="2020-01-01",
            date_depart="2020-06-01",
            metier="DEV",
            cercle_principal="DATA",
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_importees == 1

    ligne = _ligne(cx, lot.identifiant, 1)
    etat = cx.execute(
        text("SELECT membership_state FROM entity_membership WHERE id = :m"),
        {"m": ligne.target_membership_id},
    ).scalar_one()
    assert etat == "archived"
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  5. Atomicite PAR LIGNE
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_une_ligne_en_echec_n_empeche_pas_les_autres_d_etre_importees(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Une ligne dont le cercle a ete ARCHIVE entre la previsualisation et le
    lancement echoue a l'ecriture ; la ligne suivante, elle, s'importe.
    """
    entite = _entite(cx, "T13")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a13")
    _metier(cx, entite=entite.identifiant, code="DEV")
    cercle_fragile = _cercle(cx, entite=entite.identifiant, code="FRAGILE")
    _cercle(cx, entite=entite.identifiant, code="SOLIDE")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t13")

    contenu = ENTETE_COMPLET + "\n"
    contenu += (
        _ligne_complete(
            email=f"fragile13@{EMAIL_DOMAINE}",
            prenom="Fragile",
            entite=entite.code,
            metier="DEV",
            cercle_principal="FRAGILE",
            email_dsm=email_dsm,
        )
        + "\n"
    )
    contenu += (
        _ligne_complete(
            email=f"solide13@{EMAIL_DOMAINE}",
            prenom="Solide",
            entite=entite.code,
            metier="DEV",
            cercle_principal="SOLIDE",
            email_dsm=email_dsm,
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    #  Le cercle est ARCHIVE apres la previsualisation : la revalidation
    #  fraiche d'`app.imports.execution` le trouve desormais INCONNU.
    cx.execute(
        text("UPDATE circle SET archived_at = :i WHERE id = :c"),
        {"i": INSTANT, "c": cercle_fragile},
    )

    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_importees == 1
    assert rapport.lignes_rejetees_a_l_import == 1

    fragile, solide = _ligne(cx, lot.identifiant, 1), _ligne(cx, lot.identifiant, 2)
    assert fragile.state == EtatLigneImport.REJECTED.value
    assert solide.state == EtatLigneImport.IMPORTED.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_un_metier_cree_apres_la_previsualisation_passe_au_lancement(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """`app.imports.organisation` est APPELE FRAIS a chaque lancement (jamais
    en cache, voir son en-tete) : un metier cree ENTRE le depot (qui ne
    valide PAS encore ce domaine, voir `app.imports.analyse`) et le
    lancement est donc deja connu quand `lancer_l_import` s'execute.
    """
    entite = _entite(cx, "T14")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a14")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t14")

    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"metiertardif14@{EMAIL_DOMAINE}",
            entite=entite.code,
            metier="TOUT-NOUVEAU",
            cercle_principal="DATA",
            email_dsm=email_dsm,
        )
        + "\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    #  Le metier est cree APRES le depot, AVANT le lancement : c'est cet
    #  ordre precis que `lancer_l_import` doit honorer.
    _metier(cx, entite=entite.identifiant, code="TOUT-NOUVEAU")

    rapport = lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    assert rapport.lignes_importees == 1
    assert _ligne(cx, lot.identifiant, 1).state == EtatLigneImport.IMPORTED.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  6. La grille de roles de « Lancer l'import », et l'etat du lot
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_lancer_l_import_avec_un_role_de_depot_refuse_est_hors_perimetre_de_ce_module() -> None:
    """La GARDE de route (pas ce module) refuse DSM/BOOST/OFFICE — §14, meme
    grille que `ROLES_DE_DEPOT_DE_L_IMPORT` (`T6`). Verifie ici que la
    CONSTANTE reutilisee est bien celle-la, sans redeclaration (§7.27).
    """
    assert RoleDeLaMatrice.DSM not in ROLES_DE_DEPOT_DE_L_IMPORT
    assert RoleDeLaMatrice.BOOSTER not in ROLES_DE_DEPOT_DE_L_IMPORT
    assert RoleDeLaMatrice.RESPONSABLE_DE_BUREAU not in ROLES_DE_DEPOT_DE_L_IMPORT
    assert RoleDeLaMatrice.ESM in ROLES_DE_DEPOT_DE_L_IMPORT
    assert RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE in ROLES_DE_DEPOT_DE_L_IMPORT
    assert RoleDeLaMatrice.SUPER_ADMINISTRATEUR in ROLES_DE_DEPOT_DE_L_IMPORT


@pytest.mark.integration
def test_lancer_un_lot_deja_lance_est_refuse(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T15")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a15")
    _metier(cx, entite=entite.identifiant, code="DEV")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"valide15@{EMAIL_DOMAINE}",
            entite=entite.code,
            metier="DEV",
            cercle_principal="DATA",
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )

    with pytest.raises(ErreurApplicative) as excinfo:
        lancer_l_import(
            cx,
            entite=entite.identifiant,
            lot=lot.identifiant,
            acteur=acteur,
            roles=ROLES_ESM,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_ETAT_NON_LANCABLE
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_lancer_un_lot_inconnu_est_refuse(cx: Connection) -> None:
    entite = _entite(cx, "T16")
    with pytest.raises(ErreurApplicative) as excinfo:
        lancer_l_import(
            cx,
            entite=entite.identifiant,
            lot=uuid.uuid4(),
            acteur=uuid.uuid4(),
            roles=ROLES_ESM,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_LOT_INTROUVABLE


# ---------------------------------------------------------------------------
#  10. §30.17 du modele : « un import n'ecrit aucune ligne avant approbation »
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_aucune_ecriture_metier_avant_le_lancement_de_l_import(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Le depot (`T6`) et l'analyse (`T7`/`T8`) ne creent AUCUNE personne.

    Preuve du critere de recette §30.17 du modele : une ligne entierement
    valide, deposee et previsualisee, ne laisse ni `target_person_id` ni
    `target_membership_id` renseignes sur `import_row`, et AUCUNE ligne
    `person` ne porte encore son e-mail — seul `lancer_l_import` (l'APPROBATION
    du cahier §9.5) ecrit. Le temoin negatif est apparie a un temoin POSITIF
    dans le MEME test (§7.39 de la passation) : sans lui, un pipeline qui
    n'ecrirait JAMAIS rendrait la meme observation qu'un pipeline conforme.
    """
    entite = _entite(cx, "T17")
    _domaine_local(cx, entite=entite.identifiant)
    acteur = _personne(cx, "a17")
    _metier(cx, entite=entite.identifiant, code="DEV17")
    _cercle(cx, entite=entite.identifiant, code="DATA17")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t17")
    email = f"attend17@{EMAIL_DOMAINE}"
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=email,
            entite=entite.code,
            metier="DEV17",
            cercle_principal="DATA17",
            email_dsm=email_dsm,
        )
        + "\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    #  TEMOIN NEGATIF : rien n'est ecrit avant l'approbation.
    assert ligne.state == EtatLigneImport.VALID.value
    assert ligne.target_person_id is None
    assert ligne.target_membership_id is None
    assert (
        cx.execute(text("SELECT 1 FROM person WHERE email_normalized = :e"), {"e": email}).first()
        is None
    )

    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )
    apres = _ligne(cx, lot.identifiant, 1)

    #  TEMOIN POSITIF : la MEME ligne, apres l'APPROBATION, est ecrite.
    assert apres.state == EtatLigneImport.IMPORTED.value
    assert apres.target_person_id is not None
    assert (
        cx.execute(text("SELECT 1 FROM person WHERE email_normalized = :e"), {"e": email}).first()
        is not None
    )
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
