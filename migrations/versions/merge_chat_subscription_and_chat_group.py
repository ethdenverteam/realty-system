"""Merge chat subscription and chat group branches

Revision ID: merge_subscription_chat_group
Revises: ('add_subscription_chat_links', 'add_chat_group_category')
Create Date: 2024-12-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_subscription_chat_group'
down_revision = ('add_subscription_chat_links', 'add_chat_group_category')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration - no changes needed, just merging branches
    pass


def downgrade() -> None:
    # Merge migration - no changes needed
    pass

