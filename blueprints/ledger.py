from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, WorkOrder, Owner, Property
from datetime import date

ledger_bp = Blueprint('ledger', __name__)


@ledger_bp.route('/ledger')
def list_ledger():
    # All completed WOs billed to owner, grouped by owner
    billed_wos = WorkOrder.query.filter_by(
        billed_to_owner='Yes', status='Completed'
    ).order_by(WorkOrder.date_completed.desc()).all()

    # Build owner buckets
    owner_map = {}
    for wo in billed_wos:
        oid = wo.owner_id or 0
        if oid not in owner_map:
            owner_map[oid] = {
                'owner': wo.owner,
                'pending': [],
                'deducted': [],
                'pending_total': 0,
                'deducted_total': 0,
            }
        amount = float(wo.actual_cost or 0)
        if wo.owner_settlement_status == 'Deducted':
            owner_map[oid]['deducted'].append(wo)
            owner_map[oid]['deducted_total'] += amount
        else:
            owner_map[oid]['pending'].append(wo)
            owner_map[oid]['pending_total'] += amount

    # Sort: owners with pending balance first
    buckets = sorted(owner_map.values(),
                     key=lambda b: b['pending_total'], reverse=True)

    total_outstanding = sum(b['pending_total'] for b in buckets)
    owners_with_balance = sum(1 for b in buckets if b['pending_total'] > 0)
    pending_count = sum(len(b['pending']) for b in buckets)

    return render_template('ledger/list.html',
                           buckets=buckets,
                           total_outstanding=total_outstanding,
                           owners_with_balance=owners_with_balance,
                           pending_count=pending_count)


@ledger_bp.route('/ledger/wo/<int:wo_id>/deduct', methods=['POST'])
def mark_deducted(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)
    wo.owner_settlement_status = 'Deducted'
    wo.owner_settlement_date = _date(request.form.get('settlement_date')) or date.today()
    wo.owner_settlement_notes = request.form.get('settlement_notes', '').strip()
    db.session.commit()
    flash(f'{wo.wo_number} marked as deducted from rent.', 'success')
    return redirect(url_for('ledger.list_ledger'))


@ledger_bp.route('/ledger/wo/<int:wo_id>/reopen', methods=['POST'])
def reopen_billing(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)
    wo.owner_settlement_status = 'Pending'
    wo.owner_settlement_date = None
    wo.owner_settlement_notes = None
    db.session.commit()
    flash(f'{wo.wo_number} moved back to pending.', 'info')
    return redirect(url_for('ledger.list_ledger'))


def _date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None
