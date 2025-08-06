"""Add author_reputation to market_signals

Revision ID: ed2a40a4aa94
Revises: 2549b365e372
Create Date: 2025-08-03 23:29:26.670713

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ed2a40a4aa94'
down_revision = '2549b365e372'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('market_signals', sa.Column('author_reputation', sa.Float(), nullable=True))
    op.add_column('market_signals', sa.Column('comments_count', sa.Integer(), nullable=True))
    op.add_column('market_signals', sa.Column('shares_count', sa.Integer(), nullable=True))
    op.add_column('market_signals', sa.Column('views_count', sa.Integer(), nullable=True))
    op.add_column('market_signals', sa.Column('pain_point_intensity', sa.Float(), nullable=True))
    op.add_column('market_signals', sa.Column('market_validation_signals', sa.JSON(), nullable=True))
    op.add_column('market_signals', sa.Column('processed_at', sa.DateTime(), nullable=True))
    op.add_column('market_signals', sa.Column('processing_version', sa.String(length=50), nullable=True))
    op.add_column('market_signals', sa.Column('keywords', sa.JSON(), nullable=True))
    op.add_column('market_signals', sa.Column('categories', sa.JSON(), nullable=True))
    op.add_column('market_signals', sa.Column('ai_relevance_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('market_signals', 'author_reputation')
    op.drop_column('market_signals', 'comments_count')
    op.drop_column('market_signals', 'shares_count')
    op.drop_column('market_signals', 'views_count')
    op.drop_column('market_signals', 'pain_point_intensity')
    op.drop_column('market_signals', 'market_validation_signals')
    op.drop_column('market_signals', 'processed_at')
    op.drop_column('market_signals', 'processing_version')
    op.drop_column('market_signals', 'keywords')
    op.drop_column('market_signals', 'categories')
    op.drop_column('market_signals', 'ai_relevance_score')