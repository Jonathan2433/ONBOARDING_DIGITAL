"""Squelette du paquet applicatif du worker.

LOT 1, sous-etape T1, story MVP-L01-US001.

Ce paquet est volontairement vide de tout code applicatif. Le demarrage
Dramatiq et la declaration des sept files validees relevent de T3 et T4. La
persistance des jobs en PostgreSQL, l'outbox transactionnelle et
l'idempotence relevent du LOT 11, qui n'est pas ouvert.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
