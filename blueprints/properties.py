from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Property, Owner, PropertyOwner, Occupancy, Sprinkler
import urllib.parse

properties_bp = Blueprint('properties', __name__)

PROPERTY_TYPES = ['Single Family', 'Townhome', 'Condo', 'Multi-Unit']
OCCUPANCY_STATUSES = ['Occupied', 'Vacant', 'Notice Given', 'Maintenance']
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
TURNOFF_STATUSES = ['Turned Off', 'Pending', 'N/A']
TURNON_STATUSES = ['Active', 'Turned On', 'Scheduled', 'Pending', 'Skipped – Owner Decision', 'N/A']
SYSTEM_WORKING = ['Yes', 'No', 'Partially Working']
BACKFLOW_STATUSES = ['OK', 'Broken', 'Replaced', 'Not Tested', 'N/A']
REPAIR_STATUSES = ['Not Started', 'Scheduled', 'In Progress', 'Completed', 'N/A']

UTILITY_TYPES = ['Electric', 'Gas', 'Water', 'Trash', 'Sewer', 'Internet', 'Cable', 'HOA', 'Other']
RESPONSIBLE_PARTIES = ['Owner', 'Tenant', 'Shared']
UTILITY_STATUSES = [
    'Active-Owner', 'Active-Tenant', 'Pending Move-In Transfer',
    'Pending Move-Out Transfer', 'Disconnected', 'Unknown',
]


@properties_bp.route('/properties')
def list_properties():
    query = Property.query
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    if search:
        query = query.filter(
            (Property.address.ilike(f'%{search}%')) |
            (Property.city.ilike(f'%{search}%'))
        )
    properties = query.order_by(Property.address).all()
    if status_filter:
        properties = [p for p in properties if p.occupancy and p.occupancy.status == status_filter]
    if type_filter:
        properties = [p for p in properties if p.property_type == type_filter]
    return render_template('properties/list.html', properties=properties,
                           search=search, status_filter=status_filter,
                           type_filter=type_filter, property_types=PROPERTY_TYPES,
                           occupancy_statuses=OCCUPANCY_STATUSES)


@properties_bp.route('/properties/add', methods=['GET', 'POST'])
def add_property():
    owners = Owner.query.order_by(Owner.name).all()
    if request.method == 'POST':
        step = request.form.get('step', '5')
        if step == '5':
            # Final save
            addr = request.form.get('address', '').strip()
            city = request.form.get('city', '').strip()
            if not addr or not city:
                flash('Address and city are required.', 'danger')
                return redirect(url_for('properties.add_property'))

            maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(addr + ',' + city + ',CO')}"
            prop = Property(
                address=addr,
                city=city,
                state=request.form.get('state', 'CO'),
                zip=request.form.get('zip', ''),
                property_type=request.form.get('property_type', ''),
                google_maps_url=maps_url,
            )
            db.session.add(prop)
            db.session.flush()

            # Owner
            owner_id = request.form.get('owner_id')
            if owner_id == 'new':
                owner = Owner(
                    name=request.form.get('new_owner_name', '').strip(),
                    phone=request.form.get('new_owner_phone', ''),
                    email=request.form.get('new_owner_email', ''),
                )
                db.session.add(owner)
                db.session.flush()
                owner_id = owner.id
            if owner_id:
                db.session.add(PropertyOwner(property_id=prop.id, owner_id=int(owner_id)))

            # Occupancy
            occ = Occupancy(
                property_id=prop.id,
                status=request.form.get('occ_status', 'Vacant'),
                tenant_name=request.form.get('tenant_name', ''),
                tenant_phone=request.form.get('tenant_phone', ''),
                tenant_email=request.form.get('tenant_email', ''),
                rent_amount=_decimal(request.form.get('rent_amount')),
                security_deposit=_decimal(request.form.get('security_deposit')),
                lease_start=_date(request.form.get('lease_start')),
                lease_end=_date(request.form.get('lease_end')),
                notes=request.form.get('occ_notes', ''),
            )
            db.session.add(occ)

            # Sprinkler
            spr = Sprinkler(
                property_id=prop.id,
                has_sprinkler=request.form.get('has_sprinkler', 'Unknown'),
                controller_brand=request.form.get('controller_brand', ''),
                controller_model=request.form.get('controller_model', ''),
                control_method=request.form.get('control_method', ''),
                shutoff_valve_location=request.form.get('shutoff_valve_location', ''),
                repair_needed='No',
                repair_status='N/A',
            )
            db.session.add(spr)
            db.session.commit()
            flash(f'Property at {prop.address} added successfully!', 'success')
            return redirect(url_for('properties.property_detail', prop_id=prop.id))

    return render_template('properties/add.html', owners=owners,
                           property_types=PROPERTY_TYPES,
                           occupancy_statuses=OCCUPANCY_STATUSES,
                           controller_brands=CONTROLLER_BRANDS,
                           control_methods=CONTROL_METHODS,
                           shutoff_locations=SHUTOFF_LOCATIONS,
                           sprinkler_yes_no=SPRINKLER_YES_NO)


@properties_bp.route('/properties/<int:prop_id>')
def property_detail(prop_id):
    prop = Property.query.get_or_404(prop_id)
    owners = Owner.query.order_by(Owner.name).all()
    tab = request.args.get('tab', 'overview')
    return render_template('properties/detail.html', prop=prop, owners=owners,
                           tab=tab,
                           property_types=PROPERTY_TYPES,
                           occupancy_statuses=OCCUPANCY_STATUSES,
                           controller_brands=CONTROLLER_BRANDS,
                           control_methods=CONTROL_METHODS,
                           shutoff_locations=SHUTOFF_LOCATIONS,
                           blowout_statuses=BLOWOUT_STATUSES,
                           turnoff_statuses=TURNOFF_STATUSES,
                           turnon_statuses=TURNON_STATUSES,
                           system_working=SYSTEM_WORKING,
                           backflow_statuses=BACKFLOW_STATUSES,
                           repair_statuses=REPAIR_STATUSES,
                           sprinkler_yes_no=SPRINKLER_YES_NO,
                           utility_types=UTILITY_TYPES,
                           responsible_parties=RESPONSIBLE_PARTIES,
                           utility_statuses=UTILITY_STATUSES)


@properties_bp.route('/properties/<int:prop_id>/edit', methods=['POST'])
def edit_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    prop.address = request.form.get('address', prop.address).strip()
    prop.city = request.form.get('city', prop.city).strip()
    prop.state = request.form.get('state', prop.state)
    prop.zip = request.form.get('zip', prop.zip)
    prop.property_type = request.form.get('property_type', prop.property_type)
    prop.google_maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(prop.address + ',' + prop.city + ',CO')}"
    db.session.commit()
    flash('Property updated successfully.', 'success')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='overview'))


@properties_bp.route('/properties/<int:prop_id>/delete', methods=['POST'])
def delete_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    db.session.delete(prop)
    db.session.commit()
    flash('Property deleted.', 'info')
    return redirect(url_for('properties.list_properties'))


@properties_bp.route('/properties/<int:prop_id>/occupancy/edit', methods=['POST'])
def edit_occupancy(prop_id):
    prop = Property.query.get_or_404(prop_id)
    occ = prop.occupancy
    if not occ:
        occ = Occupancy(property_id=prop_id)
        db.session.add(occ)
    occ.status = request.form.get('status', occ.status)
    occ.tenant_name = request.form.get('tenant_name', '')
    occ.tenant_phone = request.form.get('tenant_phone', '')
    occ.tenant_email = request.form.get('tenant_email', '')
    occ.rent_amount = _decimal(request.form.get('rent_amount'))
    occ.security_deposit = _decimal(request.form.get('security_deposit'))
    occ.lease_start = _date(request.form.get('lease_start'))
    occ.lease_end = _date(request.form.get('lease_end'))
    occ.notes = request.form.get('notes', '')
    db.session.commit()
    flash('Occupancy updated.', 'success')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='overview'))


@properties_bp.route('/properties/<int:prop_id>/sprinkler/edit', methods=['POST'])
def edit_sprinkler(prop_id):
    prop = Property.query.get_or_404(prop_id)
    spr = prop.sprinkler
    if not spr:
        spr = Sprinkler(property_id=prop_id)
        db.session.add(spr)
    spr.has_sprinkler = request.form.get('has_sprinkler', 'Unknown')
    spr.controller_brand = request.form.get('controller_brand', '')
    spr.controller_model = request.form.get('controller_model', '')
    spr.control_method = request.form.get('control_method', '')
    spr.shutoff_valve_location = request.form.get('shutoff_valve_location', '')
    prev_blowout = spr.fall_blowout_status
    new_blowout = request.form.get('fall_blowout_status', '')
    spr.fall_blowout_status = new_blowout
    spr.fall_blowout_date = _date(request.form.get('fall_blowout_date'))
    spr.blowout_vendor = request.form.get('blowout_vendor', '')
    spr.turnoff_status = request.form.get('turnoff_status', 'Pending')
    spr.turnoff_date = _date(request.form.get('turnoff_date'))
    spr.spring_turnon_status = request.form.get('spring_turnon_status', '')
    spr.spring_turnon_date = _date(request.form.get('spring_turnon_date'))
    if new_blowout == 'Completed' and prev_blowout != 'Completed':
        from datetime import date as _date_cls
        spr.turnoff_status = 'Turned Off'
        if not spr.turnoff_date:
            spr.turnoff_date = _date_cls.today()
        spr.spring_turnon_status = 'Pending'
        spr.spring_turnon_date = None

    if spr.spring_turnon_status in ('Active', 'Turned On'):
        spr.fall_blowout_status = 'Pending'
        spr.fall_blowout_date = None
        spr.turnoff_status = 'Pending'
        spr.turnoff_date = None
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
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='sprinkler'))


@properties_bp.route('/properties/<int:prop_id>/owner/add', methods=['POST'])
def add_property_owner(prop_id):
    prop = Property.query.get_or_404(prop_id)
    owner_id = request.form.get('owner_id')
    if owner_id:
        existing = PropertyOwner.query.filter_by(property_id=prop_id, owner_id=int(owner_id)).first()
        if not existing:
            db.session.add(PropertyOwner(property_id=prop_id, owner_id=int(owner_id)))
            db.session.commit()
            flash('Owner linked to property.', 'success')
        else:
            flash('Owner already linked.', 'warning')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='owners'))


@properties_bp.route('/properties/<int:prop_id>/owner/<int:owner_id>/remove', methods=['POST'])
def remove_property_owner(prop_id, owner_id):
    po = PropertyOwner.query.filter_by(property_id=prop_id, owner_id=owner_id).first_or_404()
    db.session.delete(po)
    db.session.commit()
    flash('Owner removed from property.', 'info')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='owners'))


def _sync_sprinkler_wo(spr, prop):
    """Auto-create or update a Work Order when sprinkler repair is flagged."""
    from models import WorkOrder
    from datetime import date
    if spr.repair_needed == 'Yes':
        if spr.linked_wo_id:
            wo = WorkOrder.query.get(spr.linked_wo_id)
            if wo:
                wo.estimated_cost = spr.repair_cost
                wo.vendor_name = spr.repair_vendor or wo.vendor_name
                wo.status = _repair_status_to_wo_status(spr.repair_status)
                db.session.commit()
                return
        # Create new WO
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
            status=_repair_status_to_wo_status(spr.repair_status),
            estimated_cost=spr.repair_cost,
            invoice_status='N/A',
            source='Sprinkler',
        )
        db.session.add(wo)
        db.session.flush()
        spr.linked_wo_id = wo.id
        db.session.commit()


def _repair_status_to_wo_status(repair_status):
    mapping = {
        'Not Started': 'Open',
        'Scheduled': 'Assigned',
        'In Progress': 'In Progress',
        'Completed': 'Completed',
        'N/A': 'Open',
    }
    return mapping.get(repair_status, 'Open')


def _next_wo_number():
    from datetime import date
    from models import WorkOrder
    year = date.today().year
    count = WorkOrder.query.filter(WorkOrder.wo_number.like(f'WO-{year}-%')).count()
    return f'WO-{year}-{count + 1:03d}'


def _decimal(val):
    if val is None or val == '':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _date(val):
    if not val:
        return None
    from datetime import date
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None
