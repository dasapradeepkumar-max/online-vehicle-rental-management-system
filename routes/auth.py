from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, OTP, LoginEvent
from flask_login import login_user, logout_user, login_required, current_user
from services.otp_service import generate_otp, send_email_otp, verify_otp
from functools import wraps
from datetime import datetime, timedelta
import jwt
from config import Config

auth_bp = Blueprint('auth', __name__)

# ============================================
# RATE LIMITING DECORATOR
# ============================================
def rate_limit(max_attempts=5, window_minutes=10):
    """Rate limiting decorator to prevent abuse"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get IP address
            ip = request.remote_addr
            # Create rate limit key
            key = f"rate_limit:{f.__name__}:{ip}"
            
            # Store attempts in session or implement with Redis for production
            if key not in session:
                session[key] = {'attempts': 0, 'timestamp': datetime.now().isoformat()}
            
            attempt_data = session[key]
            attempt_time = datetime.fromisoformat(attempt_data['timestamp'])
            
            # Reset if window has passed
            if (datetime.now() - attempt_time).seconds > (window_minutes * 60):
                session[key] = {'attempts': 0, 'timestamp': datetime.now().isoformat()}
                attempt_data = session[key]
            
            # Check limit
            if attempt_data['attempts'] >= max_attempts:
                return jsonify({
                    'message': f'Too many attempts. Try again in {window_minutes} minutes.'
                }), 429
            
            # Increment attempts
            session[key]['attempts'] += 1
            session.modified = True
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ============================================
# RESTful API ROUTES (for frontend)
# ============================================

@auth_bp.route('/api/auth/send-otp', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=10)
def api_send_otp():
    """
    Send OTP to user email or phone
    POST /api/auth/send-otp
    Body: { "identifier": "email@example.com" or "9876543210" }
    """
    try:
        # Get JSON data with multiple fallbacks
        data = request.get_json() or {}
        
        # If get_json failed, try to parse from data
        if not data and request.data:
            try:
                import json
                data = json.loads(request.data)
            except:
                data = {}
        
        identifier = (data.get('identifier') or '').strip()

        if not identifier:
            return jsonify({'message': 'Email or phone number is required'}), 400

        # Find or create user
        user = None
        if '@' in identifier:
            # Email
            user = User.query.filter_by(email=identifier).first()
            if not user:
                # Auto-create user with email
                user = User(email=identifier, full_name=identifier.split('@')[0])
                db.session.add(user)
                db.session.flush()
                user.user_code = User.next_user_code()
                db.session.commit()
        else:
            # Phone number
            user = User.query.filter_by(phone=identifier).first()
            if not user:
                # Auto-create user with phone
                user = User(phone=identifier, full_name='User')
                db.session.add(user)
                db.session.flush()
                user.user_code = User.next_user_code()
                db.session.commit()

        # Generate OTP
        otp_code = generate_otp(user)
        print(f"[DEBUG] OTP for {identifier}: {otp_code}")

        # Send OTP via email if email exists
        if user.email:
            try:
                send_email_otp(user, otp_code)
            except Exception as e:
                print(f"[WARNING] Failed to send email: {e}")
                # Continue anyway for demo

        # Emit socket event for admin (try to emit, but don't fail if socket not available)
        try:
            from app import socketio
            socketio.emit('otp_sent', {
                'identifier': identifier,
                'timestamp': datetime.now().isoformat()
            }, namespace='/admin')
        except Exception as e:
            print(f"[WARNING] Could not emit socket event: {e}")

        return jsonify({
            'message': 'OTP sent successfully',
            'identifier': identifier
        }), 200

    except Exception as e:
        print(f"[ERROR] Send OTP: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Failed to send OTP. Please try again.'}), 500


@auth_bp.route('/api/auth/verify-otp', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=10)
def api_verify_otp():
    """
    Verify OTP and return JWT token
    POST /api/auth/verify-otp
    Body: { "identifier": "email@example.com", "otp": "123456" }
    """
    try:
        # Get JSON data with multiple fallbacks
        data = request.get_json() or {}
        
        # If get_json failed, try to parse from data
        if not data and request.data:
            try:
                import json
                data = json.loads(request.data)
            except:
                data = {}
        
        identifier = (data.get('identifier') or '').strip()
        otp_code = (data.get('otp') or '').strip()

        if not identifier or not otp_code:
            return jsonify({'message': 'Identifier and OTP are required'}), 400

        # Find user
        user = None
        if '@' in identifier:
            user = User.query.filter_by(email=identifier).first()
        else:
            user = User.query.filter_by(phone=identifier).first()

        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Verify OTP
        if not verify_otp(user, otp_code):
            return jsonify({'message': 'Invalid or expired OTP'}), 401

        # Mark user as verified (optional)
        user.is_verified = True
        db.session.commit()

        # Login user
        login_user(user)
        db.session.add(LoginEvent(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:255] if request.user_agent else None
        ))
        db.session.commit()

        # Generate JWT token (optional, for stateless auth)
        token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, Config.SECRET_KEY, algorithm='HS256')

        # Emit socket event (try to emit, but don't fail if socket not available)
        try:
            from app import socketio
            socketio.emit('user_logged_in', {
                'user_id': user.id,
                'email': user.email,
                'timestamp': datetime.now().isoformat()
            }, namespace='/admin')
        except Exception as e:
            print(f"[WARNING] Could not emit socket event: {e}")

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'user_code': user.display_id,
                'email': user.email or user.phone,
                'name': user.full_name,
                'is_admin': user.is_admin
            },
            'redirect_url': '/admin' if user.is_admin else '/dashboard'
        }), 200

    except Exception as e:
        print(f"[ERROR] Verify OTP: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Failed to verify OTP. Please try again.'}), 500


@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    """
    Register new user after OTP verification
    POST /api/auth/register
    Headers: Authorization: Bearer <token>
    Body: { "full_name": "", "email": "", "phone": "", "password": "" }
    """
    try:
        # Verify JWT token
        token = request.headers.get('Authorization', '').split(' ')[-1]
        if not token:
            return jsonify({'message': 'Missing authorization token'}), 401
        
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Get registration data
        data = request.get_json() or {}
        
        # Update user information
        if data.get('full_name'):
            user.full_name = data['full_name']
        if data.get('password'):
            user.set_password(data['password'])
        if data.get('phone') and not user.phone:
            user.phone = data['phone']

        if not user.user_code and not user.is_admin:
            user.user_code = User.next_user_code()
        
        user.is_verified = True
        db.session.commit()
        
        # Emit socket event
        try:
            from app import socketio
            socketio.emit('activity_update', {
                'type': 'registration',
                'title': 'New User Joined',
                'msg': f'{user.full_name} ({user.email}) registered',
                'timestamp': datetime.now().isoformat()
            })
            socketio.emit('user_registered', {
                'user_id': user.id,
                'email': user.email,
                'timestamp': datetime.now().isoformat()
            })
        except:
            pass
        
        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'is_verified': user.is_verified
            }
        }), 201
    
    except Exception as e:
        print(f"[ERROR] Registration: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Registration failed'}), 500


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/api/dashboard/data', methods=['GET'])
@login_required
def api_dashboard_data():
    """
    Get dashboard statistics for the user (redirects to the richer endpoint in bookings.py)
    GET /api/dashboard/data
    """
    try:
        from models import Vehicle, Booking
        from datetime import date
        today = date.today()

        all_bookings = Booking.query.filter_by(user_id=current_user.id).all()
        active = [b for b in all_bookings if b.status == 'Confirmed'
                  and b.start_date <= today <= b.end_date]
        upcoming = [b for b in all_bookings if b.status == 'Confirmed'
                    and b.start_date > today]
        total_spent = sum(b.total_price for b in all_bookings
                          if b.status in ('Confirmed',))

        total_vehicles = Vehicle.query.count()
        available_vehicles = Vehicle.query.filter_by(status='available').count()

        return jsonify({
            'totalVehicles': total_vehicles,
            'activeBookings': len(active),
            'totalRevenue': total_spent,
            'totalCustomers': 0,
            'activeVehicles': available_vehicles,
            'pendingRequests': len(upcoming),
            'monthlyRevenue': total_spent,
            'activeUsers': 1
        }), 200

    except Exception as e:
        print(f"[ERROR] Dashboard data: {e}")
        return jsonify({'message': 'Failed to load dashboard data'}), 500


@auth_bp.route('/api/dashboard/bookings', methods=['GET'])
@login_required
def api_dashboard_bookings():
    """Get recent bookings for the current user"""
    try:
        from models import Booking
        from datetime import date
        today = date.today()

        bookings = Booking.query.filter_by(user_id=current_user.id)\
            .order_by(Booking.created_at.desc())\
            .limit(10)\
            .all()

        def compute_status(b):
            if b.status == 'Confirmed':
                if b.end_date < today: return 'Completed'
                if b.start_date <= today <= b.end_date: return 'Active'
                return 'Upcoming'
            return b.status

        return jsonify([{
            'id': b.id,
            'vehicle_name': b.vehicle.name if b.vehicle else 'Vehicle',
            'customer_name': current_user.full_name,
            'status': compute_status(b),
            'total_price': b.total_price,
            'created_at': b.created_at.isoformat() if b.created_at else ''
        } for b in bookings]), 200

    except Exception as e:
        print(f"[ERROR] Dashboard bookings: {e}")
        return jsonify([]), 500


# ============================================
# LEGACY ROUTES (for backward compatibility)
# ============================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    
    if request.method == 'POST':
        # The frontend handles POST requests via the /api/auth/verify-otp endpoint.
        # This legacy POSThandler is not needed and was causing a redirect loop.
        pass
    
    return render_template('login.html')


@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        code = request.form.get('otp')
        uid = session.get('otp_user')
        user = User.query.get(uid)
        if user and verify_otp(user, code):
            login_user(user)
            db.session.add(LoginEvent(
                user_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string[:255] if request.user_agent else None
            ))
            db.session.commit()
            flash('Logged in via OTP', 'success')
            return redirect(url_for('auth.dashboard'))
        flash('Invalid or expired OTP', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('verify.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
        # The frontend handles registration after OTP verification.
        # This legacy POST handler is kept for compatibility but should not redirect to itself.
        pass
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    from models import Booking
    booking_count = Booking.query.filter_by(user_id=current_user.id).count()
    return render_template('dashboard.html', bookings_count=booking_count)

