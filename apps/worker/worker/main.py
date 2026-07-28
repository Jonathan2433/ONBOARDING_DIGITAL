"""Amorcage du worker Dramatiq.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §16.4 : Dramatiq et Redis gerent sept files —
`default`, `emails`, `imports`, `media`, `exports`, `maintenance`, `security`.

CE QUE CE MODULE FAIT AU LOT 1
    Il declare le courtier Redis et les sept files, et rien de plus. Le worker
    demarre, se connecte, et attend. C'est ce qu'`ARB-ROAD-002` appelle amorcer.

CE QU'IL NE FAIT PAS, ET QUI N'APPARTIENT PAS A CE LOT
    La persistance des jobs en PostgreSQL, l'outbox transactionnelle,
    l'idempotence, le rejeu sans duplication et les taches planifiees relevent
    du **LOT 11** (`MVP-L11-US001`, `US002`). Aucun acteur metier n'est declare
    ici : il n'existe aucun metier avant le LOT 2.
"""

from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker

# Les sept files du cahier §16.4. La liste est lue dans l'environnement pour
# rester alignee sur `.env.example`, mais l'ordre et le contenu par defaut sont
# ceux du cahier : une file oubliee ferait disparaitre des messages en silence.
FILES_PAR_DEFAUT = (
    "default",
    "emails",
    "imports",
    "media",
    "exports",
    "maintenance",
    "security",
)


def files_declarees() -> tuple[str, ...]:
    """Files a servir, depuis DRAMATIQ_QUEUES, defaut du cahier §16.4."""
    brut = os.environ.get("DRAMATIQ_QUEUES", "").strip()
    if not brut:
        return FILES_PAR_DEFAUT
    files = tuple(f.strip() for f in brut.split(",") if f.strip())
    return files or FILES_PAR_DEFAUT


def url_redis() -> str:
    """URL du courtier Redis, construite depuis l'environnement."""
    hote = os.environ.get("REDIS_HOST", "redis")
    port = os.environ.get("REDIS_PORT", "6379")
    mot_de_passe = os.environ.get("REDIS_PASSWORD", "")
    return f"redis://:{mot_de_passe}@{hote}:{port}/0"


def creer_courtier() -> RedisBroker:
    """Declarer le courtier Redis et ses sept files."""
    courtier = RedisBroker(url=url_redis())
    for file in files_declarees():
        courtier.declare_queue(file)
    return courtier


courtier = creer_courtier()
dramatiq.set_broker(courtier)
