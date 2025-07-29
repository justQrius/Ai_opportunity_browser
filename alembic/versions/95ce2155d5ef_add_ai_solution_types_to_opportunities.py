"""add ai_solution_types to opportunities

Revision ID: 95ce2155d5ef
Revises: 180d23c40d4e
Create Date: 2025-07-28 21:52:09.816653

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '95ce2155d5ef'
down_revision = '180d23c40d4e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('opportunities', sa.Column('ai_solution_types', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('opportunities', 'ai_solution_types')