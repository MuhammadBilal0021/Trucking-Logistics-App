import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

ORS_TIMEOUT = 30        # seconds
ORS_MAX_RETRIES = 2     # retry up to 2 times on transient errors
ORS_RETRY_BACKOFF = 2   # seconds (doubles each retry)
GEOCODE_TIMEOUT = 15    # seconds


def _get_ors_api_key():
    return os.getenv('ORS_API_KEY')


def geocode_location(location_name):
    """
    Geocodes a location name to (lat, lng) using Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': location_name,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'TruckingLogisticsApp/1.0'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=GEOCODE_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


def get_route_details(start_coords, end_coords):
    """
    Gets route details from OpenRouteService with retry logic.
    Returns:
        dict: {
            'distance_miles': float,
            'duration_hours': float,
            'polyline': str (encoded)
        }
        or None on failure.
    """
    ors_api_key = _get_ors_api_key()
    if not ors_api_key:
        raise ValueError("ORS_API_KEY not found in environment variables")

    url = "https://api.openrouteservice.org/v2/directions/driving-hgv"
    headers = {
        'Authorization': ors_api_key,
        'Content-Type': 'application/json'
    }

    # ORS expects [lon, lat]
    body = {
        "coordinates": [
            [start_coords[1], start_coords[0]],
            [end_coords[1], end_coords[0]]
        ]
    }

    last_error = None
    for attempt in range(1 + ORS_MAX_RETRIES):
        try:
            response = requests.post(url, json=body, headers=headers, timeout=ORS_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            route = data['routes'][0]
            summary = route['summary']

            # Convert distance (meters) to miles
            distance_miles = summary['distance'] * 0.000621371

            # Convert duration (seconds) to hours
            duration_hours = summary['duration'] / 3600

            return {
                'distance_miles': distance_miles,
                'duration_hours': duration_hours,
                'polyline': route['geometry']
            }
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            print(f"Routing attempt {attempt + 1}/{1 + ORS_MAX_RETRIES} failed (timeout/connection): {e}")
        except requests.exceptions.HTTPError as e:
            last_error = e
            status_code = e.response.status_code if e.response is not None else None
            if status_code in (502, 503, 504):
                print(f"Routing attempt {attempt + 1}/{1 + ORS_MAX_RETRIES} failed ({status_code}): {e}")
            else:
                # Non-transient HTTP error (4xx, etc.) — don't retry
                print(f"Routing error (non-retryable {status_code}): {e}")
                return None
        except Exception as e:
            print(f"Routing error (unexpected): {e}")
            return None

        # Backoff before next retry
        if attempt < ORS_MAX_RETRIES:
            wait = ORS_RETRY_BACKOFF * (2 ** attempt)
            print(f"Retrying in {wait}s...")
            time.sleep(wait)

    print(f"Routing failed after {1 + ORS_MAX_RETRIES} attempts. Last error: {last_error}")
    return None
