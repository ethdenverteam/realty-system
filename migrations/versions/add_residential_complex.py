"""
Add residential_complex field to objects table

Revision ID: add_residential_complex
Revises: add_autopublish_config
Create Date: 2024-12-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_residential_complex'
down_revision = 'add_autopublish_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if objects table exists
    tables = inspector.get_table_names()
    if 'objects' not in tables:
        return
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('objects')]
    
    if 'residential_complex' not in columns:
        op.add_column('objects', 
                     sa.Column('residential_complex', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Check if column exists before dropping
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    tables = inspector.get_table_names()
    if 'objects' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('objects')]
    
    if 'residential_complex' in columns:
        op.drop_column('objects', 'residential_complex')

