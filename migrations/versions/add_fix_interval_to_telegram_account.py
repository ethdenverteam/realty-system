"""
Add fix_interval_minutes to telegram_accounts for fix mode

Revision ID: add_fix_interval_account
Revises: add_account_publication_queue
Create Date: 2026-02-18 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_fix_interval_account'
down_revision = 'add_account_publication_queue'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if telegram_accounts table exists
    tables = inspector.get_table_names()
    if 'telegram_accounts' not in tables:
        return
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('telegram_accounts')]
    
    if 'fix_interval_minutes' not in columns:
        op.add_column('telegram_accounts', sa.Column('fix_interval_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Check if column exists before dropping
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    tables = inspector.get_table_names()
    if 'telegram_accounts' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('telegram_accounts')]
    
    if 'fix_interval_minutes' in columns:
        op.drop_column('telegram_accounts', 'fix_interval_minutes')

