"""Les acteurs Dramatiq du LOT 11 — `T1`, stories `MVP-L11-US001`/`US002`/`US003`.

POURQUOI LES ACTEURS VIVENT ICI, ET LA LOGIQUE AILLEURS

  Ce module ne porte QUE le decorateur `@dramatiq.actor` et l'ouverture de la
  connexion PostgreSQL : c'est le worker qui possede le courtier et le cycle
  de vie des messages. Toute la logique testable sans Dramatiq — l'upsert
  idempotent d'un job, le relais de l'outbox — vit dans `app.jobs.*`
  (`apps/api`), importable et testee sans broker.

  Importer `app.jobs.*` depuis le worker est sans risque : l'image du worker
  embarque deja la source de `apps/api` (voir `apps/worker/Dockerfile`, qui la
  COPIE et la synchronise dans le MEME environnement `uv`), et
  `onboarding-api` est desormais une dependance explicite de
  `onboarding-worker` (voir `pyproject.toml`).

AUCUN RELAIS AUTO-PLANIFIE

  `relayer_l_outbox` traite UN LOT et s'arrete — il ne se reprogramme pas
  lui-meme. Un declenchement periodique appartient a `T4` (« tâches
  planifiées avec verrou », `scheduled_task_run`, modele §20.3), qui n'existe
  pas encore : en construire un ici, hors de toute tache planifiee reelle,
  serait inventer l'infrastructure du §6.5 avant la sous-etape qui la decide.
  D'ici la, c'est a qui ECRIT dans l'outbox de PROGRAMMER le relais — meme
  discipline que `BackgroundTasks` apres la reponse en `app.auth.routes`
  (LOT 3) : enfiler APRES que sa propre transaction a commite, jamais avant.
"""

from __future__ import annotations

import datetime as dt
import logging

import dramatiq

from app.configuration.settings import parametres_en_cache
from app.jobs.outbox import TAILLE_DE_LOT_PAR_DEFAUT, relayer_le_lot
from app.shared.database import moteur

journal = logging.getLogger("worker.jobs")


@dramatiq.actor(queue_name="default", max_retries=3)
def relayer_l_outbox(taille_de_lot: int = TAILLE_DE_LOT_PAR_DEFAUT) -> None:
    """Traiter jusqu'a `taille_de_lot` messages dus de `outbox_message`.

    Une seule transaction COURTE pour lire et verrouiller le lot
    (`FOR UPDATE SKIP LOCKED`), un SAVEPOINT par message — voir
    `app.jobs.outbox.relayer_le_lot`. Rejouer ce job (message Dramatiq repris
    apres un redemarrage du worker, ou enfile deux fois) ne duplique aucun
    envoi : `app.jobs.execution.commencer_un_essai` refuse de redemarrer un
    essai deja reussi.
    """
    parametres = parametres_en_cache()
    instant = dt.datetime.now(dt.UTC)
    with moteur(parametres).begin() as connexion:
        nombre_traites = relayer_le_lot(connexion, instant=instant, taille_de_lot=taille_de_lot)
    if nombre_traites:
        journal.info("relais de l'outbox", extra={"messages_traites": nombre_traites})
