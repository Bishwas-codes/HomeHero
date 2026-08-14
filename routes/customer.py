from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import User, WorkerProfile
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.review import Review
from models.notification import Notification
from utils.decorators import customer_required
from utils.geo import get_eligible_workers_for_request, haversine_distance

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/dashboard')
@customer_required
def dashboard():
    # Fetch customer's active requests (SEARCHING, ASSIGNED, ON_THE_WAY, IN_PROGRESS)
    active_requests = ServiceRequest.query.filter(
        ServiceRequest.customer_id == current_user.id,
        ServiceRequest.status.in_(['SEARCHING', 'ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
    ).order_by(ServiceRequest.created_at.desc()).all()

    # Fetch recent requests
    recent_requests = ServiceRequest.query.filter_by(
        customer_id=current_user.id
    ).order_by(ServiceRequest.created_at.desc()).limit(5).all()

    # Metrics
    total_bookings = ServiceRequest.query.filter_by(customer_id=current_user.id).count()
    completed_bookings = ServiceRequest.query.filter_by(customer_id=current_user.id, status='COMPLETED').count()
    active_count = len(active_requests)

    # Calculate total spent
    completed_reqs = ServiceRequest.query.filter_by(customer_id=current_user.id, status='COMPLETED').all()
    total_spent = sum(r.budget or r.service.base_price for r in completed_reqs)

    popular_categories = ServiceCategory.query.filter_by(is_active=True).limit(6).all()

    return render_template(
        'customer/dashboard.html',
        active_requests=active_requests,
        recent_requests=recent_requests,
        total_bookings=total_bookings,
        completed_bookings=completed_bookings,
        active_count=active_count,
        total_spent=total_spent,
        popular_categories=popular_categories
    )


@customer_bp.route('/book', methods=['GET', 'POST'])
@customer_required
def book_service():
    categories = ServiceCategory.query.filter_by(is_active=True).all()
    demo_locations = current_app.config.get('DEMO_LOCATIONS', [])
    selected_service_id = request.args.get('service_id', type=int)

    if request.method == 'POST':
        service_id = request.form.get('service_id', type=int)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        location_name = request.form.get('location_name', '').strip()
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        budget = request.form.get('budget', type=float)

        if not service_id or not title or not description or not address:
            flash('Please complete all required fields (Service, Title, Description, and Address).', 'warning')
            return render_template('customer/book_service.html', categories=categories, demo_locations=demo_locations, selected_service_id=service_id)

        # Default fallback coordinates if user didn't select or allow GPS
        if latitude is None or longitude is None:
            latitude = 26.1820
            longitude = 91.7510
            location_name = location_name or "Guwahati Central"

        service_obj = db.get_or_404(ServiceCategory, service_id)
        if budget is None or budget <= 0:
            budget = service_obj.base_price

        # Create new service request
        new_request = ServiceRequest(
            customer_id=current_user.id,
            service_id=service_id,
            title=title,
            description=description,
            address=address,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            budget=budget,
            status='SEARCHING',
            created_at=datetime.now()
        )
        db.session.add(new_request)
        db.session.commit()

        # Find eligible workers and send in-app notifications
        eligible_workers = get_eligible_workers_for_request(new_request, max_radius_km=15.0)
        for worker_user, profile, dist in eligible_workers:
            notif = Notification(
                user_id=worker_user.id,
                request_id=new_request.id,
                title=f"New {service_obj.name} Request Nearby! ({dist} km away)",
                message=f"{new_request.title} near {new_request.location_name}. Budget: ₹{new_request.budget:.0f}",
                link=url_for('worker.dashboard')
            )
            db.session.add(notif)
        db.session.commit()

        flash('Your service request has been broadcasted! Searching for nearby active workers...', 'success')
        return redirect(url_for('customer.track_request', request_id=new_request.id))

    return render_template(
        'customer/book_service.html',
        categories=categories,
        demo_locations=demo_locations,
        selected_service_id=selected_service_id
    )


@customer_bp.route('/request/<int:request_id>')
@customer_required
def track_request(request_id):
    req_obj = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.id).first_or_404()
    
    # Calculate distance if worker assigned
    worker_distance = None
    if req_obj.assigned_worker_id and req_obj.worker and req_obj.worker.worker_profile:
        worker_distance = haversine_distance(
            req_obj.latitude, req_obj.longitude,
            req_obj.worker.worker_profile.latitude, req_obj.worker.worker_profile.longitude
        )

    # Check if review already exists
    existing_review = Review.query.filter_by(request_id=req_obj.id).first()

    return render_template(
        'customer/track_request.html',
        req=req_obj,
        worker_distance=worker_distance,
        existing_review=existing_review
    )


@customer_bp.route('/request/<int:request_id>/cancel', methods=['POST'])
@customer_required
def cancel_request(request_id):
    req_obj = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.id).first_or_404()
    
    if req_obj.status in ['COMPLETED', 'CANCELLED']:
        flash('This request cannot be cancelled because it is already finished.', 'warning')
        return redirect(url_for('customer.track_request', request_id=request_id))

    reason = request.form.get('reason', 'Cancelled by customer')
    req_obj.status = 'CANCELLED'
    req_obj.cancelled_at = datetime.now()
    req_obj.cancellation_reason = reason

    # If a worker was assigned, notify them
    if req_obj.assigned_worker_id:
        notif = Notification(
            user_id=req_obj.assigned_worker_id,
            request_id=req_obj.id,
            title="Service Request Cancelled",
            message=f"Request #{req_obj.id} was cancelled by the customer. Reason: {reason}",
            link=url_for('worker.dashboard')
        )
        db.session.add(notif)

    db.session.commit()
    flash('Service request has been cancelled.', 'info')
    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/request/<int:request_id>/review', methods=['POST'])
@customer_required
def submit_review(request_id):
    req_obj = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.id).first_or_404()

    if req_obj.status != 'COMPLETED':
        flash('You can only submit reviews for completed services.', 'warning')
        return redirect(url_for('customer.track_request', request_id=request_id))

    if not req_obj.assigned_worker_id:
        flash('No worker was assigned to this request.', 'warning')
        return redirect(url_for('customer.dashboard'))

    existing_review = Review.query.filter_by(request_id=req_obj.id).first()
    if existing_review:
        flash('You have already submitted a review for this service.', 'info')
        return redirect(url_for('customer.track_request', request_id=request_id))

    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash('Please select a rating between 1 and 5 stars.', 'warning')
        return redirect(url_for('customer.track_request', request_id=request_id))

    review = Review(
        request_id=req_obj.id,
        customer_id=current_user.id,
        worker_id=req_obj.assigned_worker_id,
        rating=rating,
        comment=comment,
        created_at=datetime.now()
    )
    db.session.add(review)
    db.session.flush()

    # Recalculate worker stats
    if req_obj.worker and req_obj.worker.worker_profile:
        req_obj.worker.worker_profile.update_rating_stats()

    # Notify worker of the review
    notif = Notification(
        user_id=req_obj.assigned_worker_id,
        request_id=req_obj.id,
        title=f"New {rating}-Star Review Received!",
        message=f"{current_user.name} rated your service {rating} stars: \"{comment[:60]}...\"",
        link=url_for('worker.jobs_history')
    )
    db.session.add(notif)
    db.session.commit()

    flash('Thank you! Your review and rating have been submitted successfully.', 'success')
    return redirect(url_for('customer.track_request', request_id=request_id))


@customer_bp.route('/history')
@customer_required
def history():
    status_filter = request.args.get('status')
    query = ServiceRequest.query.filter_by(customer_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    requests = query.order_by(ServiceRequest.created_at.desc()).all()
    return render_template('customer/history.html', requests=requests, status_filter=status_filter)


@customer_bp.route('/profile', methods=['GET', 'POST'])
@customer_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        if not name or not phone:
            flash('Name and phone number are required.', 'warning')
            return render_template('customer/profile.html')

        current_user.name = name
        current_user.phone = phone

        if new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return render_template('customer/profile.html')
            current_user.set_password(new_password)
            flash('Profile and password updated successfully!', 'success')
        else:
            flash('Profile updated successfully!', 'success')

        db.session.commit()
        return redirect(url_for('customer.profile'))

    return render_template('customer/profile.html')
