import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from . import models  # noqa: F401 — registers the models for migrations
from .admin import make_admin_command
from .api import api
from .backup import backup_db_command, restore_db_command
from .config import Config
from .errors import register_error_handlers
from .extensions import csrf, db, login_manager, migrate
from .seed import seed_command


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # The backend sits behind exactly one proxy (nginx in the web container).
    # Its last X-Forwarded-For entry is the real client IP (login throttling
    # counts by it) and X-Forwarded-Proto tells Flask the request came over HTTPS.
    # Entries a client adds itself come earlier in the header and are ignored.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    register_error_handlers(app)
    app.register_blueprint(api)
    app.cli.add_command(seed_command)
    app.cli.add_command(make_admin_command)
    app.cli.add_command(backup_db_command)
    app.cli.add_command(restore_db_command)

    return app
