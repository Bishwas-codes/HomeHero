from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer') # 'customer', 'worker', 'admin'
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'suspended'
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    worker_profile = db.relationship('WorkerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    customer_requests = db.relationship('ServiceRequest', backref='customer', foreign_keys='ServiceRequest.customer_id', lazy='dynamic')
    assigned_requests = db.relationship('ServiceRequest', backref='worker', foreign_keys='ServiceRequest.assigned_worker_id', lazy='dynamic')
    reviews_written = db.relationship('Review', backref='customer', foreign_keys='Review.customer_id', lazy='dynamic')
    reviews_received = db.relationship('Review', backref='worker', foreign_keys='Review.worker_id', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_worker(self):
        return self.role == 'worker'

    @property
    def is_customer(self):
        return self.role == 'customer'

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class WorkerProfile(db.Model):
    __tablename__ = 'worker_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    experience_years = db.Column(db.Integer, default=1)
    hourly_rate = db.Column(db.Float, default=300.0)
    bio = db.Column(db.Text, nullable=True)
    profile_photo = db.Column(db.String(255), default='default_avatar.png')
    
    # Location coordinates for Haversine matching
    latitude = db.Column(db.Float, nullable=False, default=26.1820)
    longitude = db.Column(db.Float, nullable=False, default=91.7510)
    location_name = db.Column(db.String(150), default='Paltan Bazaar, Guwahati')
    
    is_available = db.Column(db.Boolean, default=True) # Online/Offline switch
    is_approved = db.Column(db.Boolean, default=True)   # Admin approval status
    
    # Aggregated rating cache
    rating_avg = db.Column(db.Float, default=5.0)
    rating_count = db.Column(db.Integer, default=0)
    total_jobs_completed = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Many-to-many with ServiceCategory
    services = db.relationship('ServiceCategory', secondary='worker_services', backref=db.backref('workers', lazy='dynamic'))

    def update_rating_stats(self):
        """Recalculate average rating from customer reviews"""
        reviews = self.user.reviews_received.all()
        if reviews:
            self.rating_count = len(reviews)
            self.rating_avg = round(sum(r.rating for r in reviews) / self.rating_count, 1)
        else:
            self.rating_avg = 5.0
            self.rating_count = 0
        db.session.commit()

    def __repr__(self):
        return f"<WorkerProfile User={self.user_id} Approved={self.is_approved} Available={self.is_available}>"
