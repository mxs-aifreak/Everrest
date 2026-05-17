from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Sprinkler, Property, WorkOrder
from datetime import date

sprinkler_bp = Blueprint('sprinkler', __name__)

SPRINKLER_YES_NO = ['Yes', 'No', 'Unknown']
CONTROLLER_BRANDS = ['Hunter', 'Rain Bird', 'Orbit', 'Toro', 'Irritrol', 'Rachio', 'RainMaster',
                     'Weathermatic', 'K-Rain', 'Netro', 'Other']
CONTROL_METHODS = ['Physical Panel Only', 'App/WiFi Only', 'Both App & Panel',
                   'Manual Valve Only', 'Smart Home', 'Unknown']
SHUTOFF_LOCATIONS = [
    'Basement – Near Water Main', 'Basement – Utility Area', 'Curb Stop Box',
    'Water Meter Box', 'Garage', 'Crawl Space', 'Backflow Preventer Exterior',
    'Utility Room', 'Side of House', 'Front Yard Ground Box', 'Backyard Ground Box', 'Other'
]
BLOWOUT_STATUSES = ['Completed', 'Scheduled', 'Pending', 'Skipped – Owner Decision', 'N/A']
TURNON_STATUSES = ['Active', 'Turned On', 'Scheduled', 'Pending', 'Skipped – Owner Decision', 'N/A']
SYSTEM_WORKING = ['Yes', 'No', 'Partially Working']
BACKFLOW_STATUSES = ['OK', 'Broken', 'Replaced', 'Not Tested', 'N/A']
REPAIR_STATUSES = ['Not Started', 'Scheduled', 'In Progress', 'Completed', 'N/A']


@sprinkler_bp.route('/sprinkler')
def list_sprinkler():
    properties = Property.query.order_by(Property.address).all()
    # Apply filters
    has_spr_f = request.args.get('has_sprinkler', '')
    repair_f = request.args.get('repair_needed', '')
    blowout_f = request.args.get('blowout_status', '')
    turnon_f = request.args.get('turnon_status', '')

    filtered = []
    for p in properties:
        spr = p.sprinkler
        if not spr:
            spr = Sprinkler(property_id=p.id, has_sprinkler='Unknown',
                            repair_needed='No', repair_status='N/A')
            db.session.add(spr)
        if has_spr_f and spr.has_sprinkler != has_spr_f:
            continue
        if repair_f and spr.repair_needed != repair_f:
            continue
        if blowout_f and spr.fall_blowout_status != blowout_f:
            continue
        if turnon_f and spr.spring_turnon_status != turnon_f:
            continue
        filtered.append(p)
    db.session.commit()

    return render_template('sprinkler/list.html',
                           properties=filtered,
                           sprinkler_yes_no=SPRINKLER_YES_NO,
                           blowout_statuses=BLOWOUT_STATUSES,
                           turnon_statuses=TURNON_STATUSES,
                           repair_statuses=REPAIR_STATUSES,
                           has_spr_f=has_spr_f, repair_f=repair_f,
                           blowout_f=blowout_f, turnon_f=turnon_f)


@sprinkler_bp.route('/sprinkler/<int:prop_id>', methods=['GET', 'POST'])
def sprinkler_detail(prop_id):
    prop = Property.query.get_or_404(prop_id)
    spr = prop.sprinkler
    if not spr:
        spr = Sprinkler(property_id=prop_id, has_sprinkler='Unknown',
                        repair_needed='No', repair_status='N/A')
        db.session.add(spr)
        db.session.commit()

    if request.method == 'POST':
        spr.has_sprinkler = request.form.get('has_sprinkler', spr.has_sprinkler)
        spr.controller_brand = request.form.get('controller_brand', '')
        spr.controller_model = request.form.get('controller_model', '')
        spr.control_method = request.form.get('control_method', '')
        spr.shutoff_valve_location = request.form.get('shutoff_valve_location', '')
        spr.fall_blowout_status = request.form.get('fall_blowout_status', '')
        spr.fall_blowout_date = _date(request.form.get('fall_blowout_date'))
        spr.blowout_vendor = request.form.get('blowout_vendor', '')
        spr.spring_turnon_status = request.form.get('spring_turnon_status', '')
        spr.spring_turnon_date = _date(request.form.get('spring_turnon_date'))
        spr.system_working = request.form.get('system_working', '')
        spr.backflow_valve_status = request.form.get('backflow_valve_status', '')
        spr.issue_details = request.form.get('issue_details', '')
        spr.repair_needed = request.form.get('repair_needed', 'No')
        spr.repair_status = request.form.get('repair_status', 'N/A')
        spr.repair_date = _date(request.form.get('repair_date'))
        spr.repair_vendor = request.form.get('repair_vendor', '')
        spr.repair_cost = _decimal(request.form.get('repair_cost'))
        spr.notes = request.form.get('notes', '')
        db.session.commit()
        _sync_sprinkler_wo(spr, prop)
        flash('Sprinkler record updated.', 'success')
        return redirect(url_for('sprinkler.sprinkler_detail', prop_id=prop_id))

    return render_template('sprinkler/detail.html', prop=prop, spr=spr,
                           sprinkler_yes_no=SPRINKLER_YES_NO,
                           controller_brands=CONTROLLER_BRANDS,
                           control_methods=CONTROL_METHODS,
                           shutoff_locations=SHUTOFF_LOCATIONS,
                           blowout_statuses=BLOWOUT_STATUSES,
                           turnon_statuses=TURNON_STATUSES,
                           system_working=SYSTEM_WORKING,
                           backflow_statuses=BACKFLOW_STATUSES,
                           repair_statuses=REPAIR_STATUSES)


def _sync_sprinkler_wo(spr, prop):
    """Auto-create or update a WO when repair is flagged."""
    if spr.repair_needed == 'Yes':
        if spr.linked_wo_id:
            wo = WorkOrder.query.get(spr.linked_wo_id)
            if wo:
                wo.estimated_cost = spr.repair_cost
                wo.vendor_name = spr.repair_vendor or wo.vendor_name
                wo.status = _repair_to_wo_status(spr.repair_status)
                db.session.commit()
                return
        owner_id = prop.property_owners[0].owner_id if prop.property_owners else None
        wo_num = _next_wo_number()
        wo = WorkOrder(
            wo_number=wo_num,
            property_id=prop.id,
            owner_id=owner_id,
            date_submitted=date.today(),
            category='Sprinkler Repair',
            description=spr.issue_details or 'Sprinkler repair required.',
            priority='High',
            vendor_name=spr.repair_vendor or '',
            status=_repair_to_wo_status(spr.repair_status),
            estimated_cost=spr.repair_cost,
            invoice_status='N/A',
            source='Sprinkler',
        )
        db.session.add(wo)
        db.session.flush()
        spr.linked_wo_id = wo.id
        db.session.commit()


def _repair_to_wo_status(rs):
    return {'Not Started': 'Open', 'Scheduled': 'Assigned', 'In Progress': 'In Progress',
            'Completed': 'Completed'}.get(rs, 'Open')


def _next_wo_number():
    year = date.today().year
    count = WorkOrder.query.filter(WorkOrder.wo_number.like(f'WO-{year}-%')).count()
    return f'WO-{year}-{count + 1:03d}'


def _decimal(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None
