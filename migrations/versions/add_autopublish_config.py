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
    # Check if table already exists (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'autopublish_configs' not in tables:
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
    else:
        # Table exists - check and add missing columns if needed
        columns = [col['name'] for col in inspector.get_columns('autopublish_configs')]
        
        if 'accounts_config_json' not in columns:
            op.add_column('autopublish_configs', 
                         sa.Column('accounts_config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        
        # Check if indexes exist and create them if missing
        indexes = [idx['name'] for idx in inspector.get_indexes('autopublish_configs')]
        if 'ix_autopublish_configs_user_id' not in indexes:
            try:
                op.create_index('ix_autopublish_configs_user_id', 'autopublish_configs', ['user_id'])
            except Exception:
                pass  # Index might already exist with different name
        if 'ix_autopublish_configs_object_id' not in indexes:
            try:
                op.create_index('ix_autopublish_configs_object_id', 'autopublish_configs', ['object_id'])
            except Exception:
                pass  # Index might already exist with different name


def downgrade() -> None:
    op.drop_table('autopublish_configs')


