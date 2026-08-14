from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session
from flask_login import login_required, current_user
from models import db
from models.user import User, WorkerProfile
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.review import Review
from models.notification import Notification
from utils.decorators import worker_required
from utils.geo import haversine_distance, is_worker_eligible_for_request

worker_bp = Blueprint('worker', __name__, url_prefix='/worker')

@worker_bp.route('/dashboard')
@worker_required
def dashboard():
    profile = current_user.worker_profile
    if not profile:
        flash('Worker profile not found. Please contact support.', 'danger')
        return redirect(url_for('index'))

    # Check for current active ongoing job
    active_job = ServiceRequest.query.filter(
        ServiceRequest.assigned_worker_id == current_user.id,
        ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
    ).first()

    # Get rejected request IDs from session for this worker
    rejected_ids = session.get('rejected_requests', [])

    # Find incoming matching requests if worker is available and has no active job
    incoming_requests = []
    if profile.is_available and profile.is_approved and not active_job:
        worker_service_ids = [s.id for s in profile.services]
        
        # Candidate requests currently searching
        candidates = ServiceRequest.query.filter(
            ServiceRequest.status == 'SEARCHING',
            ServiceRequest.service_id.in_(worker_service_ids)
        ).order_by(ServiceRequest.created_at.desc()).all()

        max_radius = current_app.config.get('DEFAULT_SEARCH_RADIUS_KM', 15.0)

        for req in candidates:
            if req.id in rejected_ids:
                continue
            
            # Calculate distance using Haversine formula
            dist_km = haversine_distance(
                req.latitude, req.longitude,
                profile.latitude, profile.longitude
            )
            
            if dist_km <= max_radius:
                incoming_requests.append({
                    'req': req,
                    'distance': dist_km
                })

        # Sort closest first
        incoming_requests.sort(key=lambda x: x['distance'])

    # Recent completed jobs
    completed_jobs = ServiceRequest.query.filter_by(
        assigned_worker_id=current_user.id,
        status='COMPLETED'
    ).order_by(ServiceRequest.completed_at.desc()).limit(5).all()

    # Calculate earnings
    total_earnings = sum(job.budget or job.service.base_price for job in completed_jobs)

    return render_template(
        'worker/dashboard.html',
        profile=profile,
        active_job=active_job,
        incoming_requests=incoming_requests,
        completed_jobs=completed_jobs,
        total_earnings=total_earnings
    )


@worker_bp.route('/toggle-availability', methods=['POST'])
@worker_required
def toggle_availability():
    profile = current_user.worker_profile
    if profile:
        profile.is_available = not profile.is_available
        db.session.commit()
        status_str = "Online (Ready to accept jobs)" if profile.is_available else "Offline (Not receiving requests)"
        flash(f'Availability status updated to {status_str}', 'info')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'is_available': profile.is_available if profile else False})
        
    return redirect(url_for('worker.dashboard'))


@worker_bp.route('/accept-request/<int:request_id>', methods=['POST'])
@worker_required
def accept_request(request_id):
    """
    CRITICAL ATOMIC ACCEPTANCE LOGIC:
    Uses database conditional atomic update to ensure that if multiple workers
    click Accept at the same time, exactly ONE worker succeeds.
    """
    profile = current_user.worker_profile
    if not profile or not profile.is_approved or not profile.is_available:
        flash('You must be an approved and available worker to accept jobs.', 'warning')
        return redirect(url_for('worker.dashboard'))

    # Check if worker already has an active ongoing job
    current_active = ServiceRequest.query.filter(
        ServiceRequest.assigned_worker_id == current_user.id,
        ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
    ).first()

    if current_active:
        flash('You already have an active ongoing job. Complete it before accepting another.', 'warning')
        return redirect(url_for('worker.active_job'))

    # ATOMIC DATABASE UPDATE:
    # Updates status to ASSIGNED ONLY IF status is currently SEARCHING
    rows_updated = ServiceRequest.query.filter(
        ServiceRequest.id == request_id,
        ServiceRequest.status == 'SEARCHING'
    ).update({
        'status': 'ASSIGNED',
        'assigned_worker_id': current_user.id,
        'accepted_at': datetime.now()
    }, synchronize_session='fetch')

    db.session.commit()

    if rows_updated == 0:
        # Another worker already accepted or request was cancelled
        flash('Sorry, this request has already been accepted by another service provider or cancelled.', 'warning')
        return redirect(url_for('worker.dashboard'))

    # Success! Now fetch the fresh request object
    accepted_request = db.session.get(ServiceRequest, request_id)

    # Send Notification to Customer
    notif = Notification(
        user_id=accepted_request.customer_id,
        request_id=accepted_request.id,
        title=f"Worker Assigned: {current_user.name}",
        message=f"{current_user.name} ({profile.rating_avg}★) has accepted your {accepted_request.service.name} request.",
        link=url_for('customer.track_request', request_id=accepted_request.id)
    )
    db.session.add(notif)
    db.session.commit()

    flash('Request successfully accepted! Customer contact and location details are now available.', 'success')
    return redirect(url_for('worker.active_job'))


@worker_bp.route('/reject-request/<int:request_id>', methods=['POST'])
@worker_required
def reject_request(request_id):
    """Hide this request from current worker's radar during this session"""
    rejected = session.get('rejected_requests', [])
    if request_id not in rejected:
        rejected.append(request_id)
        session['rejected_requests'] = rejected
    
    flash('Request declined and removed from your radar.', 'info')
    return redirect(url_for('worker.dashboard'))


@worker_bp.route('/active-job')
@worker_required
def active_job():
    job = ServiceRequest.query.filter(
        ServiceRequest.assigned_worker_id == current_user.id,
        ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
    ).first()

    if not job:
        flash('You do not currently have any active ongoing jobs.', 'info')
        return redirect(url_for('worker.dashboard'))

    # Calculate distance to customer
    distance = haversine_distance(
        job.latitude, job.longitude,
        current_user.worker_profile.latitude, current_user.worker_profile.longitude
    )

    return render_template('worker/active_job.html', job=job, distance=distance)


@worker_bp.route('/update-status/<int:request_id>/<new_status>', methods=['POST'])
@worker_required
def update_status(request_id, new_status):
    job = ServiceRequest.query.filter_by(
        id=request_id,
        assigned_worker_id=current_user.id
    ).first_or_404()

    valid_transitions = {
        'ASSIGNED': 'ON_THE_WAY',
        'ON_THE_WAY': 'IN_PROGRESS',
        'IN_PROGRESS': 'COMPLETED'
    }

    if valid_transitions.get(job.status) != new_status:
        flash(f'Invalid status transition from {job.status} to {new_status}.', 'warning')
        return redirect(url_for('worker.active_job'))

    job.status = new_status

    if new_status == 'ON_THE_WAY':
        msg_title = "Worker On The Way!"
        msg_text = f"{current_user.name} is traveling to your location."
    elif new_status == 'IN_PROGRESS':
        job.started_at = datetime.now()
        msg_title = "Service Started!"
        msg_text = f"{current_user.name} has arrived and started the service."
    elif new_status == 'COMPLETED':
        job.completed_at = datetime.now()
        msg_title = "Service Completed!"
        msg_text = f"{current_user.name} has completed the service. Please rate your experience!"
        
        # Increment total completed jobs counter
        if current_user.worker_profile:
            current_user.worker_profile.total_jobs_completed = (current_user.worker_profile.total_jobs_completed or 0) + 1

    # Send Notification to Customer
    notif = Notification(
        user_id=job.customer_id,
        request_id=job.id,
        title=msg_title,
        message=msg_text,
        link=url_for('customer.track_request', request_id=job.id)
    )
    db.session.add(notif)
    db.session.commit()

    if new_status == 'COMPLETED':
        flash('Service marked as completed! Great job.', 'success')
        return redirect(url_for('worker.jobs_history'))

    flash(f'Status updated to: {new_status.replace("_", " ").title()}', 'success')
    return redirect(url_for('worker.active_job'))


@worker_bp.route('/jobs')
@worker_required
def jobs_history():
    jobs = ServiceRequest.query.filter_by(
        assigned_worker_id=current_user.id
    ).order_by(ServiceRequest.created_at.desc()).all()

    # Calculate earnings summary
    completed_jobs = [j for j in jobs if j.status == 'COMPLETED']
    total_earnings = sum(j.budget or j.service.base_price for j in completed_jobs)

    # Reviews received
    reviews = Review.query.filter_by(worker_id=current_user.id).order_by(Review.created_at.desc()).all()

    return render_template(
        'worker/jobs_history.html',
        jobs=jobs,
        completed_jobs=completed_jobs,
        total_earnings=total_earnings,
        reviews=reviews
    )


@worker_bp.route('/profile', methods=['GET', 'POST'])
@worker_required
def profile():
    profile_obj = current_user.worker_profile
    categories = ServiceCategory.query.filter_by(is_active=True).all()
    demo_locations = current_app.config.get('DEMO_LOCATIONS', [])

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        experience = int(request.form.get('experience', 1))
        hourly_rate = float(request.form.get('hourly_rate', 300.0))
        bio = request.form.get('bio', '').strip()
        
        location_name = request.form.get('location_name', '').strip()
        latitude = float(request.form.get('latitude', profile_obj.latitude))
        longitude = float(request.form.get('longitude', profile_obj.longitude))
        
        selected_services = request.form.getlist('services')

        if not name or not phone:
            flash('Name and phone are required.', 'warning')
            return render_template('worker/profile.html', profile=profile_obj, categories=categories, demo_locations=demo_locations)

        current_user.name = name
        current_user.phone = phone
        
        profile_obj.experience_years = experience
        profile_obj.hourly_rate = hourly_rate
        profile_obj.bio = bio
        profile_obj.location_name = location_name
        profile_obj.latitude = latitude
        profile_obj.longitude = longitude

        # Update services
        profile_obj.services = []
        for s_id in selected_services:
            cat = db.session.get(ServiceCategory, int(s_id))
            if cat:
                profile_obj.services.append(cat)

        db.session.commit()
        flash('Worker profile updated successfully!', 'success')
        return redirect(url_for('worker.profile'))

    return render_template('worker/profile.html', profile=profile_obj, categories=categories, demo_locations=demo_locations)
