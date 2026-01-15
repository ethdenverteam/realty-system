"""Change telegram_id to BigInteger

Revision ID: change_telegram_id_bigint
Revises: eef5d1222136
Create Date: 2026-01-15 22:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_telegram_id_bigint'
down_revision = 'eef5d1222136'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change telegram_id from Integer to BigInteger
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)


def downgrade() -> None:
    # Revert back to Integer (may fail if values are too large)
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)

