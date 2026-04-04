"""Add license completion form fields to user_licenses

Revision ID: e6b58c729403
Revises: a2ad67efb404
Create Date: 2025-12-02 12:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6b58c729403'
down_revision: Union[str, None] = 'a2ad67efb404'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add license completion form fields."""
    # Add license_pdf_path field (was in model but missing from DB)
    op.add_column('user_licenses', sa.Column('license_pdf_path', sa.String(500), nullable=True))
    
    # Add form status field
    op.add_column('user_licenses', sa.Column('is_form_filled', sa.Boolean(), nullable=True, server_default='0'))
    
    # Add licensee info fields
    op.add_column('user_licenses', sa.Column('licensee_name', sa.String(255), nullable=True))
    op.add_column('user_licenses', sa.Column('licensee_email', sa.String(255), nullable=True))
    op.add_column('user_licenses', sa.Column('project_title', sa.String(255), nullable=True))
    
    # Add signature fields
    op.add_column('user_licenses', sa.Column('is_signed', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('user_licenses', sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_licenses', sa.Column('timezone_offset', sa.String(50), nullable=True))
    
    # Add artist/author fields
    op.add_column('user_licenses', sa.Column('is_artist_same_as_licensee', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('user_licenses', sa.Column('artist_stage_name', sa.String(255), nullable=True))
    op.add_column('user_licenses', sa.Column('author_legal_name', sa.String(255), nullable=True))
    
    # Add PRO fields
    op.add_column('user_licenses', sa.Column('is_pro_registered', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('user_licenses', sa.Column('pro_name', sa.String(255), nullable=True))
    op.add_column('user_licenses', sa.Column('pro_ipi_number', sa.String(255), nullable=True))
    
    # Add optional fields
    op.add_column('user_licenses', sa.Column('phone_number', sa.String(50), nullable=True))
    op.add_column('user_licenses', sa.Column('address', sa.String(500), nullable=True))
    op.add_column('user_licenses', sa.Column('isrc_iswc', sa.String(255), nullable=True))
    
    # Add publisher fields
    op.add_column('user_licenses', sa.Column('has_publisher', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('user_licenses', sa.Column('publisher_name', sa.String(255), nullable=True))
    op.add_column('user_licenses', sa.Column('publisher_pro', sa.String(255), nullable=True))
    op.add_column('user_licenses', sa.Column('publisher_ipi_number', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove license completion form fields."""
    op.drop_column('user_licenses', 'publisher_ipi_number')
    op.drop_column('user_licenses', 'publisher_pro')
    op.drop_column('user_licenses', 'publisher_name')
    op.drop_column('user_licenses', 'has_publisher')
    op.drop_column('user_licenses', 'isrc_iswc')
    op.drop_column('user_licenses', 'address')
    op.drop_column('user_licenses', 'phone_number')
    op.drop_column('user_licenses', 'pro_ipi_number')
    op.drop_column('user_licenses', 'pro_name')
    op.drop_column('user_licenses', 'is_pro_registered')
    op.drop_column('user_licenses', 'author_legal_name')
    op.drop_column('user_licenses', 'artist_stage_name')
    op.drop_column('user_licenses', 'is_artist_same_as_licensee')
    op.drop_column('user_licenses', 'timezone_offset')
    op.drop_column('user_licenses', 'signed_at')
    op.drop_column('user_licenses', 'is_signed')
    op.drop_column('user_licenses', 'project_title')
    op.drop_column('user_licenses', 'licensee_email')
    op.drop_column('user_licenses', 'licensee_name')
    op.drop_column('user_licenses', 'is_form_filled')
    op.drop_column('user_licenses', 'license_pdf_path')

