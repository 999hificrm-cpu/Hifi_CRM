"""enforce target and active follow-up/claim invariants

Revision ID: 7c1d9e2f4a10
Revises: 651077a665a1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7c1d9e2f4a10"
down_revision: Union[str, None] = "651077a665a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _reconcile_duplicate_active_followups() -> None:
    """Preserve callback history while making the active-task invariant valid.

    Existing installations can contain duplicates created before the partial
    unique index existed.  The newest task remains actionable; older pending
    tasks are cancelled with an explanatory historical note rather than being
    deleted.
    """
    op.execute(sa.text("""
        WITH ranked_followups AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY organization_id, lead_id
                    ORDER BY
                        CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,
                        due_at DESC,
                        updated_at DESC,
                        created_at DESC,
                        id DESC
                ) AS row_number
            FROM tasks
            WHERE task_type = 'FOLLOW_UP'
              AND status = 'PENDING'
              AND lead_id IS NOT NULL
        )
        UPDATE tasks
        SET
            status = 'CANCELLED',
            description = CASE
                WHEN description IS NULL OR description = ''
                    THEN 'Superseded by a newer active follow-up during invariant migration.'
                ELSE description || '\n\nSuperseded by a newer active follow-up during invariant migration.'
            END
        WHERE id IN (
            SELECT id FROM ranked_followups WHERE row_number > 1
        )
    """))


def _reconcile_duplicate_targets() -> None:
    """Keep the latest daily configuration before enforcing its unique key."""
    op.execute(sa.text("""
        WITH ranked_targets AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY organization_id, user_id, target_date
                    ORDER BY updated_at DESC, created_at DESC, id DESC
                ) AS row_number
            FROM telecaller_targets
        )
        DELETE FROM telecaller_targets
        WHERE id IN (
            SELECT id FROM ranked_targets WHERE row_number > 1
        )
    """))


def upgrade() -> None:
    # Reconcile pre-existing invalid rows before creating constraints.  This
    # makes upgrade safe on databases that have already accumulated duplicate
    # callback tasks/configurations.
    _reconcile_duplicate_active_followups()
    _reconcile_duplicate_targets()

    op.create_index(
        "ux_telecaller_target_org_user_date",
        "telecaller_targets",
        ["organization_id", "user_id", "target_date"],
        unique=True,
    )
    # One active follow-up per lead is a database invariant.  PostgreSQL and
    # modern SQLite both support partial indexes; the predicate is ignored by
    # neither backend used by this project.
    op.create_index(
        "uq_active_followup_per_lead",
        "tasks",
        ["organization_id", "lead_id"],
        unique=True,
        postgresql_where=sa.text("task_type = 'FOLLOW_UP' AND status = 'PENDING' AND lead_id IS NOT NULL"),
        sqlite_where=sa.text("task_type = 'FOLLOW_UP' AND status = 'PENDING' AND lead_id IS NOT NULL"),
    )
    op.create_index(
        "uq_company_global_projection",
        "companies",
        ["organization_id", "source_global_company_id"],
        unique=True,
        postgresql_where=sa.text("source_global_company_id IS NOT NULL"),
        sqlite_where=sa.text("source_global_company_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_company_global_projection", table_name="companies")
    op.drop_index("uq_active_followup_per_lead", table_name="tasks")
    op.drop_index("ux_telecaller_target_org_user_date", table_name="telecaller_targets")
