"""add bulk coupon fields

Revision ID: e4a2b1c3d4f5
Revises: 6d4b2a9a1c3e
Create Date: 2026-04-06 21:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4a2b1c3d4f5'
down_revision: Union[str, None] = '6d4b2a9a1c3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add buy_count and get_count columns
    op.add_column('coupons', sa.Column('buy_count', sa.Integer(), nullable=True))
    op.add_column('coupons', sa.Column('get_count', sa.Integer(), nullable=True))
    
    # Make value column nullable
    # Note: For MySQL, we need to specify the existing type
    op.alter_column('coupons', 'value',
               existing_type=sa.Float(),
               nullable=True)


def downgrade() -> None:
    # Make value column NOT nullable again (might fail if there are nulls)
    op.alter_column('coupons', 'value',
               existing_type=sa.Float(),
               nullable=False)
               
    # Drop columns
    op.drop_column('coupons', 'get_count')
    op.drop_column('coupons', 'buy_count')
