"""Les six tables du LOT 10 — modele §21 et §22.3 — sous-etape `T1`.

FONDEMENT — modele §21.1 `audit_event`, §21.2 `operational_alert`, §21.3
`alert_comment`, §21.4 `bug_report`, §21.5 `export_request`, §22.3
`data_subject_request`. Champs communs du §3.1.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  Il pose les six tables, avec les champs communs du §3.1 et les cles
  COMPOSITES du §25.3 la ou elles sont SURES. Il ne pose aucun service, aucune
  route : l'ecriture d'audit arrive domaine par domaine en `T2` a `T7`, le
  journal filtrable en `T8`, l'export en `T9`, le reporting en `T10`, le
  signalement et son traitement en `T11`/`T12`, les alertes en `T13`, le suivi
  RGPD en `T14`.

  `retention_action`, `privacy_notice_version` et `privacy_notice_acknowledgement`
  (modele §22.1, §22.2, §22.4) NE SONT PAS POSEES ICI : aucune des huit stories
  du LOT 10 ne les nomme, et les poser sans consommateur ni regle metier
  validee serait inventer (§6.5 de la passation).

POURQUOI `audit_event` N'EST PAS `RessourceLocale`

  Le §21.1 ecrit « `entity_id` | Nullable pour evenement global », exactement
  le motif qui a deja ecarte `onboarding_template` de `RessourceLocale` au
  LOT 7 `T1`. Meme parti ici : une cle COMPOSITE vers une table dont
  `entity_id` est nullable serait rendue INERTE par `MATCH SIMPLE` des qu'un
  evenement global se produit (§4.14 de `CLAUDE.md`).

  `operational_alert`, `alert_comment`, `export_request` et
  `data_subject_request` NE PORTENT AUCUN `entity_id` DU TOUT : le §21.2, le
  §21.3, le §21.5 et le §22.3 n'en declarent aucun parmi leurs champs,
  contrairement au §21.1 (nullable, explicite) et au §21.4 (non nullable,
  explicite — « Entite consultee »). Une alerte operationnelle (disque, worker,
  sauvegarde), un export ou une demande RGPD ne sont pas des faits D'UNE
  entite : leur donner un `entity_id` serait une colonne que rien ne commande
  (§6.5). `bug_report` seul recoit `RessourceLocale`, le modele nommant
  explicitement sa portee.

CE QUI EST UN VOCABULAIRE FERME, ET CE QUI NE L'EST PAS — mesure champ par
champ, jamais suppose

  Le modele BACKTICKE les valeurs qu'il ferme, et les ecrit en PROSE quand il
  ne le fait pas — meme discipline qu'`import_row_issue.level` au LOT 9 :

    `operational_alert.severity`  FERME, et en MAJUSCULES : `INFO`, `WARNING`,
                                  `ERROR`, `CRITICAL` (§21.2, repris par §27.3)
    `operational_alert.state`     FERME, en minuscules : `open`, `acknowledged`,
                                  `resolved` (§21.2). « Reouverte
                                  automatiquement » (roadmap/cahier) n'ajoute
                                  PAS un quatrieme etat : rouvrir ramene a
                                  `open`, sur la MEME ligne (`fingerprint`),
                                  jamais une nouvelle
    `operational_alert.source`   OUVERT : « API, worker, security, backup,
                                  Uptime Kuma » est ecrit en PROSE, sans
                                  guillemets ni cas uniforme, et « Uptime Kuma »
                                  porte une espace qu'aucune valeur enumeree de
                                  ce depot ne tolere (`MOTIF_VALEUR_ENUMEREE`).
                                  Chaine non vide, jamais une enumeration
                                  inventee pour forcer une casse que le modele
                                  ne fixe pas
    `bug_report.state`            FERME, en minuscules : `new`, `investigating`,
                                  `fixed`, `rejected` (§21.4) — correspond mot a
                                  mot aux « nouveau, en analyse, corrige,
                                  rejete » du backlog `US006`, traduits comme le
                                  reste des enumerations de ce depot
    `data_subject_request.type`   FERME par la PHRASE du §22.3 elle-meme : «
                                  demandes d'acces, rectification, effacement
                                  OU OPPOSITION » — quatre categories nommees,
                                  jamais backtickees mais sans alternative
                                  laissee ouverte. **MESURE, PAS RESOLU** : le
                                  §11.1 du cahier (ligne ~1299) ecrit ailleurs
                                  « acces, rectification, effacement et
                                  LIMITATION » — un QUATRIEME mot different du
                                  §22.3. Le §22.3 est retenu ici parce qu'il
                                  decrit LITTERALEMENT cette table ; la
                                  divergence elle-meme n'est pas tranchee et
                                  devra etre reposee a Jonathan si `T14` la
                                  rencontre
    `data_subject_request.état`   OUVERT : ni le §22.3 ni aucune autre section
                                  n'en donne le vocabulaire. Chaine non vide

DEFAUTS TROUVES PAR `make isolation-check`, CORRIGES AVANT COMMIT

  **TROIS reference NUES, trouvees a la premiere execution reelle contre la
  base migree — pas contre une base encore a `0026`, ou le controle lit l'etat
  du catalogue et ne pouvait rien voir avant `make migrate`.**

  `audit_event.resource_id` et `audit_event.correlation_id`/
  `bug_report.correlation_id` portaient un suffixe `_id` sans cle etrangere :
  le controle les a toutes trois refusees, exactement le piege que sa propre
  doctrine nomme (« une reference sans cle etrangere donne la meme observation
  qu'un schema sans fuite »). Aucune des deux n'EST une cle etrangere au sens
  ou le controle l'entend :

    - `resource_id` est VOLONTAIREMENT polymorphe (`resource_type` varie :
      `person`, `circle`, `import_batch`…), et AUCUNE cle etrangere unique ne
      pourrait jamais la couvrir ;
    - `correlation_id` est un jeton de correlation technique (le meme nom que
      `packages/observabilite`), jamais une reference a une ligne.

  **Renommees plutot que dispensees** : `resource_id` devient
  `resource_reference`, `correlation_id` devient `correlation_token` sur les
  deux tables — un nom qui ne finit plus par `_id` dit la verite sur ce que la
  colonne EST, au lieu d'etendre `COLONNES_D_AUTEUR` pour mon propre cas, ce
  qui aurait affaibli un controle qui a raison (§7.20 de la passation).

  `export_request.job_id` a ete RETIRE plutot que pose nullable sans cle
  etrangere : `async_job` n'existe pas encore (LOT 11), et une colonne ne peut
  referencer une table absente. Meme regime que `import_batch.delimiter` au
  LOT 9 `T10` — un champ du modele que son lot proprietaire posera, pas ce
  module. `T9` servira l'export CSV de maniere SYNCHRONE (aucune
  infrastructure asynchrone dans ce lot) : aucune ligne de ce lot n'aurait de
  toute facon ecrit cette colonne.

  `operational_alert.fingerprint` porte un index UNIQUE, pas un index simple :
  le modele ecrit qu'il « permet la reouverture ET la deduplication », ce que
  seule une ligne UNIQUE par empreinte satisfait — reouvrir une alerte, c'est
  faire repasser la MEME ligne a `open`, jamais en creer une seconde qui
  dupliquerait l'historique d'acquittement.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, RessourceLocale, contrainte_enumeration


class EtatAlerte(enum.StrEnum):
    """§21.2 : les trois etats d'une alerte operationnelle."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


ETATS_ALERTE: tuple[str, ...] = tuple(membre.value for membre in EtatAlerte)


class SeveriteAlerte(enum.StrEnum):
    """§21.2/§27.3 : les quatre niveaux, en MAJUSCULES — le modele les ecrit ainsi."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


SEVERITES_ALERTE: tuple[str, ...] = tuple(membre.value for membre in SeveriteAlerte)


class EtatSignalement(enum.StrEnum):
    """§21.4 : les quatre etats d'un signalement de bug."""

    NEW = "new"
    INVESTIGATING = "investigating"
    FIXED = "fixed"
    REJECTED = "rejected"


ETATS_SIGNALEMENT: tuple[str, ...] = tuple(membre.value for membre in EtatSignalement)


class TypeDeDemandeRGPD(enum.StrEnum):
    """§22.3 : les quatre categories que la phrase du modele ferme."""

    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    OBJECTION = "objection"


TYPES_DE_DEMANDE_RGPD: tuple[str, ...] = tuple(membre.value for membre in TypeDeDemandeRGPD)


class AuditEvent(ChampsCommuns, Base):
    """Le journal d'audit general — modele §21.1.

    **PAS `RessourceLocale`** : `entity_id` est NULLABLE par le modele
    lui-meme, pour un evenement global. Voir l'en-tete du module.

    `resource_id` est NULLABLE et NE PORTE AUCUNE cle etrangere : la table est
    POLYMORPHE sur `resource_type`, et une ligne doit pouvoir auditer un echec
    sur une ressource qui n'existe PAS encore ou plus — meme motif que
    `auth_event.person_id`, deja nullable pour une adresse inconnue (§22.5,
    anti-enumeration).

    `actor_person_id` et `actor_service_account_id` sont DEDIES, distincts des
    colonnes d'auteur de `ChampsCommuns` : meme parti qu'`auth_event`, deja de
    cette nature (journal d'evenements, acteur nullable, raison facultative).
    """

    __tablename__ = "audit_event"

    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    actor_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    actor_service_account_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    #  PAS `resource_id` : voir « DEFAUTS TROUVES » en tete de module.
    resource_reference: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    #  PAS `correlation_id` : voir « DEFAUTS TROUVES » en tete de module.
    correlation_token: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    #  Un an par defaut — §21.1, §10.11, §16.1. Calcule au meme instant que
    #  `occurred_at`, jamais une valeur Python separee qui pourrait diverger.
    retention_until: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("(now() + interval '1 year')"),
    )

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["actor_person_id"], ["person.id"]),
        ForeignKeyConstraint(["actor_service_account_id"], ["service_account.id"]),
        CheckConstraint("length(btrim(action_code)) > 0", name="action_code_non_vide"),
        CheckConstraint("length(btrim(resource_type)) > 0", name="resource_type_non_vide"),
        CheckConstraint("length(btrim(summary)) > 0", name="summary_non_vide"),
        CheckConstraint("length(btrim(correlation_token)) > 0", name="correlation_token_non_vide"),
        Index("ix_audit_event_entity_occurred", "entity_id", "occurred_at"),
        Index("ix_audit_event_resource", "resource_type", "resource_reference"),
    )


class OperationalAlert(ChampsCommuns, Base):
    """Une alerte operationnelle interne — modele §21.2, distincte d'Uptime Kuma.

    GLOBALE : aucun `entity_id`, voir l'en-tete du module. L'integration REELLE
    avec Uptime Kuma (seuils de production, canaux, cahier §27) reste hors
    perimetre de ce lot — LOT 13.
    """

    __tablename__ = "operational_alert"

    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    #  Vocabulaire OUVERT, voir l'en-tete du module : jamais une enumeration.
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'open'"))
    assigned_to_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    opened_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    acknowledged_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["assigned_to_person_id"], ["person.id"]),
        contrainte_enumeration("severity", SeveriteAlerte, "severity_valide"),
        contrainte_enumeration("state", EtatAlerte, "state_valide"),
        CheckConstraint("length(btrim(source)) > 0", name="source_non_vide"),
        CheckConstraint("length(btrim(fingerprint)) > 0", name="fingerprint_non_vide"),
        UniqueConstraint("fingerprint", name="uq_operational_alert_fingerprint"),
    )


class AlertComment(ChampsCommuns, Base):
    """Un commentaire d'acquittement ou de resolution — modele §21.3.

    GLOBALE, comme son parent `operational_alert` : voir l'en-tete du module.
    """

    __tablename__ = "alert_comment"

    operational_alert_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["operational_alert_id"], ["operational_alert.id"]),
        CheckConstraint("length(btrim(content)) > 0", name="content_non_vide"),
    )


class BugReport(ChampsCommuns, RessourceLocale, Base):
    """Un signalement de bug — modele §21.4.

    **SEULE table de ce module a recevoir `RessourceLocale`** : le §21.4 nomme
    explicitement `entity_id` (« Entite consultee »), sans le marquer nullable
    — contrairement au §21.1. `reported_by_person_id` est NOT NULL : le role
    du besoin (`US005`, backlog) est "Utilisateur", un role authentifie dans
    le vocabulaire de ce depot, jamais un visiteur anonyme — toute l'
    application exige une session (§20.1).
    """

    __tablename__ = "bug_report"

    reported_by_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'new'"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reproduction_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_path: Mapped[str] = mapped_column(Text, nullable=False)
    application_version: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    browser_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    #  PAS `correlation_id` : voir « DEFAUTS TROUVES » en tete de module.
    correlation_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["reported_by_person_id"], ["person.id"]),
        contrainte_enumeration("state", EtatSignalement, "state_valide"),
        CheckConstraint("length(btrim(description)) > 0", name="description_non_vide"),
        CheckConstraint("length(btrim(page_path)) > 0", name="page_path_non_vide"),
        CheckConstraint(
            "length(btrim(application_version)) > 0", name="application_version_non_vide"
        ),
        CheckConstraint("length(btrim(environment)) > 0", name="environment_non_vide"),
        UniqueConstraint("id", "entity_id"),
    )


class ExportRequest(ChampsCommuns, Base):
    """Le suivi d'un export — modele §21.5.

    GLOBALE : voir l'en-tete du module. Le champ « job » du modele N'EST PAS
    POSE ICI : `async_job` n'existe pas encore (LOT 11), et une colonne ne
    peut referencer une table absente — voir le defaut trouve en construisant
    ce module, dans l'en-tete. `T9` sert cet export de maniere SYNCHRONE.
    """

    __tablename__ = "export_request"

    #  Vocabulaire OUVERT : une seule valeur connue a ce jour (l'export CSV de
    #  l'audit, `T9`), jamais une enumeration fermee sur un ensemble futur non
    #  decide.
    export_type: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    normalized_scope: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    generated_media_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["requested_by_person_id"], ["person.id"]),
        ForeignKeyConstraint(["generated_media_id"], ["media_asset.id"]),
        CheckConstraint("length(btrim(export_type)) > 0", name="export_type_non_vide"),
    )


class DataSubjectRequest(ChampsCommuns, Base):
    """Une demande de droit RGPD — modele §22.3.

    GLOBALE : voir l'en-tete du module. Une personne concernee n'est pas
    necessairement rattachee a une entite active au moment de sa demande.
    """

    __tablename__ = "data_subject_request"

    data_subject_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    identity_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    responsible_person_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    due_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #  Vocabulaire OUVERT : ni le §22.3 ni aucune autre section n'en donne le
    #  vocabulaire, voir l'en-tete du module.
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["data_subject_person_id"], ["person.id"]),
        ForeignKeyConstraint(["responsible_person_id"], ["person.id"]),
        contrainte_enumeration("request_type", TypeDeDemandeRGPD, "request_type_valide"),
        CheckConstraint("length(btrim(channel)) > 0", name="channel_non_vide"),
        CheckConstraint("length(btrim(state)) > 0", name="state_non_vide"),
    )
