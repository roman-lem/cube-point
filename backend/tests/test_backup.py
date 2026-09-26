import gzip
import os
import sqlite3
import time

import pytest

from app import create_app
from app.extensions import db
from app.models import User

from .conftest import TEST_CONFIG


@pytest.fixture
def file_app(tmp_path):
    """App with an SQLite file (backups do not work with an in-memory DB)."""
    app = create_app({
        **TEST_CONFIG,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'cubing.db'}",
        "BACKUP_DIR": str(tmp_path / "backups"),
    })
    with app.app_context():
        db.create_all()
        db.session.add(User(login="anna", display_name="Анна"))
        db.session.commit()
    yield app
    with app.app_context():
        db.engine.dispose()


def run(app, *args):
    result = app.test_cli_runner().invoke(args=list(args))
    assert result.exit_code == 0, result.output
    return result.output


def backups(app):
    return sorted(os.listdir(app.config["BACKUP_DIR"]))


def logins_in(path):
    connection = sqlite3.connect(path)
    try:
        return [row[0] for row in connection.execute("SELECT login FROM users ORDER BY login")]
    finally:
        connection.close()


def test_database_uses_wal(file_app):
    with file_app.app_context():
        mode = db.session.execute(db.text("PRAGMA journal_mode")).scalar()
    assert mode == "wal"


def test_backup_is_compressed_copy_of_database(file_app, tmp_path):
    run(file_app, "backup-db")

    [name] = backups(file_app)
    assert name.startswith("cubing-") and name.endswith(".db.gz")
    copy = tmp_path / "copy.db"
    with gzip.open(os.path.join(file_app.config["BACKUP_DIR"], name)) as source:
        copy.write_bytes(source.read())
    assert logins_in(copy) == ["anna"]


def test_backup_deletes_only_old_backups(file_app):
    directory = file_app.config["BACKUP_DIR"]
    os.makedirs(directory)
    old = os.path.join(directory, "cubing-20260101-030000.db.gz")
    recent = os.path.join(directory, "cubing-20260920-030000.db.gz")
    other = os.path.join(directory, "notes.txt")
    for path in (old, recent, other):
        open(path, "wb").close()
    eight_days_ago = time.time() - 8 * 24 * 60 * 60
    os.utime(old, (eight_days_ago, eight_days_ago))
    os.utime(other, (eight_days_ago, eight_days_ago))

    run(file_app, "backup-db", "--keep-days", "7")

    names = backups(file_app)
    assert "cubing-20260101-030000.db.gz" not in names
    assert "cubing-20260920-030000.db.gz" in names
    assert "notes.txt" in names
    assert len(names) == 3


def test_restore_returns_database_to_backup(file_app):
    run(file_app, "backup-db")
    [name] = backups(file_app)
    with file_app.app_context():
        db.session.add(User(login="boris", display_name="Борис"))
        db.session.commit()

    run(file_app, "restore-db", name)

    with file_app.app_context():
        assert db.session.scalars(db.select(User.login)).all() == ["anna"]
    # The database before the restore is saved too.
    [safety] = [n for n in backups(file_app) if n.endswith("-before-restore.db.gz")]
    assert safety


def test_restore_rejects_unknown_backup(file_app):
    result = file_app.test_cli_runner().invoke(args=["restore-db", "../cubing.db"])

    assert result.exit_code != 0
    assert "No backup" in result.output
