"""Add cached_at to chats table

Revision ID: add_chat_cached_at
Revises: add_chat_filters_json
Create Date: 2026-02-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_chat_cached_at'
down_revision = 'add_chat_filters_json'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cached_at column to chats table
    op.add_column('chats', sa.Column('cached_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove cached_at column
    op.drop_column('chats', 'cached_at')

