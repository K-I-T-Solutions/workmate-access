"""add guest_tokens table

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'guest_tokens',
        sa.Column('id',         sa.String(),  primary_key=True),
        sa.Column('room_id',    sa.String(),  sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('label',      sa.String(),  nullable=True),
        sa.Column('created_by', sa.String(),  nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used',    sa.Boolean(), default=False),
        sa.Column('used_at',    sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('guest_tokens')
