"""Corrélation et journalisation des jobs Dramatiq.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT
    Critere litteral de la sous-etape : « chaque requete ET chaque job portent
    un correlation_id ». Le cahier §28.1 demande en outre la « route OU tache »,
    la duree, le resultat et le code d'erreur : cote worker, la tache tient la
    place de la route.

COMMENT LA TRACE FRANCHIT LA FRONTIERE API -> WORKER
    Un job n'herite de rien : il est deserialise dans un autre processus,
    souvent plus tard. L'identifiant de correlation doit donc VOYAGER AVEC LE
    MESSAGE.

    `before_enqueue` l'inscrit dans les options du message, cote emetteur.
    `before_process_message` le relit, cote worker, et le replace dans le
    contexte. Si le message n'en porte pas — job planifie, ou emis par un
    outil — un identifiant est engendre : aucun job ne s'execute sans trace.

    Au LOT 1, aucun acteur metier n'existe : l'API n'enfile rien. Le
    middleware est neanmoins pose et teste, parce que c'est la sous-etape qui
    possede la correlation, et que l'ajouter plus tard supposerait de se
    souvenir de le faire.

POURQUOI EFFACER L'IDENTIFIANT A LA FIN
    Un fil du pool du worker est reutilise. Laisser l'identifiant du job
    precedent ferait attribuer les lignes du suivant a la trace du premier —
    une correlation fausse est pire qu'une correlation absente, parce qu'on la
    croit.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from dramatiq import Middleware

from observabilite.correlation import (
    CLE_CORRELATION_MESSAGE,
    definir_correlation,
    effacer_correlation,
    engendrer,
)

journal = logging.getLogger("worker.job")

# Cle du chronometre, posee sur le message pendant son traitement.
_CLE_DEBUT = "_debut_monotone"


class CorrelationEtJournal(Middleware):
    """Attache un identifiant de correlation a chaque job, et le journalise."""

    def before_enqueue(self, broker: Any, message: Any, delay: int) -> None:
        """Inscrire l'identifiant courant dans les options du message.

        Cote emetteur. C'est ce qui permettra, au LOT 11, de relier un job a la
        requete HTTP qui l'a declenche.
        """
        del broker, delay
        from observabilite.correlation import correlation_courante

        existant = message.options.get(CLE_CORRELATION_MESSAGE)
        if not existant:
            message.options[CLE_CORRELATION_MESSAGE] = correlation_courante() or engendrer()

    def before_process_message(self, broker: Any, message: Any) -> None:
        """Replacer l'identifiant du message dans le contexte, et chronometrer."""
        del broker
        definir_correlation(message.options.get(CLE_CORRELATION_MESSAGE))
        message.options[_CLE_DEBUT] = time.monotonic()

    def after_process_message(
        self,
        broker: Any,
        message: Any,
        *,
        result: Any = None,
        exception: BaseException | None = None,
    ) -> None:
        """Emettre la ligne de journal du job, puis effacer l'identifiant."""
        del broker, result
        self._journaliser(message, exception=exception, motif=None)
        effacer_correlation()

    def after_skip_message(self, broker: Any, message: Any) -> None:
        """Journaliser un job ignore : un job qui disparait sans trace est une panne muette."""
        del broker
        self._journaliser(message, exception=None, motif="ignore")
        effacer_correlation()

    def _journaliser(
        self, message: Any, *, exception: BaseException | None, motif: str | None
    ) -> None:
        debut = message.options.get(_CLE_DEBUT)
        duree_ms = int((time.monotonic() - debut) * 1000) if debut else None

        if motif == "ignore":
            resultat, code_erreur, niveau = "ignore", "job_ignore", logging.WARNING
        elif exception is not None:
            resultat, code_erreur, niveau = "echec", type(exception).__name__, logging.ERROR
        else:
            resultat, code_erreur, niveau = "succes", None, logging.INFO

        journal.log(
            niveau,
            "job traite",
            extra={
                # `route` porte la tache cote worker : le cahier §28.1 demande
                # « route OU tache », un seul champ pour les deux.
                "route": f"{message.queue_name}/{message.actor_name}",
                "duree_ms": duree_ms,
                "resultat": resultat,
                "code_erreur": code_erreur,
                # Les ARGUMENTS DU JOB NE SONT PAS JOURNALISES. Ils peuvent
                # porter une adresse e-mail, un identifiant de personne, ou le
                # jeton d'un magic link (cahier §28.2). Seul leur NOMBRE est
                # utile au diagnostic.
                "nombre_arguments": len(message.args) + len(message.kwargs),
            },
        )
