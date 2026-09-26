import os
import sqlite3

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine

# Constraint names are set explicitly: without them Alembic cannot
# alter SQLite tables in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))
# render_as_batch alters SQLite tables by recreating them.
# The migrations folder is backend/migrations regardless of the current directory.
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
migrate = Migrate(directory=MIGRATIONS_DIR, render_as_batch=True)

login_manager = LoginManager()
# Checks the X-CSRFToken header on all modifying requests.
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        # By default SQLite neither checks foreign keys nor runs ON DELETE.
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL: reads do not wait for a write, so a meetup with many phones saving
        # attempts at once does not stall. A writer waiting for another one
        # retries for up to 5 seconds (the sqlite3 module's default timeout).
        # The mode is stored in the database file; an in-memory test DB ignores it.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
