"""Add second contact fields to objects

Revision ID: add_second_contact_2024
Revises: add_chat_filters_json
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_second_contact_2024'
down_revision = 'add_chat_filters_json'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if objects table exists
    tables = inspector.get_table_names()
    if 'objects' not in tables:
        return
    
    # Check if columns already exist
    columns = [col['name'] for col in inspector.get_columns('objects')]
    
    if 'contact_name_2' not in columns:
        op.add_column('objects', sa.Column('contact_name_2', sa.String(100), nullable=True))
    
    if 'phone_number_2' not in columns:
        op.add_column('objects', sa.Column('phone_number_2', sa.String(20), nullable=True))


def downgrade() -> None:
    # Check if columns exist before dropping
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    tables = inspector.get_table_names()
    if 'objects' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('objects')]
    
    if 'phone_number_2' in columns:
        op.drop_column('objects', 'phone_number_2')
    
    if 'contact_name_2' in columns:
        op.drop_column('objects', 'contact_name_2')

