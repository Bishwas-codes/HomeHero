from functools import wraps
from flask import flash, redirect, url_for, abort, request
from flask_login import current_user

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in as a customer to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'customer':
            flash('Access denied. Customer account required.', 'danger')
            return redirect(url_for('index'))
        if current_user.status != 'active':
            flash('Your account has been suspended. Please contact support.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


def worker_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in as a service provider to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'worker':
            flash('Access denied. Worker / Service Provider account required.', 'danger')
            return redirect(url_for('index'))
        if current_user.status != 'active':
            flash('Your account has been suspended. Please contact support.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Admin authentication required.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
