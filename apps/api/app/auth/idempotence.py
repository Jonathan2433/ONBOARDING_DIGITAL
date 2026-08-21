"""Cles d'idempotence des ecritures — cahier §18.6, story `MVP-L03-US005`.

LOT 3, sous-etape `T7`.

CE QUE CE MODULE COUVRE, ET CE QU'IL NE COUVRE PAS

  **Le modele ne declare de cle d'idempotence QUE sur `async_job`** (§20.1,
  « `idempotency_key` | Unique dans son perimetre »), et `async_job` appartient au
  **LOT 11**. Le §18.6 enumere six operations a rendre idempotentes -- invitations,
  imports, creation d'entite, purge, exports, operations en masse -- et **aucune
  n'existe aujourd'hui**.

  Ce module traite donc le probleme qui existe **maintenant**, celui que le titre
  de la sous-etape nomme : la **double soumission**. Un double clic sur « demander
  un lien » envoie deux e-mails et invalide le premier lien -- un effet double,
  visible par l'utilisateur.

      couvert ici          la double soumission, sur une fenetre de quelques heures
      NON couvert ici      l'idempotence DURABLE des six operations du §18.6,
                           qui restera portee par `async_job.idempotency_key`
                           au LOT 11

  **Le dire est le point.** Adosser la garantie a Redis la rend non durable : un
  redemarrage de Redis efface les cles memorisees, et un rejeu ulterieur
  produirait un second effet. C'est acceptable pour une double soumission -- dont
  la fenetre est de quelques secondes -- et ce ne le serait pas pour un import.
  Inventer une table aurait ete plus fort et **interdit** : le modele declare deja
  ou cette cle doit vivre, et en poser une seconde laisserait au LOT 11 deux
  mecanismes a reconcilier (`DEC-531`).

C'EST UN COMPARE-ET-POSE, POUR LA QUATRIEME FOIS DANS CE LOT

  `SET cle valeur NX EX duree` est atomique cote Redis : il pose la cle **et**
  dit si elle existait, en une seule operation. Lire puis ecrire laisserait deux
  requetes simultanees passer la lecture avant que l'une n'ecrive -- et **les deux
  produiraient leur effet**, ce qui est exactement ce que cette protection doit
  empecher.

  Meme forme qu'en `T4` (usage unique), `T5` (compteur d'echecs) et `T6`
  (rafraichissement de session). Le patron est desormais celui du lot.

LA CLE EST CLOISONNEE PAR ROUTE

  Deux routes differentes portant la meme cle sont deux operations differentes :
  les confondre ferait qu'une demande de lien bloquerait une deconnexion. Le §20.1
  dit « unique dans son **perimetre** », et le perimetre d'une requete HTTP est sa
  route.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

#  L'en-tete que le client fournit. `Idempotency-Key` est le nom d'usage, et le
#  declarer ici en fait la seule source -- lue par le contrat partage, les tests
#  et les controles.
EN_TETE_CLE = "Idempotency-Key"

#  Duree de memorisation. **Quelques heures, pas quelques jours** : la fenetre
#  d'une double soumission est de quelques secondes, et une duree longue
#  donnerait l'illusion d'une garantie durable que Redis ne peut pas tenir.
SECONDES_DE_MEMOIRE = 6 * 3600

#  Bornes de la cle. Elle vient du client : sans borne, un en-tete de plusieurs
#  megaoctets serait accepte et stocke.
LONGUEUR_MINIMALE_CLE = 8
LONGUEUR_MAXIMALE_CLE = 200

#  Une cle est interpolee dans un nom de cle Redis : un caractere de separation
#  y creerait une collision avec un autre espace de noms. Le motif est donc
#  restrictif, et une cle fantaisiste est REFUSEE plutot que nettoyee -- nettoyer
#  ferait que deux cles differentes pourraient devenir la meme.
MOTIF_CLE = re.compile(r"^[A-Za-z0-9._:-]+$")

#  Prefixe de l'espace de noms Redis. Redis sert aussi de courtier Dramatiq
#  (§16.4) : sans prefixe, une cle d'idempotence pourrait collisionner avec une
#  cle de file.
PREFIXE_REDIS = "onboarding:idempotence:"

#  Un delai court : cette verification est sur le chemin d'une requete, et un
#  Redis lent ne doit pas la faire pendre.
DELAI_REDIS_SECONDES = 2


class CleInvalide(ValueError):
    """La cle fournie ne respecte pas la forme attendue.

    Le message nomme la contrainte, **jamais la valeur** : une cle peut porter un
    identifiant metier, et un message d'erreur finit dans un journal.
    """


class MemoireIndisponible(RuntimeError):
    """Redis ne repond pas. **L'appelant doit decider**, et ne pas deviner."""


def controler_la_cle(cle: str) -> None:
    """Refuser une cle inexploitable, en nommant la contrainte."""
    if not LONGUEUR_MINIMALE_CLE <= len(cle) <= LONGUEUR_MAXIMALE_CLE:
        message = (
            f"Idempotency-Key : longueur attendue entre {LONGUEUR_MINIMALE_CLE} et "
            f"{LONGUEUR_MAXIMALE_CLE} caracteres"
        )
        raise CleInvalide(message)
    if not MOTIF_CLE.match(cle):
        message = (
            "Idempotency-Key : caracteres attendus `A-Z a-z 0-9 . _ : -`. Une cle "
            "n'est PAS nettoyee, elle est refusee — nettoyer ferait que deux cles "
            "differentes deviendraient la meme"
        )
        raise CleInvalide(message)


def _client(parametres: Parametres) -> redis.Redis:
    return redis.Redis.from_url(
        parametres.url_redis(),
        socket_connect_timeout=DELAI_REDIS_SECONDES,
        socket_timeout=DELAI_REDIS_SECONDES,
    )


def reserver(parametres: Parametres, *, route: str, cle: str) -> bool:
    """Reserver une cle. Rend `True` si c'est la PREMIERE fois.

    **UN SEUL ALLER-RETOUR, ATOMIQUE.** `SET … NX EX` pose la cle et dit si elle
    existait, en une operation. Lire puis ecrire laisserait deux requetes
    simultanees produire leur effet toutes les deux -- ce que cette protection
    doit precisement empecher.

    Args:
        route: le perimetre. Le §20.1 dit « unique dans son perimetre », et deux
            routes portant la meme cle sont deux operations differentes.
        cle: la valeur de l'en-tete, **deja controlee** par `controler_la_cle`.

    Returns:
        `True` si la cle vient d'etre posee — l'appelant doit agir.
        `False` si elle existait deja — l'appelant doit rendre sa reponse
        habituelle SANS refaire l'effet.

    Raises:
        MemoireIndisponible: si Redis ne repond pas. **On ne devine pas** : ni
            « premiere fois » -- qui laisserait passer un doublon -- ni « deja
            vue » -- qui refuserait une operation legitime. L'appelant tranche,
            et il le fait explicitement.
    """
    try:
        pose = _client(parametres).set(
            f"{PREFIXE_REDIS}{route}:{cle}", "1", nx=True, ex=SECONDES_DE_MEMOIRE
        )
    except (redis.RedisError, OSError) as erreur:
        message = f"memoire d'idempotence injoignable ({type(erreur).__name__})"
        raise MemoireIndisponible(message) from None
    return bool(pose)


def liberer(parametres: Parametres, *, route: str, cle: str) -> None:
    """Retirer une cle reservee.

    **APPELEE QUAND L'EFFET A ECHOUE**, et c'est ce qui rend le mecanisme
    utilisable : une cle reservee sur une operation qui a leve resterait sinon
    posee six heures, et un client qui recommence -- ce qu'on attend de lui apres
    une erreur -- serait refuse sans rien avoir obtenu.

    Elle est silencieuse sur echec : si Redis ne repond plus, la cle expirera
    d'elle-meme, et lever ici masquerait l'erreur d'origine.
    """
    try:
        _client(parametres).delete(f"{PREFIXE_REDIS}{route}:{cle}")
    except (redis.RedisError, OSError):
        return
