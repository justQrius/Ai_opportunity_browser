"""fix_opportunity_status_case_sensitivity

Revision ID: 2549b365e372
Revises: 11d19b1bcb83
Create Date: 2025-07-28 23:03:34.996972

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2549b365e372'
down_revision = '11d19b1bcb83'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values to existing enum type
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'DISCOVERED'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'ANALYZING'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'VALIDATING'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'VALIDATED'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'REJECTED'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'ARCHIVED'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'ACTIVE'")
    op.execute("ALTER TYPE opportunitystatus ADD VALUE IF NOT EXISTS 'DRAFT'")
    
    # Update opportunity status values to match Python enum case
    op.execute("UPDATE opportunities SET status = 'DISCOVERED' WHERE status = 'discovered'")
    op.execute("UPDATE opportunities SET status = 'ANALYZING' WHERE status = 'analyzing'")
    op.execute("UPDATE opportunities SET status = 'VALIDATING' WHERE status = 'validating'") 
    op.execute("UPDATE opportunities SET status = 'VALIDATED' WHERE status = 'validated'")
    op.execute("UPDATE opportunities SET status = 'REJECTED' WHERE status = 'rejected'")
    op.execute("UPDATE opportunities SET status = 'ARCHIVED' WHERE status = 'archived'")
    op.execute("UPDATE opportunities SET status = 'ACTIVE' WHERE status = 'active'")
    op.execute("UPDATE opportunities SET status = 'DRAFT' WHERE status = 'draft'")


def downgrade() -> None:
    # Revert to lowercase values
    op.execute("UPDATE opportunities SET status = 'discovered' WHERE status = 'DISCOVERED'")
    op.execute("UPDATE opportunities SET status = 'analyzing' WHERE status = 'ANALYZING'")
    op.execute("UPDATE opportunities SET status = 'validating' WHERE status = 'VALIDATING'")
    op.execute("UPDATE opportunities SET status = 'validated' WHERE status = 'VALIDATED'")
    op.execute("UPDATE opportunities SET status = 'rejected' WHERE status = 'REJECTED'")
    op.execute("UPDATE opportunities SET status = 'archived' WHERE status = 'ARCHIVED'")
    op.execute("UPDATE opportunities SET status = 'active' WHERE status = 'ACTIVE'")
    op.execute("UPDATE opportunities SET status = 'draft' WHERE status = 'DRAFT'")