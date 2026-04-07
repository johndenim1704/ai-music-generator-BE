"""create music comments table

Revision ID: 6d4b2a9a1c3e
Revises: f99b3a74b7e6
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d4b2a9a1c3e'
down_revision: Union[str, None] = '85e326e05b86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'music_comments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('music_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.String(length=1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),  # MySQL compatible
        sa.ForeignKeyConstraint(['music_id'], ['music.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['music_comments.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_music_comments_music_id', 'music_comments', ['music_id'])
    op.create_index('ix_music_comments_parent_id', 'music_comments', ['parent_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_music_comments_parent_id', table_name='music_comments')
    op.drop_index('ix_music_comments_music_id', table_name='music_comments')
    op.drop_table('music_comments')
