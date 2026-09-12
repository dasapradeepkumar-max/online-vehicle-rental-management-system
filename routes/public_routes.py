from flask import Blueprint, jsonify, request
from models import Vehicle, Booking, User
from datetime import datetime, timedelta
from sqlalchemy import func

public_bp = Blueprint('public', __name__, url_prefix='/api/public')

@public_bp.route('/vehicles', methods=['GET'])
def get_vehicles():
    """
    Fetch all vehicles with real-time availability status
    Returns JSON array of vehicles
    """
    try:
        vehicles = Vehicle.query.all()
        
        vehicles_data = []
        for vehicle in vehicles:
            # Check if vehicle has active booking today
            today = datetime.now().date()
            active_booking = Booking.query.filter(
                Booking.vehicle_id == vehicle.id,
                Booking.start_date <= today,
                Booking.end_date >= today,
                Booking.status == 'Confirmed'
            ).first()
            
            status = 'booked' if active_booking else 'available'
            
            vehicles_data.append({
                'id': vehicle.id,
                'name': vehicle.name,
                'type': vehicle.type,
                'price_per_day': vehicle.price_per_day,
                'status': status,
                'image': vehicle.image,
                'location': vehicle.location if vehicle.location else 'City'
            })
        
        return jsonify(vehicles_data)
    except Exception as e:
        print(f"Error fetching vehicles: {e}")
        return jsonify({'error': 'Failed to fetch vehicles'}), 500


@public_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Fetch live platform statistics
    - Total vehicles
    - Available vehicles
    - Active rentals
    """
    try:
        today = datetime.now().date()
        
        # Total vehicles
        total_vehicles = Vehicle.query.count()
        
        # Available vehicles (not in active bookings)
        active_bookings = Booking.query.filter(
            Booking.start_date <= today,
            Booking.end_date >= today,
            Booking.status == 'Confirmed'
        ).with_entities(Booking.vehicle_id).distinct().all()
        
        booked_vehicle_ids = [b.vehicle_id for b in active_bookings]
        available_vehicles = Vehicle.query.filter(
            ~Vehicle.id.in_(booked_vehicle_ids) if booked_vehicle_ids else True
        ).count()
        
        # Active rentals
        active_rentals = Booking.query.filter(
            Booking.start_date <= today,
            Booking.end_date >= today,
            Booking.status == 'Confirmed'
        ).count()
        
        # Total users
        total_users = User.query.filter_by(is_admin=False).count()
        
        return jsonify({
            'total_vehicles': total_vehicles,
            'available': available_vehicles,
            'active_rentals': active_rentals,
            'total_users': total_users
        })
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({
            'total_vehicles': 0,
            'available': 0,
            'active_rentals': 0,
            'total_users': 0
        }), 500


@public_bp.route('/vehicle/<int:vehicle_id>', methods=['GET'])
def get_vehicle_details(vehicle_id):
    """
    Get detailed information about a specific vehicle
    """
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        # Check availability
        today = datetime.now().date()
        active_booking = Booking.query.filter(
            Booking.vehicle_id == vehicle_id,
            Booking.start_date <= today,
            Booking.end_date >= today,
            Booking.status == 'Confirmed'
        ).first()
        
        status = 'booked' if active_booking else 'available'
        
        return jsonify({
            'id': vehicle.id,
            'name': vehicle.name,
            'type': vehicle.type,
            'price_per_day': vehicle.price_per_day,
            'status': status,
            'image': vehicle.image,
            'location': vehicle.location if vehicle.location else 'City',
            'description': 'Premium vehicle rental'
        })
    except Exception as e:
        print(f"Error fetching vehicle details: {e}")
        return jsonify({'error': 'Failed to fetch vehicle details'}), 500


@public_bp.route('/availability/<int:vehicle_id>', methods=['GET'])
def check_availability(vehicle_id):
    """
    Check vehicle availability for a specific date range
    Query params: start_date, end_date (format: YYYY-MM-DD)
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date required'}), 400
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        vehicle = Vehicle.query.get_or_404(vehicle_id)
        if vehicle.status != 'available':
            return jsonify({
                'vehicle_id': vehicle_id,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'available': False
            })
        
        # Check for overlapping bookings
        conflicting_booking = Booking.query.filter(
            Booking.vehicle_id == vehicle_id,
            Booking.start_date <= end_date,
            Booking.end_date >= start_date,
            Booking.status == 'Confirmed'
        ).first()
        
        available = conflicting_booking is None
        
        return jsonify({
            'vehicle_id': vehicle_id,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'available': available
        })
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        print(f"Error checking availability: {e}")
        return jsonify({'error': 'Failed to check availability'}), 500
