"""add nfc_chips table and migrate data from users.nfc_chip_id

Revision ID: c3f8a1b2d4e6
Revises: 5ad14bbf9fa8
Create Date: 2026-02-05 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1b2d4e6'
down_revision: Union[str, Sequence[str], None] = '5ad14bbf9fa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Neue Tabelle erstellen (nur falls noch nicht vorhanden, z.B. durch create_all)
    has_table = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'nfc_chips')")
    ).scalar()
    if not has_table:
        op.create_table(
            'nfc_chips',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False, index=True),
            sa.Column('chip_uid', sa.String(), nullable=False, unique=True, index=True),
            sa.Column('label', sa.String(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    # 2. Bestehende nfc_chip_id Daten migrieren (nur falls Spalte noch existiert)
    has_column = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'nfc_chip_id')")
    ).scalar()
    if has_column:
        results = conn.execute(
            sa.text("SELECT id, nfc_chip_id FROM users WHERE nfc_chip_id IS NOT NULL AND nfc_chip_id != ''")
        )
        for row in results:
            conn.execute(
                sa.text("INSERT INTO nfc_chips (user_id, chip_uid, label) VALUES (:user_id, :chip_uid, :label)"),
                {"user_id": row[0], "chip_uid": row[1], "label": "Migriert"},
            )
        # 3. Alte Spalte entfernen
        op.drop_column('users', 'nfc_chip_id')


def downgrade() -> None:
    # 1. Spalte wieder hinzufügen
    op.add_column('users', sa.Column('nfc_chip_id', sa.String(), unique=True, nullable=True))

    # 2. Daten zurückmigrieren (nur erster aktiver Chip pro User)
    conn = op.get_bind()
    results = conn.execute(
        sa.text("SELECT DISTINCT ON (user_id) user_id, chip_uid FROM nfc_chips WHERE is_active = true ORDER BY user_id, id")
    )
    for row in results:
        conn.execute(
            sa.text("UPDATE users SET nfc_chip_id = :chip_uid WHERE id = :user_id"),
            {"chip_uid": row[1], "user_id": row[0]},
        )

    # 3. Tabelle entfernen
    op.drop_table('nfc_chips')
