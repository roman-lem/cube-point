# Architecture

This document explains how the code is organized and which domain rules it implements. For setup instructions, see the [README](../README.md).

## Repository layout

```
backend/            Flask application
  app/              application code (one module per area, see below)
  migrations/       Alembic migrations
  tests/            pytest tests
frontend/           Vue application
  src/              source code, organized by Feature-Sliced Design
  nginx/            web server config: app.conf (static files, /api proxy, CSP),
                    local.conf (HTTP), prod.conf.template (HTTPS, redirects)
testdata/           test cases shared by the backend and frontend test suites
docker-compose.yml       local run in Docker: `web` (nginx + built frontend) and `backend`
docker-compose.prod.yml  production on a VPS: the same plus HTTPS and `certbot`
deploy.ps1          builds the images on the developer's computer and sends them to the server
deploy/             server scripts: update, certificate, database backup and restore
```

In production, the `web` container serves the built frontend and proxies `/api/` to the `backend` container (`http://backend:5000`). The backend is not exposed to the outside. The frontend and the API share one domain, so CORS is not needed. In development, the Vite dev server proxies `/api` to the backend in the same way.

Production (`docker-compose.prod.yml`):
- nginx terminates HTTPS with a Let's Encrypt certificate. The `certbot` container renews it, nginx reloads every 6 hours to pick it up. HTTP, `www` and `EXTRA_DOMAINS` redirect to `https://DOMAIN` with the path kept.
- The site address comes only from `DOMAIN` in `.env`: nginx gets it through the image's template substitution, the backend as `SITE_URL`, which builds meetup links and QR codes (`join_url`).
- gunicorn settings: `backend/gunicorn.conf.py`. Migrations run when the backend container starts.
- SQLite runs in WAL mode. `flask backup-db` makes a consistent copy through the SQLite backup API, `flask restore-db` restores one (`backend/app/backup.py`).
- Container logs go to the server's journald, so they survive re-deploys.

## External resources

The app loads nothing from third-party domains: no CDNs, web fonts, analytics or external APIs. Meetups often happen in places with a poor connection, and keeping everything on one domain also keeps personal data from leaving the server. Fonts come from `@fontsource-variable/*` packages bundled into the build. The rule is enforced by the `Content-Security-Policy` header in `frontend/nginx/app.conf`, so anything new has to work under that policy.

## Backend

A Flask app with SQLAlchemy models, Flask-Login sessions and Flask-WTF CSRF protection. The database is SQLite; schema changes go through Alembic migrations (`flask db migrate` / `flask db upgrade`).

| Module | Responsibility |
|---|---|
| `models.py` | Database models |
| `results.py` | Series results: best, averages, rounding, display formatting. **Source of truth** for result calculation |
| `scoring.py` | Saving attempts (`save_attempt`, `delete_attempt`), attempt history, club records, event tables |
| `events.py` | The list of events and their default formats |
| `auth/` | Login, registration, sessions, password change, login throttling |
| `clubs.py` | Club list, club page, club settings |
| `meetups.py` | Meetups, invitation links, participation requests |
| `series.py` | A participant's series and attempts, event result tables |
| `fmc.py` | FMC attempts: start, draft, freeze, submission |
| `desk.py` | Organizer desk: manual entry, participants, disqualification, finishing a meetup |
| `members.py` | Club member list, member card, bans, organizer role, password reset |
| `profiles.py` | Public pages: club records and member profiles |
| `admin.py` | Administration: clubs (including deletion), organizers, `flask make-admin` |
| `accounts.py` | Account creation by organizers and account deletion |
| `consents.py` | Personal data consents |
| `permissions.py` | Role checks. All permission checks happen on the server |
| `errors.py`, `forms.py` | Uniform API error format and request parsing |
| `seed.py` | `flask seed`: demo data for development (requires `ALLOW_SEED=1`) |

API errors always look like `{"error": {"code", "message", "fields"?}}`. The `code` is for the client, the `message` is shown to the user, and `fields` holds form field errors.

## Frontend

Vue 3 with TypeScript, Vue Router, Pinia and VueUse. Styles are plain CSS with CSS variables and no UI framework. cubing.js generates scrambles and checks FMC solutions.

The code follows [Feature-Sliced Design](https://feature-sliced.design/). Layers, from top to bottom:

| Layer | Contents |
|---|---|
| `app` | Entry point, router and guards, global styles and design tokens |
| `pages` | Screens, one slice per route |
| `widgets` | Large composite blocks: timer, FMC keyboard, results entry table, meetup panel, navigation, member card |
| `features` | User actions: login and registration, submitting an attempt, starting a series, entering an FMC solution, organizer tools (manual entry, disqualification, bans, finishing a meetup), account deletion |
| `entities` | Domain objects with their API calls and UI: `attempt`, `series`, `meetup`, `club`, `user`, `record`, `training-session` |
| `shared` | Code with no domain knowledge: HTTP client, UI kit (`AppButton`, `AppInput`, `ConfirmDialog`…), utilities, site config |

Rules:

- A slice can import only from layers below it, never from another slice of the same layer.
- Every slice exposes a public API through its `index.ts`. Deep imports into a slice are not allowed.
- Result calculation lives in `shared/lib/results` rather than in `entities`, because both `attempt` and `series` need it; the entities re-export it.
- The service name and the developer contacts are defined only in `shared/config/site.ts`.

### Styling

- Mobile first: base styles target narrow screens, and `min-width` media queries adapt the layout for wider ones. When a component itself changes (not just the layout), `useMediaQuery` from VueUse is used.
- Components use only the CSS variables defined in `app/styles/global.css` (`--color-primary`, `--radius-card`, `--font-mono`, etc.), never hard-coded colors.
- Anything showing times or numbers uses the monospace font with tabular digits.
- The interface language is Russian.

### Navigation

- The site root shows a landing page to guests. A logged-in user who belongs to a club is redirected to the club of their latest meetup.
- Guests see the "Club", "Records" and "Members" tabs. Logged-in users see "Club", "Timer", "Records", "Statistics" and "Profile". On mobile the tabs form a bottom bar, and on desktop a top bar.
- The current meetup and the meetup list live inside the "Club" tab, which shows a LIVE indicator during a meetup.
- Organizer tools are extra buttons on the club, meetup and member pages, not a separate section. Administration is an item in the profile settings, visible only to administrators.

## Data model

All timestamps are stored in UTC. Meetup dates and times are displayed in the club's time zone (`clubs.timezone`).

```
users                  accounts; is_admin is the global administrator flag
user_consents          append-only log of personal data consents
clubs, club_links      clubs and their social links
club_members           membership: role (member / organizer), ban
meetups                date, place, status (planned / live / finished), join_token
meetup_participants    participation requests: pending / approved / rejected
meetup_events          events of a meetup with their formats
scrambles              scrambles of a meetup event, one per attempt number
series                 one per participant per meetup event; version, cached best/average
attempts               value, penalty, FMC solution, submitted_at, updated_at
attempt_history        append-only log of every attempt value
fmc_attempts           FMC attempt state: start time, draft, frozen solution
disqualifications      per meetup and user
club_records           cache of club records, rebuilt from results
```

Deleting a meetup cascades to its events, series and attempts. A club with meetups and a user with results cannot be deleted: account deletion anonymizes the user instead.

## Domain rules

### Roles

- **Participant:** any logged-in user. There is no guest mode for taking part.
- **Organizer:** a role within a specific club (`club_members.role`), not a separate user type. Organizers see extra management buttons.
- **Administrator:** a global flag (`users.is_admin`). Administrators create clubs and appoint their first organizer. A club always has at least one organizer. The first administrator is created with `flask make-admin LOGIN`. Administrators also delete clubs: everything of the club goes in one transaction (meetups with all their contents, records, links, memberships), users stay; not while a meetup is live, and the club name must be typed in to confirm.
- There are no judges: participants are responsible for their own attempts.
- A person can belong to several clubs.

### Meetups

- There are **no rounds, finals or groups**. Each participant does **exactly one series** in each event of the meetup, at their own pace, at any time during the meetup.
- A participant can have several series in progress at once, in different events.
- Scrambles are generated by the organizer's browser (cubing.js) when the meetup is created, and are the same for everyone in an event, so they can be printed on score sheets. They are not official WCA scrambles. The server only checks their count, length and that they are not empty.
- In competition mode, only the scramble of the current attempt is shown.
- **Joining a club goes through a meetup.** The organizer shares a link or QR code with a `join_token`. Following it creates a `pending` request, which the organizer approves. When a request is approved for the first time, the person automatically joins the club. Only approved participants can start a series, and this is checked on the server. A user banned in the club cannot request to join. The organizer can reissue the link; approved participants stay approved. The link stops working when the meetup is finished.
- The organizer can add a participant manually and enter results for them (for someone without a phone), including creating an account with a temporary password.
- **Finishing a meetup:** all missing attempts of started series become DNS. Series that were never started are not created, so those people do not appear in the event table. A finished meetup no longer accepts attempts from participants, but the organizer can still enter and edit results, for example from paper sheets.

### Events and formats

- Events use WCA IDs, all official events except Multi-Blind and FTO, in the standard WCA order: `333`, `222`, `444`, `555`, `666`, `777`, `333bf`, `333fm`, `333oh`, `clock`, `minx`, `pyram`, `skewb`, `sq1`, `444bf`, `555bf`. The list is defined in code (`backend/app/events.py` and its mirror `frontend/src/shared/lib/events.ts`).
- Formats are set per event when a meetup is created:

| Format | Result |
|---|---|
| `ao5` (average of 5) | The best and the worst attempts are dropped and the other three averaged. One DNF/DNS counts as the worst and is dropped; two or more make the average DNF. |
| `mo3` (mean of 3) | The mean of all three. Any DNF/DNS makes the mean DNF. |
| `bo1`, `bo3`, `bo5` (best of N) | The best attempt. |

- Defaults, as at WCA: 6x6 and 7x7 are `mo3`, 4BLD and 5BLD are `bo3`, 3BLD is `bo5`, FMC is `bo1`, everything else is `ao5`.
- Averages are **rounded down** to hundredths (thousandths are simply dropped).
- In an unfinished series, the average becomes DNF as soon as the outcome is certain (two DNF/DNS in ao5, one in mo3). Until then an unfinished series has no average.
- With equal times in ao5, the first of the best and the last of the worst attempts are dropped. This does not change the average, only which attempts are shown in parentheses.
- The training timer also shows **ao12**: one best and one worst of the last 12 solves are dropped, and the other ten averaged.
- Calculation lives in `backend/app/results.py` (source of truth) and `frontend/src/shared/lib/results` (a mirror for live recalculation). Both are tested against `testdata/results_cases.json`, so add new cases there.

### Times and penalties

- Times are stored as **integers in hundredths of a second**, never as floats. FMC results are move counts, and the FMC mean is in hundredths of a move.
- The penalty is stored separately from the time (`none`, `plus2`, `dnf`, `dns`) and is not added to the stored value, so it can be removed later. FMC has no +2.
- Display: `9.87`, `1:02.45`, `1:05:23.45`, `11.87 (+2)`, `DNF`, `DNS`. An attempt is under three hours.

### Event table

The sort key is the average then the best attempt for ao5 and mo3, and the best attempt for bo formats. Any time beats DNF. Rows come in three groups:

1. Finished series with at least one successful attempt, with places. A fully equal key shares a place (1, 2, 2, 4). A DNF average with a successful attempt goes after all real averages, ordered by best attempt.
2. Finished series where every attempt is DNF, without a place.
3. Unfinished series, without a place, ordered by best attempt and then by number of attempts done.

Ties are ordered by name. Disqualified participants are not in the table. See `rank` and `event_table` in `backend/app/scoring.py`.

### Records

- **PB** is a person's personal best across all their meetups in all clubs.
- **LR** (local record) is a club record, counting only that club's meetups. The official WCA abbreviations (CR, NR, WR) are not used.
- On a tie, the record belongs to whoever set it **first**: by meetup date, then by the moment the result was achieved (`submitted_at` of the attempt, or of the last attempt of the series for an average).
- `submitted_at` does not change when an attempt is edited, and edits update `updated_at` instead. Records use only `submitted_at` and the current attempt values.
- Averages count as records only in formats with an average (ao5, mo3). bo formats have singles only.
- Results of participants disqualified at a meetup are excluded from tables and records.
- `club_records` is a cache. `recalc_records(club_id, event_id)` fully rebuilds it and is called from the single place where results are saved (`save_attempt` and `delete_attempt` in `backend/app/scoring.py`).
- Tables mark only **current** records: LR if the series holds the club record, PB if it holds the person's personal best.

### Timer

- Training mode is the default: random scrambles, any event, session statistics (ao5, ao12, best, solve count). Training sessions are stored only in the browser's localStorage, one per event, in a versioned format. Corrupted data never breaks the page: it just gives an empty session.
- Start by holding and releasing (touch on a phone, space bar on a computer), with optional 15-second inspection or manual time entry.
- In competition mode a solve is not saved automatically: the participant picks OK / +2 / DNF and confirms.

### FMC

- Each attempt has its own 60-minute countdown. The server records the start time and gives out the scramble only after the start.
- The solution is typed on an on-screen keyboard: faces R L U D F B, modifiers `'` and `2`, wide turns (`Rw`), rotations x y z. Slice moves (M, E, S) are not allowed.
- Moves are counted per WCA rules: face turns and wide turns count 1 (doubles included), rotations count 0. A solution longer than 80 moves is DNF. A solution containing 6 or more consecutive moves of the inverse scramble is DNF; the check first converts the solution to face turns in the original orientation, so rotations and wide turns do not hide it.
- There are no correctness hints and no move counter during the attempt. The draft is autosaved to the server.
- Submission has two steps. "Submit" freezes the text and the submission time, and confirming saves the attempt. If time runs out without a submission, the last saved draft becomes the result.
- The client checks the solution on a virtual cube (cubing.js) and sends the result. The server trusts that result, as it trusts times in other events, but always stores the solution text, so the organizer can recheck it.
- A meetup cannot be finished while there are started but unsubmitted FMC attempts: the organizer resolves each one first, by checking it or setting DNF.

### Organizer desk

- The organizer can edit any saved attempt and add the next one in order, including starting a series for a participant. Everything goes through `save_attempt`.
- **Saving is automatic:** a cell saves on blur or Enter, and each cell shows its state (saving, saved, error with retry). Only actions that cannot simply be overwritten by the next edit ask for confirmation: finishing a meetup and disqualification.
- Cell input is a single line: digits are a time (`1234` → 12.34, `10234` → 1:02.34, `1052345` → 1:05:23.45), `+` means +2, `d` means DNF, `dns` means DNS.
- **Attempt history** (`attempt_history`): every creation and change of an attempt adds an entry, and entries are never changed. A corrected attempt is marked in tables; everyone sees the original value, but only organizers see the full history.
- Only the **last** attempt of a series can be erased (a gap in the middle would break the order), and only if the organizer entered it. An attempt submitted by the participant can only be corrected.
- The entry table rows are sorted by name, not by place, so they do not jump while typing.

### Concurrent edits

A series can be changed by both the participant and the organizer. Each series has a `version`; a save is rejected if the version changed since the client read it, and the client reloads the data. Saves of one series from the organizer desk are queued, so fast typing does not cause false conflicts.

### Disqualification and bans

- **Disqualification** applies to one meetup and annuls all of the participant's results there. It is stored separately, and the series are kept, so it can be undone.
- **A ban** applies to a club and only affects the future: the person cannot request to join meetups or submit attempts, even at a live meetup. Past results and records stay. Organizers cannot be banned, and neither can oneself.
- Both require a reason and a confirmation.

### Public pages

- Club records, the club member list and member profiles are public.
- **Logins are never exposed on public pages or in public endpoints**, only the user's ID and display name. Club organizers and administrators can see logins.

### Authentication

- Flask-Login sessions in an httpOnly cookie (`SameSite=Lax`) and a CSRF token for modifying requests. "Remember me" gives a long session.
- Passwords are hashed on the server (Werkzeug). Logins are case-insensitive.
- Sessions can be revoked instantly: the session ID includes `session_version`, which increases on a password reset.
- Without email, a password is recovered through a club organizer, who issues a temporary password that must be changed at the next login. An organizer cannot reset the password of another organizer or an administrator; only an administrator can.
- Login attempts are throttled per login and per client IP. The backend trusts exactly one proxy (`ProxyFix` in `create_app`): the real IP and scheme come from the headers nginx sets.

### Personal data

Registration requires two separate consents: to processing and to publication of the display name and results. They are stored in an append-only log with the text version. When a consent text changes, its version changes in both `backend/app/consents.py` and `frontend/src/features/auth/model/consents.ts`, and users are asked to accept the new version.

Users can delete their account. The login, email, password hash and consents are destroyed, and the results stay under a placeholder name. Optionally, the user can keep their display name in result tables; in that case the account has no public profile, and an administrator can anonymize the name later on request.
