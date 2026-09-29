"""age consent

Revision ID: d8e2f4a6b1c9
Revises: a1c5e7f9b3d2
Create Date: 2026-09-29 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8e2f4a6b1c9'
down_revision = 'a1c5e7f9b3d2'
branch_labels = None
depends_on = None

OLD = ('processing', 'publication', 'deleted_name')
NEW = ('processing', 'publication', 'deleted_name', 'age')


def consent_type(*values):
    return sa.Enum(*values, name='consenttype', native_enum=False, create_constraint=True, length=16)


def upgrade():
    # New value in the consent type CHECK constraint: SQLite recreates the table.
    with op.batch_alter_table('user_consents', schema=None) as batch_op:
        batch_op.alter_column(
            'type', existing_type=consent_type(*OLD), type_=consent_type(*NEW),
            existing_nullable=False,
        )


def downgrade():
    op.execute("DELETE FROM user_consents WHERE type = 'age'")
    with op.batch_alter_table('user_consents', schema=None) as batch_op:
        batch_op.alter_column(
            'type', existing_type=consent_type(*NEW), type_=consent_type(*OLD),
            existing_nullable=False,
        )
