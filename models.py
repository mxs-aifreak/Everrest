from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Property(db.Model):
    __tablename__ = 'properties'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), default='CO')
    zip = db.Column(db.String(10))
    property_type = db.Column(db.String(50))
    google_maps_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    property_owners = db.relationship('PropertyOwner', backref='property', lazy=True, cascade='all, delete-orphan')
    occupancy = db.relationship('Occupancy', backref='property', lazy=True, uselist=False, cascade='all, delete-orphan')
    sprinkler = db.relationship('Sprinkler', backref='property', lazy=True, uselist=False, cascade='all, delete-orphan')
    work_orders = db.relationship('WorkOrder', backref='property', lazy=True)
    inspections = db.relationship('Inspection', backref='property', lazy=True)

    @property
    def owners(self):
        return [po.owner for po in self.property_owners]

    @property
    def primary_owner(self):
        if self.property_owners:
            return self.property_owners[0].owner
        return None

    def generate_maps_url(self):
        addr = f"{self.address},{self.city},CO"
        import urllib.parse
        return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(addr)}"


class Owner(db.Model):
    __tablename__ = 'owners'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(200))
    emergency_contact = db.Column(db.String(200))
    emergency_phone = db.Column(db.String(20))
    onboarding_fee = db.Column(db.Numeric(10, 2))
    reserve_fee = db.Column(db.Numeric(10, 2))
    renewal_fee = db.Column(db.Numeric(10, 2))
    monthly_mgmt_fee = db.Column(db.Numeric(10, 2))
    contract_status = db.Column(db.String(50), default='Not Started')
    landlord_insurance_status = db.Column(db.String(50), default='N/A')
    landlord_insurance_expiry = db.Column(db.Date)
    notes = db.Column(db.Text)

    property_owners = db.relationship('PropertyOwner', backref='owner', lazy=True)
    work_orders = db.relationship('WorkOrder', backref='owner', lazy=True)

    @property
    def properties(self):
        return [po.property for po in self.property_owners]


class PropertyOwner(db.Model):
    __tablename__ = 'property_owners'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)


class Occupancy(db.Model):
    __tablename__ = 'occupancy'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(50), default='Vacant')
    tenant_name = db.Column(db.String(200))
    tenant_phone = db.Column(db.String(20))
    tenant_email = db.Column(db.String(200))
    rent_amount = db.Column(db.Numeric(10, 2))
    security_deposit = db.Column(db.Numeric(10, 2))
    lease_start = db.Column(db.Date)
    lease_end = db.Column(db.Date)
    notes = db.Column(db.Text)


class Sprinkler(db.Model):
    __tablename__ = 'sprinkler'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    has_sprinkler = db.Column(db.String(10), default='Unknown')
    controller_brand = db.Column(db.String(100))
    controller_model = db.Column(db.String(100))
    control_method = db.Column(db.String(100))
    shutoff_valve_location = db.Column(db.String(200))
    fall_blowout_status = db.Column(db.String(50), default='Pending')
    fall_blowout_date = db.Column(db.Date)
    blowout_vendor = db.Column(db.String(200))
    spring_turnon_status = db.Column(db.String(50), default='Pending')
    spring_turnon_date = db.Column(db.Date)
    system_working = db.Column(db.String(30))
    backflow_valve_status = db.Column(db.String(50))
    issue_details = db.Column(db.Text)
    repair_needed = db.Column(db.String(5))
    repair_status = db.Column(db.String(50), default='N/A')
    repair_date = db.Column(db.Date)
    repair_vendor = db.Column(db.String(200))
    repair_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    linked_wo_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), nullable=True)

    linked_wo = db.relationship('WorkOrder', foreign_keys=[linked_wo_id])


class WorkOrder(db.Model):
    __tablename__ = 'work_orders'
    id = db.Column(db.Integer, primary_key=True)
    wo_number = db.Column(db.String(20), unique=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'))
    date_submitted = db.Column(db.Date, default=datetime.utcnow)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='Medium')
    vendor_name = db.Column(db.String(200))
    vendor_phone = db.Column(db.String(20))
    date_assigned = db.Column(db.Date)
    target_completion = db.Column(db.Date)
    status = db.Column(db.String(50), default='Open')
    date_completed = db.Column(db.Date)
    estimated_cost = db.Column(db.Numeric(10, 2))
    actual_cost = db.Column(db.Numeric(10, 2))
    invoice_number = db.Column(db.String(100))
    invoice_status = db.Column(db.String(50), default='N/A')
    notes = db.Column(db.Text)
    source = db.Column(db.String(20), default='Manual')


class Insurance(db.Model):
    __tablename__ = 'insurance'
    id = db.Column(db.Integer, primary_key=True)
    insurance_type = db.Column(db.String(20), nullable=False)  # 'Renters' or 'Landlord'
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=True)  # Landlord only
    provider = db.Column(db.String(200))
    policy_number = db.Column(db.String(100))
    coverage_amount = db.Column(db.Numeric(12, 2))
    annual_premium = db.Column(db.Numeric(10, 2))
    effective_date = db.Column(db.Date)
    expiration_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pending')
    date_received = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    property = db.relationship('Property', backref=db.backref('insurance_policies', lazy=True))
    owner = db.relationship('Owner', backref=db.backref('insurance_policies', lazy=True))


class Inspection(db.Model):
    __tablename__ = 'inspections'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    inspection_type = db.Column(db.String(100))
    inspection_date = db.Column(db.Date)
    inspector_name = db.Column(db.String(200))
    tenant_present = db.Column(db.String(5))
    overall_condition = db.Column(db.String(100))
    status = db.Column(db.String(50))
    kitchen_rating = db.Column(db.String(20))
    bathrooms_rating = db.Column(db.String(20))
    bedrooms_rating = db.Column(db.String(20))
    living_areas_rating = db.Column(db.String(20))
    basement_rating = db.Column(db.String(20))
    exterior_rating = db.Column(db.String(20))
    garage_rating = db.Column(db.String(20))
    hvac_rating = db.Column(db.String(20))
    plumbing_rating = db.Column(db.String(20))
    issues_found = db.Column(db.String(5))
    issue_details = db.Column(db.Text)
    photos_taken = db.Column(db.String(5))
    report_sent = db.Column(db.String(5))
    report_sent_date = db.Column(db.Date)
    follow_up_required = db.Column(db.String(5))
    follow_up_notes = db.Column(db.Text)
    notes = db.Column(db.Text)
