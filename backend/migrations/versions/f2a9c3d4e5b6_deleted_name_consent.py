"""deleted_name consent

Revision ID: f2a9c3d4e5b6
Revises: c41d7e2a9b10
Create Date: 2026-09-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a9c3d4e5b6'
down_revision = 'c41d7e2a9b10'
branch_labels = None
depends_on = None


def consent_type(*values):
    return sa.Enum(*values, name='consenttype', native_enum=False, create_constraint=True, length=16)


def upgrade():
    # New value in the consent type CHECK constraint: SQLite recreates the table.
    with op.batch_alter_table('user_consents', schema=None) as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=consent_type('processing', 'publication'),
            type_=consent_type('processing', 'publication', 'deleted_name'),
            existing_nullable=False,
        )


def downgrade():
    # Without the consent, a deleted account cannot keep its name.
    op.execute(
        "UPDATE users SET display_name = 'Удалённый участник' WHERE id IN "
        "(SELECT user_id FROM user_consents WHERE type = 'deleted_name')"
    )
    op.execute("DELETE FROM user_consents WHERE type = 'deleted_name'")
    with op.batch_alter_table('user_consents', schema=None) as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=consent_type('processing', 'publication', 'deleted_name'),
            type_=consent_type('processing', 'publication'),
            existing_nullable=False,
        )
