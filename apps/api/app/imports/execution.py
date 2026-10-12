"""Lancer l'import — transaction reelle des lignes valides. LOT 9, `T9`.

Story `MVP-L09-US006` (1/2) — `Approved -> Importing -> Completed`, diagramme §24.4.

QUI LANCE, ET CE QUE CE MODULE NE FAIT JAMAIS TOUT SEUL

  Matrice §14 « Lancer l'import » : `ESM`/`ADM-E` Entite, `SUPER` Global,
  `DSM`/`BOOST`/`OFFICE` a tiret — MOT POUR MOT la meme grille que « Charger
  un CSV » (`T6`). `ROLES_DE_DEPOT_DE_L_IMPORT` est donc reutilisee telle
  quelle (§7.27), jamais une seconde declaration identique.

  « Reactiver un profil archive » (matrice §14) est une ligne SEPAREE et PLUS
  ETROITE : `DSM` tiret, `ESM`/`ADM-E` « Confirmation explicite », `SUPER`
  Global — exactement `app.permissions.perimetre.ROLES_DU_CYCLE_DE_VIE`. Un
  defaut a ete trouve et corrige dans `app.imports.decisions` (`T8`) a cette
  occasion : la route generique de decision y autorisait un DSM a enregistrer
  une `profile_reactivation`, ce que cette ligne de la matrice refuse — voir
  son en-tete.

L'ORDRE REEL DES ECRITURES, ET POURQUOI DEUX PASSES

  schema-csv-collaborateurs.md §5.5 : `F16` (le DSM) « doit designer une
  personne PRESENTE DANS LE FICHIER ou en base ». Une personne du fichier
  n'existe reellement qu'APRES que ce module l'a creee — et sa responsabilite
  DSM (`F17=DSM`, ou `F08=dg` par `RIGHTS-005`) n'existe reellement qu'apres
  que ce module l'a accordee. La PASSE 1 cree ou met a jour CHAQUE ligne
  eligible (personne, appartenance, metier, cercles, statut/client,
  responsabilites Framework, roles techniques, categorie `dg` -> DSM
  automatique, depart deja passe -> archivage immediat). La PASSE 2, apres
  que la passe 1 a TOUT ecrit, resout chaque `F16` par une requete ordinaire
  — plus besoin d'aucune logique « candidat du fichier », puisque la
  responsabilite DSM visee existe desormais REELLEMENT en base, quelle que
  soit la ligne qui l'a creee.

CHAQUE LIGNE EST ATOMIQUE, LE LOT NE L'EST PAS — MODELE §19.5, LITTERALEMENT

  « L'import des lignes valides […] garantit pour chaque ligne […] aucune
  mise a jour partielle […] une ligne rejetee n'empeche pas les lignes
  valides d'etre importees. » Chaque ligne s'ecrit donc dans son PROPRE
  `SAVEPOINT` (`connexion.begin_nested()`) : un refus de la base sur UNE
  ligne (contrainte d'exclusion, de verification…) annule SA SEULE ecriture,
  jamais celle des lignes deja traitees ni celles qui suivent. **PREMIER
  usage de `begin_nested()` dans ce projet** — aucune autre sous-etape
  n'avait encore eu besoin d'isoler un echec partiel a l'interieur d'une
  transaction HTTP unique.

LA VALIDATION ORGANISATIONNELLE EST REJOUEE, FRAICHE, ICI — JAMAIS EN CACHE

  `app.imports.organisation.valider_les_champs_organisationnels` est rappelee
  pour CHAQUE ligne encore candidate, au moment reel de l'import : un metier
  cree ou un cercle archive ENTRE la previsualisation et ce lancement change
  le verdict, et c'est voulu — voir l'en-tete de ce module. Si cette
  verification fraiche trouve un niveau `E`, la ligne est REJETEE maintenant,
  meme si `T7`/`T8` l'avaient jugee `valid`. Si elle trouve un niveau `D`
  encore non resolu, la ligne RESTE `needs_decision`.

  **CE QUE `T7`/`T8` AVAIENT DEJA JUGE N'EST PAS REJOUE** : l'appartenance a
  un e-mail existant (`D-PERSONNE-001`/`002`), l'homonymie intra-fichier
  (`D-PERSONNE-003`) et le rapprochement client (`W-CLIENT-001`/
  `D-CLIENT-002`) restent ceux de la previsualisation — seule une DECISION
  explicitement enregistree (`import_decision`) les fait progresser. Les
  rejouer ici aurait exige de dupliquer leurs requetes `=ANY(...)` sur TOUT
  le lot une seconde fois pour un gain etroit (la fenetre entre deux appels
  HTTP consecutifs du meme acteur), documente plutot que construit (§6.5).

CE QUE CE MODULE NE POSE JAMAIS

  - `F19` (autorisation photo) : AUCUNE ecriture. `photo_authorization.
    media_asset_id` est NOT NULL (modele §12.2, LOT 5) et aucun media n'existe
    a l'import — rien a quoi rattacher une autorisation. La valeur est
    VALIDEE (`app.imports.organisation`) et rien de plus ;
  - un changement de `professional_category` sur une personne EXISTANTE
    (fusion ou reactivation) : les SIX champs de `ChampOrganisationnel`
    (`T7` du LOT 5) ne l'incluent pas, et `attribuer_la_categorie_dg` est le
    SEUL service qui sache poser un `dg` sans violer `dg_implique_dsm_local` —
    il n'est appele qu'a la CREATION, jamais a la mise a jour. Une promotion
    `dg` d'un profil deja existant reste donc hors de ce module ;
  - l'etat `failed` du diagramme §24.4 : ce module tourne dans UNE SEULE
    transaction HTTP synchrone (`DEC-462`). Un echec non rattrape y fait
    echouer la transaction ENTIERE, ce qui laisse le lot `preview_ready` (rien
    n'est jamais persiste) plutot que de le figer dans un `importing` ou
    `failed` dont personne ne pourrait repartir avant le LOT 11.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.imports.analyse import (
    CODE_PERSONNE_PROFIL_ACTIF,
    CODE_PERSONNE_PROFIL_ARCHIVE,
    etat_depuis_les_problemes,
)
from app.imports.clients import CODE_CLIENT_INCONNU
from app.imports.correspondance import valeur_logique
from app.imports.modeles import EtatLigneImport, EtatLotImport, TypeDeDecisionImport
from app.imports.organisation import (
    NIVEAU_DU_CODE_ORGANISATION,
    TEXTES_ORGANISATION,
    ResolutionOrganisationnelle,
    ResponsabiliteDemandee,
    valider_les_champs_organisationnels,
)
from app.imports.structures import Probleme
from app.organization.services import attribuer_la_categorie_dg
from app.people.archivage import archiver_un_profil, restaurer_un_profil
from app.people.creation import (
    DemandeDAppartenance,
    DemandeDeCollaborateur,
    creer_un_collaborateur,
)
from app.people.ecriture import (
    modifier_les_donnees_organisationnelles,
    traduire_un_refus_de_la_base,
)
from app.people.modeles import SituationProfessionnelle
from app.permissions.perimetre import (
    TOUS_LES_CHAMPS,
    ChampOrganisationnel,
    PerimetreDEcriture,
    resoudre_le_cycle_de_vie,
)
from app.permissions.services import RoleDeLaMatrice
from app.shared.errors import ErreurApplicative

CODE_LOT_INTROUVABLE: Final = "lot_introuvable"
MESSAGE_LOT_INTROUVABLE: Final = "Ce lot d'import n'existe pas dans cette entite."

CODE_ETAT_NON_LANCABLE: Final = "etat_non_lancable"
MESSAGE_ETAT_NON_LANCABLE: Final = (
    "Ce lot n'est pas en previsualisation : il a deja ete lance, ou il est annule."
)

#  Generique, pour un refus de la base NON TRADUIT par `traduire_un_refus_de_la_base`
#  (ex. une contrainte propre a une table que ce module ecrit directement,
#  comme `framework_responsibility_assignment`).
CODE_LIGNE_REJETEE_PAR_LA_BASE: Final = "refus_de_la_base"
MESSAGE_LIGNE_REJETEE_PAR_LA_BASE: Final = (
    "Cette ligne a ete rejetee par une contrainte d'integrite au moment de l'import."
)


@dataclasses.dataclass(frozen=True, slots=True)
class RapportDeLancement:
    """Ce que `lancer_l_import` a produit — un COMPTE, jamais un cache du rapport de `T10`.

    `T10` relira `import_row.state` directement : ces compteurs ne sont que ce
    que CET APPEL a fait, pour le corps de reponse HTTP.
    """

    version: int
    etat: str
    lignes_importees: int
    lignes_mises_a_jour: int
    lignes_rejetees_a_l_import: int
    lignes_en_attente_de_decision: int


@dataclasses.dataclass(frozen=True, slots=True)
class _LigneAImporter:
    identifiant: uuid.UUID
    row_number: int
    raw_data: dict[str, object]
    state: str
    error_codes: list[str]


_LOT_SOUS_VERROU: Final = text(
    "SELECT state, version FROM import_batch WHERE id = :lot AND entity_id = :entite FOR UPDATE"
)

_LIGNES_DU_LOT_SOUS_VERROU: Final = text(
    """
    SELECT id, row_number, raw_data, state, error_codes
      FROM import_row
     WHERE import_batch_id = :lot
     ORDER BY row_number
       FOR UPDATE
    """
)

_DECISIONS_DU_LOT: Final = text(
    """
    SELECT d.import_row_id, d.decision_type, d.target_person_id
      FROM import_decision d
      JOIN import_row r ON r.id = d.import_row_id
     WHERE r.import_batch_id = :lot
    """
)

_FIXER_LA_LIGNE_IMPORTEE: Final = text(
    """
    UPDATE import_row
       SET state = :etat, target_person_id = :personne, target_membership_id = :appartenance,
           error_codes = CAST(:codes AS jsonb), updated_at = :instant
     WHERE id = :ligne
    """
)

_FIXER_LA_LIGNE_REJETEE_OU_EN_ATTENTE: Final = text(
    """
    UPDATE import_row
       SET state = :etat, error_codes = CAST(:codes AS jsonb), updated_at = :instant
     WHERE id = :ligne
    """
)

_INSERER_UN_PROBLEME: Final = text(
    """
    INSERT INTO import_row_issue
      (entity_id, import_row_id, code, field, message, level,
       normalized_value_safe, resolution)
    VALUES
      (:entite, :ligne, :code, :champ, :message, :niveau,
       :valeur_normalisee_sure, :resolution)
    """
)

_FIXER_LE_LOT: Final = text(
    """
    UPDATE import_batch
       SET state = :etat, approved_by_person_id = :acteur, updated_at = :instant,
           updated_by_person_id = :acteur, version = version + 1
     WHERE id = :lot AND entity_id = :entite
    RETURNING version
    """
)

_APPARTENANCE_ACTIVE: Final = text(
    "SELECT id, version FROM entity_membership "
    "WHERE person_id = :personne AND entity_id = :entite AND membership_state = 'active' "
    "ORDER BY created_at DESC LIMIT 1"
)

_APPARTENANCE_ARCHIVEE: Final = text(
    "SELECT id, version FROM entity_membership "
    "WHERE person_id = :personne AND entity_id = :entite AND membership_state = 'archived' "
    "ORDER BY created_at DESC LIMIT 1"
)

_PERSONNE_DE_L_APPARTENANCE: Final = text(
    "SELECT person_id FROM entity_membership WHERE id = :appartenance"
)

_CERCLES_SECONDAIRES_ACTIFS: Final = text(
    "SELECT id, circle_id FROM circle_membership "
    "WHERE entity_membership_id = :appartenance AND membership_type = 'secondary' "
    "AND ends_at IS NULL"
)

_FERMER_LE_CERCLE_SECONDAIRE: Final = text(
    "UPDATE circle_membership SET ends_at = :instant, updated_at = :instant, "
    "updated_by_person_id = :acteur, version = version + 1 WHERE id = :ligne"
)

_OUVRIR_LE_CERCLE_SECONDAIRE: Final = text(
    "INSERT INTO circle_membership "
    "(entity_membership_id, entity_id, circle_id, membership_type, starts_at, "
    " created_by_person_id) "
    "VALUES (:cible, :entite, :cercle, 'secondary', :instant, :acteur)"
)

_ECRIRE_LA_PRESENTATION: Final = text(
    "UPDATE entity_membership SET short_bio = COALESCE(:presentation, short_bio), "
    "fun_fact = COALESCE(:fun_fact, fun_fact), updated_at = :instant, "
    "updated_by_person_id = :acteur WHERE id = :cible"
)

_RESPONSABILITE_ACTIVE: Final = text(
    """
    SELECT id FROM framework_responsibility_assignment
     WHERE person_id = :personne AND entity_id = :entite AND responsibility_type = :type
       AND archived_at IS NULL AND period @> :instant
       AND circle_id IS NOT DISTINCT FROM :cercle AND office_id IS NOT DISTINCT FROM :bureau
     LIMIT 1
    """
)

_ACCORDER_UNE_RESPONSABILITE: Final = text(
    """
    INSERT INTO framework_responsibility_assignment
      (person_id, entity_id, responsibility_type, circle_id, office_id,
       assigned_by_person_id, starts_at, created_by_person_id)
    VALUES
      (:personne, :entite, :type, :cercle, :bureau, :acteur, :instant, :acteur)
    """
)

_ROLE_TECHNIQUE_ACTIF: Final = text(
    "SELECT id FROM technical_role_assignment WHERE person_id = :personne AND entity_id = :entite "
    "AND role_type = :role AND archived_at IS NULL AND period @> :instant LIMIT 1"
)

_ACCORDER_UN_ROLE_TECHNIQUE: Final = text(
    "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at, "
    "created_by_person_id) VALUES (:personne, :entite, :role, :instant, :acteur)"
)

_DSM_CIBLE_PAR_EMAIL: Final = text(
    """
    SELECT p.email_normalized AS email, p.id AS personne
      FROM person p
      JOIN framework_responsibility_assignment fra ON fra.person_id = p.id
     WHERE fra.entity_id = :entite AND fra.responsibility_type = 'DSM'
       AND fra.archived_at IS NULL AND fra.period @> :instant
       AND p.email_normalized = ANY(:emails)
    """
)

_DSM_ACTUEL: Final = text(
    "SELECT id, dsm_person_id FROM dsm_assignment WHERE consultant_membership_id = :appartenance "
    "AND ends_at IS NULL"
)

_FERMER_LE_DSM: Final = text(
    "UPDATE dsm_assignment SET ends_at = :instant, updated_at = :instant, "
    "updated_by_person_id = :acteur, version = version + 1 WHERE id = :ligne"
)

_OUVRIR_LE_DSM: Final = text(
    "INSERT INTO dsm_assignment (consultant_membership_id, entity_id, dsm_person_id, "
    "starts_at, created_by_person_id) VALUES (:cible, :entite, :dsm, :instant, :acteur)"
)


def _ecrire_les_problemes(
    connexion: Connection, *, entite: uuid.UUID, ligne: uuid.UUID, problemes: tuple[Probleme, ...]
) -> None:
    """Ecrit les problemes FRAIS d'`app.imports.organisation` — jamais ceux de T7/T8.

    Les codes produits par ce module sont TOUJOURS des codes d'organisation
    (voir l'en-tete de `app.imports.execution`) : `TEXTES_ORGANISATION` et
    `NIVEAU_DU_CODE_ORGANISATION` suffisent, jamais besoin de ceux de l'e-mail
    ou du client.
    """
    for probleme in problemes:
        message, resolution = TEXTES_ORGANISATION[probleme.code]
        connexion.execute(
            _INSERER_UN_PROBLEME,
            {
                "entite": entite,
                "ligne": ligne,
                "code": probleme.code,
                "champ": probleme.champ,
                "message": message,
                "niveau": NIVEAU_DU_CODE_ORGANISATION[probleme.code],
                "valeur_normalisee_sure": probleme.valeur_normalisee_sure,
                "resolution": resolution,
            },
        )


def _accorder_les_responsabilites(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    responsabilites: tuple[ResponsabiliteDemandee, ...],
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> None:
    for demandee in responsabilites:
        deja_active = connexion.execute(
            _RESPONSABILITE_ACTIVE,
            {
                "personne": personne,
                "entite": entite,
                "type": demandee.type_responsabilite,
                "instant": instant,
                "cercle": demandee.circle_id,
                "bureau": demandee.office_id,
            },
        ).first()
        if deja_active is not None:
            continue
        connexion.execute(
            _ACCORDER_UNE_RESPONSABILITE,
            {
                "personne": personne,
                "entite": entite,
                "type": demandee.type_responsabilite,
                "cercle": demandee.circle_id,
                "bureau": demandee.office_id,
                "acteur": acteur,
                "instant": instant,
            },
        )


def _accorder_les_roles_techniques(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    personne: uuid.UUID,
    roles_techniques: tuple[str, ...],
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> None:
    for role in roles_techniques:
        deja_actif = connexion.execute(
            _ROLE_TECHNIQUE_ACTIF,
            {"personne": personne, "entite": entite, "role": role, "instant": instant},
        ).first()
        if deja_actif is None:
            connexion.execute(
                _ACCORDER_UN_ROLE_TECHNIQUE,
                {
                    "personne": personne,
                    "entite": entite,
                    "role": role,
                    "acteur": acteur,
                    "instant": instant,
                },
            )


def _rafraichir_les_cercles_secondaires(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    cercles_vises: tuple[uuid.UUID, ...],
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> None:
    """Ferme les secondaires qui ne sont plus vises, ouvre les nouveaux.

    Aucune route existante ne gere les cercles SECONDAIRES (`T7` du LOT 5 ne
    porte que le principal) : cette logique est donc PROPRE a l'import, selon
    la MEME discipline « clore puis ouvrir » que `app.people.ecriture`.
    """
    actifs = {
        row.circle_id: row.id
        for row in connexion.execute(_CERCLES_SECONDAIRES_ACTIFS, {"appartenance": appartenance})
    }
    for cercle_id, ligne_id in actifs.items():
        if cercle_id not in cercles_vises:
            connexion.execute(
                _FERMER_LE_CERCLE_SECONDAIRE,
                {"ligne": ligne_id, "instant": instant, "acteur": acteur},
            )
    for cercle_id in cercles_vises:
        if cercle_id not in actifs:
            connexion.execute(
                _OUVRIR_LE_CERCLE_SECONDAIRE,
                {
                    "cible": appartenance,
                    "entite": entite,
                    "cercle": cercle_id,
                    "instant": instant,
                    "acteur": acteur,
                },
            )


def _archiver_si_depart_passe(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    departure_date: dt.date | None,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> None:
    """`W-DEPART-001` : « le profil est importe PUIS archive, sans acces »."""
    if departure_date is None or departure_date > instant.date():
        return
    perimetre = resoudre_le_cycle_de_vie(connexion, entite=entite, cible=appartenance, roles=roles)
    version = connexion.execute(
        text("SELECT version FROM entity_membership WHERE id = :cible"), {"cible": appartenance}
    ).scalar_one()
    archiver_un_profil(
        connexion,
        entite=entite,
        cible=appartenance,
        acteur=acteur,
        version_attendue=int(version),
        perimetre=perimetre,
        instant=instant,
        date_de_depart=departure_date,
    )


def _creer(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    raw_data: dict[str, object],
    resolution: ResolutionOrganisationnelle,
    client_id: uuid.UUID | None,
    instant: dt.datetime,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Chemin CREATION — `app.people.creation`, `T2`. Rend `(personne, appartenance)`."""
    assert resolution.arrival_date is not None  # noqa: S101 — garanti par l'eligibilite
    assert resolution.situation is not None  # noqa: S101
    assert resolution.entite_cible is not None  # noqa: S101
    demande = DemandeDeCollaborateur(
        email=valeur_logique(raw_data, "F01") or "",
        first_name=resolution.prenom or "",
        last_name=resolution.nom or "",
        preferred_name=resolution.nom_usage,
        appartenance=DemandeDAppartenance(
            arrival_date=resolution.arrival_date,
            job_catalog_id=resolution.job_catalog_id,
            status=SituationProfessionnelle(resolution.situation),
            client_id=client_id,
            dsm_person_id=None,
            circle_id=resolution.cercle_principal_id,
        ),
    )
    cree = creer_un_collaborateur(
        connexion, entite=resolution.entite_cible, acteur=acteur, demande=demande, instant=instant
    )
    personne = uuid.UUID(
        str(
            connexion.execute(
                _PERSONNE_DE_L_APPARTENANCE, {"appartenance": cree.appartenance}
            ).scalar_one()
        )
    )
    if resolution.categorie is not None and resolution.categorie == "dg":
        attribuer_la_categorie_dg(
            connexion,
            entite=entite,
            appartenance=cree.appartenance,
            attribue_par=acteur,
            debut=instant,
        )
    connexion.execute(
        _ECRIRE_LA_PRESENTATION,
        {
            "presentation": resolution.presentation_courte,
            "fun_fact": resolution.fun_fact,
            "instant": instant,
            "acteur": acteur,
            "cible": cree.appartenance,
        },
    )
    _rafraichir_les_cercles_secondaires(
        connexion,
        entite=entite,
        appartenance=cree.appartenance,
        cercles_vises=resolution.cercles_secondaires_ids,
        acteur=acteur,
        instant=instant,
    )
    _accorder_les_responsabilites(
        connexion,
        entite=entite,
        personne=personne,
        responsabilites=resolution.responsabilites,
        acteur=acteur,
        instant=instant,
    )
    _accorder_les_roles_techniques(
        connexion,
        entite=entite,
        personne=personne,
        roles_techniques=resolution.roles_techniques,
        acteur=acteur,
        instant=instant,
    )
    _archiver_si_depart_passe(
        connexion,
        entite=entite,
        appartenance=cree.appartenance,
        roles=roles,
        departure_date=resolution.departure_date,
        acteur=acteur,
        instant=instant,
    )
    return personne, cree.appartenance


def _mettre_a_jour(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    personne: uuid.UUID,
    reactiver: bool,
    resolution: ResolutionOrganisationnelle,
    client_id: uuid.UUID | None,
    instant: dt.datetime,
) -> uuid.UUID:
    """Chemin MISE A JOUR (`person_merge`) ou REACTIVATION (`profile_reactivation`).

    Rend l'identifiant de l'appartenance ecrite.
    """
    if reactiver:
        ligne_appartenance = connexion.execute(
            _APPARTENANCE_ARCHIVEE, {"personne": personne, "entite": entite}
        ).one()
        appartenance = uuid.UUID(str(ligne_appartenance.id))
        version = int(ligne_appartenance.version)
        perimetre_cycle = resoudre_le_cycle_de_vie(
            connexion, entite=entite, cible=appartenance, roles=roles
        )
        restauration = restaurer_un_profil(
            connexion,
            entite=entite,
            cible=appartenance,
            acteur=acteur,
            version_attendue=version,
            perimetre=perimetre_cycle,
            instant=instant,
        )
        version = restauration.version
    else:
        ligne_appartenance = connexion.execute(
            _APPARTENANCE_ACTIVE, {"personne": personne, "entite": entite}
        ).one()
        appartenance = uuid.UUID(str(ligne_appartenance.id))
        version = int(ligne_appartenance.version)

    demande: dict[ChampOrganisationnel, object] = {}
    if resolution.job_catalog_id is not None:
        demande[ChampOrganisationnel.METIER] = resolution.job_catalog_id
    if resolution.situation is not None:
        demande[ChampOrganisationnel.STATUT] = resolution.situation
        demande[ChampOrganisationnel.CLIENT] = client_id
    if resolution.cercle_principal_id is not None:
        demande[ChampOrganisationnel.CERCLE_PRINCIPAL] = resolution.cercle_principal_id

    if demande:
        modifier_les_donnees_organisationnelles(
            connexion,
            entite=entite,
            cible=appartenance,
            acteur=acteur,
            version_attendue=version,
            demande=demande,
            perimetre=PerimetreDEcriture(champs=TOUS_LES_CHAMPS),
            instant=instant,
        )

    connexion.execute(
        _ECRIRE_LA_PRESENTATION,
        {
            "presentation": resolution.presentation_courte,
            "fun_fact": resolution.fun_fact,
            "instant": instant,
            "acteur": acteur,
            "cible": appartenance,
        },
    )
    _rafraichir_les_cercles_secondaires(
        connexion,
        entite=entite,
        appartenance=appartenance,
        cercles_vises=resolution.cercles_secondaires_ids,
        acteur=acteur,
        instant=instant,
    )
    _accorder_les_responsabilites(
        connexion,
        entite=entite,
        personne=personne,
        responsabilites=resolution.responsabilites,
        acteur=acteur,
        instant=instant,
    )
    _accorder_les_roles_techniques(
        connexion,
        entite=entite,
        personne=personne,
        roles_techniques=resolution.roles_techniques,
        acteur=acteur,
        instant=instant,
    )
    _archiver_si_depart_passe(
        connexion,
        entite=entite,
        appartenance=appartenance,
        roles=roles,
        departure_date=resolution.departure_date,
        acteur=acteur,
        instant=instant,
    )
    return appartenance


def lancer_l_import(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lot: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> RapportDeLancement:
    """Transitionner `preview_ready -> importing -> completed` et ecrire les lignes.

    Matrice §14 : la garde de ROUTE verifie deja `ROLES_DE_DEPOT_DE_L_IMPORT`
    (reutilisee, §7.27) — ce service re-verifie l'etat du lot, pas le role.
    """
    ligne_lot = connexion.execute(_LOT_SOUS_VERROU, {"lot": lot, "entite": entite}).one_or_none()
    if ligne_lot is None:
        raise ErreurApplicative(
            code=CODE_LOT_INTROUVABLE,
            message=MESSAGE_LOT_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    if ligne_lot.state != EtatLotImport.PREVIEW_READY.value:
        raise ErreurApplicative(
            code=CODE_ETAT_NON_LANCABLE,
            message=MESSAGE_ETAT_NON_LANCABLE,
            statut=status.HTTP_409_CONFLICT,
        )

    lignes = [
        _LigneAImporter(
            identifiant=row.id,
            row_number=row.row_number,
            raw_data=row.raw_data,
            state=row.state,
            error_codes=list(row.error_codes or []),
        )
        for row in connexion.execute(_LIGNES_DU_LOT_SOUS_VERROU, {"lot": lot})
    ]

    decisions: dict[uuid.UUID, dict[str, uuid.UUID | None]] = {}
    for d in connexion.execute(_DECISIONS_DU_LOT, {"lot": lot}):
        decisions.setdefault(d.import_row_id, {})[d.decision_type] = d.target_person_id

    resolutions = valider_les_champs_organisationnels(
        connexion,
        entite=entite,
        lignes=[(ligne.identifiant, ligne.raw_data) for ligne in lignes],
        instant=instant,
    )

    importees = mises_a_jour = rejetees = en_attente = 0

    for ligne in lignes:
        if ligne.state == EtatLigneImport.REJECTED.value:
            continue

        decisions_de_la_ligne = decisions.get(ligne.identifiant, {})
        if TypeDeDecisionImport.VOLUNTARY_REJECTION.value in decisions_de_la_ligne:
            connexion.execute(
                _FIXER_LA_LIGNE_REJETEE_OU_EN_ATTENTE,
                {
                    "etat": EtatLigneImport.REJECTED.value,
                    "codes": json.dumps(ligne.error_codes),
                    "instant": instant,
                    "ligne": ligne.identifiant,
                },
            )
            rejetees += 1
            continue

        resolution = resolutions[ligne.identifiant]
        niveau_frais = etat_depuis_les_problemes(list(resolution.problemes))

        resolu_par_decision = True
        if ligne.state == EtatLigneImport.NEEDS_DECISION.value:
            resolu_par_decision = _decisions_couvrent_les_codes(
                ligne.error_codes, decisions_de_la_ligne
            )

        if niveau_frais == EtatLigneImport.REJECTED.value:
            _ecrire_les_problemes(
                connexion, entite=entite, ligne=ligne.identifiant, problemes=resolution.problemes
            )
            connexion.execute(
                _FIXER_LA_LIGNE_REJETEE_OU_EN_ATTENTE,
                {
                    "etat": EtatLigneImport.REJECTED.value,
                    "codes": json.dumps(
                        sorted(set(ligne.error_codes) | {p.code for p in resolution.problemes})
                    ),
                    "instant": instant,
                    "ligne": ligne.identifiant,
                },
            )
            rejetees += 1
            continue

        if niveau_frais == EtatLigneImport.NEEDS_DECISION.value or not resolu_par_decision:
            if resolution.problemes:
                _ecrire_les_problemes(
                    connexion,
                    entite=entite,
                    ligne=ligne.identifiant,
                    problemes=resolution.problemes,
                )
            connexion.execute(
                _FIXER_LA_LIGNE_REJETEE_OU_EN_ATTENTE,
                {
                    "etat": EtatLigneImport.NEEDS_DECISION.value,
                    "codes": json.dumps(
                        sorted(set(ligne.error_codes) | {p.code for p in resolution.problemes})
                    ),
                    "instant": instant,
                    "ligne": ligne.identifiant,
                },
            )
            en_attente += 1
            continue

        #  --- Eligible : CREATION, MISE A JOUR, ou REACTIVATION ---
        #  `niveau_frais` n'est ici ni `rejected` ni `needs_decision` : les
        #  seuls problemes qui subsistent sont de niveau `W` (avertissement).
        #  codes-erreurs-import.md §4 : « une ligne en avertissement EST
        #  importable […] L'avertissement est CONSERVE au rapport ». Ecrits
        #  AVANT l'ecriture metier, jamais apres un refus de savepoint —
        #  perdre les avertissements serait aussi faux que perdre les rejets.
        if resolution.problemes:
            _ecrire_les_problemes(
                connexion, entite=entite, ligne=ligne.identifiant, problemes=resolution.problemes
            )
        codes_finaux = sorted(set(ligne.error_codes) | {p.code for p in resolution.problemes})

        client_id = _client_resolu(decisions_de_la_ligne, ligne.identifiant)
        reactiver = TypeDeDecisionImport.PROFILE_REACTIVATION.value in decisions_de_la_ligne
        fusionner = TypeDeDecisionImport.PERSON_MERGE.value in decisions_de_la_ligne
        personne_cible = (
            decisions_de_la_ligne.get(TypeDeDecisionImport.PROFILE_REACTIVATION.value)
            if reactiver
            else decisions_de_la_ligne.get(TypeDeDecisionImport.PERSON_MERGE.value)
            if fusionner
            else None
        )

        try:
            with connexion.begin_nested():
                if personne_cible is not None:
                    appartenance = _mettre_a_jour(
                        connexion,
                        entite=entite,
                        acteur=acteur,
                        roles=roles,
                        personne=personne_cible,
                        reactiver=reactiver,
                        resolution=resolution,
                        client_id=client_id,
                        instant=instant,
                    )
                    personne = personne_cible
                else:
                    personne, appartenance = _creer(
                        connexion,
                        entite=entite,
                        acteur=acteur,
                        roles=roles,
                        raw_data=ligne.raw_data,
                        resolution=resolution,
                        client_id=client_id,
                        instant=instant,
                    )
        except (IntegrityError, DataError) as erreur:
            #  `traduire_un_refus_de_la_base` RE-LEVE l'erreur TELLE QUELLE
            #  (jamais un message invente) pour les causes qu'elle ne reconnait
            #  pas (ex. une `ForeignKeyViolation`, qu'aucune des quatre ecritures
            #  de `T7` du LOT 5 n'avait encore rencontree). Un refus generique,
            #  nomme comme tel, couvre ce residu plutot que de laisser
            #  remonter une exception non geree.
            try:
                refus = traduire_un_refus_de_la_base(erreur)
                code_refus, message_refus = refus.code, refus.message
            except (IntegrityError, DataError):
                code_refus, message_refus = (
                    CODE_LIGNE_REJETEE_PAR_LA_BASE,
                    MESSAGE_LIGNE_REJETEE_PAR_LA_BASE,
                )
            connexion.execute(
                _INSERER_UN_PROBLEME,
                {
                    "entite": entite,
                    "ligne": ligne.identifiant,
                    "code": code_refus,
                    "champ": None,
                    "message": message_refus,
                    "niveau": "E",
                    "valeur_normalisee_sure": None,
                    "resolution": None,
                },
            )
            connexion.execute(
                _FIXER_LA_LIGNE_REJETEE_OU_EN_ATTENTE,
                {
                    "etat": EtatLigneImport.REJECTED.value,
                    "codes": json.dumps([*ligne.error_codes, code_refus]),
                    "instant": instant,
                    "ligne": ligne.identifiant,
                },
            )
            rejetees += 1
            continue

        etat_final = (
            EtatLigneImport.UPDATED.value
            if personne_cible is not None
            else EtatLigneImport.IMPORTED.value
        )
        connexion.execute(
            _FIXER_LA_LIGNE_IMPORTEE,
            {
                "etat": etat_final,
                "personne": personne,
                "appartenance": appartenance,
                "codes": json.dumps(codes_finaux),
                "instant": instant,
                "ligne": ligne.identifiant,
            },
        )
        if etat_final == EtatLigneImport.IMPORTED.value:
            importees += 1
        else:
            mises_a_jour += 1

    #  --- Passe 2 : le DSM, maintenant que TOUTES les responsabilites de ce
    #      lot existent reellement en base, qu'elles viennent de ce lot ou
    #      d'avant lui. ---
    _resoudre_les_dsm(
        connexion,
        entite=entite,
        lignes=lignes,
        resolutions=resolutions,
        acteur=acteur,
        instant=instant,
    )

    version = connexion.execute(
        _FIXER_LE_LOT,
        {
            "etat": EtatLotImport.COMPLETED.value,
            "acteur": acteur,
            "instant": instant,
            "lot": lot,
            "entite": entite,
        },
    ).scalar_one()

    return RapportDeLancement(
        version=int(version),
        etat=EtatLotImport.COMPLETED.value,
        lignes_importees=importees,
        lignes_mises_a_jour=mises_a_jour,
        lignes_rejetees_a_l_import=rejetees,
        lignes_en_attente_de_decision=en_attente,
    )


def _client_resolu(
    decisions_de_la_ligne: dict[str, uuid.UUID | None], ligne: uuid.UUID
) -> uuid.UUID | None:
    """Le `F13` resolu — par `app.imports.clients` (preview) ou une decision cliente.

    Lu depuis `import_row.normalized_data['F13']`, deja ecrit par `T7`/`T8` —
    voir l'appelant, qui le fournit directement.
    """
    for type_de_decision in (
        TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value,
        TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value,
    ):
        cible = decisions_de_la_ligne.get(type_de_decision)
        if cible is not None:
            return cible
    return None


def _decisions_couvrent_les_codes(
    error_codes: list[str], decisions_de_la_ligne: dict[str, uuid.UUID | None]
) -> bool:
    """Chaque code `D-*` encore porte par la ligne a-t-il une decision qui le resout ?

    `D-PERSONNE-003` (homonymie) n'a AUCUN type resolvant — voir l'en-tete
    d'`app.imports.decisions` : seul `voluntary_rejection` (deja traite plus
    haut) peut faire progresser une telle ligne.
    """
    for code in error_codes:
        if code == CODE_PERSONNE_PROFIL_ACTIF:
            if TypeDeDecisionImport.PERSON_MERGE.value not in decisions_de_la_ligne:
                return False
        elif code == CODE_PERSONNE_PROFIL_ARCHIVE:
            if TypeDeDecisionImport.PROFILE_REACTIVATION.value not in decisions_de_la_ligne:
                return False
        elif code == CODE_CLIENT_INCONNU and not (
            {
                TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value,
                TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value,
            }
            & decisions_de_la_ligne.keys()
        ):
            return False
    return True


def _resoudre_les_dsm(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lignes: list[_LigneAImporter],
    resolutions: dict[uuid.UUID, ResolutionOrganisationnelle],
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> None:
    emails_cibles_vus: set[str] = set()
    for ligne in lignes:
        email_cible_brut = resolutions[ligne.identifiant].dsm_email_normalise
        if email_cible_brut is not None:
            emails_cibles_vus.add(email_cible_brut)
    emails_cibles = sorted(emails_cibles_vus)
    if not emails_cibles:
        return
    dsm_par_email = {
        row.email: row.personne
        for row in connexion.execute(
            _DSM_CIBLE_PAR_EMAIL, {"entite": entite, "instant": instant, "emails": emails_cibles}
        )
    }
    for ligne in lignes:
        email_cible = resolutions[ligne.identifiant].dsm_email_normalise
        if email_cible is None:
            continue
        dsm_person_id = dsm_par_email.get(email_cible)
        if dsm_person_id is None:
            continue
        appartenance = connexion.execute(
            text("SELECT target_membership_id FROM import_row WHERE id = :ligne"),
            {"ligne": ligne.identifiant},
        ).scalar_one_or_none()
        if appartenance is None:
            continue
        actuel = connexion.execute(_DSM_ACTUEL, {"appartenance": appartenance}).one_or_none()
        if actuel is not None and actuel.dsm_person_id == dsm_person_id:
            continue
        if actuel is not None:
            connexion.execute(
                _FERMER_LE_DSM, {"ligne": actuel.id, "instant": instant, "acteur": acteur}
            )
        connexion.execute(
            _OUVRIR_LE_DSM,
            {
                "cible": appartenance,
                "entite": entite,
                "dsm": dsm_person_id,
                "instant": instant,
                "acteur": acteur,
            },
        )
