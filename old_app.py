from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    @property
    def password(self):
        raise AttributeError('Password is not readable')

    @password.setter
    def password(self, plaintext):
        self.password_hash = generate_password_hash(plaintext)

    def verify_password(self, plaintext):
        return check_password_hash(self.password_hash, plaintext)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    pickup = db.Column(db.String(10), nullable=False)
    drop = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='Confirmed')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_tables():
    db.create_all()
    # create an admin user if not exists
    if not User.query.filter_by(email='admin@project.local').first():
        admin = User(full_name='Administrator', email='admin@project.local', phone='', is_admin=True)
        admin.password = 'adminpass'
        db.session.add(admin)
        db.session.commit()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        user = User(full_name=full_name, email=email, phone=phone)
        user.password = password
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    booking_count = Booking.query.filter_by(user_id=current_user.id).count()
    return render_template('dashboard.html', bookings_count=booking_count)


@app.route('/vehicles')
def vehicles():
    # static list for demo
    vehicle_list = [
        {'name': 'Toyota Fortuner', 'price': 1900, 'image': 'https://source.unsplash.com/400x300/?toyota,fortuner'},
        {'name': 'BMW X5', 'price': 3200, 'image': 'https://source.unsplash.com/400x300/?bmw,x5'},
        {'name': 'Audi Q7', 'price': 2800, 'image': 'https://source.unsplash.com/400x300/?audi,q7'},
    ]
    return render_template('vehicles.html', vehicles=vehicle_list)


@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    if request.method == 'POST':
        vehicle_name = request.form['vehicle_name']
        date = request.form['date']
        pickup = request.form['pickup']
        drop = request.form['drop']
        new = Booking(user_id=current_user.id, vehicle_name=vehicle_name, date=date, pickup=pickup, drop=drop)
        db.session.add(new)
        db.session.commit()
        flash('Booking confirmed!', 'success')
        return redirect(url_for('mybookings'))
    vehicle_name = request.args.get('car', '')
    return render_template('booking.html', vehicle_name=vehicle_name)


@app.route('/mybookings')
@login_required
def mybookings():
    bks = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('mybookings.html', bookings=bks)


@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    user_count = User.query.count()
    booking_count = Booking.query.count()
    return render_template('admin.html', user_count=user_count, booking_count=booking_count)


if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run(debug=True)
