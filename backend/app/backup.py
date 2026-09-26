"""SQLite database backups: `flask backup-db` and `flask restore-db NAME`.

The copy is made with the SQLite backup API (sqlite3.Connection.backup), not by
copying the file: it is consistent even while the app is writing, WAL included.
Backups are gzip files cubing-YYYYMMDD-HHMMSS.db.gz in instance/backups/
(in Docker, the backend-data volume). Called on the server by deploy/backup.sh
and deploy/restore.sh.
"""

import gzip
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone

import click
from flask import current_app
from flask.cli import with_appcontext

from .extensions import db

PREFIX = "cubing-"
SUFFIX = ".db.gz"


def backup_dir():
    path = current_app.config.get("BACKUP_DIR") or os.path.join(current_app.instance_path, "backups")
    os.makedirs(path, exist_ok=True)
    return path


def database_path():
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise click.ClickException("Backups work only with an SQLite database file.")
    return url.database


def check_integrity(path):
    connection = sqlite3.connect(path)
    try:
        result = connection.execute("PRAGMA quick_check").fetchone()[0]
    finally:
        connection.close()
    if result != "ok":
        raise click.ClickException(f"The database copy is damaged: {result}")


def copy_database(source_path, target_path):
    """Consistent copy of an SQLite database through the backup API."""
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(target_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def make_backup(label=""):
    """Makes a compressed backup, returns its full path."""
    directory = backup_dir()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"{PREFIX}{stamp}{label}{SUFFIX}"
    raw = os.path.join(directory, name + ".tmp")
    # The file gets its final name only when it is complete, so an interrupted
    # backup never looks like a real one.
    partial = os.path.join(directory, name + ".partial")
    try:
        copy_database(database_path(), raw)
        check_integrity(raw)
        with open(raw, "rb") as source, gzip.open(partial, "wb") as target:
            shutil.copyfileobj(source, target)
        os.replace(partial, os.path.join(directory, name))
    finally:
        for leftover in (raw, partial):
            if os.path.exists(leftover):
                os.remove(leftover)
    return os.path.join(directory, name)


def delete_old_backups(keep_days):
    """Deletes backups older than keep_days, returns their names."""
    directory = backup_dir()
    limit = time.time() - keep_days * 24 * 60 * 60
    deleted = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if name.startswith(PREFIX) and name.endswith(SUFFIX) and os.path.getmtime(path) < limit:
            os.remove(path)
            deleted.append(name)
    return deleted


@click.command("backup-db")
@click.option("--keep-days", type=click.IntRange(min=1), default=None, envvar="BACKUP_KEEP_DAYS",
              help="Also delete backups older than this many days (default: BACKUP_KEEP_DAYS).")
@with_appcontext
def backup_db_command(keep_days):
    """Backs up the database to instance/backups/."""
    path = make_backup()
    click.echo(f"Backup: {os.path.basename(path)} ({os.path.getsize(path)} bytes)")
    if keep_days is not None:
        for name in delete_old_backups(keep_days):
            click.echo(f"Deleted old backup: {name}")


@click.command("restore-db")
@click.argument("name")
@with_appcontext
def restore_db_command(name):
    """Replaces the database with backup NAME from instance/backups/.

    The current database is backed up first (…-before-restore.db.gz).
    Stop the backend before restoring so nobody writes in the meantime.
    """
    directory = backup_dir()
    # Only a file name from the backups folder, no paths.
    path = os.path.join(directory, os.path.basename(name))
    if not name.endswith(SUFFIX) or not os.path.isfile(path):
        raise click.ClickException(f"No backup {name} in {directory}.")

    safety = make_backup("-before-restore")
    click.echo(f"Current database saved: {os.path.basename(safety)}")

    raw = path + ".tmp"
    try:
        with gzip.open(path, "rb") as source, open(raw, "wb") as target:
            shutil.copyfileobj(source, target)
        check_integrity(raw)
        # Through the backup API as well: it writes over the database correctly,
        # including its WAL file, instead of swapping files under SQLite.
        db.engine.dispose()
        copy_database(raw, database_path())
    finally:
        if os.path.exists(raw):
            os.remove(raw)
    click.echo(f"Database restored from {os.path.basename(path)}.")
