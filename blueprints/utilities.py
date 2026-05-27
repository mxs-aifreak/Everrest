from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Utility, UtilityExpense, Property, Owner, PropertyOwner
from datetime import date

utilities_bp = Blueprint('utilities', __name__)

UTILITY_TYPES = ['Electric', 'Gas', 'Water', 'Trash', 'Sewer', 'Internet', 'Cable', 'HOA', 'Other']
RESPONSIBLE_PARTIES = ['Owner', 'Tenant', 'Shared']
UTILITY_STATUSES = [
    'Active-Owner',
    'Active-Tenant',
    'Pending Move-In Transfer',
    'Pending Move-Out Transfer',
    'Disconnected',
    'Unknown',
]


def _decimal(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _date(val):
    try:
        return date.fromisoformat(val) if val else None
    except (ValueError, TypeError):
        return None


# ── Utility account CRUD ──────────────────────────────────────────────────────

@utilities_bp.route('/properties/<int:prop_id>/utilities/add', methods=['POST'])
def add_utility(prop_id):
    prop = Property.query.get_or_404(prop_id)
    u = Utility(
        property_id=prop_id,
        utility_type=request.form.get('utility_type', 'Other'),
        provider_name=request.form.get('provider_name', ''),
        account_number=request.form.get('account_number', ''),
        responsible_party=request.form.get('responsible_party', 'Owner'),
        status=request.form.get('status', 'Active-Owner'),
        estimated_monthly=_decimal(request.form.get('estimated_monthly')),
        notes=request.form.get('notes', ''),
    )
    db.session.add(u)
    db.session.commit()
    flash(f'{u.utility_type} utility added.', 'success')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='utilities'))


@utilities_bp.route('/utilities/<int:util_id>/edit', methods=['POST'])
def edit_utility(util_id):
    u = Utility.query.get_or_404(util_id)
    u.utility_type = request.form.get('utility_type', u.utility_type)
    u.provider_name = request.form.get('provider_name', '')
    u.account_number = request.form.get('account_number', '')
    u.responsible_party = request.form.get('responsible_party', u.responsible_party)
    u.status = request.form.get('status', u.status)
    u.estimated_monthly = _decimal(request.form.get('estimated_monthly'))
    u.notes = request.form.get('notes', '')
    db.session.commit()
    flash('Utility updated.', 'success')
    return redirect(url_for('properties.property_detail', prop_id=u.property_id, tab='utilities'))


@utilities_bp.route('/utilities/<int:util_id>/delete', methods=['POST'])
def delete_utility(util_id):
    u = Utility.query.get_or_404(util_id)
    prop_id = u.property_id
    db.session.delete(u)
    db.session.commit()
    flash('Utility removed.', 'info')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='utilities'))


# ── Utility expense CRUD ──────────────────────────────────────────────────────

@utilities_bp.route('/properties/<int:prop_id>/utility-expenses/add', methods=['POST'])
def add_expense(prop_id):
    prop = Property.query.get_or_404(prop_id)

    # Resolve owner — either selected or inferred from property
    owner_id = request.form.get('owner_id') or None
    if not owner_id:
        po = PropertyOwner.query.filter_by(property_id=prop_id).first()
        owner_id = po.owner_id if po else None

    util_id = request.form.get('utility_id') or None
    util_type = request.form.get('utility_type', 'Other')
    # If a utility account is selected, copy its type for denormalization
    if util_id:
        u = Utility.query.get(int(util_id))
        if u:
            util_type = u.utility_type

    exp = UtilityExpense(
        property_id=prop_id,
        owner_id=int(owner_id) if owner_id else None,
        utility_id=int(util_id) if util_id else None,
        utility_type=util_type,
        description=request.form.get('description', ''),
        amount=_decimal(request.form.get('amount')),
        expense_date=_date(request.form.get('expense_date')),
        billing_period=request.form.get('billing_period', ''),
        settlement_status='Pending',
    )
    db.session.add(exp)
    db.session.commit()
    flash('Expense added to ledger.', 'success')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='utilities'))


@utilities_bp.route('/utility-expenses/<int:exp_id>/delete', methods=['POST'])
def delete_expense(exp_id):
    exp = UtilityExpense.query.get_or_404(exp_id)
    prop_id = exp.property_id
    db.session.delete(exp)
    db.session.commit()
    flash('Expense removed.', 'info')
    return redirect(url_for('properties.property_detail', prop_id=prop_id, tab='utilities'))


# ── Ledger settlement endpoints (called from /ledger) ────────────────────────

@utilities_bp.route('/ledger/utility-expense/<int:exp_id>/deduct', methods=['POST'])
def deduct_expense(exp_id):
    exp = UtilityExpense.query.get_or_404(exp_id)
    exp.settlement_status = 'Deducted'
    exp.settlement_date = _date(request.form.get('settlement_date')) or date.today()
    exp.settlement_notes = request.form.get('settlement_notes', '')
    db.session.commit()
    flash('Utility expense marked as deducted.', 'success')
    return redirect(url_for('ledger.list_ledger'))


@utilities_bp.route('/ledger/utility-expense/<int:exp_id>/reopen', methods=['POST'])
def reopen_expense(exp_id):
    exp = UtilityExpense.query.get_or_404(exp_id)
    exp.settlement_status = 'Pending'
    exp.settlement_date = None
    exp.settlement_notes = None
    db.session.commit()
    flash('Utility expense moved back to pending.', 'info')
    return redirect(url_for('ledger.list_ledger'))
