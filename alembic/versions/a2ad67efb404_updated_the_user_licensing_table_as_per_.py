"""updated the user_licensing table as per the new chnages

Revision ID: a2ad67efb404
Revises: 46a15d7d5717
Create Date: 2025-12-02 12:02:48.611172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2ad67efb404'
down_revision: Union[str, None] = '46a15d7d5717'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
