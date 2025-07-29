"""add target_industries to opportunities

Revision ID: ea53eca6f8e8
Revises: 7a807eb0ea74
Create Date: 2025-07-28 22:11:13.195162

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea53eca6f8e8'
down_revision = '7a807eb0ea74'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('opportunities', sa.Column('target_industries', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('opportunities', 'target_industries')