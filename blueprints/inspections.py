from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Inspection, Property
from datetime import date

inspections_bp = Blueprint('inspections', __name__)

INSPECTION_TYPES = ['Move-In', 'Move-Out', 'Routine', 'Annual', 'Drive-By', 'Pre-Listing', 'Maintenance Follow-Up']
CONDITIONS = ['Excellent', 'Good', 'Fair', 'Poor', 'Needs Immediate Attention']
STATUSES = ['Passed', 'Conditional Pass', 'Failed', 'Pending Review', 'Cancelled']
RATINGS = ['Excellent', 'Good', 'Fair', 'Poor', 'N/A']
YES_NO = ['Yes', 'No']


@inspections_bp.route('/inspections')
def list_inspections():
    query = Inspection.query
    property_f = request.args.get('property_id', '')
    type_f = request.args.get('type', '')
    status_f = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    if property_f:
        query = query.filter(Inspection.property_id == int(property_f))
    if type_f:
        query = query.filter(Inspection.inspection_type == type_f)
    if status_f:
        query = query.filter(Inspection.status == status_f)
    if date_from:
        query = query.filter(Inspection.inspection_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.filter(Inspection.inspection_date <= date.fromisoformat(date_to))

    inspections = query.order_by(Inspection.inspection_date.desc()).all()

    passed = sum(1 for i in inspections if i.status == 'Passed')
    failed = sum(1 for i in inspections if i.status == 'Failed')
    pending = sum(1 for i in inspections if i.status == 'Pending Review')

    properties = Property.query.order_by(Property.address).all()
    return render_template('inspections/list.html',
                           inspections=inspections,
                           passed=passed, failed=failed, pending=pending,
                           properties=properties,
                           inspection_types=INSPECTION_TYPES,
                           statuses=STATUSES,
                           property_f=property_f, type_f=type_f,
                           status_f=status_f, date_from=date_from, date_to=date_to)


@inspections_bp.route('/inspections/new', methods=['GET', 'POST'])
def new_inspection():
    properties = Property.query.order_by(Property.address).all()
    if request.method == 'POST':
        insp = _build_inspection(Inspection(), request.form)
        db.session.add(insp)
        db.session.commit()
        flash('Inspection record created.', 'success')
        return redirect(url_for('inspections.inspection_detail', insp_id=insp.id))
    return render_template('inspections/form.html',
                           properties=properties, insp=None,
                           inspection_types=INSPECTION_TYPES,
                           conditions=CONDITIONS, statuses=STATUSES,
                           ratings=RATINGS, yes_no=YES_NO)


@inspections_bp.route('/inspections/<int:insp_id>')
def inspection_detail(insp_id):
    insp = Inspection.query.get_or_404(insp_id)
    properties = Property.query.order_by(Property.address).all()
    return render_template('inspections/detail.html', insp=insp,
                           properties=properties,
                           inspection_types=INSPECTION_TYPES,
                           conditions=CONDITIONS, statuses=STATUSES,
                           ratings=RATINGS, yes_no=YES_NO)


@inspections_bp.route('/inspections/<int:insp_id>/edit', methods=['POST'])
def edit_inspection(insp_id):
    insp = Inspection.query.get_or_404(insp_id)
    _build_inspection(insp, request.form)
    db.session.commit()
    flash('Inspection updated.', 'success')
    return redirect(url_for('inspections.inspection_detail', insp_id=insp_id))


@inspections_bp.route('/inspections/<int:insp_id>/delete', methods=['POST'])
def delete_inspection(insp_id):
    insp = Inspection.query.get_or_404(insp_id)
    db.session.delete(insp)
    db.session.commit()
    flash('Inspection deleted.', 'info')
    return redirect(url_for('inspections.list_inspections'))


def _build_inspection(insp, form):
    insp.property_id = _int(form.get('property_id'))
    insp.inspection_type = form.get('inspection_type', '')
    insp.inspection_date = _date(form.get('inspection_date'))
    insp.inspector_name = form.get('inspector_name', '')
    insp.tenant_present = form.get('tenant_present', 'No')
    insp.overall_condition = form.get('overall_condition', '')
    insp.status = form.get('status', '')
    insp.kitchen_rating = form.get('kitchen_rating', 'N/A')
    insp.bathrooms_rating = form.get('bathrooms_rating', 'N/A')
    insp.bedrooms_rating = form.get('bedrooms_rating', 'N/A')
    insp.living_areas_rating = form.get('living_areas_rating', 'N/A')
    insp.basement_rating = form.get('basement_rating', 'N/A')
    insp.exterior_rating = form.get('exterior_rating', 'N/A')
    insp.garage_rating = form.get('garage_rating', 'N/A')
    insp.hvac_rating = form.get('hvac_rating', 'N/A')
    insp.plumbing_rating = form.get('plumbing_rating', 'N/A')
    insp.issues_found = form.get('issues_found', 'No')
    insp.issue_details = form.get('issue_details', '')
    insp.photos_taken = form.get('photos_taken', 'No')
    insp.report_sent = form.get('report_sent', 'No')
    insp.report_sent_date = _date(form.get('report_sent_date'))
    insp.follow_up_required = form.get('follow_up_required', 'No')
    insp.follow_up_notes = form.get('follow_up_notes', '')
    insp.notes = form.get('notes', '')
    return insp


def _int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None
