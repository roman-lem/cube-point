# Cubing SaaS

A web app for local speedcubing clubs. It runs small competitions at club meetups: participants enter their own results from their phones, and the app keeps live result tables, club records and personal statistics. No more paper score sheets to process after the meetup.

The project is non-commercial. The interface is in Russian.

## Features

- **Meetups.** The organizer creates a meetup with events and formats, and the app generates the scrambles. People join through a link or QR code, and the organizer approves them.
- **Results from any device.** A timer with hold-to-start, optional 15-second inspection and manual entry. Each participant does one series per event at their own pace, with no rounds or finals.
- **Live tables.** Event rankings update during the meetup. Supported formats are ao5, mo3, bo1, bo3 and bo5.
- **FMC.** A one-hour countdown per attempt, an on-screen move keyboard, draft autosave and solution checking on a virtual cube.
- **Club records and personal bests.** Personal bests count across all clubs; club records count only that club's meetups.
- **Organizer desk.** A spreadsheet-like table for entering results from paper sheets, an edit history for every attempt, printable scramble sheets, disqualifications and bans.
- **Training mode.** Random scrambles and session statistics (ao5, ao12, best), stored only in the browser.

## Tech stack

- **Frontend:** Vue 3, TypeScript, Vite, Vue Router, Pinia, VueUse, cubing.js. Plain CSS, no UI framework.
- **Backend:** Flask, SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF (CSRF). SQLite.
- **Deployment:** Docker Compose, with nginx serving the frontend and proxying `/api/` to the backend.

The app loads nothing from third-party domains: fonts and libraries are bundled with the build.

## Running locally

You need Python 3.13+ and Node.js 24+.

**Backend** (runs at http://localhost:5000):

```sh
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
# The backend does not start without SECRET_KEY (at least 32 characters). Put it in
# the repository's .env: flask reads that file. See .env.example.
cp ../.env.example ../.env       # then set SECRET_KEY, and MAIL_LOG_BODY=1 to see letters in the log

flask --app wsgi db upgrade                 # create the database (backend/instance/cubing.db)
ALLOW_SEED=1 flask --app wsgi seed          # optional: demo club, users and meetups
ALLOW_SEED=1 flask --app wsgi seed-demo     # or: three clubs for showing the service
flask --app wsgi run
```

The demo data includes an administrator `admin` and club members such as `a.smirnov` (organizer) and `d.kozlov`, all with the password `password`. `flask seed` is full of edge cases for development; `flask seed-demo` fills an ordinary club life for demonstrations: three clubs, finished meetups and a live one in the main club, the same logins with the password `demo2026` (`d.kozlov` is in all three clubs). To make your own administrator, run `flask --app wsgi make-admin LOGIN`.

On Windows, set the variable separately: `set ALLOW_SEED=1` (cmd) or `$env:ALLOW_SEED=1` (PowerShell).

**Frontend** (runs at http://localhost:5173):

```sh
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to the backend, so the browser sees a single origin. To point it at another backend address, set `VITE_BACKEND_URL`.

### Running with Docker

```sh
cp .env.example .env    # then set SECRET_KEY
docker compose up --build
```

The app is served on port 80. The database is created empty on first start. Create the first administrator with:

```sh
docker compose exec backend flask make-admin LOGIN
```

### Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | — | Flask secret key, at least 32 characters. Required everywhere except tests: the backend refuses to start without it. |
| `SECURE_COOKIES` | `1` in Docker Compose, off otherwise | Send cookies over HTTPS only. Set `0` when opening the local Docker build over plain http from a device other than localhost. Always `1` in production. |
| `REGISTRATION_OPEN` | `1` | `0` closes registration. Login and organizer-created accounts keep working. |
| `ALLOW_SEED` | off | `1` allows `flask seed` and `flask seed-demo`, which wipe the database and fills it with demo data. Never set it in production. |
| `DATABASE_URL` | `sqlite:///cubing.db` | SQLAlchemy database URL. A relative SQLite path is resolved against `backend/instance/`. |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | — | SMTP mailbox for letters. `MAIL_HOST` is required in production. Without it letters are not sent, only their subject is logged. |
| `MAIL_LOG_BODY` | off | Development: `1` writes whole letters (with links) to the log when `MAIL_HOST` is not set. |
| `SITE_URL` | `http://localhost:5173` | Site address; meetup links and QR codes are built from it. In production it is `https://DOMAIN`. |

### Production

`docker-compose.prod.yml` runs the app on a single VPS with HTTPS (Let's Encrypt), automatic certificate renewal and daily database backups. The images are built on the developer's computer and sent to the server by `deploy.ps1`; server-side scripts are in `deploy/`. All production variables are described in `.env.example`.

## Tests

```sh
cd backend && pytest               # backend
cd frontend && npx vitest run      # frontend unit tests
cd frontend && npm run type-check  # TypeScript
```

The result calculation (averages, rounding, DNF rules) exists on both the backend and the frontend. Both implementations are checked against the same cases in `testdata/results_cases.json`.

## Documentation

For the repository layout, frontend and backend architecture, data model and domain rules, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

Copyright (C) 2026 Leparskiy Roman. Licensed under the [GNU Affero General Public License v3.0](LICENSE). If you run a modified version of this app as a service, you must offer its source code to its users.
