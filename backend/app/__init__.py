import os

from flask import Flask

from . import models  # noqa: F401 — регистрирует модели для миграций
from .admin import make_admin_command
from .api import api
from .config import Config
from .errors import register_error_handlers
from .extensions import csrf, db, login_manager, migrate
from .seed import seed_command


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    register_error_handlers(app)
    app.register_blueprint(api)
    app.cli.add_command(seed_command)
    app.cli.add_command(make_admin_command)

    return app
