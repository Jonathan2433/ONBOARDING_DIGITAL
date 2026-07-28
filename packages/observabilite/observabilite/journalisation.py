"""Journalisation JSON structuree.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT — cahier des charges §28.1, litteral
    « Logs JSON structures avec : date ; niveau ; service ; environnement ;
    version ; identifiant de correlation ; route ou tache ; duree ; resultat ;
    code d'erreur. »

    Les DIX champs sont TOUJOURS presents, meme a `null`. Un consommateur qui
    doit tester l'existence d'une cle avant de la lire finit par se tromper, et
    une requete d'agregation sur un champ absent une fois sur dix ne donne rien.

SORTIE SUR stdout, ET LA ROTATION N'EST PAS ICI
    Le processus ecrit sur la sortie standard. Il n'ouvre aucun fichier : dans
    un conteneur, c'est le pilote de journalisation de Docker qui collecte et
    qui applique la rotation et la limite de taille exigees par le §28.3. Ecrire
    dans un fichier a l'interieur du conteneur reviendrait a produire une donnee
    d'etat que `DEC-447` interdit de faire sortir par un bind mount, et que
    personne ne rotaterait.

    La configuration de la rotation est donc dans `docker-compose.base.yml`.

CE QUI N'EST PAS ENCORE COUVERT
    Le §28.3 demande aussi une conservation de 30 jours pour les logs
    techniques. Le pilote `json-file` de Docker borne par la TAILLE, pas par la
    duree : la conservation calendaire releve d'une collecte centralisee, qui
    appartient au LOT 13. `LOG_RETENTION_DAYS` porte l'intention et sera
    consommee la. Voir `QO-113`.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys
from typing import Any

from observabilite.correlation import correlation_courante
from observabilite.masquage import masquer

# Les dix champs du cahier §28.1, dans l'ordre ou le cahier les enumere. Le
# test `test_les_dix_champs_du_cahier_sont_toujours_presents` compare la sortie
# reelle a ce tuple : ajouter ou retirer un champ ici fait echouer le test.
CHAMPS_DU_CAHIER: tuple[str, ...] = (
    "date",
    "niveau",
    "service",
    "environnement",
    "version",
    "identifiant_correlation",
    "route",
    "duree_ms",
    "resultat",
    "code_erreur",
)

# Attributs propres a `logging.LogRecord`. Tout autre attribut a ete ajoute par
# l'appelant via `extra=` et rejoint le contexte du journal.
_ATTRIBUTS_STANDARDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "stacklevel",
        "thread",
        "threadName",
        "taskName",
    }
)


class FormateurJson(logging.Formatter):
    """Formateur produisant une ligne JSON conforme au cahier §28.1."""

    def __init__(self, *, service: str, environnement: str, version: str) -> None:
        super().__init__()
        self.service = service
        self.environnement = environnement
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        """Produire la ligne JSON. Les dix champs y sont toujours."""
        ligne: dict[str, Any] = {
            "date": dt.datetime.fromtimestamp(record.created, tz=dt.UTC).isoformat(
                timespec="milliseconds"
            ),
            "niveau": record.levelname.lower(),
            "service": self.service,
            "environnement": self.environnement,
            "version": self.version,
            "identifiant_correlation": getattr(record, "identifiant_correlation", None)
            or correlation_courante(),
            "route": getattr(record, "route", None),
            "duree_ms": getattr(record, "duree_ms", None),
            "resultat": getattr(record, "resultat", None),
            "code_erreur": getattr(record, "code_erreur", None),
        }

        # Le message est ajoute en plus des dix champs : il ne les remplace pas.
        ligne["message"] = masquer(record.getMessage())

        # Tout `extra=` supplementaire rejoint un sous-objet `contexte`, masque
        # comme le reste. Les champs du cahier sont exclus pour ne pas etre
        # dupliques.
        contexte = {
            cle: valeur
            for cle, valeur in record.__dict__.items()
            if cle not in _ATTRIBUTS_STANDARDS
            and cle not in CHAMPS_DU_CAHIER
            and not cle.startswith("_")
        }
        if contexte:
            ligne["contexte"] = masquer(contexte)

        if record.exc_info:
            # Le TYPE de l'exception, pas sa trace : une trace peut contenir des
            # valeurs de variables locales, donc des secrets. Le diagnostic se
            # fait par l'identifiant de correlation.
            type_exception = record.exc_info[0]
            ligne["exception"] = type_exception.__name__ if type_exception is not None else None

        # `masquer` est applique champ par champ ci-dessus ; ce second passage
        # couvre les valeurs des dix champs eux-memes, dont `route`, qui peut
        # porter une chaine de requete.
        return json.dumps(masquer(ligne), ensure_ascii=False, separators=(",", ":"))


def configurer_journalisation(
    *,
    service: str,
    environnement: str,
    version: str,
    niveau: str = "info",
    format_demande: str = "json",
) -> None:
    """Installer la journalisation JSON sur la racine.

    Args:
        service: `api` ou `worker`. Apparait dans chaque ligne.
        environnement: valeur d'`APP_ENV`.
        version: valeur d'`APP_VERSION`.
        niveau: valeur de `LOG_LEVEL`.
        format_demande: valeur de `LOG_FORMAT`. Seul `json` est accepte — le
            garde-fou de demarrage refuse deja toute autre valeur, ceci est la
            seconde barriere.

    Raises:
        ValueError: si `format_demande` n'est pas `json`.
    """
    if format_demande != "json":
        message = (
            f"LOG_FORMAT doit valoir json, recu '{format_demande}' "
            "(cahier §28.1). Aucun format alternatif n'est prevu."
        )
        raise ValueError(message)

    formateur = FormateurJson(service=service, environnement=environnement, version=version)

    # stdout et non stderr : les deux flux sont collectes par Docker, mais tout
    # envoyer sur stdout evite qu'un agregateur classe des lignes `info` en
    # erreurs sur le seul critere du flux.
    poignee = logging.StreamHandler(sys.stdout)
    poignee.setFormatter(formateur)

    racine = logging.getLogger()
    # Les poignees existantes sont retirees : uvicorn et dramatiq installent les
    # leurs, en texte. Les laisser produirait deux formats melanges dans le meme
    # flux, et le §28.1 n'en admet qu'un.
    for existante in list(racine.handlers):
        racine.removeHandler(existante)
    racine.addHandler(poignee)
    racine.setLevel(niveau.upper())

    # uvicorn et dramatiq propagent alors vers la racine au lieu d'ecrire
    # directement.
    for nom in ("uvicorn", "uvicorn.error", "uvicorn.access", "dramatiq"):
        journal = logging.getLogger(nom)
        journal.handlers.clear()
        journal.propagate = True

    # LE JOURNAL D'ACCES D'UVICORN EST REDUIT AUX AVERTISSEMENTS.
    #
    # Trois raisons, mesurees sur les journaux reels de la stack :
    #   1. il double chaque ligne du middleware applicatif, qui porte deja la
    #      route de gabarit, la duree, le resultat et le code d'erreur — le
    #      §28.1 demande ces champs, la ligne d'uvicorn n'en a aucun ;
    #   2. il journalise les sondes de sante interrogees toutes les dix
    #      secondes par Docker : 8 640 lignes par jour et par service, sans
    #      aucune valeur de diagnostic ;
    #   3. il ecrit le chemin BRUT, chaine de requete comprise. Un magic link du
    #      LOT 3 y passerait, ce que le §28.2 interdit.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # BIBLIOTHEQUES BAVARDES, REDUITES AUX AVERTISSEMENTS.
    #
    # httpx journalise chaque requete sortante avec son URL COMPLETE, chaine de
    # requete comprise. Un magic link du LOT 3 y passerait, ce que le §28.2
    # interdit. Sa ligne duplique par ailleurs notre propre journal de requete.
    # botocore et urllib3 sont reduits pour la meme raison : leurs URL signees
    # portent des parametres d'authentification.
    for nom in ("httpx", "httpcore", "botocore", "boto3", "urllib3", "s3transfer"):
        logging.getLogger(nom).setLevel(logging.WARNING)
