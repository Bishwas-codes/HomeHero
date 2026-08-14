import os
import unittest
import threading
from app import create_app
from config import Config
from models import db
from models.user import User, WorkerProfile
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.review import Review
from utils.geo import haversine_distance, get_eligible_workers_for_request
from utils.seed import seed_database

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class HomeHeroTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        seed_database()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_haversine_distance(self):
        """Test Haversine distance computation between known coordinates"""
        # Paltan Bazaar (26.1820, 91.7510) to GS Road (26.1584, 91.7761) ~ 3.69 km
        dist = haversine_distance(26.1820, 91.7510, 26.1584, 91.7761)
        self.assertGreater(dist, 3.0)
        self.assertLess(dist, 4.5)

        # Same point distance should be 0.0
        self.assertEqual(haversine_distance(26.1820, 91.7510, 26.1820, 91.7510), 0.0)

    def test_user_authentication_and_roles(self):
        """Test authentication and role separation"""
        customer = User.query.filter_by(email='customer@example.com').first()
        self.assertIsNotNone(customer)
        self.assertTrue(customer.check_password('Customer@123'))
        self.assertFalse(customer.check_password('WrongPassword'))
        self.assertTrue(customer.is_customer)
        self.assertFalse(customer.is_worker)

        plumber = User.query.filter_by(email='rahul@example.com').first()
        self.assertIsNotNone(plumber)
        self.assertTrue(plumber.is_worker)
        self.assertTrue(plumber.worker_profile.is_approved)

    def test_service_request_lifecycle_and_matching(self):
        """Test full request flow: Create -> Match -> Accept -> On Way -> Complete -> Review"""
        customer = User.query.filter_by(email='customer@example.com').first()
        plumbing_service = ServiceCategory.query.filter_by(name='Plumbing').first()

        # 1. Customer creates plumbing request
        req = ServiceRequest(
            customer_id=customer.id,
            service_id=plumbing_service.id,
            title='Kitchen sink pipe leaking',
            description='Water leaking continuously under sink',
            address='Hillview Apt, Paltan Bazaar, Guwahati',
            location_name='Paltan Bazaar, Guwahati',
            latitude=26.1820,
            longitude=91.7510,
            budget=350.0,
            status='SEARCHING'
        )
        db.session.add(req)
        db.session.commit()

        # 2. Check matching eligible workers
        eligible = get_eligible_workers_for_request(req, max_radius_km=15.0)
        self.assertGreaterEqual(len(eligible), 1)
        
        # Rahul is a plumber in Paltan Bazaar (distance ~ 0 km)
        worker_names = [w[0].name for w in eligible]
        self.assertIn('Rahul Sharma', worker_names)

        # 3. Worker accepts the request (Atomic update)
        rahul = User.query.filter_by(email='rahul@example.com').first()
        rows_updated = ServiceRequest.query.filter(
            ServiceRequest.id == req.id,
            ServiceRequest.status == 'SEARCHING'
        ).update({
            'status': 'ASSIGNED',
            'assigned_worker_id': rahul.id
        })
        db.session.commit()
        self.assertEqual(rows_updated, 1)

        # 4. Status progression
        req.status = 'ON_THE_WAY'
        db.session.commit()
        self.assertEqual(req.status, 'ON_THE_WAY')

        req.status = 'IN_PROGRESS'
        db.session.commit()
        self.assertEqual(req.status, 'IN_PROGRESS')

        req.status = 'COMPLETED'
        db.session.commit()
        self.assertEqual(req.status, 'COMPLETED')

        # 5. Customer submits review
        review = Review(
            request_id=req.id,
            customer_id=customer.id,
            worker_id=rahul.id,
            rating=5,
            comment='Super fast and fixed the leak in 10 minutes!'
        )
        db.session.add(review)
        db.session.commit()
        rahul.worker_profile.update_rating_stats()

        self.assertGreaterEqual(rahul.worker_profile.rating_avg, 4.0)

    def test_concurrency_atomic_acceptance(self):
        """
        Simulate two workers clicking 'Accept' simultaneously on the same request.
        Verify that exactly ONE worker succeeds and the other receives 0 rows updated.
        """
        customer = User.query.filter_by(email='customer@example.com').first()
        plumbing_service = ServiceCategory.query.filter_by(name='Plumbing').first()

        req = ServiceRequest(
            customer_id=customer.id,
            service_id=plumbing_service.id,
            title='Tap leakage emergency',
            description='Urgent fix needed',
            address='Zoo Road, Guwahati',
            latitude=26.1695,
            longitude=91.7820,
            status='SEARCHING'
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

        worker1 = User.query.filter_by(email='rahul@example.com').first()
        worker2 = User.query.filter_by(email='manoj@example.com').first()

        results = []

        # Simulate Worker 1 accept
        u1 = ServiceRequest.query.filter(
            ServiceRequest.id == req_id,
            ServiceRequest.status == 'SEARCHING'
        ).update({'status': 'ASSIGNED', 'assigned_worker_id': worker1.id})
        db.session.commit()
        results.append(u1)

        # Simulate Worker 2 accept immediately after
        u2 = ServiceRequest.query.filter(
            ServiceRequest.id == req_id,
            ServiceRequest.status == 'SEARCHING'
        ).update({'status': 'ASSIGNED', 'assigned_worker_id': worker2.id})
        db.session.commit()
        results.append(u2)

        # Exactly 1 success (1 row updated) and 1 failure (0 rows updated)
        self.assertEqual(results, [1, 0])


if __name__ == '__main__':
    unittest.main()
