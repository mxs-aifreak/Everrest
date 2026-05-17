from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Owner, Property, PropertyOwner
from datetime import date

owners_bp = Blueprint('owners', __name__)

CONTRACT_STATUSES = ['Not Started', 'Sent for Signature', 'Signed']
INSURANCE_STATUSES = ['Active', 'Expired', 'Pending', 'N/A']


@owners_bp.route('/owners')
def list_owners():
    search = request.args.get('search', '')
    query = Owner.query
    if search:
        query = query.filter(
            (Owner.name.ilike(f'%{search}%')) |
            (Owner.email.ilike(f'%{search}%')) |
            (Owner.phone.ilike(f'%{search}%'))
        )
    owners = query.order_by(Owner.name).all()
    return render_template('owners/list.html', owners=owners, search=search)


@owners_bp.route('/owners/new', methods=['GET', 'POST'])
def new_owner():
    if request.method == 'POST':
        owner = Owner(
            name=request.form.get('name', '').strip(),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            emergency_contact=request.form.get('emergency_contact', ''),
            emergency_phone=request.form.get('emergency_phone', ''),
            onboarding_fee=_decimal(request.form.get('onboarding_fee')),
            reserve_fee=_decimal(request.form.get('reserve_fee')),
            renewal_fee=_decimal(request.form.get('renewal_fee')),
            monthly_mgmt_fee=_decimal(request.form.get('monthly_mgmt_fee')),
            contract_status=request.form.get('contract_status', 'Not Started'),
            landlord_insurance_status=request.form.get('landlord_insurance_status', 'N/A'),
            landlord_insurance_expiry=_date(request.form.get('landlord_insurance_expiry')),
            notes=request.form.get('notes', ''),
        )
        if not owner.name:
            flash('Owner name is required.', 'danger')
            return redirect(url_for('owners.new_owner'))
        db.session.add(owner)
        db.session.commit()
        flash(f'Owner {owner.name} created.', 'success')
        return redirect(url_for('owners.owner_detail', owner_id=owner.id))
    return render_template('owners/form.html', owner=None,
                           contract_statuses=CONTRACT_STATUSES,
                           insurance_statuses=INSURANCE_STATUSES)


@owners_bp.route('/owners/<int:owner_id>')
def owner_detail(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    all_properties = Property.query.order_by(Property.address).all()
    linked_ids = {po.property_id for po in owner.property_owners}
    available_properties = [p for p in all_properties if p.id not in linked_ids]
    return render_template('owners/detail.html', owner=owner,
                           available_properties=available_properties,
                           contract_statuses=CONTRACT_STATUSES,
                           insurance_statuses=INSURANCE_STATUSES)


@owners_bp.route('/owners/<int:owner_id>/edit', methods=['POST'])
def edit_owner(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    owner.name = request.form.get('name', owner.name).strip()
    owner.phone = request.form.get('phone', '')
    owner.email = request.form.get('email', '')
    owner.emergency_contact = request.form.get('emergency_contact', '')
    owner.emergency_phone = request.form.get('emergency_phone', '')
    owner.onboarding_fee = _decimal(request.form.get('onboarding_fee'))
    owner.reserve_fee = _decimal(request.form.get('reserve_fee'))
    owner.renewal_fee = _decimal(request.form.get('renewal_fee'))
    owner.monthly_mgmt_fee = _decimal(request.form.get('monthly_mgmt_fee'))
    owner.contract_status = request.form.get('contract_status', owner.contract_status)
    owner.landlord_insurance_status = request.form.get('landlord_insurance_status', owner.landlord_insurance_status)
    owner.landlord_insurance_expiry = _date(request.form.get('landlord_insurance_expiry'))
    owner.notes = request.form.get('notes', '')
    db.session.commit()
    flash('Owner updated.', 'success')
    return redirect(url_for('owners.owner_detail', owner_id=owner_id))


@owners_bp.route('/owners/<int:owner_id>/delete', methods=['POST'])
def delete_owner(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    db.session.delete(owner)
    db.session.commit()
    flash('Owner deleted.', 'info')
    return redirect(url_for('owners.list_owners'))


@owners_bp.route('/owners/<int:owner_id>/link-property', methods=['POST'])
def link_property(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    prop_id = _int(request.form.get('property_id'))
    if prop_id:
        existing = PropertyOwner.query.filter_by(property_id=prop_id, owner_id=owner_id).first()
        if not existing:
            db.session.add(PropertyOwner(property_id=prop_id, owner_id=owner_id))
            db.session.commit()
            flash('Property linked.', 'success')
        else:
            flash('Property already linked.', 'warning')
    return redirect(url_for('owners.owner_detail', owner_id=owner_id))


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


def _int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None
