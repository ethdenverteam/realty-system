"""
Add interval_mode to chat_subscription_tasks

Revision ID: add_chat_subscription_interval_mode
Revises: add_chat_subscription_next_run_at
Create Date: 2026-02-17 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_chat_subscription_interval_mode'
down_revision = 'add_chat_subscription_next_run_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chat_subscription_tasks',
        sa.Column('interval_mode', sa.String(length=20), nullable=False, server_default='safe'),
    )
    op.alter_column('chat_subscription_tasks', 'interval_mode', server_default=None)


def downgrade() -> None:
    op.drop_column('chat_subscription_tasks', 'interval_mode')


