"""add workmate_id to users

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'workmate_id', sa.String(),
        nullable=True,
        comment='WM-100 — plattformübergreifende ID'
    ))
    op.create_unique_constraint('uq_users_workmate_id', 'users', ['workmate_id'])
    op.create_index('ix_users_workmate_id', 'users', ['workmate_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_workmate_id', table_name='users')
    op.drop_constraint('uq_users_workmate_id', 'users', type_='unique')
    op.drop_column('users', 'workmate_id')
