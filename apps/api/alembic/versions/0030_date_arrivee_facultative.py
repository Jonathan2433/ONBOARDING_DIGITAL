"""Rendre la date d'arrivee facultative sans perdre l'historique d'appartenance.

Revision ID: 0030
Revises: 0029
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `membership_started_on` porte le debut technique de la periode lorsque la
    # date RH n'est pas encore connue. La colonne reste nullable afin que les
    # INSERT historiques qui donnent `arrival_date` restent compatibles ; la
    # contrainte garantit qu'au moins une des deux dates est toujours presente.
    op.execute(
        "ALTER TABLE entity_membership DROP CONSTRAINT ex_entity_membership_sans_chevauchement"
    )
    op.execute(
        "ALTER TABLE entity_membership DROP CONSTRAINT ck_entity_membership_depart_apres_arrivee"
    )
    op.drop_column("entity_membership", "period")

    op.add_column(
        "entity_membership",
        sa.Column("membership_started_on", sa.Date(), nullable=True),
    )
    op.execute(
        "UPDATE entity_membership SET membership_started_on = arrival_date "
        "WHERE membership_started_on IS NULL"
    )
    op.alter_column("entity_membership", "arrival_date", existing_type=sa.Date(), nullable=True)
    op.add_column(
        "entity_membership",
        sa.Column(
            "period",
            postgresql.DATERANGE(),
            sa.Computed(
                "daterange(COALESCE(arrival_date, membership_started_on), departure_date)",
                persisted=True,
            ),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_entity_membership_debut_appartenance_present"),
        "entity_membership",
        "arrival_date IS NOT NULL OR membership_started_on IS NOT NULL",
    )
    op.create_check_constraint(
        op.f("ck_entity_membership_depart_apres_debut_appartenance"),
        "entity_membership",
        "departure_date IS NULL OR departure_date >= COALESCE(arrival_date, membership_started_on)",
    )
    op.create_exclude_constraint(
        "ex_entity_membership_sans_chevauchement",
        "entity_membership",
        ("person_id", "="),
        ("period", "&&"),
        using="gist",
    )


def downgrade() -> None:
    # Un downgrade ne peut pas representer « date inconnue » : on restaure la
    # date technique pour conserver les lignes plutot que de les perdre.
    op.execute(
        "ALTER TABLE entity_membership DROP CONSTRAINT ex_entity_membership_sans_chevauchement"
    )
    op.execute(
        "ALTER TABLE entity_membership "
        "DROP CONSTRAINT ck_entity_membership_depart_apres_debut_appartenance"
    )
    op.execute(
        "ALTER TABLE entity_membership "
        "DROP CONSTRAINT ck_entity_membership_debut_appartenance_present"
    )
    op.drop_column("entity_membership", "period")
    op.execute(
        "UPDATE entity_membership SET arrival_date = membership_started_on "
        "WHERE arrival_date IS NULL"
    )
    op.alter_column("entity_membership", "arrival_date", existing_type=sa.Date(), nullable=False)
    op.drop_column("entity_membership", "membership_started_on")
    op.add_column(
        "entity_membership",
        sa.Column(
            "period",
            postgresql.DATERANGE(),
            sa.Computed("daterange(arrival_date, departure_date)", persisted=True),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_entity_membership_depart_apres_arrivee"),
        "entity_membership",
        "departure_date IS NULL OR departure_date >= arrival_date",
    )
    op.create_exclude_constraint(
        "ex_entity_membership_sans_chevauchement",
        "entity_membership",
        ("person_id", "="),
        ("period", "&&"),
        using="gist",
    )
