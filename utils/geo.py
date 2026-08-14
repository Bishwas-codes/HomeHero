import math
from models.user import User, WorkerProfile
from models.request import ServiceRequest

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the earth
    (specified in decimal degrees) using the Haversine formula.
    
    Formula:
      a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
      c = 2 ⋅ atan2( √a, √(1−a) )
      d = R ⋅ c
      where R is earth's radius (mean radius = 6371 km).
    
    Returns distance in kilometers.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 9999.0

    # Convert decimal degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    earth_radius_km = 6371.0
    distance = earth_radius_km * c
    return round(distance, 2)


def get_eligible_workers_for_request(request_obj: ServiceRequest, max_radius_km: float = 15.0):
    """
    Finds active, approved workers who provide the requested service and
    are within the radius of the customer's request location.
    
    Returns: List of tuples (worker_user, worker_profile, distance_km) sorted by distance.
    """
    service_id = request_obj.service_id
    
    # Query all active worker users with approved profiles and availability ON
    workers = (
        User.query.filter_by(role='worker', status='active')
        .join(WorkerProfile)
        .filter(
            WorkerProfile.is_approved == True,
            WorkerProfile.is_available == True
        )
        .all()
    )

    eligible = []
    for worker in workers:
        profile = worker.worker_profile
        if not profile:
            continue
            
        # 1. Verify worker offers this service category
        worker_service_ids = [s.id for s in profile.services]
        if service_id not in worker_service_ids:
            continue

        # 2. Check if worker already has an ongoing active job
        active_job = ServiceRequest.query.filter(
            ServiceRequest.assigned_worker_id == worker.id,
            ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
        ).first()
        if active_job:
            continue

        # 3. Calculate distance using Haversine
        dist_km = haversine_distance(
            request_obj.latitude, request_obj.longitude,
            profile.latitude, profile.longitude
        )

        if dist_km <= max_radius_km:
            eligible.append((worker, profile, dist_km))

    # Sort workers by closest distance first
    eligible.sort(key=lambda x: x[2])
    return eligible


def is_worker_eligible_for_request(worker_user: User, request_obj: ServiceRequest, max_radius_km: float = 15.0) -> tuple[bool, float, str]:
    """
    Checks if a specific worker is eligible to accept a request.
    Returns (is_eligible: bool, distance_km: float, reason: str)
    """
    profile = worker_user.worker_profile
    if not profile or not profile.is_approved:
        return False, 999.0, "Worker profile is not approved by administrator."
    
    if not profile.is_available:
        return False, 999.0, "Worker is currently set to Offline."

    # Check service match
    if request_obj.service_id not in [s.id for s in profile.services]:
        return False, 999.0, f"Worker does not provide {request_obj.service.name} service."

    # Check if worker is already busy
    active_job = ServiceRequest.query.filter(
        ServiceRequest.assigned_worker_id == worker_user.id,
        ServiceRequest.status.in_(['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS'])
    ).first()
    if active_job and active_job.id != request_obj.id:
        return False, 999.0, "Worker already has an active ongoing job."

    # Calculate distance
    dist = haversine_distance(
        request_obj.latitude, request_obj.longitude,
        profile.latitude, profile.longitude
    )

    if dist > max_radius_km:
        return False, dist, f"Location is {dist} km away (exceeds {max_radius_km} km radius)."

    return True, dist, "Eligible"
