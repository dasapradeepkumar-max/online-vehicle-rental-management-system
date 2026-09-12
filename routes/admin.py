from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, User, Booking, Vehicle, LoginEvent, Issue
from datetime import datetime, date, timedelta
from functools import wraps
from sqlalchemy import func, or_

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

        paid_bookings = Booking.query.filter(Booking.payment_status.in_(['Paid', 'Refunded'])).all()
        total_payments = sum(b.total_price for b in paid_bookings)
        total_cancellations = Booking.query.filter_by(status='Cancelled').count()
        total_refunds = db.session.query(func.sum(Booking.refund_amount)).filter(
            Booking.refund_status == 'Processed'
        ).scalar() or 0
        total_cancellation_fees = db.session.query(func.sum(Booking.cancellation_fee)).filter(
            Booking.status == 'Cancelled'
        ).scalar() or 0

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
                'total_payments': total_payments,
                'total_cancellations': total_cancellations,
                'total_refunds': total_refunds,
                'total_cancellation_fees': total_cancellation_fees,
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
        search = request.args.get('search', '').strip().lower()
        created_from = request.args.get('created_from')
        created_to = request.args.get('created_to')
        booking_filter = request.args.get('bookings', 'all')
        login_filter = request.args.get('login_activity', 'all')
        booking_status = request.args.get('booking_status', 'all')
        issue_status = request.args.get('issue_status', 'all')
        payment_status = request.args.get('payment_status', 'all')
        rental_status = request.args.get('rental_status', 'all')
        booking_from = request.args.get('booking_from')
        booking_to = request.args.get('booking_to')
        sort = request.args.get('sort', 'created_desc')
        users = User.query.filter_by(is_admin=False).all()
        today = date.today()
        result = []
        for u in users:
            bookings = Booking.query.filter_by(user_id=u.id).order_by(Booking.created_at.desc()).all()
            issues = Issue.query.filter_by(user_id=u.id).order_by(Issue.created_at.desc()).all()
            login_count = LoginEvent.query.filter_by(user_id=u.id).count()
            last_login = LoginEvent.query.filter_by(user_id=u.id).order_by(LoginEvent.logged_in_at.desc()).first()
            statuses = {_rental_status(booking, today) for booking in bookings}
            user_issue_status = _issue_status(issues)
            if search and search not in ' '.join(filter(None, [u.user_code, u.full_name, u.email, u.phone])).lower():
                continue
            if created_from and (not u.created_at or u.created_at.date() < date.fromisoformat(created_from)):
                continue
            if created_to and (not u.created_at or u.created_at.date() > date.fromisoformat(created_to)):
                continue
            if booking_from:
                booking_from_date = date.fromisoformat(booking_from)
                if not any(b.end_date >= booking_from_date for b in bookings):
                    continue
            if booking_to:
                booking_to_date = date.fromisoformat(booking_to)
                if not any(b.start_date <= booking_to_date for b in bookings):
                    continue
            if booking_filter == 'with' and not bookings or booking_filter == 'without' and bookings:
                continue
            if login_filter == 'active' and not last_login or login_filter == 'inactive' and last_login:
                continue
            if booking_status != 'all' and not any(b.status == booking_status for b in bookings):
                continue
            if issue_status != 'all' and user_issue_status != issue_status:
                continue
            if payment_status != 'all' and not any((b.payment_status or 'Pending') == payment_status for b in bookings):
                continue
            if rental_status != 'all' and rental_status not in statuses:
                continue
            booking_count = len(bookings)
            total_spent = db.session.query(func.sum(Booking.total_price)).filter(
                Booking.user_id == u.id,
                Booking.status.in_(['Confirmed', 'Completed'])
            ).scalar() or 0
            result.append({
                'id': u.id,
                'user_id': u.display_id,
                'name': u.full_name,
                'email': u.email or '',
                'phone': u.phone or '',
                'is_verified': u.is_verified,
                'bookings': booking_count,
                'total_spent': total_spent,
                'created_at': u.created_at.isoformat() if u.created_at else '',
                'total_logins': login_count,
                'last_login': last_login.logged_in_at.isoformat() if last_login else '',
                'issue_status': user_issue_status,
                'rental_statuses': sorted(statuses),
            })
        reverse = sort.endswith('_desc')
        sort_key = sort.replace('_desc', '').replace('_asc', '')
        keys = {
            'created': lambda item: item['created_at'],
            'name': lambda item: item['name'].lower(),
            'bookings': lambda item: item['bookings'],
            'logins': lambda item: item['total_logins'],
            'last_login': lambda item: item['last_login'],
        }
        result.sort(key=keys.get(sort_key, keys['created']), reverse=reverse)
        return jsonify(result)
    except Exception as e:
        print(f'[ERROR] api_admin_users: {e}')
        return jsonify([]), 500


def _rental_status(booking, today):
    if booking.status == 'Cancelled':
        return 'Cancelled'
    if booking.status == 'Completed' or booking.end_date < today:
        return 'Completed'
    if booking.status == 'Confirmed' and booking.start_date <= today <= booking.end_date:
        return 'Active'
    return 'Upcoming'


def _issue_status(issues):
    if not issues:
        return 'None'
    if any(issue.status == 'Open' for issue in issues):
        return 'Open'
    return issues[0].status


@admin_bp.route('/api/admin/users/<int:user_id>/history', methods=['GET'])
@login_required
@admin_required
def api_admin_user_history(user_id):
    user = User.query.filter_by(id=user_id, is_admin=False).first_or_404()
    today = date.today()
    bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    return jsonify({
        'user': {
            'id': user.id,
            'user_id': user.display_id,
            'name': user.full_name,
            'email': user.email or '',
            'phone': user.phone or '',
            'created_at': user.created_at.isoformat() if user.created_at else '',
        },
        'login_history': [{
            'logged_in_at': event.logged_in_at.isoformat(),
            'ip_address': event.ip_address or '',
            'user_agent': event.user_agent or '',
        } for event in LoginEvent.query.filter_by(user_id=user.id).order_by(LoginEvent.logged_in_at.desc()).all()],
        'rental_history': [{
            'booking_id': booking.id,
            'vehicle': booking.vehicle.name if booking.vehicle else 'N/A',
            'vehicle_number': booking.vehicle.vehicle_number if booking.vehicle else '',
            'booking_time': booking.created_at.isoformat() if booking.created_at else '',
            'pickup_time': booking.pickup_time.isoformat() if booking.pickup_time else '',
            'return_time': booking.return_time.isoformat() if booking.return_time else '',
            'rental_days': (booking.end_date - booking.start_date).days,
            'start_date': booking.start_date.isoformat(),
            'end_date': booking.end_date.isoformat(),
            'payment': booking.total_price,
            'payment_status': booking.payment_status or 'Pending',
            'payment_reference': booking.payment_reference or '',
            'cancellation_fee': booking.cancellation_fee or 0,
            'refund_amount': booking.refund_amount or 0,
            'refund_status': booking.refund_status or 'Not applicable',
            'booking_status': booking.status,
            'rental_status': _rental_status(booking, today),
            'cancellation_reason': booking.cancellation_reason or '',
        } for booking in bookings],
        'issues': [{
            'id': issue.id,
            'booking_id': issue.booking_id,
            'description': issue.description,
            'created_at': issue.created_at.isoformat(),
            'status': issue.status,
            'admin_response': issue.admin_response or '',
        } for issue in Issue.query.filter_by(user_id=user.id).order_by(Issue.created_at.desc()).all()]
    })


@admin_bp.route('/api/admin/users/<int:user_id>/issues', methods=['POST'])
@login_required
@admin_required
def api_create_user_issue(user_id):
    user = User.query.filter_by(id=user_id, is_admin=False).first_or_404()
    data = request.get_json() or {}
    description = (data.get('description') or '').strip()
    if not description:
        return jsonify({'message': 'Issue description is required'}), 400
    issue = Issue(user_id=user.id, booking_id=data.get('booking_id'), description=description)
    db.session.add(issue)
    db.session.commit()
    return jsonify({'message': 'Issue created', 'issue_id': issue.id}), 201


@admin_bp.route('/api/admin/issues/<int:issue_id>', methods=['PATCH'])
@login_required
@admin_required
def api_update_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json() or {}
    if data.get('status') not in (None, 'Open', 'In Progress', 'Resolved', 'Closed'):
        return jsonify({'message': 'Invalid issue status'}), 400
    if data.get('status'):
        issue.status = data['status']
    if 'admin_response' in data:
        issue.admin_response = (data.get('admin_response') or '').strip()
    db.session.commit()
    return jsonify({'message': 'Issue updated'})


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
            })
            
            socketio.emit('activity_update', {
                'type': 'vehicle_status',
                'title': 'Vehicle Status Changed',
                'msg': f'{vehicle.name} is now {new_status}',
                'timestamp': datetime.now().isoformat()
            })
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
            if old_status != 'Cancelled':
                booking.cancellation_fee = round(booking.total_price * 0.10, 2)
                booking.refund_amount = round(booking.total_price - booking.cancellation_fee, 2)
                booking.refund_status = 'Processed'
                booking.payment_status = 'Refunded'
                booking.cancelled_at = datetime.utcnow()
                booking.cancellation_reason = 'Cancelled by administrator'
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
            })
            
            if new_status == 'Cancelled':
                socketio.emit('vehicle_status_update', {
                    'vehicle_id': booking.vehicle_id,
                    'status': 'available'
                })
                
            socketio.emit('activity_update', {
                'type': 'booking_status',
                'title': 'Booking Updated',
                'msg': f'Booking #BK-{booking_id} marked as {new_status}',
                'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            print(f'[WARNING] Socket emit failed: {e}')
            
        return jsonify({'message': f'Booking status updated to {new_status}'})
    except Exception as e:
        print(f'[ERROR] api_update_booking_status: {e}')
        db.session.rollback()
        return jsonify({'message': 'Failed to update booking status'}), 500
