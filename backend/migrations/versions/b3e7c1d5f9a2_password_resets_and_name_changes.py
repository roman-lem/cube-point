"""password resets and display name changes

Revision ID: b3e7c1d5f9a2
Revises: e4b8a2c6d0f1
Create Date: 2026-10-01 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3e7c1d5f9a2'
down_revision = 'e4b8a2c6d0f1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('password_resets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=254), nullable=True),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_resets_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_password_resets')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_password_resets_token_hash'))
    )
    with op.batch_alter_table('password_resets', schema=None) as batch_op:
        batch_op.create_index('ix_password_resets_ip_created_at', ['ip', 'created_at'], unique=False)
        batch_op.create_index('ix_password_resets_user_id_created_at', ['user_id', 'created_at'], unique=False)

    op.create_table('display_name_changes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('old_name', sa.String(length=100), nullable=False),
    sa.Column('new_name', sa.String(length=100), nullable=False),
    sa.Column('changed_at', sa.DateTime(), nullable=False),
    sa.Column('changed_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_display_name_changes_changed_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_display_name_changes_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_display_name_changes'))
    )
    with op.batch_alter_table('display_name_changes', schema=None) as batch_op:
        batch_op.create_index('ix_display_name_changes_user_id_changed_at', ['user_id', 'changed_at'], unique=False)


def downgrade():
    with op.batch_alter_table('display_name_changes', schema=None) as batch_op:
        batch_op.drop_index('ix_display_name_changes_user_id_changed_at')
    op.drop_table('display_name_changes')

    with op.batch_alter_table('password_resets', schema=None) as batch_op:
        batch_op.drop_index('ix_password_resets_user_id_created_at')
        batch_op.drop_index('ix_password_resets_ip_created_at')
    op.drop_table('password_resets')
