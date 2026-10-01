"""email confirmations

Revision ID: e4b8a2c6d0f1
Revises: c5d9e3f7a2b4
Create Date: 2026-10-01 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4b8a2c6d0f1'
down_revision = 'c5d9e3f7a2b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('email_confirmations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=True),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_email_confirmations_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_email_confirmations')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_email_confirmations_token_hash'))
    )
    with op.batch_alter_table('email_confirmations', schema=None) as batch_op:
        batch_op.create_index('ix_email_confirmations_ip_created_at', ['ip', 'created_at'], unique=False)
        batch_op.create_index('ix_email_confirmations_user_id_created_at', ['user_id', 'created_at'], unique=False)

    # users.email now holds only a confirmed address: the flag is not needed.
    # Nobody could bind an email before, so there is nothing to keep.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('email_verified')


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    # Every bound address was confirmed.
    op.execute("UPDATE users SET email_verified = 1 WHERE email IS NOT NULL")

    with op.batch_alter_table('email_confirmations', schema=None) as batch_op:
        batch_op.drop_index('ix_email_confirmations_user_id_created_at')
        batch_op.drop_index('ix_email_confirmations_ip_created_at')

    op.drop_table('email_confirmations')
