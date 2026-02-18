"""Add account_publication_queues table

Revision ID: add_account_publication_queue
Revises: add_autopublish_config
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_account_publication_queue'
down_revision = 'add_autopublish_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'account_publication_queues' not in tables:
        op.create_table(
            'account_publication_queues',
            sa.Column('queue_id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('object_id', sa.String(length=50), nullable=False),
            sa.Column('chat_id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('scheduled_time', sa.DateTime(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('message_id', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['object_id'], ['objects.object_id'], name='fk_account_publication_queues_object_id'),
            sa.ForeignKeyConstraint(['chat_id'], ['chats.chat_id'], name='fk_account_publication_queues_chat_id'),
            sa.ForeignKeyConstraint(['account_id'], ['telegram_accounts.account_id'], name='fk_account_publication_queues_account_id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_account_publication_queues_user_id'),
        )
        op.create_index('ix_account_publication_queues_object_id', 'account_publication_queues', ['object_id'])
        op.create_index('ix_account_publication_queues_chat_id', 'account_publication_queues', ['chat_id'])
        op.create_index('ix_account_publication_queues_account_id', 'account_publication_queues', ['account_id'])
        op.create_index('ix_account_publication_queues_user_id', 'account_publication_queues', ['user_id'])
        op.create_index('ix_account_publication_queues_scheduled_time', 'account_publication_queues', ['scheduled_time'])
        op.create_index('ix_account_publication_queues_status', 'account_publication_queues', ['status'])


def downgrade() -> None:
    op.drop_table('account_publication_queues')

