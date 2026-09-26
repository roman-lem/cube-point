"""consents and account deletion

Revision ID: c41d7e2a9b10
Revises: 5b1f0c2e9a47
Create Date: 2026-09-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c41d7e2a9b10'
down_revision = '5b1f0c2e9a47'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user_consents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Enum('processing', 'publication', name='consenttype', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('version', sa.String(length=32), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_consents_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_consents'))
    )
    with op.batch_alter_table('user_consents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_consents_user_id'), ['user_id'], unique=False)

    # Deleted account: no login and no password hash (NULL). Existing accounts
    # have not given consents; they will be asked on next login.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('login', existing_type=sa.String(length=32), nullable=True)
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=True)


def downgrade():
    # Deleted accounts get a placeholder login and a hash nobody can log in with.
    op.execute(
        "UPDATE users SET login = 'deleted-' || id, password_hash = '!' "
        "WHERE deleted_at IS NOT NULL"
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column('login', existing_type=sa.String(length=32), nullable=False)
        batch_op.drop_column('deleted_at')

    with op.batch_alter_table('user_consents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_consents_user_id'))

    op.drop_table('user_consents')
