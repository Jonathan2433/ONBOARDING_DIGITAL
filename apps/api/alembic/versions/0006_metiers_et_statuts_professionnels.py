"""Metiers, affectations metier et situations professionnelles.

LOT 2, sous-etape `T5`, story `MVP-L02-US003`.
Revision : 0006
Revision precedente : 0005

FONDEMENT — modele §6.3 a §6.5, contraintes §25.1 a §25.3, point 5 de l'ordre du
§28.

**LA PREMIERE MIGRATION DE CE LOT SANS AUCUN DECLENCHEUR**, et ce n'est pas un
hasard : toutes les regles applicables ici s'expriment de facon DECLARATIVE. Ce
qui le permet est la conception du §25.3 -- les cles etrangeres COMPOSITES
transforment une regle inter-tables en contrainte de ligne.

TROIS TABLES, ET CE QUI PORTE CHAQUE REGLE

  `job_catalog`
    §25.1 litteralement : `job_catalog(entity_id, code) UNIQUE WHERE archived_at
    IS NULL`. Index PARTIEL, donc un metier archive LIBERE son code -- a la
    difference de `entity(code)`, dont l'unicite n'est pas partielle. La
    difference est dans le §25.1 lui-meme, et elle se comprend : un code
    d'entite est cite dans les journaux d'audit, un code de metier est une
    donnee de configuration locale.

  `membership_job_assignment`
    « une seule affectation metier active »   -> index unique PARTIEL
                                                `WHERE ends_at IS NULL`
    « le metier appartient a la meme entite » -> DEUX cles etrangeres
                                                COMPOSITES, §25.3
    « les periodes ne se chevauchent pas »    -> contrainte d'exclusion, §25.2

    **LES CLES COMPOSITES SONT CE QUI APPLIQUE VRAIMENT LA REGLE D'ENTITE.** Une
    paire de cles simples vers `entity_membership(id)` et `job_catalog(id)`
    laisserait affecter un metier de Lille a une appartenance de Bordeaux : rien
    ne relierait les deux entites. En faisant passer `entity_id` dans les deux
    cles, l'entite est forcement la meme -- c'est la MEME colonne.

  `professional_status_assignment`
    « une seule situation active »            -> index unique PARTIEL
    periodes                                 -> exclusion, §25.2
    « `client_id` obligatoire en mission,     -> contrainte de verification
      nul en intercontrat »

CE QUI N'EST PAS APPLICABLE EN `T5`, ET IL FAUT LE DIRE

  - **`client_id` n'a pas encore de cle etrangere.** Le §6.5 la veut vers
    `client`, que le §28 place au point 6, donc en `T6`. La contrainte y sera
    ajoutee. L'alternative aurait ete de deplacer cette table en `T6`, ce qui
    aurait contredit l'ordre du §28 et le decoupage valide ;
  - « **`mission` exige un client ACTIF POUR L'ENTITE** » et « **`intercontract`
    interdit un client actif** » supposent `entity_client` : `T6` au plus tot,
    et vraisemblablement `T9` ou `T10` avec les autres regles inter-tables ;
  - « un changement de statut declenche l'evaluation du parcours d'onboarding » :
    LOT 7.

LA VALEUR STOCKEE EST `intercontract`, EN ANGLAIS. Le modele emploie les deux
orthographes, et la mesure les separe : `intercontract` toujours entre accents
graves, donc la ou il specifie une VALEUR ; `intercontrat` en prose, la ou il
nomme le concept. `ECART-012` citait la forme francaise : corrige.

UN DEFAUT DE NOMMAGE, ATTRAPE PAR UN CONTROLE POSE EN `T1`

  La convention rend `fk_<table>_<toutes_les_colonnes>_<table_visee>`, ce qui est
  parfait pour une cle simple et explose pour une cle COMPOSITE :
  `fk_professional_status_assignment_entity_membership_id_entity_id_entity_membership`
  fait **82 caracteres** pour une limite de **63**. Trois cles depassaient, a 77,
  65 et 82.

  PostgreSQL tronque a 63 octets **en silence**. Le controle
  `noms_de_contraintes_trop_longs`, ecrit en `T1`, les a attrapees -- quatre
  sous-etapes plus tard, sur des noms qui n'existaient pas quand il a ete ecrit.
  La regle `nom_cle_composite` est posee dans `app/shared/modele.py`.

UN INDEX QUE J'AVAIS AJOUTE, ET QUE LA MESURE A FAIT RETIRER

  Le §6.4 pose « une seule affectation metier active », le §6.5 « une seule
  situation active par appartenance ». J'avais traduit chacune par un index unique
  PARTIEL `WHERE ends_at IS NULL`, sur le motif que le §25.1 emploie pour
  `dsm_assignment`.

  **Mesure : ils ne peuvent JAMAIS se declencher.** Deux affectations actives ont
  toutes deux `ends_at` a NULL, donc deux plages NON BORNEES, qui se chevauchent
  toujours -- `[janvier,)` contient decembre. La contrainte d'exclusion les refuse
  systematiquement la premiere, et les deux tests qui visaient l'index ont echoue
  en nommant l'exclusion.

  **C'est l'INVERSE de `entity_membership` en `T4`**, ou l'index partiel et
  l'exclusion sont complementaires : la-bas l'index porte sur `membership_state`
  et non sur `ends_at`, et deux appartenances occupantes peuvent avoir des
  periodes disjointes. **Le meme motif est complementaire dans une table et
  redondant dans l'autre, et seule la mesure les distingue.**

  Les deux index sont donc retires. Ils n'etaient pas dans le §25.1 -- qui ne
  mentionne pas ces tables -- c'etait ma derivation, et elle etait inutile. Un
  index redondant coute a chaque ecriture et laisse croire qu'il travaille.

UNE SECONDE COLLISION DE NOM, ET SA CAUSE EST LA MEME QU'EN `T4`

  `0005` avait nomme explicitement `id_entite_unique` la contrainte UNIQUE du
  couple `(id, entity_id)` de `entity_membership`. `T5` a voulu la meme sur
  `job_catalog` : « relation "id_entite_unique" already exists ».

  **Une contrainte UNIQUE est implementee par un INDEX**, comme une exclusion, et
  les noms d'index sont uniques a l'echelle du SCHEMA. Mais a la difference des
  exclusions, la convention de SQLAlchemy SAIT nommer une contrainte UNIQUE :
  `uq_<table>_<colonnes>`. **Le `name=` explicite avait donc ecrase un prefixe
  qui existait deja** -- exactement le defaut `T2-4`, ou un `name=` sur une cle
  etrangere avait produit deux contraintes appelees `entity`.

  La doctrine est desormais ecrite dans `app/shared/modele.py`, avec le controle
  `noms_d_index_en_collision` qui compare les noms entre eux -- ce que PostgreSQL
  fera de toute facon -- plutot que de verifier un prefixe.

  `0005` n'est PAS reecrite : une migration appliquee ne se reecrit jamais. La
  contrainte est RENOMMEE par la presente migration.

RETOUR ARRIERE. Le renommage se defait ; aucun declencheur ni fonction a
supprimer par ailleurs.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    #  RENOMMAGE D'UNE CONTRAINTE CREEE PAR `0005`, ET POURQUOI IL EST ICI
    #
    #  `0005` a cree sur `entity_membership` une contrainte UNIQUE nommee
    #  explicitement `id_entite_unique`. `T5` a voulu la meme sur
    #  `job_catalog`, et la creation a echoue : « relation
    #  "id_entite_unique" already exists ».
    #
    #  Une contrainte UNIQUE est implementee par un INDEX, et les noms
    #  d'index sont uniques a l'echelle du SCHEMA. Le `name=` explicite
    #  avait de plus ECRASE la convention, qui aurait produit un nom
    #  prefixe par la table.
    #
    #  `0005` n'est PAS reecrite -- une migration appliquee ne se reecrit
    #  jamais. La contrainte est RENOMMEE ici, ce qui rend le schema final
    #  conforme aux metadonnees et laisse la chaine rejouable depuis une
    #  base vide : `0005` cree l'ancien nom, `0006` le corrige.
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE entity_membership "
        "RENAME CONSTRAINT id_entite_unique TO uq_entity_membership_id_entity_id"
    )

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "job_catalog",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_job_catalog_entity_id_entity")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_catalog")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_job_catalog_id_entity_id")),
    )
    op.create_index(op.f("ix_job_catalog_entity_id"), "job_catalog", ["entity_id"], unique=False)
    op.create_index(
        "ix_job_catalog_entity_id_active", "job_catalog", ["entity_id", "active"], unique=False
    )
    op.create_index(
        "uq_job_catalog_entity_id_code_non_archive",
        "job_catalog",
        ["entity_id", "code"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_table(
        "membership_job_assignment",
        sa.Column("entity_membership_id", sa.Uuid(), nullable=False),
        sa.Column("job_catalog_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "period",
            postgresql.TSTZRANGE(),
            sa.Computed("tstzrange(starts_at, ends_at)", persisted=True),
            nullable=False,
        ),
        postgresql.ExcludeConstraint(
            (sa.column("entity_membership_id"), "="),
            (sa.column("period"), "&&"),
            using="gist",
            name="ex_membership_job_assignment_sans_chevauchement",
        ),
        sa.ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name="fk_membership_job_assignment_entity_membership",
        ),
        sa.ForeignKeyConstraint(
            ["job_catalog_id", "entity_id"],
            ["job_catalog.id", "job_catalog.entity_id"],
            name="fk_membership_job_assignment_job_catalog",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_membership_job_assignment")),
    )
    op.create_index(
        op.f("ix_membership_job_assignment_entity_id"),
        "membership_job_assignment",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_membership_job_assignment_entity_membership_id"),
        "membership_job_assignment",
        ["entity_membership_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_membership_job_assignment_job_catalog_id"),
        "membership_job_assignment",
        ["job_catalog_id"],
        unique=False,
    )
    op.create_table(
        "professional_status_assignment",
        sa.Column("entity_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "period",
            postgresql.TSTZRANGE(),
            sa.Computed("tstzrange(starts_at, ends_at)", persisted=True),
            nullable=False,
        ),
        postgresql.ExcludeConstraint(
            (sa.column("entity_membership_id"), "="),
            (sa.column("period"), "&&"),
            using="gist",
            name="ex_professional_status_assignment_sans_chevauchement",
        ),
        sa.CheckConstraint(
            "(status = 'mission') = (client_id IS NOT NULL)",
            name=op.f("ck_professional_status_assignment_client_selon_le_statut"),
        ),
        sa.CheckConstraint(
            "status IN ('mission', 'intercontract')",
            name=op.f("ck_professional_status_assignment_status_valide"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name="fk_professional_status_assignment_entity_membership",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professional_status_assignment")),
    )
    op.create_index(
        op.f("ix_professional_status_assignment_client_id"),
        "professional_status_assignment",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_professional_status_assignment_entity_id"),
        "professional_status_assignment",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_professional_status_assignment_entity_membership_id"),
        "professional_status_assignment",
        ["entity_membership_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_professional_status_assignment_entity_membership_id"),
        table_name="professional_status_assignment",
    )
    op.drop_index(
        op.f("ix_professional_status_assignment_entity_id"),
        table_name="professional_status_assignment",
    )
    op.drop_index(
        op.f("ix_professional_status_assignment_client_id"),
        table_name="professional_status_assignment",
    )
    op.drop_table("professional_status_assignment")
    op.drop_index(
        op.f("ix_membership_job_assignment_job_catalog_id"), table_name="membership_job_assignment"
    )
    op.drop_index(
        op.f("ix_membership_job_assignment_entity_membership_id"),
        table_name="membership_job_assignment",
    )
    op.drop_index(
        op.f("ix_membership_job_assignment_entity_id"), table_name="membership_job_assignment"
    )
    op.drop_table("membership_job_assignment")
    op.drop_index(
        "uq_job_catalog_entity_id_code_non_archive",
        table_name="job_catalog",
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.drop_index("ix_job_catalog_entity_id_active", table_name="job_catalog")
    op.drop_index(op.f("ix_job_catalog_entity_id"), table_name="job_catalog")
    op.drop_table("job_catalog")
    # ### end Alembic commands ###

    #  LE RENOMMAGE SE DEFAIT EN DERNIER, ET L'ORDRE EST LA MOITIE DE LA
    #  CORRECTION. Place en tete de la descente, il rendait le nom
    #  `id_entite_unique` a `entity_membership` alors que `job_catalog` le portait
    #  encore : la descente echouait sur la meme collision que la montee. Une
    #  descente doit etre le MIROIR de sa montee, et non sa copie dans le meme
    #  ordre. Defaut rencontre le 19/08/2026, et seul le rejeu descente-remontee
    #  l'a montre -- une montee seule ne l'aurait jamais revele.
    op.execute(
        "ALTER TABLE entity_membership "
        "RENAME CONSTRAINT uq_entity_membership_id_entity_id TO id_entite_unique"
    )
