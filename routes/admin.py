from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, User, Booking, Vehicle
from datetime import datetime, date, timedelta
from functools import wraps
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapped


# ─── Admin Page Route ─────────────────────────────────────────────────────────

@admin_bp.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        from flask import redirect, url_for, flash
        flash('Access denied', 'danger')
        return redirect(url_for('auth.dashboard'))
    return render_template('admin.html')


# ─── API: Admin Dashboard Stats ───────────────────────────────────────────────

@admin_bp.route('/api/admin/dashboard', methods=['GET'])
@login_required
@admin_required
def api_admin_dashboard():
    try:
        today = date.today()

        total_users = User.query.filter_by(is_admin=False).count()
        total_vehicles = Vehicle.query.count()
        available_vehicles = Vehicle.query.filter_by(status='available').count()
        total_bookings = Booking.query.count()

        # Revenue
        confirmed_bookings = Booking.query.filter(
            Booking.status.in_(['Confirmed', 'Completed'])
        ).all()
        total_revenue = sum(b.total_price for b in confirmed_bookings)

        # Active rentals today
        active_rentals = Booking.query.filter(
            Booking.start_date <= today,
            Booking.end_date >= today,
            Booking.status == 'Confirmed'
        ).count()

        # Monthly revenue (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        monthly_revenue = db.session.query(func.sum(Booking.total_price)).filter(
            Booking.created_at >= thirty_days_ago,
            Booking.status.in_(['Confirmed', 'Completed'])
        ).scalar() or 0

        # Monthly booking chart (last 6 months)
        monthly_chart = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=30 * i))
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            count = Booking.query.filter(
                Booking.created_at >= datetime.combine(month_start, datetime.min.time()),
                Booking.created_at <= datetime.combine(month_end, datetime.max.time()),
                Booking.status.in_(['Confirmed', 'Completed'])
            ).count()
            revenue = db.session.query(func.sum(Booking.total_price)).filter(
                Booking.created_at >= datetime.combine(month_start, datetime.min.time()),
                Booking.created_at <= datetime.combine(month_end, datetime.max.time()),
                Booking.status.in_(['Confirmed', 'Completed'])
            ).scalar() or 0
            monthly_chart.append({
                'month': month_start.strftime('%b %Y'),
                'bookings': count,
                'revenue': revenue
            })

        # Vehicle type distribution
        car_count = Vehicle.query.filter_by(type='car').count()
        bike_count = Vehicle.query.filter_by(type='bike').count()

        return jsonify({
            'stats': {
                'total_users': total_users,
                'total_vehicles': total_vehicles,
                'available_vehicles': available_vehicles,
                'total_bookings': total_bookings,
                'total_revenue': total_revenue,
                'active_rentals': active_rentals,
                'monthly_revenue': monthly_revenue,
            },
            'charts': {
                'monthly': monthly_chart,
                'vehicle_types': {'cars': car_count, 'bikes': bike_count}
            }
        })
    except Exception as e:
        print(f'[ERROR] api_admin_dashboard: {e}')
        import traceback; traceback.print_exc()
        return jsonify({'message': 'Failed to load admin dashboard'}), 500


# ─── API: Admin Users List ────────────────────────────────────────────────────

@admin_bp.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def api_admin_users():
    try:
        users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
        result = []
        for u in users:
            booking_count = Booking.query.filter_by(user_id=u.id).count()
            total_spent = db.session.query(func.sum(Booking.total_price)).filter(
                Booking.user_id == u.id,
                Booking.status.in_(['Confirmed', 'Completed'])
            ).scalar() or 0
            result.append({
                'id': u.id,
                'name': u.full_name,
                'email': u.email or '',
                'phone': u.phone or '',
                'is_verified': u.is_verified,
                'bookings': booking_count,
                'total_spent': total_spent,
                'created_at': u.created_at.isoformat() if u.created_at else ''
            })
        return jsonify(result)
    except Exception as e:
        print(f'[ERROR] api_admin_users: {e}')
        return jsonify([]), 500


# ─── API: Admin Vehicle List ──────────────────────────────────────────────────

@admin_bp.route('/api/admin/vehicles', methods=['GET'])
@login_required
@admin_required
def api_admin_vehicles():
    try:
        vehicles = Vehicle.query.order_by(Vehicle.id.desc()).all()
        today = date.today()
        result = []
        for v in vehicles:
            active = Booking.query.filter(
                Booking.vehicle_id == v.id,
                Booking.start_date <= today,
                Booking.end_date >= today,
                Booking.status == 'Confirmed'
            ).first()
            total_bookings = Booking.query.filter_by(vehicle_id=v.id).count()
            total_revenue = db.session.query(func.sum(Booking.total_price)).filter(
                Booking.vehicle_id == v.id,
                Booking.status.in_(['Confirmed', 'Completed'])
            ).scalar() or 0
            result.append({
                'id': v.id,
                'name': v.name,
                'type': v.type,
                'price_per_day': v.price_per_day,
                'status': 'booked' if active else v.status,
                'location': v.location or 'City',
                'image': v.image or '',
                'total_bookings': total_bookings,
                'total_revenue': total_revenue
            })
        return jsonify(result)
    except Exception as e:
        print(f'[ERROR] api_admin_vehicles: {e}')
        return jsonify([]), 500


# ─── API: Admin Vehicle Status Override ───────────────────────────────────────

@admin_bp.route('/api/admin/vehicles/<int:vehicle_id>/status', methods=['POST'])
@login_required
@admin_required
def api_update_vehicle_status(vehicle_id):
    try:
        data = request.get_json() or {}
        new_status = data.get('status')
        
        if new_status not in ['available', 'maintenance', 'booked']:
            return jsonify({'message': 'Invalid status'}), 400
            
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        vehicle.status = new_status
        db.session.commit()
        
        # Real-time update to all users
        try:
            from app import socketio
            socketio.emit('vehicle_status_update', {
                'vehicle_id': vehicle_id,
                'status': new_status,
                'available_count': Vehicle.query.filter_by(status='available').count()
            }, broadcast=True)
            
            socketio.emit('activity_update', {
                'type': 'vehicle_status',
                'title': 'Vehicle Status Changed',
                'msg': f'{vehicle.name} is now {new_status}',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        except Exception as e:
            print(f'[WARNING] Socket emit failed: {e}')
            
        return jsonify({'message': f'Vehicle status updated to {new_status}'})
    except Exception as e:
        print(f'[ERROR] api_update_vehicle_status: {e}')
        db.session.rollback()
        return jsonify({'message': 'Failed to update vehicle status'}), 500


# ─── API: Admin Booking Status Update ─────────────────────────────────────────

@admin_bp.route('/api/admin/bookings/<int:booking_id>/status', methods=['POST'])
@login_required
@admin_required
def api_update_booking_status(booking_id):
    try:
        data = request.get_json() or {}
        new_status = data.get('status')
        
        if new_status not in ['Confirmed', 'Cancelled', 'Completed']:
            return jsonify({'message': 'Invalid status'}), 400
            
        booking = Booking.query.get_or_404(booking_id)
        old_status = booking.status
        booking.status = new_status
        
        # If cancelled, free up vehicle
        if new_status == 'Cancelled':
            # Check if there are other confirmed bookings for this vehicle at this time
            # For simplicity in this "real-time" override, we set it to available
            # but ideally we'd check schedules.
            booking.vehicle.status = 'available'
            
        db.session.commit()
        
        # Real-time update
        try:
            from app import socketio
            socketio.emit('booking_status_update', {
                'booking_id': booking_id,
                'status': new_status,
                'vehicle_id': booking.vehicle_id
            }, broadcast=True)
            
            if new_status == 'Cancelled':
                socketio.emit('vehicle_status_update', {
                    'vehicle_id': booking.vehicle_id,
                    'status': 'available'
                }, broadcast=True)
                
            socketio.emit('activity_update', {
                'type': 'booking_status',
                'title': 'Booking Updated',
                'msg': f'Booking #BK-{booking_id} marked as {new_status}',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        except Exception as e:
            print(f'[WARNING] Socket emit failed: {e}')
            
        return jsonify({'message': f'Booking status updated to {new_status}'})
    except Exception as e:
        print(f'[ERROR] api_update_booking_status: {e}')
        db.session.rollback()
        return jsonify({'message': 'Failed to update booking status'}), 500
