"""add indexes and unique constraints

Revision ID: a1b2c3d4e5f6
Revises: 5ad14bbf9fa8
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # access_logs: Einzelne Spalten-Indexes
    op.create_index('ix_access_logs_user_id',    'access_logs', ['user_id'])
    op.create_index('ix_access_logs_room_id',    'access_logs', ['room_id'])
    op.create_index('ix_access_logs_nfc_chip_id','access_logs', ['nfc_chip_id'])
    op.create_index('ix_access_logs_timestamp',  'access_logs', ['timestamp'])

    # access_logs: Zusammengesetzte Indexes für häufige Queries
    op.create_index('ix_access_logs_timestamp_granted', 'access_logs', ['timestamp', 'granted'])
    op.create_index('ix_access_logs_nfc_timestamp',     'access_logs', ['nfc_chip_id', 'timestamp'])

    # permissions: Spalten-Indexes + UNIQUE auf (user_id, room_id)
    op.create_index('ix_permissions_user_id', 'permissions', ['user_id'])
    op.create_index('ix_permissions_room_id', 'permissions', ['room_id'])
    op.create_unique_constraint('uq_permission_user_room', 'permissions', ['user_id', 'room_id'])


def downgrade() -> None:
    op.drop_constraint('uq_permission_user_room', 'permissions', type_='unique')
    op.drop_index('ix_permissions_room_id',  table_name='permissions')
    op.drop_index('ix_permissions_user_id',  table_name='permissions')

    op.drop_index('ix_access_logs_nfc_timestamp',        table_name='access_logs')
    op.drop_index('ix_access_logs_timestamp_granted',    table_name='access_logs')
    op.drop_index('ix_access_logs_timestamp',            table_name='access_logs')
    op.drop_index('ix_access_logs_nfc_chip_id',          table_name='access_logs')
    op.drop_index('ix_access_logs_room_id',              table_name='access_logs')
    op.drop_index('ix_access_logs_user_id',              table_name='access_logs')
