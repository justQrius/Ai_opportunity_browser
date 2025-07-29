"""add all missing opportunity columns

Revision ID: 11d19b1bcb83
Revises: ea53eca6f8e8
Create Date: 2025-07-28 22:14:22.095672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '11d19b1bcb83'
down_revision = 'ea53eca6f8e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to opportunities table
    op.add_column('opportunities', sa.Column('geographic_scope', sa.String(100), nullable=True))
    op.add_column('opportunities', sa.Column('validation_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('opportunities', sa.Column('confidence_rating', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('opportunities', sa.Column('ai_feasibility_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('opportunities', sa.Column('competition_analysis', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('competitive_advantage', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('implementation_complexity', sa.String(50), nullable=True))
    op.add_column('opportunities', sa.Column('estimated_development_time', sa.Integer(), nullable=True))
    op.add_column('opportunities', sa.Column('required_team_size', sa.Integer(), nullable=True))
    op.add_column('opportunities', sa.Column('estimated_budget_range', sa.String(100), nullable=True))
    op.add_column('opportunities', sa.Column('revenue_projections', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('monetization_strategies', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('go_to_market_strategy', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('discovery_method', sa.String(100), nullable=True))
    
    # Update status enum to match new values
    op.execute("ALTER TYPE opportunitystatus RENAME TO opportunitystatus_old")
    op.execute("CREATE TYPE opportunitystatus AS ENUM ('discovered', 'analyzing', 'validating', 'validated', 'rejected', 'archived')")
    op.execute("""
        ALTER TABLE opportunities ALTER COLUMN status TYPE opportunitystatus 
        USING CASE 
            WHEN status::text = 'active' THEN 'discovered'::opportunitystatus
            WHEN status::text = 'draft' THEN 'discovered'::opportunitystatus
            WHEN status::text = 'validated' THEN 'validated'::opportunitystatus
            WHEN status::text = 'archived' THEN 'archived'::opportunitystatus
            ELSE 'discovered'::opportunitystatus
        END
    """)
    op.execute("DROP TYPE opportunitystatus_old")
    
    # Update market_size_estimate from BigInteger to JSON
    op.drop_column('opportunities', 'market_size_estimate')
    op.add_column('opportunities', sa.Column('market_size_estimate', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove added columns
    op.drop_column('opportunities', 'geographic_scope')
    op.drop_column('opportunities', 'validation_score')
    op.drop_column('opportunities', 'confidence_rating')
    op.drop_column('opportunities', 'ai_feasibility_score')
    op.drop_column('opportunities', 'competition_analysis')
    op.drop_column('opportunities', 'competitive_advantage')
    op.drop_column('opportunities', 'implementation_complexity')
    op.drop_column('opportunities', 'estimated_development_time')
    op.drop_column('opportunities', 'required_team_size')
    op.drop_column('opportunities', 'estimated_budget_range')
    op.drop_column('opportunities', 'revenue_projections')
    op.drop_column('opportunities', 'monetization_strategies')
    op.drop_column('opportunities', 'go_to_market_strategy')
    op.drop_column('opportunities', 'discovery_method')
    
    # Revert status enum
    op.execute("ALTER TYPE opportunitystatus RENAME TO opportunitystatus_old")
    op.execute("CREATE TYPE opportunitystatus AS ENUM ('draft', 'active', 'validated', 'archived')")
    op.execute("ALTER TABLE opportunities ALTER COLUMN status TYPE opportunitystatus USING 'draft'::opportunitystatus")
    op.execute("DROP TYPE opportunitystatus_old")
    
    # Revert market_size_estimate to BigInteger
    op.drop_column('opportunities', 'market_size_estimate')
    op.add_column('opportunities', sa.Column('market_size_estimate', sa.BigInteger(), nullable=True))