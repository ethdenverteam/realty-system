"""
Add AutopublishConfig table

Revision ID: add_autopublish_config
Revises: add_chat_cached_at
Create Date: 2026-02-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_autopublish_config'
down_revision = 'add_chat_cached_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'autopublish_configs',
        sa.Column('config_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('object_id', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('bot_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('accounts_config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_autopublish_configs_user_id'),
        sa.ForeignKeyConstraint(['object_id'], ['objects.object_id'], name='fk_autopublish_configs_object_id'),
    )
    op.create_index('ix_autopublish_configs_user_id', 'autopublish_configs', ['user_id'])
    op.create_index('ix_autopublish_configs_object_id', 'autopublish_configs', ['object_id'])


def downgrade() -> None:
    op.drop_table('autopublish_configs')


