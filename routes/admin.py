from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import User, WorkerProfile
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.review import Review
from utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Key Metrics
    total_customers = User.query.filter_by(role='customer').count()
    total_workers = User.query.filter_by(role='worker').count()
    
    active_workers = (
        WorkerProfile.query
        .join(User)
        .filter(User.status == 'active', WorkerProfile.is_approved == True, WorkerProfile.is_available == True)
        .count()
    )

    pending_requests = ServiceRequest.query.filter_by(status='SEARCHING').count()
    active_jobs = ServiceRequest.query.filter(ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])).count()
    completed_jobs = ServiceRequest.query.filter_by(status='COMPLETED').count()
    cancelled_jobs = ServiceRequest.query.filter_by(status='CANCELLED').count()
    
    total_requests = ServiceRequest.query.count()

    # Total Platform Booking Volume
    completed_reqs = ServiceRequest.query.filter_by(status='COMPLETED').all()
    total_volume = sum(r.budget or r.service.base_price for r in completed_reqs)

    # Recent Requests
    recent_requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).limit(8).all()

    # Service categories with request count
    categories = ServiceCategory.query.all()
    category_stats = []
    for cat in categories:
        count = ServiceRequest.query.filter_by(service_id=cat.id).count()
        category_stats.append({
            'name': cat.name,
            'icon': cat.icon,
            'base_price': cat.base_price,
            'request_count': count
        })

    return render_template(
        'admin/dashboard.html',
        total_customers=total_customers,
        total_workers=total_workers,
        active_workers=active_workers,
        pending_requests=pending_requests,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        cancelled_jobs=cancelled_jobs,
        total_requests=total_requests,
        total_volume=total_volume,
        recent_requests=recent_requests,
        category_stats=category_stats
    )


@admin_bp.route('/workers')
@admin_required
def workers():
    workers_list = User.query.filter_by(role='worker').order_by(User.created_at.desc()).all()
    return render_template('admin/workers.html', workers=workers_list)


@admin_bp.route('/workers/<int:user_id>/toggle-approval', methods=['POST'])
@admin_required
def toggle_worker_approval(user_id):
    worker_user = User.query.filter_by(id=user_id, role='worker').first_or_404()
    if worker_user.worker_profile:
        worker_user.worker_profile.is_approved = not worker_user.worker_profile.is_approved
        db.session.commit()
        status = "Approved" if worker_user.worker_profile.is_approved else "Pending Approval"
        flash(f"Worker {worker_user.name} status updated to: {status}", "success")
    return redirect(url_for('admin.workers'))


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot suspend your own admin account.", "warning")
        return redirect(request.referrer or url_for('admin.dashboard'))

    user.status = 'suspended' if user.status == 'active' else 'active'
    db.session.commit()
    flash(f"User {user.name} ({user.role}) is now {user.status.upper()}.", "info")
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/customers')
@admin_required
def customers():
    customers_list = User.query.filter_by(role='customer').order_by(User.created_at.desc()).all()
    return render_template('admin/customers.html', customers=customers_list)


@admin_bp.route('/requests')
@admin_required
def requests():
    status_filter = request.args.get('status')
    query = ServiceRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    all_requests = query.order_by(ServiceRequest.created_at.desc()).all()
    return render_template('admin/requests.html', requests=all_requests, status_filter=status_filter)


@admin_bp.route('/services', methods=['GET', 'POST'])
@admin_required
def services():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', 'fa-tools').strip()
        description = request.form.get('description', '').strip()
        base_price = float(request.form.get('base_price', 299.0))

        if not name:
            flash('Category name is required.', 'warning')
            return redirect(url_for('admin.services'))

        existing = ServiceCategory.query.filter_by(name=name).first()
        if existing:
            flash('A service category with this name already exists.', 'warning')
            return redirect(url_for('admin.services'))

        new_cat = ServiceCategory(
            name=name,
            icon=icon,
            description=description,
            base_price=base_price,
            is_active=True
        )
        db.session.add(new_cat)
        db.session.commit()
        flash(f'Service category "{name}" added successfully.', 'success')
        return redirect(url_for('admin.services'))

    all_services = ServiceCategory.query.order_by(ServiceCategory.name).all()
    return render_template('admin/services.html', services=all_services)


@admin_bp.route('/services/<int:service_id>/toggle', methods=['POST'])
@admin_required
def toggle_service(service_id):
    cat = db.get_or_404(ServiceCategory, service_id)
    cat.is_active = not cat.is_active
    db.session.commit()
    flash(f'Service category "{cat.name}" is now {"Active" if cat.is_active else "Inactive"}.', 'info')
    return redirect(url_for('admin.services'))


@admin_bp.route('/reviews')
@admin_required
def reviews():
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=all_reviews)


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def delete_review(review_id):
    rev = db.get_or_404(Review, review_id)
    worker_prof = rev.worker.worker_profile if rev.worker else None
    db.session.delete(rev)
    db.session.commit()
    
    if worker_prof:
        worker_prof.update_rating_stats()
        
    flash('Review deleted successfully.', 'info')
    return redirect(url_for('admin.reviews'))
