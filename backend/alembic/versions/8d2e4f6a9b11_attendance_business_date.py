"""store attendance business date as DATE

Revision ID: 8d2e4f6a9b11
Revises: 7c1d9e2f4a10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "8d2e4f6a9b11"
down_revision: Union[str, None] = "7c1d9e2f4a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table("attendance_sessions") as batch_op:
        batch_op.alter_column("date", existing_type=sa.DateTime(), type_=sa.Date(), existing_nullable=False)
    # Older request races may have left several open rows. Preserve the newest
    # open shift and close older rows at their login time before adding the
    # partial unique index.
    op.execute(sa.text("""
        WITH ranked_open_shifts AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY organization_id, user_id
                ORDER BY login_at DESC, id DESC
            ) AS row_number
            FROM attendance_sessions
            WHERE logout_at IS NULL
        )
        UPDATE attendance_sessions
        SET logout_at = login_at
        WHERE id IN (
            SELECT id FROM ranked_open_shifts WHERE row_number > 1
        )
    """))
    op.create_index(
        "uq_open_attendance_session_per_user",
        "attendance_sessions",
        ["organization_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("logout_at IS NULL"),
        sqlite_where=sa.text("logout_at IS NULL"),
    )

def downgrade() -> None:
    op.drop_index("uq_open_attendance_session_per_user", table_name="attendance_sessions")
    with op.batch_alter_table("attendance_sessions") as batch_op:
        batch_op.alter_column("date", existing_type=sa.Date(), type_=sa.DateTime(), existing_nullable=False)
