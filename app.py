from flask import Flask, render_template
from flask_login import LoginManager
from flask_socketio import SocketIO

from config import Config
from models import db, User, Vehicle
from sqlalchemy import inspect, text

# blueprints
from routes.auth import auth_bp
from routes.vehicles import vehicles_bp
from routes.bookings import bookings_bp
from routes.admin import admin_bp
from routes.public_routes import public_bp

app = Flask(__name__)
app.config.from_object(Config)

# extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
socketio = SocketIO(app, cors_allowed_origins="*")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_tables():
    db.create_all()
    _upgrade_tracking_schema()

    # Create admin user if not exists
    admin = User.query.filter_by(email='admin@vehiclehub.local').first()
    if not admin:
        admin = User(full_name='Administrator', email='admin@vehiclehub.local', phone='', is_admin=True, is_verified=True)
        db.session.add(admin)
        db.session.flush()
        admin.user_code = 'ADMIN001'
    elif admin.user_code and admin.user_code.startswith('USR'):
        admin.user_code = f'ADMIN{admin.id:03d}'

    # Add sample vehicles if none exist
    if Vehicle.query.count() == 0:
        sample_vehicles = [
            # Cars
            {
                'name': 'Toyota Fortuner',
                'type': 'car',
                'price_per_day': 1900,
                'location': 'Mumbai',
                'image': 'https://images.unsplash.com/photo-1672329468664-f9a960f14003?w=800&q=80'
            },
            {
                'name': 'BMW X5',
                'type': 'car',
                'price_per_day': 3200,
                'location': 'Delhi',
                'image': 'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800&q=80'
            },
            {
                'name': 'Honda City',
                'type': 'car',
                'price_per_day': 900,
                'location': 'Bangalore',
                'image': 'https://images.unsplash.com/photo-1590362891991-f776e747a588?w=800&q=80'
            },
            {
                'name': 'Hyundai Creta',
                'type': 'car',
                'price_per_day': 1200,
                'location': 'Hyderabad',
                'image': 'https://images.unsplash.com/photo-1616788494672-ec7ca25fdda9?w=800&q=80'
            },
            {
                'name': 'Mercedes C-Class',
                'type': 'car',
                'price_per_day': 4500,
                'location': 'Pune',
                'image': 'https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=800&q=80'
            },
            {
                'name': 'Tata Nexon EV',
                'type': 'car',
                'price_per_day': 1400,
                'location': 'Chennai',
                'image': 'https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=800&q=80'
            },
            # Bikes
            {
                'name': 'Royal Enfield Classic 350',
                'type': 'bike',
                'price_per_day': 700,
                'location': 'Goa',
                'image': 'https://images.unsplash.com/photo-1558981285-6f0c68243e90?w=800&q=80'
            },
            {
                'name': 'Yamaha R15',
                'type': 'bike',
                'price_per_day': 600,
                'location': 'Mumbai',
                'image': 'https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?w=800&q=80'
            },
            {
                'name': 'Honda Activa',
                'type': 'bike',
                'price_per_day': 250,
                'location': 'Bangalore',
                'image': 'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&q=80'
            },
            {
                'name': 'KTM Duke 390',
                'type': 'bike',
                'price_per_day': 850,
                'location': 'Delhi',
                'image': 'https://images.unsplash.com/photo-1609630875171-b1321377ee65?w=800&q=80'
            },
        ]
        for v_data in sample_vehicles:
            db.session.add(Vehicle(**v_data))

    db.session.flush()
    for user in User.query.filter(User.user_code.is_(None)).all():
        user.user_code = User.next_user_code() if not user.is_admin else f'ADMIN{user.id:03d}'
    for vehicle in Vehicle.query.filter(Vehicle.vehicle_number.is_(None)).all():
        vehicle.vehicle_number = f'VH-{vehicle.id:04d}'
    db.session.commit()


def _upgrade_tracking_schema():
    """Add tracking columns to existing SQLite installs without a migration dependency."""
    inspector = inspect(db.engine)
    additions = {
        'user': {
            'user_code': 'VARCHAR(20)',
        },
        'vehicle': {
            'vehicle_number': 'VARCHAR(30)',
        },
        'booking': {
            'pickup_time': 'DATETIME',
            'return_time': 'DATETIME',
            'payment_status': "VARCHAR(20) DEFAULT 'Paid'",
            'payment_reference': 'VARCHAR(100)',
            'cancellation_reason': 'VARCHAR(255)',
            'cancellation_fee': 'FLOAT DEFAULT 0',
            'refund_amount': 'FLOAT DEFAULT 0',
            'refund_status': "VARCHAR(20) DEFAULT 'Not applicable'",
            'cancelled_at': 'DATETIME',
        },
    }
    for table, columns in additions.items():
        existing = {column['name'] for column in inspector.get_columns(table)}
        for name, definition in columns.items():
            if name not in existing:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
    index_definitions = [
        ('user', 'ix_user_user_code', 'CREATE UNIQUE INDEX ix_user_user_code ON user (user_code)'),
        ('vehicle', 'ix_vehicle_vehicle_number', 'CREATE UNIQUE INDEX ix_vehicle_vehicle_number ON vehicle (vehicle_number)'),
        ('booking', 'ix_booking_user_status', 'CREATE INDEX ix_booking_user_status ON booking (user_id, status)'),
        ('booking', 'ix_booking_vehicle_dates', 'CREATE INDEX ix_booking_vehicle_dates ON booking (vehicle_id, start_date, end_date)'),
        ('booking', 'ix_booking_payment_status', 'CREATE INDEX ix_booking_payment_status ON booking (payment_status)'),
    ]
    existing_indexes = {
        table: {index['name'] for index in inspect(db.engine).get_indexes(table)}
        for table in ('user', 'vehicle', 'booking')
    }
    for table, name, statement in index_definitions:
        if name not in existing_indexes[table]:
            db.session.execute(text(statement))


# register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(vehicles_bp)
app.register_blueprint(bookings_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(public_bp)

@app.route('/')
def index():
    return render_template('index.html')

# ─── Real-time Socket.IO Event Handlers ──────────────────────────────────────
active_users = {}

@socketio.on('connect')
def handle_connect():
    print('✓ Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('✗ Client disconnected')

@socketio.on('user_online')
def handle_user_online(data):
    user_id = data.get('user_id')
    if user_id:
        active_users[str(user_id)] = True
    socketio.emit('user_activity', {'count': len(active_users)})

@socketio.on('user_offline')
def handle_user_offline(data):
    user_id = str(data.get('user_id', ''))
    active_users.pop(user_id, None)
    socketio.emit('user_activity', {'count': len(active_users)})


if __name__ == '__main__':
    with app.app_context():
        create_tables()
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
