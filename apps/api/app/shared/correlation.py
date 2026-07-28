"""Identifiant de correlation de requete.

LOT 1, sous-etape T3, story MVP-L01-US003.

Le cahier §18.3 exige un identifiant de correlation dans chaque reponse
d'erreur, et le §28.1 le veut dans chaque ligne de journal. Ce module fournit
le porteur ; la journalisation JSON qui le consomme arrive en T4
(`MVP-L01-US004`).

Le stockage passe par un `ContextVar` : chaque requete, y compris traitee dans
un fil du pool de FastAPI, voit sa propre valeur sans qu'aucune variable
globale ne soit partagee entre requetes concurrentes.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

# En-tete accepte en entree et renvoye en sortie. `X-Request-ID` est la
# convention la plus repandue, et Caddy comme les mandataires usuels la
# propagent sans configuration particuliere.
EN_TETE_CORRELATION = "X-Request-ID"

_correlation: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def definir_correlation(valeur: str | None) -> str:
    """Fixer l'identifiant de correlation de la requete courante.

    Une valeur fournie par l'appelant est reprise, ce qui permet de suivre une
    trace de bout en bout ; sinon un identifiant est engendre.
    """
    identifiant = (valeur or "").strip() or str(uuid.uuid4())
    _correlation.set(identifiant)
    return identifiant


def correlation_courante() -> str | None:
    """Identifiant de correlation de la requete courante, ou None hors requete."""
    return _correlation.get()
