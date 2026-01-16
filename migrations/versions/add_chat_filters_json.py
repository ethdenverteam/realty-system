"""Add filters_json to chats table

Revision ID: add_chat_filters_json
Revises: change_telegram_id_bigint
Create Date: 2026-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_filters_json'
down_revision = 'change_telegram_id_bigint'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add filters_json column to chats table
    op.add_column('chats', sa.Column('filters_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove filters_json column
    op.drop_column('chats', 'filters_json')

