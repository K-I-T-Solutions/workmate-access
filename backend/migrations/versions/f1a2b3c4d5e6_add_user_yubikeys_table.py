"""add user_yubikeys table

Revision ID: f1a2b3c4d5e6
Revises: e8f3c2d1a4b5
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e8f3c2d1a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    has_table = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'user_yubikeys')"
        )
    ).scalar()
    if not has_table:
        op.create_table(
            'user_yubikeys',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('public_id', sa.String(12), nullable=False, unique=True),
            sa.Column('label', sa.String(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('ix_user_yubikeys_user_id', 'user_yubikeys', ['user_id'])
        op.create_index('ix_user_yubikeys_public_id', 'user_yubikeys', ['public_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_user_yubikeys_public_id', table_name='user_yubikeys')
    op.drop_index('ix_user_yubikeys_user_id', table_name='user_yubikeys')
    op.drop_table('user_yubikeys')
