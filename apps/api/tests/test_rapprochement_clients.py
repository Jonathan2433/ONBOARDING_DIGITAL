"""Rapprocher les clients, enregistrer une décision humaine — LOT 9, `T8`.

Story `MVP-L09-US005` — « Valider les rapprochements de clients ».

CE QUE CETTE SUITE PROUVE, ET DANS QUEL ORDRE

  1. les quatre issues du rapprochement d'un client (`F13`) : correspondance
     exacte déjà active localement (aucun code), client global pas encore
     activé (`W-CLIENT-001`), client inconnu (`D-CLIENT-002`), et la priorité
     STRICTE alias local > alias global > nom canonique ;
  2. le témoin négatif central : **`D-CLIENT-001` n'est JAMAIS produit**,
     même pour un nom qui « ressemble » fortement à un client existant —
     arbitrage explicite de Jonathan, aucune détection automatique ;
  3. `GET .../clients` ferme `ECART-060` : un client non encore activé
     localement reste VISIBLE, sinon personne ne pourrait le choisir ;
  4. l'enregistrement d'une décision : `client_alias_creation` crée la ligne
     `client_alias` ET met à jour `normalized_data`, `canonical_client_selection`
     met à jour `normalized_data` SANS créer d'alias — et dans les DEUX cas,
     `import_row.state` reste `needs_decision` (ce n'est PAS un import) ;
  5. les refus : type de décision incohérent avec les codes de la ligne,
     cible manquante, cible inconnue, ligne qui n'attend aucune décision ;
  6. la portée DSM : refusé hors de son périmètre (`F16` ne le désigne pas),
     accepté dans son périmètre — et un rôle à portée large (ESM) n'a besoin
     d'aucun périmètre.

Ce fichier ne reteste PAS la normalisation de l'e-mail ni les doublons de
personne (`test_analyse_import.py`, `T7`), ni le dépôt du CSV
(`test_depot_import.py`, `T6`).
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
from app.imports.clients import (
    CODE_CLIENT_INCONNU,
    CODE_CLIENT_NON_ACTIVE_LOCALEMENT,
    lister_les_clients,
)
from app.imports.decisions import (
    CODE_CIBLE_INCONNUE,
    CODE_CIBLE_MANQUANTE,
    CODE_LIGNE_INTROUVABLE,
    CODE_PORTEE_DSM_REFUSEE,
    CODE_TYPE_INCOHERENT,
    enregistrer_une_decision,
)
from app.imports.depot import LotDepose, deposer_un_csv
from app.imports.modeles import EtatLigneImport, TypeDeDecisionImport
from app.media.objets import client_s3
from app.permissions.services import RoleDeLaMatrice
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

MARQUEUR = "L9T8"
INSTANT = dt.datetime(2026, 10, 10, 9, 0, tzinfo=dt.UTC)
EMAIL_DOMAINE = "exalt-company.com"


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


def _personne(cx: Connection, suffixe: str, *, email: str | None = None) -> uuid.UUID:
    adresse = (
        email or f"{MARQUEUR.lower()}-{suffixe.lower()}-{uuid.uuid4().hex[:8]}@{EMAIL_DOMAINE}"
    )
    normalise = adresse.strip().lower()
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO person (email, email_normalized, first_name, last_name, account_state) "
            "VALUES (:email, :normalise, 'Client', :s, 'active') RETURNING id"
        ),
        {"email": adresse, "normalise": normalise, "s": suffixe},
    ).scalar_one()


def _client(cx: Connection, nom_canonique: str) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO client (canonical_name, display_name, status) "
            "VALUES (:canonique, :affiche, 'active') RETURNING id"
        ),
        {"canonique": nom_canonique, "affiche": nom_canonique.title()},
    ).scalar_one()


def _activer_localement(cx: Connection, *, entite: uuid.UUID, client: uuid.UUID) -> None:
    cx.execute(
        text("INSERT INTO entity_client (entity_id, client_id) VALUES (:e, :c)"),
        {"e": entite, "c": client},
    )


def _alias(
    cx: Connection, *, nom: str, client: uuid.UUID, validateur: uuid.UUID, entite: uuid.UUID | None
) -> uuid.UUID:
    return cx.execute(  # type: ignore[no-any-return]
        text(
            "INSERT INTO client_alias "
            "(entity_id, alias_normalized, client_id, validated_by_person_id, validated_at) "
            "VALUES (:entite, :nom, :client, :validateur, now()) RETURNING id"
        ),
        {"entite": entite, "nom": nom, "client": client, "validateur": validateur},
    ).scalar_one()


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
    """Supprime l'objet MinIO par SA CLE CONNUE — jamais par relecture en base.

    **NE JAMAIS REINTERROGER `cx` ICI** : un test qui attend une erreur de
    contrainte (`IntegrityError`/`DataError`, traduite par le service) laisse
    la transaction PostgreSQL AVORTEE — toute requete suivante sur la MEME
    connexion echouerait avec `InFailedSqlTransaction`, meme une lecture
    anodine. La cle suit la convention deterministe de `app.imports.depot`
    (`imports/{entite}/{lot}.csv`), jamais une colonne relue.
    """
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
    normalized_data: dict[str, str] | None


def _ligne(cx: Connection, lot: uuid.UUID, numero: int) -> _LigneVue:
    ligne = cx.execute(
        text(
            "SELECT id, state, error_codes, normalized_data FROM import_row "
            "WHERE import_batch_id = :lot AND row_number = :n"
        ),
        {"lot": lot, "n": numero},
    ).one()
    return _LigneVue(
        id=ligne.id,
        state=ligne.state,
        error_codes=ligne.error_codes,
        normalized_data=ligne.normalized_data,
    )


# ---------------------------------------------------------------------------
#  1. Les quatre issues du rapprochement, et la priorite stricte des alias
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_correspondance_exacte_active_localement_ne_produit_aucun_code(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T1")
    acteur = _personne(cx, "a1")
    client = _client(cx, f"{MARQUEUR.lower()} client un")
    _activer_localement(cx, entite=entite, client=client)
    contenu = (
        f"email,nom,prenom,situation,client\n"
        f"valide1@{EMAIL_DOMAINE},EXEMPLE,Un,mission,{MARQUEUR.lower()} client un\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.error_codes == []
    assert ligne.state == EtatLigneImport.VALID.value
    assert ligne.normalized_data is not None
    assert ligne.normalized_data["F13"] == str(client)
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_client_global_non_active_localement_est_un_avertissement(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T2")
    acteur = _personne(cx, "a2")
    client = _client(cx, f"{MARQUEUR.lower()} client deux")
    #  AUCUNE activation locale : le client existe, globalement, seulement.
    contenu = (
        f"email,nom,prenom,client\n"
        f"valide2@{EMAIL_DOMAINE},EXEMPLE,Deux,{MARQUEUR.lower()} client deux\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.error_codes == [CODE_CLIENT_NON_ACTIVE_LOCALEMENT]
    assert ligne.state == EtatLigneImport.WARNING.value
    assert ligne.normalized_data is not None
    assert ligne.normalized_data["F13"] == str(client)
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_client_inconnu_devient_une_decision(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T3")
    acteur = _personne(cx, "a3")
    contenu = (
        f"email,nom,prenom,client\n"
        f"valide3@{EMAIL_DOMAINE},EXEMPLE,Trois,{MARQUEUR.lower()} client totalement inconnu\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.error_codes == [CODE_CLIENT_INCONNU]
    assert ligne.state == EtatLigneImport.NEEDS_DECISION.value
    #  L'e-mail, lui, est valide : `normalized_data` porte F01 sans F13 —
    #  jamais `None` en bloc, le dictionnaire ne vaut `None` que si RIEN
    #  n'a ete resolu du tout (voir `app.imports.analyse`).
    assert ligne.normalized_data == {"F01": f"valide3@{EMAIL_DOMAINE}"}
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_aucune_ressemblance_n_est_detectee_meme_pour_un_nom_tres_proche(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    """Temoin central (arbitrage de Jonathan) : `D-CLIENT-001` n'existe pas ici."""
    entite = _entite(cx, "T4")
    acteur = _personne(cx, "a4")
    _client(cx, f"{MARQUEUR.lower()} client fictif un")
    #  "1" au lieu de "un" : l'exemple meme cite par le LOT 0 comme cas de
    #  ressemblance. Sans detection automatique, c'est un client INCONNU.
    contenu = (
        f"email,nom,prenom,client\n"
        f"valide4@{EMAIL_DOMAINE},EXEMPLE,Quatre,{MARQUEUR.lower()} client fictif 1\n"
    )

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.error_codes == [CODE_CLIENT_INCONNU]
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_alias_local_prime_sur_alias_global_et_nom_canonique(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T5")
    acteur = _personne(cx, "a5")
    client_canonique = _client(cx, f"{MARQUEUR.lower()} alpha sa")
    client_global = _client(cx, f"{MARQUEUR.lower()} alpha global")
    client_local = _client(cx, f"{MARQUEUR.lower()} alpha local")
    nom_ambigu = f"{MARQUEUR.lower()} alpha"
    #  Le nom AMBIGU correspond a un alias GLOBAL et a un alias LOCAL a
    #  cette entite -- le local doit l'emporter.
    _alias(cx, nom=nom_ambigu, client=client_global, validateur=acteur, entite=None)
    _alias(cx, nom=nom_ambigu, client=client_local, validateur=acteur, entite=entite)
    _activer_localement(cx, entite=entite, client=client_local)
    contenu = f"email,nom,prenom,client\nvalide5@{EMAIL_DOMAINE},EXEMPLE,Cinq,{nom_ambigu}\n"

    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    assert ligne.normalized_data is not None
    assert ligne.normalized_data["F13"] == str(client_local)
    assert ligne.error_codes == []
    assert client_canonique  # cree pour le decor, jamais choisi
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  2. Le referentiel, ECART-060
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_le_referentiel_montre_aussi_un_client_pas_encore_active(
    cx: Connection,
) -> None:
    entite = _entite(cx, "T6")
    client_actif = _client(cx, f"{MARQUEUR.lower()} liste actif")
    client_latent = _client(cx, f"{MARQUEUR.lower()} liste latent")
    _activer_localement(cx, entite=entite, client=client_actif)

    catalogue = {c.identifiant: c for c in lister_les_clients(cx, entite=entite)}

    assert catalogue[client_actif].actif_localement is True
    assert catalogue[client_latent].actif_localement is False


# ---------------------------------------------------------------------------
#  3. Enregistrer une decision
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_creer_un_alias_resout_F13_et_cree_la_ligne_client_alias(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T7")
    acteur = _personne(cx, "a7")
    cible = _client(cx, f"{MARQUEUR.lower()} cible alias")
    contenu = (
        f"email,nom,prenom,client\nvalide7@{EMAIL_DOMAINE},EXEMPLE,Sept,"
        f"{MARQUEUR.lower()} nom libre\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)
    assert ligne.error_codes == [CODE_CLIENT_INCONNU]

    decision = enregistrer_une_decision(
        cx,
        entite=entite,
        lot=lot.identifiant,
        ligne=ligne.id,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        type_de_decision=TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value,
        personne_cible=None,
        client_cible=cible,
        motif="rapprochement manuel",
        instant=INSTANT,
    )

    assert decision.decision_type == TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value
    alias = cx.execute(
        text(
            "SELECT client_id, validated_by_person_id FROM client_alias "
            "WHERE alias_normalized = :nom AND entity_id = :entite"
        ),
        {"nom": f"{MARQUEUR.lower()} nom libre", "entite": entite},
    ).one()
    assert alias.client_id == cible
    assert alias.validated_by_person_id == acteur

    ligne_apres = _ligne(cx, lot.identifiant, 1)
    assert ligne_apres.normalized_data is not None
    assert ligne_apres.normalized_data["F13"] == str(cible)
    #  N'IMPORTE RIEN : l'etat de la ligne reste needs_decision.
    assert ligne_apres.state == EtatLigneImport.NEEDS_DECISION.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_selection_canonique_ne_cree_aucun_alias(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T8")
    acteur = _personne(cx, "a8")
    cible = _client(cx, f"{MARQUEUR.lower()} cible canonique")
    contenu = (
        f"email,nom,prenom,client\nvalide8@{EMAIL_DOMAINE},EXEMPLE,Huit,"
        f"{MARQUEUR.lower()} une fois\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    enregistrer_une_decision(
        cx,
        entite=entite,
        lot=lot.identifiant,
        ligne=ligne.id,
        acteur=acteur,
        roles=frozenset({RoleDeLaMatrice.ESM}),
        type_de_decision=TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value,
        personne_cible=None,
        client_cible=cible,
        motif=None,
        instant=INSTANT,
    )

    nombre_d_alias = cx.execute(
        text("SELECT count(*) FROM client_alias WHERE entity_id = :entite"), {"entite": entite}
    ).scalar_one()
    assert nombre_d_alias == 0
    ligne_apres = _ligne(cx, lot.identifiant, 1)
    assert ligne_apres.normalized_data is not None
    assert ligne_apres.normalized_data["F13"] == str(cible)
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  4. Les refus
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_type_de_decision_incoherent_est_refuse(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T9")
    acteur = _personne(cx, "a9")
    contenu = (
        f"email,nom,prenom,client\nvalide9@{EMAIL_DOMAINE},EXEMPLE,Neuf,"
        f"{MARQUEUR.lower()} inconnu\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite,
            lot=lot.identifiant,
            ligne=ligne.id,
            acteur=acteur,
            roles=frozenset({RoleDeLaMatrice.ESM}),
            #  PERSON_MERGE exige D-PERSONNE-001, absent ici.
            type_de_decision=TypeDeDecisionImport.PERSON_MERGE.value,
            personne_cible=acteur,
            client_cible=None,
            motif=None,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_TYPE_INCOHERENT
    assert excinfo.value.statut == 409
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_cible_manquante_est_refusee(cx: Connection, parametres_de_la_stack: Parametres) -> None:
    entite = _entite(cx, "T10")
    acteur = _personne(cx, "a10")
    contenu = (
        f"email,nom,prenom,client\nvalide10@{EMAIL_DOMAINE},EXEMPLE,Dix,"
        f"{MARQUEUR.lower()} inconnu\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite,
            lot=lot.identifiant,
            ligne=ligne.id,
            acteur=acteur,
            roles=frozenset({RoleDeLaMatrice.ESM}),
            type_de_decision=TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value,
            personne_cible=None,
            client_cible=None,
            motif=None,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_CIBLE_MANQUANTE
    assert excinfo.value.statut == 422
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_cible_inconnue_est_refusee(cx: Connection, parametres_de_la_stack: Parametres) -> None:
    entite = _entite(cx, "T11")
    acteur = _personne(cx, "a11")
    contenu = (
        f"email,nom,prenom,client\nvalide11@{EMAIL_DOMAINE},EXEMPLE,Onze,"
        f"{MARQUEUR.lower()} inconnu\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite,
            lot=lot.identifiant,
            ligne=ligne.id,
            acteur=acteur,
            roles=frozenset({RoleDeLaMatrice.ESM}),
            type_de_decision=TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value,
            personne_cible=None,
            client_cible=uuid.uuid4(),
            motif=None,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_CIBLE_INCONNUE
    assert excinfo.value.statut == 404
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_une_ligne_qui_n_attend_aucune_decision_est_refusee(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T12")
    acteur = _personne(cx, "a12")
    client = _client(cx, f"{MARQUEUR.lower()} douze")
    _activer_localement(cx, entite=entite, client=client)
    contenu = (
        f"email,nom,prenom,client\nvalide12@{EMAIL_DOMAINE},EXEMPLE,Douze,"
        f"{MARQUEUR.lower()} douze\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)
    assert ligne.state == EtatLigneImport.VALID.value

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite,
            lot=lot.identifiant,
            ligne=ligne.id,
            acteur=acteur,
            roles=frozenset({RoleDeLaMatrice.ESM}),
            type_de_decision=TypeDeDecisionImport.VOLUNTARY_REJECTION.value,
            personne_cible=None,
            client_cible=None,
            motif=None,
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_LIGNE_INTROUVABLE
    assert excinfo.value.statut == 404
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


# ---------------------------------------------------------------------------
#  5. La portee DSM
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_un_dsm_hors_de_son_perimetre_est_refuse(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T13")
    dsm = _personne(cx, "dsm13", email=f"dsm13@{EMAIL_DOMAINE}")
    acteur_du_depot = _personne(cx, "a13")
    #  Le F16 de la ligne designe un AUTRE DSM que celui qui tente de decider.
    contenu = (
        f"email,nom,prenom,client,email_dsm\n"
        f"valide13@{EMAIL_DOMAINE},EXEMPLE,Treize,{MARQUEUR.lower()} treize,"
        f"autre-dsm@{EMAIL_DOMAINE}\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur_du_depot, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    with pytest.raises(ErreurApplicative) as excinfo:
        enregistrer_une_decision(
            cx,
            entite=entite,
            lot=lot.identifiant,
            ligne=ligne.id,
            acteur=dsm,
            roles=frozenset({RoleDeLaMatrice.DSM}),
            type_de_decision=TypeDeDecisionImport.VOLUNTARY_REJECTION.value,
            personne_cible=None,
            client_cible=None,
            motif="hors perimetre",
            instant=INSTANT,
        )
    assert excinfo.value.code == CODE_PORTEE_DSM_REFUSEE
    assert excinfo.value.statut == 403
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)


@pytest.mark.integration
def test_un_dsm_dans_son_perimetre_est_accepte(
    cx: Connection, parametres_de_la_stack: Parametres
) -> None:
    entite = _entite(cx, "T14")
    email_dsm = f"dsm14@{EMAIL_DOMAINE}"
    dsm = _personne(cx, "dsm14", email=email_dsm)
    acteur_du_depot = _personne(cx, "a14")
    #  Le F16 de la ligne designe CE DSM precisement.
    contenu = (
        f"email,nom,prenom,client,email_dsm\n"
        f"valide14@{EMAIL_DOMAINE},EXEMPLE,Quatorze,{MARQUEUR.lower()} quatorze,{email_dsm}\n"
    )
    lot = _deposer_ou_sauter(
        cx, parametres_de_la_stack, entite=entite, acteur=acteur_du_depot, contenu=contenu
    )
    ligne = _ligne(cx, lot.identifiant, 1)

    decision = enregistrer_une_decision(
        cx,
        entite=entite,
        lot=lot.identifiant,
        ligne=ligne.id,
        acteur=dsm,
        roles=frozenset({RoleDeLaMatrice.DSM}),
        type_de_decision=TypeDeDecisionImport.VOLUNTARY_REJECTION.value,
        personne_cible=None,
        client_cible=None,
        motif="dans mon perimetre",
        instant=INSTANT,
    )

    assert decision.decision_type == TypeDeDecisionImport.VOLUNTARY_REJECTION.value
    _nettoyer_le_lot(parametres_de_la_stack, entite=entite, lot=lot.identifiant)
