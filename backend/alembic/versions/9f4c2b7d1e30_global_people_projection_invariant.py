"""enforce one tenant projection per global person

Revision ID: 9f4c2b7d1e30
Revises: 8d2e4f6a9b11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f4c2b7d1e30"
down_revision: Union[str, None] = "8d2e4f6a9b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Retain every contact while removing ambiguous duplicate lineage from
    # older rows. The newest projection remains linked to the global master.
    op.execute(sa.text("""
        WITH ranked_projections AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY organization_id, source_global_contact_id
                ORDER BY updated_at DESC, created_at DESC, id DESC
            ) AS row_number
            FROM contacts
            WHERE source_global_contact_id IS NOT NULL
        )
        UPDATE contacts
        SET source_global_contact_id = NULL
        WHERE id IN (
            SELECT id FROM ranked_projections WHERE row_number > 1
        )
    """))
    op.create_index(
        "uq_contact_global_projection",
        "contacts",
        ["organization_id", "source_global_contact_id"],
        unique=True,
        postgresql_where=sa.text("source_global_contact_id IS NOT NULL"),
        sqlite_where=sa.text("source_global_contact_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_contact_global_projection", table_name="contacts")
