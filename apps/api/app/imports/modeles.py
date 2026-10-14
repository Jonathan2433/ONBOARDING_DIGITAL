"""Les quatre tables de l'import CSV — modele §19 — LOT 9, `T1`.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  Il pose `import_batch`, `import_row`, `import_row_issue` et `import_decision`,
  toutes locales et protegees par les cles composites du §25.3. Il ne pose
  aucun service ni route : le depot du fichier arrive en `T6`, l'analyse et la
  detection de doublons en `T7`, les decisions humaines en `T8`, l'import
  transactionnel en `T9`/`T10`.

  Aucune table `async_job` ni `outbox_message` : l'import reste SYNCHRONE
  (`DEC-462`), confirme par Jonathan le 08/10/2026. Ces deux tables restent
  reservees au LOT 11 — precedent mesure au LOT 7 `T10`, aucune ligne du depot
  n'y ecrit encore.

CE QUI EST DERIVE DU MODELE, ET CE QUI NE L'EST PAS

  - `import_batch.state` et `import_row.state` reprennent LITTERALEMENT les
    enumerations du §19.1 et §19.2 — aucune valeur n'est inventee ;
  - `import_decision.decision_type` reprend les CINQ categories que le §19.4
    NOMME explicitement (fusion, reactivation, alias, selection canonique,
    rejet) — un enum ferme, parce que le modele ferme la liste ;
  - `import_row_issue.level` n'est PAS un enum : le §19.3 ecrit « niveau » sans
    en donner le vocabulaire, exactement le piege deja rencontre sur
    `event_media.display_role` (LOT 8, `T1`) — une chaine non vide, jamais une
    enumeration inventee ;
  - le schema REEL des colonnes CSV (en-tetes, langue, nomenclature) n'est pas
    ici : `QO-096`/`QO-110` restent ouvertes, et `raw_data`/`normalized_data`
    sont volontairement opaques (`jsonb`), au sens ou ce module ne connait pas
    encore F01-F19 (`DEC-434`) — c'est `T6`/`T7` qui liront le CSV.

DEFAUT TROUVE PAR `make isolation-check`, CORRIGE AVANT COMMIT

  `import_batch.approved_by_person_id` avait d'abord ete pose SANS cle
  etrangere, par un faux parallele avec les trois colonnes d'auteur de
  `ChampsCommuns`. Le controle d'isolation l'a refuse : CES TROIS COLONNES
  SONT LA SEULE EXCEPTION du depot, parce qu'elles sont GENERIQUES et posees
  sur TOUTE table ; toute colonne d'acteur NOMMEE par un module (comme
  `media_asset.uploaded_by_person_id` ou `onboarding_template_version.
  published_by_person_id`) porte une cle etrangere reelle vers `person`. Une
  reference nue donne la meme observation qu'un schema sans fuite — corrige.
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import (
    Base,
    ChampsCommuns,
    RessourceLocale,
    contrainte_enumeration,
    nom_cle_composite,
)


class EtatLotImport(enum.StrEnum):
    """§19.1 : les huit etats d'un lot d'import, diagramme §24.4."""

    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    PREVIEW_READY = "preview_ready"
    APPROVED = "approved"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ETATS_LOT_IMPORT: tuple[str, ...] = tuple(membre.value for membre in EtatLotImport)


class EtatLigneImport(enum.StrEnum):
    """§19.2 : les six etats d'une ligne du CSV."""

    VALID = "valid"
    WARNING = "warning"
    NEEDS_DECISION = "needs_decision"
    REJECTED = "rejected"
    IMPORTED = "imported"
    UPDATED = "updated"


ETATS_LIGNE_IMPORT: tuple[str, ...] = tuple(membre.value for membre in EtatLigneImport)


class TypeDeDecisionImport(enum.StrEnum):
    """§19.4 : les cinq categories de decision humaine, fermees par le modele."""

    PERSON_MERGE = "person_merge"
    PROFILE_REACTIVATION = "profile_reactivation"
    CLIENT_ALIAS_CREATION = "client_alias_creation"
    CANONICAL_CLIENT_SELECTION = "canonical_client_selection"
    VOLUNTARY_REJECTION = "voluntary_rejection"


TYPES_DE_DECISION_IMPORT: tuple[str, ...] = tuple(membre.value for membre in TypeDeDecisionImport)


class ImportBatch(ChampsCommuns, RessourceLocale, Base):
    """Un lot d'import — modele §19.1."""

    __tablename__ = "import_batch"

    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'uploaded'")
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    warning_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    #  Ajoutee par `T7` (LOT 9) : la PREMIERE sous-etape a produire des lignes
    #  `needs_decision` (modele §19.2). Sans cette colonne, `total_rows`
    #  depasserait la somme des trois autres compteurs sans qu'aucune colonne
    #  n'explique l'ecart — voir l'en-tete de la migration `0025`.
    needs_decision_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    approved_by_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    #  Ajoutee par `T10` (LOT 9) — residu nomme par `T6` : le separateur
    #  detecte (`DEC-432`) n'etait jamais consigne. NULLABLE : les lots
    #  anterieurs a cette migration (aucun hors des tests) ne l'ont jamais eu.
    delimiter: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["approved_by_person_id"], ["person.id"]),
        contrainte_enumeration("state", EtatLotImport, "state_valide"),
        CheckConstraint(
            "total_rows >= 0 AND valid_rows >= 0 AND warning_rows >= 0 "
            "AND needs_decision_rows >= 0 AND rejected_rows >= 0",
            name="comptes_non_negatifs",
        ),
        #  Les DEUX SEULES valeurs que `_detecter_le_delimiteur` peut jamais
        #  rendre (`app.imports.depot`, `DEC-432`) — pas une regle de plus.
        CheckConstraint(
            "delimiter IS NULL OR delimiter IN (';', ',')",
            name="delimiter_connu",
        ),
        Index("ix_import_batch_entity_state", "entity_id", "state"),
        UniqueConstraint("id", "entity_id"),
    )


class ImportRow(ChampsCommuns, RessourceLocale, Base):
    """Une ligne du CSV, dans son lot — modele §19.2."""

    __tablename__ = "import_row"

    import_batch_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalized_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'valid'"))
    target_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    target_membership_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    error_codes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["import_batch_id", "entity_id"],
            ["import_batch.id", "import_batch.entity_id"],
            name=nom_cle_composite("import_row", "import_batch"),
        ),
        ForeignKeyConstraint(["target_person_id"], ["person.id"]),
        ForeignKeyConstraint(
            ["target_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name=nom_cle_composite("import_row", "entity_membership"),
        ),
        contrainte_enumeration("state", EtatLigneImport, "state_valide"),
        CheckConstraint("row_number > 0", name="numero_de_ligne_positif"),
        Index(
            "uq_import_row_batch_numero",
            "import_batch_id",
            "row_number",
            unique=True,
        ),
        Index("ix_import_row_entity_state", "entity_id", "state"),
        UniqueConstraint("id", "entity_id"),
    )


class ImportRowIssue(ChampsCommuns, RessourceLocale, Base):
    """Une erreur ou un avertissement sur une ligne — modele §19.3."""

    __tablename__ = "import_row_issue"

    import_row_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    field: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    #  Le §19.3 ecrit « niveau » sans en donner le vocabulaire — meme piege que
    #  `event_media.display_role` (LOT 8, `T1`) : une chaine non vide, jamais
    #  une enumeration inventee pour l'occasion.
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_value_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["import_row_id", "entity_id"],
            ["import_row.id", "import_row.entity_id"],
            name=nom_cle_composite("import_row_issue", "import_row"),
        ),
        CheckConstraint("length(btrim(code)) > 0", name="code_non_vide"),
        CheckConstraint("length(btrim(level)) > 0", name="niveau_non_vide"),
        UniqueConstraint("id", "entity_id"),
    )


class ImportDecision(ChampsCommuns, RessourceLocale, Base):
    """Une decision humaine sur une ligne — modele §19.4.

    L'auteur, la date et le motif que le §19.4 exige : l'auteur et la date
    viennent de `ChampsCommuns` (`created_by_person_id`, `created_at`), SANS
    les redeclarer ; seul le motif est propre a cette table (`reason`).
    """

    __tablename__ = "import_decision"

    import_row_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    target_client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["import_row_id", "entity_id"],
            ["import_row.id", "import_row.entity_id"],
            name=nom_cle_composite("import_decision", "import_row"),
        ),
        ForeignKeyConstraint(["target_person_id"], ["person.id"]),
        ForeignKeyConstraint(["target_client_id"], ["client.id"]),
        contrainte_enumeration("decision_type", TypeDeDecisionImport, "decision_type_valide"),
        UniqueConstraint("id", "entity_id"),
    )
