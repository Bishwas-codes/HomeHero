import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
from models import db
from models.user import User
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.review import Review
from utils.seed import seed_database

class TestE2EConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class HomeHeroE2EWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestE2EConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        seed_database()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_full_demo_workflow(self):
        print("\nStep 1: Login as customer...")
        login_res = self.client.post('/auth/login', data={
            'email': 'customer@example.com',
            'password': 'Customer@123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back, Sneha Roy', login_res.data)

        print("Step 2: Customer books plumbing service...")
        plumbing = ServiceCategory.query.filter_by(name='Plumbing').first()
        book_res = self.client.post('/customer/book', data={
            'service_id': plumbing.id,
            'title': 'Kitchen tap leaking continuously',
            'description': 'Water leaking from main kitchen sink faucet valve',
            'address': 'Flat 4B, Hillview Apartments, Paltan Bazaar, Guwahati',
            'location_name': 'Paltan Bazaar, Guwahati',
            'latitude': 26.1820,
            'longitude': 91.7510,
            'budget': 350.0
        }, follow_redirects=True)
        self.assertEqual(book_res.status_code, 200)

        req = ServiceRequest.query.filter_by(title='Kitchen tap leaking continuously').first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, 'SEARCHING')

        print("Step 3: Customer logout...")
        self.client.get('/auth/logout', follow_redirects=True)

        print("Step 4: Worker login...")
        w_login = self.client.post('/auth/login', data={
            'email': 'rahul@example.com',
            'password': 'Worker@123'
        }, follow_redirects=True)
        self.assertEqual(w_login.status_code, 200)
        self.assertIn(b'Nearby Job Radar', w_login.data)

        print("Step 5: Worker accepts request...")
        accept_res = self.client.post(f'/worker/accept-request/{req.id}', follow_redirects=True)
        self.assertEqual(accept_res.status_code, 200)
        self.assertIn(b'Customer Details Unlocked', accept_res.data)
        self.assertIn(b'Flat 4B, Hillview Apartments', accept_res.data)

        print("Step 6: Worker progresses status...")
        step1 = self.client.post(f'/worker/update-status/{req.id}/ON_THE_WAY', follow_redirects=True)
        self.assertEqual(step1.status_code, 200)
        self.assertIn(b'On The Way', step1.data)

        step2 = self.client.post(f'/worker/update-status/{req.id}/IN_PROGRESS', follow_redirects=True)
        self.assertEqual(step2.status_code, 200)
        self.assertIn(b'In Progress', step2.data)

        step3 = self.client.post(f'/worker/update-status/{req.id}/COMPLETED', follow_redirects=True)
        self.assertEqual(step3.status_code, 200)

        db.session.refresh(req)
        self.assertEqual(req.status, 'COMPLETED')

        print("Step 7: Worker logout & Customer reviews...")
        self.client.get('/auth/logout', follow_redirects=True)

        self.client.post('/auth/login', data={
            'email': 'customer@example.com',
            'password': 'Customer@123'
        }, follow_redirects=True)

        rev_res = self.client.post(f'/customer/request/{req.id}/review', data={
            'rating': 5,
            'comment': 'Rahul was extremely professional and fixed the tap in no time!'
        }, follow_redirects=True)
        self.assertEqual(rev_res.status_code, 200)
        self.assertIn(b'Your review and rating have been submitted successfully', rev_res.data)

        print("Step 8: Admin dashboard verification...")
        self.client.get('/auth/logout', follow_redirects=True)
        admin_login = self.client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)
        self.assertIn(b'Platform Operations Dashboard', admin_login.data)
        print(">> All E2E workflow steps verified successfully!")


if __name__ == '__main__':
    unittest.main()
