"""add required_capabilities to opportunities

Revision ID: 7a807eb0ea74
Revises: 95ce2155d5ef
Create Date: 2025-07-28 22:01:16.684089

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a807eb0ea74'
down_revision = '95ce2155d5ef'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('opportunities', sa.Column('required_capabilities', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('opportunities', 'required_capabilities')