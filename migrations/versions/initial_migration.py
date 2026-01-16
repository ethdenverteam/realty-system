"""Initial migration - create base tables

Revision ID: eef5d1222136
Revises: 
Create Date: 2026-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'eef5d1222136'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a placeholder migration
    # The actual tables should already exist in the database
    # This migration exists only to establish the revision chain
    pass


def downgrade() -> None:
    pass

