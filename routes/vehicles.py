from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Vehicle, Booking
from datetime import datetime
from functools import wraps

vehicles_bp = Blueprint('vehicles', __name__)


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapped


# ─── Public page route ───────────────────────────────────────────────────────

@vehicles_bp.route('/vehicles')
@login_required
def list_vehicles():
    from flask import render_template
    return render_template('vehicles.html')


# ─── API: List / filter vehicles ─────────────────────────────────────────────

@vehicles_bp.route('/api/vehicles', methods=['GET'])
def api_list_vehicles():
    """
    GET /api/vehicles?type=car|bike&location=...&min_price=...&max_price=...&search=...
    Returns all vehicles with real-time availability based on today's date.
    """
    try:
        query = Vehicle.query

        v_type = request.args.get('type', '').strip().lower()
        if v_type in ('car', 'bike'):
            query = query.filter_by(type=v_type)

        location = request.args.get('location', '').strip()
        if location:
            query = query.filter(Vehicle.location.ilike(f'%{location}%'))

        search = request.args.get('search', '').strip()
        if search:
            query = query.filter(Vehicle.name.ilike(f'%{search}%'))

        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        if min_price is not None:
            query = query.filter(Vehicle.price_per_day >= min_price)
        if max_price is not None:
            query = query.filter(Vehicle.price_per_day <= max_price)

        vehicles = query.all()
        today = datetime.now().date()

        result = []
        for v in vehicles:
            active = Booking.query.filter(
                Booking.vehicle_id == v.id,
                Booking.start_date <= today,
                Booking.end_date >= today,
                Booking.status == 'Confirmed'
            ).first()
            # Determine status: Manual override (maintenance, etc) takes priority
            # If manual status is 'booked' or 'maintenance', use it.
            # Otherwise, check for active calendar bookings.
            display_status = v.status if v.status != 'available' else ('booked' if active else 'available')
            
            result.append({
                'id': v.id,
                'name': v.name,
                'vehicle_number': v.vehicle_number or f'VH-{v.id:04d}',
                'type': v.type,
                'price_per_day': v.price_per_day,
                'status': display_status,
                'image': v.image or '',
                'location': v.location or 'City Centre',
                'fuel': getattr(v, 'fuel', 'Petrol'),
                'seats': getattr(v, 'seats', 5),
                'description': getattr(v, 'description', 'Premium vehicle for rent'),
            })

        return jsonify(result)
    except Exception as e:
        print(f'[ERROR] api_list_vehicles: {e}')
        return jsonify({'error': 'Failed to fetch vehicles'}), 500


# ─── API: Vehicle detail ──────────────────────────────────────────────────────

@vehicles_bp.route('/api/vehicles/<int:vehicle_id>', methods=['GET'])
def api_vehicle_detail(vehicle_id):
    try:
        v = Vehicle.query.get_or_404(vehicle_id)
        today = datetime.now().date()
        active = Booking.query.filter(
            Booking.vehicle_id == vehicle_id,
            Booking.start_date <= today,
            Booking.end_date >= today,
            Booking.status == 'Confirmed'
        ).first()
        display_status = v.status if v.status != 'available' else ('booked' if active else 'available')
        return jsonify({
            'id': v.id,
            'name': v.name,
            'vehicle_number': v.vehicle_number or f'VH-{v.id:04d}',
            'type': v.type,
            'price_per_day': v.price_per_day,
            'status': display_status,
            'image': v.image or '',
            'location': v.location or 'City Centre',
            'fuel': getattr(v, 'fuel', 'Petrol'),
            'seats': getattr(v, 'seats', 5),
            'description': getattr(v, 'description', 'Premium vehicle for rent'),
        })
    except Exception as e:
        print(f'[ERROR] api_vehicle_detail: {e}')
        return jsonify({'error': 'Vehicle not found'}), 404


# ─── API: Admin CRUD ──────────────────────────────────────────────────────────

@vehicles_bp.route('/api/admin/vehicles', methods=['POST'])
@login_required
@admin_required
def api_add_vehicle():
    data = request.get_json() or {}
    required = ['name', 'type', 'price_per_day']
    for f in required:
        if not data.get(f):
            return jsonify({'message': f'Field {f} is required'}), 400
    v = Vehicle(
        name=data['name'],
        type=data['type'],
        price_per_day=float(data['price_per_day']),
        location=data.get('location', 'City Centre'),
        image=data.get('image', ''),
        status='available'
    )
    db.session.add(v)
    db.session.commit()
    try:
        from app import socketio
        socketio.emit('vehicle_added', {'id': v.id, 'name': v.name})
    except Exception:
        pass
    return jsonify({'message': 'Vehicle added', 'id': v.id}), 201


@vehicles_bp.route('/api/admin/vehicles/<int:vehicle_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json() or {}
    for field in ('name', 'type', 'location', 'image', 'status'):
        if field in data:
            setattr(v, field, data[field])
    if 'price_per_day' in data:
        v.price_per_day = float(data['price_per_day'])
    db.session.commit()
    try:
        from app import socketio
        socketio.emit('vehicle_status_update', {'id': v.id, 'status': v.status})
    except Exception:
        pass
    return jsonify({'message': 'Vehicle updated'})


@vehicles_bp.route('/api/admin/vehicles/<int:vehicle_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(v)
    db.session.commit()
    return jsonify({'message': 'Vehicle deleted'})
