"""Initial migration with all models

Revision ID: 77fbf0e7da68
Revises: 
Create Date: 2025-07-15 19:57:29.780307

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '77fbf0e7da68'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.Enum('admin', 'moderator', 'expert', 'user', name='userrole'), nullable=False),
        sa.Column('reputation_score', sa.Float(), nullable=False),
        sa.Column('validation_count', sa.Integer(), nullable=False),
        sa.Column('validation_accuracy', sa.Float(), nullable=False),
        sa.Column('expertise_domains', sa.Text(), nullable=True),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('github_url', sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)

    # Create opportunities table
    op.create_table('opportunities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'validated', 'archived', name='opportunitystatus'), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('market_size_estimate', sa.BigInteger(), nullable=True),
        sa.Column('difficulty_level', sa.Integer(), nullable=False),
        sa.Column('time_to_market', sa.Integer(), nullable=True),
        sa.Column('source_urls', sa.JSON(), nullable=True),
        sa.Column('validation_count', sa.Integer(), nullable=False),
        sa.Column('upvotes', sa.Integer(), nullable=False),
        sa.Column('downvotes', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('bookmark_count', sa.Integer(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_opportunities_category'), 'opportunities', ['category'], unique=False)
    op.create_index(op.f('ix_opportunities_status'), 'opportunities', ['status'], unique=False)
    op.create_index(op.f('ix_opportunities_confidence_score'), 'opportunities', ['confidence_score'], unique=False)

    # Create market_signals table
    op.create_table('market_signals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('signal_type', sa.Enum('reddit_post', 'github_issue', 'news_article', 'social_media', 'forum_discussion', name='signaltype'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('author', sa.String(100), nullable=True),
        sa.Column('engagement_metrics', sa.JSON(), nullable=True),
        sa.Column('extracted_keywords', sa.JSON(), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_signals_source'), 'market_signals', ['source'], unique=False)
    op.create_index(op.f('ix_market_signals_signal_type'), 'market_signals', ['signal_type'], unique=False)
    op.create_index(op.f('ix_market_signals_processed'), 'market_signals', ['processed'], unique=False)
    op.create_index(op.f('ix_market_signals_relevance_score'), 'market_signals', ['relevance_score'], unique=False)

    # Create validations table
    op.create_table('validations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('validator_id', sa.String(36), nullable=False),
        sa.Column('validation_type', sa.Enum('market_validation', 'technical_feasibility', 'competitive_analysis', 'user_demand', name='validationtype'), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('evidence_urls', sa.JSON(), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('time_spent_minutes', sa.Integer(), nullable=True),
        sa.Column('helpful_votes', sa.Integer(), nullable=False),
        sa.Column('unhelpful_votes', sa.Integer(), nullable=False),
        sa.Column('is_flagged', sa.Boolean(), nullable=False),
        sa.Column('flag_reason', sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['validator_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validations_opportunity_id'), 'validations', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_validations_validator_id'), 'validations', ['validator_id'], unique=False)
    op.create_index(op.f('ix_validations_validation_type'), 'validations', ['validation_type'], unique=False)

    # Create ai_capability_assessments table
    op.create_table('ai_capability_assessments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('ai_feasibility_score', sa.Float(), nullable=False),
        sa.Column('complexity_level', sa.Enum('low', 'medium', 'high', 'very_high', name='complexitylevel'), nullable=False),
        sa.Column('required_capabilities', sa.JSON(), nullable=False),
        sa.Column('existing_solutions', sa.JSON(), nullable=True),
        sa.Column('technical_challenges', sa.JSON(), nullable=True),
        sa.Column('recommended_approach', sa.Text(), nullable=True),
        sa.Column('estimated_development_time', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_capability_assessments_opportunity_id'), 'ai_capability_assessments', ['opportunity_id'], unique=False)

    # Create implementation_guides table
    op.create_table('implementation_guides',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('overview', sa.Text(), nullable=False),
        sa.Column('technical_requirements', sa.JSON(), nullable=False),
        sa.Column('implementation_steps', sa.JSON(), nullable=False),
        sa.Column('estimated_timeline', sa.JSON(), nullable=True),
        sa.Column('resource_requirements', sa.JSON(), nullable=True),
        sa.Column('risk_factors', sa.JSON(), nullable=True),
        sa.Column('success_metrics', sa.JSON(), nullable=True),
        sa.Column('helpful_votes', sa.Integer(), nullable=False),
        sa.Column('unhelpful_votes', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_implementation_guides_opportunity_id'), 'implementation_guides', ['opportunity_id'], unique=False)

    # Create reputation_events table
    op.create_table('reputation_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.Enum('validation_submitted', 'validation_helpful', 'validation_unhelpful', 'validation_flagged', 'validation_moderated', 'expert_verification', 'badge_earned', 'penalty_applied', name='reputationeventtype'), nullable=False),
        sa.Column('points_change', sa.Float(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('related_validation_id', sa.String(36), nullable=True),
        sa.Column('related_opportunity_id', sa.String(36), nullable=True),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['related_opportunity_id'], ['opportunities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_validation_id'], ['validations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reputation_events_user_id'), 'reputation_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_reputation_events_event_type'), 'reputation_events', ['event_type'], unique=False)

    # Create user_badges table
    op.create_table('user_badges',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('badge_type', sa.Enum('first_validation', 'helpful_validator', 'expert_contributor', 'quality_reviewer', 'community_moderator', 'domain_expert', 'prolific_contributor', 'accuracy_champion', name='badgetype'), nullable=False),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('earned_for', sa.String(500), nullable=True),
        sa.Column('milestone_value', sa.Integer(), nullable=True),
        sa.Column('icon_url', sa.String(500), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_badges_user_id'), 'user_badges', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_badges_badge_type'), 'user_badges', ['badge_type'], unique=False)

    # Create expertise_verifications table
    op.create_table('expertise_verifications',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('domain', sa.String(100), nullable=False),
        sa.Column('verification_method', sa.String(50), nullable=False),
        sa.Column('verification_status', sa.String(20), nullable=False),
        sa.Column('evidence_url', sa.String(500), nullable=True),
        sa.Column('credentials', sa.Text(), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        sa.Column('verified_by', sa.String(36), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('expertise_score', sa.Float(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expertise_verifications_user_id'), 'expertise_verifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_expertise_verifications_domain'), 'expertise_verifications', ['domain'], unique=False)

    # Create reputation_summaries table
    op.create_table('reputation_summaries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('total_reputation_points', sa.Float(), nullable=False),
        sa.Column('reputation_rank', sa.Integer(), nullable=True),
        sa.Column('influence_weight', sa.Float(), nullable=False),
        sa.Column('total_validations', sa.Integer(), nullable=False),
        sa.Column('helpful_validations', sa.Integer(), nullable=False),
        sa.Column('accuracy_score', sa.Float(), nullable=False),
        sa.Column('total_votes_received', sa.Integer(), nullable=False),
        sa.Column('helpful_votes_received', sa.Integer(), nullable=False),
        sa.Column('badges_earned', sa.Integer(), nullable=False),
        sa.Column('verified_domains', sa.Integer(), nullable=False),
        sa.Column('average_expertise_score', sa.Float(), nullable=False),
        sa.Column('days_active', sa.Integer(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('flagged_validations', sa.Integer(), nullable=False),
        sa.Column('moderation_actions', sa.Integer(), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_reputation_summaries_user_id'), 'reputation_summaries', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('reputation_summaries')
    op.drop_table('expertise_verifications')
    op.drop_table('user_badges')
    op.drop_table('reputation_events')
    op.drop_table('implementation_guides')
    op.drop_table('ai_capability_assessments')
    op.drop_table('validations')
    op.drop_table('market_signals')
    op.drop_table('opportunities')
    op.drop_table('users')
    
    # Drop custom enum types
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS opportunitystatus')
    op.execute('DROP TYPE IF EXISTS signaltype')
    op.execute('DROP TYPE IF EXISTS validationtype')
    op.execute('DROP TYPE IF EXISTS complexitylevel')
    op.execute('DROP TYPE IF EXISTS reputationeventtype')
    op.execute('DROP TYPE IF EXISTS badgetype')