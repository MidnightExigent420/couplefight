./s<prompt>
  <task>
    Build a gamified couples spend-tracking web app using Flask. Couples form a group, log their spending, and challenge each other through goals (set on themselves) and trip wires (set by their partner). Goals met and trip wires tripped earn points.
  </task>

  <tech_stack>
    <backend>Python + Flask</backend>
    <database>SQLite (dev) / PostgreSQL (prod) via SQLAlchemy</database>
    <auth>Flask-Login</auth>
    <frontend>Jinja2 templates + Tailwind CSS + vanilla JS</frontend>
    <charts>Chart.js (CDN)</charts>
  </tech_stack>

  <features>

    <feature name="Auth and Couple Groups">
      <requirement>User registration and login via Flask-Login.</requirement>
      <requirement>A user can create a Couple group and invite one partner via a shareable invite link.</requirement>
      <requirement>Each Couple group has exactly two members.</requirement>
      <requirement>Each user has their own personal dashboard; both are linked under the same Couple group.</requirement>
    </feature>

    <feature name="Currency">
      <requirement>Each user sets their preferred display currency on their profile (e.g. SGD, USD, EUR).</requirement>
      <requirement>All spend entries are stored with their original amount and original currency.</requirement>
      <requirement>When displaying amounts to a user, convert to their preferred currency using a static daily exchange rate.</requirement>
      <requirement>Fetch FX rates from a free FX API such as frankfurter.app and cache them daily in the FXRate table to avoid repeated calls.</requirement>
      <requirement>Currency conversion applies to: spend entries, goal thresholds, trip wire thresholds, and chart values.</requirement>
    </feature>

    <feature name="Spend Categories">
      <requirement>Each Couple group has a shared list of spend categories.</requirement>
      <requirement>On Couple group creation, seed defaults: Food, Medical, Transport, Shopping, Entertainment, Utilities, Travel, Other.</requirement>
      <requirement>Either member of the Couple can add new custom categories; the new category is immediately available to both partners.</requirement>
      <requirement>Categories are scoped to the Couple group — not global.</requirement>
    </feature>

    <feature name="Spend Tracker">
      <requirement>Log spend entries with: amount, currency (defaults to user's preferred currency), date, description, and category.</requirement>
      <requirement>Category is selected from the Couple's shared list.</requirement>
      <requirement>Provide an option to add a new category inline from the spend form.</requirement>
    </feature>

    <feature name="Goals">
      <description>A user sets a spending goal for themselves, e.g. "Spend less than $500 SGD on Food between Jun 1 and Jun 30".</description>
      <fields>
        <field>label</field>
        <field>condition_type (total spend OR specific category)</field>
        <field>category_id (if condition_type is specific category)</field>
        <field>threshold amount</field>
        <field>threshold currency</field>
        <field>start_date</field>
        <field>end_date</field>
      </fields>
      <requirement>Tier badge (Short / Medium / Long) is auto-displayed via classify_tier(start_date, end_date).</requirement>
      <requirement>Goal must be approved by the partner before becoming active.</requirement>
      <requirement>Partner receives an in-dashboard notification with inline approve / reject actions.</requirement>
      <requirement>When the goal condition is met within the period, the partner is alerted via notification.</requirement>
      <requirement>Meeting a goal earns the goal-setter 10 points.</requirement>
    </feature>

    <feature name="Trip Wires">
      <description>A user sets a trip wire targeting their partner's spend, e.g. "Alert me if they spend more than $200 SGD on Shopping between Jun 1 and Jun 30".</description>
      <fields>
        <field>label</field>
        <field>condition_type (total spend OR specific category)</field>
        <field>category_id (if condition_type is specific category)</field>
        <field>threshold amount</field>
        <field>threshold currency</field>
        <field>start_date</field>
        <field>end_date</field>
      </fields>
      <requirement>Tier badge auto-displayed via classify_tier(start_date, end_date).</requirement>
      <requirement>No approval required — trip wires are active immediately on creation.</requirement>
      <requirement>When triggered, both users are alerted via notifications.</requirement>
      <requirement>Tripping a trip wire earns the setter 10 points.</requirement>
    </feature>

    <feature name="Points">
      <requirement>Each user has a cumulative points total displayed prominently on their dashboard.</requirement>
      <requirement>Points are tracking only — no redemption mechanic in this version.</requirement>
    </feature>

    <feature name="Notifications">
      <requirement>Bell icon in the navbar with an unread count badge.</requirement>
      <requirement>Clicking the bell opens a notification drawer.</requirement>
      <requirement>Drawer lists: pending goal approvals (with inline approve/reject), goal met alerts, trip wire triggered alerts, expired goals and trip wires.</requirement>
      <requirement>Polled every 30 seconds via GET /api/notifications. Do not use WebSockets for the MVP.</requirement>
    </feature>

    <feature name="Spend Chart">
      <requirement>Line chart (Chart.js) showing the user's cumulative spend over a selected goal or trip wire's custom date range.</requirement>
      <requirement>Dropdown lets the user select which active goal or trip wire to visualise; the chart date range adjusts accordingly.</requirement>
      <requirement>Overlay a green horizontal line for the selected goal's threshold.</requirement>
      <requirement>Overlay a red horizontal line for any trip wire thresholds active in the same period.</requirement>
      <requirement>When a new spend entry is added, animate the chart line update over ~600ms (Chart.js built-in animation).</requirement>
      <requirement>All chart values are displayed in the viewing user's preferred currency.</requirement>
    </feature>

    <feature name="Spend Replay Mode">
      <requirement>Replay panel sits below the spend chart.</requirement>
      <requirement>Previous / Next buttons step one day at a time through the selected goal or trip wire's date range.</requirement>
      <requirement>Chart re-renders on each step showing cumulative spend up to that day only.</requirement>
    </feature>

  </features>

  <tier_classification>
    <rule>Tier is NEVER stored in the database. It is always derived at query time from the goal/tripwire's start_date and end_date.</rule>
    <rule>Tier thresholds live in a single config dict so the developer can adjust ranges without a schema migration.</rule>
    <rule>Implement tier as a Python @property on the Goal and TripWire models (or in the serialisation layer) — never as a column.</rule>
    <rule>Tier is informational only. It does NOT affect scoring or business logic.</rule>
    <rule>When end_date passes, the goal or trip wire expires automatically. No auto-renewal.</rule>

    <implementation>
      <file>app/config.py</file>
      <code><![CDATA[
TIER_THRESHOLDS = {
    "Short":  (1, 7),      # 1–7 days
    "Medium": (8, 90),     # 8–90 days
    "Long":   (91, None),  # 91+ days
}

def classify_tier(start_date, end_date):
    duration = (end_date - start_date).days
    for tier, (low, high) in TIER_THRESHOLDS.items():
        if duration >= low and (high is None or duration <= high):
            return tier
    return "Unknown"
      ]]></code>
    </implementation>
  </tier_classification>

  <data_models>
    <model name="User">
      <field>id</field>
      <field>email</field>
      <field>password_hash</field>
      <field>couple_group_id (FK)</field>
      <field>preferred_currency</field>
      <field>points (integer, default 0)</field>
    </model>

    <model name="CoupleGroup">
      <field>id</field>
      <field>invite_token (unique)</field>
    </model>

    <model name="Category">
      <field>id</field>
      <field>name</field>
      <field>couple_group_id (FK)</field>
    </model>

    <model name="SpendEntry">
      <field>id</field>
      <field>user_id (FK)</field>
      <field>amount</field>
      <field>original_currency</field>
      <field>date</field>
      <field>description</field>
      <field>category_id (FK)</field>
    </model>

    <model name="FXRate">
      <field>id</field>
      <field>from_currency</field>
      <field>to_currency</field>
      <field>rate</field>
      <field>date (cached daily)</field>
    </model>

    <model name="Goal">
      <field>id</field>
      <field>owner_id (FK to User)</field>
      <field>label</field>
      <field>condition_type (total | category)</field>
      <field>category_id (FK, nullable)</field>
      <field>threshold</field>
      <field>threshold_currency</field>
      <field>start_date</field>
      <field>end_date</field>
      <field>status (pending | active | met | expired)</field>
      <note>tier is a @property derived via classify_tier(start_date, end_date) — NOT a column</note>
    </model>

    <model name="TripWire">
      <field>id</field>
      <field>setter_id (FK to User)</field>
      <field>target_user_id (FK to User)</field>
      <field>label</field>
      <field>condition_type (total | category)</field>
      <field>category_id (FK, nullable)</field>
      <field>threshold</field>
      <field>threshold_currency</field>
      <field>start_date</field>
      <field>end_date</field>
      <field>status (active | tripped | expired)</field>
      <note>tier is a @property derived via classify_tier(start_date, end_date) — NOT a column</note>
    </model>

    <model name="Notification">
      <field>id</field>
      <field>recipient_id (FK to User)</field>
      <field>type</field>
      <field>message</field>
      <field>read (boolean)</field>
      <field>created_at</field>
    </model>
  </data_models>

  <project_structure>
    <![CDATA[
app/
├── __init__.py            # App factory
├── config.py              # TIER_THRESHOLDS + classify_tier() live here
├── models.py              # SQLAlchemy models
├── auth/                  # Login, register, invite blueprints
├── dashboard/             # Personal dashboard blueprint
├── spend/                 # Spend CRUD blueprint
├── goals/                 # Goals blueprint
├── tripwires/             # Trip wire blueprint
├── notifications/         # Notification polling endpoint
├── categories/            # Category management blueprint
├── fx/                    # FX rate fetching + caching
├── templates/
│   ├── base.html
│   ├── dashboard/
│   ├── spend/
│   ├── goals/
│   ├── tripwires/
│   └── ...
└── static/
    ├── css/
    └── js/
    ]]>
  </project_structure>

  <constraints>
    <constraint>Use Flask blueprints to keep features modular.</constraint>
    <constraint>Store all monetary amounts with their original currency; never pre-convert before storage.</constraint>
    <constraint>Tier classification must be derived, not stored.</constraint>
    <constraint>No WebSockets in the MVP — notifications are polled.</constraint>
    <constraint>Goals require partner approval; trip wires do not.</constraint>
    <constraint>Goals and trip wires expire on end_date; do not auto-renew.</constraint>
    <constraint>Points are awarded but not redeemable.</constraint>
  </constraints>

  <deliverables>
    <deliverable>Working Flask app with all features above.</deliverable>
    <deliverable>SQLAlchemy models matching the data_models section.</deliverable>
    <deliverable>Database migrations (use Flask-Migrate / Alembic).</deliverable>
    <deliverable>Seed script that creates default categories on Couple group creation.</deliverable>
    <deliverable>requirements.txt listing all dependencies.</deliverable>
    <deliverable>README.md with setup instructions, including how to obtain an FX API key (if needed) and how to run migrations.</deliverable>
    <deliverable>.env.example showing required environment variables.</deliverable>
  </deliverables>
</prompt>