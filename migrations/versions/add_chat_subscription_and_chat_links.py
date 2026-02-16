"""
Add ChatSubscriptionTask table and chat_links to ChatGroup

Revision ID: add_chat_subscription_and_chat_links
Revises: add_chat_subscription_task
Create Date: 2024-12-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_subscription_and_chat_links'
down_revision = 'add_chat_subscription_task'  # Эта миграция идет после add_chat_subscription_task
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    columns_chat_groups = []
    
    if 'chat_groups' in tables:
        columns_chat_groups = [col['name'] for col in inspector.get_columns('chat_groups')]
    
    # Add chat_links column to chat_groups if it doesn't exist
    if 'chat_links' not in columns_chat_groups:
        op.add_column('chat_groups', sa.Column('chat_links', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove chat_links column from chat_groups
    op.drop_column('chat_groups', 'chat_links')

