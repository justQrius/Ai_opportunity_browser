"""Add discussions and comments tables

Revision ID: add_discussions_and_comments
Revises: 77fbf0e7da68
Create Date: 2025-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_discussions_and_comments'
down_revision = '77fbf0e7da68'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create discussions table
    op.create_table('discussions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('author_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('discussion_type', sa.Enum('general', 'technical', 'market_analysis', 'implementation', 'business_model', name='discussiontype'), nullable=False),
        sa.Column('status', sa.Enum('active', 'locked', 'archived', 'deleted', name='discussionstatus'), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('upvotes', sa.Integer(), nullable=False),
        sa.Column('downvotes', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=False),
        sa.Column('is_flagged', sa.Boolean(), nullable=False),
        sa.Column('flag_count', sa.Integer(), nullable=False),
        sa.Column('moderator_reviewed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discussions_author_id'), 'discussions', ['author_id'], unique=False)
    op.create_index(op.f('ix_discussions_discussion_type'), 'discussions', ['discussion_type'], unique=False)
    op.create_index(op.f('ix_discussions_opportunity_id'), 'discussions', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_discussions_status'), 'discussions', ['status'], unique=False)

    # Create comments table
    op.create_table('comments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('discussion_id', sa.String(36), nullable=False),
        sa.Column('author_id', sa.String(36), nullable=False),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('upvotes', sa.Integer(), nullable=False),
        sa.Column('downvotes', sa.Integer(), nullable=False),
        sa.Column('is_flagged', sa.Boolean(), nullable=False),
        sa.Column('flag_count', sa.Integer(), nullable=False),
        sa.Column('moderator_reviewed', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('reply_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['discussion_id'], ['discussions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_author_id'), 'comments', ['author_id'], unique=False)
    op.create_index(op.f('ix_comments_discussion_id'), 'comments', ['discussion_id'], unique=False)
    op.create_index(op.f('ix_comments_parent_id'), 'comments', ['parent_id'], unique=False)

    # Create discussion_votes table
    op.create_table('discussion_votes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('discussion_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('vote_type', sa.Enum('upvote', 'downvote', name='votetype'), nullable=False),
        sa.ForeignKeyConstraint(['discussion_id'], ['discussions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'discussion_id', name='uq_discussion_votes_user_discussion')
    )
    op.create_index(op.f('ix_discussion_votes_discussion_id'), 'discussion_votes', ['discussion_id'], unique=False)
    op.create_index(op.f('ix_discussion_votes_user_id'), 'discussion_votes', ['user_id'], unique=False)

    # Create comment_votes table
    op.create_table('comment_votes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('comment_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('vote_type', sa.Enum('upvote', 'downvote', name='votetype'), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'comment_id', name='uq_comment_votes_user_comment')
    )
    op.create_index(op.f('ix_comment_votes_comment_id'), 'comment_votes', ['comment_id'], unique=False)
    op.create_index(op.f('ix_comment_votes_user_id'), 'comment_votes', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_comment_votes_user_id'), table_name='comment_votes')
    op.drop_index(op.f('ix_comment_votes_comment_id'), table_name='comment_votes')
    op.drop_table('comment_votes')
    
    op.drop_index(op.f('ix_discussion_votes_user_id'), table_name='discussion_votes')
    op.drop_index(op.f('ix_discussion_votes_discussion_id'), table_name='discussion_votes')
    op.drop_table('discussion_votes')
    
    op.drop_index(op.f('ix_comments_parent_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_discussion_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_author_id'), table_name='comments')
    op.drop_table('comments')
    
    op.drop_index(op.f('ix_discussions_status'), table_name='discussions')
    op.drop_index(op.f('ix_discussions_opportunity_id'), table_name='discussions')
    op.drop_index(op.f('ix_discussions_discussion_type'), table_name='discussions')
    op.drop_index(op.f('ix_discussions_author_id'), table_name='discussions')
    op.drop_table('discussions')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS votetype')
    op.execute('DROP TYPE IF EXISTS discussionstatus')
    op.execute('DROP TYPE IF EXISTS discussiontype')