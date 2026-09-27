"""Terminer une tache, l'annuler dans les cinq minutes — matrice §8.1/§8.3, modele §13.6, `T8`.

CE QUE `T8` LIVRE, ET CE QU'IL NE LIVRE PAS

  Deux gestes, matrice §8.1 : « Marquer une tache comme terminee » et
  « Annuler la completion dans les 5 minutes ». Les DEUX lignes sont IDENTIQUES
  — `Soi` uniquement, tiret partout ailleurs, y compris `DSM`/`BOOST` qui ont
  pourtant « Consultants »/« Cercle » sur la LECTURE du parcours (§2.1 de
  `fiche-lot-7.md`, piege n°1). La reouverture APRES le delai (§8.3, `ESM`/
  `ADM-E`/`SUPER`, motif obligatoire) est `T9`, une route SEPAREE : ce module
  n'y touche pas, et `EtatTacheInstance.REOPENED` n'apparait jamais ici.

`annuler_la_completion` NE PRODUIT JAMAIS L'ETAT `cancelled`

  Le modele §13.6 donne QUATRE etats — `todo`, `completed`, `reopened`,
  `cancelled` — et il serait tentant de lire « annulation » comme une
  transition vers `cancelled`. Ce n'est PAS le cas : `cancelled` est reserve a
  `T10` (§13.7, evenement `CANCELLED_ON_REPLACEMENT` — une tache rendue
  obsolete par un changement de statut, jamais desiree a nouveau). Annuler UNE
  COMPLETION dans les cinq minutes est un GESTE DU NOUVEL ARRIVANT SUR SA
  PROPRE ERREUR : la tache redevient `todo`, `completed_at`/`completed_by_
  person_id` sont EFFACES — comme si la completion n'avait jamais eu lieu,
  hormis l'evenement `CANCELLED` que ce module pose au journal (§13.7,
  evenement distinct de l'etat du meme nom). Le nouvel arrivant peut donc la
  re-terminer ensuite, ce qu'une transition vers `cancelled` (terminale)
  interdirait.

LA FENETRE DE CINQ MINUTES EST ANCREE A `completed_at`, JAMAIS A UNE HORLOGE MOCKEE

  `fiche-lot-7.md` §3 l'exige en toutes lettres : « la fenetre de cinq minutes
  doit etre injectable, jamais un `sleep()` de test ni une horloge figee ».
  Ici, la precondition compare l'`instant` REEL de la requete (capture par la
  route, jamais figee) a `completed_at`, une valeur deja STOCKEE en base — et
  c'est CETTE valeur que les tests font varier, en la reculant directement par
  SQL, jamais en dormant ni en mockant `dt.datetime.now`. Aucune horloge n'est
  jamais figee : `instant` est toujours le vrai `now()` de la route, comme
  partout ailleurs dans ce module (`T2`-`T7`).

LA PRECONDITION EST DANS LE `WHERE`, LE DIAGNOSTIC DANS UNE LECTURE SEPAREE

  Meme parti que `cycle_de_vie.py` (`T6`) pour l'atomicite de l'ecriture : la
  transition entiere — etat de depart ET fenetre de temps pour l'annulation —
  est UNE SEULE clause `WHERE` d'un `UPDATE`, sans lecture prealable qui
  laisserait une fenetre de course. MAIS, contrairement a `cycle_de_vie.py`
  (qui replie toute cause d'echec dans UN SEUL code, deliberement), ce module
  DISTINGUE deux causes d'echec pour `annuler_la_completion` — la tache n'est
  pas `completed`, ou elle l'est mais hors delai — parce que la difference
  est UTILE a l'appelant : un delai depasse renvoie vers `T9` (reouverture
  administrative, motif), un etat different signale une erreur de client.
  Cette distinction n'exige PAS une seconde ecriture ni une fenetre de
  course : elle relit, APRES l'echec de l'ecriture, le SEUL etat necessaire
  pour choisir entre les deux codes — un diagnostic, jamais une decision.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Final, NoReturn

from fastapi import status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.onboarding.instances import (
    COLONNES_TACHE,
    TacheDuParcours,
    enregistrer_un_evenement_de_tache,
    tache_depuis_la_ligne,
)
from app.onboarding.modeles import TypeEvenementTache
from app.shared.errors import ErreurApplicative

CODE_TACHE_INTROUVABLE: Final = "tache_introuvable"
MESSAGE_TACHE_INTROUVABLE: Final = (
    "Aucune tache de ce parcours actif ne correspond a cet identifiant."
)

CODE_TRANSITION_TACHE_INVALIDE: Final = "transition_de_tache_invalide"
MESSAGE_TRANSITION_TACHE_INVALIDE: Final = (
    "Cette tache n'est pas dans l'etat requis pour cette action — modele §13.6."
)

CODE_DELAI_DEPASSE: Final = "delai_d_annulation_depasse"
MESSAGE_DELAI_DEPASSE: Final = (
    "Le delai de cinq minutes pour annuler cette completion est depasse — matrice §8.3. "
    "Seuls l'ESM, l'administrateur d'entite ou le super-administrateur peuvent desormais "
    "reouvrir cette tache, avec un motif."
)

_FENETRE_D_ANNULATION: Final = "5 minutes"

_TERMINER_LA_TACHE: Final = f"""
UPDATE onboarding_instance_task
   SET state = 'completed', completed_at = :instant, completed_by_person_id = :acteur
 WHERE id = :tache AND onboarding_instance_id = :instance AND state = 'todo'
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

_ANNULER_LA_COMPLETION: Final = f"""
UPDATE onboarding_instance_task
   SET state = 'todo', completed_at = NULL, completed_by_person_id = NULL
 WHERE id = :tache AND onboarding_instance_id = :instance AND state = 'completed'
   AND completed_at >= CAST(:instant AS timestamptz) - INTERVAL '{_FENETRE_D_ANNULATION}'
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

_LIRE_L_ETAT_ACTUEL: Final = """
SELECT state FROM onboarding_instance_task WHERE id = :tache AND onboarding_instance_id = :instance
"""


def _echouer(
    connexion: Connection, *, instance: uuid.UUID, tache: uuid.UUID, etat_attendu: str
) -> NoReturn:
    """Diagnostic APRES l'echec de l'ecriture atomique — jamais une decision :
    voir l'en-tete. Choisit entre 404 (tache introuvable dans CE parcours),
    409 transition invalide (mauvais etat de depart), et pour `annuler_la_
    completion` seul, 409 delai depasse (bon etat, fenetre fermee)."""
    ligne = connexion.execute(
        text(_LIRE_L_ETAT_ACTUEL), {"tache": tache, "instance": instance}
    ).first()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_TACHE_INTROUVABLE,
            message=MESSAGE_TACHE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    if str(ligne[0]) != etat_attendu:
        raise ErreurApplicative(
            code=CODE_TRANSITION_TACHE_INVALIDE,
            message=MESSAGE_TRANSITION_TACHE_INVALIDE,
            statut=status.HTTP_409_CONFLICT,
        )
    #  L'etat de depart correspond : la SEULE cause d'echec qui reste, pour
    #  `annuler_la_completion`, est la fenetre de cinq minutes depassee.
    raise ErreurApplicative(
        code=CODE_DELAI_DEPASSE, message=MESSAGE_DELAI_DEPASSE, statut=status.HTTP_409_CONFLICT
    )


def terminer_une_tache(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    instance: uuid.UUID,
    tache: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> TacheDuParcours:
    """Matrice §8.1 « Marquer une tache comme terminee » — `Soi` uniquement,
    verifie par l'appelant (`perimetre.peut_agir_sur_sa_tache_onboarding`)."""
    ligne = (
        connexion.execute(
            text(_TERMINER_LA_TACHE),
            {"tache": tache, "instance": instance, "acteur": acteur, "instant": instant},
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        _echouer(connexion, instance=instance, tache=tache, etat_attendu="todo")
    enregistrer_un_evenement_de_tache(
        connexion,
        entite=entite,
        tache=tache,
        type_evenement=TypeEvenementTache.COMPLETED.value,
        instant=instant,
        acteur=acteur,
    )
    return tache_depuis_la_ligne(ligne)


def annuler_la_completion(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    instance: uuid.UUID,
    tache: uuid.UUID,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> TacheDuParcours:
    """Matrice §8.1 « Annuler la completion dans les 5 minutes » — `Soi`
    uniquement. `completed` redevient `todo`, JAMAIS `cancelled` — voir
    l'en-tete du module. Au-dela de cinq minutes, seule `T9` (reouverture
    administrative, motif obligatoire) peut agir."""
    ligne = (
        connexion.execute(
            text(_ANNULER_LA_COMPLETION), {"tache": tache, "instance": instance, "instant": instant}
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        _echouer(connexion, instance=instance, tache=tache, etat_attendu="completed")
    enregistrer_un_evenement_de_tache(
        connexion,
        entite=entite,
        tache=tache,
        type_evenement=TypeEvenementTache.CANCELLED.value,
        instant=instant,
        acteur=acteur,
    )
    return tache_depuis_la_ligne(ligne)
