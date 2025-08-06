"""add_default_timestamps_to_opportunities

Revision ID: 7076db7b41d1
Revises: ed2a40a4aa94
Create Date: 2025-08-05 22:29:27.723704

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '7076db7b41d1'
down_revision = 'ed2a40a4aa94'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add default values for created_at and updated_at columns in opportunities table
    op.execute(text("ALTER TABLE opportunities ALTER COLUMN created_at SET DEFAULT NOW()"))
    op.execute(text("ALTER TABLE opportunities ALTER COLUMN updated_at SET DEFAULT NOW()"))
    
    # Update existing NULL values (if any) with current timestamp
    op.execute(text("UPDATE opportunities SET created_at = NOW() WHERE created_at IS NULL"))
    op.execute(text("UPDATE opportunities SET updated_at = NOW() WHERE updated_at IS NULL"))


def downgrade() -> None:
    # Remove default values
    op.execute(text("ALTER TABLE opportunities ALTER COLUMN created_at DROP DEFAULT"))
    op.execute(text("ALTER TABLE opportunities ALTER COLUMN updated_at DROP DEFAULT"))