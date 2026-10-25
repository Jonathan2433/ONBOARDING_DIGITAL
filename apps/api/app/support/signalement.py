"""Écrire un signalement de bug — modèle §21.4, cahier §9.6/§10.12.

LOT 10, sous-étape `T11`, story `MVP-L10-US005`.

QUATRE CHAMPS « AJOUTÉS AUTOMATIQUEMENT », ET AUCUN NE VIENT DU CORPS DE LA REQUÊTE

  Le cahier §10.12 et le modèle §21.4 marquent `application_version`,
  `environment` et `browser_summary` comme ajoutés automatiquement — jamais
  saisis. Ce service les résout donc lui-même, à partir de ce que l'API SAIT
  déjà sur elle-même (`Parametres.APP_VERSION`/`APP_ENV`, posés depuis le
  LOT 1) et sur la requête (l'en-tête `User-Agent`), jamais depuis une valeur
  que le client soumettrait — ce que le client soumet n'est pas « automatique »,
  c'est une donnée qu'on lui ferait croire l'être. Seul `page_path` reste fourni
  par l'appelant : c'est la route AFFICHÉE côté client au moment du clic, une
  information que le serveur ne peut structurellement pas connaître (l'API ne
  voit jamais l'URL du routeur React, seulement la sienne).

`correlation_token` EST TOUJOURS REMPLI, MÊME SI LA COLONNE EST NULLABLE

  Le modèle §21.4 écrit « Facultatif » pour cette colonne, à la différence
  d'`audit_event.correlation_token` qui est `NOT NULL` — et c'est pour cela
  qu'elle a été posée nullable par `T1` (`apps/api/app/audit/modeles.py`).
  Mais le critère de sortie 5 du lot (« l'identifiant de corrélation relie
  interface, API et logs … réutilisation de `packages/observabilite`, jamais
  un second mécanisme ») ne distingue pas `audit_event` de `bug_report` : les
  deux tables appartiennent au même critère. Ce service reprend donc EXACTEMENT
  le même repli que `app.audit.services.enregistrer_un_evenement` —
  `correlation_courante() ou engendrer()` — et ne laisse jamais la colonne
  vide en pratique. « Nullable au schéma » n'est pas « optionnel au service » :
  la colonne reste nullable parce qu'une ligne insérée hors requête (un script,
  un test unitaire sans contexte applicatif) n'a structurellement rien à y
  mettre, pas parce que ce service choisirait de l'omettre.

`BROWSER_SUMMARY` EST LU DANS L'EN-TÊTE, JAMAIS DANS LE CORPS

  Le modèle dit « Minimisé », pas « absent » : le `User-Agent` est tronqué à
  une longueur bornée, jamais transmis en entier ni enrichi (pas d'analyse de
  famille de navigateur, qui n'est demandée nulle part). Le lire dans l'EN-TÊTE
  de la requête plutôt que dans un champ de formulaire que le frontend
  recopierait depuis `navigator.userAgent` est strictement la même donnée, une
  source de moins à faire confiance — et une fonction partagée de moins entre
  le frontend et le backend à tenir synchronisée.

CE SERVICE N'ÉCRIT PAS DE SECOND `audit_event`

  Un signalement de bug EST sa propre trace — qui, quand, depuis quelle page,
  avec quelle corrélation — exactement ce qu'`audit_event` apporterait de plus
  pour un domaine qui n'en a pas une déjà. Les écritures `T2` à `T7` auditent
  des actions qui modifient des données métier protégées ; déposer un
  signalement n'en modifie aucune. Pas de second `audit_event` ici, par le
  même raisonnement que celui qui épargne `audit_event` lui-même d'un
  méta-événement pour sa propre écriture.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.audit.modeles import EtatSignalement
from app.shared.correlation import correlation_courante, engendrer

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  §16.2 de la matrice / §10.12 du cahier : « limitées au contexte nécessaire ».
#  Une longueur bornée et arbitraire, jamais le `User-Agent` brut et illimité —
#  « Minimisé » (modèle §21.4), pas « tronqué au hasard ». 200 caractères
#  couvrent largement un `User-Agent` de navigateur moderne sans jamais
#  s'approcher d'un `TEXT` illimité.
LONGUEUR_MAXIMALE_DU_RESUME_NAVIGATEUR: Final = 200


def _resumer_le_navigateur(user_agent: str | None) -> str | None:
    """Le `User-Agent` de la requête, minimisé — jamais une valeur du client."""
    if user_agent is None or user_agent.strip() == "":
        return None
    return user_agent.strip()[:LONGUEUR_MAXIMALE_DU_RESUME_NAVIGATEUR]


@dataclasses.dataclass(frozen=True, slots=True)
class SignalementCree:
    """Ce que la route rend après l'écriture."""

    id: uuid.UUID
    state: str
    created_at: dt.datetime


_INSERER_UN_SIGNALEMENT: Final = text(
    "INSERT INTO bug_report "
    "(entity_id, reported_by_person_id, state, description, reproduction_steps, "
    " page_path, application_version, environment, browser_summary, "
    " correlation_token, created_by_person_id, updated_by_person_id, "
    " created_at, updated_at) "
    "VALUES "
    "(:entite, :acteur, :etat, :description, :etapes_de_reproduction, "
    " :chemin_de_page, :version_application, :environnement, :resume_navigateur, "
    " :correlation, :acteur, :acteur, :instant, :instant) "
    "RETURNING id, state, created_at"
)


def creer_un_signalement(
    connexion: Connection,
    *,
    entity_id: uuid.UUID,
    reported_by_person_id: uuid.UUID,
    description: str,
    reproduction_steps: str | None,
    page_path: str,
    application_version: str,
    environment: str,
    user_agent: str | None,
    instant: dt.datetime,
    correlation_token: str | None = None,
) -> SignalementCree:
    """Écrire une ligne `bug_report`, dans la transaction déjà ouverte de l'appelant.

    Args:
        connexion: connexion ouverte, dans une transaction que l'appelant valide.
        entity_id: l'entité consultée — toujours l'entité PRINCIPALE du
            rapporteur, résolue par l'appelant (`app.permissions.services.
            entite_principale`) : voir `app/support/routes.py` pour le motif.
        reported_by_person_id: l'auteur, `NOT NULL` — un visiteur anonyme n'a
            jamais de session, donc jamais accès à cette fonction.
        description, reproduction_steps: saisie libre de l'utilisateur.
        page_path: la route du frontend affichée au moment du clic — fournie
            par l'appelant, jamais déduite ici.
        application_version, environment: ajoutés automatiquement, lus par
            l'appelant depuis `Parametres.APP_VERSION`/`APP_ENV`, jamais
            depuis le corps de la requête.
        user_agent: l'en-tête `User-Agent` BRUT de la requête HTTP — ce service
            le minimise lui-même (`_resumer_le_navigateur`), l'appelant ne
            doit rien tronquer avant de le passer.
        instant: l'horodatage de l'action, injecté — jamais un `now()` lu ici.
        correlation_token: si `None`, repris de `correlation_courante()` (posé
            par le middleware sur chaque requête, LOT 1 `T4`), avec repli sur
            `engendrer()` pour un appel hors requête.
    """
    jeton_de_correlation = correlation_token or correlation_courante() or engendrer()
    ligne = connexion.execute(
        _INSERER_UN_SIGNALEMENT,
        {
            "entite": entity_id,
            "acteur": reported_by_person_id,
            "etat": EtatSignalement.NEW.value,
            "description": description,
            "etapes_de_reproduction": reproduction_steps,
            "chemin_de_page": page_path,
            "version_application": application_version,
            "environnement": environment,
            "resume_navigateur": _resumer_le_navigateur(user_agent),
            "correlation": jeton_de_correlation,
            "instant": instant,
        },
    ).one()
    return SignalementCree(id=ligne.id, state=ligne.state, created_at=ligne.created_at)
