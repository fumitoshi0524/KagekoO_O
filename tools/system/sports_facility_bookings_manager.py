"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manages sports facility bookings."""
    import json
    from datetime import datetime
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ['action', 'facility_id', 'user_id']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'})
        
        action = data['action']
        facility_id = data['facility_id']
        user_id = data['user_id']
        
        # In-memory storage (in production, this would be a database)
        # Using a dictionary to simulate persistent storage
        if not hasattr(run, 'bookings'):
            run.bookings = {}
        if not hasattr(run, 'facility_availability'):
            # Pre-populate some facility slots
            run.facility_availability = {
                'court_01': [{'start': '08:00', 'end': '22:00'}],
                'court_02': [{'start': '08:00', 'end': '22:00'}],
                'field_a': [{'start': '06:00', 'end': '20:00'}],
                'pool_lane_1': [{'start': '07:00', 'end': '21:00'}]
            }
        
        if action == 'check_availability':
            if facility_id not in run.facility_availability:
                return json.dumps({'error': f'Facility {facility_id} not found'})
            
            # Check existing bookings for conflicts
            facility_bookings = [b for b in run.bookings.values() 
                              if b['facility_id'] == facility_id]
            
            available_slots = run.facility_availability[facility_id]
            for booking in facility_bookings:
                # Simple overlap check
                if booking['start_time'] < data.get('end_time', '23:59') and \
                   booking['end_time'] > data.get('start_time', '00:00'):
                    # Remove overlapping time from available slots
                    pass  # In production, calculate actual availability
            
            return json.dumps({
                'facility_id': facility_id,
                'available': True,
                'available_slots': available_slots,
                'existing_bookings': len(facility_bookings)
            })
        
        elif action == 'create_booking':
            if 'start_time' not in data or 'end_time' not in data:
                return json.dumps({'error': 'start_time and end_time required for booking creation'})
            
            if facility_id not in run.facility_availability:
                return json.dumps({'error': f'Facility {facility_id} not found'})
            
            # Generate booking ID
            booking_id = f'BK-{user_id}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            
            # Create booking
            booking = {
                'booking_id': booking_id,
                'facility_id': facility_id,
                'user_id': user_id,
                'start_time': data['start_time'],
                'end_time': data['end_time'],
                'status': 'confirmed',
                'created_at': datetime.now().isoformat()
            }
            
            run.bookings[booking_id] = booking
            
            return json.dumps({
                'success': True,
                'booking_id': booking_id,
                'message': f'Booking confirmed for {facility_id}',
                'booking_details': booking
            })
        
        elif action == 'cancel_booking':
            if 'booking_id' not in data:
                return json.dumps({'error': 'booking_id required for cancellation'})
            
            booking_id = data['booking_id']
            if booking_id not in run.bookings:
                return json.dumps({'error': f'Booking {booking_id} not found'})
            
            booking = run.bookings[booking_id]
            if booking['user_id'] != user_id:
                return json.dumps({'error': 'Cannot cancel booking belonging to another user'})
            
            booking['status'] = 'cancelled'
            run.bookings[booking_id] = booking
            
            return json.dumps({
                'success': True,
                'booking_id': booking_id,
                'message': f'Booking {booking_id} cancelled successfully'
            })
        
        elif action == 'get_user_bookings':
            user_bookings = [b for b in run.bookings.values() if b['user_id'] == user_id]
            
            return json.dumps({
                'user_id': user_id,
                'total_bookings': len(user_bookings),
                'bookings': user_bookings
            })
        
        else:
            return json.dumps({'error': f'Invalid action: {action}'})
            
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON payload - {str(e)}'
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "sports_facility_bookings_manager",
    "description": "Manages sports facility bookings by checking availability, creating new reservations, cancelling existing bookings, and retrieving booking history for any registered sports facility or user.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The booking operation to perform: check_availability, create_booking, cancel_booking, or get_user_bookings",
            "enum": [
                "check_availability",
                "create_booking",
                "cancel_booking",
                "get_user_bookings"
            ]
        },
        "facility_id": {
            "type": "string",
            "description": "Unique identifier of the sports facility (e.g., court number, field name, or facility code)"
        },
        "user_id": {
            "type": "string",
            "description": "Unique identifier of the user making the booking or whose bookings to retrieve"
        },
        "start_time": {
            "type": "string",
            "description": "Booking start time (ISO 8601 format YYYY-MM-DDTHH:mm:ss, e.g., 2024-12-01T14:00:00)"
        },
        "end_time": {
            "type": "string",
            "description": "Booking end time (ISO 8601 format YYYY-MM-DDTHH:mm:ss, must be after start_time)"
        },
        "booking_id": {
            "type": "string",
            "description": "Optional: Unique booking identifier, required only for cancellation operations"
        }
    },
    "required": [
        "action",
        "facility_id",
        "user_id"
    ]
},
}
