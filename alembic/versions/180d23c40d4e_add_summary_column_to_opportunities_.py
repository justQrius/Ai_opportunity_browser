"""Add summary column to opportunities table

Revision ID: 180d23c40d4e
Revises: add_discussions_and_comments
Create Date: 2025-07-28 17:41:31.148968

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '180d23c40d4e'
down_revision = 'add_discussions_and_comments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('opportunities', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('opportunities', 'summary')