from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, WorkOrder, Property, Owner
from datetime import date
import calendar

work_orders_bp = Blueprint('work_orders', __name__)

CATEGORIES = ['Plumbing', 'Electrical', 'HVAC', 'Sprinkler Repair', 'Carpet Cleaning',
              'Painting', 'Landscaping', 'Appliance', 'Structural', 'General Maintenance', 'Other']
PRIORITIES = ['Critical', 'High', 'Medium', 'Low']
STATUSES = ['Open', 'Assigned', 'In Progress', 'Pending Approval', 'Completed', 'On Hold', 'Cancelled']
INVOICE_STATUSES = ['Pending', 'Received', 'Disputed', 'N/A']


@work_orders_bp.route('/work-orders')
def list_work_orders():
    query = WorkOrder.query
    status_f = request.args.get('status', '')
    priority_f = request.args.get('priority', '')
    category_f = request.args.get('category', '')
    property_f = request.args.get('property_id', '')
    search = request.args.get('search', '')

    if status_f:
        query = query.filter(WorkOrder.status == status_f)
    if priority_f:
        query = query.filter(WorkOrder.priority == priority_f)
    if category_f:
        query = query.filter(WorkOrder.category == category_f)
    if property_f:
        query = query.filter(WorkOrder.property_id == int(property_f))
    if search:
        query = query.filter(
            (WorkOrder.wo_number.ilike(f'%{search}%')) |
            (WorkOrder.description.ilike(f'%{search}%')) |
            (WorkOrder.vendor_name.ilike(f'%{search}%'))
        )

    work_orders = query.order_by(WorkOrder.id.desc()).all()

    # Monthly summary strip for current year
    year = date.today().year
    monthly_summary = []
    for m in range(1, 13):
        start = date(year, m, 1)
        end_day = calendar.monthrange(year, m)[1]
        end = date(year, m, end_day)
        wos = WorkOrder.query.filter(
            WorkOrder.date_submitted >= start,
            WorkOrder.date_submitted <= end
        ).all()
        total_cost = sum(float(w.actual_cost or 0) for w in wos)
        monthly_summary.append({
            'month': calendar.month_abbr[m],
            'count': len(wos),
            'total': total_cost,
        })

    properties = Property.query.order_by(Property.address).all()
    return render_template('work_orders/list.html',
                           work_orders=work_orders,
                           monthly_summary=monthly_summary,
                           properties=properties,
                           categories=CATEGORIES,
                           priorities=PRIORITIES,
                           statuses=STATUSES,
                           status_f=status_f, priority_f=priority_f,
                           category_f=category_f, property_f=property_f,
                           search=search)


@work_orders_bp.route('/work-orders/new', methods=['GET', 'POST'])
def new_work_order():
    properties = Property.query.order_by(Property.address).all()
    owners = Owner.query.order_by(Owner.name).all()
    if request.method == 'POST':
        wo_num = _next_wo_number()
        wo = WorkOrder(
            wo_number=wo_num,
            property_id=_int(request.form.get('property_id')),
            owner_id=_int(request.form.get('owner_id')),
            date_submitted=_date(request.form.get('date_submitted')) or date.today(),
            category=request.form.get('category', ''),
            description=request.form.get('description', ''),
            priority=request.form.get('priority', 'Medium'),
            vendor_name=request.form.get('vendor_name', ''),
            vendor_phone=request.form.get('vendor_phone', ''),
            date_assigned=_date(request.form.get('date_assigned')),
            target_completion=_date(request.form.get('target_completion')),
            status=request.form.get('status', 'Open'),
            date_completed=_date(request.form.get('date_completed')),
            estimated_cost=_decimal(request.form.get('estimated_cost')),
            actual_cost=_decimal(request.form.get('actual_cost')),
            invoice_number=request.form.get('invoice_number', ''),
            invoice_status=request.form.get('invoice_status', 'N/A'),
            notes=request.form.get('notes', ''),
            source='Manual',
        )
        db.session.add(wo)
        db.session.commit()
        flash(f'Work Order {wo_num} created.', 'success')
        return redirect(url_for('work_orders.work_order_detail', wo_id=wo.id))
    return render_template('work_orders/form.html',
                           properties=properties, owners=owners,
                           categories=CATEGORIES, priorities=PRIORITIES,
                           statuses=STATUSES, invoice_statuses=INVOICE_STATUSES,
                           wo=None)


@work_orders_bp.route('/work-orders/<int:wo_id>')
def work_order_detail(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)
    properties = Property.query.order_by(Property.address).all()
    owners = Owner.query.order_by(Owner.name).all()
    return render_template('work_orders/detail.html', wo=wo,
                           properties=properties, owners=owners,
                           categories=CATEGORIES, priorities=PRIORITIES,
                           statuses=STATUSES, invoice_statuses=INVOICE_STATUSES)


@work_orders_bp.route('/work-orders/<int:wo_id>/edit', methods=['POST'])
def edit_work_order(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)
    wo.property_id = _int(request.form.get('property_id'))
    wo.owner_id = _int(request.form.get('owner_id'))
    wo.date_submitted = _date(request.form.get('date_submitted')) or wo.date_submitted
    wo.category = request.form.get('category', wo.category)
    wo.description = request.form.get('description', wo.description)
    wo.priority = request.form.get('priority', wo.priority)
    wo.vendor_name = request.form.get('vendor_name', '')
    wo.vendor_phone = request.form.get('vendor_phone', '')
    wo.date_assigned = _date(request.form.get('date_assigned'))
    wo.target_completion = _date(request.form.get('target_completion'))
    wo.status = request.form.get('status', wo.status)
    wo.date_completed = _date(request.form.get('date_completed'))
    wo.estimated_cost = _decimal(request.form.get('estimated_cost'))
    wo.actual_cost = _decimal(request.form.get('actual_cost'))
    wo.invoice_number = request.form.get('invoice_number', '')
    wo.invoice_status = request.form.get('invoice_status', wo.invoice_status)
    wo.notes = request.form.get('notes', '')
    db.session.commit()
    flash('Work Order updated.', 'success')
    return redirect(url_for('work_orders.work_order_detail', wo_id=wo_id))


@work_orders_bp.route('/work-orders/<int:wo_id>/delete', methods=['POST'])
def delete_work_order(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)
    db.session.delete(wo)
    db.session.commit()
    flash('Work Order deleted.', 'info')
    return redirect(url_for('work_orders.list_work_orders'))


def _next_wo_number():
    year = date.today().year
    count = WorkOrder.query.filter(WorkOrder.wo_number.like(f'WO-{year}-%')).count()
    return f'WO-{year}-{count + 1:03d}'


def _int(val):
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


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
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None
