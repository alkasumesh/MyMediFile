import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, HealthProfile, MedicalRecord, Appointment, MenstrualCycle, Vaccination, HealthMetric, FamilyMember, Notification

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Sync dropdowns & alerts inside request pipeline
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)
        if g.user is None:
            session.clear()
            return
            
        # Refresh dynamic session info for base template widgets
        session['user_name'] = g.user.full_name
        session['user_gender'] = g.user.gender
        
        # Load family members for profile switcher
        members = FamilyMember.query.filter_by(user_id=user_id).all()
        session['family_members_list'] = [{'id': m.id, 'name': m.name, 'relationship': m.relationship} for m in members]
        
        # Unread notifications count
        session['unread_notifications_count'] = Notification.query.filter_by(user_id=user_id, is_read=False).count()

# --- PUBLIC ROUTING ---

@app.route('/')
def landing():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # In a real app, send mail or record in database
        flash('Thank you! Your message was submitted securely. Our clinical support team will review it shortly.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

# --- AUTHENTICATION ROUTING ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email').lower().strip()
        phone_number = request.form.get('phone_number')
        dob_str = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
            
        # Check if email exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
            
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date of birth format.', 'error')
            return redirect(url_for('register'))
            
        # Create User
        new_user = User(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            date_of_birth=dob,
            gender=gender
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Initialize default empty health profile for user
        profile = HealthProfile(
            user_id=new_user.id,
            blood_group='O+',
            height=0.0,
            weight=0.0,
            allergies='',
            chronic_diseases='',
            current_medications=''
        )
        db.session.add(profile)
        
        # Send welcome notification
        welcome_notif = Notification(
            user_id=new_user.id,
            title='Account Setup Completed',
            message=f'Welcome {full_name} to MyMediFile! Keep your health profile, records, and vitals updated to monitor your wellness progress.'
        )
        db.session.add(welcome_notif)
        db.session.commit()
        
        flash('Profile registered successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['user_gender'] = user.gender
            
            # Reset active switched profiles to Primary user by default
            session['active_profile_id'] = None
            session['active_profile_name'] = None
            
            flash(f'Logged in successfully. Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
            
        flash('Invalid email address or password.', 'error')
        return redirect(url_for('login'))
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('landing'))

# --- PROFILE SWITCHER API ---

@app.route('/switch-profile', methods=['POST'])
def switch_profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    profile_target = request.form.get('profile_id')
    
    if profile_target == 'me':
        session['active_profile_id'] = None
        session['active_profile_name'] = None
        flash('Switched context to Primary Profile.', 'info')
    else:
        try:
            member_id = int(profile_target)
            member = FamilyMember.query.filter_by(id=member_id, user_id=session['user_id']).first()
            if member:
                session['active_profile_id'] = member.id
                session['active_profile_name'] = member.name
                flash(f"Switched context to {member.name}'s profile.", 'info')
            else:
                flash('Profile not found.', 'error')
        except (ValueError, TypeError):
            flash('Invalid profile selected.', 'error')
            
    return redirect(request.referrer or url_for('dashboard'))

# --- PRIVATE ROUTING (DASHBOARD) ---

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    # 1. Base counts & filters based on switched profile
    if active_profile_id:
        total_records = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=active_profile_id).count()
        upcoming_appts = Appointment.query.filter_by(user_id=user_id, family_member_id=active_profile_id).filter(Appointment.date >= date.today()).count()
        vaccines_taken = Vaccination.query.filter_by(user_id=user_id, family_member_id=active_profile_id).count()
        active_prescriptions = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=active_profile_id, category='Prescription').count()
        
        # Load Health Profile for BMI & vitals summary
        profile = HealthProfile.query.filter_by(family_member_id=active_profile_id).first()
        recent_vitals = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(HealthMetric.recorded_at.desc()).first()
    else:
        # Primary user
        total_records = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=None).count()
        upcoming_appts = Appointment.query.filter_by(user_id=user_id, family_member_id=None).filter(Appointment.date >= date.today()).count()
        vaccines_taken = Vaccination.query.filter_by(user_id=user_id, family_member_id=None).count()
        active_prescriptions = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=None, category='Prescription').count()
        
        profile = HealthProfile.query.filter_by(user_id=user_id, family_member_id=None).first()
        recent_vitals = HealthMetric.query.filter_by(user_id=user_id, family_member_id=None).order_by(HealthMetric.recorded_at.desc()).first()

    family_members_count = FamilyMember.query.filter_by(user_id=user_id).count()
    
    # Calculate health score dynamically
    health_score = calculate_health_score_value(user_id, active_profile_id)
    
    # Recent Activities simulation logs
    recent_activities = []
    # Build list of last changes
    if active_profile_id:
        recs = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(MedicalRecord.created_at.desc()).limit(3).all()
        for r in recs:
            recent_activities.append({'action': f"Document Uploaded: {r.title}", 'timestamp': r.created_at})
        vits = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(HealthMetric.recorded_at.desc()).limit(2).all()
        for v in vits:
            recent_activities.append({'action': "Vitals Metric Recorded", 'timestamp': v.recorded_at})
    else:
        recs = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=None).order_by(MedicalRecord.created_at.desc()).limit(3).all()
        for r in recs:
            recent_activities.append({'action': f"Document Uploaded: {r.title}", 'timestamp': r.created_at})
        vits = HealthMetric.query.filter_by(user_id=user_id, family_member_id=None).order_by(HealthMetric.recorded_at.desc()).limit(2).all()
        for v in vits:
            recent_activities.append({'action': "Vitals Metric Recorded", 'timestamp': v.recorded_at})
            
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]
    
    # 2. Charts Data Processing
    # Records by Category counts
    category_counts = {}
    if active_profile_id:
        cats = db.session.query(MedicalRecord.category, db.func.count(MedicalRecord.id))\
            .filter_by(user_id=user_id, family_member_id=active_profile_id).group_by(MedicalRecord.category).all()
    else:
        cats = db.session.query(MedicalRecord.category, db.func.count(MedicalRecord.id))\
            .filter_by(user_id=user_id, family_member_id=None).group_by(MedicalRecord.category).all()
            
    for cat, val in cats:
        category_counts[cat] = val
        
    # Monthly Activity logs count (last 6 months)
    monthly_activity = {}
    for i in range(5, -1, -1):
        m_start = datetime.now() - timedelta(days=i*30)
        m_name = m_start.strftime('%b')
        monthly_activity[m_name] = 0
        
    # Count metrics and documents logged per month
    if active_profile_id:
        db_recs = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
        db_vits = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    else:
        db_recs = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=None).all()
        db_vits = HealthMetric.query.filter_by(user_id=user_id, family_member_id=None).all()
        
    for r in db_recs:
        m_name = r.created_at.strftime('%b')
        if m_name in monthly_activity:
            monthly_activity[m_name] += 1
    for v in db_vits:
        m_name = v.recorded_at.strftime('%b')
        if m_name in monthly_activity:
            monthly_activity[m_name] += 1

    return render_template('dashboard.html',
                           today=date.today(),
                           total_records=total_records,
                           upcoming_appts=upcoming_appts,
                           active_prescriptions=active_prescriptions,
                           vaccines_taken=vaccines_taken,
                           family_members_count=family_members_count,
                           health_score=health_score,
                           profile=profile,
                           recent_vitals=recent_vitals,
                           recent_activities=recent_activities,
                           category_counts=category_counts,
                           monthly_activity=monthly_activity)

# --- PROFILE HANDLING ROUTING ---

@app.route('/profile', methods=['GET', 'POST'])
def health_profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    # Load profile row based on Swapped profile status
    if active_profile_id:
        profile = HealthProfile.query.filter_by(family_member_id=active_profile_id).first()
    else:
        profile = HealthProfile.query.filter_by(user_id=user_id, family_member_id=None).first()
        
    if request.method == 'POST':
        blood_group = request.form.get('blood_group')
        height = float(request.form.get('height') or 0.0)
        weight = float(request.form.get('weight') or 0.0)
        allergies = request.form.get('allergies')
        chronic_diseases = request.form.get('chronic_diseases')
        current_medications = request.form.get('current_medications')
        
        emergency_contact_name = request.form.get('emergency_contact_name')
        emergency_contact_phone = request.form.get('emergency_contact_phone')
        family_doctor_name = request.form.get('family_doctor_name')
        family_doctor_phone = request.form.get('family_doctor_phone')
        insurance_provider = request.form.get('insurance_provider')
        insurance_policy_number = request.form.get('insurance_policy_number')
        
        if not profile:
            # Create a profile
            profile = HealthProfile(
                user_id=user_id if not active_profile_id else None,
                family_member_id=active_profile_id,
                blood_group=blood_group,
                height=height,
                weight=weight,
                allergies=allergies,
                chronic_diseases=chronic_diseases,
                current_medications=current_medications,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                family_doctor_name=family_doctor_name,
                family_doctor_phone=family_doctor_phone,
                insurance_provider=insurance_provider,
                insurance_policy_number=insurance_policy_number
            )
            db.session.add(profile)
        else:
            # Update
            profile.blood_group = blood_group
            profile.height = height
            profile.weight = weight
            profile.allergies = allergies
            profile.chronic_diseases = chronic_diseases
            profile.current_medications = current_medications
            profile.emergency_contact_name = emergency_contact_name
            profile.emergency_contact_phone = emergency_contact_phone
            profile.family_doctor_name = family_doctor_name
            profile.family_doctor_phone = family_doctor_phone
            profile.insurance_provider = insurance_provider
            profile.insurance_policy_number = insurance_policy_number
            
        db.session.commit()
        flash('Health Profile saved successfully!', 'success')
        return redirect(url_for('health_profile'))
        
    return render_template('profile.html', profile=profile)

# --- MEDICAL RECORDS ROUTING ---

@app.route('/records')
def medical_records():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    # Query parameters
    search_query = request.args.get('search', '').strip()
    category_query = request.args.get('category', '').strip()
    date_query = request.args.get('date', '').strip()
    
    # Base filter query
    if active_profile_id:
        query = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=active_profile_id)
    else:
        query = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=None)
        
    if search_query:
        query = query.filter(MedicalRecord.title.like(f"%{search_query}%"))
    if category_query:
        query = query.filter_by(category=category_query)
    if date_query:
        try:
            target_date = datetime.strptime(date_query, '%Y-%m-%d').date()
            query = query.filter_by(date=target_date)
        except ValueError:
            pass
            
    records = query.order_by(MedicalRecord.date.desc()).all()
    
    return render_template('records.html', 
                           records=records,
                           search_query=search_query,
                           category_query=category_query,
                           date_query=date_query)

@app.route('/records/upload', methods=['GET', 'POST'])
def upload_record():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        date_str = request.form.get('date')
        doctor_name = request.form.get('doctor_name')
        hospital_name = request.form.get('hospital_name')
        description = request.form.get('description')
        
        file = request.files.get('record_file')
        
        if not file or file.filename == '':
            flash('No file attached.', 'error')
            return redirect(url_for('upload_record'))
            
        if not allowed_file(file.filename):
            flash('Unsupported file format. PDF, Word documents, and Images are allowed.', 'error')
            return redirect(url_for('upload_record'))
            
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('upload_record'))
            
        # Secure filename configuration
        ext = file.filename.rsplit('.', 1)[1].lower()
        rand_filename = f"{session['user_id']}_{int(datetime.now().timestamp())}.{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], rand_filename)
        file.save(file_path)
        
        # Save record
        new_record = MedicalRecord(
            user_id=session['user_id'],
            family_member_id=session.get('active_profile_id'),
            title=title,
            category=category,
            date=record_date,
            doctor_name=doctor_name,
            hospital_name=hospital_name,
            file_path=rand_filename,
            description=description
        )
        db.session.add(new_record)
        
        # Add system log alert
        new_alert = Notification(
            user_id=session['user_id'],
            title='New Medical Document Logged',
            message=f"Document '{title}' categorized as {category} was successfully uploaded."
        )
        db.session.add(new_alert)
        db.session.commit()
        
        flash('Medical Record uploaded and logged successfully!', 'success')
        return redirect(url_for('medical_records'))
        
    return render_template('upload_record.html')

@app.route('/records/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    record = MedicalRecord.query.filter_by(id=record_id, user_id=session['user_id']).first()
    if record:
        # Delete local file if it exists
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], record.file_path)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass
        db.session.delete(record)
        db.session.commit()
        flash('Medical record deleted successfully.', 'success')
    else:
        flash('Medical record not found.', 'error')
        
    return redirect(url_for('medical_records'))

# --- HEALTH TIMELINE ROUTING ---

@app.route('/timeline')
def health_timeline():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    # Compile events
    timeline_events = []
    
    # 1. Fetch Records
    records = MedicalRecord.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    for r in records:
        timeline_events.append({
            'date': r.date,
            'title': r.title,
            'filter_type': 'records',
            'badge_text': r.category,
            'meta1': f"Doctor: {r.doctor_name}" if r.doctor_name else None,
            'meta2': f"Hospital: {r.hospital_name}" if r.hospital_name else None,
            'description': r.description,
            'file_path': r.file_path
        })
        
    # 2. Fetch Vitals Logs
    vitals = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    for v in vitals:
        # Build vital log text
        v_list = []
        if v.systolic and v.diastolic:
            v_list.append(f"BP: {v.systolic}/{v.diastolic} mmHg")
        if v.blood_sugar:
            v_list.append(f"Sugar: {v.blood_sugar} mg/dL")
        if v.oxygen_level:
            v_list.append(f"SpO2: {v.oxygen_level}%")
        if v.heart_rate:
            v_list.append(f"Pulse: {v.heart_rate} bpm")
        if v.body_temperature:
            v_list.append(f"Temp: {v.body_temperature} F")
            
        timeline_events.append({
            'date': v.recorded_at.date(),
            'title': "Vital Signs Logged",
            'filter_type': 'metrics',
            'badge_text': 'Vitals Metric',
            'meta1': ", ".join(v_list) if v_list else "No parameters recorded",
            'meta2': None,
            'description': f"Logged on {v.recorded_at.strftime('%I:%M %p')}"
        })
        
    # 3. Fetch Vaccinations
    vaccines = Vaccination.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    for vac in vaccines:
        timeline_events.append({
            'date': vac.date_taken,
            'title': vac.vaccine_name,
            'filter_type': 'vaccines',
            'badge_text': 'Vaccination',
            'meta1': f"Next booster due: {vac.next_due_date.strftime('%b %d, %Y')}" if vac.next_due_date else "No booster due",
            'meta2': f"Clinic: {vac.hospital_clinic_name}" if vac.hospital_clinic_name else None,
            'description': None
        })
        
    # 4. Fetch Appointments
    appts = Appointment.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    for a in appts:
        timeline_events.append({
            'date': a.date,
            'title': f"Consultation with Dr. {a.doctor_name}",
            'filter_type': 'appointments',
            'badge_text': 'Appointment Check',
            'meta1': f"Scheduled Time: {a.time.strftime('%I:%M %p')}",
            'meta2': f"Clinic: {a.hospital_name}",
            'description': a.purpose
        })
        
    # Sort timeline chronologically (latest first)
    timeline_events.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('timeline.html', timeline_events=timeline_events)

# --- APPOINTMENTS CALENDAR ROUTING ---

@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    if request.method == 'POST':
        doctor_name = request.form.get('doctor_name')
        hospital_name = request.form.get('hospital_name')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        purpose = request.form.get('purpose')
        
        try:
            appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            appt_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time formats.', 'error')
            return redirect(url_for('appointments'))
            
        new_appt = Appointment(
            user_id=user_id,
            family_member_id=active_profile_id,
            doctor_name=doctor_name,
            hospital_name=hospital_name,
            date=appt_date,
            time=appt_time,
            purpose=purpose
        )
        db.session.add(new_appt)
        
        # Add notification alert
        new_notif = Notification(
            user_id=user_id,
            title='New Appointment Scheduled',
            message=f"Consultation with Dr. {doctor_name} is booked on {appt_date.strftime('%b %d')} at {appt_time.strftime('%I:%M %p')}."
        )
        db.session.add(new_notif)
        db.session.commit()
        
        flash('Appointment successfully scheduled!', 'success')
        return redirect(url_for('appointments'))
        
    # Retrieve upcoming schedules
    if active_profile_id:
        appts = Appointment.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(Appointment.date.asc(), Appointment.time.asc()).all()
    else:
        appts = Appointment.query.filter_by(user_id=user_id, family_member_id=None).order_by(Appointment.date.asc(), Appointment.time.asc()).all()
        
    return render_template('appointments.html', appointments=appts)

@app.route('/appointments/delete/<int:appt_id>', methods=['POST'])
def delete_appointment(appt_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    appt = Appointment.query.filter_by(id=appt_id, user_id=session['user_id']).first()
    if appt:
        db.session.delete(appt)
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    else:
        flash('Appointment not found.', 'error')
        
    return redirect(url_for('appointments'))

# API route returning appointments JSON to FullCalendar.js
@app.route('/api/appointments')
def api_appointments():
    if not session.get('user_id'):
        return jsonify([])
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    if active_profile_id:
        appts = Appointment.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    else:
        appts = Appointment.query.filter_by(user_id=user_id, family_member_id=None).all()
        
    fc_events = []
    for a in appts:
        # Merge date and time strings for calendar parser
        start_datetime = datetime.combine(a.date, a.time).isoformat()
        fc_events.append({
            'id': a.id,
            'title': a.doctor_name,
            'start': start_datetime,
            'extendedProps': {
                'hospital': a.hospital_name,
                'description': a.purpose
            }
        })
        
    return jsonify(fc_events)

# --- EMERGENCY CARD ROUTING ---

@app.route('/emergency')
def emergency_access():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    # Fetch clinical profile parameters specifically
    if active_profile_id:
        # Switched to family member
        member = FamilyMember.query.filter_by(id=active_profile_id, user_id=user_id).first()
        profile = HealthProfile.query.filter_by(family_member_id=active_profile_id).first()
        
        # Mocking user data structure for template reuse
        user_stub = type('UserStub', (object,), {
            'full_name': member.name,
            'date_of_birth': date.today() - timedelta(days=member.age*365), # estimated DOB from age
            'gender': 'N/A',
            'phone_number': 'N/A'
        })()
        return render_template('emergency.html', user=user_stub, profile=profile)
    else:
        user = User.query.get(user_id)
        profile = HealthProfile.query.filter_by(user_id=user_id, family_member_id=None).first()
        return render_template('emergency.html', user=user, profile=profile)

# --- FAMILY MANAGEMENT ROUTING ---

@app.route('/family', methods=['GET', 'POST'])
def family_members():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form.get('name')
        relationship = request.form.get('relationship')
        age = int(request.form.get('age') or 0)
        blood_group = request.form.get('blood_group')
        
        # Insert member
        new_member = FamilyMember(
            user_id=user_id,
            name=name,
            relationship=relationship,
            age=age,
            blood_group=blood_group
        )
        db.session.add(new_member)
        db.session.commit()
        
        # Initialize default empty health profile for family member
        member_profile = HealthProfile(
            family_member_id=new_member.id,
            blood_group=blood_group,
            height=0.0,
            weight=0.0,
            allergies='',
            chronic_diseases='',
            current_medications=''
        )
        db.session.add(member_profile)
        db.session.commit()
        
        flash(f"Profile for '{name}' initialized successfully!", 'success')
        return redirect(url_for('family_members'))
        
    members = FamilyMember.query.filter_by(user_id=user_id).all()
    primary_user = User.query.get(user_id)
    owner_profile = HealthProfile.query.filter_by(user_id=user_id, family_member_id=None).first()
    
    return render_template('family.html', members=members, primary_user=primary_user, owner_profile=owner_profile)

@app.route('/family/delete/<int:member_id>', methods=['POST'])
def delete_family_member(member_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    member = FamilyMember.query.filter_by(id=member_id, user_id=session['user_id']).first()
    if member:
        # Clear profile switch target session variables if active
        if session.get('active_profile_id') == member_id:
            session['active_profile_id'] = None
            session['active_profile_name'] = None
            
        db.session.delete(member)
        db.session.commit()
        flash('Family member profile removed successfully.', 'success')
    else:
        flash('Profile not found.', 'error')
        
    return redirect(url_for('family_members'))

# --- FEMALE HEALTH ROUTING ---

@app.route('/female-health', methods=['GET', 'POST'])
def female_health():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    if session.get('user_gender') != 'Female':
        flash('Access restricted to Female accounts only.', 'error')
        return redirect(url_for('dashboard'))
        
    user_id = session['user_id']
    
    if request.method == 'POST':
        date_str = request.form.get('last_period_date')
        avg_len = int(request.form.get('average_cycle_length') or 28)
        duration = int(request.form.get('period_duration') or 5)
        
        cramps = 'cramps' in request.form
        headache = 'headache' in request.form
        mood_swings = 'mood_swings' in request.form
        fatigue = 'fatigue' in request.form
        back_pain = 'back_pain' in request.form
        
        try:
            last_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid period date format.', 'error')
            return redirect(url_for('female_health'))
            
        new_cycle = MenstrualCycle(
            user_id=user_id,
            last_period_date=last_date,
            average_cycle_length=avg_len,
            period_duration=duration,
            cramps=cramps,
            headache=headache,
            mood_swings=mood_swings,
            fatigue=fatigue,
            back_pain=back_pain
        )
        db.session.add(new_cycle)
        
        # Add calendar notification
        new_notif = Notification(
            user_id=user_id,
            title='Cycle Log Updated',
            message=f"Period start logged on {last_date.strftime('%b %d')}. Forecast indicators configured."
        )
        db.session.add(new_notif)
        db.session.commit()
        
        flash('Menstrual Cycle entry logged successfully!', 'success')
        return redirect(url_for('female_health'))
        
    cycles = MenstrualCycle.query.filter_by(user_id=user_id).order_by(MenstrualCycle.last_period_date.desc()).all()
    
    # Predictions logic based on latest entry
    next_period_date = None
    ovulation_date = None
    fertile_start = None
    fertile_end = None
    days_until_period = None
    current_cycle_day = None
    
    symptoms_count = {'cramps': 0, 'headache': 0, 'mood_swings': 0, 'fatigue': 0, 'back_pain': 0}
    
    if cycles:
        latest = cycles[0]
        # Forecast calculations
        next_period_date = latest.last_period_date + timedelta(days=latest.average_cycle_length)
        ovulation_date = latest.last_period_date + timedelta(days=latest.average_cycle_length - 14)
        fertile_start = ovulation_date - timedelta(days=5)
        fertile_end = ovulation_date + timedelta(days=1)
        
        days_until_period = (next_period_date - date.today()).days
        current_cycle_day = (date.today() - latest.last_period_date).days + 1
        
        # Symptoms aggregations for pie charts
        for c in cycles:
            if c.cramps: symptoms_count['cramps'] += 1
            if c.headache: symptoms_count['headache'] += 1
            if c.mood_swings: symptoms_count['mood_swings'] += 1
            if c.fatigue: symptoms_count['fatigue'] += 1
            if c.back_pain: symptoms_count['back_pain'] += 1

    return render_template('female_health.html',
                           cycles=cycles,
                           next_period_date=next_period_date,
                           ovulation_date=ovulation_date,
                           fertile_start=fertile_start,
                           fertile_end=fertile_end,
                           days_until_period=days_until_period,
                           current_cycle_day=current_cycle_day,
                           symptoms_count=symptoms_count)

@app.route('/female-health/delete/<int:cycle_id>', methods=['POST'])
def delete_cycle(cycle_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    cycle = MenstrualCycle.query.filter_by(id=cycle_id, user_id=session['user_id']).first()
    if cycle:
        db.session.delete(cycle)
        db.session.commit()
        flash('Menstrual Cycle log entry removed.', 'success')
    else:
        flash('Entry not found.', 'error')
        
    return redirect(url_for('female_health'))

# --- VACCINATION ROUTING ---

@app.route('/vaccinations', methods=['GET', 'POST'])
def vaccinations():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    if request.method == 'POST':
        vaccine_name = request.form.get('vaccine_name')
        date_taken_str = request.form.get('date_taken')
        next_due_str = request.form.get('next_due_date')
        hospital_clinic_name = request.form.get('hospital_clinic_name')
        
        try:
            taken_date = datetime.strptime(date_taken_str, '%Y-%m-%d').date()
            next_due_date = datetime.strptime(next_due_str, '%Y-%m-%d').date() if next_due_str else None
        except ValueError:
            flash('Invalid date values.', 'error')
            return redirect(url_for('vaccinations'))
            
        new_vax = Vaccination(
            user_id=user_id,
            family_member_id=active_profile_id,
            vaccine_name=vaccine_name,
            date_taken=taken_date,
            next_due_date=next_due_date,
            hospital_clinic_name=hospital_clinic_name
        )
        db.session.add(new_vax)
        
        # Add notifications trigger
        new_notif = Notification(
            user_id=user_id,
            title='Vaccination Logged',
            message=f"Immunization: {vaccine_name} administered successfully."
        )
        db.session.add(new_notif)
        db.session.commit()
        
        flash('Vaccination booster logged successfully!', 'success')
        return redirect(url_for('vaccinations'))
        
    # Read histories
    if active_profile_id:
        vaxs = Vaccination.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(Vaccination.date_taken.desc()).all()
    else:
        vaxs = Vaccination.query.filter_by(user_id=user_id, family_member_id=None).order_by(Vaccination.date_taken.desc()).all()
        
    # Booster alert generation (Due within 7 days)
    due_alerts = []
    for v in vaxs:
        if v.next_due_date and (v.next_due_date - date.today()).days <= 7:
            due_alerts.append(v)
            
    return render_template('vaccinations.html',
                           vaccinations=vaxs,
                           due_alerts=due_alerts,
                           today=date.today())

@app.route('/vaccinations/delete/<int:vax_id>', methods=['POST'])
def delete_vaccination(vax_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    vax = Vaccination.query.filter_by(id=vax_id, user_id=session['user_id']).first()
    if vax:
        db.session.delete(vax)
        db.session.commit()
        flash('Vaccination log deleted successfully.', 'success')
    else:
        flash('Vaccination not found.', 'error')
        
    return redirect(url_for('vaccinations'))

# --- HEALTH MONITORING ROUTING ---

@app.route('/monitoring', methods=['GET', 'POST'])
def health_monitoring():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    if request.method == 'POST':
        systolic = int(request.form.get('systolic') or 0)
        diastolic = int(request.form.get('diastolic') or 0)
        blood_sugar = float(request.form.get('blood_sugar') or 0.0)
        heart_rate = int(request.form.get('heart_rate') or 0)
        oxygen_level = int(request.form.get('oxygen_level') or 0)
        body_temperature = float(request.form.get('body_temperature') or 0.0)
        
        new_metric = HealthMetric(
            user_id=user_id,
            family_member_id=active_profile_id,
            systolic=systolic if systolic > 0 else None,
            diastolic=diastolic if diastolic > 0 else None,
            blood_sugar=blood_sugar if blood_sugar > 0 else None,
            heart_rate=heart_rate if heart_rate > 0 else None,
            oxygen_level=oxygen_level if oxygen_level > 0 else None,
            body_temperature=body_temperature if body_temperature > 0 else None
        )
        db.session.add(new_metric)
        
        # Check alerts threshold
        notif_msg = []
        if systolic > 140 or diastolic > 90:
            notif_msg.append("Blood pressure is elevated.")
        if oxygen_level > 0 and oxygen_level < 95:
            notif_msg.append("Oxygen levels show drop below 95%.")
            
        if notif_msg:
            critical_alert = Notification(
                user_id=user_id,
                title='Vitals Level Warning',
                message=" ".join(notif_msg) + " Consider consultations."
            )
            db.session.add(critical_alert)
            
        db.session.commit()
        flash('Health vitals metrics logged successfully!', 'success')
        return redirect(url_for('health_monitoring'))
        
    # Read metrics logs (Limit 15 for trends charts performance)
    if active_profile_id:
        metrics = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(HealthMetric.recorded_at.desc()).limit(15).all()
    else:
        metrics = HealthMetric.query.filter_by(user_id=user_id, family_member_id=None).order_by(HealthMetric.recorded_at.desc()).limit(15).all()
        
    return render_template('monitoring.html', metrics=metrics)

@app.route('/monitoring/delete/<int:vitals_id>', methods=['POST'])
def delete_vitals(vitals_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    metric = HealthMetric.query.filter_by(id=vitals_id, user_id=session['user_id']).first()
    if metric:
        db.session.delete(metric)
        db.session.commit()
        flash('Vitals entry log deleted successfully.', 'success')
    else:
        flash('Vitals entry not found.', 'error')
        
    return redirect(url_for('health_monitoring'))

# --- HEALTH ANALYTICS ROUTING ---

@app.route('/analytics')
def health_analytics():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    active_profile_id = session.get('active_profile_id')
    
    # 1. Base user demographics
    if active_profile_id:
        member = FamilyMember.query.filter_by(id=active_profile_id, user_id=user_id).first()
        profile = HealthProfile.query.filter_by(family_member_id=active_profile_id).first()
        recent_vitals = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).order_by(HealthMetric.recorded_at.desc()).first()
        
        user_stub = type('UserStub', (object,), {
            'full_name': member.name,
            'date_of_birth': date.today() - timedelta(days=member.age*365),
            'gender': 'N/A',
            'phone_number': 'N/A'
        })()
    else:
        user_stub = User.query.get(user_id)
        profile = HealthProfile.query.filter_by(user_id=user_id, family_member_id=None).first()
        recent_vitals = HealthMetric.query.filter_by(user_id=user_id, family_member_id=None).order_by(HealthMetric.recorded_at.desc()).first()
        
    # Health Score & breakdown details
    health_score, scores = calculate_health_score_breakdown(user_id, active_profile_id)
    
    # Insights compiler
    insights = []
    if profile:
        # BMI Insights
        if profile.bmi_category == 'Normal':
            insights.append(('Optimal BMI Range', 'Your BMI is within the healthy range. Maintain standard calorie intake.', 'success'))
        elif profile.bmi_category == 'Overweight':
            insights.append(('Overweight Threshold', 'Your BMI falls in the overweight range. Consider cardio activities.', 'warning'))
        elif profile.bmi_category == 'Obese':
            insights.append(('Clinical Obesity Alert', 'Your BMI indicates obesity. We advise consulting a clinical nutritionist.', 'danger'))
        elif profile.bmi_category == 'Underweight':
            insights.append(('Underweight Indicator', 'Your BMI is below normal range. Increase dietary nutrients.', 'warning'))
            
    if recent_vitals:
        # Blood pressure
        if recent_vitals.systolic and recent_vitals.diastolic:
            if recent_vitals.systolic < 120 and recent_vitals.diastolic < 80:
                insights.append(('Healthy Blood Pressure', 'Blood pressure is optimal. Cardiorespiratory readings are strong.', 'success'))
            elif recent_vitals.systolic < 130 and recent_vitals.diastolic < 80:
                insights.append(('Pre-hypertension Warning', 'Systolic readings show elevated trends.', 'warning'))
            else:
                insights.append(('Hypertension Alert', 'Recent blood pressure logs indicate high systolic/diastolic levels.', 'danger'))
                
        # SpO2
        if recent_vitals.oxygen_level:
            if recent_vitals.oxygen_level >= 95:
                insights.append(('Oxygen Saturation Optimal', f"SpO2 oxygen level is healthy at {recent_vitals.oxygen_level}%.", 'success'))
            else:
                insights.append(('Hypoxia Risk Alert', f"Oxygen level SpO2 dropped below safe threshold to {recent_vitals.oxygen_level}%.", 'danger'))
                
    # Vaccine check
    vaxs = Vaccination.query.filter_by(user_id=user_id, family_member_id=active_profile_id).all()
    overdue_booster = False
    for v in vaxs:
        if v.next_due_date and v.next_due_date < date.today():
            overdue_booster = True
            break
    if overdue_booster:
        insights.append(('Booster Immunization Overdue', 'One or more vaccine booster doses are overdue. Check vaccine log.', 'danger'))
    elif vaxs:
        insights.append(('Immunization Status Up-to-date', 'Vaccination schedule is current and active.', 'success'))

    return render_template('analytics.html',
                           user=user_stub,
                           profile=profile,
                           recent_vitals=recent_vitals,
                           health_score=health_score,
                           vitals_score=scores['vitals'],
                           vax_score=scores['vaccine'],
                           appt_score=scores['appointments'],
                           insights=insights,
                           today=date.today())

# Dynamic calculators helpers for scoring
def calculate_health_score_value(user_id, active_profile_id):
    score, _ = calculate_health_score_breakdown(user_id, active_profile_id)
    return score

def calculate_health_score_breakdown(user_id, active_profile_id):
    scores = {'bmi': 0, 'vitals': 0, 'vaccine': 0, 'appointments': 0}
    
    if active_profile_id:
        profile = HealthProfile.query.filter_by(family_member_id=active_profile_id).first()
        vits_count = HealthMetric.query.filter_by(user_id=user_id, family_member_id=active_profile_id).count()
        vax_count = Vaccination.query.filter_by(user_id=user_id, family_member_id=active_profile_id).count()
        appt_count = Appointment.query.filter_by(user_id=user_id, family_member_id=active_profile_id).count()
    else:
        profile = HealthProfile.query.filter_by(user_id=user_id, family_member_id=None).first()
        vits_count = HealthMetric.query.filter_by(user_id=user_id, family_member_id=None).count()
        vax_count = Vaccination.query.filter_by(user_id=user_id, family_member_id=None).count()
        appt_count = Appointment.query.filter_by(user_id=user_id, family_member_id=None).count()
        
    # 1. BMI category points (25 pts)
    if profile:
        if profile.bmi_category == 'Normal':
            scores['bmi'] = 25
        elif profile.bmi_category in ['Overweight', 'Underweight']:
            scores['bmi'] = 15
        else:
            scores['bmi'] = 10
            
    # 2. Vitals entries logs factor (25 pts)
    if vits_count >= 5:
        scores['vitals'] = 25
    elif vits_count >= 2:
        scores['vitals'] = 15
    elif vits_count > 0:
        scores['vitals'] = 10
        
    # 3. Vaccines factor (25 pts)
    if vax_count >= 2:
        scores['vaccine'] = 25
    elif vax_count > 0:
        scores['vaccine'] = 15
        
    # 4. Appts factor (25 pts)
    if appt_count >= 2:
        scores['appointments'] = 25
    elif appt_count > 0:
        scores['appointments'] = 15
        
    total_score = scores['bmi'] + scores['vitals'] + scores['vaccine'] + scores['appointments']
    # fallback default score if profile parameters are completely blank
    if total_score == 0:
        total_score = 50
        
    return total_score, scores

# --- NOTIFICATIONS CENTER ROUTING ---

@app.route('/notifications')
def notifications():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    notifs = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/read/<int:notif_id>', methods=['POST'])
def mark_notification_read(notif_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    notif = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first()
    if notif:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('notifications'))

@app.route('/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    Notification.query.filter_by(user_id=session['user_id'], is_read=False).update({Notification.is_read: True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

@app.route('/notifications/clear', methods=['POST'])
def clear_notifications():
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    Notification.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()
    flash('Notifications cleared.', 'success')
    return redirect(url_for('notifications'))

@app.route('/notifications/delete/<int:notif_id>', methods=['POST'])
def delete_notification(notif_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    notif = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first()
    if notif:
        db.session.delete(notif)
        db.session.commit()
    return redirect(url_for('notifications'))

# --- ENGINE LAUNCH FOR PRODUCTION ---

if __name__ == '__main__':
    with app.app_context():
        # Provision tables automatically on SQLite fallback or MySQL setup
        db.create_all()
    # Runs on standard port 5000
    app.run(debug=True, port=5000)
