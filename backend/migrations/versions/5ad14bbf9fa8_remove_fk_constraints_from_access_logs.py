"""remove fk constraints from access_logs

Revision ID: 5ad14bbf9fa8
Revises: a0e027b89d1f
Create Date: 2026-02-05 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5ad14bbf9fa8'
down_revision: Union[str, Sequence[str], None] = 'a0e027b89d1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove foreign key constraints from access_logs.

    Audit logs should never fail to write - even for unknown
    users or non-existent rooms.
    """
    op.drop_constraint('access_logs_user_id_fkey', 'access_logs', type_='foreignkey')
    op.drop_constraint('access_logs_room_id_fkey', 'access_logs', type_='foreignkey')


def downgrade() -> None:
    """Restore foreign key constraints on access_logs."""
    op.create_foreign_key('access_logs_user_id_fkey', 'access_logs', 'users', ['user_id'], ['id'])
    op.create_foreign_key('access_logs_room_id_fkey', 'access_logs', 'rooms', ['room_id'], ['id'])
