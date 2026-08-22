"""Les sept tables du modele de donnees §10 — authentification et securite.

LOT 3, sous-etape `T2`. Elles servent les huit stories `MVP-L03-US001` a `US008`.

FONDEMENT — modele §10.1 `user_account`, §10.2 `admin_password_credential`,
§10.3 `magic_link_request`, §10.4 `user_session`, §10.5 `service_account` et
`service_token`, §10.6 `auth_event`. Champs communs du §3.1.

CE QUE LE MODELE IMPOSE, ET CE QU'IL LAISSE OUVERT — mesure du 21/08/2026

  Le §25.1 ne nomme que **deux** contraintes pour ces tables :

      magic_link_request(token_hash) UNIQUE
      user_session(session_token_hash) UNIQUE

  Et les §25.2, §25.3 et §25.4 n'en nomment **aucune** : pas d'historisation, pas
  de cle composite, pas de regle inter-tables. **Aucune contrainte d'exclusion
  n'est donc posee ici** -- ce serait exiger plus que le modele, defaut du §7.20.

  MAIS le §25.1 s'ouvre par « **A prevoir notamment** » : la liste est
  explicitement NON EXHAUSTIVE. Quatre unicites de plus sont donc posees, et
  **chacune est DERIVEE d'une regle ecrite**, jamais inventee :

    user_account(person_id, account_type)          §10.1 : « un compte employe
      UNIQUE                                       et, si necessaire, un compte
                                                   administrateur local DISTINCT »
    admin_password_credential(user_account_id)     §10.2 : `revoked_at` implique
      UNIQUE WHERE revoked_at IS NULL              qu'au plus un est actif
    magic_link_request(person_id)                  §10.3 : « le dernier lien
      UNIQUE WHERE used_at IS NULL                 invalide les precedents encore
      AND invalidated_at IS NULL                   actifs »
    service_token(token_hash) UNIQUE               §10.5 : « un hash du jeton ».
                                                   Deux jetons de meme hash
                                                   rendraient l'authentification
                                                   AMBIGUE

  **La troisieme merite d'etre lue deux fois.** Le §10.3 decrit une ACTION -- le
  dernier lien invalide les precedents -- et l'index unique partiel en porte
  l'INVARIANT : « au plus un lien actif par personne ». Il ne fait pas
  l'invalidation, il la rend OBLIGATOIRE : un service qui l'oublierait verrait son
  insertion refusee. C'est exactement le parti de `DEC-514` pour « DG implique DSM
  local », et c'est ce qui rend l'oubli impossible plutot qu'improbable.

CES TABLES SONT GLOBALES, SAUF UNE

  `person` est globale -- `ARB-DATA-001` -- et un compte authentifie une personne,
  non une appartenance. Aucune de ces tables ne porte donc d'`entity_id`, **sauf
  `service_account`**, dont le §10.5 dit « une entite FACULTATIVE ». Sa colonne est
  donc NULLABLE, comme `allowed_email_domain` en `T2` du LOT 2 et
  `technical_role_assignment` en `T8`.

CE QUI N'EST PAS DE CE RESSORT, ET QUI EST DIT

  - **l'usage unique d'un magic link** est une regle de PROCESSUS : `used_at` ne se
    pose qu'une fois, ce qu'aucune contrainte de ligne n'exprime. `T4` la portera,
    et l'index partiel ci-dessus en garantit deja l'invariant structurant ;
  - **la reponse generique anti-enumeration** du §10.3 est une regle d'API : elle
    n'a aucune traduction en schema. `T3` ;
  - **l'expiration par inactivite de 7 jours** du §10.4 n'a pas de colonne : elle
    se calcule sur `last_activity_at`. Poser une colonne serait inventer ;
  - **« aucun lien complet dans les logs »** est une regle d'observabilite. `T4`,
    et les trois barrieres de `packages/observabilite` devront recevoir les formats
    que ce lot produit -- lecon `T4-1` du LOT 1 ;
  - **le §30.20**, « une action metier et son audit sont atomiques », reste classe
    LOT 12 : `auth_event` est un historique SPECIALISE, non l'audit general du §21.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, contrainte_enumeration

#  Les jetons ne sont JAMAIS stockes en clair : seule leur empreinte l'est. 64
#  caracteres est la longueur d'un SHA-256 en hexadecimal, et la contrainte de
#  longueur exacte rend un stockage en clair impossible a passer inapercu -- un
#  jeton brut n'aurait pas exactement cette longueur.
LONGUEUR_EMPREINTE_SHA256 = 64

#  §10.3 : « 15 minutes apres emission ». La valeur est ecrite dans le cahier et
#  dans la roadmap ; elle est donc CONTRAINTE, et la rendre configurable serait
#  une migration d'une ligne -- doctrine `DEC-499` sur les enumerations.
MINUTES_DE_VALIDITE_DU_MAGIC_LINK = 15

#  §10.4 : « absolute_expires_at | Maximum 30 jours ».
JOURS_MAXIMUM_DE_SESSION = 30

#  §10.4 : « last_activity_at | Expiration inactive apres 7 jours », et cahier
#  §7.4, « expiration apres 7 jours d'inactivite ».
#
#  **CETTE VALEUR N'A PAS DE COLONNE, ET C'EST DELIBERE** — `T2` du LOT 3 l'a
#  pose : l'expiration par inactivite se CALCULE sur `last_activity_at`, et une
#  colonne `inactive_expires_at` divergerait de sa source des la premiere mise a
#  jour. Elle est donc ici, avec la valeur du modele, et **elle est plus exposee
#  qu'une borne en base** : aucune contrainte ne refuserait une divergence. C'est
#  pourquoi un garde-fou de demarrage la confronte a `SESSION_IDLE_DAYS`.
JOURS_D_INACTIVITE_DE_SESSION = 7


class TypeCompte(enum.StrEnum):
    """§10.1 : `EMPLOYEE_MAGIC_LINK` ou `ADMIN_LOCAL`, litteralement."""

    EMPLOYEE_MAGIC_LINK = "EMPLOYEE_MAGIC_LINK"
    ADMIN_LOCAL = "ADMIN_LOCAL"


TYPES_COMPTE: tuple[str, ...] = tuple(membre.value for membre in TypeCompte)


class EtatCompte(enum.StrEnum):
    """§10.1 : `active`, `locked`, `disabled`, litteralement."""

    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


ETATS_COMPTE: tuple[str, ...] = tuple(membre.value for membre in EtatCompte)


class EtatCompteDeService(enum.StrEnum):
    """§10.5 : « un etat ». Le modele ne l'enumere PAS.

    Les valeurs reprennent celles de `EtatCompte`, moins `locked` : un compte de
    service ne se verrouille pas apres des echecs de mot de passe, il n'en a pas.
    **C'est une derivation, declaree ici**, et l'elargir serait une migration d'une
    ligne -- doctrine `DEC-499`.
    """

    ACTIVE = "active"
    DISABLED = "disabled"


ETATS_COMPTE_DE_SERVICE: tuple[str, ...] = tuple(membre.value for membre in EtatCompteDeService)


class TypeEvenementAuth(enum.StrEnum):
    """§10.6 : les SEPT evenements, dans l'ordre du modele.

    **LE MODELE LES DECRIT EN FRANCAIS ET NE LEUR DONNE AUCUN IDENTIFIANT.** Les
    sept noms ci-dessous sont donc une derivation, declaree : ils reprennent la
    casse MAJUSCULE des types du §10.1 et du §8.4, et l'ordre du modele.

      succes                              -> LOGIN_SUCCESS
      echec                               -> LOGIN_FAILURE
      magic link demande                  -> MAGIC_LINK_REQUESTED
      magic link utilise                  -> MAGIC_LINK_USED
      compte verrouille                   -> ACCOUNT_LOCKED
      session revoquee                    -> SESSION_REVOKED
      mot de passe administrateur modifie -> ADMIN_PASSWORD_CHANGED
    """

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    MAGIC_LINK_REQUESTED = "MAGIC_LINK_REQUESTED"
    MAGIC_LINK_USED = "MAGIC_LINK_USED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    SESSION_REVOKED = "SESSION_REVOKED"
    #  S105 : c'est le NOM d'un type d'evenement, pas un mot de passe. Le
    #  detecteur se declenche sur le mot « PASSWORD » dans un litteral, et il a
    #  raison de chercher -- mais ici la valeur EST son identifiant. C'est la
    #  meme famille que le §7.25 : un garde-fou qui refuse du code correct.
    ADMIN_PASSWORD_CHANGED = "ADMIN_PASSWORD_CHANGED"  # noqa: S105


TYPES_EVENEMENT_AUTH: tuple[str, ...] = tuple(membre.value for membre in TypeEvenementAuth)


class UserAccount(ChampsCommuns, Base):
    """Compte permettant l'authentification — modele §10.1.

    `person_id` est `NOT NULL`, et c'est une LECTURE du modele, posee ici. Le §10.1
    ecrit « obligatoire pour les comptes humains », ce qui laisserait croire a
    l'existence de comptes non humains dans cette table -- **mais les DEUX seules
    valeurs de `account_type` qu'il declare sont humaines**, et les comptes machine
    ont leur propre table, `service_account` §10.5. Ajouter un type machine ici
    serait une migration ET une decision.
    """

    __tablename__ = "user_account"

    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default=EtatCompte.ACTIVE)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        contrainte_enumeration("account_type", TypeCompte, "account_type_valide"),
        contrainte_enumeration("state", EtatCompte, "state_valide"),
        #  §10.1 : « un compte employe et, si necessaire, un compte administrateur
        #  local DISTINCT ». C'est une PERMISSION d'avoir les deux, et une
        #  interdiction d'en avoir deux du meme type. Un index unique sur
        #  `person_id` seul casserait la permission -- c'est le contresens que
        #  `T7` et `T8` du LOT 2 ont appris a eviter.
        UniqueConstraint(
            "person_id", "account_type", name="uq_user_account_person_id_account_type"
        ),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count_positif"),
    )


class AdminPasswordCredential(ChampsCommuns, Base):
    """Mot de passe d'un compte administrateur local — modele §10.2.

    « Aucun mot de passe brut ni historique reversible » : la table ne porte que
    `password_hash`, et `make secrets-check` verifie qu'aucune colonne de ce lot ne
    peut contenir un secret en clair.

    `algorithm` et `parameters` sont en COLONNES, ce que le §10.2 exige
    explicitement. Le motif est operationnel : migrer d'un algorithme a un autre
    exige de savoir avec lequel chaque empreinte a ete produite, sinon aucune
    verification n'est possible apres le changement.
    """

    __tablename__ = "admin_password_credential"

    user_account_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    changed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    must_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["user_account_id"], ["user_account.id"]),
        #  Derive de `revoked_at` : un mot de passe revoque n'est plus actif, donc
        #  au plus un l'est. Sans cette contrainte, deux empreintes actives pour un
        #  meme compte rendraient la verification ambigue.
        Index(
            "uq_admin_password_credential_user_account_id_actif",
            "user_account_id",
            unique=True,
            postgresql_where="revoked_at IS NULL",
        ),
    )


class MagicLinkRequest(ChampsCommuns, Base):
    """Demande de lien de connexion a usage unique — modele §10.3.

    `token_hash` est UNIQUE : c'est le §25.1, litteralement.

    **L'INDEX PARTIEL SUR `person_id` PORTE UN INVARIANT, PAS UNE ACTION.** Le
    §10.3 dit « le dernier lien invalide les precedents encore actifs » : c'est une
    ACTION, que `T4` executera. L'invariant qui en resulte -- « au plus un lien
    actif par personne » -- est ici, et il rend l'oubli IMPOSSIBLE : un service qui
    insererait sans invalider verrait son insertion refusee. Meme parti que
    `DEC-514`.
    """

    __tablename__ = "magic_link_request"

    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(LONGUEUR_EMPREINTE_SHA256), nullable=False)
    requested_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #  §10.3 : « valeur minimisee pour la limitation ». Une empreinte, jamais une
    #  adresse IP : le §28.2 interdit de journaliser une donnee identifiante, et
    #  `T8` s'en servira pour la limitation de debit.
    request_origin_hash: Mapped[str | None] = mapped_column(
        String(LONGUEUR_EMPREINTE_SHA256), nullable=True
    )

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        UniqueConstraint("token_hash", name="uq_magic_link_request_token_hash"),
        Index(
            "uq_magic_link_request_person_id_actif",
            "person_id",
            unique=True,
            postgresql_where="used_at IS NULL AND invalidated_at IS NULL",
        ),
        #  §10.3 : « 15 minutes apres emission ». La valeur est dans le cahier et
        #  dans la roadmap : elle est donc contrainte, non supposee.
        CheckConstraint(
            f"expires_at = requested_at + interval '{MINUTES_DE_VALIDITE_DU_MAGIC_LINK} minutes'",
            name="expiration_a_quinze_minutes",
        ),
        #  Un lien ne peut pas etre a la fois consomme ET invalide : les deux
        #  colonnes decrivent des fins de vie exclusives.
        CheckConstraint(
            "used_at IS NULL OR invalidated_at IS NULL",
            name="fin_de_vie_exclusive",
        ),
    )


class UserSession(ChampsCommuns, Base):
    """Session d'un utilisateur humain — modele §10.4.

    `session_token_hash` est UNIQUE : §25.1, litteralement.

    **L'EXPIRATION PAR INACTIVITE DE 7 JOURS N'A PAS DE COLONNE**, et ce n'est pas
    un oubli : elle se CALCULE sur `last_activity_at`. Poser une colonne
    `inactive_expires_at` la ferait diverger de sa source des la premiere mise a
    jour -- c'est le motif de la colonne generee `period` en `T1` du LOT 2.
    """

    __tablename__ = "user_session"

    session_token_hash: Mapped[str] = mapped_column(
        String(LONGUEUR_EMPREINTE_SHA256), nullable=False
    )
    person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    last_activity_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    absolute_expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        UniqueConstraint("session_token_hash", name="uq_user_session_session_token_hash"),
        CheckConstraint("last_activity_at >= created_at", name="activite_apres_creation"),
        #  §10.4 : « absolute_expires_at | Maximum 30 jours ».
        CheckConstraint(
            f"absolute_expires_at <= created_at + interval '{JOURS_MAXIMUM_DE_SESSION} days'",
            name="duree_absolue_bornee",
        ),
        CheckConstraint("absolute_expires_at > created_at", name="expiration_apres_creation"),
    )


class ServiceAccount(ChampsCommuns, Base):
    """Compte machine — modele §10.5.

    `entity_id` est NULLABLE, et c'est le §10.5 qui l'ecrit : « une entite
    FACULTATIVE ». Le mixin `RessourceLocale` la poserait `NOT NULL`, comme pour
    `allowed_email_domain` en `T2` du LOT 2 et `technical_role_assignment` en `T8`.

    `technical_owner_person_id` porte « un proprietaire technique » du §10.5. Il est
    `NOT NULL` : un compte machine sans responsable identifie est precisement ce
    qu'un audit reproche.
    """

    __tablename__ = "service_account"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default=EtatCompteDeService.ACTIVE
    )
    technical_owner_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["technical_owner_person_id"], ["person.id"]),
        contrainte_enumeration("state", EtatCompteDeService, "state_valide"),
        UniqueConstraint("name", name="uq_service_account_name"),
    )


class ServiceToken(ChampsCommuns, Base):
    """Jeton d'un compte machine — modele §10.5.

    `token_hash` est UNIQUE, et ce n'est PAS dans la liste du §25.1 -- qui s'ouvre
    par « a prevoir NOTAMMENT ». La derivation est nette : deux jetons de meme
    empreinte rendraient l'authentification **ambigue**, ce qui est un defaut de
    securite, non une preference.

    « La duree maximale des jetons reste configurable avant leur creation reelle »
    (§10.5) : **aucune borne n'est donc posee ici**, contrairement a `user_session`.
    Le modele le dit explicitement, et poser une borne serait inventer.
    """

    __tablename__ = "service_token"

    service_account_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(LONGUEUR_EMPREINTE_SHA256), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #  §10.5 : « les scopes ». Aucun catalogue n'existe dans le corpus -- c'est une
    #  decision ouverte de `T10`, §8 de la fiche. La colonne accueille donc une
    #  liste JSON, et une contrainte exige que ce soit bien un TABLEAU : un objet
    #  ou une chaine y passerait sans elle.
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["service_account_id"], ["service_account.id"]),
        UniqueConstraint("token_hash", name="uq_service_token_token_hash"),
        CheckConstraint("jsonb_typeof(scopes) = 'array'", name="scopes_est_un_tableau"),
        CheckConstraint("expires_at > created_at", name="expiration_apres_creation"),
    )


class AuthEvent(ChampsCommuns, Base):
    """Historique specialise des evenements d'authentification — modele §10.6.

    **CE N'EST PAS L'AUDIT GENERAL.** Le §21.1 declare `audit_event`, qui releve du
    LOT 12, et le controle §30.20 -- « une action metier et son audit sont
    atomiques » -- y reste classe. Confondre les deux ferait croire l'audit acquis.

    « Les donnees sensibles sont exclues » : la table ne porte NI mot de passe, NI
    jeton, NI lien complet. `person_id` et `user_account_id` sont NULLABLES parce
    qu'un echec de connexion sur une adresse INCONNUE doit pouvoir etre trace sans
    rattacher l'evenement a une personne qui n'existe pas -- c'est precisement le
    cas que la reponse generique anti-enumeration du §10.3 protege.
    """

    __tablename__ = "auth_event"

    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    user_account_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    #  LOT 3, `T10`, migration `0013`. **LE DIAGRAMME §11 DECLARE
    #  `SERVICE_ACCOUNT ||--o{ AUTH_EVENT : produces`**, et `T2` ne l'avait pas
    #  porte : c'est `ECART-037`. Sans cette colonne, « chaque appel est audite »
    #  exigerait un HUITIEME type d'evenement, or le §10.6 en declare SEPT et
    #  `T12` auditera exactement ces sept. Avec elle, `LOGIN_SUCCESS` et
    #  `LOGIN_FAILURE` suffisent -- le §10.6 les nomme « succes » et « echec »
    #  sans les restreindre aux humains.
    service_account_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    #  Une empreinte, jamais une adresse : meme motif que
    #  `magic_link_request.request_origin_hash`.
    request_origin_hash: Mapped[str | None] = mapped_column(
        String(LONGUEUR_EMPREINTE_SHA256), nullable=True
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["person_id"], ["person.id"]),
        ForeignKeyConstraint(["user_account_id"], ["user_account.id"]),
        ForeignKeyConstraint(["service_account_id"], ["service_account.id"]),
        contrainte_enumeration("event_type", TypeEvenementAuth, "event_type_valide"),
        #  **LES DEUX NULS RESTENT PERMIS, ET C'EST INDISPENSABLE** : un magic link
        #  demande pour une adresse inconnue, ou un jeton inconnu refuse, ne
        #  designe personne. Interdire ce cas casserait la reponse generique.
        CheckConstraint(
            "person_id IS NULL OR service_account_id IS NULL",
            name="ck_auth_event_un_seul_acteur",
        ),
    )
