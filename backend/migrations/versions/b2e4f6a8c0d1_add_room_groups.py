"""add room_groups table and group_id to rooms

Revision ID: b2e4f6a8c0d1
Revises: f1a2b3c4d5e6
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2e4f6a8c0d1'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'room_groups',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=False, server_default='#6366f1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.add_column('rooms', sa.Column('group_id', sa.Integer(), sa.ForeignKey('room_groups.id'), nullable=True))


def downgrade():
    op.drop_column('rooms', 'group_id')
    op.drop_table('room_groups')
