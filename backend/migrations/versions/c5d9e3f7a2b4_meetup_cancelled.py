"""meetup cancelled status

Revision ID: c5d9e3f7a2b4
Revises: d8e2f4a6b1c9
Create Date: 2026-10-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5d9e3f7a2b4'
down_revision = 'd8e2f4a6b1c9'
branch_labels = None
depends_on = None


def meetup_status(*values):
    return sa.Enum(*values, name='meetupstatus', native_enum=False, create_constraint=True, length=16)


def upgrade():
    # New value in the meetup status CHECK constraint: SQLite recreates the table.
    with op.batch_alter_table('meetups', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=meetup_status('planned', 'live', 'finished'),
            type_=meetup_status('planned', 'live', 'finished', 'cancelled'),
            existing_nullable=False,
        )


def downgrade():
    # Without the status, cancelled meetups cannot stay. They have no results:
    # only their events are left, requests and scrambles were deleted on cancelling.
    op.execute(
        "DELETE FROM meetup_events WHERE meetup_id IN "
        "(SELECT id FROM meetups WHERE status = 'cancelled')"
    )
    op.execute("DELETE FROM meetups WHERE status = 'cancelled'")
    with op.batch_alter_table('meetups', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=meetup_status('planned', 'live', 'finished', 'cancelled'),
            type_=meetup_status('planned', 'live', 'finished'),
            existing_nullable=False,
        )
