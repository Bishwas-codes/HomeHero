from datetime import datetime
from . import db

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'

    id = db.Column(db.Integer, primary_key=True)
    
    # Customer requesting the service
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Service requested
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    
    # Worker assigned (nullable until a worker accepts)
    assigned_worker_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Request details
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.Text, nullable=False)
    location_name = db.Column(db.String(150), nullable=True)
    
    # Customer coordinates for Haversine matching
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    budget = db.Column(db.Float, nullable=True)
    
    # Request Status Lifecycle:
    # SEARCHING -> ASSIGNED -> ON_THE_WAY -> IN_PROGRESS -> COMPLETED (or CANCELLED)
    status = db.Column(db.String(30), default='SEARCHING', nullable=False, index=True)
    
    # Lifecycle Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    accepted_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.String(255), nullable=True)

    # Relationships
    review = db.relationship('Review', backref='request', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='request', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_pending_worker(self):
        return self.status == 'SEARCHING'

    @property
    def is_active_job(self):
        return self.status in ['ASSIGNED', 'ON_THE_WAY', 'IN_PROGRESS']

    @property
    def is_finished(self):
        return self.status in ['COMPLETED', 'CANCELLED']

    def status_badge_class(self):
        mapping = {
            'SEARCHING': 'bg-warning text-dark',
            'ASSIGNED': 'bg-info text-dark',
            'ON_THE_WAY': 'bg-primary text-white',
            'IN_PROGRESS': 'bg-info text-white',
            'COMPLETED': 'bg-success text-white',
            'CANCELLED': 'bg-danger text-white'
        }
        return mapping.get(self.status, 'bg-secondary text-white')

    def __repr__(self):
        return f"<ServiceRequest #{self.id} {self.status} Customer={self.customer_id}>"
