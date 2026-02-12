import math

def decode_polyline(polyline_str):
    """Decodes a Google-encoded polyline string into a list of (lat, lng) tuples."""
    index, len_str = 0, len(polyline_str)
    lat, lng = 0, 0
    coordinates = []

    while index < len_str:
        shift, result = 0, 0
        while True:
            byte = ord(polyline_str[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            if byte < 0x20:
                break
        d_lat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += d_lat

        shift, result = 0, 0
        while True:
            byte = ord(polyline_str[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            if byte < 0x20:
                break
        d_lng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += d_lng

        coordinates.append((lat / 100000.0, lng / 100000.0))

    return coordinates

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates distance in miles between two points."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_coordinate_at_distance(path, target_miles):
    """
    Interpolates a coordinate along a path at a specific distance from the start.
    path: list of (lat, lng)
    target_miles: distance from start to find
    """
    if not path:
        return None
    if target_miles <= 0:
        return path[0]
    
    current_dist = 0.0
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i+1]
        dist_segment = haversine_distance(p1[0], p1[1], p2[0], p2[1])
        
        if current_dist + dist_segment >= target_miles:
            # Interpolate
            remaining = target_miles - current_dist
            if dist_segment == 0:
                return p1
            ratio = remaining / dist_segment
            lat = p1[0] + (p2[0] - p1[0]) * ratio
            lng = p1[1] + (p2[1] - p1[1]) * ratio
            return (lat, lng)
        
        current_dist += dist_segment
        
    return path[-1] # Return end if target > total length

def calculate_trip_segments(distance_miles, hours_already_used):
    """
    Calculate trip segments with HOS compliance and fuel stops.
    Returns segments list and updated cycle hours used.
    """
    segments = []
    
    # 70-hour / 8-day limit check
    available_cycle_hours = 70.0 - float(hours_already_used)
    if available_cycle_hours <= 0:
        raise ValueError("No hours available in 70-hour cycle")

    remaining_distance = float(distance_miles)
    avg_speed = 60.0  # mph
    
    current_trip_time = 0.0
    
    # Duration tracking
    driving_since_break = 0.0
    driving_daily = 0.0
    on_duty_daily = 0.0
    cycle_hours_consumed = 0.0
    
    miles_since_fuel = 0.0
    
    # --- 1. PICKUP (1 Hour On Duty) ---
    segments.append({
        'type': 'on_duty',
        'status': 'on_duty',
        'start_time': current_trip_time,
        'duration': 1.0,
        'description': 'Pickup at Origin',
        'distance_miles': 0.0
    })
    current_trip_time += 1.0
    on_duty_daily += 1.0
    cycle_hours_consumed += 1.0
    
    # --- 2. MAIN DRIVING LOOP ---
    while remaining_distance > 0:
        
        # Check if we hit 70-hour limit usage
        if cycle_hours_consumed >= available_cycle_hours:
            segments.append({
                'type': 'off_duty', 
                'status': 'off_duty',
                'start_time': current_trip_time,
                'duration': 0, 
                'description': 'REACHED 70-HOUR LIMIT',
                'distance_miles': 0.0
            })
            break

        # Calculate limits based on constraints
        
        # 1. Distance constraint (how long to drive to finish?)
        time_to_finish = remaining_distance / avg_speed
        
        # 2. 8-Hour Break Rule (Must drive max 8h before 30m break)
        time_to_break = 8.0 - driving_since_break
        if time_to_break <= 0: # Should have taken break
             time_to_break = 0
        
        # 3. 11-Hour Daily Drive Limit
        time_to_daily_limit = 11.0 - driving_daily
        
        # 4. 14-Hour Duty Window (Reset by 10h break)
        # We assume simplified window: Duty time accumulated.
        time_to_window_limit = 14.0 - on_duty_daily
        
        # 5. Fuel Stop (Every 1000 miles)
        dist_to_fuel = 1000.0 - miles_since_fuel
        time_to_fuel = dist_to_fuel / avg_speed
        
        # 6. 70-Hour Cycle Limit
        time_to_cycle_limit = available_cycle_hours - cycle_hours_consumed

        # Determine the limiting factor
        # We want to drive as much as possible, but limited by the MIN of all these.
        
        # If any "Time to X" is <= 0, we must perform an action.
        
        # Priority Actions:
        # A. 10-Hour Rest (Resets 11h and 14h)
        if time_to_daily_limit <= 0.001 or time_to_window_limit <= 0.001:
            segments.append({
                'type': 'sleeper',
                'status': 'sleeper',
                'start_time': current_trip_time,
                'duration': 10.0,
                'description': '10-hour Mandatory Rest',
                'distance_miles': 0.0
            })
            current_trip_time += 10.0
            # Reset daily counters
            driving_daily = 0.0
            on_duty_daily = 0.0
            driving_since_break = 0.0 # 10h rest also satisfies 30m break requirement
            # Sleeper does NOT consume cycle hours (usually) if off-duty/sleeper
            continue
            
        # B. 30-Minute Break (Resets 8h clock)
        if time_to_break <= 0.001:
            segments.append({
                'type': 'off_duty',
                'status': 'off_duty', 
                'start_time': current_trip_time,
                'duration': 0.5,
                'description': '30-minute Mandatory Break',
                'distance_miles': 0.0
            })
            current_trip_time += 0.5
            on_duty_daily += 0.5 # 14h window keeps ticking during break!
            driving_since_break = 0.0
            # Off duty break doesn't consume cycle hours
            continue
            
        # C. Drive!
        drive_duration = min(
            time_to_finish,
            time_to_break,
            time_to_daily_limit,
            time_to_window_limit,
            time_to_fuel,
            time_to_cycle_limit
        )
        
        # If drive_duration is tiny (floating point error), force action
        if drive_duration <= 0.001:
             # This means we are stuck on a limit.
             # Loop logic above should have caught <= 0, but if we are miniscule positive,
             # we might need to handle it.
             # Let's assume we proceed to next iteration to trigger the limit.
             # To avoid infinite loop, we must identify which limit is close.
             if time_to_daily_limit < 0.01: time_to_daily_limit = 0; continue
             if time_to_break < 0.01: time_to_break = 0; continue
             if time_to_window_limit < 0.01: time_to_window_limit = 0; continue
             
             # If completely stuck, break
             break

        # Execute Drive Segment
        dist_driven = drive_duration * avg_speed
        
        segments.append({
            'type': 'driving',
            'status': 'driving',
            'start_time': current_trip_time,
            'duration': drive_duration,
            'description': f'Driving {dist_driven:.1f} miles',
            'distance_miles': dist_driven
        })
        
        # Update State
        current_trip_time += drive_duration
        remaining_distance -= dist_driven
        
        driving_since_break += drive_duration
        driving_daily += drive_duration
        on_duty_daily += drive_duration
        cycle_hours_consumed += drive_duration
        miles_since_fuel += dist_driven
        
        # Check Fuel (If we stopped BECAUSE of fuel)
        # Using fuzzy comparison
        if abs(miles_since_fuel - 1000.0) < 0.1:
            segments.append({
                'type': 'on_duty',
                'status': 'on_duty',
                'start_time': current_trip_time,
                'duration': 0.5,
                'description': 'Fuel Stop',
                'distance_miles': 0.0
            })
            current_trip_time += 0.5
            on_duty_daily += 0.5
            cycle_hours_consumed += 0.5
            miles_since_fuel = 0.0
            
    # --- 3. DROPOFF (1 Hour On Duty) ---
    if remaining_distance <= 0.1:
        segments.append({
            'type': 'on_duty',
            'status': 'on_duty',
            'start_time': current_trip_time,
            'duration': 1.0,
            'description': 'Dropoff at Destination',
            'distance_miles': 0.0
        })
        cycle_hours_consumed += 1.0
        
    return segments, cycle_hours_consumed
