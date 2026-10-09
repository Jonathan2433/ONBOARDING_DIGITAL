"""Lire ET deposer un objet MinIO — LOT 5 `T5` pour la lecture, LOT 9 `T6` pour le depot.

CE MODULE EXISTE POUR NE PAS DUPLIQUER LA CONSTRUCTION DU CLIENT

  `app/health/dependances.py` construisait deja un client S3, pour son
  `head_bucket`. Deux constructions divergeraient au premier reglage change --
  un delai, une region, un identifiant -- et la divergence serait silencieuse :
  la sonde de sante dirait « MinIO joignable » pendant que la lecture echouerait.

  Les REGLAGES sont donc ici, en une source ; la sonde garde son propre delai,
  qui est court a dessein -- une sonde de sante ne doit pas attendre.

POURQUOI L'API SERT LES OCTETS, ET NON UNE URL SIGNEE

  **Le corpus ne dit pas comment un media parvient au navigateur.** Mesure du
  06/09/2026 : zero occurrence d'« URL signee », de « presigned » ou de CDN pour
  les medias, et le §16.1 dit seulement « objets MinIO references par
  `object_key`, jamais Base64 ».

  Servir les octets par notre API est la seule option qui n'invente rien :

    une URL signee vers MinIO   exposerait le port 9000 au navigateur, or
                                `DEC-460` publie tout sur `127.0.0.1` seulement,
                                et `DEC-470` pose UNE seule origine sans CORS
    l'`object_key` en clair     exposerait la disposition du stockage, et le
                                navigateur ne pourrait rien en faire
    les octets par l'API        une origine, un cookie de session, aucun reglage
                                nouveau -- et `boto3` est deja une dependance

  Le choix reste **reversible** : le jour ou le LOT 11 voudra des URL signees, le
  chemin de la route ne change pas, seul son corps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import boto3
from botocore.config import Config as ConfigBoto
from botocore.exceptions import BotoCoreError, ClientError

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

#  Plus genereux que le delai de la sonde de sante : celle-ci doit rendre son
#  verdict vite, une lecture de miniature a le droit d'attendre un peu.
DELAI_LECTURE_SECONDES: Final[int] = 5


class ObjetIntrouvable(RuntimeError):
    """L'objet n'est pas dans le bucket, ou MinIO ne repond pas.

    **UNE SEULE EXCEPTION POUR LES DEUX CAUSES, ET C'EST DELIBERE COTE APPELANT** :
    la route rend le meme refus dans les deux cas. Distinguer « la miniature a
    disparu du stockage » de « MinIO est en panne » n'apporte rien a un
    navigateur, et le journal porte deja la cause pour l'exploitant.
    """


class ObjetNonDepose(RuntimeError):
    """Le depot a echoue — MinIO ne repond pas, ou refuse l'ecriture.

    **MEME DISCIPLINE QUE `ObjetIntrouvable`** : une seule exception pour les
    deux causes, le journal portant la vraie cause pour l'exploitant.
    """


def client_s3(parametres: Parametres) -> object:
    """Le client S3 de lecture, construit avec les reglages du depot."""
    return boto3.client(
        "s3",
        endpoint_url=parametres.url_minio(),
        aws_access_key_id=parametres.MINIO_ROOT_USER,
        aws_secret_access_key=parametres.MINIO_ROOT_PASSWORD,
        region_name=parametres.MINIO_REGION,
        config=ConfigBoto(
            connect_timeout=DELAI_LECTURE_SECONDES,
            read_timeout=DELAI_LECTURE_SECONDES,
            retries={"max_attempts": 1},
        ),
    )


def lire_l_objet(parametres: Parametres, cle: str) -> bytes:
    """Les octets de l'objet, ou `ObjetIntrouvable`.

    **LA CLE NE VIENT JAMAIS DU CLIENT**, et c'est le §16.1 : « aucun `object_key`
    fourni par le client ». Elle est lue en base par
    `app/media/photo.py`, qui ne selectionne que celle d'une variante.
    """
    client = client_s3(parametres)
    try:
        reponse = client.get_object(Bucket=parametres.MINIO_BUCKET, Key=cle)  # type: ignore[attr-defined]
        corps: bytes = reponse["Body"].read()
    except (ClientError, BotoCoreError) as erreur:
        message = f"objet illisible : {type(erreur).__name__}"
        raise ObjetIntrouvable(message) from erreur
    return corps


def deposer_l_objet(parametres: Parametres, cle: str, contenu: bytes) -> None:
    """Deposer des octets dans le bucket — LA PREMIERE ECRITURE MinIO DU PROJET.

    **CE MODULE N'AVAIT JAMAIS ECRIT, SEULEMENT LU, JUSQU'AU LOT 9 `T6`.**
    Mesure avant d'ecrire une ligne : zero occurrence de `put_object` hors des
    tests, dans tout le depot — chaque media du jeu de donnees ou des decors
    de test est pose directement par `boto3`, jamais par l'API elle-meme.
    `T6` sert le depot securise d'un CSV (cahier §19.1) et en a besoin pour de
    vrai, la premiere fois qu'une route ecrit dans le bucket.

    **LE CLIENT EST RECONSTRUIT PAR `client_s3`, JAMAIS UN SECOND**, pour la
    meme raison que la lecture : une seconde construction divergerait au
    premier reglage change, silencieusement.
    """
    client = client_s3(parametres)
    try:
        client.put_object(  # type: ignore[attr-defined]
            Bucket=parametres.MINIO_BUCKET, Key=cle, Body=contenu
        )
    except (ClientError, BotoCoreError) as erreur:
        message = f"depot impossible : {type(erreur).__name__}"
        raise ObjetNonDepose(message) from erreur
