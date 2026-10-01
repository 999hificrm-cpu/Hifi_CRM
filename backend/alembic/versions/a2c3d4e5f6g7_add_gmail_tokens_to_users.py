"""add_gmail_tokens_to_users

Revision ID: a2c3d4e5f6g7
Revises: 155b06cfc05d
Create Date: 2026-09-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2c3d4e5f6g7'
down_revision: Union[str, None] = '155b06cfc05d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('gmail_tokens', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'gmail_tokens')
