"""Creer une nouvelle entite depuis des modeles generiques — LOT 9, `T12`.

Cahier §4.1 (« la possibilite pour un super-administrateur de creer une
nouvelle entite »), §21 (« Seul le role `SUPER` peut : creer une entite […]
nommer le premier administrateur de l'entite »), backlog `MVP-L09-US007`.

CE QUE « DEPUIS DES MODELES GENERIQUES » VEUT DIRE ICI, ET CE QU'IL NE VEUT
PAS DIRE — ARBITRAGE EXPLICITE DE JONATHAN, POSE AVANT TOUT CODE

  Le critere d'acceptation du backlog dit : « aucune donnee Bordeaux n'est
  copiee ; roles, contenus et onboarding generiques sont initialises puis
  configurables ». Ni le cahier ni la matrice ne precisent de CONTENU
  generique a poser (aucune page, aucun modele d'onboarding « par defaut »
  n'est decrit nulle part dans le corpus) — l'inventer serait exactement ce
  que le §6.5 interdit.

  Pose a Jonathan via `AskUserQuestion` (reformule sans jargon) : **l'entite
  nait VIERGE**, rien n'est copie ni seme automatiquement :

    - `role` : aucune responsabilite Framework (DSM/ESM/BOOST/OFFICE) n'existe
      encore dans la nouvelle entite — exactement l'etat d'une entite
      quelconque avant qu'un humain n'y affecte quiconque. « Initialises »
      decrit cet etat VIDE, pas une action de ce module ;
    - `contenus` : `content_page`/`content_block` sont des RESSOURCES LOCALES
      (LOT 6, `T1`) — une entite neuve n'en a AUCUNE, exactement comme
      aujourd'hui pour toute entite qui n'a pas encore ete editee. Les ecrans
      du LOT 6/8 rendent deja ce cas (`presentation` vaut `null`, LOT 8 `T8`) ;
    - `onboarding` : le modele d'onboarding « generique eXalt » du cahier §9.1
      EXISTE DEJA structurellement — `onboarding_template.entity_id` est
      NULLABLE pour la portee `GLOBAL` (LOT 7, `T5`), et la resolution
      `DSM > CIRCLE > ENTITY > GLOBAL` (LOT 7, `T7`) retombe DEJA sur un
      modele `GLOBAL` des qu'aucun modele `ENTITY` n'existe pour la nouvelle
      entite. Rien de nouveau a construire ici : la portee `GLOBAL` EST le
      mecanisme « generique », pose trois sous-etapes avant celle-ci.

  **« Aucune donnee Bordeaux n'est copiee » est donc vrai PAR CONSTRUCTION,
  pas par un filtre que ce module appliquerait** : il n'existe tout
  simplement AUCUN mecanisme de copie entre entites dans ce depot, et en
  ajouter un pour l'exclure ensuite aurait ete une invention dans les deux
  sens.

LE PREMIER ADMINISTRATEUR, LUI, EST POSE DANS LA MEME TRANSACTION —
SECOND ARBITRAGE DE JONATHAN

  Une entite qui ne porterait AUCUN role local resterait injoignable tant
  qu'un geste manuel en base ne nommerait pas un administrateur — ce que le
  cahier §21 liste pourtant comme un gestes DISTINCT du super-administrateur
  (« nommer le premier administrateur de l'entite »). Arbitrage : ce geste
  est inclus dans LE MEME appel que la creation, pour qu'une entite creee
  soit immediatement administrable localement, sans second geste manuel.

  `technical_role_assignment.person_id` ne reference que `person` (§8.6) —
  PAS `entity_membership` : la personne designee n'a pas besoin d'avoir deja
  une appartenance dans la nouvelle entite, ce qui est le cas general, une
  entite neuve n'ayant par definition aucun collaborateur.

AUCUN ETAT `draft` INTERMEDIAIRE

  Le modele distingue `draft` et `active` (§5.1), et un declencheur
  (migration `0003`) verrouille `code` des que `activated_at` est pose. Le
  decoupage de cette sous-etape ne nomme AUCUN geste « activer une entite »
  distinct de la creation — le cahier §21 les liste cote a cote mais ne les
  ordonne pas. Simplification retenue, documentee comme telle : l'entite est
  creee DIRECTEMENT `active`, `activated_at = instant` — une entite nouvelle
  doit pouvoir etre configuree et rejointe sans second geste. Si un besoin
  reel de brouillon pre-publication apparait plus tard, ce sera une decision
  a reposer, pas une extension silencieuse d'ici.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import Final

from psycopg import errors as erreurs_psycopg
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.entities.modeles import StatutEntite
from app.organization.modeles import TypeRoleTechnique
from app.shared.errors import ErreurApplicative

CODE_CODE_DEJA_UTILISE: Final = "code_deja_utilise"
MESSAGE_CODE_DEJA_UTILISE: Final = "Ce code d'entite est deja utilise par une autre entite."

CODE_PERSONNE_INTROUVABLE: Final = "personne_introuvable"
MESSAGE_PERSONNE_INTROUVABLE: Final = (
    "La personne designee comme premier administrateur n'existe pas."
)

_PERSONNE_EXISTE: Final = text("SELECT 1 FROM person WHERE id = :personne")

_INSERER_L_ENTITE: Final = text(
    "INSERT INTO entity (code, display_name, city, country_code, status, timezone, "
    "activated_at, created_by_person_id) "
    "VALUES (:code, :nom, :ville, :pays, :statut, :fuseau, :instant, :acteur) "
    "RETURNING id, version"
)

#  **MEME INSTRUCTION QUE `app.imports.execution` POUR ACCORDER UN ROLE
#  TECHNIQUE** (`RIGHTS-005`, `T9`) — une copie propre, et non un import
#  croise d'une fonction privee d'un module sans rapport (§7.27).
_ACCORDER_L_ADMINISTRATION_DE_L_ENTITE: Final = text(
    "INSERT INTO technical_role_assignment (person_id, entity_id, role_type, starts_at, "
    "created_by_person_id) VALUES (:personne, :entite, :role, :instant, :acteur)"
)


@dataclasses.dataclass(frozen=True, slots=True)
class DemandeDeCreationDEntite:
    """Les champs du §5.1 necessaires a la creation, plus le premier administrateur."""

    code: str
    display_name: str
    city: str
    country_code: str
    timezone: str
    premier_administrateur: uuid.UUID


@dataclasses.dataclass(frozen=True, slots=True)
class EntiteCreee:
    """Ce que la creation a produit."""

    id: uuid.UUID
    code: str
    version: int


def creer_une_entite(
    connexion: Connection,
    *,
    demande: DemandeDeCreationDEntite,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> EntiteCreee:
    """Creer l'entite et nommer son premier administrateur — UNE transaction.

    Leve `ErreurApplicative` : `422` personne introuvable, `409` code deja
    utilise. Voir l'en-tete du module pour ce qui n'est PAS fait ici (aucun
    contenu, role Framework ni modele d'onboarding n'est seme).
    """
    #  **LA PERSONNE D'ABORD** : `technical_role_assignment.person_id` est une
    #  cle etrangere vers `person`, et un refus de la base sur ELLE SEULE
    #  rendrait un message qui ne distingue pas « personne introuvable » de
    #  « code deja utilise » si les deux arrivaient dans la meme transaction.
    #  Verifier en lecture avant d'ecrire, meme discipline que `T3`.
    if (
        connexion.execute(_PERSONNE_EXISTE, {"personne": demande.premier_administrateur}).first()
        is None
    ):
        raise ErreurApplicative(
            code=CODE_PERSONNE_INTROUVABLE,
            message=MESSAGE_PERSONNE_INTROUVABLE,
            statut=422,
        )

    try:
        ligne = connexion.execute(
            _INSERER_L_ENTITE,
            {
                "code": demande.code,
                "nom": demande.display_name,
                "ville": demande.city,
                "pays": demande.country_code,
                "statut": StatutEntite.ACTIVE.value,
                "fuseau": demande.timezone,
                "instant": instant,
                "acteur": acteur,
            },
        ).one()
    except IntegrityError as erreur:
        if isinstance(erreur.orig, erreurs_psycopg.UniqueViolation):
            raise ErreurApplicative(
                code=CODE_CODE_DEJA_UTILISE,
                message=MESSAGE_CODE_DEJA_UTILISE,
                statut=409,
            ) from erreur
        raise

    entite_id, version = uuid.UUID(str(ligne[0])), int(ligne[1])

    connexion.execute(
        _ACCORDER_L_ADMINISTRATION_DE_L_ENTITE,
        {
            "personne": demande.premier_administrateur,
            "entite": entite_id,
            "role": TypeRoleTechnique.ENTITY_ADMIN.value,
            "instant": instant,
            "acteur": acteur,
        },
    )

    return EntiteCreee(id=entite_id, code=demande.code, version=version)
