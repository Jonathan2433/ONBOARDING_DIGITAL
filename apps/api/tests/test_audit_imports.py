"""Le cablage de l'audit generique sur l'import CSV (LOT 9) — LOT 10, `T7`.

Stories `MVP-L10-US001`/`US002`, modele §21.1, `ARB-DATA-005`/`§30.20`.

CE QUE CE FICHIER PROUVE, ET DANS QUEL ORDRE

  1. `deposer_un_csv` (depot + previsualisation, LOT 9 `T6`/`T7`) ecrit UN
     SEUL `audit_event` pour l'appel entier ;
  2. `enregistrer_une_decision` (LOT 9 `T8`) ecrit un `audit_event`, et exige
     un motif quand `SUPER` autorise l'appel (`ECART-064`) ;
  3. `lancer_l_import` (LOT 9 `T9`) exige lui aussi un motif pour `SUPER`,
     jamais pour `ESM` ;
  4. les QUATRE ecritures de `lancer_l_import` qui n'etaient PAS deja
     auditees par l'heritage de `T3` — responsabilites Framework, roles
     techniques, cercles secondaires, resolution du DSM — ecrivent chacune
     leur propre `audit_event`, chacun reprenant le MEME motif que l'appel
     entier ;
  5. `rejouer_une_ligne` herite du meme cablage que `lancer_l_import`, via
     `_traiter_une_ligne` partagee.

CE QUE CE FICHIER NE REPROUVE PAS

  Les regles METIER de l'import (validation du referentiel, savepoint par
  ligne, deux passes) sont deja prouvees par `test_import_transactionnel.py`,
  `test_depot_import.py`, `test_analyse_import.py`, `test_rapport_import.py`.
  Ce fichier ne porte que ce que `T7` ajoute : la ligne `audit_event`
  elle-meme, et le motif du §18.1.
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

from app.audit.motif import CODE_MOTIF_OBLIGATOIRE
from app.configuration.settings import Parametres
from app.imports.decisions import enregistrer_une_decision
from app.imports.depot import deposer_un_csv
from app.imports.execution import lancer_l_import, rejouer_une_ligne
from app.imports.modeles import EtatLigneImport, EtatLotImport, TypeDeDecisionImport
from app.media.objets import client_s3
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "T7L10"
INSTANT = dt.datetime(2026, 10, 19, 9, 0, tzinfo=dt.UTC)
EMAIL_DOMAINE = "exalt-company.com"
ROLES_ESM: frozenset[RoleDeLaMatrice] = frozenset({RoleDeLaMatrice.ESM})
ROLES_SUPER: frozenset[RoleDeLaMatrice] = frozenset({RoleDeLaMatrice.SUPER_ADMINISTRATEUR})

ENTETE = (
    "email,nom,prenom,entite,date_arrivee,date_depart,categorie_professionnelle,"
    "metier,situation,client,cercle_principal,cercles_secondaires,email_dsm,"
    "responsabilites_framework,roles_techniques,autorisation_photo"
)


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip("PostgreSQL absent — lancer `make up`, puis `make migrate`.")


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    """Connexion en ROLLBACK : aucun test ne laisse de ligne derriere lui."""
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


# ---------------------------------------------------------------------------
#  Le decor. Local a ce fichier (§7.27 de la passation : chaque depot est
#  taille a sa question), bati sur le MEME patron que `test_import_
#  transactionnel.py` — pas importe de la, une duplication minimale valant
#  mieux qu'un couplage entre deux fichiers de test.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class _Entite:
    identifiant: uuid.UUID
    code: str


def _entite(cx: Connection, suffixe: str) -> _Entite:
    code = f"{MARQUEUR}-{suffixe}-{uuid.uuid4().hex[:6]}"
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


def _appartenance(cx: Connection, *, personne: uuid.UUID, entite: uuid.UUID) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
            "membership_state, professional_category, profile_visibility) "
            "VALUES (:p, :e, '2020-01-01', 'active', 'consultant', 'draft') RETURNING id"
        ),
        {"p": personne, "e": entite},
    ).scalar_one()


def _cercle(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text("INSERT INTO circle (entity_id, code, name) VALUES (:e, :code, :nom) RETURNING id"),
        {"e": entite, "code": code, "nom": code},
    ).scalar_one()


def _metier(cx: Connection, *, entite: uuid.UUID, code: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO job_catalog (entity_id, code, label) "
            "VALUES (:e, :code, :libelle) RETURNING id"
        ),
        {"e": entite, "code": code, "libelle": code},
    ).scalar_one()


def _responsabilite_dsm(cx: Connection, *, entite: uuid.UUID, personne: uuid.UUID) -> None:
    cx.execute(
        text(
            "INSERT INTO framework_responsibility_assignment "
            "(person_id, entity_id, responsibility_type, assigned_by_person_id, starts_at) "
            "VALUES (:p, :e, 'DSM', :p, :instant)"
        ),
        {"p": personne, "e": entite, "instant": INSTANT},
    )


def _dsm_existant(cx: Connection, *, entite: uuid.UUID) -> str:
    """Une personne DEJA DSM active (en base) — rend son e-mail, pour `F16`."""
    email = f"{MARQUEUR.lower()}-dsm-{uuid.uuid4().hex[:6]}@{EMAIL_DOMAINE}"
    personne = _personne(cx, "dsm", email=email)
    _responsabilite_dsm(cx, entite=entite, personne=personne)
    return email


def _ligne_complete(
    *,
    email: str,
    entite: str,
    cercle_principal: str,
    metier: str = "",
    cercles_secondaires: str = "",
    email_dsm: str = "",
    responsabilites: str = "",
    roles_techniques: str = "",
) -> str:
    """Une ligne CSV minimale, valide par defaut — intercontrat, sans client.

    `intercontrat` (francais, litteralement cite par `codes-erreurs-
    import.md`) est la valeur CSV attendue en F12 — PAS la valeur de colonne
    `intercontract` que porte `SituationProfessionnelle` : les deux divergent
    deliberement, `app.imports.organisation` traduit l'une vers l'autre.
    """
    return (
        f"{email},EXEMPLE,Prenom,{entite},2026-10-01,,consultant,{metier},intercontrat,,"
        f"{cercle_principal},{cercles_secondaires},{email_dsm},{responsabilites},"
        f"{roles_techniques},"
    )


def _deposer_ou_sauter(
    cx: Connection, parametres: Parametres, *, entite: uuid.UUID, acteur: uuid.UUID, contenu: str
) -> uuid.UUID:
    try:
        lot = deposer_un_csv(
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
    return lot.identifiant


def _nettoyer_le_lot(parametres: Parametres, *, entite: uuid.UUID, lot: uuid.UUID) -> None:
    client = client_s3(parametres)
    with contextlib.suppress(Exception):
        client.delete_object(  # type: ignore[attr-defined]
            Bucket=parametres.MINIO_BUCKET, Key=f"imports/{entite}/{lot}.csv"
        )


def _audit_events(cx: Connection, *, entite: uuid.UUID) -> list[dict[str, object]]:
    lignes = cx.execute(
        text(
            "SELECT action_code, resource_type, resource_reference, entity_id, "
            "actor_person_id, reason, old_values, new_values "
            "FROM audit_event WHERE entity_id = :e ORDER BY occurred_at"
        ),
        {"e": entite},
    ).mappings()
    return [dict(ligne) for ligne in lignes]


# ---------------------------------------------------------------------------
#  1. Le depot — `deposer_un_csv`.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_deposer_un_csv_ecrit_un_seul_audit_event(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "depot")
    contenu = (
        ENTETE + "\n" + _ligne_complete(email="x@y.test", entite=entite.code, cercle_principal="")
    )
    acteur = _personne(cx, "acteur")
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    try:
        evenements = _audit_events(cx, entite=entite.identifiant)
        assert len(evenements) == 1
        evenement = evenements[0]
        assert evenement["action_code"] == "import_lot_depose"
        assert evenement["resource_type"] == "import_batch"
        assert uuid.UUID(str(evenement["resource_reference"])) == lot
        assert uuid.UUID(str(evenement["actor_person_id"])) == acteur
        assert evenement["reason"] is None
    finally:
        _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot)


# ---------------------------------------------------------------------------
#  2. Une decision — `enregistrer_une_decision`. `voluntary_rejection` :
#     aucun code requis, aucune cible — le decor le plus simple qui exerce le
#     chemin generique, exactement ce que ce fichier doit prouver (§7.27 :
#     ne jamais rebatir ce qu'un autre test prouve deja pour les CINQ types).
# ---------------------------------------------------------------------------


def _lot_et_ligne_en_attente(cx: Connection, *, entite: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    lot = cx.execute(
        text(
            "INSERT INTO import_batch (entity_id, source_filename, source_checksum_sha256, "
            "state, total_rows) VALUES (:e, 'f.csv', 'empreinte', :etat, 1) RETURNING id"
        ),
        {"e": entite, "etat": EtatLotImport.PREVIEW_READY.value},
    ).scalar_one()
    ligne = cx.execute(
        text(
            "INSERT INTO import_row (entity_id, import_batch_id, row_number, raw_data, state) "
            "VALUES (:e, :lot, 1, '{}'::jsonb, :etat) RETURNING id"
        ),
        {"e": entite, "lot": lot, "etat": EtatLigneImport.NEEDS_DECISION.value},
    ).scalar_one()
    return uuid.UUID(str(lot)), uuid.UUID(str(ligne))


@pytest.mark.integration
def test_enregistrer_une_decision_ecrit_un_audit_event(cx: Connection) -> None:
    entite = _entite(cx, "decision")
    lot, ligne = _lot_et_ligne_en_attente(cx, entite=entite.identifiant)
    acteur = _personne(cx, "esm")

    decision = enregistrer_une_decision(
        cx,
        entite=entite.identifiant,
        lot=lot,
        ligne=ligne,
        acteur=acteur,
        roles=ROLES_ESM,
        type_de_decision=TypeDeDecisionImport.VOLUNTARY_REJECTION.value,
        personne_cible=None,
        client_cible=None,
        motif=None,
        instant=INSTANT,
    )

    evenements = _audit_events(cx, entite=entite.identifiant)
    assert len(evenements) == 1
    assert evenements[0]["action_code"] == "decision_d_import_enregistree"
    assert evenements[0]["resource_type"] == "import_decision"
    assert uuid.UUID(str(evenements[0]["resource_reference"])) == decision.identifiant
    assert evenements[0]["reason"] is None


@pytest.mark.integration
def test_enregistrer_une_decision_exige_un_motif_pour_super(cx: Connection) -> None:
    entite = _entite(cx, "decision-super")
    lot, ligne = _lot_et_ligne_en_attente(cx, entite=entite.identifiant)
    acteur = _personne(cx, "super")

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite.identifiant,
            lot=lot,
            ligne=ligne,
            acteur=acteur,
            roles=ROLES_SUPER,
            type_de_decision=TypeDeDecisionImport.VOLUNTARY_REJECTION.value,
            personne_cible=None,
            client_cible=None,
            motif=None,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_MOTIF_OBLIGATOIRE
    assert excinfo.value.statut == 422

    #  **TEMOIN POSITIF, APPARIE** (§7.39) : le MEME appel, motif fourni,
    #  reussit et le motif se retrouve dans `audit_event.reason`.
    decision = enregistrer_une_decision(
        cx,
        entite=entite.identifiant,
        lot=lot,
        ligne=ligne,
        acteur=acteur,
        roles=ROLES_SUPER,
        type_de_decision=TypeDeDecisionImport.VOLUNTARY_REJECTION.value,
        personne_cible=None,
        client_cible=None,
        motif="Decision prise sur demande de Jonathan",
        instant=INSTANT,
    )
    evenements = _audit_events(cx, entite=entite.identifiant)
    assert len(evenements) == 1
    assert uuid.UUID(str(evenements[0]["resource_reference"])) == decision.identifiant
    assert evenements[0]["reason"] == "Decision prise sur demande de Jonathan"


# ---------------------------------------------------------------------------
#  3 et 4. `lancer_l_import` — le motif, et les quatre ecritures internes.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_lancer_l_import_exige_un_motif_pour_super_jamais_pour_esm(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "lancement")
    _domaine_local(cx, entite=entite.identifiant)
    _cercle(cx, entite=entite.identifiant, code=f"{entite.code}-cercle")
    _metier(cx, entite=entite.identifiant, code=f"{entite.code}-metier")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant)
    acteur = _personne(cx, "acteur")
    contenu = (
        ENTETE
        + "\n"
        + _ligne_complete(
            email=f"{MARQUEUR.lower()}-{uuid.uuid4().hex[:8]}@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal=f"{entite.code}-cercle",
            metier=f"{entite.code}-metier",
            email_dsm=email_dsm,
        )
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    try:
        with pytest.raises(ErreurApplicative) as excinfo:
            lancer_l_import(
                cx,
                entite=entite.identifiant,
                lot=lot,
                acteur=acteur,
                roles=ROLES_SUPER,
                motif=None,
                instant=INSTANT,
            )
        assert excinfo.value.code == CODE_MOTIF_OBLIGATOIRE

        #  **TEMOIN POSITIF** : la MEME requete, par un role LOCAL (`ESM`),
        #  sans motif, reussit — la regle ne s'applique jamais a lui.
        rapport = lancer_l_import(
            cx,
            entite=entite.identifiant,
            lot=lot,
            acteur=acteur,
            roles=ROLES_ESM,
            motif=None,
            instant=INSTANT,
        )
        assert rapport.lignes_importees == 1
    finally:
        _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot)


@pytest.mark.integration
def test_lancer_l_import_ecrit_les_quatre_evenements_non_herites(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Les quatre ecritures PROPRES a l'import — responsabilites Framework,
    roles techniques, cercles secondaires, resolution du DSM — que `T3`
    n'avait PAS auditees (elles ne passent par aucune fonction partagee deja
    cablee). Reprises par un motif unique, celui de l'appel entier.
    """
    entite = _entite(cx, "interne")
    _domaine_local(cx, entite=entite.identifiant)
    _cercle(cx, entite=entite.identifiant, code=f"{entite.code}-principal")
    cercle_secondaire = _cercle(cx, entite=entite.identifiant, code=f"{entite.code}-secondaire")
    _metier(cx, entite=entite.identifiant, code=f"{entite.code}-metier")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant)
    acteur = _personne(cx, "acteur")

    contenu = (
        ENTETE
        + "\n"
        + _ligne_complete(
            email=f"{MARQUEUR.lower()}-{uuid.uuid4().hex[:8]}@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal=f"{entite.code}-principal",
            metier=f"{entite.code}-metier",
            cercles_secondaires=f"{entite.code}-secondaire",
            email_dsm=email_dsm,
            responsabilites="ESM",
            roles_techniques="ENTITY_ADMIN",
        )
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    try:
        rapport = lancer_l_import(
            cx,
            entite=entite.identifiant,
            lot=lot,
            acteur=acteur,
            roles=ROLES_SUPER,
            motif="Import de reprise, autorise par Jonathan",
            instant=INSTANT,
        )
        assert rapport.lignes_importees == 1

        evenements = {
            str(evenement["action_code"]): evenement
            for evenement in _audit_events(cx, entite=entite.identifiant)
        }
        #  Les CINQ actions attendues : la creation du collaborateur (deja
        #  auditee par `T3`, heritee sans cablage ici) plus les QUATRE
        #  nouvelles de `T7`.
        assert "collaborateur_cree" in evenements
        for code_action in (
            "responsabilites_framework_accordees",
            "roles_techniques_accordes_a_l_import",
            "cercles_secondaires_rafraichis",
            "dsm_resolu_a_l_import",
        ):
            assert code_action in evenements, f"evenement manquant : {code_action}"
            evenement = evenements[code_action]
            assert evenement["reason"] == "Import de reprise, autorise par Jonathan"

        responsabilites = evenements["responsabilites_framework_accordees"]
        assert responsabilites["resource_type"] == "framework_responsibility_assignment"

        roles_techniques = evenements["roles_techniques_accordes_a_l_import"]
        assert roles_techniques["resource_type"] == "technical_role_assignment"
        nouvelles_valeurs_roles = dict(roles_techniques["new_values"])  # type: ignore[call-overload]
        assert nouvelles_valeurs_roles["roles_techniques"] == ["ENTITY_ADMIN"]

        cercles = evenements["cercles_secondaires_rafraichis"]
        assert cercles["resource_type"] == "circle_membership"
        nouvelles_valeurs_cercles = dict(cercles["new_values"])  # type: ignore[call-overload]
        assert nouvelles_valeurs_cercles["cercles_ouverts"] == [str(cercle_secondaire)]

        dsm = evenements["dsm_resolu_a_l_import"]
        assert dsm["resource_type"] == "dsm_assignment"
        assert dsm["old_values"] is None
    finally:
        _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot)


@pytest.mark.integration
def test_rejouer_une_ligne_herite_le_meme_cablage(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """`rejouer_une_ligne` appelle la MEME `_traiter_une_ligne` que `lancer_
    l_import` — un seul temoin suffit a prouver l'heritage, le reste de la
    mecanique (savepoint, revalidation fraiche) est deja prouve par
    `test_import_transactionnel.py`.
    """
    entite = _entite(cx, "rejeu")
    _domaine_local(cx, entite=entite.identifiant)
    _metier(cx, entite=entite.identifiant, code=f"{entite.code}-metier")
    email_dsm = _dsm_existant(cx, entite=entite.identifiant)
    acteur = _personne(cx, "acteur")
    #  Le CODE du cercle est deja ECRIT dans la ligne, mais le cercle n'existe
    #  PAS ENCORE — `cercle_principal_inconnu`, rejetee. Creer le cercle APRES
    #  coup (meme code) est ce qui resout le blocage au rejeu : `raw_data` est
    #  IMMUABLE, changer le CODE au rejeu ne prouverait rien de la revalidation
    #  fraiche — c'est le cercle qui doit apparaitre, pas le code qui change.
    code_cercle = f"{entite.code}-principal"
    contenu = (
        ENTETE
        + "\n"
        + _ligne_complete(
            email=f"{MARQUEUR.lower()}-{uuid.uuid4().hex[:8]}@{EMAIL_DOMAINE}",
            entite=entite.code,
            cercle_principal=code_cercle,
            metier=f"{entite.code}-metier",
            email_dsm=email_dsm,
        )
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite.identifiant, acteur=acteur, contenu=contenu
    )
    try:
        rapport = lancer_l_import(
            cx,
            entite=entite.identifiant,
            lot=lot,
            acteur=acteur,
            roles=ROLES_ESM,
            motif=None,
            instant=INSTANT,
        )
        assert rapport.lignes_rejetees_a_l_import == 1

        ligne_id = cx.execute(
            text("SELECT id FROM import_row WHERE import_batch_id = :lot"), {"lot": lot}
        ).scalar_one()

        #  Le cercle est cree ENTRE-TEMPS, avec le MEME code — meme discipline
        #  que `test_import_transactionnel.py` pour la revalidation fraiche.
        _cercle(cx, entite=entite.identifiant, code=code_cercle)

        with pytest.raises(ErreurApplicative) as excinfo:
            rejouer_une_ligne(
                cx,
                entite=entite.identifiant,
                lot=lot,
                ligne_id=uuid.UUID(str(ligne_id)),
                acteur=acteur,
                roles=ROLES_SUPER,
                motif=None,
                instant=INSTANT,
            )
        assert excinfo.value.code == CODE_MOTIF_OBLIGATOIRE

        resultat = rejouer_une_ligne(
            cx,
            entite=entite.identifiant,
            lot=lot,
            ligne_id=uuid.UUID(str(ligne_id)),
            acteur=acteur,
            roles=ROLES_SUPER,
            motif="Rejeu autorise",
            instant=INSTANT,
        )
        assert resultat.etat == EtatLigneImport.IMPORTED.value

        evenements = _audit_events(cx, entite=entite.identifiant)
        assert any(
            str(e["action_code"]) == "collaborateur_cree" and e["reason"] == "Rejeu autorise"
            for e in evenements
        )
    finally:
        _nettoyer_le_lot(parametres_de_la_stack, entite=entite.identifiant, lot=lot)
