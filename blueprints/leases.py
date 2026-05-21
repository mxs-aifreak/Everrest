from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Occupancy, Property
from datetime import date

leases_bp = Blueprint('leases', __name__)

RENEWAL_STATUSES = ['Unknown', 'Renewing', 'Moving Out', 'Negotiating']


def _days_left(lease_end):
    if not lease_end:
        return None
    return (lease_end - date.today()).days


def _urgency(days):
    if days is None:
        return 'no_date'
    if days < 0:
        return 'expired'
    if days <= 30:
        return 'critical'
    if days <= 90:
        return 'soon'
    return 'ok'


def _urgency_order(u):
    return {'expired': 0, 'critical': 1, 'soon': 2, 'ok': 3, 'no_date': 4}[u]


@leases_bp.route('/leases')
def list_leases():
    renewal_filter = request.args.get('renewal', '')
    occupancies = Occupancy.query.filter(
        Occupancy.status.in_(['Occupied', 'Notice Given'])
    ).all()

    rows = []
    for occ in occupancies:
        days = _days_left(occ.lease_end)
        urgency = _urgency(days)
        if renewal_filter and occ.renewal_status != renewal_filter:
            continue
        rows.append({
            'occ': occ,
            'property': occ.property,
            'days': days,
            'urgency': urgency,
        })

    rows.sort(key=lambda r: (_urgency_order(r['urgency']),
                             r['days'] if r['days'] is not None else 9999))

    # KPIs
    all_occ = Occupancy.query.filter(
        Occupancy.status.in_(['Occupied', 'Notice Given'])
    ).all()
    all_rows = [{'days': _days_left(o.lease_end),
                 'urgency': _urgency(_days_left(o.lease_end)),
                 'renewal': o.renewal_status} for o in all_occ]

    kpis = {
        'total': len(all_rows),
        'expired': sum(1 for r in all_rows if r['urgency'] == 'expired'),
        'critical': sum(1 for r in all_rows if r['urgency'] == 'critical'),
        'soon': sum(1 for r in all_rows if r['urgency'] == 'soon'),
        'ok': sum(1 for r in all_rows if r['urgency'] == 'ok'),
        'renewing': sum(1 for r in all_rows if r['renewal'] == 'Renewing'),
        'moving_out': sum(1 for r in all_rows if r['renewal'] == 'Moving Out'),
        'unknown': sum(1 for r in all_rows if r['renewal'] in ('Unknown', None, '')),
    }

    return render_template('leases/list.html', rows=rows, kpis=kpis,
                           renewal_statuses=RENEWAL_STATUSES,
                           renewal_filter=renewal_filter)


@leases_bp.route('/leases/<int:occ_id>/update', methods=['POST'])
def update_lease(occ_id):
    occ = Occupancy.query.get_or_404(occ_id)
    occ.renewal_status = request.form.get('renewal_status', occ.renewal_status)
    occ.renewal_contacted_date = _date(request.form.get('renewal_contacted_date'))
    occ.renewal_notes = request.form.get('renewal_notes', '').strip()
    db.session.commit()
    flash('Lease renewal status updated.', 'success')
    return redirect(url_for('leases.list_leases'))


def _date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None
