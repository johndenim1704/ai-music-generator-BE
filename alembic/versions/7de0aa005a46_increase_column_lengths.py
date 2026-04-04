"""increase_column_lengths

Revision ID: 7de0aa005a46
Revises: 985e4babcba5
Create Date: 2025-06-09 16:58:02.292154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7de0aa005a46'
down_revision: Union[str, None] = '985e4babcba5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alter provider_id in auth_providers
    op.alter_column('auth_providers', 'provider_id',
                    type_=sa.String(length=512),
                    existing_type=sa.String(length=255))
    
def downgrade() -> None:
    # Revert provider_id in auth_providers
    op.alter_column('auth_providers', 'provider_id',
                    type_=sa.String(length=255),
                    existing_type=sa.String(length=512))
    