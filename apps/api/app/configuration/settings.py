"""Configuration de l'API et garde-fous de demarrage.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT
    Cahier des charges §20.3 : configuration par variables d'environnement,
    `.env` local non versionne, validation au demarrage, et refus de demarrer
    en production lorsqu'un secret est absent ou qu'une option de
    developpement est active.

    Les onze garde-fous sont enumeres dans
    `docs/operations/politique-configuration-et-secrets.md` §6 : QUATRE
    s'appliquent a tous les environnements, SEPT uniquement lorsque
    `APP_ENV=production`.

REGLE ABSOLUE SUR LES MESSAGES D'ERREUR
    Le message nomme la variable fautive et **n'affiche JAMAIS sa valeur**.
    Un message de configuration finit dans un journal, une capture d'ecran ou
    un ticket : y laisser fuir un secret annulerait l'interet du garde-fou.
    Le test `test_aucun_message_ne_divulgue_une_valeur` l'eprouve.

PORTEE DU GARDE-FOU « AUCUN CHANGE_ME RESIDUEL »
    Il porte sur les variables que l'API DECLARE ci-dessous, non sur toutes
    celles de `.env.example`. Deux variables y restent volontairement en
    `CHANGE_ME` : `IMPORT_SOURCE_RETENTION_DAYS`, dont la valeur releve de
    `QO-100` et qui appartient au LOT 9, et `UPTIME_KUMA_PUSH_URL`, qui
    appartient au LOT 13. Aucune n'est utilisee par l'API aujourd'hui, donc
    aucune ne figure dans ce modele. Le jour ou le LOT 9 ajoutera la premiere
    a sa configuration, `QO-100` devra etre tranchee : c'est precisement
    l'effet recherche.
"""

from __future__ import annotations

import functools
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

Environnement = Literal["development", "recette", "production"]

# Longueur minimale de la cle de signature en production. Le cahier exige une
# cle « suffisamment longue » sans donner de seuil : 32 caracteres est le
# plancher usuel pour une cle de 256 bits encodee.
LONGUEUR_MINIMALE_CLE = 32

MARQUEUR_NON_RENSEIGNE = "CHANGE_ME"


class ConfigurationInvalide(RuntimeError):
    """La configuration ne permet pas de demarrer.

    Porte la liste des manquements, chacun nommant la variable fautive sans
    jamais exposer sa valeur.
    """

    def __init__(self, manquements: list[str]) -> None:
        self.manquements = manquements
        detail = "\n".join(f"  - {m}" for m in manquements)
        super().__init__(
            f"Demarrage refuse : {len(manquements)} garde-fou(s) de configuration "
            f"en echec.\n{detail}"
        )


class Parametres(BaseSettings):
    """Configuration de l'API, lue depuis l'environnement.

    Seules les variables reellement utilisees par l'API a ce stade sont
    declarees. En ajouter une qui ne sert pas encore donnerait l'illusion
    qu'elle est validee.
    """

    model_config = SettingsConfigDict(
        env_file=None,  # Le conteneur recoit ses variables par l'environnement.
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    APP_ENV: Environnement = "development"
    APP_VERSION: str = "0.0.0-dev"
    APP_REVISION: str = "inconnue"
    APP_SECRET_KEY: str = ""
    PUBLIC_BASE_URL: str = "https://localhost"
    API_DOCS_ENABLED: bool = True
    API_PREFIX: str = "/api/v1"

    # --- Journalisation (cahier §28.1) --------------------------------------
    LOG_FORMAT: str = "json"
    LOG_LEVEL: str = "info"

    # --- PostgreSQL ----------------------------------------------------------
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    #  MOINDRE PRIVILEGE — LOT 3, T1, `QO-116`, `DEC-518`.
    #
    #  `POSTGRES_USER` est le compte que cree `initdb` : il est SUPERUTILISATEUR
    #  et proprietaire du cluster. Rien ne peut l'empecher d'exister, et le
    #  pretendre serait pire que le nommer. Ce qui change au LOT 3, c'est que
    #  **l'application ne l'emploie plus** : il ne sert qu'a l'initialisation du
    #  cluster et a l'approvisionnement des deux roles ci-dessous.
    #
    #  DEUX ROLES, ET LEUR SEPARATION EST LE POINT :
    #    - MIGRATIONS possede les objets du schema et peut les modifier. Alembic
    #      l'emploie, et lui seul ;
    #    - RUNTIME ne peut que lire et ecrire des LIGNES. L'API et le worker
    #      l'emploient. Il ne peut ni creer, ni supprimer, ni modifier une table,
    #      et un temoin l'exige.
    POSTGRES_MIGRATIONS_USER: str = ""
    POSTGRES_MIGRATIONS_PASSWORD: str = ""
    POSTGRES_RUNTIME_USER: str = ""
    POSTGRES_RUNTIME_PASSWORD: str = ""
    DB_AUTO_CREATE: bool = False

    # --- Redis ---------------------------------------------------------------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # --- MinIO ---------------------------------------------------------------
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = ""
    MINIO_ROOT_PASSWORD: str = ""
    MINIO_BUCKET: str = ""
    MINIO_REGION: str = "eu-west-1"
    MINIO_USE_SSL: bool = False

    # --- E-mail (cahier §16.5) ----------------------------------------------
    EMAIL_PROVIDER: str = "mailpit"
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025

    # --- Securite (cahier §7.4, §20.1) --------------------------------------
    SESSION_COOKIE_SECURE: bool = True
    CSRF_PROTECTION_ENABLED: bool = True

    # --- Variables obligatoires dans TOUS les environnements ----------------
    # Sans elles, l'API ne peut ni joindre sa base, ni son cache, ni son
    # stockage objet : demarrer serait demarrer pour echouer a la premiere
    # requete.
    OBLIGATOIRES: tuple[str, ...] = Field(
        default=(
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            #  LOT 3, T1 : sans elles, l'API tenterait de se connecter avec un
            #  utilisateur vide et echouerait a la premiere requete. Les declarer
            #  obligatoires les fait echouer au DEMARRAGE, en les NOMMANT.
            "POSTGRES_RUNTIME_USER",
            "POSTGRES_RUNTIME_PASSWORD",
            "POSTGRES_MIGRATIONS_USER",
            "POSTGRES_MIGRATIONS_PASSWORD",
            "REDIS_PASSWORD",
            "MINIO_ROOT_USER",
            "MINIO_ROOT_PASSWORD",
            "MINIO_BUCKET",
        ),
        exclude=True,
    )

    # ------------------------------------------------------------------------
    #  Les onze garde-fous
    # ------------------------------------------------------------------------

    def controler(self) -> list[str]:
        """Retourner la liste des manquements. Vide si la configuration passe."""
        manquements: list[str] = []
        manquements += self._controles_universels()
        if self.APP_ENV == "production":
            manquements += self._controles_production()
        return manquements

    def _controles_universels(self) -> list[str]:
        """Les quatre controles applicables a tous les environnements."""
        manquements: list[str] = []

        # 1 — toute variable obligatoire est presente
        for nom in self.OBLIGATOIRES:
            valeur = getattr(self, nom)
            if not str(valeur).strip():
                manquements.append(f"{nom} : variable obligatoire absente ou vide")

        # 2 — aucune variable ne vaut encore CHANGE_ME_*
        for nom in type(self).model_fields:
            if nom == "OBLIGATOIRES":
                continue
            valeur = getattr(self, nom)
            if isinstance(valeur, str) and valeur.startswith(MARQUEUR_NON_RENSEIGNE):
                manquements.append(f"{nom} : valeur encore non renseignee (CHANGE_ME_*)")

        # 3 — les valeurs typees sont valides
        #     Les entiers et booleens sont deja valides par Pydantic, qui echoue
        #     avant d'arriver ici. Restent les enumerations que Pydantic ne peut
        #     pas connaitre, et les bornes de bon sens.
        if self.LOG_LEVEL.lower() not in {"debug", "info", "warning", "error", "critical"}:
            manquements.append("LOG_LEVEL : valeur hors de l'enumeration attendue")
        if not 1 <= self.POSTGRES_PORT <= 65535:
            manquements.append("POSTGRES_PORT : hors de la plage 1-65535")
        if not 1 <= self.REDIS_PORT <= 65535:
            manquements.append("REDIS_PORT : hors de la plage 1-65535")

        # 4 — LOG_FORMAT vaut json
        if self.LOG_FORMAT != "json":
            manquements.append("LOG_FORMAT : doit valoir json (cahier §28.1)")

        return manquements

    def _controles_production(self) -> list[str]:
        """Les sept controles propres a APP_ENV=production."""
        manquements: list[str] = []

        if len(self.APP_SECRET_KEY.strip()) < LONGUEUR_MINIMALE_CLE:
            manquements.append(
                f"APP_SECRET_KEY : absente ou plus courte que {LONGUEUR_MINIMALE_CLE} caracteres"
            )
        if self.EMAIL_PROVIDER == "mailpit":
            manquements.append("EMAIL_PROVIDER : mailpit est interdit en production (cahier §16.5)")
        if self.API_DOCS_ENABLED:
            manquements.append("API_DOCS_ENABLED : doit valoir false en production (cahier §18.1)")
        if not self.SESSION_COOKIE_SECURE:
            manquements.append(
                "SESSION_COOKIE_SECURE : doit valoir true en production (cahier §7.4)"
            )
        if not self.CSRF_PROTECTION_ENABLED:
            manquements.append(
                "CSRF_PROTECTION_ENABLED : doit valoir true en production (cahier §7.4)"
            )
        if self.DB_AUTO_CREATE:
            manquements.append(
                "DB_AUTO_CREATE : doit valoir false, aucune creation automatique "
                "de table (cahier §16.2)"
            )
        if not self.PUBLIC_BASE_URL.startswith("https://"):
            manquements.append("PUBLIC_BASE_URL : doit commencer par https:// en production")

        return manquements

    # ------------------------------------------------------------------------
    #  Chaines de connexion
    # ------------------------------------------------------------------------

    def url_postgresql(self) -> str:
        """URL SQLAlchemy de l'APPLICATION — le role d'execution, jamais le superutilisateur.

        Contient le mot de passe : ne jamais la journaliser telle quelle.

        **CETTE METHODE EMPLOYAIT `POSTGRES_USER` JUSQU'AU LOT 3.** C'etait
        `QO-116` : le cahier §20.1 pose le moindre privilege, et l'API se
        connectait avec le compte proprietaire du cluster. Elle emploie desormais
        `POSTGRES_RUNTIME_USER`, qui ne peut que lire et ecrire des lignes.
        """
        return self._url(self.POSTGRES_RUNTIME_USER, self.POSTGRES_RUNTIME_PASSWORD)

    def url_postgresql_migrations(self) -> str:
        """URL SQLAlchemy des MIGRATIONS — le role qui possede les objets du schema.

        Employee par `alembic/env.py`, et par lui seul. Elle porte le droit de
        creer et de modifier des tables, que l'application n'a pas.
        """
        return self._url(self.POSTGRES_MIGRATIONS_USER, self.POSTGRES_MIGRATIONS_PASSWORD)

    def url_postgresql_superutilisateur(self) -> str:
        """URL du compte cree par `initdb`. **N'A QU'UN SEUL USAGE LEGITIME.**

        Approvisionner les deux roles ci-dessus — `make roles-provision` — parce
        que `CREATE ROLE` exige le superutilisateur. Toute autre utilisation est
        une regression de `QO-116`, et `make privileges-check` la detecte.
        """
        return self._url(self.POSTGRES_USER, self.POSTGRES_PASSWORD)

    def _url(self, utilisateur: str, mot_de_passe: str) -> str:
        return (
            f"postgresql+psycopg://{utilisateur}:{mot_de_passe}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def url_redis(self) -> str:
        """URL de connexion Redis. Contient le mot de passe."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    def url_minio(self) -> str:
        """URL du point d'acces S3 de MinIO."""
        schema = "https" if self.MINIO_USE_SSL else "http"
        return f"{schema}://{self.MINIO_ENDPOINT}"


def charger_parametres() -> Parametres:
    """Lire la configuration et refuser de demarrer si elle est invalide.

    Deux etages de validation, et c'est voulu :
      - Pydantic rejette d'abord ce qui n'est pas typable — un entier qui n'en
        est pas, un booleen illisible, un APP_ENV hors enumeration ;
      - `controler()` applique ensuite les onze garde-fous metier.

    Les deux levent `ConfigurationInvalide`, pour que l'appelant n'ait qu'un
    seul cas a traiter.
    """
    try:
        parametres = Parametres()
    except ValidationError as erreur:
        manquements = [
            f"{'.'.join(str(p) for p in detail['loc'])} : {detail['msg']}"
            for detail in erreur.errors()
        ]
        raise ConfigurationInvalide(manquements) from erreur

    manquements = parametres.controler()
    if manquements:
        raise ConfigurationInvalide(manquements)

    return parametres


@functools.lru_cache(maxsize=1)
def parametres_en_cache() -> Parametres:
    """Configuration chargee une seule fois par processus.

    Le cache est vide dans les tests par `parametres_en_cache.cache_clear()`.
    """
    return charger_parametres()
