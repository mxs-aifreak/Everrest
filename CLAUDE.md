# EverRest Property Management — Project Context

## What This Is
A Flask-based Progressive Web App (PWA) for managing rental properties. Built for mobile-first use. Deployed on Railway, database on Supabase (PostgreSQL).

## Live App
- **Railway URL**: check Railway dashboard — project is named `everrest` or similar
- **GitHub repo**: `git@github.com:mxs-aifreak/Everrest.git`
- Railway auto-deploys on every `git push` to `main`

## Local Dev Path
Code lives at: `/Users/mxs-mac/everrest`

To run locally:
```bash
cd /Users/mxs-mac/everrest
source venv/bin/activate   # or: python3 -m venv venv && pip install -r requirements.txt
python app.py
```

## Tech Stack
- **Backend**: Python / Flask with blueprints
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL on Supabase (free tier)
- **Hosting**: Railway (free tier)
- **Frontend**: Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Auth**: None (single-user internal tool)

## Database Setup (CRITICAL)
The app uses Supabase PostgreSQL. The connection string is set as an environment variable on Railway:
- Variable name: `DATABASE_URL`
- Must use the **Session Pooler** connection string from Supabase (NOT the direct connection — Railway is IPv4 only, Supabase direct is IPv6 only)
- Find it: Supabase project → "Connect" button at top → "Session Pooler" tab → copy the URI
- Format: `postgresql://postgres.xxxx:PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres`

SQLite is used as fallback when `DATABASE_URL` is not set (local dev).

## Database Migrations
`db.create_all()` does NOT add new columns to existing tables. New columns are added via `_run_migrations()` in `app.py`, which runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` on every startup. This is safe to run repeatedly.

## Git / SSH
SSH key is set up at `/Users/mxs-mac/.ssh/id_ed25519`. Remote is SSH-based:
```
git@github.com:mxs-aifreak/Everrest.git
```
To push from the `mxs` user profile, a new SSH key needs to be generated and added to GitHub settings.

## Project Structure
```
everrest/
├── app.py                  # App factory, db init, _run_migrations()
├── models.py               # All SQLAlchemy models
├── requirements.txt        # psycopg2-binary required for PostgreSQL
├── blueprints/
│   ├── properties.py
│   ├── work_orders.py
│   ├── inspections.py
│   ├── sprinkler.py        # Also handles sprinkler tab in property detail
│   ├── owners.py
│   ├── insurance.py        # Also handles security deposits tab
│   ├── ledger.py
│   └── leases.py
├── templates/
│   ├── base.html           # Shared layout: top navbar (desktop) + bottom nav (mobile)
│   ├── index.html          # Dashboard
│   ├── properties/
│   ├── work_orders/
│   ├── inspections/
│   ├── sprinkler/
│   ├── owners/
│   ├── insurance/          # 3 tabs: Renters, Landlord, Security Deposits
│   ├── ledger/
│   └── leases/
└── static/
    ├── css/style.css
    ├── js/app.js
    ├── manifest.json       # PWA manifest
    └── icons/
```

## Navigation (9 sections)
| Section | URL | Icon |
|---------|-----|------|
| Dashboard | `/` | speedometer2 |
| Properties | `/properties` | house |
| Work Orders | `/work-orders` | tools |
| Inspections | `/inspections` | clipboard-check |
| Sprinkler | `/sprinkler` | droplet |
| Owners | `/owners` | people |
| Insurance | `/insurance` | shield-check |
| Leases | `/leases` | calendar-check |
| Ledger | `/ledger` | cash-stack |

**Mobile**: Fixed bottom navigation bar (scrollable icon tabs). Desktop: horizontal top navbar.

## Key Features Built

### Properties
- Full CRUD with multi-step add form
- Tabs on property detail: Overview, Occupancy, Inspections, Work Orders, Sprinkler, Documents
- Deep-link tab navigation: `/properties/<id>?tab=sprinkler` etc.
- Property links from other sections go directly to the relevant tab

### Work Orders
- Statuses: Open, Assigned, In Progress, On Hold, Completed, Cancelled
- Priorities: Low, Medium, High, Critical
- **Owner Billing card** on completed WOs with actual_cost — bill repair to owner, tracked in Ledger
- Source field: 'Sprinkler' auto-tag for sprinkler-generated WOs

### Sprinkler
- Per-property tracking: Spring Turn-On, Fall Blowout, Turn Off Status/Date
- **Auto-logic**: When Fall Blowout → Completed: auto-sets Turn Off Status = "Turned Off", Turn Off Date = today, resets Spring Turn-On to Pending
- **Reverse logic**: When Spring Turn-On → "Active" or "Turned On": resets Fall Blowout to Pending, clears Turn Off status/date
- ⚠️ Sprinkler form exists in TWO places: `templates/sprinkler/detail.html` AND `templates/properties/detail.html` (Sprinkler tab). Both must be updated for any sprinkler changes. Same for `blueprints/sprinkler.py` and `blueprints/properties.py`.

### Insurance (`/insurance`)
- 3 tabs: Renter's Insurance, Landlord Insurance, Security Deposits
- Color-coded urgency: missing (grey), expired (red), expiring ≤30d (orange), active (green)
- Security Deposits tab: deposit amount, held by (EverRest/Owner), status, inline edit

### Owner Ledger (`/ledger`)
- Tracks repair costs billed to owners (always deducted from rent disbursement, never waived)
- Groups by owner, shows pending deduction + settled history
- Mark Deducted form with date + notes (e.g. "Deducted from June disbursement")
- Running balance across multiple WOs per owner

### Lease Renewals (`/leases`)
- All Occupied/Notice Given properties sorted by urgency
- Color-coded: expired, ≤30d, 31–90d, >90d
- Inline form: renewal decision (Unknown/Renewing/Moving Out/Negotiating), contact date, notes

### Data
- 44 properties, 38 owners loaded from Excel seed data

## Models (key relationships)
```
Property → has many Occupancy, WorkOrder, Inspection, Sprinkler, Insurance
Owner → linked via PropertyOwner (many-to-many)
Occupancy → has deposit fields + renewal fields
WorkOrder → has billing fields (billed_to_owner, owner_settlement_status/date/notes)
Insurance → insurance_type ('Renters' or 'Landlord'), property_id, owner_id
```

## Common Patterns
- Flash messages for success/error feedback
- `data-confirm="..."` attribute triggers JS confirmation dialogs
- Inline Bootstrap collapse forms for quick edits without page navigation
- `d-none d-md-table-cell` to hide columns on mobile
- `status-badge` + `badge-*` CSS classes for colored pill badges
- `dateformat` Jinja filter for consistent date display
- `currency` Jinja filter for $ amounts

## Known Gotchas
1. **Two-template sprinkler**: Any change to sprinkler form needs updating in BOTH `templates/sprinkler/detail.html` AND `templates/properties/detail.html`, and BOTH `blueprints/sprinkler.py` AND `blueprints/properties.py`
2. **Migrations**: New model columns need `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` entries in `_run_migrations()` in `app.py`
3. **Supabase pooler**: Must use Session Pooler URL, not Direct Connection (IPv4 vs IPv6 issue)
4. **psycopg2-binary**: Must be in requirements.txt for PostgreSQL to work
