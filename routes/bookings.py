from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Booking, Vehicle, User
from datetime import datetime, date, time, timedelta
import jwt
from config import Config
from functools import wraps

bookings_bp = Blueprint('bookings', __name__)


def jwt_or_session_required(f):
    """Allow both JWT (API) and Flask-Login (session) auth."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        # 1. Already logged in via session
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        # 2. Try JWT from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
                user = User.query.get(payload.get('user_id'))
                if user:
                    from flask_login import login_user
                    login_user(user)
                    return f(*args, **kwargs)
            except Exception:
                pass
        return jsonify({'message': 'Authentication required'}), 401
    return wrapped


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapped


# ─── Page Routes ──────────────────────────────────────────────────────────────

@bookings_bp.route('/booking')
@login_required
def booking_page():
    vehicle_id = request.args.get('vehicle_id', '')
    vehicle = Vehicle.query.get(vehicle_id) if vehicle_id else None
    return render_template('booking.html', vehicle=vehicle)


@bookings_bp.route('/mybookings')
@login_required
def my_bookings_page():
    return render_template('mybookings.html')


# ─── API: Create booking ──────────────────────────────────────────────────────

@bookings_bp.route('/api/bookings', methods=['POST'])
@jwt_or_session_required
def api_create_booking():
    """
    POST /api/bookings
    Body: { vehicle_id, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD) }
    """
    try:
        data = request.get_json() or {}
        vehicle_id = data.get('vehicle_id')
        start_str = data.get('start_date', '').strip()
        end_str = data.get('end_date', '').strip()

        if not all([vehicle_id, start_str, end_str]):
            return jsonify({'message': 'vehicle_id, start_date and end_date are required'}), 400

        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        pickup_time = _parse_datetime(data.get('pickup_time'), start_date)
        return_time = _parse_datetime(data.get('return_time'), end_date)

        if start_date >= end_date:
            return jsonify({'message': 'end_date must be after start_date'}), 400
        if start_date < date.today():
            return jsonify({'message': 'start_date cannot be in the past'}), 400

        vehicle = Vehicle.query.filter_by(id=vehicle_id).with_for_update().first()
        if not vehicle:
            return jsonify({'message': 'Vehicle not found'}), 404
        if vehicle.status != 'available':
            return jsonify({'message': 'Vehicle is not currently available'}), 409

        # Check overlapping confirmed bookings
        overlap = Booking.query.filter(
            Booking.vehicle_id == vehicle_id,
            Booking.start_date <= end_date,
            Booking.end_date >= start_date,
            Booking.status == 'Confirmed'
        ).first()
        if overlap:
            return jsonify({'message': 'Vehicle not available for selected dates'}), 409

        # Calculate price
        days = (end_date - start_date).days
        total_price = days * vehicle.price_per_day

        booking = Booking(
            user_id=current_user.id,
            vehicle_id=vehicle_id,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            status='Confirmed',
            pickup_time=pickup_time,
            return_time=return_time,
            payment_status='Paid',
            payment_reference=(data.get('payment_reference') or '').strip() or None
        )
        db.session.add(booking)
        db.session.commit()

        # Emit real-time events
        try:
            from app import socketio
            booking_data = {
                'id': booking.id,
                'vehicle_name': vehicle.name,
                'customer_name': current_user.full_name,
                'total_price': total_price,
                'start_date': start_str,
                'end_date': end_str,
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('new_booking', booking_data)
            socketio.emit('booking_confirmed', booking_data)
            socketio.emit('vehicle_status_update', {
                'vehicle_id': vehicle_id,
                'status': 'booked',
                'available_count': Vehicle.query.filter_by(status='available').count()
            })
        except Exception as e:
            print(f'[WARNING] Socket emit failed: {e}')

        # Send notifications
        try:
            from services.notification_service import send_booking_confirmation
            send_booking_confirmation(booking, current_user, vehicle)
        except Exception as e:
            print(f'[WARNING] Notification failed: {e}')

        return jsonify({
            'message': 'Booking confirmed!',
            'booking': {
                'id': booking.id,
                'vehicle_name': vehicle.name,
                'start_date': start_str,
                'end_date': end_str,
                'total_price': total_price,
                'status': 'Confirmed',
                'days': days
            }
        }), 201

    except ValueError as e:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        print(f'[ERROR] api_create_booking: {e}')
        import traceback; traceback.print_exc()
        db.session.rollback()
        return jsonify({'message': 'Failed to create booking'}), 500


def _parse_datetime(value, rental_date):
    if not value:
        return None
    try:
        return datetime.fromisoformat(f'{rental_date.isoformat()}T{value}')
    except ValueError:
        raise ValueError('Invalid pickup or return time')


# ─── API: My bookings ─────────────────────────────────────────────────────────

@bookings_bp.route('/api/bookings/my', methods=['GET'])
@jwt_or_session_required
def api_my_bookings():
    try:
        bookings = Booking.query.filter_by(user_id=current_user.id)\
            .order_by(Booking.created_at.desc()).all()
        today = date.today()
        result = []
        for b in bookings:
            status = b.status
            if b.status == 'Confirmed':
                if b.end_date < today:
                    status = 'Completed'
                elif b.start_date <= today <= b.end_date:
                    status = 'Active'
                else:
                    status = 'Upcoming'
            result.append({
                'id': b.id,
                'vehicle_name': b.vehicle.name if b.vehicle else 'N/A',
                'vehicle_type': b.vehicle.type if b.vehicle else 'car',
                'vehicle_image': b.vehicle.image if b.vehicle else '',
                'start_date': b.start_date.isoformat(),
                'end_date': b.end_date.isoformat(),
                'total_price': b.total_price,
                'days': (b.end_date - b.start_date).days,
                'status': status,
                'pickup_time': b.pickup_time.isoformat() if b.pickup_time else None,
                'cancellation_fee': b.cancellation_fee or 0,
                'refund_amount': b.refund_amount or 0,
                'refund_status': b.refund_status or 'Not applicable',
                'payment_status': b.payment_status or 'Paid',
                'created_at': b.created_at.isoformat() if b.created_at else ''
            })
        return jsonify(result)
    except Exception as e:
        print(f'[ERROR] api_my_bookings: {e}')
        return jsonify([]), 500


# ─── API: Cancel booking ──────────────────────────────────────────────────────

@bookings_bp.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
@jwt_or_session_required
def api_cancel_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        if booking.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'message': 'Unauthorized'}), 403
        if booking.status == 'Cancelled':
            return jsonify({'message': 'Booking already cancelled'}), 400
        pickup_at = booking.pickup_time or datetime.combine(booking.start_date, time.min)
        now = datetime.utcnow()
        if now >= pickup_at:
            return jsonify({'message': 'Cannot cancel after the pickup/booking start time'}), 400
        if pickup_at - now < timedelta(hours=24):
            return jsonify({'message': 'Cancellation is allowed only at least 24 hours before pickup'}), 400

        fee = round(booking.total_price * 0.10, 2)
        refund_amount = round(booking.total_price - fee, 2)

        booking.status = 'Cancelled'
        booking.cancellation_reason = (request.get_json(silent=True) or {}).get('reason') or 'Cancelled by user'
        booking.cancellation_fee = fee
        booking.refund_amount = refund_amount
        booking.refund_status = 'Processed'
        booking.payment_status = 'Refunded'
        booking.cancelled_at = now
        # Free the vehicle only when no other confirmed rental is active today.
        replacement_booking = Booking.query.filter(
            Booking.id != booking.id,
            Booking.vehicle_id == booking.vehicle_id,
            Booking.start_date <= date.today(),
            Booking.end_date >= date.today(),
            Booking.status == 'Confirmed'
        ).first()
        if booking.vehicle and not replacement_booking:
            booking.vehicle.status = 'available'
            
        db.session.commit()

        try:
            from app import socketio
            socketio.emit('booking_cancelled', {
                'booking_id': booking_id,
                'vehicle_id': booking.vehicle_id,
                'customer_name': current_user.full_name
            })
            socketio.emit('vehicle_status_update', {
                'vehicle_id': booking.vehicle_id,
                'status': 'available'
            })
            # Add general activity for admin feed
            socketio.emit('activity_update', {
                'type': 'cancellation',
                'title': 'Booking Cancelled',
                'msg': f'{current_user.full_name} cancelled booking #BK-{booking_id}',
                'timestamp': datetime.now().isoformat()
            })
        except Exception:
            pass

        return jsonify({
            'message': 'Booking cancelled successfully',
            'fee': fee,
            'refund': refund_amount,
            'cancellation_fee': fee,
            'refund_amount': refund_amount,
            'refund_status': booking.refund_status,
            'booking_status': booking.status
        })
    except Exception as e:
        print(f'[ERROR] api_cancel_booking: {e}')
        db.session.rollback()
        return jsonify({'message': 'Failed to cancel booking'}), 500


# ─── API: User dashboard data ─────────────────────────────────────────────────

@bookings_bp.route('/api/dashboard/user', methods=['GET'])
@jwt_or_session_required
def api_user_dashboard():
    try:
        today = date.today()
        all_bookings = Booking.query.filter_by(user_id=current_user.id).all()
        active = [b for b in all_bookings if b.status == 'Confirmed'
                  and b.start_date <= today <= b.end_date]
        upcoming = [b for b in all_bookings if b.status == 'Confirmed'
                    and b.start_date > today]
        total_spent = sum(b.total_price for b in all_bookings
                          if b.status in ('Confirmed', 'Completed'))

        recent = sorted(all_bookings, key=lambda b: b.created_at, reverse=True)[:5]

        return jsonify({
            'user': {
                'name': current_user.full_name,
                'email': current_user.email,
                'is_admin': current_user.is_admin
            },
            'stats': {
                'total_bookings': len(all_bookings),
                'active_rentals': len(active),
                'upcoming_bookings': len(upcoming),
                'total_spent': total_spent
            },
            'recent_bookings': [{
                'id': b.id,
                'vehicle_name': b.vehicle.name if b.vehicle else 'N/A',
                'vehicle_image': b.vehicle.image if b.vehicle else '',
                'start_date': b.start_date.isoformat(),
                'end_date': b.end_date.isoformat(),
                'total_price': b.total_price,
                'status': b.status,
                'created_at': b.created_at.isoformat() if b.created_at else ''
            } for b in recent]
        })
    except Exception as e:
        print(f'[ERROR] api_user_dashboard: {e}')
        return jsonify({'message': 'Failed to load dashboard'}), 500


# ─── API: Admin booking list ──────────────────────────────────────────────────

@bookings_bp.route('/api/admin/bookings', methods=['GET'])
@login_required
@admin_required
def api_admin_bookings():
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).limit(50).all()
        today = date.today()
        result = []
        for b in bookings:
            status = b.status
            if b.status == 'Confirmed':
                if b.end_date < today:
                    status = 'Completed'
                elif b.start_date <= today <= b.end_date:
                    status = 'Active'
                else:
                    status = 'Upcoming'
            result.append({
                'id': b.id,
                'customer_name': b.user.full_name if b.user else 'N/A',
                'customer_email': b.user.email if b.user else '',
                'vehicle_name': b.vehicle.name if b.vehicle else 'N/A',
                'start_date': b.start_date.isoformat(),
                'end_date': b.end_date.isoformat(),
                'total_price': b.total_price,
                'status': status,
                'created_at': b.created_at.isoformat() if b.created_at else ''
            })
        return jsonify(result)
    except Exception as e:
        print(f'[ERROR] api_admin_bookings: {e}')
        return jsonify([]), 500
