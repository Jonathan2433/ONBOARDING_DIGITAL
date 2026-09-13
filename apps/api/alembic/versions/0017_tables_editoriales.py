"""Les trois tables editoriales du §15 — LOT 6, sous-etape `T1`.

Stories `MVP-L06-US001` a `US007` : toutes en dependent, et aucune des trois
tables n'existait. Mesure du 13/09/2026 sur le schema reel : **29 tables**,
`alembic_version` comprise.

CE QUE CETTE MIGRATION POSE

  `content_page` (§15.1), `content_block` (§15.2) et `internal_link` (§15.3),
  avec les champs communs du §3.1 et les cles COMPOSITES du §25.3.

**CE QU'ALEMBIC AVAIT PROPOSE EN PLUS, ET QUI A ETE RETIRE — LIS CECI AVANT DE
RELANCER UN `--autogenerate`.**

  `alembic revision --autogenerate` a propose, dans le meme `upgrade()` :

      op.drop_index(op.f('ix_person_recherche_nom'), table_name='person')

  **Cet index est celui de la recherche du trombinoscope**, pose en SQL brut par
  la migration `0015`. C'est un index sur EXPRESSION --
  `fn_normaliser_pour_recherche((first_name || ' ') || last_name)` -- et
  autogenerate ne sait pas les reconcilier : il le voit present en base, absent
  des metadonnees, et conclut qu'il faut le detruire.

  **Le livrer aurait supprime la recherche du LOT 5 en silence**, sur une
  migration dont le titre ne parle que de contenus editoriaux. C'est le §7.24 :
  un outil qui reussit ne prouve rien, et seul le RESULTAT discrimine.

  Mesure du 13/09/2026 : l'index n'est declare dans **aucun** module de
  `app/`, et **aucun test n'exigeait son existence**. Le piege etait donc debout
  pour toutes les sous-etapes suivantes. `T1` ajoute ce test -- un test est un
  meilleur vehicule qu'un commentaire (§7.32) -- et il nommera l'index le jour
  ou quelqu'un le fera disparaitre.

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#  Les champs communs du §3.1, identiques sur les trois tables. Les ecrire une
#  fois evite qu'une des trois ne diverge silencieusement d'une autre.
def _champs_communs() -> tuple[sa.Column[Any], ...]:
    return (
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
    )


def upgrade() -> None:
    # -----------------------------------------------------------------------
    #  §15.1 — `content_page`
    # -----------------------------------------------------------------------
    op.create_table(
        "content_page",
        sa.Column("page_type", sa.String(length=32), nullable=False),
        sa.Column("circle_id", sa.Uuid(), nullable=True),
        sa.Column("office_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "page_type IN ('HOME', 'FRAMEWORK', 'CIRCLE', 'OFFICE', 'LEGAL')",
            name=op.f("ck_content_page_page_type_valide"),
        ),
        sa.CheckConstraint(
            "state IN ('draft', 'published', 'archived')",
            name=op.f("ck_content_page_state_valide"),
        ),
        #  L'IMPLICATION SEULE : le §15.1 ecrit « requis pour », jamais
        #  « interdit ailleurs » -- au contraire du §8.4. Voir le module.
        sa.CheckConstraint(
            "page_type <> 'CIRCLE' OR circle_id IS NOT NULL",
            name=op.f("ck_content_page_circle_id_requis_pour_une_page_de_cercle"),
        ),
        sa.CheckConstraint(
            "page_type <> 'OFFICE' OR office_id IS NOT NULL",
            name=op.f("ck_content_page_office_id_requis_pour_une_page_de_bureau"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_content_page_entity_id_entity")
        ),
        #  §25.3 : COMPOSITES. Une page de cercle ne peut pas pointer le cercle
        #  d'une AUTRE entite, et c'est la cle qui l'empeche.
        sa.ForeignKeyConstraint(
            ["circle_id", "entity_id"],
            ["circle.id", "circle.entity_id"],
            name="fk_content_page_circle",
        ),
        sa.ForeignKeyConstraint(
            ["office_id", "entity_id"],
            ["office.id", "office.entity_id"],
            name="fk_content_page_office",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_page")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_content_page_id_entity_id")),
    )
    op.create_index(op.f("ix_content_page_entity_id"), "content_page", ["entity_id"])
    op.create_index(op.f("ix_content_page_circle_id"), "content_page", ["circle_id"])
    op.create_index(op.f("ix_content_page_office_id"), "content_page", ["office_id"])
    #  §15.1 : « unique dans l'entite ET le type ». Partielle, comme les unicites
    #  de `job_catalog`, `circle` et `office` : une page archivee ne doit pas
    #  reserver son slug pour toujours.
    op.create_index(
        "uq_content_page_entity_type_slug_non_archive",
        "content_page",
        ["entity_id", "page_type", "slug"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    #  §15.2 — `content_block`
    # -----------------------------------------------------------------------
    op.create_table(
        "content_block",
        sa.Column("content_page_id", sa.Uuid(), nullable=False),
        sa.Column("block_type", sa.String(length=32), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_champs_communs(),
        #  L'UNION des deux listes du corpus — `DEC-577`. ONZE types, la lecture
        #  la plus large : fusionner detruirait une distinction que le cahier
        #  ecrit en deux puces separees, la separer n'en detruit aucune.
        #  `QO-119` tranchera, et ce sera une migration d'une ligne.
        sa.CheckConstraint(
            "block_type IN ('TITLE', 'RICH_TEXT', 'IMAGE', 'VIDEO', 'LIST', "
            "'CARD', 'LINK', 'PRESENTATION', 'LINK_CARD', 'QUOTE', 'CALL_TO_ACTION')",
            name=op.f("ck_content_block_block_type_valide"),
        ),
        sa.CheckConstraint("display_order >= 0", name=op.f("ck_content_block_ordre_positif")),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_content_block_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["content_page_id", "entity_id"],
            ["content_page.id", "content_page.entity_id"],
            name="fk_content_block_content_page",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_block")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_content_block_id_entity_id")),
    )
    op.create_index(op.f("ix_content_block_entity_id"), "content_block", ["entity_id"])
    op.create_index(op.f("ix_content_block_content_page_id"), "content_block", ["content_page_id"])
    #  UN ORDRE TOTAL : deux blocs de meme rang rendraient l'affichage non
    #  deterministe, defaut que `T2` du LOT 5 a corrige sur le trombinoscope.
    op.create_index(
        "uq_content_block_page_ordre_non_archive",
        "content_block",
        ["content_page_id", "display_order"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    #  §15.3 — `internal_link`
    # -----------------------------------------------------------------------
    op.create_table(
        "internal_link",
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_reference", sa.String(length=64), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_champs_communs(),
        sa.CheckConstraint(
            "link_type IN ('HUB', 'ACADEMY', 'SHAREPOINT', 'OTHER')",
            name=op.f("ck_internal_link_link_type_valide"),
        ),
        sa.CheckConstraint("display_order >= 0", name=op.f("ck_internal_link_ordre_positif")),
        #  BORNE DE FORME, PAS DE PROTOCOLE. Le corpus dit deux fois « une liste
        #  de protocoles autorises » et ne la donne JAMAIS : `QO-120`.
        sa.CheckConstraint("length(btrim(url)) > 0", name=op.f("ck_internal_link_url_non_vide")),
        sa.CheckConstraint(
            "length(btrim(label)) > 0", name=op.f("ck_internal_link_label_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_internal_link_entity_id_entity")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_internal_link")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_internal_link_id_entity_id")),
    )
    op.create_index(op.f("ix_internal_link_entity_id"), "internal_link", ["entity_id"])
    op.create_index(
        "uq_internal_link_entity_ordre_non_archive",
        "internal_link",
        ["entity_id", "display_order"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )


def downgrade() -> None:
    #  L'ordre inverse de la creation : `content_block` reference `content_page`.
    op.drop_index("uq_internal_link_entity_ordre_non_archive", table_name="internal_link")
    op.drop_index(op.f("ix_internal_link_entity_id"), table_name="internal_link")
    op.drop_table("internal_link")

    op.drop_index("uq_content_block_page_ordre_non_archive", table_name="content_block")
    op.drop_index(op.f("ix_content_block_content_page_id"), table_name="content_block")
    op.drop_index(op.f("ix_content_block_entity_id"), table_name="content_block")
    op.drop_table("content_block")

    op.drop_index("uq_content_page_entity_type_slug_non_archive", table_name="content_page")
    op.drop_index(op.f("ix_content_page_office_id"), table_name="content_page")
    op.drop_index(op.f("ix_content_page_circle_id"), table_name="content_page")
    op.drop_index(op.f("ix_content_page_entity_id"), table_name="content_page")
    op.drop_table("content_page")
