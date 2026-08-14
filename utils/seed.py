from datetime import datetime, timedelta
from models import db
from models.user import User, WorkerProfile
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.review import Review
from models.notification import Notification

def seed_database():
    """Populates the database with initial categories, demo users, and workers."""
    
    # 1. Create Default Service Categories
    services_data = [
        {"name": "Plumbing", "icon": "fa-faucet-drip", "desc": "Leakage repair, pipe fittings, tap replacement, bathroom sanitary fixes", "price": 299.0},
        {"name": "Electrical", "icon": "fa-bolt", "desc": "Short circuits, fan installation, switchboard repair, MCB wiring", "price": 299.0},
        {"name": "Cleaning", "icon": "fa-broom", "desc": "Deep home cleaning, bathroom sanitization, kitchen degreasing, sofa shampoo", "price": 499.0},
        {"name": "Carpenter", "icon": "fa-hammer", "desc": "Furniture repair, door lock installation, modular wardrobe, woodwork fixes", "price": 349.0},
        {"name": "Painting", "icon": "fa-paint-roller", "desc": "Interior wall painting, touch-ups, waterproof coating, exterior finish", "price": 599.0},
        {"name": "Appliance Repair", "icon": "fa-tv", "desc": "Microwave, geyser, mixer grinder, television and kitchen appliances", "price": 399.0},
        {"name": "AC Repair", "icon": "fa-snowflake", "desc": "AC filter cleaning, gas refill, cooling issues, compressor repair", "price": 549.0},
        {"name": "Washing Machine Repair", "icon": "fa-soap", "desc": "Drum rotation issues, water drainage fault, motor error, PCB repair", "price": 399.0},
        {"name": "Refrigerator Repair", "icon": "fa-cube", "desc": "Defrost issue, compressor replacement, gas leak, thermostat fix", "price": 449.0},
        {"name": "General Maintenance", "icon": "fa-screwdriver-wrench", "desc": "Curtain rod installation, drill and hang, minor fixes, tile repair", "price": 249.0}
    ]

    service_map = {}
    for s_info in services_data:
        existing = ServiceCategory.query.filter_by(name=s_info["name"]).first()
        if not existing:
            cat = ServiceCategory(
                name=s_info["name"],
                icon=s_info["icon"],
                description=s_info["desc"],
                base_price=s_info["price"],
                is_active=True
            )
            db.session.add(cat)
            db.session.flush()
            service_map[s_info["name"]] = cat
        else:
            service_map[s_info["name"]] = existing

    # 2. Create Admin Account
    admin_user = User.query.filter_by(email="admin@example.com").first()
    if not admin_user:
        admin_user = User(
            name="Platform Administrator",
            email="admin@example.com",
            phone="+91 9876543210",
            role="admin",
            status="active"
        )
        admin_user.set_password("Admin@123")
        db.session.add(admin_user)

    # 3. Create Demo Customer Account
    customer_user = User.query.filter_by(email="customer@example.com").first()
    if not customer_user:
        customer_user = User(
            name="Sneha Roy",
            email="customer@example.com",
            phone="+91 9812345678",
            role="customer",
            status="active"
        )
        customer_user.set_password("Customer@123")
        db.session.add(customer_user)

    # 4. Create Demo Workers
    workers_seed = [
        {
            "name": "Rahul Sharma",
            "email": "rahul@example.com",
            "phone": "+91 9700011122",
            "password": "Worker@123",
            "experience": 6,
            "hourly_rate": 350.0,
            "bio": "Certified professional plumber with 6+ years experience in sanitary and pipeline fixtures.",
            "lat": 26.1820,
            "lng": 91.7510,
            "location_name": "Paltan Bazaar, Guwahati",
            "services": ["Plumbing", "General Maintenance"],
            "rating_avg": 4.8,
            "rating_count": 14,
            "total_jobs": 28
        },
        {
            "name": "Amit Das",
            "email": "amit@example.com",
            "phone": "+91 9700022233",
            "password": "Worker@123",
            "experience": 5,
            "hourly_rate": 300.0,
            "bio": "Licensed domestic electrician specialized in short circuits, inverters, and switchboards.",
            "lat": 26.1584,
            "lng": 91.7761,
            "location_name": "GS Road, Guwahati",
            "services": ["Electrical", "Appliance Repair"],
            "rating_avg": 4.9,
            "rating_count": 19,
            "total_jobs": 35
        },
        {
            "name": "Rohit Kalita",
            "email": "rohit@example.com",
            "phone": "+91 9700033344",
            "password": "Worker@123",
            "experience": 4,
            "hourly_rate": 400.0,
            "bio": "Expert deep cleaning specialist with modern scrubbing and sanitization equipment.",
            "lat": 26.1695,
            "lng": 91.7820,
            "location_name": "Zoo Road, Guwahati",
            "services": ["Cleaning", "Painting"],
            "rating_avg": 4.7,
            "rating_count": 11,
            "total_jobs": 22
        },
        {
            "name": "Priya Boro",
            "email": "priya@example.com",
            "phone": "+91 9700044455",
            "password": "Worker@123",
            "experience": 7,
            "hourly_rate": 450.0,
            "bio": "HVAC and cooling systems technician for AC, refrigerators, and washing machines.",
            "lat": 26.1412,
            "lng": 91.7905,
            "location_name": "Dispur Last Gate, Guwahati",
            "services": ["AC Repair", "Washing Machine Repair", "Refrigerator Repair"],
            "rating_avg": 5.0,
            "rating_count": 16,
            "total_jobs": 31
        },
        {
            "name": "Manoj Paul",
            "email": "manoj@example.com",
            "phone": "+91 9700055566",
            "password": "Worker@123",
            "experience": 8,
            "hourly_rate": 350.0,
            "bio": "Master carpenter for modular furniture assembly, door locks, and woodwork fixes.",
            "lat": 26.1555,
            "lng": 91.6625,
            "location_name": "Jalukbari, Guwahati",
            "services": ["Carpenter", "General Maintenance"],
            "rating_avg": 4.8,
            "rating_count": 9,
            "total_jobs": 18
        }
    ]

    worker_users = {}
    for w_data in workers_seed:
        existing_w = User.query.filter_by(email=w_data["email"]).first()
        if not existing_w:
            w_user = User(
                name=w_data["name"],
                email=w_data["email"],
                phone=w_data["phone"],
                role="worker",
                status="active"
            )
            w_user.set_password(w_data["password"])
            db.session.add(w_user)
            db.session.flush()

            w_profile = WorkerProfile(
                user_id=w_user.id,
                experience_years=w_data["experience"],
                hourly_rate=w_data["hourly_rate"],
                bio=w_data["bio"],
                latitude=w_data["lat"],
                longitude=w_data["lng"],
                location_name=w_data["location_name"],
                is_available=True,
                is_approved=True,
                rating_avg=w_data["rating_avg"],
                rating_count=w_data["rating_count"],
                total_jobs_completed=w_data["total_jobs"]
            )
            # Add service relationships
            for s_name in w_data["services"]:
                if s_name in service_map:
                    w_profile.services.append(service_map[s_name])

            db.session.add(w_profile)
            worker_users[w_data["name"]] = w_user
        else:
            worker_users[w_data["name"]] = existing_w

    db.session.commit()

    # 5. Create Sample Past Completed Requests & Reviews for Demo Realism
    if customer_user and "Amit Das" in worker_users:
        amit = worker_users["Amit Das"]
        past_req = ServiceRequest.query.filter_by(customer_id=customer_user.id, title="Ceiling fan sparking sound").first()
        if not past_req:
            elec_serv = service_map.get("Electrical")
            if elec_serv:
                sample_req = ServiceRequest(
                    customer_id=customer_user.id,
                    service_id=elec_serv.id,
                    assigned_worker_id=amit.id,
                    title="Ceiling fan sparking sound",
                    description="Living room fan stopped rotating and made a sparking noise in regulator.",
                    address="Flat 3B, Silver Heights, GS Road, Guwahati",
                    location_name="GS Road, Guwahati",
                    latitude=26.1590,
                    longitude=91.7765,
                    budget=350.0,
                    status="COMPLETED",
                    created_at=datetime.now() - timedelta(days=3, hours=2),
                    accepted_at=datetime.now() - timedelta(days=3, hours=1, minutes=50),
                    started_at=datetime.now() - timedelta(days=3, hours=1, minutes=10),
                    completed_at=datetime.now() - timedelta(days=3, minutes=30)
                )
                db.session.add(sample_req)
                db.session.flush()

                sample_review = Review(
                    request_id=sample_req.id,
                    customer_id=customer_user.id,
                    worker_id=amit.id,
                    rating=5,
                    comment="Amit arrived within 15 minutes and replaced the faulty capacitor quickly. Very polite and professional!",
                    created_at=datetime.now() - timedelta(days=3, minutes=20)
                )
                db.session.add(sample_review)
                db.session.commit()

    print(">> Database seeded successfully with demo data.")
