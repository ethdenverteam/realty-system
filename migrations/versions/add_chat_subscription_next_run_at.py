"""
Add next_run_at to chat_subscription_tasks for resilient scheduling

Revision ID: add_chat_subscription_next_run_at
Revises: add_chat_group_purpose
Create Date: 2026-02-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_chat_subscription_next_run_at'
down_revision = 'add_chat_group_purpose'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add next_run_at column to chat_subscription_tasks table
    op.add_column('chat_subscription_tasks', sa.Column('next_run_at', sa.DateTime(), nullable=True))
    op.create_index('ix_chat_subscription_tasks_next_run_at', 'chat_subscription_tasks', ['next_run_at'])


def downgrade() -> None:
    # Remove next_run_at column and index
    op.drop_index('ix_chat_subscription_tasks_next_run_at', table_name='chat_subscription_tasks')
    op.drop_column('chat_subscription_tasks', 'next_run_at')


