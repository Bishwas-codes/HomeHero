from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User, WorkerProfile
from models.service import ServiceCategory

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        elif current_user.role == 'worker':
            return redirect(url_for('worker.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please check your credentials.', 'danger')
            return render_template('auth/login.html')

        if user.status != 'active':
            flash('Your account has been suspended. Please contact platform support.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        elif user.role == 'worker':
            return redirect(url_for('worker.dashboard'))
        elif user.role == 'admin':
            return redirect(url_for('admin.dashboard'))

        return redirect(url_for('index'))

    return render_template('auth/login.html')


@auth_bp.route('/demo-login/<role_key>')
def demo_login(role_key):
    """
    1-Click Demo Login switcher for Viva and Project Presentations.
    Instant switch without typing credentials!
    """
    demo_emails = {
        'admin': 'admin@example.com',
        'customer': 'customer@example.com',
        'plumber': 'rahul@example.com',
        'electrician': 'amit@example.com',
        'cleaner': 'rohit@example.com',
        'ac_repair': 'priya@example.com',
        'carpenter': 'manoj@example.com',
    }

    target_email = demo_emails.get(role_key)
    if not target_email:
        flash('Unknown demo account requested.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=target_email).first()
    if not user:
        flash(f'Demo account {target_email} not found in database. Please run seed script.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user, remember=True)
    flash(f'Logged in as Demo User: {user.name} ({user.role.title()})', 'info')

    if user.role == 'customer':
        return redirect(url_for('customer.dashboard'))
    elif user.role == 'worker':
        return redirect(url_for('worker.dashboard'))
    elif user.role == 'admin':
        return redirect(url_for('admin.dashboard'))

    return redirect(url_for('index'))


@auth_bp.route('/register/customer', methods=['GET', 'POST'])
def register_customer():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validation
        if not name or not email or not phone or not password:
            flash('All fields are required.', 'warning')
            return render_template('auth/register_customer.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return render_template('auth/register_customer.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return render_template('auth/register_customer.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register_customer.html')

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            role='customer',
            status='active'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Registration successful! Welcome to HomeHero.', 'success')
        return redirect(url_for('customer.dashboard'))

    return render_template('auth/register_customer.html')


@auth_bp.route('/register/worker', methods=['GET', 'POST'])
def register_worker():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    categories = ServiceCategory.query.filter_by(is_active=True).all()
    demo_locations = current_app.config.get('DEMO_LOCATIONS', [])

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        experience = int(request.form.get('experience', 1))
        hourly_rate = float(request.form.get('hourly_rate', 300.0))
        bio = request.form.get('bio', '').strip()
        
        location_name = request.form.get('location_name', 'Guwahati')
        latitude = float(request.form.get('latitude', 26.1820))
        longitude = float(request.form.get('longitude', 91.7510))
        
        selected_services = request.form.getlist('services')

        if not name or not email or not phone or not password:
            flash('Please fill in all basic registration fields.', 'warning')
            return render_template('auth/register_worker.html', categories=categories, demo_locations=demo_locations)

        if not selected_services:
            flash('Please select at least one service category you can provide.', 'warning')
            return render_template('auth/register_worker.html', categories=categories, demo_locations=demo_locations)

        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return render_template('auth/register_worker.html', categories=categories, demo_locations=demo_locations)

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register_worker.html', categories=categories, demo_locations=demo_locations)

        # Create worker user
        new_worker = User(
            name=name,
            email=email,
            phone=phone,
            role='worker',
            status='active'
        )
        new_worker.set_password(password)
        db.session.add(new_worker)
        db.session.flush()

        # Create worker profile (auto-approved for smooth demonstration)
        worker_profile = WorkerProfile(
            user_id=new_worker.id,
            experience_years=experience,
            hourly_rate=hourly_rate,
            bio=bio,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            is_available=True,
            is_approved=True,
            rating_avg=5.0,
            rating_count=0,
            total_jobs_completed=0
        )

        for s_id in selected_services:
            service_obj = db.session.get(ServiceCategory, int(s_id))
            if service_obj:
                worker_profile.services.append(service_obj)

        db.session.add(worker_profile)
        db.session.commit()

        login_user(new_worker)
        flash('Worker registration successful! Your profile is active and ready to accept nearby jobs.', 'success')
        return redirect(url_for('worker.dashboard'))

    return render_template('auth/register_worker.html', categories=categories, demo_locations=demo_locations)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))
