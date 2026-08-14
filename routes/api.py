from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user
from models import db
from models.request import ServiceRequest
from models.review import Review
from models.notification import Notification
from utils.geo import haversine_distance

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/request-status/<int:request_id>')
def get_request_status(request_id):
    """
    Live Polling Endpoint for Customer tracking screen.
    Returns request status, assigned worker info, and timestamps.
    """
    req_obj = db.session.get(ServiceRequest, request_id)
    if not req_obj:
        return jsonify({'error': 'Request not found'}), 404

    # Security check: Only customer, assigned worker, or admin can query status
    if current_user.is_authenticated:
        if current_user.role == 'customer' and req_obj.customer_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

    worker_info = None
    if req_obj.assigned_worker_id and req_obj.worker:
        w_user = req_obj.worker
        w_prof = w_user.worker_profile
        
        # Calculate distance
        dist = None
        if w_prof:
            dist = haversine_distance(req_obj.latitude, req_obj.longitude, w_prof.latitude, w_prof.longitude)

        worker_info = {
            'id': w_user.id,
            'name': w_user.name,
            'phone': w_user.phone,
            'rating_avg': w_prof.rating_avg if w_prof else 5.0,
            'rating_count': w_prof.rating_count if w_prof else 0,
            'experience_years': w_prof.experience_years if w_prof else 1,
            'distance_km': dist
        }

    has_reviewed = False
    if req_obj.status == 'COMPLETED':
        has_reviewed = Review.query.filter_by(request_id=req_obj.id).first() is not None

    return jsonify({
        'id': req_obj.id,
        'status': req_obj.status,
        'title': req_obj.title,
        'service_name': req_obj.service.name if req_obj.service else 'Service',
        'created_at': req_obj.created_at.strftime('%I:%M %p') if req_obj.created_at else None,
        'accepted_at': req_obj.accepted_at.strftime('%I:%M %p') if req_obj.accepted_at else None,
        'started_at': req_obj.started_at.strftime('%I:%M %p') if req_obj.started_at else None,
        'completed_at': req_obj.completed_at.strftime('%I:%M %p') if req_obj.completed_at else None,
        'worker': worker_info,
        'has_reviewed': has_reviewed,
        'cancellation_reason': req_obj.cancellation_reason
    })


@api_bp.route('/worker/incoming-requests')
def get_worker_incoming_requests():
    """
    Live Polling Endpoint for Worker Dashboard radar.
    Returns list of nearby eligible unassigned requests.
    """
    if not current_user.is_authenticated or current_user.role != 'worker':
        return jsonify({'requests': []})

    profile = current_user.worker_profile
    if not profile or not profile.is_available or not profile.is_approved:
        return jsonify({'requests': []})

    # If worker already has an active job, do not show incoming requests
    active_job = ServiceRequest.query.filter(
        ServiceRequest.assigned_worker_id == current_user.id,
        ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
    ).first()

    if active_job:
        return jsonify({'requests': [], 'has_active_job': True})

    worker_service_ids = [s.id for s in profile.services]
    max_radius = current_app.config.get('DEFAULT_SEARCH_RADIUS_KM', 15.0)

    candidates = ServiceRequest.query.filter(
        ServiceRequest.status == 'SEARCHING',
        ServiceRequest.service_id.in_(worker_service_ids)
    ).order_by(ServiceRequest.created_at.desc()).all()

    requests_data = []
    for req in candidates:
        dist_km = haversine_distance(
            req.latitude, req.longitude,
            profile.latitude, profile.longitude
        )

        if dist_km <= max_radius:
            requests_data.append({
                'id': req.id,
                'service_name': req.service.name,
                'title': req.title,
                'description': req.description[:100] + ('...' if len(req.description) > 100 else ''),
                'location_name': req.location_name or 'Nearby Location',
                'distance_km': dist_km,
                'budget': req.budget or req.service.base_price,
                'created_time': req.created_at.strftime('%I:%M %p')
            })

    requests_data.sort(key=lambda x: x['distance_km'])
    return jsonify({'requests': requests_data, 'has_active_job': False})


@api_bp.route('/calculate-distance')
def calculate_distance_api():
    """Helper to calculate distance between two pairs of coordinates"""
    lat1 = request.args.get('lat1', type=float)
    lon1 = request.args.get('lon1', type=float)
    lat2 = request.args.get('lat2', type=float)
    lon2 = request.args.get('lon2', type=float)

    if None in (lat1, lon1, lat2, lon2):
        return jsonify({'error': 'Missing coordinates'}), 400

    dist = haversine_distance(lat1, lon1, lat2, lon2)
    return jsonify({'distance_km': dist})


@api_bp.route('/notifications/unread')
def get_unread_notifications():
    if not current_user.is_authenticated:
        return jsonify({'count': 0, 'notifications': []})

    notifs = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()

    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'link': n.link,
        'created_at': n.created_at.strftime('%I:%M %p')
    } for n in notifs]

    return jsonify({'count': len(data), 'notifications': data})
