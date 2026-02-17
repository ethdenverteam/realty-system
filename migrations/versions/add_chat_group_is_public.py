"""
Add is_public to chat_groups table

Revision ID: add_chat_group_is_public
Revises: add_chat_subscription_interval_mode
Create Date: 2026-02-17 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_chat_group_is_public'
down_revision = 'add_chat_subscription_interval_mode'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.add_column('chat_groups', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')))
  op.create_index('ix_chat_groups_is_public', 'chat_groups', ['is_public'])
  # Убираем server_default после инициализации
  op.alter_column('chat_groups', 'is_public', server_default=None)


def downgrade() -> None:
  op.drop_index('ix_chat_groups_is_public', table_name='chat_groups')
  op.drop_column('chat_groups', 'is_public')


