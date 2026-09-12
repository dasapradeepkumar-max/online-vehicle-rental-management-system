from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_code = db.Column(db.String(20), unique=True, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)  # not used when OTP
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email or self.phone}>"
    
    def set_password(self, password):
        """Securely hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def display_id(self):
        return self.user_code or f'USR{self.id:03d}'

    @staticmethod
    def next_user_code():
        """Allocate the next permanent customer ID without counting admins."""
        codes = db.session.query(User.user_code).filter(
            User.is_admin.is_(False), User.user_code.like('USR%')
        ).all()
        numbers = [int(code[0][3:]) for code in codes if code[0] and code[0][3:].isdigit()]
        return f'USR{max(numbers, default=0) + 1:03d}'


class LoginEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    logged_in_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    user = db.relationship('User', backref=db.backref('login_events', lazy='dynamic'))


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Open', nullable=False, index=True)
    admin_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('issues', lazy='dynamic'))
    booking = db.relationship('Booking', backref=db.backref('issues', lazy='dynamic'))


class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __init__(self, user_id, code, ttl=5):
        self.user_id = user_id
        self.code = code
        self.expires_at = datetime.utcnow() + timedelta(minutes=ttl)

    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # car or bike
    price_per_day = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='available')
    image = db.Column(db.String(255))
    location = db.Column(db.String(255))
    vehicle_number = db.Column(db.String(30), unique=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Confirmed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pickup_time = db.Column(db.DateTime)
    return_time = db.Column(db.DateTime)
    payment_status = db.Column(db.String(20), default='Paid')
    payment_reference = db.Column(db.String(100))
    cancellation_reason = db.Column(db.String(255))
    cancellation_fee = db.Column(db.Float, default=0.0)
    refund_amount = db.Column(db.Float, default=0.0)
    refund_status = db.Column(db.String(20), default='Not applicable')
    cancelled_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('ix_booking_user_status', 'user_id', 'status'),
        db.Index('ix_booking_vehicle_dates', 'vehicle_id', 'start_date', 'end_date'),
        db.Index('ix_booking_payment_status', 'payment_status'),
    )

    user = db.relationship('User')
    vehicle = db.relationship('Vehicle')
