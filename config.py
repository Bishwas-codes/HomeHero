import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'homehero-secret-key-super-secure-2026-viva')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'household_app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Matching radius in kilometers for Haversine matching
    DEFAULT_SEARCH_RADIUS_KM = 10.0
    
    # Upload folder for profile photos if uploaded
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4MB max
    
    # Pre-configured demo locations for fast selection during demonstrations
    DEMO_LOCATIONS = [
        {"name": "Paltan Bazaar, Guwahati", "lat": 26.1820, "lng": 91.7510},
        {"name": "GS Road, Guwahati", "lat": 26.1584, "lng": 91.7761},
        {"name": "Zoo Road, Guwahati", "lat": 26.1695, "lng": 91.7820},
        {"name": "Dispur Last Gate, Guwahati", "lat": 26.1412, "lng": 91.7905},
        {"name": "Jalukbari (Gauhati Univ)", "lat": 26.1555, "lng": 91.6625},
        {"name": "Connaught Place, New Delhi", "lat": 28.6315, "lng": 77.2167},
        {"name": "Koramangala, Bengaluru", "lat": 12.9352, "lng": 77.6245},
        {"name": "Andheri West, Mumbai", "lat": 19.1363, "lng": 72.8277},
    ]
