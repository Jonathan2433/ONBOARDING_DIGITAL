"""Demarrer la boucle des taches planifiees — LOT 11, `T4`.

POURQUOI UN MIDDLEWARE, ET PAS UN APPEL A L'IMPORT DE `worker.main`

  `worker.main` est importe par CHAQUE test qui lit `FILES_PAR_DEFAUT` ou
  `url_redis()` (`apps/worker/tests/test_squelette_worker.py`, LOT 1). Un envoi
  Dramatiq a l'import tenterait une connexion Redis a CHAQUE collecte de test,
  et casserait `test_aucun_acteur_metier_n_est_declare` en y ajoutant un effet
  de bord que ce test ne nomme pas.

  `after_worker_boot(broker, worker)` est un crochet du cycle de vie du
  `Worker` Dramatiq LUI-MEME (la boucle de consommation reelle), jamais
  invoque par une simple importation de module. C'est exactement le moment ou
  la boucle de planification doit demarrer : une fois, par PROCESSUS worker
  reel, jamais pendant une collecte de test.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import dramatiq

if TYPE_CHECKING:  # pragma: no cover
    from dramatiq import Broker, Worker

journal = logging.getLogger("worker.amorcage")


class DemarrerLaPlanification(dramatiq.Middleware):
    """Envoie le premier message du cycle planifie, une fois le worker demarre."""

    def after_worker_boot(self, broker: Broker, worker: Worker) -> None:
        #  Import DIFFERE : `worker.actors` importe ce module via `worker.main`
        #  AVANT que les acteurs n'existent (voir l'ordre d'import de
        #  `worker.main`). Au moment ou `after_worker_boot` s'execute
        #  reellement, les acteurs sont deja enregistres.
        from worker.actors import executer_le_cycle_planifie

        journal.info("demarrage de la boucle des taches planifiees")
        executer_le_cycle_planifie.send()
