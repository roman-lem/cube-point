"""organizer pledges

Revision ID: a1c5e7f9b3d2
Revises: b7d4e1f09a3c
Create Date: 2026-09-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c5e7f9b3d2'
down_revision = 'b7d4e1f09a3c'
branch_labels = None
depends_on = None


def upgrade():
    # Existing organizers have no entries: they accept the pledge on their next visit.
    op.create_table('organizer_pledges',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('club_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.String(length=32), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], name=op.f('fk_organizer_pledges_club_id_clubs'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_organizer_pledges_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_organizer_pledges'))
    )
    with op.batch_alter_table('organizer_pledges', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_organizer_pledges_club_id'), ['club_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_organizer_pledges_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('organizer_pledges', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_organizer_pledges_user_id'))
        batch_op.drop_index(batch_op.f('ix_organizer_pledges_club_id'))

    op.drop_table('organizer_pledges')
