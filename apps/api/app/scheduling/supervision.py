"""Le battement pousse vers Uptime Kuma — cahier §27, `T4`, story `MVP-L11-US008`.

POURQUOI UN SEUL BATTEMENT, PAS UN MONITOR PAR COMPOSANT

  Le §27.2 nomme onze composants a superviser (interface HTTPS, liveness,
  readiness, PostgreSQL, Redis, MinIO, workers, jobs bloques, e-mails, disque,
  certificats, sauvegardes, restauration). Mais `.env.example` ne declare
  qu'UNE SEULE variable, `UPTIME_KUMA_PUSH_URL` -- au singulier, jamais une
  liste -- et c'est elle qui fait foi (§6.5 : ne pas inventer onze variables
  que le modele ne nomme pas).

  La plupart des composants listes au §27.2 sont deja interrogeables en TIRANT
  dessus : `/health/ready` (LOT 1, `T3`) les sonde deja tous (PostgreSQL,
  Redis, MinIO). Un monitor HTTP Uptime Kuma configure sur cette route, par
  Jonathan, couvre ce qui se TIRE. Ce que ce module POUSSE est precisement ce
  qui ne peut PAS se tirer : la preuve que le worker TOURNE et EXECUTE ses
  cycles -- la demonstration citee par le cahier, « heartbeat de sauvegarde ou
  de maintenance recu dans Uptime Kuma ».

LE PROTOCOLE EST CELUI, PUBLIC ET DOCUMENTE, D'UPTIME KUMA

  Un monitor de type « Push » attend un GET sur l'URL fournie, avec deux
  parametres de requete : `status` (`up` ou `down`) et `msg` (un libelle
  court). Rien de ce depot ne l'invente : c'est le contrat du logiciel tiers.

NO-OP SILENCIEUX SI L'URL N'EST PAS CONFIGUREE

  `UPTIME_KUMA_PUSH_URL` vaut `""` par defaut (`.env.example`) : en
  developpement et en integration continue, aucun battement n'est tente, et
  aucune erreur n'est levee. C'est la MEME discipline que `EMAIL_PROVIDER`
  pour Mailpit -- une dependance externe absente de la pile locale ne doit
  jamais faire echouer un cycle.

AUCUN ALLER-RETOUR REEL POSSIBLE, ET C'EST NOMME

  Uptime Kuma n'est PAS un des huit services de `make up` -- §7.43 de la
  passation ne peut donc pas s'appliquer ici comme pour un ecran. La preuve
  est un serveur HTTP de test LOCAL (`infra/scripts/verifier-taches-
  planifiees.py`), qui capture la requete reelle emise par ce module et
  confirme sa forme -- une pile SIMULEE, jamais la pile REELLE.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import httpx

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

DELAI_SECONDES: Final[int] = 5


def envoyer_le_battement(parametres: Parametres, *, etat_sain: bool, message: str) -> None:
    """Pousser un battement vers Uptime Kuma — no-op si l'URL n'est pas configuree.

    **NE LEVE JAMAIS** : une supervision qui ferait echouer le cycle qu'elle
    supervise serait son propre defaut. Toute erreur reseau est avalee, et
    c'est delibere -- Uptime Kuma lui-meme detecte l'absence de battement.
    """
    url = parametres.UPTIME_KUMA_PUSH_URL.strip()
    if not url:
        return
    try:
        httpx.get(
            url,
            params={"status": "up" if etat_sain else "down", "msg": message},
            timeout=DELAI_SECONDES,
        )
    except httpx.HTTPError:
        #  Uptime Kuma constatera lui-meme l'absence de battement suivant --
        #  c'est exactement le role d'un monitor Push. Rien a journaliser de
        #  plus que ce que l'infrastructure reseau journalise deja.
        return
