"""gunicorn settings for production (backend/Dockerfile).

Sized for a 1-core, 2 GB server with SQLite: 2 processes of 4 threads each,
about 80 MB per process. More processes would not help on one core and would
only make writers wait for the SQLite lock more often; threads keep a process
busy while one request waits for that lock. Both can be changed from .env.
"""

import os

bind = "0.0.0.0:5000"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# Errors and app messages go to stderr, from there to the Docker log driver
# (journald in docker-compose.prod.yml, limited in size). Requests are logged by nginx.
errorlog = "-"
loglevel = "info"
accesslog = None
