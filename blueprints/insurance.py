from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Insurance, Property, Owner, Occupancy, PropertyOwner
from datetime import date

insurance_bp = Blueprint('insurance', __name__)

STATUSES = ['Active', 'Pending', 'Expired', 'N/A']
PROVIDERS_RENTERS = ['State Farm', 'Allstate', 'USAA', 'Lemonade', 'Liberty Mutual',
                     'Farmers', 'Nationwide', 'Progressive', 'Travelers', 'Other']
PROVIDERS_LANDLORD = ['State Farm', 'Allstate', 'USAA', 'Liberty Mutual', 'Farmers',
                      'Nationwide', 'Progressive', 'Travelers', 'American Family', 'Other']


def _date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


def _decimal(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _days_left(expiry):
    if not expiry:
        return None
    return (expiry - date.today()).days


def _urgency(policy, days):
    if policy is None:
        return 'missing'
    if policy.status == 'N/A':
        return 'na'
    if days is None:
        return 'pending'
    if days < 0:
        return 'expired'
    if days <= 30:
        return 'expiring'
    return 'active'


def _urgency_order(u):
    return {'missing': 0, 'expired': 1, 'expiring': 2, 'pending': 3, 'active': 4, 'na': 5}[u]


def _build_rows(insurance_type):
    """Return sorted list of dicts, one per property, for a given insurance type."""
    properties = Property.query.order_by(Property.address).all()
    policies = {p.property_id: p for p in
                Insurance.query.filter_by(insurance_type=insurance_type).all()}
    occupancies = {o.property_id: o for o in Occupancy.query.all()}

    rows = []
    for prop in properties:
        policy = policies.get(prop.id)
        days = _days_left(policy.expiration_date) if policy else None
        urgency = _urgency(policy, days)
        owner = prop.primary_owner
        occ = occupancies.get(prop.id)
        rows.append({
            'property': prop,
            'policy': policy,
            'owner': owner,
            'tenant': occ.tenant_name if occ else None,
            'occ_status': occ.status if occ else None,
            'days_left': days,
            'urgency': urgency,
        })

    rows.sort(key=lambda r: (_urgency_order(r['urgency']),
                             r['days_left'] if r['days_left'] is not None else 9999))
    return rows


def _kpis(rows):
    total = len(rows)
    active = sum(1 for r in rows if r['urgency'] == 'active')
    expiring = sum(1 for r in rows if r['urgency'] == 'expiring')
    expired = sum(1 for r in rows if r['urgency'] == 'expired')
    missing = sum(1 for r in rows if r['urgency'] == 'missing')
    pending = sum(1 for r in rows if r['urgency'] == 'pending')
    return dict(total=total, active=active, expiring=expiring,
                expired=expired, missing=missing, pending=pending)


@insurance_bp.route('/insurance')
def list_insurance():
    tab = request.args.get('tab', 'renters')
    renters_rows = _build_rows('Renters')
    landlord_rows = _build_rows('Landlord')
    deposit_rows = _deposit_rows()

    # Deposit KPIs
    dep_kpis = {
        'total': len(deposit_rows),
        'collected_us': sum(1 for r in deposit_rows if r['occ'] and r['occ'].deposit_held_by == 'EverRest' and r['occ'].deposit_status == 'Collected'),
        'held_owner': sum(1 for r in deposit_rows if r['occ'] and r['occ'].deposit_held_by == 'Owner'),
        'pending': sum(1 for r in deposit_rows if r['occ'] and r['occ'].deposit_status == 'Pending'),
        'returned': sum(1 for r in deposit_rows if r['occ'] and r['occ'].deposit_status in ('Returned', 'Partial Return')),
    }

    return render_template('insurance/list.html',
                           renters_rows=renters_rows,
                           landlord_rows=landlord_rows,
                           renters_kpis=_kpis(renters_rows),
                           landlord_kpis=_kpis(landlord_rows),
                           deposit_rows=deposit_rows,
                           dep_kpis=dep_kpis,
                           deposit_held_by=DEPOSIT_HELD_BY,
                           deposit_statuses=DEPOSIT_STATUSES,
                           tab=tab)


@insurance_bp.route('/insurance/renters/add', methods=['GET', 'POST'])
def add_renters():
    properties = Property.query.order_by(Property.address).all()
    prop_id = request.args.get('property_id', type=int)
    if request.method == 'POST':
        prop_id = request.form.get('property_id', type=int)
        existing = Insurance.query.filter_by(insurance_type='Renters', property_id=prop_id).first()
        if existing:
            flash('This property already has a renter\'s insurance record. Edit it instead.', 'warning')
            return redirect(url_for('insurance.edit_renters', ins_id=existing.id))
        ins = Insurance(
            insurance_type='Renters',
            property_id=prop_id,
            provider=request.form.get('provider', '').strip(),
            policy_number=request.form.get('policy_number', '').strip(),
            coverage_amount=_decimal(request.form.get('coverage_amount')),
            annual_premium=_decimal(request.form.get('annual_premium')),
            effective_date=_date(request.form.get('effective_date')),
            expiration_date=_date(request.form.get('expiration_date')),
            status=request.form.get('status', 'Pending'),
            date_received=_date(request.form.get('date_received')),
            notes=request.form.get('notes', '').strip(),
        )
        db.session.add(ins)
        db.session.commit()
        flash('Renter\'s insurance policy added.', 'success')
        return redirect(url_for('insurance.list_insurance', tab='renters'))
    prop = Property.query.get(prop_id) if prop_id else None
    return render_template('insurance/form.html',
                           ins=None, ins_type='Renters',
                           properties=properties,
                           selected_prop=prop,
                           owners=[],
                           statuses=STATUSES,
                           providers=PROVIDERS_RENTERS)


@insurance_bp.route('/insurance/renters/<int:ins_id>/edit', methods=['GET', 'POST'])
def edit_renters(ins_id):
    ins = Insurance.query.get_or_404(ins_id)
    properties = Property.query.order_by(Property.address).all()
    if request.method == 'POST':
        ins.provider = request.form.get('provider', '').strip()
        ins.policy_number = request.form.get('policy_number', '').strip()
        ins.coverage_amount = _decimal(request.form.get('coverage_amount'))
        ins.annual_premium = _decimal(request.form.get('annual_premium'))
        ins.effective_date = _date(request.form.get('effective_date'))
        ins.expiration_date = _date(request.form.get('expiration_date'))
        ins.status = request.form.get('status', ins.status)
        ins.date_received = _date(request.form.get('date_received'))
        ins.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Renter\'s insurance updated.', 'success')
        return redirect(url_for('insurance.list_insurance', tab='renters'))
    return render_template('insurance/form.html',
                           ins=ins, ins_type='Renters',
                           properties=properties,
                           selected_prop=ins.property,
                           owners=[],
                           statuses=STATUSES,
                           providers=PROVIDERS_RENTERS)


@insurance_bp.route('/insurance/landlord/add', methods=['GET', 'POST'])
def add_landlord():
    properties = Property.query.order_by(Property.address).all()
    owners = Owner.query.order_by(Owner.name).all()
    prop_id = request.args.get('property_id', type=int)
    if request.method == 'POST':
        prop_id = request.form.get('property_id', type=int)
        existing = Insurance.query.filter_by(insurance_type='Landlord', property_id=prop_id).first()
        if existing:
            flash('This property already has a landlord insurance record. Edit it instead.', 'warning')
            return redirect(url_for('insurance.edit_landlord', ins_id=existing.id))
        ins = Insurance(
            insurance_type='Landlord',
            property_id=prop_id,
            owner_id=request.form.get('owner_id', type=int),
            provider=request.form.get('provider', '').strip(),
            policy_number=request.form.get('policy_number', '').strip(),
            coverage_amount=_decimal(request.form.get('coverage_amount')),
            annual_premium=_decimal(request.form.get('annual_premium')),
            effective_date=_date(request.form.get('effective_date')),
            expiration_date=_date(request.form.get('expiration_date')),
            status=request.form.get('status', 'Pending'),
            date_received=_date(request.form.get('date_received')),
            notes=request.form.get('notes', '').strip(),
        )
        db.session.add(ins)
        db.session.commit()
        flash('Landlord insurance policy added.', 'success')
        return redirect(url_for('insurance.list_insurance', tab='landlord'))
    prop = Property.query.get(prop_id) if prop_id else None
    return render_template('insurance/form.html',
                           ins=None, ins_type='Landlord',
                           properties=properties,
                           selected_prop=prop,
                           owners=owners,
                           statuses=STATUSES,
                           providers=PROVIDERS_LANDLORD)


@insurance_bp.route('/insurance/landlord/<int:ins_id>/edit', methods=['GET', 'POST'])
def edit_landlord(ins_id):
    ins = Insurance.query.get_or_404(ins_id)
    properties = Property.query.order_by(Property.address).all()
    owners = Owner.query.order_by(Owner.name).all()
    if request.method == 'POST':
        ins.owner_id = request.form.get('owner_id', type=int)
        ins.provider = request.form.get('provider', '').strip()
        ins.policy_number = request.form.get('policy_number', '').strip()
        ins.coverage_amount = _decimal(request.form.get('coverage_amount'))
        ins.annual_premium = _decimal(request.form.get('annual_premium'))
        ins.effective_date = _date(request.form.get('effective_date'))
        ins.expiration_date = _date(request.form.get('expiration_date'))
        ins.status = request.form.get('status', ins.status)
        ins.date_received = _date(request.form.get('date_received'))
        ins.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Landlord insurance updated.', 'success')
        return redirect(url_for('insurance.list_insurance', tab='landlord'))
    return render_template('insurance/form.html',
                           ins=ins, ins_type='Landlord',
                           properties=properties,
                           selected_prop=ins.property,
                           owners=owners,
                           statuses=STATUSES,
                           providers=PROVIDERS_LANDLORD)


DEPOSIT_HELD_BY = ['EverRest', 'Owner']
DEPOSIT_STATUSES = ['Pending', 'Collected', 'Returned', 'Partial Return']


def _deposit_rows():
    properties = Property.query.order_by(Property.address).all()
    occupancies = {o.property_id: o for o in Occupancy.query.all()}
    rows = []
    for prop in properties:
        occ = occupancies.get(prop.id)
        rows.append({'property': prop, 'occ': occ})
    return rows


@insurance_bp.route('/insurance/deposits/<int:prop_id>/update', methods=['POST'])
def update_deposit(prop_id):
    occ = Occupancy.query.filter_by(property_id=prop_id).first()
    if not occ:
        flash('No occupancy record for this property.', 'warning')
        return redirect(url_for('insurance.list_insurance', tab='deposits'))
    occ.security_deposit = _decimal(request.form.get('security_deposit')) or occ.security_deposit
    occ.deposit_held_by = request.form.get('deposit_held_by', 'EverRest')
    occ.deposit_status = request.form.get('deposit_status', 'Pending')
    occ.deposit_returned_amount = _decimal(request.form.get('deposit_returned_amount'))
    occ.deposit_return_date = _date(request.form.get('deposit_return_date'))
    occ.deposit_notes = request.form.get('deposit_notes', '').strip()
    db.session.commit()
    flash('Security deposit updated.', 'success')
    return redirect(url_for('insurance.list_insurance', tab='deposits'))


@insurance_bp.route('/insurance/<int:ins_id>/delete', methods=['POST'])
def delete_insurance(ins_id):
    ins = Insurance.query.get_or_404(ins_id)
    tab = 'renters' if ins.insurance_type == 'Renters' else 'landlord'
    db.session.delete(ins)
    db.session.commit()
    flash('Insurance record deleted.', 'info')
    return redirect(url_for('insurance.list_insurance', tab=tab))
