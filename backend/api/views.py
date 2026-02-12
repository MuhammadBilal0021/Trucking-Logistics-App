from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import geocode_location, get_route_details
from .utils import calculate_trip_segments, decode_polyline, get_coordinate_at_distance

class CalculateTripView(APIView):
    def post(self, request):
        current_loc = request.data.get('current_location')
        pickup_loc = request.data.get('pickup_location')
        dropoff_loc = request.data.get('dropoff_location')
        hours_used = request.data.get('hours_used')
        
        # Validation
        if not all([current_loc, pickup_loc, dropoff_loc]):
            return Response({'error': 'All locations are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            hours_used = float(hours_used)
            if hours_used < 0 or hours_used > 70:
                return Response({'error': 'Hours used must be between 0 and 70.'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
             return Response({'error': 'Invalid hours_used value.'}, status=status.HTTP_400_BAD_REQUEST)
             
        if hours_used >= 70:
             return Response({'error': 'No driving hours available (>= 70 used).'}, status=status.HTTP_400_BAD_REQUEST)

        # Geocoding
        curr_coords = geocode_location(current_loc)
        pickup_coords = geocode_location(pickup_loc)
        dropoff_coords = geocode_location(dropoff_loc)
        
        if not all([curr_coords, pickup_coords, dropoff_coords]):
             return Response({'error': 'Could not geocode one or more locations.'}, status=status.HTTP_400_BAD_REQUEST)
             
        # Routing (Current -> Pickup -> Dropoff)
        # Leg 1: Current -> Pickup (Deadhead? usually HOS applies differently but let's assume standard driving)
        # Actually user prompt says: "Route from Current -> Pickup -> Dropoff"
        # But HOS usually starts when working.
        # Let's assume the trip STARTS at Pickup for cargo? 
        # Requirement: "Display route from Current -> Pickup -> Dropoff"
        # Requirement: "Pickup/Dropoff Time: Add 1 hour 'On Duty' time at pickup location"
        # Usually checking empty drive to pickup is "Driving". 
        # Let's calculate total distance.
        
        route1 = get_route_details(curr_coords, pickup_coords)
        route2 = get_route_details(pickup_coords, dropoff_coords)
        
        if not route1 or not route2:
             return Response(
                 {'error': 'Routing service is temporarily unavailable. Please try again in a moment.'},
                 status=status.HTTP_503_SERVICE_UNAVAILABLE
             )
             
        total_dist = route1['distance_miles'] + route2['distance_miles']
        
        # HOS Calculation
        # We process the ENTIRE distance as driving segments?
        # Or do we process Leg 1, then Pickup, then Leg 2, then Dropoff?
        # Logic says: "Add 1 hour... at pickup".
        # So structure: Drive(Current->Pickup) -> OnDuty(Pickup) -> Drive(Pickup->Dropoff) -> OnDuty(Dropoff)
        # My utils.py assumed a single "distance" and started with Pickup.
        # I should Refactor utils to handle generic segments or just pass total distance?
        
        # Refined Logic:
        # The user example: "Chicago -> Indy -> Nashville".
        # "Pickup time: 1 hour".
        # "Driving time: 473 / 60" (Total distance).
        # Segments example: 0:00-1:00 On Duty (Pickup) -> Driving -> Dropoff.
        # It seems the example IGNORES the drive from Current to Pickup or assumes Current IS Pickup?
        # Example Input: Current: Chicago, Pickup: Indy.
        # Example Calculation: "Total distance 184 + 289 = 473".
        # Example Segments: "0:00 - 1:00: On Duty (Pickup)".
        # This implies the driver is ALREADY at Pickup? Or the "Current" loc is just for map?
        # Wait, 184 miles is Chi->Indy.
        # If segments start with "On Duty (Pickup)", then the drive Chi->Indy is MISSING from the log?
        # OR the example assumes Current = Pickup?
        # Input: Current: Chicago, Pickup: Indy (184 miles).
        # Calculation: "Total distance... 473 miles".
        # Segments: "1:00 - 9:00: Driving (473 miles)".
        # Visual: "Hours 1-9: Driving".
        
        # Okay, the example implementation combines the distances (Current->Pickup + Pickup->Dropoff) into ONE driving block AFTER the Pickup?
        # That's slightly weird physically (how do you drive from Current to Pickup AFTER picking up?).
        # However, looking at the code provided in the prompt:
        # segments.append({'type': 'on_duty', ... 'description': 'Pickup'})
        # current_time += 1
        # while remaining_distance > 0: ...
        
        # The prompt's example algorithm calculates "Pickup" FIRST, then drives "Total Distance".
        # I will follow the prompt's algorithm vs physical reality if they conflict, 
        # BUT "Current -> Pickup" is usually "Empty Move" and counts as Driving.
        # Constructing the timeline:
        # The prompt Example says:
        # Distance: 184 (Chi->Indy) + 289 (Indy->Nash) = 473.
        # Segments: Pickup (1h) -> Driving (473mi).
        # This implies: Do Pickup Op -> Drive ALL miles.
        # I will stick to this simplified model as requested by the prompt's "Example Calculation Walkthrough".
        
        try:
            segments, cycle_hours_consumed = calculate_trip_segments(total_dist, hours_used)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        final_hours_used = float(hours_used) + cycle_hours_consumed

        # --- COORDINATE INTERPOLATION ---
        # 1. Decode path
        path1 = decode_polyline(route1['polyline'])
        path2 = decode_polyline(route2['polyline'])
        full_path = path1 + path2
        
        # 2. Assign coordinates to segments
        driven_dist = 0.0
        
        for segment in segments:
            # If segment has duration > 0 and type is driving, it advances distance
            if segment['type'] == 'driving':
                # Driving segment advances distance
                # But we want the coordinate for the END of the driving? 
                # No, driving is a span.
                # Only "Events" (Stops) need coordinates for markers.
                # Fuel Stop, Rest, Pickup, Dropoff.
                
                # Advance distance
                seg_dist = segment.get('distance_miles', 0.0)
                driven_dist += seg_dist
                
            elif segment['type'] in ['on_duty', 'off_duty', 'sleeper']:
                # This affects Fuel Stops, Rest Breaks, Pickup, Dropoff
                
                # If Pickup (driven_dist = 0), get start.
                # If Fuel/Rest (happens at driven_dist), get coord.
                
                # Need to distinguish "Pickup" from generic on_duty?
                # Using description or existing distance check.
                
                coord = get_coordinate_at_distance(full_path, driven_dist)
                if coord:
                    segment['latitude'] = coord[0]
                    segment['longitude'] = coord[1]
        
        response_data = {
            'route': {
                'total_distance': total_dist,
                'total_duration': segments[-1]['start_time'] + segments[-1]['duration'],
                'polyline_leg1': route1['polyline'],
                'polyline_leg2': route2['polyline']
            },
            'trip_segments': segments,
            'eld_logs': segments,
            'available_hours': 70 - final_hours_used,
            'total_trip_hours': segments[-1]['start_time'] + segments[-1]['duration']
        }
        
        return Response(response_data)
