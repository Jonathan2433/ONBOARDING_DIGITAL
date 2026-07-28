"""Verification effective des dependances de l'API.

LOT 1, sous-etape T3, story MVP-L01-US003.

Critere litteral du backlog : « readiness verifie les dependances
necessaires ». Chaque sonde ci-dessous fait donc un ALLER-RETOUR REEL avec le
service — une requete SQL, un PING Redis, un appel S3 sur le bucket. Aucune ne
se contente d'ouvrir une connexion TCP : un port ouvert ne prouve pas qu'un
service repond, et une sonde qui ne peut pas echouer ne prouve rien.

Les trois dependances verifiees sont celles que la fiche du LOT 1 nomme pour
`T3` : PostgreSQL, Redis et MinIO. Mailpit n'en fait pas partie — l'API ne
depend pas de l'envoi d'e-mails pour servir une requete, et le rendre bloquant
ferait tomber l'API pour une panne de messagerie.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable

import boto3
import redis
from botocore.config import Config as ConfigBoto
from botocore.exceptions import BotoCoreError, ClientError

from app.configuration.settings import Parametres
from app.shared.database import verifier_connexion

# Delai au-dela duquel une dependance est declaree indisponible. Court
# volontairement : `ready` est interroge par l'orchestrateur, il ne doit pas
# rester suspendu sur un service muet.
DELAI_SONDE_SECONDES = 3


@dataclasses.dataclass(frozen=True)
class ResultatSonde:
    """Resultat d'une sonde de dependance."""

    nom: str
    disponible: bool
    duree_ms: int
    motif: str | None = None


def _mesurer(nom: str, sonde: Callable[[], None]) -> ResultatSonde:
    """Executer une sonde en capturant son echec et sa duree.

    Le motif retourne est le TYPE de l'exception, jamais son message : un
    message d'erreur de pilote peut contenir un identifiant de connexion, un
    nom d'utilisateur ou une URL avec mot de passe. `/health/ready` est
    interrogeable sans authentification.
    """
    debut = time.monotonic()
    try:
        sonde()
    except Exception as erreur:  # toute panne, quelle qu'elle soit, rend indisponible
        return ResultatSonde(
            nom=nom,
            disponible=False,
            duree_ms=int((time.monotonic() - debut) * 1000),
            motif=type(erreur).__name__,
        )
    return ResultatSonde(
        nom=nom,
        disponible=True,
        duree_ms=int((time.monotonic() - debut) * 1000),
    )


def sonder_postgresql(parametres: Parametres) -> ResultatSonde:
    """Executer `SELECT 1` sur PostgreSQL."""
    return _mesurer("postgresql", lambda: verifier_connexion(parametres))


def sonder_redis(parametres: Parametres) -> ResultatSonde:
    """Envoyer un PING a Redis."""

    def sonde() -> None:
        client = redis.Redis.from_url(
            parametres.url_redis(),
            socket_connect_timeout=DELAI_SONDE_SECONDES,
            socket_timeout=DELAI_SONDE_SECONDES,
        )
        try:
            if not client.ping():
                message = "Redis n'a pas repondu PONG"
                raise RuntimeError(message)
        finally:
            client.close()

    return _mesurer("redis", sonde)


def sonder_minio(parametres: Parametres) -> ResultatSonde:
    """Interroger le bucket configure par un appel S3 `head_bucket`.

    `head_bucket` et non une simple connexion : il eprouve a la fois la
    joignabilite du service, la validite des identifiants ET l'existence du
    bucket. Les trois sont necessaires pour que l'API puisse servir un media.
    """

    def sonde() -> None:
        client = boto3.client(
            "s3",
            endpoint_url=parametres.url_minio(),
            aws_access_key_id=parametres.MINIO_ROOT_USER,
            aws_secret_access_key=parametres.MINIO_ROOT_PASSWORD,
            region_name=parametres.MINIO_REGION,
            config=ConfigBoto(
                connect_timeout=DELAI_SONDE_SECONDES,
                read_timeout=DELAI_SONDE_SECONDES,
                retries={"max_attempts": 1},
            ),
        )
        try:
            client.head_bucket(Bucket=parametres.MINIO_BUCKET)
        except (BotoCoreError, ClientError) as erreur:
            raise RuntimeError("bucket injoignable") from erreur

    return _mesurer("minio", sonde)


def sonder_toutes(parametres: Parametres) -> list[ResultatSonde]:
    """Sonder les trois dependances necessaires a l'API."""
    return [
        sonder_postgresql(parametres),
        sonder_redis(parametres),
        sonder_minio(parametres),
    ]
