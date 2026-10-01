"""registrations journal

Revision ID: c9f1a3e5b7d2
Revises: b3e7c1d5f9a2
Create Date: 2026-10-01 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9f1a3e5b7d2'
down_revision = 'b3e7c1d5f9a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('registrations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.create_index('ix_registrations_ip_created_at', ['ip', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_registrations_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_registrations_created_at'))
        batch_op.drop_index('ix_registrations_ip_created_at')

    op.drop_table('registrations')
