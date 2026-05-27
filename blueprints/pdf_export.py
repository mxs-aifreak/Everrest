import os
import io
import smtplib
from email.message import EmailMessage
from datetime import date

from flask import Blueprint, abort, make_response, request, flash, redirect, url_for
from fpdf import FPDF

from models import db, Inspection, WorkOrder, Owner, Property

pdf_export_bp = Blueprint('pdf_export', __name__)

# Logo path — sits in static/logo/ so Railway has it after git push
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'static', 'logo', 'EverRest_Logo.png')

# ─────────────────────────────────────────
# Brand palette (from EverRest_Brand_Profile.md)
# ─────────────────────────────────────────

NAVY        = (15,  27,  46)   # #0F1B2E  primary navy
ORANGE      = (217, 101, 30)   # #D9651E  accent orange
COOL_BLUE   = (63,  110, 140)  # #3F6E8C  dusk blue
IVORY       = (241, 232, 210)  # #F1E8D2  cream
STONE       = (138, 153, 166)  # #8A99A6  stone gray
GREEN_PAY   = (39,  174, 96)   # payment-positive green
TEXT_DARK   = (28,  28,  28)
TEXT_MUTED  = (110, 110, 110)
WHITE       = (255, 255, 255)

# Per-document color schemes
SCHEMES = {
    'inspection': {
        'header_bg':   COOL_BLUE,          # section header bars
        'row_alt':     (235, 244, 250),    # light blue alternating rows
        'title_color': NAVY,
        'total_bg':    COOL_BLUE,
    },
    'invoice': {
        'header_bg':   ORANGE,             # warm orange section headers
        'row_alt':     (251, 246, 238),    # warm ivory alternating rows
        'title_color': NAVY,
        'total_bg':    GREEN_PAY,          # green = "go, pay, positive"
    },
}


def _s(text, fallback='-'):
    """Sanitize text for Helvetica (Latin-1 only). Replaces unmappable chars with '?'."""
    if not text:
        return fallback
    return str(text).encode('latin-1', errors='replace').decode('latin-1')


class EverRestPDF(FPDF):
    """Base PDF class with EverRest branding and logo watermark."""

    def __init__(self, scheme='inspection'):
        super().__init__()
        self.scheme = SCHEMES.get(scheme, SCHEMES['inspection'])

    def header(self):
        # Navy top bar with company name
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 16, 'F')
        self.set_y(4)
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*WHITE)
        self.cell(0, 8, 'EverRest Property Management', align='C')
        self.set_text_color(*TEXT_DARK)

        # Logo watermark — centered on page, faint, rotated 30 degrees
        if os.path.exists(LOGO_PATH):
            logo_size = 110
            cx = self.w / 2
            cy = self.h / 2
            with self.local_context(fill_opacity=0.06, stroke_opacity=0.06):
                with self.rotation(30, cx, cy):
                    self.image(LOGO_PATH,
                               x=cx - logo_size / 2,
                               y=cy - logo_size / 2,
                               w=logo_size, h=logo_size)

        self.ln(16)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 7.5)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 8,
                  f'Generated {date.today().strftime("%B %d, %Y")}  |'
                  f'  EverRest Property Management  |  everrestproperties.com  |'
                  f'  Page {self.page_no()}',
                  align='C')

    def section_title(self, title):
        self.set_fill_color(*self.scheme['header_bg'])
        self.set_text_color(*WHITE)
        self.set_font('Helvetica', 'B', 9)
        self.cell(0, 7, f'  {title}', fill=True, ln=True)
        self.set_text_color(*TEXT_DARK)
        self.ln(1)

    def kv_row(self, label, value, fill=False):
        if fill:
            self.set_fill_color(*self.scheme['row_alt'])
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(*TEXT_MUTED)
        self.cell(50, 6, label, fill=fill)
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(*TEXT_DARK)
        self.cell(0, 6, str(value) if value else '-', fill=fill, ln=True)

    def rating_badge(self, rating):
        mapping = {
            'Excellent': (40,  167,  69),
            'Good':      (23,  162, 184),
            'Fair':      (232, 144,  44),
            'Poor':      (220,  53,  69),
            'N/A':       (150, 150, 150),
        }
        return mapping.get(rating, (150, 150, 150))


# ─────────────────────────────────────────
# Inspection Report PDF
# ─────────────────────────────────────────

def _build_inspection_pdf(insp):
    pdf = EverRestPDF(scheme='inspection')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 5, 15)

    prop = insp.property

    # Document title
    pdf.set_font('Helvetica', 'B', 17)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, 'Inspection Report', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6,
             _s(f'{insp.inspection_type or "Inspection"}  -  {prop.address if prop else "Unknown Property"}'),
             ln=True, align='C')
    # Thin accent line under title
    pdf.set_draw_color(*COOL_BLUE)
    pdf.set_line_width(0.5)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(5)

    # Property Info
    pdf.section_title('PROPERTY INFORMATION')
    pdf.kv_row('Address',    _s(prop.address) if prop else '-',               fill=True)
    pdf.kv_row('City / State', _s(f'{prop.city}, {prop.state}') if prop else '-')
    if prop and prop.primary_owner:
        pdf.kv_row('Owner',  _s(prop.primary_owner.name),                    fill=True)
    pdf.ln(3)

    # Inspection Details
    pdf.section_title('INSPECTION DETAILS')
    pdf.kv_row('Type',             _s(insp.inspection_type),                 fill=True)
    pdf.kv_row('Date',             insp.inspection_date.strftime('%B %d, %Y') if insp.inspection_date else '-')
    pdf.kv_row('Inspector',        _s(insp.inspector_name),                  fill=True)
    pdf.kv_row('Tenant Present',   _s(insp.tenant_present))
    pdf.kv_row('Overall Condition',_s(insp.overall_condition),               fill=True)
    pdf.kv_row('Status',           _s(insp.status))
    pdf.kv_row('Issues Found',     _s(insp.issues_found),                    fill=True)
    pdf.kv_row('Photos Taken',     _s(insp.photos_taken))
    pdf.ln(3)

    # Area Ratings
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
        pdf.set_fill_color(*(pdf.scheme['row_alt'] if fill_bg else (255, 255, 255)))
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(col_w * 0.55, 6, label, fill=fill_bg)
        r, g, b = pdf.rating_badge(rating)
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(*WHITE)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.cell(col_w * 0.45, 6, rating or 'N/A', fill=True, align='C')
        if (i + 1) % 3 == 0 or i == len(areas) - 1:
            pdf.ln()

    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(3)

    # Issues
    if insp.issues_found == 'Yes' or insp.issue_details:
        pdf.section_title('ISSUES FOUND')
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(0, 5.5, _s(insp.issue_details or 'Issues found - no details recorded.'))
        pdf.ln(2)

    # Follow-Up
    if insp.follow_up_required == 'Yes' or insp.follow_up_notes:
        pdf.section_title('FOLLOW-UP REQUIRED')
        pdf.set_font('Helvetica', '', 8.5)
        pdf.multi_cell(0, 5.5, _s(insp.follow_up_notes or 'Follow-up required - no notes recorded.'))
        pdf.ln(2)

    # Notes
    if insp.notes:
        pdf.section_title('GENERAL NOTES')
        pdf.set_font('Helvetica', '', 8.5)
        pdf.multi_cell(0, 5.5, _s(insp.notes))
        pdf.ln(2)

    # Report Status
    pdf.section_title('REPORT STATUS')
    pdf.kv_row('Report Sent', _s(insp.report_sent), fill=True)
    pdf.kv_row('Date Sent', insp.report_sent_date.strftime('%B %d, %Y') if insp.report_sent_date else '-')

    return bytes(pdf.output())


# ─────────────────────────────────────────
# Owner Invoice PDF
# ─────────────────────────────────────────

def _build_invoice_pdf(owner, wos):
    pdf = EverRestPDF(scheme='invoice')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 5, 15)

    # Document title
    pdf.set_font('Helvetica', 'B', 17)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, 'Owner Billing Invoice', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, f'EverRest Property Management  -  {date.today().strftime("%B %d, %Y")}',
             ln=True, align='C')
    # Warm accent line
    pdf.set_draw_color(*ORANGE)
    pdf.set_line_width(0.5)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(5)

    # Owner Info
    pdf.section_title('OWNER INFORMATION')
    pdf.kv_row('Name',  _s(owner.name) if owner else 'Unknown', fill=True)
    pdf.kv_row('Email', _s(owner.email))
    pdf.kv_row('Phone', _s(owner.phone), fill=True)
    pdf.ln(3)

    # Work Orders table
    pdf.section_title('BILLED WORK ORDERS')

    col_wo   = 22
    col_prop = 55
    col_cat  = 30
    col_date = 25
    col_amt  = 22
    col_stat = 26

    # Table column headers
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
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
        pdf.set_fill_color(*(pdf.scheme['row_alt'] if fill else (255, 255, 255)))

        amount    = float(wo.actual_cost or 0)
        status    = wo.owner_settlement_status or 'Pending'
        raw_addr  = wo.property.address if wo.property else '-'
        prop_addr = _s(raw_addr[:30] + '...' if len(raw_addr) > 30 else raw_addr)
        category  = _s(wo.category[:14] + '...' if wo.category and len(wo.category) > 14 else (wo.category or '-'))

        pdf.set_font('Helvetica', '', 8)
        pdf.cell(col_wo,   5.5, _s(wo.wo_number or '-'),                                       fill=fill)
        pdf.cell(col_prop, 5.5, prop_addr,                                                      fill=fill)
        pdf.cell(col_cat,  5.5, category,                                                       fill=fill)
        pdf.cell(col_date, 5.5, wo.date_completed.strftime('%m/%d/%Y') if wo.date_completed else '-', fill=fill)
        pdf.cell(col_amt,  5.5, f'${amount:,.2f}',                                             fill=fill, align='R')
        pdf.cell(col_stat, 5.5, _s(status),                                                     fill=fill, align='C')
        pdf.ln()

        if status == 'Deducted':
            deducted_total += amount
        else:
            pending_total  += amount

    pdf.ln(2)

    # Totals — green "go pay" bar
    total_width = col_wo + col_prop + col_cat + col_date
    pdf.set_fill_color(*GREEN_PAY)
    pdf.set_text_color(*WHITE)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(total_width, 8, 'TOTAL AMOUNT DUE', fill=True)
    pdf.cell(col_amt + col_stat, 8, f'${pending_total:,.2f}', fill=True, align='R', ln=True)
    pdf.ln(4)
    pdf.set_text_color(*TEXT_DARK)

    if deducted_total > 0:
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 6, f'Previously settled (deducted from rent):  ${deducted_total:,.2f}',
                 ln=True, align='R')
        pdf.set_text_color(*TEXT_DARK)

    # Work Order descriptions
    has_desc = any(wo.description for wo in wos)
    if has_desc:
        pdf.ln(2)
        pdf.section_title('WORK ORDER DETAILS')
        for wo in wos:
            if wo.description:
                pdf.set_font('Helvetica', 'B', 8.5)
                pdf.set_text_color(*NAVY)
                pdf.cell(0, 5.5,
                         _s(f'{wo.wo_number}  -  {wo.property.address if wo.property else ""}'),
                         ln=True)
                pdf.set_font('Helvetica', '', 8.5)
                pdf.set_text_color(*TEXT_DARK)
                pdf.multi_cell(0, 5, _s(wo.description))
                pdf.ln(1)

    # Friendly payment note
    pdf.ln(4)
    pdf.set_fill_color(*(251, 246, 238))
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.multi_cell(0, 5,
                   'This amount will be deducted from your next rent disbursement. '
                   'Please contact us at info@everrestproperties.com or 307-460-1692 '
                   'if you have any questions.',
                   fill=True)

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

        subject = f'Inspection Report - {prop_addr}'
        body    = (
            f'Please find attached the inspection report for {prop_addr}.\n\n'
            f'Type: {insp.inspection_type or "-"}\n'
            f'Date: {insp.inspection_date.strftime("%B %d, %Y") if insp.inspection_date else "-"}\n'
            f'Inspector: {insp.inspector_name or "-"}\n'
            f'Status: {insp.status or "-"}\n\n'
            f'EverRest Property Management\n'
            f'everrestproperties.com  |  info@everrestproperties.com'
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

        subject = f'Owner Billing Invoice - {owner.name}'
        body    = (
            f'Dear {owner.name},\n\n'
            f'Please find attached your billing invoice for repair costs '
            f'to be deducted from your next rent disbursement.\n\n'
            f'If you have any questions, please reach out to us.\n\n'
            f'EverRest Property Management\n'
            f'everrestproperties.com  |  info@everrestproperties.com\n'
            f'307-460-1692'
        )
        _send_pdf_email(to_email, subject, body, pdf_bytes, filename)
        flash(f'Invoice sent to {to_email}.', 'success')

    except RuntimeError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'Failed to send email: {e}', 'danger')

    return redirect(url_for('ledger.list_ledger'))
