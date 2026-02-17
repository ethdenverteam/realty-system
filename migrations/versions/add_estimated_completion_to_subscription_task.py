"""
Add estimated_completion to chat_subscription_tasks

Revision ID: add_est_completion
Revises: convert_chat_links
Create Date: 2026-02-17 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_est_completion'
down_revision = 'convert_chat_links'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add estimated_completion column to chat_subscription_tasks table
    op.add_column('chat_subscription_tasks', sa.Column('estimated_completion', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove estimated_completion column
    op.drop_column('chat_subscription_tasks', 'estimated_completion')

