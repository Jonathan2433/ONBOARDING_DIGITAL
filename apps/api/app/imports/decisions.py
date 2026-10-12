"""Enregistrer une décision humaine sur une ligne `needs_decision` — LOT 9, `T8`.

Story `MVP-L09-US005` — « Valider les rapprochements de clients ».

POURQUOI UNE ROUTE GÉNÉRIQUE SUR LES CINQ TYPES, ALORS QUE `T8` NE PORTE QUE
LES CLIENTS

  `import_decision.decision_type` ferme CINQ catégories depuis `T1`
  (`person_merge`, `profile_reactivation`, `client_alias_creation`,
  `canonical_client_selection`, `voluntary_rejection`) — le modèle §19.4 les
  nomme toutes les cinq, et `T7` produit déjà deux codes qui appellent les
  deux premières (`D-PERSONNE-001`/`002`) sans qu'aucun mécanisme n'existe
  pour les résoudre. Écrire une route qui ne couvrirait que les décisions
  « client » aurait dupliqué, pour un gain nul, exactement la même
  mécanique (verrou de la ligne, vérification du type contre les codes en
  cours, écriture de `import_decision`) une seconde fois quand `T9` ou un
  lot ultérieur en aurait besoin pour les personnes.

  **Seuls les DEUX types « client » sont exercés et testés par `T8`** —
  celui qui porte la story. Les trois autres sont structurellement
  acceptés (le type existe, la table l'accepte) mais non éprouvés ici :
  aucun test de `T8` ne les exerce, et ce n'est pas un oubli.

CE QUI RÉSOUT VRAIMENT UNE DÉCISION, ET CE QUI NE LE FAIT PAS

  Enregistrer une décision n'EST PAS importer la ligne : `import_row.state`
  reste `needs_decision` après cet appel. L'IMPORT RÉEL (`T9`, transactionnel)
  relira les décisions enregistrées et décidera, pour de vrai, si la ligne
  devient `imported`/`updated`/`rejected`. Ce module se contente de
  mémoriser le choix humain — exactement ce que le critère de `US005`
  demande (« chaque décision humaine est mémorisée dans le lot d'import »),
  rien de plus.

  **EXCEPTION, ET ELLE EST STRUCTURELLE** : `client_alias_creation` crée
  IMMÉDIATEMENT la ligne `client_alias` (`validated_by_person_id`/
  `validated_at` y sont `NOT NULL` depuis le LOT 2 — une ligne n'y vit QUE
  validée). Ce n'est pas une écriture métier sur le COLLABORATEUR importé :
  c'est la mémorisation de la décision elle-même, dans la table que le
  modèle §7.3 lui réserve. `normalized_data["F13"]` est mis à jour en même
  temps, pour que la réponse de prévisualisation reflète la décision prise
  — mais `import_row.state` et ses autres codes restent inchangés, un
  AUTRE code pouvant encore peser sur la même ligne (homonymie, par
  exemple).

QUI DÉCIDE, ET LA PORTÉE PARTICULIÈRE DU DSM

  Matrice §14 « Valider les rapprochements clients » : `DSM` Consultants,
  `ESM` Entité, `ADM-E` Entité, `SUPER` Global — `BOOST` et `OFFICE` À
  TIRET, contrairement à « Prévisualiser et corriger les correspondances »
  (ligne voisine, qui admet `BOOST`). La garde de route admet les QUATRE
  rôles ; **le SERVICE resserre pour le DSM seul** : sans `ESM`/`ADM-E`/
  `SUPER` en plus, un DSM ne décide que sur une ligne qui le nomme LUI-MÊME
  comme DSM (`F16`, normalisé, comparé à sa propre adresse) — « ses
  consultants », ici lus directement dans la ligne du fichier puisqu'aucun
  profil n'existe encore pour la relier autrement.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError

from app.clients import normaliser_nom_client
from app.imports.analyse import CODE_PERSONNE_PROFIL_ACTIF, CODE_PERSONNE_PROFIL_ARCHIVE
from app.imports.clients import CODE_CLIENT_INCONNU
from app.imports.correspondance import valeur_logique
from app.imports.modeles import EtatLigneImport, TypeDeDecisionImport
from app.people.modeles import normaliser_email
from app.permissions.services import RoleDeLaMatrice
from app.shared.errors import ErreurApplicative

#  §14 : DSM/ESM/ADM-E/SUPER. BOOST et OFFICE a tiret -- a la difference de
#  « Previsualiser et corriger les correspondances », ligne voisine.
ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  Roles dont la portee EST deja l'entite ou le monde -- un DSM qui les
#  porte AUSSI n'a pas besoin du filtre « ses consultants ».
_ROLES_A_PORTEE_LARGE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

CODE_LIGNE_INTROUVABLE: Final = "ligne_introuvable"
MESSAGE_LIGNE_INTROUVABLE: Final = "Cette ligne n'existe pas, ou n'attend aucune decision."

CODE_TYPE_INCOHERENT: Final = "type_de_decision_incoherent"
MESSAGE_TYPE_INCOHERENT: Final = (
    "Ce type de decision ne correspond a aucun probleme actuellement signale sur cette ligne."
)

CODE_CIBLE_MANQUANTE: Final = "cible_manquante"
MESSAGE_CIBLE_MANQUANTE: Final = "Ce type de decision exige une cible."

CODE_PORTEE_DSM_REFUSEE: Final = "acces_refuse"
MESSAGE_PORTEE_DSM_REFUSEE: Final = (
    "Cette ligne ne vous designe pas comme DSM -- hors de votre perimetre."
)

CODE_CIBLE_INCONNUE: Final = "cible_inconnue"
MESSAGE_CIBLE_INCONNUE: Final = "La personne ou le client cible n'existe pas."

#  Le type de decision EXIGE la presence d'au moins un de ces codes parmi
#  ceux DEJA signales sur la ligne -- `None` veut dire « aucune exigence »,
#  seul le cas du rejet volontaire, valide sur toute ligne `needs_decision`.
_CODES_REQUIS: Final[dict[str, frozenset[str] | None]] = {
    TypeDeDecisionImport.PERSON_MERGE.value: frozenset({CODE_PERSONNE_PROFIL_ACTIF}),
    TypeDeDecisionImport.PROFILE_REACTIVATION.value: frozenset({CODE_PERSONNE_PROFIL_ARCHIVE}),
    TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value: frozenset({CODE_CLIENT_INCONNU}),
    TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value: frozenset({CODE_CLIENT_INCONNU}),
    TypeDeDecisionImport.VOLUNTARY_REJECTION.value: None,
}

_TYPES_EXIGEANT_UN_CLIENT: Final = frozenset(
    {
        TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value,
        TypeDeDecisionImport.CANONICAL_CLIENT_SELECTION.value,
    }
)
_TYPES_EXIGEANT_UNE_PERSONNE: Final = frozenset(
    {
        TypeDeDecisionImport.PERSON_MERGE.value,
        TypeDeDecisionImport.PROFILE_REACTIVATION.value,
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class DecisionEnregistree:
    """Ce que l'enregistrement d'une decision a produit."""

    identifiant: uuid.UUID
    decision_type: str


_LIGNE_A_DECIDER: Final = text(
    """
    SELECT state, raw_data, error_codes
      FROM import_row
     WHERE id = :ligne AND import_batch_id = :lot AND entity_id = :entite
       FOR UPDATE
    """
)

_INSERER_LA_DECISION: Final = text(
    """
    INSERT INTO import_decision
      (entity_id, import_row_id, decision_type, target_person_id, target_client_id,
       reason, created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :ligne, :type_de_decision, :personne_cible, :client_cible,
       :motif, :acteur, :acteur, :instant, :instant)
    RETURNING id
    """
)

_CREER_L_ALIAS: Final = text(
    """
    INSERT INTO client_alias
      (entity_id, alias_normalized, client_id, validated_by_person_id, validated_at,
       created_by_person_id, updated_by_person_id, created_at, updated_at)
    VALUES
      (:entite, :alias, :client_cible, :acteur, :instant, :acteur, :acteur, :instant, :instant)
    """
)

_METTRE_A_JOUR_LE_CLIENT_RESOLU: Final = text(
    """
    UPDATE import_row
       SET normalized_data = jsonb_set(
               COALESCE(normalized_data, '{}'::jsonb), '{F13}',
               to_jsonb(CAST(:client_cible AS text))
           ),
           updated_at = :instant
     WHERE id = :ligne
    """
)


def _acteur_est_dsm_dans_son_perimetre(
    connexion: Connection, *, acteur: uuid.UUID, raw_data: dict[str, object]
) -> bool:
    """Le `F16` de la ligne designe-t-il CET acteur comme son DSM ?

    Lu DIRECTEMENT dans le fichier : aucun profil n'existe encore pour cette
    ligne, donc aucune relation `dsm_assignment` ne peut encore la porter.
    """
    email_dsm_de_la_ligne = valeur_logique(raw_data, "F16")
    if email_dsm_de_la_ligne is None:
        return False
    email_acteur = connexion.execute(
        text("SELECT email_normalized FROM person WHERE id = :acteur"), {"acteur": acteur}
    ).scalar_one_or_none()
    if email_acteur is None:
        return False
    return bool(normaliser_email(email_dsm_de_la_ligne) == email_acteur)


def enregistrer_une_decision(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    lot: uuid.UUID,
    ligne: uuid.UUID,
    acteur: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    type_de_decision: str,
    personne_cible: uuid.UUID | None,
    client_cible: uuid.UUID | None,
    motif: str | None,
    instant: dt.datetime,
) -> DecisionEnregistree:
    """Enregistrer une décision humaine — matrice §14, modèle §19.4.

    Ne touche JAMAIS `import_row.state` : voir l'en-tête du module. Seul
    `client_alias_creation` écrit en dehors de `import_decision`, et
    uniquement dans la table que le modèle lui réserve.
    """
    ligne_actuelle = connexion.execute(
        _LIGNE_A_DECIDER, {"ligne": ligne, "lot": lot, "entite": entite}
    ).one_or_none()
    if ligne_actuelle is None or ligne_actuelle.state != EtatLigneImport.NEEDS_DECISION.value:
        raise ErreurApplicative(
            code=CODE_LIGNE_INTROUVABLE,
            message=MESSAGE_LIGNE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )

    if not (roles & _ROLES_A_PORTEE_LARGE) and not _acteur_est_dsm_dans_son_perimetre(
        connexion, acteur=acteur, raw_data=ligne_actuelle.raw_data
    ):
        raise ErreurApplicative(
            code=CODE_PORTEE_DSM_REFUSEE,
            message=MESSAGE_PORTEE_DSM_REFUSEE,
            statut=status.HTTP_403_FORBIDDEN,
        )

    #  **DEFAUT TROUVE EN CONSTRUISANT `T9`, CORRIGE AVANT COMMIT.** Le refus
    #  ci-dessus admet un DSM dans SON perimetre pour LES CINQ types — correct
    #  pour `client_alias_creation`/`canonical_client_selection`
    #  (« Valider les rapprochements clients », matrice §14, DSM Consultants),
    #  mais `person_merge`/`profile_reactivation` relevent d'une AUTRE ligne de
    #  la matrice (« Reactiver un profil archive » : DSM a TIRET, ESM/ADM-E
    #  « Confirmation explicite », SUPER Global — exactement
    #  `app.permissions.perimetre.ROLES_DU_CYCLE_DE_VIE`). `codes-erreurs-
    #  import.md` §5 le confirme : `D-PERSONNE-001` et `002` ne nomment NI
    #  BOOST ni DSM parmi « qui decide ». Un DSM, meme dans son perimetre, ne
    #  peut donc PAS fusionner ni reactiver un profil — seul `T9` (qui AGIT
    #  sur ces deux types) exerce enfin cette branche, jamais testee par `T8`.
    if (
        type_de_decision
        in (
            TypeDeDecisionImport.PERSON_MERGE.value,
            TypeDeDecisionImport.PROFILE_REACTIVATION.value,
        )
        and not roles & _ROLES_A_PORTEE_LARGE
    ):
        raise ErreurApplicative(
            code=CODE_PORTEE_DSM_REFUSEE,
            message=MESSAGE_PORTEE_DSM_REFUSEE,
            statut=status.HTTP_403_FORBIDDEN,
        )

    codes_requis = _CODES_REQUIS[type_de_decision]
    codes_de_la_ligne = set(ligne_actuelle.error_codes or [])
    if codes_requis is not None and not (codes_requis & codes_de_la_ligne):
        raise ErreurApplicative(
            code=CODE_TYPE_INCOHERENT,
            message=MESSAGE_TYPE_INCOHERENT,
            statut=status.HTTP_409_CONFLICT,
        )

    if type_de_decision in _TYPES_EXIGEANT_UN_CLIENT and client_cible is None:
        raise ErreurApplicative(
            code=CODE_CIBLE_MANQUANTE,
            message=MESSAGE_CIBLE_MANQUANTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="target_client_id",
        )
    if type_de_decision in _TYPES_EXIGEANT_UNE_PERSONNE and personne_cible is None:
        raise ErreurApplicative(
            code=CODE_CIBLE_MANQUANTE,
            message=MESSAGE_CIBLE_MANQUANTE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="target_person_id",
        )

    try:
        identifiant = connexion.execute(
            _INSERER_LA_DECISION,
            {
                "entite": entite,
                "ligne": ligne,
                "type_de_decision": type_de_decision,
                "personne_cible": personne_cible,
                "client_cible": client_cible,
                "motif": motif,
                "acteur": acteur,
                "instant": instant,
            },
        ).scalar_one()

        if type_de_decision == TypeDeDecisionImport.CLIENT_ALIAS_CREATION.value:
            brut_client = valeur_logique(ligne_actuelle.raw_data, "F13")
            #  `client_cible` est garanti non None ici (verifie plus haut) ;
            #  `brut_client` l'est aussi : le code `D-CLIENT-002` exige par
            #  construction un `F13` present (voir `app.imports.analyse`).
            connexion.execute(
                _CREER_L_ALIAS,
                {
                    "entite": entite,
                    "alias": normaliser_nom_client(brut_client or ""),
                    "client_cible": client_cible,
                    "acteur": acteur,
                    "instant": instant,
                },
            )

        if type_de_decision in _TYPES_EXIGEANT_UN_CLIENT:
            connexion.execute(
                _METTRE_A_JOUR_LE_CLIENT_RESOLU,
                {"ligne": ligne, "client_cible": str(client_cible), "instant": instant},
            )
    except (IntegrityError, DataError) as erreur:
        raise ErreurApplicative(
            code=CODE_CIBLE_INCONNUE,
            message=MESSAGE_CIBLE_INCONNUE,
            statut=status.HTTP_404_NOT_FOUND,
        ) from erreur

    return DecisionEnregistree(identifiant=identifiant, decision_type=type_de_decision)
