"""Les acteurs Dramatiq du LOT 11 — `T1` et `T4`.

POURQUOI LES ACTEURS VIVENT ICI, ET LA LOGIQUE AILLEURS

  Ce module ne porte QUE le decorateur `@dramatiq.actor` et l'ouverture de la
  connexion PostgreSQL : c'est le worker qui possede le courtier et le cycle
  de vie des messages. Toute la logique testable sans Dramatiq — l'upsert
  idempotent d'un job, le relais de l'outbox, l'orchestration des taches
  planifiees — vit dans `app.jobs.*`/`app.scheduling.*` (`apps/api`),
  importable et testee sans broker.

  Importer `app.jobs.*`/`app.scheduling.*` depuis le worker est sans risque :
  l'image du worker embarque deja la source de `apps/api` (voir
  `apps/worker/Dockerfile`, qui la COPIE et la synchronise dans le MEME
  environnement `uv`), et `onboarding-api` est desormais une dependance
  explicite de `onboarding-worker` (voir `pyproject.toml`).

`relayer_l_outbox` RESTE SANS RELAIS AUTO-PLANIFIE

  Elle traite UN LOT et s'arrete — c'est a qui ECRIT dans l'outbox de
  PROGRAMMER le relais (`BackgroundTasks` apres la reponse HTTP, LOT 3). Rien
  ne change ici : voir `app.media.routes` pour ce mecanisme.

`executer_le_cycle_planifie` S'AUTO-REPLANIFIE, ET C'EST LA PREMIERE FOIS

  §20.3 demande une EXECUTION PERIODIQUE, pas declenchee par un ecrivain —
  aucun outil de planification (type `cron`, `dramatiq-crontab`) n'est une
  dependance de ce depot, et en ajouter un pour cette seule tache serait plus
  qu'un GET pousse vers Uptime Kuma. Le mecanisme retenu est celui que
  Dramatiq offre deja NATIVEMENT : `send_with_options(delay=...)`, que
  `RedisBroker.enqueue` sait honorer sans middleware supplementaire (mesure
  dans la bibliotheque elle-meme avant de l'employer). L'acteur se renvoie
  donc LUI-MEME, `SCHEDULED_TASKS_INTERVAL_MINUTES` plus tard, **dans un
  `finally`** : un cycle qui echoue ne doit jamais interrompre la boucle, sous
  peine de perdre toute supervision silencieusement.

  Le PREMIER envoi — qui demarre la boucle — ne vient PAS de l'import de ce
  module (cela romprait `test_aucun_acteur_metier_n_est_declare` du LOT 1 ET
  tenterait une connexion Redis a chaque simple `import worker.main` dans les
  tests). Il vient du middleware `DemarrerLaPlanification`
  (`worker.amorcage`), sur le crochet `after_worker_boot` de Dramatiq — invoque
  par le PROCESSUS worker reel, jamais par une importation de test.
"""

from __future__ import annotations

import datetime as dt
import logging

import dramatiq

from app.configuration.settings import parametres_en_cache
from app.jobs.outbox import TAILLE_DE_LOT_PAR_DEFAUT, relayer_le_lot
from app.scheduling.orchestrateur import executer_le_cycle
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


@dramatiq.actor(queue_name="maintenance", max_retries=0)
def executer_le_cycle_planifie() -> None:
    """Un cycle des six taches planifiees, puis se reprogrammer soi-meme.

    `max_retries=0` : une reprise Dramatiq dupliquerait un cycle qui va de
    toute facon se representer dans `SCHEDULED_TASKS_INTERVAL_MINUTES` — les
    echecs INDIVIDUELS de chaque tache sont deja consignes dans
    `scheduled_task_run.error_message` par `executer_le_cycle` lui-meme, ce
    n'est jamais a Dramatiq de les rattraper.
    """
    parametres = parametres_en_cache()
    try:
        instant = dt.datetime.now(dt.UTC)
        with moteur(parametres).begin() as connexion:
            resultat = executer_le_cycle(connexion, instant=instant, parametres=parametres)
        if resultat.nombre_d_echecs:
            journal.warning(
                "cycle de taches planifiees avec echecs",
                extra={"echecs": resultat.nombre_d_echecs, "taches": len(resultat.taches)},
            )
    except Exception:
        journal.exception("cycle de taches planifiees : echec inattendu")
    finally:
        executer_le_cycle_planifie.send_with_options(
            delay=dt.timedelta(minutes=parametres.SCHEDULED_TASKS_INTERVAL_MINUTES)
        )
