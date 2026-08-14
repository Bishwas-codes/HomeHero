from datetime import datetime
from . import db

# Association Table for Many-to-Many relationship between WorkerProfile and ServiceCategory
worker_services = db.Table(
    'worker_services',
    db.Column('worker_profile_id', db.Integer, db.ForeignKey('worker_profiles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), primary_key=True)
)

class ServiceCategory(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), default='fa-tools')
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Float, default=299.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    requests = db.relationship('ServiceRequest', backref='service', lazy='dynamic')

    def __repr__(self):
        return f"<ServiceCategory {self.name}>"
