"""
Add ChatSubscriptionTask table

Revision ID: add_chat_subscription_task
Revises: add_autopublish_config
Create Date: 2024-12-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_subscription_task'
down_revision = 'add_autopublish_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'chat_subscription_tasks' not in tables:
        op.create_table(
            'chat_subscription_tasks',
            sa.Column('task_id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('group_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('current_index', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_chats', sa.Integer(), nullable=False),
            sa.Column('successful_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('flood_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('flood_wait_until', sa.DateTime(), nullable=True),
            sa.Column('result', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('chat_links', postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_chat_subscription_tasks_user_id'),
            sa.ForeignKeyConstraint(['account_id'], ['telegram_accounts.account_id'], name='fk_chat_subscription_tasks_account_id'),
            sa.ForeignKeyConstraint(['group_id'], ['chat_groups.group_id'], name='fk_chat_subscription_tasks_group_id'),
        )
        op.create_index('ix_chat_subscription_tasks_user_id', 'chat_subscription_tasks', ['user_id'])
        op.create_index('ix_chat_subscription_tasks_account_id', 'chat_subscription_tasks', ['account_id'])
        op.create_index('ix_chat_subscription_tasks_group_id', 'chat_subscription_tasks', ['group_id'])
        op.create_index('ix_chat_subscription_tasks_status', 'chat_subscription_tasks', ['status'])


def downgrade() -> None:
    op.drop_table('chat_subscription_tasks')

