"""add presence table

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'presence',
        sa.Column('id',         sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('user_id',    sa.String(),   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('room_id',    sa.String(),   sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('entered_at', sa.DateTime(), nullable=True),
        sa.Column('left_at',    sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('presence')
