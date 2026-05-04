"""rename zitadel_id to keycloak_id

Revision ID: d7a2b3c4e5f6
Revises: c3f8a1b2d4e6
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd7a2b3c4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1b2d4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename zitadel_id column to keycloak_id."""
    op.alter_column('users', 'zitadel_id', new_column_name='keycloak_id')


def downgrade() -> None:
    """Revert keycloak_id back to zitadel_id."""
    op.alter_column('users', 'keycloak_id', new_column_name='zitadel_id')
