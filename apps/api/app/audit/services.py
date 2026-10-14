"""Le service d'ecriture d'audit generique — modele §21.1, cahier §10.11/§16.2.

LOT 10, sous-etape `T2`, stories `MVP-L10-US001`/`US002`.

ECRITURE SYNCHRONE, DANS LA MEME TRANSACTION QUE L'ACTION METIER

  `ARB-DATA-005`/`§30.20` : « une action metier et son audit sont atomiques ».
  Meme motif, meme forme que toutes les ecritures `auth_event` deja posees par
  le LOT 3 (`app/auth/services.py`, `sessions.py`, `comptes_de_service.py`) :
  une fonction recoit une `Connection` DEJA OUVERTE dans la transaction de
  l'appelant, et n'en ouvre jamais une elle-meme. Ce service ne fait rien de
  plus — c'est le meme patron que `app.imports.execution._ecrire_les_problemes`
  (LOT 9), applique ici au journal general plutot qu'a un domaine particulier.

`action_code` REUTILISE LE VOCABULAIRE DE CHAQUE DOMAINE, IL N'EN INVENTE PAS UN SECOND

  `audit_event.action_code` est un vocabulaire OUVERT (modele §21.1 : « Code
  stable », sans enumeration fermee — meme lecture que `operational_alert.
  source`, voir `app/audit/modeles.py`). Pour l'authentification, les sept
  valeurs existent deja : `TypeEvenementAuth`, posees par `T2` du LOT 3 et
  ecrites dans `auth_event.event_type`. Inventer un second vocabulaire pour la
  meme notion dupliquerait une classification deja correcte (§7.27 de la
  passation) — c'est a l'appelant de fournir le code de SON domaine, jamais a
  ce service d'en connaitre un seul.

`correlation_token` EST TOUJOURS RENSEIGNE, JAMAIS LAISSE VIDE

  `audit_event.correlation_token` est `NOT NULL`, non vide (contrainte
  `correlation_token_non_vide`). `app.main` pose systematiquement un
  identifiant de correlation avant d'atteindre une route (`definir_correlation`,
  LOT 1 `T4`) : `correlation_courante()` le rend donc TOUJOURS a l'interieur
  d'une requete ou d'un job. Le repli sur `engendrer()` ne sert que le seul cas
  ou ce service est appele directement, hors requete et hors job — un test qui
  n'ouvre pas l'application.

CE QUE CE SERVICE NE FAIT PAS

  Il n'invente et ne verifie AUCUNE exclusion de contenu : le §16.2/§21.1
  interdit mots de passe, jetons, liens magiques complets, secrets, CSV
  complets, corps d'e-mail bruts — c'est a CHAQUE SITE D'APPEL de ne jamais les
  passer en `summary`, `old_values`, `new_values` ou `reason`. Un filtre pose
  ICI, a posteriori, masquerait un defaut d'appelant au lieu de le faire
  echouer au bon endroit — et aucune liste de motifs textuels ne peut remplacer
  la discipline deja tenue par `app.auth.services`/`sessions.py`/
  `comptes_de_service.py`, dont aucun `detail` d'`auth_event` ne porte jamais
  ces donnees depuis le LOT 3.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from app.shared.correlation import correlation_courante, engendrer

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  §21.1/§10.11/§16.1 : « conservees un an ». Calculee EXPLICITEMENT depuis le
#  MEME `instant` que `occurred_at`, jamais laissee au defaut serveur de la
#  table (`now() + interval '1 year'`) : un `instant` injecte qui differe de
#  `now()` — tout test de ce depot en injecte un — ferait diverger les deux
#  colonnes l'une de l'autre. Meme lecon que `creer_un_jeton`
#  (`app/auth/comptes_de_service.py`, §7.0 sixieme proposition de la passation).
DUREE_DE_RETENTION = dt.timedelta(days=365)

_INSERER_UN_EVENEMENT = text(
    "INSERT INTO audit_event "
    "(entity_id, actor_person_id, actor_service_account_id, action_code, "
    " resource_type, resource_reference, summary, old_values, new_values, "
    " reason, correlation_token, occurred_at, retention_until) "
    "VALUES (:entite, :acteur_personne, :acteur_compte_de_service, :code_action, "
    " :type_ressource, :reference_ressource, :resume, "
    " CAST(:anciennes_valeurs AS jsonb), CAST(:nouvelles_valeurs AS jsonb), "
    " :motif, :correlation, :survenu_a, :retenu_jusqua)"
)


def enregistrer_un_evenement(
    connexion: Connection,
    *,
    instant: dt.datetime,
    action_code: str,
    resource_type: str,
    summary: str,
    entity_id: uuid.UUID | None = None,
    actor_person_id: uuid.UUID | None = None,
    actor_service_account_id: uuid.UUID | None = None,
    resource_reference: uuid.UUID | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    reason: str | None = None,
    correlation_token: str | None = None,
) -> None:
    """Ecrire une ligne `audit_event`, dans la transaction DEJA ouverte de l'appelant.

    Args:
        connexion: connexion ouverte, dans une transaction que l'appelant
            valide — jamais ouverte ici, meme discipline que tout `app.auth`
            (`§2` de la fiche du LOT 10, `ARB-DATA-005`).
        instant: l'horodatage de l'action metier auditee, **jamais un `now()`
            lu ici** : c'est le MEME instant que l'ecriture metier, celui que
            l'appelant a deja recu ou calcule.
        action_code: code stable, non vide (contrainte `action_code_non_vide`).
            Vocabulaire OUVERT (§21.1) : reutiliser l'enumeration du domaine
            appelant plutot que d'en inventer une seconde pour la meme notion
            (`TypeEvenementAuth.value` pour l'authentification).
        resource_type: le type de ressource concernee, non vide.
        summary: resume lisible, non vide, **jamais une donnee exclue** — mot
            de passe, jeton, lien magique complet, secret, CSV complet, corps
            d'e-mail brut (cahier §16.2, modele §21.1).
        resource_reference: identifiant de la ressource, polymorphe et SANS clé
            etrangere (le modele le veut ainsi, voir `app/audit/modeles.py`) —
            peut rester `None` quand aucune ligne stable n'existe (ressource
            pas encore creee, ou refus avant toute ecriture).
        old_values, new_values: `jsonb` filtre, jamais les colonnes sensibles
            d'une table metier. `None` reste une colonne SQL `NULL`, jamais le
            litteral JSON `null`.
        reason: motif humain, obligatoire pour les actions que le domaine
            appelant juge sensibles (§21.1 : « obligatoire pour actions
            sensibles ») — ce service ne l'exige jamais lui-meme, la regle
            appartient a chaque domaine cable.
        correlation_token: si `None`, repris de `correlation_courante()` (pose
            par le middleware sur chaque requete, LOT 1 `T4`), avec repli sur
            `engendrer()` pour un appel hors requete et hors job.
    """
    jeton_de_correlation = correlation_token or correlation_courante() or engendrer()
    connexion.execute(
        _INSERER_UN_EVENEMENT,
        {
            "entite": entity_id,
            "acteur_personne": actor_person_id,
            "acteur_compte_de_service": actor_service_account_id,
            "code_action": action_code,
            "type_ressource": resource_type,
            "reference_ressource": resource_reference,
            "resume": summary,
            "anciennes_valeurs": json.dumps(old_values) if old_values is not None else None,
            "nouvelles_valeurs": json.dumps(new_values) if new_values is not None else None,
            "motif": reason,
            "correlation": jeton_de_correlation,
            "survenu_a": instant,
            "retenu_jusqua": instant + DUREE_DE_RETENTION,
        },
    )
