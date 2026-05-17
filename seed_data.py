from models import db, Property, Owner, PropertyOwner, Occupancy, Sprinkler, WorkOrder, Inspection
from datetime import date, timedelta


def seed_if_empty():
    if Property.query.count() > 0:
        return

    # --- Owners ---
    o1 = Owner(
        name='Robert & Linda Harmon',
        phone='720-555-0101',
        email='rharmon@email.com',
        emergency_contact='Linda Harmon',
        emergency_phone='720-555-0102',
        onboarding_fee=500.00,
        reserve_fee=250.00,
        renewal_fee=150.00,
        monthly_mgmt_fee=125.00,
        contract_status='Signed',
        landlord_insurance_status='Active',
        landlord_insurance_expiry=date(2026, 3, 15),
        notes='Prefers email communication. Long-time client since 2019.'
    )
    o2 = Owner(
        name='Marcus Delgado',
        phone='303-555-0210',
        email='mdelgado@gmail.com',
        emergency_contact='Sofia Delgado',
        emergency_phone='303-555-0211',
        onboarding_fee=500.00,
        reserve_fee=250.00,
        renewal_fee=150.00,
        monthly_mgmt_fee=110.00,
        contract_status='Signed',
        landlord_insurance_status='Active',
        landlord_insurance_expiry=date(2025, 11, 30),
        notes='Out of state investor. Prefers monthly summary email.'
    )
    o3 = Owner(
        name='Priya Nair',
        phone='720-555-0330',
        email='pnair@outlook.com',
        emergency_contact='',
        emergency_phone='',
        onboarding_fee=500.00,
        reserve_fee=250.00,
        renewal_fee=150.00,
        monthly_mgmt_fee=125.00,
        contract_status='Sent for Signature',
        landlord_insurance_status='Pending',
        landlord_insurance_expiry=None,
        notes='New client. Contract pending signature.'
    )
    db.session.add_all([o1, o2, o3])
    db.session.flush()

    # --- Properties ---
    p1 = Property(
        address='4821 Cedarwood Lane',
        city='Loveland',
        state='CO',
        zip='80537',
        property_type='Single Family',
    )
    p2 = Property(
        address='1123 Maple Ridge Dr',
        city='Fort Collins',
        state='CO',
        zip='80525',
        property_type='Townhome',
    )
    p3 = Property(
        address='712 Summit View Ct',
        city='Longmont',
        state='CO',
        zip='80501',
        property_type='Single Family',
    )
    db.session.add_all([p1, p2, p3])
    db.session.flush()

    # Set Google Maps URLs
    for p in [p1, p2, p3]:
        p.google_maps_url = p.generate_maps_url()

    # --- Property Owners ---
    db.session.add_all([
        PropertyOwner(property_id=p1.id, owner_id=o1.id),
        PropertyOwner(property_id=p2.id, owner_id=o2.id),
        PropertyOwner(property_id=p3.id, owner_id=o3.id),
    ])

    # --- Occupancy ---
    db.session.add_all([
        Occupancy(
            property_id=p1.id,
            status='Occupied',
            tenant_name='Jake & Megan Sorenson',
            tenant_phone='970-555-0401',
            tenant_email='jsorenson@email.com',
            rent_amount=2100.00,
            security_deposit=2100.00,
            lease_start=date(2024, 9, 1),
            lease_end=date(2025, 8, 31),
            notes='Good tenants. On-time payment history.'
        ),
        Occupancy(
            property_id=p2.id,
            status='Notice Given',
            tenant_name='Amy Chen',
            tenant_phone='970-555-0502',
            tenant_email='amychen@gmail.com',
            rent_amount=1750.00,
            security_deposit=1750.00,
            lease_start=date(2024, 3, 1),
            lease_end=date(2025, 5, 31),
            notes='Tenant gave 30-day notice on Apr 15. Schedule move-out inspection.'
        ),
        Occupancy(
            property_id=p3.id,
            status='Vacant',
            tenant_name='',
            tenant_phone='',
            tenant_email='',
            rent_amount=1950.00,
            security_deposit=1950.00,
            lease_start=None,
            lease_end=None,
            notes='Recently vacated. Cleaning and carpet cleaning scheduled.'
        ),
    ])

    # --- Sprinkler ---
    db.session.add_all([
        Sprinkler(
            property_id=p1.id,
            has_sprinkler='Yes',
            controller_brand='Rain Bird',
            controller_model='ST8I-WIFI',
            control_method='Both App & Panel',
            shutoff_valve_location='Basement – Near Water Main',
            fall_blowout_status='Completed',
            fall_blowout_date=date(2024, 10, 12),
            blowout_vendor='Front Range Sprinkler Co.',
            spring_turnon_status='Active',
            spring_turnon_date=date(2025, 4, 20),
            system_working='Yes',
            backflow_valve_status='OK',
            repair_needed='No',
            repair_status='N/A',
        ),
        Sprinkler(
            property_id=p2.id,
            has_sprinkler='Yes',
            controller_brand='Hunter',
            controller_model='Pro-C',
            control_method='Physical Panel Only',
            shutoff_valve_location='Garage',
            fall_blowout_status='Completed',
            fall_blowout_date=date(2024, 10, 5),
            blowout_vendor='Aqua Systems LLC',
            spring_turnon_status='Turned On',
            spring_turnon_date=date(2025, 4, 28),
            system_working='Partially Working',
            backflow_valve_status='Not Tested',
            issue_details='Zone 3 head is stuck open. Needs replacement.',
            repair_needed='Yes',
            repair_status='Scheduled',
            repair_vendor='Aqua Systems LLC',
            repair_cost=185.00,
        ),
        Sprinkler(
            property_id=p3.id,
            has_sprinkler='No',
            repair_needed='No',
            repair_status='N/A',
        ),
    ])
    db.session.flush()

    # --- Work Orders ---
    wo1 = WorkOrder(
        wo_number='WO-2025-001',
        property_id=p1.id,
        owner_id=o1.id,
        date_submitted=date(2025, 4, 10),
        category='Plumbing',
        description='Kitchen faucet leaking under sink. Tenant reported slow drip that has worsened.',
        priority='Medium',
        vendor_name='Peak Plumbing Services',
        vendor_phone='970-555-0601',
        date_assigned=date(2025, 4, 12),
        target_completion=date(2025, 4, 20),
        status='Completed',
        date_completed=date(2025, 4, 18),
        estimated_cost=150.00,
        actual_cost=175.00,
        invoice_number='INV-PP-4482',
        invoice_status='Received',
        notes='Replaced faucet cartridge and supply lines.',
        source='Manual',
    )
    wo2 = WorkOrder(
        wo_number='WO-2025-002',
        property_id=p2.id,
        owner_id=o2.id,
        date_submitted=date(2025, 5, 1),
        category='Sprinkler Repair',
        description='Zone 3 head stuck open — needs replacement. Auto-created from sprinkler record.',
        priority='High',
        vendor_name='Aqua Systems LLC',
        vendor_phone='970-555-0710',
        date_assigned=date(2025, 5, 3),
        target_completion=date(2025, 5, 15),
        status='Assigned',
        estimated_cost=185.00,
        actual_cost=None,
        invoice_status='N/A',
        source='Sprinkler',
    )
    wo3 = WorkOrder(
        wo_number='WO-2025-003',
        property_id=p3.id,
        owner_id=o3.id,
        date_submitted=date(2025, 5, 5),
        category='Carpet Cleaning',
        description='Full carpet cleaning needed after vacancy. All bedrooms and living room.',
        priority='Medium',
        vendor_name='Colorado Clean Team',
        vendor_phone='303-555-0801',
        date_assigned=date(2025, 5, 8),
        target_completion=date(2025, 5, 14),
        status='In Progress',
        estimated_cost=350.00,
        invoice_status='Pending',
        source='Manual',
    )
    db.session.add_all([wo1, wo2, wo3])
    db.session.flush()

    # Link sprinkler WO
    spr2 = Sprinkler.query.filter_by(property_id=p2.id).first()
    if spr2:
        spr2.linked_wo_id = wo2.id

    # --- Inspections ---
    db.session.add_all([
        Inspection(
            property_id=p1.id,
            inspection_type='Routine',
            inspection_date=date(2025, 3, 15),
            inspector_name='Dana Ellis',
            tenant_present='Yes',
            overall_condition='Good',
            status='Passed',
            kitchen_rating='Good',
            bathrooms_rating='Good',
            bedrooms_rating='Excellent',
            living_areas_rating='Good',
            basement_rating='N/A',
            exterior_rating='Good',
            garage_rating='Fair',
            hvac_rating='Good',
            plumbing_rating='Good',
            issues_found='No',
            photos_taken='Yes',
            report_sent='Yes',
            report_sent_date=date(2025, 3, 16),
            follow_up_required='No',
        ),
        Inspection(
            property_id=p2.id,
            inspection_type='Move-Out',
            inspection_date=date(2025, 5, 31),
            inspector_name='Dana Ellis',
            tenant_present='Yes',
            overall_condition='Fair',
            status='Pending Review',
            kitchen_rating='Fair',
            bathrooms_rating='Poor',
            bedrooms_rating='Fair',
            living_areas_rating='Good',
            basement_rating='N/A',
            exterior_rating='Good',
            garage_rating='N/A',
            hvac_rating='Good',
            plumbing_rating='Fair',
            issues_found='Yes',
            issue_details='Bathroom grout needs re-caulking. Scuff marks on bedroom walls.',
            photos_taken='Yes',
            report_sent='No',
            follow_up_required='Yes',
            follow_up_notes='Get repair estimates before releasing deposit.',
        ),
    ])

    db.session.commit()
    print('✅ Sample data seeded successfully.')
