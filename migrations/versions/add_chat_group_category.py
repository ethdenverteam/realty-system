"""Add category and filters_json to chat_groups table

Revision ID: add_chat_group_category
Revises: add_chat_filters_json
Create Date: 2026-02-15 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_group_category'
down_revision = 'add_second_contact_2024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category and filters_json columns to chat_groups table
    op.add_column('chat_groups', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('chat_groups', sa.Column('filters_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove category and filters_json columns
    op.drop_column('chat_groups', 'filters_json')
    op.drop_column('chat_groups', 'category')

