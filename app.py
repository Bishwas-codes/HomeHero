import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
from config import Config
from models import db
from models.user import User
from models.service import ServiceCategory
from models.request import ServiceRequest
from models.notification import Notification

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance and upload directories exist
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize SQLAlchemy
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.customer import customer_bp
    from routes.worker import worker_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Context processors for all templates
    @app.context_processor
    def inject_global_data():
        unread_notifs_count = 0
        if current_user.is_authenticated:
            unread_notifs_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        return {
            'now': datetime.now(),
            'app_name': 'HomeHero',
            'unread_notifications_count': unread_notifs_count,
            'demo_locations': app.config.get('DEMO_LOCATIONS', [])
        }

    # Public Landing Page Route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'customer':
                return redirect(url_for('customer.dashboard'))
            elif current_user.role == 'worker':
                return redirect(url_for('worker.dashboard'))
            elif current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))

        categories = ServiceCategory.query.filter_by(is_active=True).all()
        # In case DB is empty yet
        if not categories:
            categories = []

        return render_template('index.html', categories=categories)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Auto-initialize DB and Seed data if first run
    with app.app_context():
        db.create_all()
        from utils.seed import seed_database
        if not ServiceCategory.query.first():
            print(">> First run detected. Auto-seeding database...")
            seed_database()

    # CLI Commands
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database."""
        db.create_all()
        print('Initialized database tables.')

    @app.cli.command('seed-db')
    def seed_db_command():
        """Seed demo data."""
        from utils.seed import seed_database
        seed_database()
        print('Database populated with demo accounts and sample services.')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
