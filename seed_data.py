"""
EverRest Property Management — real data seed.
Loaded from EverRest_Runbook_v2.xlsx on 2026-05-16.
Run once on first boot; skipped if real data already exists.
"""
from models import db, Property, Owner, PropertyOwner, Occupancy, Sprinkler, WorkOrder, Inspection
from datetime import date
import urllib.parse


def _d(val):
    """Parse ISO date string or return None."""
    if not val or str(val).strip() in ('', 'nan', 'NaT'):
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def _maps(address, city):
    q = urllib.parse.quote(f"{address},{city},CO")
    return f"https://www.google.com/maps/search/?api=1&query={q}"


# ── Unique Owners ─────────────────────────────────────────────────────────────
OWNERS_DATA = [
    # name, phone, contract_status, insurance_status, onboarding, reserve, renewal, monthly_mgmt, notes
    ('Aditya & Karmacharya Shrestha', '(720) 299-0159', 'Signed',             'Pending', 750,  None, 750, None, '6% of rent monthly mgmt fee'),
    ('Sanjaya KC',                    '(402) 853-8857', 'Signed',             'Pending', 1000, None, 1000, None, '7% of rent monthly mgmt fee'),
    ('Arun Basnet Chettry',           '(720) 575-9859', 'Not Started',        'Pending', 0,    0,    500, None, 'Flat $75/mo (9961 Tucson) & $125/mo (10959 Nucla). Waived onboarding fee first time; will charge at renewal. Owner had tenant on Nucla property; onboarding fee never collected.'),
    ('Ashish Pageni',                 '(580) 399-1953', 'Signed',             'Pending', 750,  500,  750, None, '5% of rent monthly mgmt fee'),
    ('Bala Ram Kafley / Sharmila Ghimire', '(720) 629-8108', 'Not Started',   'Pending', 500,  500,  500, None, '5% of rent monthly mgmt fee. Off market property.'),
    ('Bikal Man Gurung',              '(347) 876-6695', 'Sent for Signature', 'Pending', 750,  500,  1000, None, '5% of rent monthly mgmt fee'),
    ('Bir Raut',                      '(407) 607-0291', 'Signed',             'Pending', 500,  500,  500, None, '5% of rent monthly mgmt fee'),
    ('Bishan Raj Shrestha',           '(720) 229-8933', 'Not Started',        'Pending', 300,  0,    750, 100, 'Flat $100/mo mgmt fee. No reserve fee.'),
    ('Ganga Ram Koirala',             '(720) 569-4014', 'Signed',             'Active',  0,    0,    1000, 150, 'Flat $150/mo mgmt fee. No onboarding fee.'),
    ('Jada Amerally',                 '(201) 285-9678', 'Signed',             'Active',  1000, 500,  1000, None, '7% of rent monthly mgmt fee'),
    ('Madhu Khanal',                  '(720) 233-0796', 'Signed',             'Active',  750,  500,  750, None, '7% of rent monthly mgmt fee'),
    ('Meena Sherpa',                  '(720) 935-5986', 'Not Started',        'Pending', 0,    0,    1000, None, '5% of rent monthly mgmt fee. No onboarding, reserve, or agreement dates.'),
    ('Suman Chakrabarti',             '(720) 656-1166', 'Signed',             'Active',  1000, 500,  1000, None, '5% of rent monthly mgmt fee. 2 properties: 14109 Deertrack Lane & 14159 Deertrack Ln.'),
    ('Nawaraj Meraseni',              '(720) 421-7256', 'Not Started',        'Pending', 0,    0,    1000, None, '5% of rent monthly mgmt fee. No onboarding, reserve, or agreement dates.'),
    ('Nita Sharma / Sudesh Sharma',   '(720) 201-0085', 'Not Started',        'Pending', 750,  0,    750, None, '4% of rent monthly mgmt fee. 4 properties. No agreement dates; no reserve fee.'),
    ('Roshan & Yogendra Bishwakarma', '(720) 427-3901', 'Not Started',        'Pending', 500,  500,  500, None, '5% of rent monthly mgmt fee'),
    ('Sandeep Lama',                  '(720) 354-6958', 'Not Started',        'Pending', 0,    0,    1000, 125, 'Flat $125/mo mgmt fee. No onboarding, reserve, or agreement dates.'),
    ('Sandhya Neupane',               '(443) 564-5553', 'Not Started',        'Pending', 0,    0,    1000, None, '5% of rent monthly mgmt fee. No onboarding, reserve, or agreement dates.'),
    ('Sarita Basnet',                 '(303) 889-9837', 'Not Started',        'Active',  0,    0,    1000, 220, 'Flat $220/mo mgmt fee. No onboarding, reserve, or agreement dates.'),
    ('Sharad Ram Bhandary / Sharada Bhandari', '',     'Not Started',        'Active',  1000, None, 1000, None, '5% of rent monthly mgmt fee'),
    ('Siddhartha Sah',                '(720) 810-8396', 'Not Started',        'Pending', 500,  500,  750, None, '5% of rent monthly mgmt fee'),
    ('Dipen Shrestha',                '(720) 878-1156', 'Signed',             'Active',  500,  None, 500, None, '5% of rent monthly mgmt fee'),
    ('Vishwa Adhikari & Asmita Khadka','(251) 643-4781','Not Started',        'Pending', 500,  0,    500, None, '5% of rent monthly mgmt fee. Posted as 9921 Cathay in Zillow.'),
    ('Narayan Chapagain',             '(720) 587-9440', 'Signed',             None,      500,  None, 500, None, '5% of rent monthly mgmt fee'),
    ('Sudeep Pradhan',                '(303) 419-7474', 'Not Started',        'Pending', 1000, None, 1000, None, '5% of rent monthly mgmt fee'),
    ('Anup Adhikari',                 '(857) 251-9874', 'Not Started',        'Active',  1000, None, 1000, None, '5% of rent monthly mgmt fee'),
    ('Santosh Parajuli',              '(970) 714-9127', 'Signed',             'Pending', 500,  None, None, None, '5% of rent monthly mgmt fee'),
    ('Puskar Adhikari',               '(720) 490-8192', 'Not Started',        'Active',  750,  None, 750, None, '5% of rent monthly mgmt fee'),
    ('Sachin Bhandari',               '(218) 790-6393', None,                 'Pending', 1000, None, 1000, None, '4% of rent monthly mgmt fee'),
    ('Prem Bahadur Basnet & Sikha Raut','(303) 335-8219',None,                'Pending', 1000, None, 1000, None, 'Flat $150/mo mgmt fee. Includes pet + solar fee.'),
    ('Satrughan Gautam & Amita Gautam','(720) 850-7655','Signed',             'Active',  1000, None, 1000, 250, '6% of rent monthly mgmt fee'),
    ('Nilkantha Guragain',            '(303) 847-3870', 'Signed',             'Active',  500,  None, 500, None, '4% of rent monthly mgmt fee'),
    ('Niju Shrestha',                 '(205) 568-2018', 'Signed',             'Pending', 750,  None, 750, None, '6% of rent monthly mgmt fee'),
    ('Ashish Dhital',                 '(303) 875-9593', 'Signed',             'Pending', 500,  None, 500, None, '5% of rent monthly mgmt fee'),
    ('Swastika Sapkota',              '(424) 382-5734', 'Signed',             'Active',  500,  None, 500, None, '4% of rent monthly mgmt fee'),
    ('Lachhuman Rana',                '(303) 956-4705', 'Signed',             'Pending', 750,  None, 750, None, '5% of rent monthly mgmt fee'),
    ('Dadhi Ram Dhimal',              '(720) 995-9065', 'Signed',             'Active',  500,  None, 500, None, '5% of rent monthly mgmt fee'),
    ('Pratisara Shakya',              '(763) 670-7998', 'Sent for Signature', 'Pending', 750,  None, 750, None, '6% of rent monthly mgmt fee'),
]

# ── Properties ────────────────────────────────────────────────────────────────
# address, city, prop_type, has_sprinkler, owner_name
PROPERTIES_DATA = [
    ('10957 Olathe St',       'Commerce City', 'Single Family', 'Yes',     'Bir Raut'),
    ('10959 Nucla Court',     'Commerce City', 'Single Family', 'Yes',     'Arun Basnet Chettry'),
    ('1135 Sunrise Dr',       'Erie',          'Single Family', 'Yes',     'Prem Bahadur Basnet & Sikha Raut'),
    ('1219 Atwood St',        'Denver',        'Condo',         'Unknown', 'Pratisara Shakya'),
    ('1293 Loraine Cir S',    'Lafayette',     'Single Family', 'Yes',     'Nita Sharma / Sudesh Sharma'),
    ('1351 S Andes St',       'Aurora',        'Single Family', 'Unknown', 'Dadhi Ram Dhimal'),
    ('13163 Jasmine St',      'Thornton',      'Single Family', 'Yes',     'Sudeep Pradhan'),
    ('13385 Xanthia St',      'Commerce City', 'Single Family', 'Yes',     'Anup Adhikari'),
    ('13717 Del Corso Way',   'Broomfield',    'Townhome',      'Unknown', 'Lachhuman Rana'),
    ('14109 Deertrack Lane',  'Parker',        'Single Family', 'No',      'Suman Chakrabarti'),
    ('14159 Deertrack Ln',    'Parker',        'Single Family', 'No',      'Suman Chakrabarti'),
    ('14166 Madison Way',     'Thornton',      'Single Family', 'No',      'Nita Sharma / Sudesh Sharma'),
    ('16431 E 111th Dr',      'Commerce City', 'Single Family', 'Yes',     'Sharad Ram Bhandary / Sharada Bhandari'),
    ('16551 Peak Way',        'Broomfield',    'Townhome',      'No',      'Nita Sharma / Sudesh Sharma'),
    ('1708 Elis Cir',         'Lafayette',     'Townhome',      'No',      'Sanjaya KC'),
    ('1861 Miranda Road',     'Erie',          'Single Family', 'Yes',     'Sandeep Lama'),
    ('19061 E 99th Pl',       'Commerce City', 'Single Family', 'Unknown', 'Swastika Sapkota'),
    ('20922 E Quincy Pl',     'Aurora',        'Single Family', 'Yes',     'Roshan & Yogendra Bishwakarma'),
    ('2054 E 98th Ave',       'Thornton',      'Single Family', 'Yes',     'Nawaraj Meraseni'),
    ('2281 Buttercup Ln',     'Superior',      'Townhome',      'No',      'Nita Sharma / Sudesh Sharma'),
    ('2301 Frontier St',      'Longmont',      'Single Family', 'Yes',     'Meena Sherpa'),
    ('24564 E Walsh Ave',     'Aurora',        'Single Family', 'Yes',     'Sarita Basnet'),
    ('2512 S Worchester Ct',  'Aurora',        'Townhome',      'No',      'Puskar Adhikari'),
    ('2729 W 167th Pl',       'Broomfield',    'Single Family', 'Yes',     'Sachin Bhandari'),
    ('3412 Eagle Butte Ave',  'Frederick',     'Single Family', 'Unknown', 'Niju Shrestha'),
    ('3565 E 141st Dr',       'Thornton',      'Single Family', 'No',      'Santosh Parajuli'),
    ('3880 Jebel St',         'Commerce City', 'Single Family', 'Yes',     'Bala Ram Kafley / Sharmila Ghimire'),
    ('3960 N Quatar Ct',      'Commerce City', 'Single Family', 'Unknown', None),
    ('4555 Genoa St',         'Denver',        'Single Family', 'Yes',     'Jada Amerally'),
    ('4581 N Quemoy St',      'Commerce City', 'Single Family', 'Yes',     'Bikal Man Gurung'),
    ('4637 Walden Way',       'Lafayette',     'Single Family', 'Yes',     'Ganga Ram Koirala'),
    ('4666 S Malaya Ct',      'Aurora',        'Single Family', 'Yes',     'Siddhartha Sah'),
    ('4720 S Dudley St',      'Littleton',     'Townhome',      'No',      'Dipen Shrestha'),
    ('4839 Halifax Way',      'Broomfield',    'Single Family', 'No',      'Narayan Chapagain'),
    ('4884 S Liverpool Ct',   'Aurora',        'Single Family', 'No',      'Satrughan Gautam & Amita Gautam'),
    ('6013 Granite Ct',       'Frederick',     'Single Family', 'Yes',     'Bishan Raj Shrestha'),
    ('784 Gold Hill Dr',      'Erie',          'Single Family', 'Yes',     'Sandhya Neupane'),
    ('8482 Golden Eye Dr',    'Parker',        'Single Family', 'Yes',     'Nilkantha Guragain'),
    ('833 Vixen Dr',          'Fort Collins',  'Single Family', 'Yes',     'Aditya & Karmacharya Shrestha'),
    ('9323 Biscay St',        'Commerce City', 'Single Family', 'Yes',     'Madhu Khanal'),
    ('9876 Ceylon Ct',        'Commerce City', 'Single Family', 'Yes',     'Vishwa Adhikari & Asmita Khadka'),
    ('9922 Cathay St',        'Commerce City', 'Single Family', 'Yes',     'Ashish Pageni'),
    ('9961 Tucson St',        'Commerce City', 'Single Family', 'Yes',     'Arun Basnet Chettry'),
    ('12415 E 101st Dr',      'Commerce City', 'Single Family', 'Unknown', 'Ashish Dhital'),
]

# ── Occupancy ─────────────────────────────────────────────────────────────────
# address, status, rent, deposit, pet_dep, lease_start, lease_end, renters_ins, notes
OCCUPANCY_DATA = [
    ('10957 Olathe St',      'Occupied',        3450, 3450,   0,    '2025-07-01', '2026-06-30', None,       None),
    ('1708 Elis Cir',        'Occupied',        2695, 4042.5, 0,    '2026-03-29', '2027-03-31', 'Active',   'Tenant moved in 3/29/2026. Pending move-in at time of data entry.'),
    ('1861 Miranda Road',    'Occupied',        3950, 3800,   0,    '2025-03-01', '2026-02-28', 'Active',   None),
    ('2054 E 98th Ave',      'Occupied',        3100, 3000,   None, '2025-01-01', '2027-02-28', None,       'Owner holds deposit'),
    ('2301 Frontier St',     'Occupied',        2950, 2850,   None, '2025-10-01', '2026-09-30', None,       'Owner holds deposit'),
    ('24564 E Walsh Ave',    'Occupied',        3400, 3350,   None, '2025-10-01', '2026-09-30', 'Active',   'Lease expired — tenant remained. Owner holds deposit'),
    ('4555 Genoa St',        'Occupied',        2500, 2500,   None, '2025-05-02', '2026-07-31', None,       None),
    ('784 Gold Hill Dr',     'Occupied',        3300, None,   None, '2025-10-01', '2027-09-30', 'Active',   'Owner holds deposit ($3,200)'),
    ('9323 Biscay St',       'Occupied',        3150, 3150,   250,  '2025-10-01', '2026-09-30', 'Active',   None),
    ('9922 Cathay St',       'Occupied',        3325, 3500,   None, '2025-04-05', '2026-04-30', None,       None),
    ('9961 Tucson St',       'Occupied',        3400, 3350,   None, '2025-03-01', '2027-02-28', None,       None),
    ('833 Vixen Dr',         'Occupied',        2900, 2500,   400,  '2025-07-01', '2026-06-30', None,       None),
    ('10959 Nucla Court',    'Occupied',        3600, 0,      None, '2025-06-01', '2026-05-31', None,       'Owner holds deposit'),
    ('9876 Ceylon Ct',       'Occupied',        2850, 2850,   250,  '2025-10-01', '2027-09-30', None,       'Posted as 9921 Cathay in Zillow'),
    ('6013 Granite Ct',      'Occupied',        2575, 2575,   None, '2025-08-01', '2027-07-31', 'Active',   None),
    ('3880 Jebel St',        'Maintenance',     3000, None,   None, None,         None,         None,       'Off market'),
    ('4581 N Quemoy St',     'Occupied',        3100, None,   None, '2025-07-18', '2026-07-17', None,       None),
    ('14166 Madison Way',    'Occupied',        3100, 3100,   400,  '2025-07-16', '2026-07-31', None,       None),
    ('1293 Loraine Cir S',   'Occupied',        3595, 3595,   None, None,         None,         None,       None),
    ('4666 S Malaya Ct',     'Occupied',        3300, 3300,   None, '2025-09-03', '2026-09-02', None,       None),
    ('16551 Peak Way',       'Occupied',        2835, 2800,   None, '2025-10-05', '2028-10-04', None,       None),
    ('4720 S Dudley St',     'Occupied',        2350, 2300,   300,  '2025-11-03', '2026-10-31', 'Active',   None),
    ('2281 Buttercup Ln',    'Occupied',        3030, 2995,   250,  '2025-12-15', '2027-06-30', 'Active',   None),
    ('4637 Walden Way',      'Occupied',        3700, 3900,   None, '2025-07-29', '2026-07-31', None,       None),
    ('2729 W 167th Pl',      'Occupied',        2500, 2500,   None, '2025-12-19', '2027-06-30', None,       None),
    ('20922 E Quincy Pl',    'Occupied',        3000, 3000,   None, '2025-11-12', '2026-10-31', None,       None),
    ('16431 E 111th Dr',     'Occupied',        3175, 3100,   500,  '2025-11-15', '2026-10-31', 'Active',   None),
    ('4839 Halifax Way',     'Occupied',        2700, 5400,   None, '2026-03-01', '2027-02-28', 'Active',   None),
    ('13163 Jasmine St',     'Occupied',        2820, 2750,   500,  '2026-03-01', '2028-02-29', 'Active',   None),
    ('13385 Xanthia St',     'Occupied',        3135, 3100,   250,  '2025-12-27', '2028-06-30', None,       None),
    ('3565 E 141st Dr',      'Occupied',        2550, 2500,   500,  '2026-02-01', '2027-08-31', 'Active',   None),
    ('2512 S Worchester Ct', 'Occupied',        2395, 3600,   None, '2026-03-14', '2027-03-31', 'Active',   None),
    ('1135 Sunrise Dr',      'Occupied',        4155, 3995,   750,  '2025-12-10', '2027-06-30', 'Active',   'Includes pet + solar fee'),
    ('3960 N Quatar Ct',     'Maintenance',     None, None,   None, None,         None,         None,       'Off market'),
    ('14109 Deertrack Lane', 'Occupied',        2800, 2800,   None, '2025-07-18', '2025-07-31', 'Active',   None),
    ('4884 S Liverpool Ct',  'Occupied',        2550, 2550,   None, '2026-01-17', '2027-01-31', 'Active',   None),
    ('14159 Deertrack Ln',   'Occupied',        2750, 2750,   None, None,         None,         None,       None),
    ('8482 Golden Eye Dr',   'Occupied',        2795, 5000,   None, '2026-03-01', '2027-02-28', 'Active',   None),
    ('13717 Del Corso Way',  'Occupied',        2800, 2800,   None, '2026-04-01', '2027-09-30', 'Active',   None),
    ('19061 E 99th Pl',      'Occupied',        3300, 3300,   None, '2026-03-15', '2027-03-31', 'Active',   None),
    ('12415 E 101st Dr',     'Occupied',        3070, 3495,   None, '2026-04-27', '2027-04-30', 'Active',   None),
    ('1219 Atwood St',       'Vacant',          None, None,   None, None,         None,         None,       'Vacant — listed for rent'),
    ('1351 S Andes St',      'Occupied',        2420, 2420,   0,    None,         None,         None,       None),
    ('3412 Eagle Butte Ave', 'Occupied',        3295, None,   None, '2026-05-22', '2027-05-31', None,       None),
]


def seed_if_empty():
    if Property.query.count() > 0:
        return

    print('🌱 Seeding real EverRest data...')

    # ── Build owners ──────────────────────────────────────────────────────────
    owner_map = {}  # name → Owner instance
    for row in OWNERS_DATA:
        name, phone, contract, insurance, onboard, reserve, renewal, mgmt, notes = row
        o = Owner(
            name=name,
            phone=phone or '',
            contract_status=contract or 'Not Started',
            landlord_insurance_status=insurance or 'N/A',
            onboarding_fee=onboard,
            reserve_fee=reserve,
            renewal_fee=renewal,
            monthly_mgmt_fee=mgmt,
            notes=notes or '',
        )
        db.session.add(o)
        owner_map[name] = o
    db.session.flush()

    # ── Build properties + sprinkler + occupancy ──────────────────────────────
    prop_map = {}  # address → Property instance
    for row in PROPERTIES_DATA:
        addr, city, ptype, has_spr, owner_name = row
        p = Property(
            address=addr,
            city=city,
            state='CO',
            property_type=ptype,
            google_maps_url=_maps(addr, city),
        )
        db.session.add(p)
        db.session.flush()
        prop_map[addr] = p

        # Link owner
        if owner_name and owner_name in owner_map:
            db.session.add(PropertyOwner(property_id=p.id, owner_id=owner_map[owner_name].id))

        # Sprinkler record (basic — blowout details added separately)
        spr = Sprinkler(
            property_id=p.id,
            has_sprinkler=has_spr,
            repair_needed='No',
            repair_status='N/A',
        )
        db.session.add(spr)

    db.session.flush()

    # ── Occupancy ─────────────────────────────────────────────────────────────
    occ_map = {}
    for row in OCCUPANCY_DATA:
        addr, status, rent, deposit, pet_dep, ls, le, renters, notes = row
        p = prop_map.get(addr)
        if not p:
            continue
        occ = Occupancy(
            property_id=p.id,
            status=status,
            rent_amount=rent,
            security_deposit=deposit,
            lease_start=_d(ls),
            lease_end=_d(le),
            notes=notes or '',
        )
        db.session.add(occ)
        occ_map[addr] = occ

    # Properties that don't have an occupancy entry yet get a blank one
    for addr, p in prop_map.items():
        if addr not in occ_map:
            db.session.add(Occupancy(property_id=p.id, status='Vacant'))

    db.session.flush()

    # ── Work Orders ───────────────────────────────────────────────────────────
    wo1 = WorkOrder(
        wo_number='WO-2026-001',
        property_id=prop_map['10957 Olathe St'].id,
        owner_id=owner_map['Bir Raut'].id,
        date_submitted=date(2026, 5, 1),
        category='Carpet Cleaning',
        description='Replace carpet in master bedroom after tenant move-out.',
        priority='High',
        vendor_name='CleanPro Services',
        vendor_phone='(720) 555-0101',
        target_completion=date(2026, 5, 15),
        status='In Progress',
        estimated_cost=850.00,
        invoice_status='Pending',
        source='Manual',
    )
    wo2 = WorkOrder(
        wo_number='WO-2026-002',
        property_id=prop_map['1708 Elis Cir'].id,
        owner_id=owner_map['Sanjaya KC'].id,
        date_submitted=date(2026, 5, 3),
        category='Carpet Cleaning',
        description='Steam cleaning before new tenant move-in.',
        priority='Medium',
        vendor_name='CleanPro Services',
        vendor_phone='(720) 555-0101',
        date_assigned=date(2026, 5, 10),
        target_completion=date(2026, 5, 15),
        status='Completed',
        date_completed=date(2026, 5, 15),
        estimated_cost=250.00,
        actual_cost=250.00,
        invoice_number='INV-CP-2026-044',
        invoice_status='Received',
        source='Manual',
    )
    wo3 = WorkOrder(
        wo_number='WO-2026-003',
        property_id=prop_map['1861 Miranda Road'].id,
        owner_id=owner_map['Sandeep Lama'].id,
        date_submitted=date(2026, 5, 5),
        category='Electrical',
        description='Replace outdoor light fixtures — 3 units.',
        priority='Low',
        vendor_name='Bright Electric LLC',
        vendor_phone='(720) 555-0202',
        target_completion=date(2026, 5, 25),
        status='Open',
        estimated_cost=320.00,
        invoice_status='Pending',
        source='Manual',
    )
    db.session.add_all([wo1, wo2, wo3])
    db.session.flush()

    # ── Inspections ───────────────────────────────────────────────────────────
    db.session.add_all([
        Inspection(
            property_id=prop_map['1708 Elis Cir'].id,
            inspection_type='Move-In',
            inspection_date=date(2026, 3, 29),
            inspector_name='Mohan Shrestha',
            tenant_present='No',
            overall_condition='Good',
            status='Passed',
            kitchen_rating='Good',
            bathrooms_rating='Good',
            bedrooms_rating='Good',
            living_areas_rating='Good',
            basement_rating='N/A',
            exterior_rating='Good',
            garage_rating='N/A',
            hvac_rating='Good',
            plumbing_rating='Good',
            issues_found='No',
            photos_taken='Yes',
            report_sent='Yes',
            report_sent_date=date(2026, 3, 29),
            follow_up_required='No',
            notes='Property clean and ready. Tenant moving in 3/29. Tenant notified.',
        ),
        Inspection(
            property_id=prop_map['10957 Olathe St'].id,
            inspection_type='Routine',
            inspection_date=date(2026, 5, 1),
            inspector_name='Mohan Shrestha',
            tenant_present='Yes',
            overall_condition='Fair',
            status='Conditional Pass',
            kitchen_rating='Fair',
            bathrooms_rating='Good',
            bedrooms_rating='Fair',
            living_areas_rating='Good',
            basement_rating='N/A',
            exterior_rating='Good',
            garage_rating='N/A',
            hvac_rating='Good',
            plumbing_rating='Good',
            issues_found='Yes',
            issue_details='Carpet wear in master bedroom noted. Kitchen faucet dripping. Roof & gutters fair condition.',
            photos_taken='Yes',
            report_sent='Yes',
            report_sent_date=date(2026, 5, 1),
            follow_up_required='Yes',
            follow_up_notes='Work order raised for carpet and faucet. Follow-up by 5/15/2026.',
            notes='Tenant notified. WO-2026-001 created.',
        ),
        Inspection(
            property_id=prop_map['2054 E 98th Ave'].id,
            inspection_type='Routine',
            inspection_date=date(2026, 5, 7),
            inspector_name='Mohan Shrestha',
            tenant_present='Yes',
            overall_condition='Good',
            status='Passed',
            kitchen_rating='Good',
            bathrooms_rating='Good',
            bedrooms_rating='Good',
            living_areas_rating='Good',
            basement_rating='N/A',
            exterior_rating='Good',
            garage_rating='N/A',
            hvac_rating='Good',
            plumbing_rating='Good',
            issues_found='No',
            photos_taken='Yes',
            report_sent='Yes',
            report_sent_date=date(2026, 5, 7),
            follow_up_required='No',
            notes='No issues found. Property well maintained. Tenant notified.',
        ),
    ])

    db.session.commit()
    print(f'✅ Seeded {len(PROPERTIES_DATA)} properties, {len(OWNERS_DATA)} owners, 3 work orders, 3 inspections.')
