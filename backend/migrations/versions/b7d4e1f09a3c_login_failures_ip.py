"""login failures ip

Revision ID: b7d4e1f09a3c
Revises: f2a9c3d4e5b6
Create Date: 2026-09-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d4e1f09a3c'
down_revision = 'f2a9c3d4e5b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('login_failures', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ip', sa.String(length=45), nullable=True))
        batch_op.create_index('ix_login_failures_ip_created_at', ['ip', 'created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('login_failures', schema=None) as batch_op:
        batch_op.drop_index('ix_login_failures_ip_created_at')
        batch_op.drop_column('ip')
