"""Terminer, annuler, reouvrir une tache — matrice §8.1/§8.3, modele §13.6, `T8`/`T9`.

CE QUE `T8` LIVRE, ET CE QUE `T9` Y AJOUTE

  Trois gestes, matrice §8.1 : « Marquer une tache comme terminee », « Annuler
  la completion dans les 5 minutes » (`T8`) et « Reouvrir apres le delai de 5
  minutes » (`T9`). Les DEUX PREMIERES lignes sont IDENTIQUES — `Soi`
  uniquement, tiret partout ailleurs, y compris `DSM`/`BOOST` qui ont pourtant
  « Consultants »/« Cercle » sur la LECTURE du parcours (§2.1 de
  `fiche-lot-7.md`, piege n°1). La TROISIEME est l'INVERSE : `ESM`/`ADM-E`/
  `SUPER` seulement, `Soi` (et `DSM`/`BOOST`, meme rattaches) EXCLUS EN BLOC —
  voir `perimetre.py`, cinquieme grille du module.

LE DIAGRAMME §24.2 DU MODELE EST LA SOURCE DE VERITE DES TRANSITIONS

  `Todo -> Completed -> Todo` (annulation, `T8`) ; `Completed -> Reopened`
  (`T9`) ; **`Reopened -> Completed` : le nouvel arrivant termine A NOUVEAU**,
  meme geste que la premiere completion. `terminer_une_tache` accepte donc
  DEUX etats de depart, `todo` ET `reopened` — CORRECTIF `T9` a la fonction
  ecrite par `T8`, qui n'acceptait que `todo` et laissait une tache reouverte
  dans une impasse. `completed_at`/`completed_by_person_id` sont ECRASES par
  la nouvelle completion ; `reopened_at`/`reopened_by_person_id`/
  `reopen_reason` sont laisses TELS QUELS — aucune section du corpus n'exige
  de les effacer, et les effacer serait une invention (§6.5).

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

  **`T9` REUTILISE LA MEME ANCRE, JAMAIS UN SECOND MECANISME DE FENETRE** —
  `_FENETRE_DE_CINQ_MINUTES` (renommee depuis `_FENETRE_D_ANNULATION`, qui ne
  disait plus tout : elle sert desormais les DEUX sens). `annuler_la_
  completion` exige `completed_at >= instant - 5 min` (encore dans la
  fenetre) ; `reouvrir_une_tache` exige l'INVERSE STRICT, `completed_at <
  instant - 5 min` (fenetre CLOSE) — les deux frontieres se touchent sans se
  chevaucher : au instant exact ou la fenetre se ferme, l'annulation est
  encore possible (`>=`) et la reouverture ne l'est pas encore (`<` strict).

LA PRECONDITION EST DANS LE `WHERE`, LE DIAGNOSTIC DANS UNE LECTURE SEPAREE

  Meme parti que `cycle_de_vie.py` (`T6`) pour l'atomicite de l'ecriture : la
  transition entiere — etat de depart ET fenetre de temps — est UNE SEULE
  clause `WHERE` d'un `UPDATE`, sans lecture prealable qui laisserait une
  fenetre de course. MAIS, contrairement a `cycle_de_vie.py` (qui replie toute
  cause d'echec dans UN SEUL code, deliberement), `_echouer` DISTINGUE, pour
  `annuler_la_completion` ET `reouvrir_une_tache`, deux causes d'echec — la
  tache n'est pas dans l'etat requis, ou elle l'est mais la fenetre est du
  MAUVAIS cote — parce que la difference est UTILE a l'appelant : une
  annulation trop tardive renvoie vers `T9` (reouverture administrative,
  motif) ; une reouverture trop hative renvoie vers l'annulation en libre
  service (`T8`, que le nouvel arrivant peut encore faire lui-meme). Cette
  distinction n'exige PAS une seconde ecriture ni une fenetre de course :
  elle relit, APRES l'echec de l'ecriture, le SEUL etat necessaire pour
  choisir entre les codes — un diagnostic, jamais une decision.
  `terminer_une_tache`, elle, n'a PAS de troisieme cause : ses deux etats de
  depart (`todo`, `reopened`) ne portent aucune precondition de fenetre.
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

CODE_REOUVERTURE_PREMATUREE: Final = "reouverture_prematuree"
MESSAGE_REOUVERTURE_PREMATUREE: Final = (
    "Le delai de cinq minutes depuis la completion n'est pas encore ecoule — matrice §8.3. "
    "Le nouvel arrivant peut encore annuler lui-meme sa propre completion."
)

_FENETRE_DE_CINQ_MINUTES: Final = "5 minutes"

_TERMINER_LA_TACHE: Final = f"""
UPDATE onboarding_instance_task
   SET state = 'completed', completed_at = :instant, completed_by_person_id = :acteur
 WHERE id = :tache AND onboarding_instance_id = :instance AND state IN ('todo', 'reopened')
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

_ANNULER_LA_COMPLETION: Final = f"""
UPDATE onboarding_instance_task
   SET state = 'todo', completed_at = NULL, completed_by_person_id = NULL
 WHERE id = :tache AND onboarding_instance_id = :instance AND state = 'completed'
   AND completed_at >= CAST(:instant AS timestamptz) - INTERVAL '{_FENETRE_DE_CINQ_MINUTES}'
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

_REOUVRIR_LA_TACHE: Final = f"""
UPDATE onboarding_instance_task
   SET state = 'reopened', reopened_at = :instant, reopened_by_person_id = :acteur,
       reopen_reason = :motif
 WHERE id = :tache AND onboarding_instance_id = :instance AND state = 'completed'
   AND completed_at < CAST(:instant AS timestamptz) - INTERVAL '{_FENETRE_DE_CINQ_MINUTES}'
RETURNING {COLONNES_TACHE}
"""  # noqa: S608

_LIRE_L_ETAT_ACTUEL: Final = """
SELECT state FROM onboarding_instance_task WHERE id = :tache AND onboarding_instance_id = :instance
"""


def _echouer(
    connexion: Connection,
    *,
    instance: uuid.UUID,
    tache: uuid.UUID,
    etats_attendus: frozenset[str],
    code_fenetre: str | None = None,
    message_fenetre: str | None = None,
) -> NoReturn:
    """Diagnostic APRES l'echec de l'ecriture atomique — jamais une decision :
    voir l'en-tete. Choisit entre 404 (tache introuvable dans CE parcours),
    409 transition invalide (etat de depart hors de `etats_attendus`), et,
    quand `code_fenetre` est fourni, un TROISIEME code pour l'etat attendu
    mais la fenetre de temps du MAUVAIS cote (annulation trop tardive,
    reouverture trop hative)."""
    ligne = connexion.execute(
        text(_LIRE_L_ETAT_ACTUEL), {"tache": tache, "instance": instance}
    ).first()
    if ligne is None:
        raise ErreurApplicative(
            code=CODE_TACHE_INTROUVABLE,
            message=MESSAGE_TACHE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    if str(ligne[0]) in etats_attendus and code_fenetre is not None:
        #  L'etat de depart correspond : la SEULE cause d'echec qui reste est
        #  la fenetre de cinq minutes, du mauvais cote.
        raise ErreurApplicative(
            code=code_fenetre, message=message_fenetre or "", statut=status.HTTP_409_CONFLICT
        )
    raise ErreurApplicative(
        code=CODE_TRANSITION_TACHE_INVALIDE,
        message=MESSAGE_TRANSITION_TACHE_INVALIDE,
        statut=status.HTTP_409_CONFLICT,
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
    verifie par l'appelant (`perimetre.peut_agir_sur_sa_tache_onboarding`).
    Accepte `todo` ET `reopened` comme etat de depart — voir l'en-tete,
    diagramme §24.2, correctif `T9`."""
    ligne = (
        connexion.execute(
            text(_TERMINER_LA_TACHE),
            {"tache": tache, "instance": instance, "acteur": acteur, "instant": instant},
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        _echouer(
            connexion,
            instance=instance,
            tache=tache,
            etats_attendus=frozenset({"todo", "reopened"}),
        )
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
        _echouer(
            connexion,
            instance=instance,
            tache=tache,
            etats_attendus=frozenset({"completed"}),
            code_fenetre=CODE_DELAI_DEPASSE,
            message_fenetre=MESSAGE_DELAI_DEPASSE,
        )
    enregistrer_un_evenement_de_tache(
        connexion,
        entite=entite,
        tache=tache,
        type_evenement=TypeEvenementTache.CANCELLED.value,
        instant=instant,
        acteur=acteur,
    )
    return tache_depuis_la_ligne(ligne)


def reouvrir_une_tache(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    instance: uuid.UUID,
    tache: uuid.UUID,
    acteur: uuid.UUID,
    motif: str,
    instant: dt.datetime,
) -> TacheDuParcours:
    """Matrice §8.1 « Reouvrir apres le delai de 5 minutes » / §8.3 — `ESM`,
    administrateur d'entite ou super-administrateur SEULEMENT, verifie par
    l'appelant (`perimetre.ROLES_DE_REOUVERTURE_DES_TACHES`, garde de role
    coarse). `completed_at`/`completed_by_person_id` sont CONSERVES — a la
    difference de `annuler_la_completion`, la reouverture garde la trace de
    la completion originale et AJOUTE celle de la reouverture. Le motif est
    OBLIGATOIRE (§8.3, « exige un motif ») ; la base l'impose aussi, par la
    contrainte `motif_requis_a_la_reouverture` (modele §13.6, posee des
    `T1`) — voir §7.32, n'ecris pas de defense contre un etat que la base
    interdit deja."""
    ligne = (
        connexion.execute(
            text(_REOUVRIR_LA_TACHE),
            {
                "tache": tache,
                "instance": instance,
                "acteur": acteur,
                "motif": motif,
                "instant": instant,
            },
        )
        .mappings()
        .one_or_none()
    )
    if ligne is None:
        _echouer(
            connexion,
            instance=instance,
            tache=tache,
            etats_attendus=frozenset({"completed"}),
            code_fenetre=CODE_REOUVERTURE_PREMATUREE,
            message_fenetre=MESSAGE_REOUVERTURE_PREMATUREE,
        )
    enregistrer_un_evenement_de_tache(
        connexion,
        entite=entite,
        tache=tache,
        type_evenement=TypeEvenementTache.REOPENED.value,
        instant=instant,
        acteur=acteur,
        motif=motif,
    )
    return tache_depuis_la_ligne(ligne)
