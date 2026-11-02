"""L'orchestrateur d'un cycle de taches planifiees — `T4`.

UNE TRANSACTION PAR CYCLE, UNE SAVEPOINT PAR TACHE

  Meme patron que `app.jobs.outbox.relayer_le_lot` et `app.imports.execution`
  (§7.27) : l'appelant (l'acteur Dramatiq) ouvre UNE transaction pour tout le
  cycle, et cette fonction isole chaque tache dans sa PROPRE savepoint. Une
  tache qui echoue n'annule ni les precedentes ni les suivantes du MEME cycle.

  Un echec AVANT la fin du cycle (le worker est tue, par exemple) annule tout
  le cycle non commite -- le suivant arrive de toute facon dans
  `SCHEDULED_TASKS_INTERVAL_MINUTES`, et chaque tache est idempotente par
  construction (voir `app.scheduling.taches`).

LE VERROU EST DEJA DANS `commencer_l_execution` : CETTE FONCTION NE FAIT QUE
LE RESPECTER

  `TacheDejaEnCours` signale qu'une AUTRE execution de cette tache est en
  cours (un worker concurrent, ou un cycle precedent anormalement long) : le
  cycle courant saute cette tache sans qu'aucune donnee ne soit touchee.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import TYPE_CHECKING, Final

from app.scheduling import taches
from app.scheduling.execution import (
    TacheDejaEnCours,
    commencer_l_execution,
    terminer_avec_succes,
    terminer_en_echec,
)
from app.scheduling.modeles import NOMS_DE_TACHE_PLANIFIEE
from app.scheduling.supervision import envoyer_le_battement

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

#  Chaque tache porte la MEME signature : `(connexion, *, instant, parametres) -> int`.
EXECUTER_LA_TACHE: Final = {
    "expiration_liens_sessions": taches.expirer_les_liens_et_sessions,
    "evenements_passes": taches.confirmer_les_evenements_passes,
    "anonymisation_apres_depart": taches.anonymiser_apres_depart,
    "purge_audit": taches.purger_l_audit,
    "detection_jobs_bloques": taches.detecter_les_jobs_bloques,
    "nettoyage_medias": taches.nettoyer_les_medias,
}

#  Garde-fou de coherence : un septieme nom ajoute a l'enumeration sans son
#  executeur ici romprait silencieusement le cycle sur cette seule tache.
assert set(EXECUTER_LA_TACHE) == set(NOMS_DE_TACHE_PLANIFIEE)  # noqa: S101


@dataclasses.dataclass(frozen=True, slots=True)
class ResultatDUneTache:
    """Ce qu'un cycle a fait d'une tache precise."""

    task_name: str
    #  `None` : la tache a ete sautee, une autre execution etait en cours.
    etat: str | None
    items_processed: int | None
    error_message: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class ResultatDuCycle:
    """Le resume d'un cycle complet, pour le journal et la supervision."""

    taches: tuple[ResultatDUneTache, ...]

    @property
    def nombre_d_echecs(self) -> int:
        return sum(1 for t in self.taches if t.etat == "failed")


def executer_le_cycle(
    connexion: Connection, *, instant: dt.datetime, parametres: Parametres
) -> ResultatDuCycle:
    """Executer les six taches planifiees, chacune dans sa propre savepoint."""
    resultats: list[ResultatDUneTache] = []

    for nom in NOMS_DE_TACHE_PLANIFIEE:
        try:
            ligne = commencer_l_execution(connexion, task_name=nom, instant=instant)
        except TacheDejaEnCours:
            resultats.append(
                ResultatDUneTache(
                    task_name=nom, etat=None, items_processed=None, error_message=None
                )
            )
            continue

        savepoint = connexion.begin_nested()
        try:
            nombre = EXECUTER_LA_TACHE[nom](connexion, instant=instant, parametres=parametres)
        except Exception as erreur:  # toute erreur doit etre consignee, jamais remonter
            savepoint.rollback()
            ligne_finale = terminer_en_echec(
                connexion, ligne.id, instant=instant, error_message=str(erreur)[:500]
            )
            resultats.append(
                ResultatDUneTache(
                    task_name=nom,
                    etat=ligne_finale.state,
                    items_processed=None,
                    error_message=ligne_finale.error_message,
                )
            )
        else:
            savepoint.commit()
            ligne_finale = terminer_avec_succes(
                connexion, ligne.id, instant=instant, items_processed=nombre
            )
            resultats.append(
                ResultatDUneTache(
                    task_name=nom,
                    etat=ligne_finale.state,
                    items_processed=ligne_finale.items_processed,
                    error_message=None,
                )
            )

    resultat = ResultatDuCycle(taches=tuple(resultats))
    envoyer_le_battement(
        parametres,
        etat_sain=resultat.nombre_d_echecs == 0,
        message=f"{resultat.nombre_d_echecs} echec(s) sur {len(resultat.taches)} taches",
    )
    return resultat
