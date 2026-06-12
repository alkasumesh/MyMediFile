from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)  # Male, Female, Other
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    health_profile = db.relationship('HealthProfile', backref='user', uselist=False, cascade="all, delete-orphan", foreign_keys="[HealthProfile.user_id]")
    medical_records = db.relationship('MedicalRecord', backref='user', lazy=True, cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', backref='user', lazy=True, cascade="all, delete-orphan")
    menstrual_cycles = db.relationship('MenstrualCycle', backref='user', lazy=True, cascade="all, delete-orphan")
    vaccinations = db.relationship('Vaccination', backref='user', lazy=True, cascade="all, delete-orphan")
    health_metrics = db.relationship('HealthMetric', backref='user', lazy=True, cascade="all, delete-orphan")
    family_members = db.relationship('FamilyMember', backref='user', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class FamilyMember(db.Model):
    __tablename__ = 'family_members'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)  # Spouse, Child, Parent, Sibling, Other
    age = db.Column(db.Integer, nullable=False)
    blood_group = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    health_profile = db.relationship('HealthProfile', backref='family_member', uselist=False, cascade="all, delete-orphan", foreign_keys="[HealthProfile.family_member_id]")
    medical_records = db.relationship('MedicalRecord', backref='family_member', lazy=True, cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', backref='family_member', lazy=True, cascade="all, delete-orphan")
    vaccinations = db.relationship('Vaccination', backref='family_member', lazy=True, cascade="all, delete-orphan")
    health_metrics = db.relationship('HealthMetric', backref='family_member', lazy=True, cascade="all, delete-orphan")


class HealthProfile(db.Model):
    __tablename__ = 'health_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id', ondelete='CASCADE'), nullable=True)
    
    blood_group = db.Column(db.String(10), nullable=False)
    height = db.Column(db.Float, nullable=False)  # in cm
    weight = db.Column(db.Float, nullable=False)  # in kg
    allergies = db.Column(db.Text, nullable=True)
    chronic_diseases = db.Column(db.Text, nullable=True)
    current_medications = db.Column(db.Text, nullable=True)
    
    # Emergency Details
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    family_doctor_name = db.Column(db.String(100), nullable=True)
    family_doctor_phone = db.Column(db.String(20), nullable=True)
    insurance_provider = db.Column(db.String(100), nullable=True)
    insurance_policy_number = db.Column(db.String(50), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def bmi(self):
        if self.height and self.weight:
            height_m = self.height / 100.0
            return round(self.weight / (height_m * height_m), 1)
        return 0.0

    @property
    def bmi_category(self):
        val = self.bmi
        if val == 0.0:
            return "N/A"
        if val < 18.5:
            return "Underweight"
        elif val < 25.0:
            return "Normal"
        elif val < 30.0:
            return "Overweight"
        else:
            return "Obese"


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id', ondelete='CASCADE'), nullable=True)
    
    title = db.Column(db.String(150), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=True)
    hospital_name = db.Column(db.String(100), nullable=True)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Blood Test, Prescription, Scan, Vaccination, Surgery, Allergy Report, Others
    file_path = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id', ondelete='CASCADE'), nullable=True)
    
    doctor_name = db.Column(db.String(100), nullable=False)
    hospital_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MenstrualCycle(db.Model):
    __tablename__ = 'menstrual_cycles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    last_period_date = db.Column(db.Date, nullable=False)
    average_cycle_length = db.Column(db.Integer, nullable=False, default=28)
    period_duration = db.Column(db.Integer, nullable=False, default=5)
    
    # Symptom checklist
    cramps = db.Column(db.Boolean, default=False)
    headache = db.Column(db.Boolean, default=False)
    mood_swings = db.Column(db.Boolean, default=False)
    fatigue = db.Column(db.Boolean, default=False)
    back_pain = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Vaccination(db.Model):
    __tablename__ = 'vaccinations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id', ondelete='CASCADE'), nullable=True)
    
    vaccine_name = db.Column(db.String(100), nullable=False)
    date_taken = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date, nullable=True)
    hospital_clinic_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class HealthMetric(db.Model):
    __tablename__ = 'health_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id', ondelete='CASCADE'), nullable=True)
    
    systolic = db.Column(db.Integer, nullable=True)  # Blood Pressure Systolic (mmHg)
    diastolic = db.Column(db.Integer, nullable=True)  # Blood Pressure Diastolic (mmHg)
    blood_sugar = db.Column(db.Float, nullable=True)  # Blood Sugar (mg/dL)
    heart_rate = db.Column(db.Integer, nullable=True)  # Heart Rate (bpm)
    oxygen_level = db.Column(db.Integer, nullable=True)  # SpO2 (%)
    body_temperature = db.Column(db.Float, nullable=True)  # Temp (F or C)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
