import os
import io
import smtplib
from email.message import EmailMessage
from datetime import date

from flask import Blueprint, abort, make_response, request, flash, redirect, url_for
from fpdf import FPDF

from models import db, Inspection, WorkOrder, Owner, Property

pdf_export_bp = Blueprint('pdf_export', __name__)

# ─────────────────────────────────────────
# Shared PDF helpers
# ─────────────────────────────────────────

BRAND_NAVY  = (30, 58, 95)    # #1e3a5f
BRAND_GOLD  = (196, 151, 76)  # #c4974c
LIGHT_GRAY  = (245, 245, 245)
MID_GRAY    = (180, 180, 180)
TEXT_DARK   = (40, 40, 40)
TEXT_MUTED  = (110, 110, 110)


class EverRestPDF(FPDF):
    """Base PDF class with EverRest branding."""

    def header(self):
        # Navy top bar
        self.set_fill_color(*BRAND_NAVY)
        self.rect(0, 0, 210, 14, 'F')
        self.set_y(3)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'EverRest Property Management', align='C')
        self.set_text_color(*TEXT_DARK)
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 8, f'Generated {date.today().strftime("%B %d, %Y")}  |  EverRest Property Management  |  Page {self.page_no()}', align='C')

    def section_title(self, title):
        self.set_fill_color(*BRAND_NAVY)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 9)
        self.cell(0, 7, f'  {title}', fill=True, ln=True)
        self.set_text_color(*TEXT_DARK)
        self.ln(1)

    def kv_row(self, label, value, fill=False):
        if fill:
            self.set_fill_color(*LIGHT_GRAY)
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(*TEXT_MUTED)
        self.cell(50, 6, label, fill=fill)
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(*TEXT_DARK)
        self.cell(0, 6, str(value) if value else '—', fill=fill, ln=True)

    def rating_badge(self, rating):
        """Return color tuple for a rating value."""
        mapping = {
            'Excellent': (40, 167, 69),
            'Good':      (23, 162, 184),
            'Fair':      (255, 193, 7),
            'Poor':      (220, 53, 69),
            'N/A':       (150, 150, 150),
        }
        return mapping.get(rating, (150, 150, 150))


# ─────────────────────────────────────────
# Inspection Report PDF
# ─────────────────────────────────────────

def _build_inspection_pdf(insp):
    pdf = EverRestPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 5, 15)

    prop = insp.property

    # Document title
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*BRAND_NAVY)
    pdf.cell(0, 10, 'Inspection Report', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, f'{insp.inspection_type or "Inspection"}  ·  {prop.address if prop else "Unknown Property"}', ln=True, align='C')
    pdf.ln(4)

    # ── Property Info ──
    pdf.section_title('PROPERTY INFORMATION')
    pdf.kv_row('Address', prop.address if prop else '—', fill=True)
    pdf.kv_row('City / State', f'{prop.city}, {prop.state}' if prop else '—')
    if prop and prop.primary_owner:
        pdf.kv_row('Owner', prop.primary_owner.name, fill=True)
    pdf.ln(3)

    # ── Inspection Details ──
    pdf.section_title('INSPECTION DETAILS')
    pdf.kv_row('Type', insp.inspection_type, fill=True)
    pdf.kv_row('Date', insp.inspection_date.strftime('%B %d, %Y') if insp.inspection_date else '—')
    pdf.kv_row('Inspector', insp.inspector_name, fill=True)
    pdf.kv_row('Tenant Present', insp.tenant_present or '—')
    pdf.kv_row('Overall Condition', insp.overall_condition or '—', fill=True)
    pdf.kv_row('Status', insp.status or '—')
    pdf.kv_row('Issues Found', insp.issues_found or '—', fill=True)
    pdf.kv_row('Photos Taken', insp.photos_taken or '—')
    pdf.ln(3)

    # ── Area Ratings ──
    pdf.section_title('AREA RATINGS')
    areas = [
        ('Kitchen',      insp.kitchen_rating),
        ('Bathrooms',    insp.bathrooms_rating),
        ('Bedrooms',     insp.bedrooms_rating),
        ('Living Areas', insp.living_areas_rating),
        ('Basement',     insp.basement_rating),
        ('Exterior',     insp.exterior_rating),
        ('Garage',       insp.garage_rating),
        ('HVAC',         insp.hvac_rating),
        ('Plumbing',     insp.plumbing_rating),
    ]
    col_w = (pdf.w - 30) / 3
    for i, (label, rating) in enumerate(areas):
        if i % 3 == 0:
            pdf.set_x(15)
        fill_bg = (i // 3) % 2 == 0
        if fill_bg:
            pdf.set_fill_color(*LIGHT_GRAY)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(col_w * 0.55, 6, label, fill=fill_bg)

        # Colored rating pill
        r, g, b = pdf.rating_badge(rating)
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.cell(col_w * 0.45, 6, rating or 'N/A', fill=True, align='C')

        if (i + 1) % 3 == 0 or i == len(areas) - 1:
            pdf.ln()

    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(3)

    # ── Issues ──
    if insp.issues_found == 'Yes' or insp.issue_details:
        pdf.section_title('ISSUES FOUND')
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(0, 5.5, insp.issue_details or 'Issues found — no details recorded.')
        pdf.ln(2)

    # ── Follow-Up ──
    if insp.follow_up_required == 'Yes' or insp.follow_up_notes:
        pdf.section_title('FOLLOW-UP REQUIRED')
        pdf.set_font('Helvetica', '', 8.5)
        pdf.multi_cell(0, 5.5, insp.follow_up_notes or 'Follow-up required — no notes recorded.')
        pdf.ln(2)

    # ── Notes ──
    if insp.notes:
        pdf.section_title('GENERAL NOTES')
        pdf.set_font('Helvetica', '', 8.5)
        pdf.multi_cell(0, 5.5, insp.notes)
        pdf.ln(2)

    # ── Report Sent ──
    pdf.section_title('REPORT STATUS')
    pdf.kv_row('Report Sent', insp.report_sent or '—', fill=True)
    pdf.kv_row('Date Sent', insp.report_sent_date.strftime('%B %d, %Y') if insp.report_sent_date else '—')

    return bytes(pdf.output())


# ─────────────────────────────────────────
# Owner Invoice PDF
# ─────────────────────────────────────────

def _build_invoice_pdf(owner, wos):
    pdf = EverRestPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 5, 15)

    # Document title
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*BRAND_NAVY)
    pdf.cell(0, 10, 'Owner Billing Invoice', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, f'Repair costs billed to owner  ·  {date.today().strftime("%B %d, %Y")}', ln=True, align='C')
    pdf.ln(4)

    # ── Owner Info ──
    pdf.section_title('OWNER INFORMATION')
    pdf.kv_row('Name',  owner.name if owner else 'Unknown', fill=True)
    pdf.kv_row('Email', owner.email or '—')
    pdf.kv_row('Phone', owner.phone or '—', fill=True)
    pdf.ln(3)

    # ── Work Orders table ──
    pdf.section_title('BILLED WORK ORDERS')

    # Table header
    col_wo   = 22
    col_prop = 55
    col_cat  = 30
    col_date = 25
    col_amt  = 22
    col_stat = 26

    pdf.set_fill_color(*BRAND_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(col_wo,   6, 'WO #',      fill=True)
    pdf.cell(col_prop, 6, 'Property',  fill=True)
    pdf.cell(col_cat,  6, 'Category',  fill=True)
    pdf.cell(col_date, 6, 'Completed', fill=True)
    pdf.cell(col_amt,  6, 'Amount',    fill=True, align='R')
    pdf.cell(col_stat, 6, 'Status',    fill=True, align='C')
    pdf.ln()
    pdf.set_text_color(*TEXT_DARK)

    pending_total  = 0.0
    deducted_total = 0.0

    for i, wo in enumerate(wos):
        fill = i % 2 == 0
        if fill:
            pdf.set_fill_color(*LIGHT_GRAY)
        else:
            pdf.set_fill_color(255, 255, 255)

        amount = float(wo.actual_cost or 0)
        status = wo.owner_settlement_status or 'Pending'
        prop_addr = (wo.property.address[:30] + '…') if wo.property and len(wo.property.address) > 30 else (wo.property.address if wo.property else '—')
        category  = (wo.category[:14] + '…') if wo.category and len(wo.category) > 14 else (wo.category or '—')

        pdf.set_font('Helvetica', '', 8)
        pdf.cell(col_wo,   5.5, wo.wo_number or '—',                                          fill=fill)
        pdf.cell(col_prop, 5.5, prop_addr,                                                     fill=fill)
        pdf.cell(col_cat,  5.5, category,                                                      fill=fill)
        pdf.cell(col_date, 5.5, wo.date_completed.strftime('%m/%d/%Y') if wo.date_completed else '—', fill=fill)
        pdf.cell(col_amt,  5.5, f'${amount:,.2f}',                                            fill=fill, align='R')
        pdf.cell(col_stat, 5.5, status,                                                        fill=fill, align='C')
        pdf.ln()

        if status == 'Deducted':
            deducted_total += amount
        else:
            pending_total  += amount

    # If a WO has description, add a notes row below it
    # (keep table clean — only show if issues/notes exist)
    pdf.ln(2)

    # ── Totals ──
    pdf.set_fill_color(*BRAND_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    total_width = col_wo + col_prop + col_cat + col_date
    pdf.cell(total_width, 7, '', fill=True)
    pdf.cell(col_amt, 7, f'${pending_total:,.2f}', fill=True, align='R')
    pdf.cell(col_stat, 7, 'PENDING', fill=True, align='C')
    pdf.ln()

    pdf.set_fill_color(*BRAND_GOLD)
    pdf.cell(total_width, 7, 'TOTAL OUTSTANDING', fill=True)
    pdf.cell(col_amt + col_stat, 7, f'${pending_total:,.2f}', fill=True, align='R')
    pdf.ln(3)
    pdf.set_text_color(*TEXT_DARK)

    if deducted_total > 0:
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 6, f'Previously deducted from rent:  ${deducted_total:,.2f}', ln=True, align='R')
        pdf.set_text_color(*TEXT_DARK)

    # ── WO Descriptions (detail block) ──
    has_desc = any(wo.description for wo in wos)
    if has_desc:
        pdf.ln(2)
        pdf.section_title('WORK ORDER DESCRIPTIONS')
        for wo in wos:
            if wo.description:
                pdf.set_font('Helvetica', 'B', 8.5)
                pdf.cell(0, 5.5, f'{wo.wo_number}  —  {wo.property.address if wo.property else ""}', ln=True)
                pdf.set_font('Helvetica', '', 8.5)
                pdf.multi_cell(0, 5, wo.description)
                pdf.ln(1)

    return bytes(pdf.output())


# ─────────────────────────────────────────
# Email helper
# ─────────────────────────────────────────

def _send_pdf_email(to_address, subject, body, pdf_bytes, filename):
    mail_user = os.environ.get('MAIL_USER')
    mail_pass = os.environ.get('MAIL_PASSWORD')

    if not mail_user or not mail_pass:
        raise RuntimeError('Email not configured. Set MAIL_USER and MAIL_PASSWORD environment variables.')

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = mail_user
    msg['To']      = to_address
    msg.set_content(body)
    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=filename)

    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(mail_user, mail_pass)
        smtp.send_message(msg)


# ─────────────────────────────────────────
# Routes — Inspection
# ─────────────────────────────────────────

@pdf_export_bp.route('/inspections/<int:insp_id>/pdf')
def inspection_pdf(insp_id):
    insp = Inspection.query.get_or_404(insp_id)
    pdf_bytes = _build_inspection_pdf(insp)

    prop_slug = insp.property.address.replace(' ', '_')[:30] if insp.property else f'insp_{insp_id}'
    filename  = f'Inspection_{prop_slug}_{insp_id}.pdf'

    response = make_response(pdf_bytes)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@pdf_export_bp.route('/inspections/<int:insp_id>/email-pdf', methods=['POST'])
def inspection_email_pdf(insp_id):
    insp     = Inspection.query.get_or_404(insp_id)
    to_email = request.form.get('email', '').strip()

    if not to_email:
        flash('Please enter a recipient email address.', 'warning')
        return redirect(url_for('inspections.inspection_detail', insp_id=insp_id))

    try:
        pdf_bytes = _build_inspection_pdf(insp)
        prop_addr = insp.property.address if insp.property else 'Property'
        prop_slug = prop_addr.replace(' ', '_')[:30]
        filename  = f'Inspection_{prop_slug}_{insp_id}.pdf'

        subject = f'Inspection Report — {prop_addr}'
        body    = (
            f'Please find attached the inspection report for {prop_addr}.\n\n'
            f'Type: {insp.inspection_type or "—"}\n'
            f'Date: {insp.inspection_date.strftime("%B %d, %Y") if insp.inspection_date else "—"}\n'
            f'Inspector: {insp.inspector_name or "—"}\n'
            f'Status: {insp.status or "—"}\n\n'
            f'EverRest Property Management'
        )
        _send_pdf_email(to_email, subject, body, pdf_bytes, filename)
        flash(f'Inspection report sent to {to_email}.', 'success')

    except RuntimeError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'Failed to send email: {e}', 'danger')

    return redirect(url_for('inspections.inspection_detail', insp_id=insp_id))


# ─────────────────────────────────────────
# Routes — Owner Invoice
# ─────────────────────────────────────────

@pdf_export_bp.route('/ledger/owner/<int:owner_id>/pdf')
def owner_invoice_pdf(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    wos   = WorkOrder.query.filter_by(
        owner_id=owner_id, billed_to_owner='Yes', status='Completed'
    ).order_by(WorkOrder.date_completed.desc()).all()

    if not wos:
        abort(404, description='No billed work orders found for this owner.')

    pdf_bytes = _build_invoice_pdf(owner, wos)
    name_slug = owner.name.replace(' ', '_')[:25]
    filename  = f'Invoice_{name_slug}_{date.today().isoformat()}.pdf'

    response = make_response(pdf_bytes)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@pdf_export_bp.route('/ledger/owner/<int:owner_id>/email-pdf', methods=['POST'])
def owner_invoice_email_pdf(owner_id):
    owner    = Owner.query.get_or_404(owner_id)
    to_email = request.form.get('email', '').strip()

    if not to_email:
        flash('Please enter a recipient email address.', 'warning')
        return redirect(url_for('ledger.list_ledger'))

    wos = WorkOrder.query.filter_by(
        owner_id=owner_id, billed_to_owner='Yes', status='Completed'
    ).order_by(WorkOrder.date_completed.desc()).all()

    if not wos:
        flash('No billed work orders found for this owner.', 'warning')
        return redirect(url_for('ledger.list_ledger'))

    try:
        pdf_bytes = _build_invoice_pdf(owner, wos)
        name_slug = owner.name.replace(' ', '_')[:25]
        filename  = f'Invoice_{name_slug}_{date.today().isoformat()}.pdf'

        subject = f'Owner Billing Invoice — {owner.name}'
        body    = (
            f'Dear {owner.name},\n\n'
            f'Please find attached your billing invoice for repair costs to be deducted from your rent disbursement.\n\n'
            f'If you have any questions, please reach out to EverRest Property Management.\n\n'
            f'EverRest Property Management'
        )
        _send_pdf_email(to_email, subject, body, pdf_bytes, filename)
        flash(f'Invoice sent to {to_email}.', 'success')

    except RuntimeError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'Failed to send email: {e}', 'danger')

    return redirect(url_for('ledger.list_ledger'))
