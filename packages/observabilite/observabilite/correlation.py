"""Identifiant de correlation, partage par l'API et le worker.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT
    Cahier §18.3 : chaque reponse d'erreur porte un identifiant de correlation.
    Cahier §28.1 : chaque ligne de journal aussi.

    Le critere de `T4` est litteral : « chaque requete ET chaque job portent un
    correlation_id ». Il doit donc traverser la frontiere entre l'API et le
    worker, ce qui suppose un porteur commun aux deux — d'ou ce module dans le
    paquet partage plutot que dans `apps/api/app/shared/`, ou il vivait a `T3`.

Le stockage passe par un `ContextVar` : chaque requete, et chaque job traite
dans un fil du worker, voit sa propre valeur sans qu'aucune variable globale ne
soit partagee entre traitements concurrents.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

# En-tete accepte en entree et renvoye en sortie. `X-Request-ID` est la
# convention la plus repandue, et Caddy la propage sans configuration
# particuliere — verifie de bout en bout en `T3`.
EN_TETE_CORRELATION = "X-Request-ID"

# Cle portant l'identifiant dans les metadonnees d'un message Dramatiq. C'est
# elle qui fait franchir la frontiere API -> worker : sans elle, un job
# declenche par une requete perdrait la trace de son origine.
CLE_CORRELATION_MESSAGE = "correlation_id"

_correlation: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def engendrer() -> str:
    """Produire un identifiant de correlation neuf."""
    return str(uuid.uuid4())


def definir_correlation(valeur: str | None) -> str:
    """Fixer l'identifiant de correlation du traitement courant.

    Une valeur fournie par l'appelant est reprise, ce qui permet de suivre une
    trace de bout en bout a travers plusieurs services ; sinon un identifiant
    est engendre. Aucune requete, aucun job ne doit s'executer sans.
    """
    identifiant = (valeur or "").strip() or engendrer()
    _correlation.set(identifiant)
    return identifiant


def correlation_courante() -> str | None:
    """Identifiant du traitement courant, ou None hors requete et hors job."""
    return _correlation.get()


def effacer_correlation() -> None:
    """Retirer l'identifiant courant.

    Utile a la fin d'un job : un fil du pool du worker est reutilise, et laisser
    l'identifiant du job precedent ferait attribuer ses journaux au suivant.
    """
    _correlation.set(None)
