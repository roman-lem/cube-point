"""attempt history

Revision ID: 5b1f0c2e9a47
Revises: e8fb5dc472df
Create Date: 2026-09-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b1f0c2e9a47'
down_revision = 'e8fb5dc472df'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('attempt_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attempt_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=True),
    sa.Column('penalty', sa.Enum('none', 'plus2', 'dnf', 'dns', name='penalty', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('solution', sa.Text(), nullable=True),
    sa.Column('changed_by', sa.Integer(), nullable=True),
    sa.Column('changed_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['attempt_id'], ['attempts.id'], name=op.f('fk_attempt_history_attempt_id_attempts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_attempt_history_changed_by_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attempt_history'))
    )
    with op.batch_alter_table('attempt_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_attempt_history_attempt_id'), ['attempt_id'], unique=False)

    # Начальная запись для уже сохранённых попыток — из текущих значений:
    # исходный результат попыток, которые правили раньше, уже не восстановить.
    op.execute(
        "INSERT INTO attempt_history (attempt_id, value, penalty, solution, changed_by, changed_at) "
        "SELECT id, value, penalty, solution, entered_by, COALESCE(updated_at, submitted_at) "
        "FROM attempts"
    )


def downgrade():
    with op.batch_alter_table('attempt_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_attempt_history_attempt_id'))

    op.drop_table('attempt_history')
