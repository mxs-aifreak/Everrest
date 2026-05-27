import os
import calendar
from datetime import date
from flask import Flask, render_template
from models import db
from blueprints.properties import properties_bp
from blueprints.work_orders import work_orders_bp
from blueprints.inspections import inspections_bp
from blueprints.sprinkler import sprinkler_bp
from blueprints.owners import owners_bp
from blueprints.insurance import insurance_bp
from blueprints.ledger import ledger_bp
from blueprints.leases import leases_bp
from blueprints.pdf_export import pdf_export_bp


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'everrest-change-me-in-production')
    # Railway PostgreSQL support: swap postgres:// → postgresql://
    db_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(app.instance_path, "everrest.db")}')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    app.register_blueprint(properties_bp)
    app.register_blueprint(work_orders_bp)
    app.register_blueprint(inspections_bp)
    app.register_blueprint(sprinkler_bp)
    app.register_blueprint(owners_bp)
    app.register_blueprint(insurance_bp)
    app.register_blueprint(ledger_bp)
    app.register_blueprint(leases_bp)
    app.register_blueprint(pdf_export_bp)

    @app.route('/')
    def dashboard():
        from models import Property, Occupancy, WorkOrder, Inspection, Sprinkler
        from sqlalchemy import func

        total_properties = Property.query.count()
        occupied = Occupancy.query.filter_by(status='Occupied').count()
        vacant = Occupancy.query.filter_by(status='Vacant').count()
        notice = Occupancy.query.filter_by(status='Notice Given').count()
        occupied_pct = round((occupied / total_properties * 100) if total_properties > 0 else 0)

        open_wo = WorkOrder.query.filter(
            WorkOrder.status.notin_(['Completed', 'Cancelled'])
        ).count()
        repairs_needed = Sprinkler.query.filter_by(repair_needed='Yes').count()

        # Inspections due: pending review or upcoming this month
        today = date.today()
        inspections_due = Inspection.query.filter(
            (Inspection.status == 'Pending Review') |
            (Inspection.follow_up_required == 'Yes')
        ).count()

        recent_wos = WorkOrder.query.order_by(WorkOrder.id.desc()).limit(5).all()
        recent_inspections = Inspection.query.order_by(Inspection.id.desc()).limit(3).all()

        # Bar chart: monthly WO actual costs for last 6 months
        monthly_costs = []
        monthly_labels = []
        for i in range(5, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            monthly_labels.append(f"{calendar.month_abbr[month]} {year}")
            start = date(year, month, 1)
            end_day = calendar.monthrange(year, month)[1]
            end = date(year, month, end_day)
            total = db.session.query(func.sum(WorkOrder.actual_cost)).filter(
                WorkOrder.date_completed >= start,
                WorkOrder.date_completed <= end,
            ).scalar() or 0
            monthly_costs.append(float(total))

        return render_template('dashboard.html',
                               total_properties=total_properties,
                               occupied_pct=occupied_pct,
                               vacant=vacant,
                               notice=notice,
                               open_wo=open_wo,
                               repairs_needed=repairs_needed,
                               inspections_due=inspections_due,
                               recent_wos=recent_wos,
                               recent_inspections=recent_inspections,
                               monthly_costs=monthly_costs,
                               monthly_labels=monthly_labels)

    @app.route('/api/property-owner/<int:prop_id>')
    def api_property_owner(prop_id):
        from models import PropertyOwner
        from flask import jsonify
        po = PropertyOwner.query.filter_by(property_id=prop_id).first()
        return jsonify({'owner_id': po.owner_id if po else None})

    @app.route('/settings')
    def settings():
        return render_template('settings.html')

    # Jinja2 helpers
    @app.template_filter('currency')
    def currency_filter(value):
        if value is None:
            return '—'
        try:
            return f'${float(value):,.2f}'
        except (ValueError, TypeError):
            return '—'

    @app.template_filter('dateformat')
    def dateformat_filter(value, fmt='%b %d, %Y'):
        if not value:
            return '—'
        try:
            return value.strftime(fmt)
        except AttributeError:
            return str(value)

    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()
        _run_migrations()
        from seed_data import seed_if_empty
        seed_if_empty()

    return app


def _run_migrations():
    """Safely add new columns to existing tables that db.create_all() won't touch."""
    migrations = [
        "ALTER TABLE sprinkler ADD COLUMN IF NOT EXISTS turnoff_status VARCHAR(50) DEFAULT 'Pending'",
        "ALTER TABLE sprinkler ADD COLUMN IF NOT EXISTS turnoff_date DATE",
        # WorkOrder billing fields
        "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS billed_to_owner VARCHAR(5) DEFAULT 'No'",
        "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS owner_settlement_status VARCHAR(50) DEFAULT 'N/A'",
        "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS owner_settlement_date DATE",
        "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS owner_settlement_notes TEXT",
        # Occupancy deposit fields
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS deposit_held_by VARCHAR(50) DEFAULT 'EverRest'",
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS deposit_status VARCHAR(50) DEFAULT 'Pending'",
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS deposit_returned_amount NUMERIC(10,2)",
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS deposit_return_date DATE",
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS deposit_notes TEXT",
        # Occupancy renewal fields
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS renewal_status VARCHAR(50) DEFAULT 'Unknown'",
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS renewal_contacted_date DATE",
        "ALTER TABLE occupancy ADD COLUMN IF NOT EXISTS renewal_notes TEXT",
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(db.text(sql))
            except Exception:
                pass
        conn.commit()


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
