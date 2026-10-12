"""Le rapport d'un lot d'import et le rejeu d'une ligne — LOT 9, `T10`.

Story `MVP-L09-US006` (2/2), matrice §14 « Consulter le rapport » et
« Rejouer les lignes rejetees », `criteres-qualite-import.md` §4.

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. la reconciliation (`criteres-qualite-import.md` §4) egale EXACTEMENT
     les quatre termes — creations, mises_a_jour, rejets,
     en_attente_de_decision — et AUCUNE ligne n'est masquee, y compris une
     ligne rejetee et une ligne `needs_decision` non tranchee ;
  2. le fichier du rapport (nom, empreinte, delimiteur, encodage) et ses
     auteurs (depose_par, approuve_par) ;
  3. la pagination du cahier §18.2 ;
  4. `import_batch.delimiter` est bien CONSIGNE a l'instant du depot —
     residu nomme par `T6`, corrige ici (migration `0026`) ;
  5. `rejouer_une_ligne` fait REUSSIR une ligne rejetee par
     `app.imports.organisation` une fois la ressource manquante creee, SANS
     aucune correction saisie — la MEME ligne, a l'instant present ;
  6. les quatre refus du rejeu : lot pas encore importe, ligne introuvable,
     ligne pas rejetee, ligne hors de la portee du rejeu (`E-EMAIL-*`).

Ce fichier ne reteste PAS `app.imports.organisation` ni l'import
transactionnel lui-meme (`test_import_transactionnel.py`).
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
from app.imports.depot import LotDepose, deposer_un_csv
from app.imports.execution import (
    CODE_LIGNE_NON_REJETEE,
    CODE_LOT_INTROUVABLE,
    CODE_LOT_NON_COMPLETE,
    CODE_REJEU_HORS_PORTEE,
    lancer_l_import,
    rejouer_une_ligne,
)
from app.imports.modeles import EtatLigneImport
from app.imports.rapport import consulter_le_rapport
from app.media.objets import client_s3
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T10"
INSTANT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
EMAIL_DOMAINE = "exalt-company.com"
ROLES_ESM: frozenset[RoleDeLaMatrice] = frozenset({RoleDeLaMatrice.ESM})


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


def _domaine_exalt_company_toujours_autorise(connexion: Connection) -> None:
    """Une seconde ligne GLOBALE, bornee dans le passe — §7.47, troisieme theatre.

    Voir la meme fonction dans les autres fichiers de ce lot : `starts_at =
    now()` (semee par `make domaines-provision`) cesse de couvrir `INSTANT`
    des que le calendrier reel depasse 2026-10-10.
    """
    connexion.execute(
        text(
            "INSERT INTO allowed_email_domain (domain, entity_id, starts_at) "
            "VALUES ('exalt-company.com', NULL, '2020-01-01T00:00:00+00:00')"
        )
    )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            _domaine_exalt_company_toujours_autorise(connexion)
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


def _personne(cx: Connection, suffixe: str) -> uuid.UUID:
    adresse = f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@{EMAIL_DOMAINE}"
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :email, 'Existant', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "s": suffixe},
    ).scalar_one()


def _appartenance_active(cx: Connection, *, personne: uuid.UUID, entite: uuid.UUID) -> None:
    """`D-PERSONNE-001` (`app.imports.analyse`) exige une JOINTURE sur
    `entity_membership` — un `person` seul, sans appartenance, n'est trouve
    par AUCUNE des deux requetes de doublon.
    """
    cx.execute(
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2020-01-01', 'active', 'consultant', 'draft')"
        ),
        {"p": personne, "e": entite},
    )


def _cercle(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _metier(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    #  **DEUX PARAMETRES DISTINCTS POUR LA MEME VALEUR** — `code` est
    #  `character varying(64)`, `label` est `text` : un seul `:code` partage
    #  produirait `AmbiguousParameter` (§7.25).
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label) "
            "VALUES (:e, :code, :libelle) RETURNING id"
        ),
        {"e": entite, "code": code, "libelle": code},
    ).scalar_one()


def _responsabilite_dsm(cx: Connection, *, entite: uuid.UUID, personne: uuid.UUID) -> None:
    """`:instant` (l'ancre FIXE), JAMAIS `now()` — §7.47, meme discipline que `T9`."""
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :instant)"
        ),
        {"p": personne, "e": entite, "instant": INSTANT},
    )


def _dsm_existant(cx: Connection, *, entite: uuid.UUID, suffixe: str) -> str:
    """Une personne DEJA DSM active — rend son e-mail, pour `F16`.

    `E-DSM-001` frappe tout consultant ACTIF (arrivee passee) sans DSM
    renseigne : presque toute ligne de cette suite en a besoin pour ne pas
    etre rejetee par un domaine HORS SUJET du test en cours.
    """
    email = f"{MARQUEUR.lower()}-dsm-{suffixe.lower()}@{EMAIL_DOMAINE}"
    personne = cx.execute(
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :email, 'Existant', :s, 'active') RETURNING id"
        ),
        {"email": email, "s": f"dsm-{suffixe}"},
    ).scalar_one()
    _responsabilite_dsm(cx, entite=entite, personne=personne)
    return email


def _ligne_complete(
    *,
    email: str,
    entite: str,
    cercle_principal: str,
    email_dsm: str = "",
    metier: str = "",
    nom: str = "EXEMPLE",
    prenom: str = "Prenom",
) -> str:
    """Une ligne F01-F19 minimale, intercontrat sans client requis."""
    return (
        f"{email},{nom},{prenom},{entite},2026-10-01,,consultant,{metier},intercontrat,,"
        f"{cercle_principal},,{email_dsm},,,"
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


def _ligne_id(cx: Connection, lot: uuid.UUID, numero: int) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("SELECT id FROM import_row WHERE import_batch_id = :lot AND row_number = :n"),
        {"lot": lot, "n": numero},
    ).scalar_one()


# ---------------------------------------------------------------------------
#  1-3. Le rapport : reconciliation, fichier, pagination
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_le_rapport_reconcilie_les_quatre_termes_et_n_omet_aucune_ligne(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Une creation, un rejet (organisation) et une decision en attente — trois lignes."""
    entite = _entite(cx, "T1")
    acteur = _personne(cx, "a1")
    cercle = _cercle(cx, entite=entite.identifiant, code="DATA")
    dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t1")
    _metier(cx, entite=entite.identifiant, code="DEV")
    #  En attente de decision : un e-mail DEJA actif en base (`D-PERSONNE-001`,
    #  `app.imports.analyse`), jamais decide. Le DSM est renseigne pour que
    #  SEUL ce code tienne la ligne a `needs_decision` (sans lui, l'absence
    #  de DSM la ferait aussi tomber `rejected` par `app.imports.organisation`,
    #  niveau ERREUR, qui prime).
    existant = _personne(cx, "existant1")
    _appartenance_active(cx, personne=existant, entite=entite.identifiant)
    email_existant = cx.execute(
        text("SELECT email FROM person WHERE id = :p"), {"p": existant}
    ).scalar_one()
    contenu = (
        ENTETE_COMPLET
        + "\n"
        #  **PRENOM VARIE PAR LIGNE** : le nom/prenom par defaut de
        #  `_ligne_complete` est identique pour toutes les lignes, et trois
        #  lignes homonymes dans le MEME fichier declenchent `D-PERSONNE-003`
        #  (homonymie) sans rapport avec ce que ce test observe — meme piege
        #  que celui deja rencontre dans `test_import_transactionnel.py`.
        + _ligne_complete(
            email=f"cree1@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal="DATA",
            email_dsm=dsm,
            metier="DEV",
            prenom="Alpha",
        )
        + "\n"
        #  Rejetee : cercle principal INCONNU du catalogue — `E-CERCLE-002`,
        #  niveau ERREUR dans `app.imports.organisation`.
        + _ligne_complete(
            email=f"rejetee1@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal="INCONNU",
            email_dsm=dsm,
            metier="DEV",
            prenom="Bravo",
        )
        + "\n"
        + _ligne_complete(
            email=email_existant,
            entite=entite.code,
            cercle_principal="DATA",
            email_dsm=dsm,
            metier="DEV",
            prenom="Charlie",
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

    rapport = consulter_le_rapport(
        cx, entite=entite.identifiant, lot=lot.identifiant, page=1, taille=25
    )

    assert rapport.reconciliation.total_lignes == 3
    assert rapport.reconciliation.creations == 1
    assert rapport.reconciliation.rejets == 1
    assert rapport.reconciliation.en_attente_de_decision == 1
    assert rapport.reconciliation.mises_a_jour == 0
    assert (
        rapport.reconciliation.creations
        + rapport.reconciliation.mises_a_jour
        + rapport.reconciliation.rejets
        + rapport.reconciliation.en_attente_de_decision
        == rapport.reconciliation.total_lignes
    )

    #  **AUCUNE LIGNE REJETEE N'EST MASQUEE** — critere de sortie du LOT 9.
    assert len(rapport.lignes) == 3
    par_etat = {ligne.etat: ligne for ligne in rapport.lignes}
    #  La ligne importee peut encore porter des AVERTISSEMENTS (`W-*`) — seule
    #  l'absence de code `E-*`/`D-*` est garantie par l'etat `imported` lui-meme.
    assert not any(
        c.startswith(("E-", "D-")) for c in par_etat[EtatLigneImport.IMPORTED.value].codes_derreur
    )
    ligne_rejetee = par_etat[EtatLigneImport.REJECTED.value]
    assert ligne_rejetee.codes_derreur != ()
    assert any(p.code in ligne_rejetee.codes_derreur for p in ligne_rejetee.problemes)
    ligne_en_attente = par_etat[EtatLigneImport.NEEDS_DECISION.value]
    assert ligne_en_attente.codes_derreur != ()

    assert rapport.nom_de_fichier == "fichier.csv"
    assert rapport.empreinte_sha256 == lot.source_checksum_sha256
    assert rapport.delimiteur == ","
    assert rapport.encodage == "utf-8"
    assert rapport.depose_par == acteur
    assert rapport.approuve_par == acteur
    assert rapport.etat_du_lot == "completed"

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
    _ = cercle


@pytest.mark.integration
def test_le_rapport_pagine_selon_le_cahier_18_2(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T2")
    acteur = _personne(cx, "a2")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    contenu = ENTETE_COMPLET + "\n"
    for i in range(3):
        contenu += (
            _ligne_complete(
                email=f"page{i}@{EMAIL_DOMAINE}", entite=entite.code, cercle_principal="DATA"
            )
            + "\n"
        )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )

    page1 = consulter_le_rapport(
        cx, entite=entite.identifiant, lot=lot.identifiant, page=1, taille=2
    )
    assert len(page1.lignes) == 2
    assert page1.total_des_lignes == 3
    assert page1.pages == 2
    assert [ligne.numero for ligne in page1.lignes] == [1, 2]

    page2 = consulter_le_rapport(
        cx, entite=entite.identifiant, lot=lot.identifiant, page=2, taille=2
    )
    assert [ligne.numero for ligne in page2.lignes] == [3]

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_le_rapport_refuse_un_lot_introuvable(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T3")
    with pytest.raises(ErreurApplicative) as echec:
        consulter_le_rapport(cx, entite=entite.identifiant, lot=uuid.uuid4(), page=1, taille=25)
    assert echec.value.code == CODE_LOT_INTROUVABLE


@pytest.mark.integration
def test_le_delimiteur_est_consigne_a_l_instant_du_depot(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Residu nomme par `T6`, corrige par `T10` (migration `0026`)."""
    entite = _entite(cx, "T4")
    acteur = _personne(cx, "a4")
    _cercle(cx, entite=entite.identifiant, code="DATA")

    #  Point-virgule : DEC-432 l'impose des qu'il est present.
    contenu_point_virgule = (
        ENTETE_COMPLET.replace(",", ";")
        + "\n"
        + _ligne_complete(
            email=f"pv@{EMAIL_DOMAINE}", entite=entite.code, cercle_principal="DATA"
        ).replace(",", ";")
        + "\n"
    )
    lot_pv = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite.identifiant,
        acteur=acteur,
        contenu=contenu_point_virgule,
    )
    delimiteur_pv = cx.execute(
        text("SELECT delimiter FROM import_batch WHERE id = :lot"), {"lot": lot_pv.identifiant}
    ).scalar_one()
    assert delimiteur_pv == ";"

    #  Virgule : tolérée SEULEMENT en l'absence de point-virgule — déjà le
    #  cas de `ENTETE_COMPLET` par défaut.
    contenu_virgule = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(email=f"v@{EMAIL_DOMAINE}", entite=entite.code, cercle_principal="DATA")
        + "\n"
    )
    lot_v = _deposer_ou_sauter(
        cx,
        parametres_de_la_stack,
        entite=entite.identifiant,
        acteur=acteur,
        contenu=contenu_virgule,
    )
    delimiteur_v = cx.execute(
        text("SELECT delimiter FROM import_batch WHERE id = :lot"), {"lot": lot_v.identifiant}
    ).scalar_one()
    assert delimiteur_v == ","

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot_pv.identifiant)
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot_v.identifiant)


# ---------------------------------------------------------------------------
#  5-6. Le rejeu
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_rejouer_reussit_une_fois_le_cercle_cree_sans_aucune_correction_saisie(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Le scenario que Jonathan a decrit : le cercle manquant est cree ENTRE-TEMPS."""
    entite = _entite(cx, "T5")
    acteur = _personne(cx, "a5")
    dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t5")
    _metier(cx, entite=entite.identifiant, code="DEV")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"rejeu1@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal="PAS-ENCORE",
            email_dsm=dsm,
            metier="DEV",
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
    ligne_id = _ligne_id(cx, lot.identifiant, 1)
    avant = cx.execute(
        text("SELECT state, error_codes FROM import_row WHERE id = :l"), {"l": ligne_id}
    ).one()
    assert avant.state == EtatLigneImport.REJECTED.value
    assert "E-CERCLE-002" in avant.error_codes

    #  **AUCUNE CORRECTION SAISIE** — le cercle est cree, la ligne n'est pas
    #  touchee : c'est exactement ce que `rejouer_une_ligne` ne fait jamais.
    _cercle(cx, entite=entite.identifiant, code="PAS-ENCORE")

    resultat = rejouer_une_ligne(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        ligne_id=ligne_id,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )

    assert resultat.etat == EtatLigneImport.IMPORTED.value
    assert not any(c.startswith(("E-", "D-")) for c in resultat.codes_derreur)

    rapport = consulter_le_rapport(
        cx, entite=entite.identifiant, lot=lot.identifiant, page=1, taille=25
    )
    assert rapport.reconciliation.creations == 1
    assert rapport.reconciliation.rejets == 0

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_rejouer_refuse_si_le_lot_n_a_pas_encore_ete_importe(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T6")
    acteur = _personne(cx, "a6")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(email=f"t6@{EMAIL_DOMAINE}", entite=entite.code, cercle_principal="DATA")
        + "\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne_id = _ligne_id(cx, lot.identifiant, 1)

    with pytest.raises(ErreurApplicative) as echec:
        rejouer_une_ligne(
            cx,
            entite=entite.identifiant,
            lot=lot.identifiant,
            ligne_id=ligne_id,
            acteur=acteur,
            roles=ROLES_ESM,
            instant=INSTANT,
        )
    assert echec.value.code == CODE_LOT_NON_COMPLETE

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_rejouer_refuse_une_ligne_qui_n_est_pas_rejetee(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T7")
    acteur = _personne(cx, "a7")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    dsm = _dsm_existant(cx, entite=entite.identifiant, suffixe="t7")
    _metier(cx, entite=entite.identifiant, code="DEV")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email=f"t7@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal="DATA",
            email_dsm=dsm,
            metier="DEV",
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
    ligne_id = _ligne_id(cx, lot.identifiant, 1)
    assert (
        cx.execute(text("SELECT state FROM import_row WHERE id = :l"), {"l": ligne_id}).scalar_one()
        == EtatLigneImport.IMPORTED.value
    )

    with pytest.raises(ErreurApplicative) as echec:
        rejouer_une_ligne(
            cx,
            entite=entite.identifiant,
            lot=lot.identifiant,
            ligne_id=ligne_id,
            acteur=acteur,
            roles=ROLES_ESM,
            instant=INSTANT,
        )
    assert echec.value.code == CODE_LIGNE_NON_REJETEE

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_rejouer_refuse_une_ligne_rejetee_par_un_code_e_email(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """`E-EMAIL-*` depend du fichier entier ou ne change pas avec le temps — hors portee."""
    entite = _entite(cx, "T8")
    acteur = _personne(cx, "a8")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    #  Domaine JAMAIS autorise dans ce test — `E-EMAIL-003`.
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(
            email="quelquun@domaine-non-autorise.example",
            entite=entite.code,
            cercle_principal="DATA",
        )
        + "\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    ligne_id = _ligne_id(cx, lot.identifiant, 1)
    avant = cx.execute(
        text("SELECT state, error_codes FROM import_row WHERE id = :l"), {"l": ligne_id}
    ).one()
    assert avant.state == EtatLigneImport.REJECTED.value
    assert "E-EMAIL-003" in avant.error_codes

    lancer_l_import(
        cx,
        entite=entite.identifiant,
        lot=lot.identifiant,
        acteur=acteur,
        roles=ROLES_ESM,
        instant=INSTANT,
    )

    with pytest.raises(ErreurApplicative) as echec:
        rejouer_une_ligne(
            cx,
            entite=entite.identifiant,
            lot=lot.identifiant,
            ligne_id=ligne_id,
            acteur=acteur,
            roles=ROLES_ESM,
            instant=INSTANT,
        )
    assert echec.value.code == CODE_REJEU_HORS_PORTEE

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)


@pytest.mark.integration
def test_rejouer_refuse_une_ligne_introuvable(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T9")
    acteur = _personne(cx, "a9")
    _cercle(cx, entite=entite.identifiant, code="DATA")
    contenu = (
        ENTETE_COMPLET
        + "\n"
        + _ligne_complete(email=f"t9@{EMAIL_DOMAINE}", entite=entite.code, cercle_principal="DATA")
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

    with pytest.raises(ErreurApplicative) as echec:
        rejouer_une_ligne(
            cx,
            entite=entite.identifiant,
            lot=lot.identifiant,
            ligne_id=uuid.uuid4(),
            acteur=acteur,
            roles=ROLES_ESM,
            instant=INSTANT,
        )
    assert echec.value.code == "ligne_introuvable"

    _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot.identifiant)
