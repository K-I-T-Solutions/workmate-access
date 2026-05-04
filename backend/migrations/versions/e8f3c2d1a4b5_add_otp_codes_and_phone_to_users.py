"""add otp_codes table and phone_number to users

Revision ID: e8f3c2d1a4b5
Revises: d7a2b3c4e5f6
Create Date: 2026-05-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e8f3c2d1a4b5'
down_revision: Union[str, Sequence[str], None] = 'd7a2b3c4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # phone_number zu users hinzufügen (falls noch nicht vorhanden)
    has_column = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'phone_number')"
        )
    ).scalar()
    if not has_column:
        op.add_column(
            'users',
            sa.Column('phone_number', sa.String(), nullable=True)
        )
        op.create_index('ix_users_phone_number', 'users', ['phone_number'], unique=True)

    # otp_codes Tabelle erstellen (falls noch nicht vorhanden)
    has_table = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'otp_codes')"
        )
    ).scalar()
    if not has_table:
        op.create_table(
            'otp_codes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('phone_number', sa.String(), nullable=False),
            sa.Column('code', sa.String(6), nullable=False),
            sa.Column('room_id', sa.String(), nullable=True),
            sa.Column('channel', sa.String(), server_default='sms'),
            sa.Column('is_used', sa.Boolean(), server_default=sa.text('false')),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_otp_codes_phone_number', 'otp_codes', ['phone_number'])


def downgrade() -> None:
    op.drop_index('ix_otp_codes_phone_number', table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_index('ix_users_phone_number', table_name='users')
    op.drop_column('users', 'phone_number')
