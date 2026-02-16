"""Add purpose field to chat_groups table

Revision ID: add_chat_group_purpose
Revises: merge_chat_subscription_and_chat_group
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_chat_group_purpose'
down_revision = 'merge_subscription_chat_group'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add purpose column to chat_groups table
    # Default value 'autopublish' для существующих записей (они были созданы для автопубликации)
    op.add_column('chat_groups', sa.Column('purpose', sa.String(length=50), nullable=False, server_default='autopublish'))
    # Создаем индекс для быстрого поиска по purpose
    op.create_index('ix_chat_groups_purpose', 'chat_groups', ['purpose'])


def downgrade() -> None:
    # Remove purpose column and index
    op.drop_index('ix_chat_groups_purpose', table_name='chat_groups')
    op.drop_column('chat_groups', 'purpose')

