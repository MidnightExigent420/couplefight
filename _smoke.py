"""Ad-hoc smoke test for the simplification pass. Deletes itself effect: not committed (caller removes)."""
import os, re, tempfile

# Force a throwaway sqlite db so we don't touch the dev one.
tmp_db = os.path.join(tempfile.gettempdir(), "_couplefight_smoke.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db}"
os.environ["SECRET_KEY"] = "smoke-test-key"
# Disable rate limiting so /register doesn't return 429 across re-runs.
os.environ["RATELIMIT_ENABLED"] = "false"

from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.create_all()

c = app.test_client()


def csrf_token(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html) or re.search(r'content="([^"]+)" name="csrf-token"', html)
    return m.group(1) if m else None


# 1. Register
r = c.get("/auth/register"); tok = csrf_token(r.get_data(as_text=True))
r = c.post("/auth/register", data={
    "csrf_token": tok, "email": "a@example.com", "password": "password123",
    "confirm": "password123", "preferred_currency": "USD", "submit": "Create account",
}, follow_redirects=False)
print("register status:", r.status_code, "->", r.headers.get("Location"))

# 2. Create couple group (POST /auth/couple/create)
r = c.get("/dashboard"); tok = csrf_token(r.get_data(as_text=True))
r = c.post("/auth/couple/create", data={"csrf_token": tok}, follow_redirects=True)
print("create couple status:", r.status_code)

# 3. GET /goals/ and /tripwires/ and /spend/ — all should be 200
for path in ("/goals/", "/tripwires/", "/spend/"):
    r = c.get(path)
    print(f"GET {path}: {r.status_code}")

# 4. POST /goals/ with end < start to verify validator flashes correctly
r = c.get("/goals/"); tok = csrf_token(r.get_data(as_text=True))
r = c.post("/goals/", data={
    "csrf_token": tok, "label": "Bad date goal", "goal_type": "cap",
    "condition_type": "total", "threshold": "100", "threshold_currency": "USD",
    "start_date": "2026-06-30", "end_date": "2026-06-01",  # end < start
    "submit": "Submit goal",
}, follow_redirects=True)
print("POST goal (bad dates) status:", r.status_code)
body = r.get_data(as_text=True)
print("  end-after-start flash present:", "End date must be on or after start date" in body)

# 5. POST /tripwires/ with end < start — same validator
r = c.get("/tripwires/"); tok = csrf_token(r.get_data(as_text=True))
r = c.post("/tripwires/", data={
    "csrf_token": tok, "label": "Bad date tw",
    "condition_type": "total", "threshold": "100", "threshold_currency": "USD",
    "start_date": "2026-06-30", "end_date": "2026-06-01",
    "submit": "Set trip wire",
}, follow_redirects=True)
print("POST tripwire (bad dates) status:", r.status_code)
body = r.get_data(as_text=True)
print("  end-after-start flash present:", "End date must be on or after start date" in body)

# 6. Notifications poll — exercises the logging change
r = c.get("/api/notifications")
print("GET /api/notifications:", r.status_code)
print("DONE")
