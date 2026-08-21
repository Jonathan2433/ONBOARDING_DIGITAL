"""Purge des compteurs de limitation de debit — helper PARTAGE des verificateurs.

LOT 3, sous-etape `T8`.

POURQUOI UN MODULE PARTAGE PLUTOT QU'UNE COPIE PAR VERIFICATEUR

  `T8` a ajoute une CONDITION a deux operations qui existaient deja : dix demandes
  de lien par adresse et par heure, cinq echecs administrateur par adresse. Les
  compteurs vivent dans **Redis**, donc ils survivent d'un controle au suivant --
  contrairement a un nettoyage SQL, qui repart d'un etat connu.

  Consequence mesuree : `make csrf-check` et `make admin-check`, tous deux justes
  la veille, ont echoue sur un livrable conforme. Le premier fait une dizaine de
  demandes sur la meme adresse ; le second pousse deliberement un compte jusqu'au
  verrouillage. **C'est le §7.21** -- un controle ne devient pas faux tout seul, il
  le devient quand nous changeons le monde autour de lui.

  **ET C'EST POURQUOI CE FICHIER EXISTE.** Chaque verificateur du depot porte sa
  propre copie de `lire_env` et de `psql` -- convention assumee, ces fonctions ne
  bougent plus. Ici c'est l'inverse : `T9` a `T12` ajouteront des controles qui
  passeront par les memes routes, et trois copies d'une purge finiraient par
  diverger sur le prefixe. Le prefixe est **importe** de `app.auth.debit`, une
  seule source -- motif de `DEC-466`, et §7.27 pour les listes recopiees.

CE QU'ELLE N'EFFACE PAS

  Redis sert aussi de courtier Dramatiq (§16.4) et porte les cles d'idempotence de
  `T7`. La purge ne touche **que** le prefixe de debit, et un motif errone
  effacerait des files : c'est pourquoi il n'est pas ecrit ici.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping


def purger_les_compteurs_de_debit(env: Mapping[str, str]) -> int:
    """Effacer tous les compteurs de debit. Rend le nombre de cles supprimees.

    Args:
        env: le fichier d'environnement deja lu. `REDIS_HOST_PORT` et
            `REDIS_PASSWORD` en sont extraits ; le port est publie sur
            `127.0.0.1` (`DEC-460`), donc aucun conteneur n'est sollicite.

    Raises:
        Elle NE rattrape RIEN. Un verificateur qui ne peut pas repartir d'un etat
        connu doit **echouer bruyamment** : masquer l'erreur ici ferait echouer le
        controle suivant sur une cause qui n'est pas la sienne -- §7.6.
    """
    import redis

    from app.auth.debit import PREFIXE_REDIS

    client = redis.Redis(
        host="127.0.0.1",
        port=int(env.get("REDIS_HOST_PORT", "6379")),
        password=env.get("REDIS_PASSWORD") or None,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    cles = list(client.scan_iter(match=f"{PREFIXE_REDIS}*", count=500))
    return int(client.delete(*cles)) if cles else 0
