"""add time constraints to permissions

Revision ID: c1d2e3f4a5b6
Revises: b2e4f6a8c0d1
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = 'b2e4f6a8c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('permissions', sa.Column('valid_from',  sa.Date(), nullable=True))
    op.add_column('permissions', sa.Column('valid_until', sa.Date(), nullable=True))
    op.add_column('permissions', sa.Column('time_from',   sa.Time(), nullable=True))
    op.add_column('permissions', sa.Column('time_until',  sa.Time(), nullable=True))
    op.add_column('permissions', sa.Column('weekdays',    sa.String(), nullable=True))


def downgrade():
    op.drop_column('permissions', 'weekdays')
    op.drop_column('permissions', 'time_until')
    op.drop_column('permissions', 'time_from')
    op.drop_column('permissions', 'valid_until')
    op.drop_column('permissions', 'valid_from')
