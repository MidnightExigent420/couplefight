# CoupleFight

A gamified couples spend-tracking web app. Couples form a group, log spending, and challenge each other through goals (set on themselves) and trip wires (set by their partner). Goals met and trip wires tripped earn 10 points each.

## Stack
- Python 3.11+ / Flask 3
- SQLAlchemy 2.x + Flask-Migrate (Alembic)
- Flask-Login (Argon2id password hashing)
- Flask-WTF for CSRF + form validation
- Flask-Limiter for auth rate limiting
- Jinja2 + Tailwind (CDN) + vanilla JS
- Chart.js (CDN)
- frankfurter.app for FX rates (no API key required)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — set SECRET_KEY at minimum

export FLASK_APP=run.py
flask db init           # only the first time, creates migrations/
flask db migrate -m "init"
flask db upgrade

flask run               # or: python run.py
```

App listens on `http://127.0.0.1:5000` by default.

## Environment variables (`.env`)

| Var | Required | Notes |
|---|---|---|
| `SECRET_KEY` | yes (prod) | Long random string. Required when `FLASK_ENV=production`. |
| `DATABASE_URL` | no | Defaults to `sqlite:///couplefight.db`. Use `postgresql+psycopg2://…` in prod. |
| `FX_API_BASE` | no | Defaults to `https://api.frankfurter.app`. **No API key needed.** |
| `SESSION_COOKIE_SECURE` | prod | Set to `1` behind HTTPS so the session cookie gets `Secure`. |

## FX rates

This app uses [frankfurter.app](https://www.frankfurter.app/), which is free and **does not require an API key**. Rates are fetched on demand and cached daily in the `fx_rates` table — subsequent reads for the same `(from, to, date)` triple are served from cache.

If you want to use a different provider, swap the implementation in `app/fx/service.py::_fetch_rate`.

## Architecture

```
app/
├── __init__.py            # App factory, security headers
├── config.py              # TIER_THRESHOLDS + classify_tier()
├── extensions.py          # db, migrate, login_manager, csrf, limiter
├── models.py              # SQLAlchemy models (tier is a @property — never stored)
├── auth/                  # Register, login, profile, couple group invite/join/leave
├── dashboard/             # Personal dashboard + /api/chart endpoint
├── spend/                 # Spend CRUD
├── goals/                 # Goals (require partner approval)
├── tripwires/             # Trip wires (active immediately)
├── notifications/         # /api/notifications poll endpoint
├── categories/            # Inline category creation (JSON + form)
├── fx/                    # FX rate fetching + daily caching + convert()
├── services/
│   └── evaluation.py      # Re-evaluates goals & trip wires after spend; awards points
├── templates/
└── static/
```

### Tier classification

Tier is **never stored** in the DB. It's derived from `start_date`/`end_date` in `app/config.py`:

```python
TIER_THRESHOLDS = {"Short": (1, 7), "Medium": (8, 90), "Long": (91, None)}
```

…and exposed as `Goal.tier` / `TripWire.tier` `@property` on the SQLAlchemy models.

### Scoring

| Event | Who gets points |
|---|---|
| Goal met (under threshold for full window) | Goal owner: +10 |
| Trip wire tripped (target exceeds threshold in window) | Trip wire setter: +10 |

Points are tracking-only — there's no redemption mechanic in the MVP.

### Notifications

Polled every 30s from `GET /api/notifications`. The bell icon shows an unread count and the drawer renders inline approve/reject buttons for pending goal approvals. Goal/trip-wire status transitions (approved, rejected, met, busted, tripped, expired) all create notifications.

### Spend Replay

The dashboard chart picker drives a replay panel under the chart. Prev/Next step the displayed cumulative line forward/back one day at a time within the selected goal or trip wire's window.

## Default categories

Seeded automatically on couple group creation: Food, Medical, Transport, Shopping, Entertainment, Utilities, Travel, Other. Either partner can add custom categories; new categories appear immediately for both.

## Security notes

- Argon2id password hashing.
- CSRF on all state-changing requests (Flask-WTF + `X-CSRFToken` for fetch).
- `HttpOnly`, `SameSite=Lax` session cookies; `Secure` flag toggles via `SESSION_COOKIE_SECURE=1` in prod.
- Strict CSP (allows only Tailwind/Chart.js CDNs), `X-Frame-Options: DENY`, HSTS in prod.
- All authorization checks are server-side and object-level (e.g., spend deletion, goal approval, chart data).
- Rate-limiting on `/auth/login` (20/h) and `/auth/register` (10/h) per IP.
- ORM-only DB access — no raw SQL.
- Open-redirect protection on `?next=` parameter.

## Known limitations / next steps

- No "edit goal/trip wire" — they're immutable once submitted (delete/recreate by extension).
- Replay animation is a single forward/back step; a continuous play button could be added.
- FX failures fall back to `1.0` and log a warning — production deployments should alert on this.
- No background scheduler for `expire_stale()`; it runs lazily on `/dashboard` and `/api/notifications` polls.
