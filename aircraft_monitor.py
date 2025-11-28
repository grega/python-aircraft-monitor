import math
import time
import os
import requests
from dotenv import load_dotenv
from postmark import PMMail

load_dotenv()

API_ENDPOINT = os.getenv("API_ENDPOINT")
API_TOKEN = os.getenv("API_TOKEN")
LATITUDE = float(os.getenv("LATITUDE"))
LONGITUDE = float(os.getenv("LONGITUDE"))
RADIUS_KM = int(os.getenv("RADIUS_KM", 50))
LOW_ALTITUDE_THRESHOLD_M = int(os.getenv("LOW_ALTITUDE_THRESHOLD_M", 1000))
TARGET_AIRCRAFT_CODE = os.getenv("TARGET_AIRCRAFT_CODE")

POSTMARK_API_TOKEN = os.getenv("POSTMARK_API_TOKEN")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")

ALERT_DISTANCE_THRESHOLD_KM = float(os.getenv("ALERT_DISTANCE_THRESHOLD_KM", 50))
ALERT_TIME_THRESHOLD_MIN = float(os.getenv("ALERT_TIME_THRESHOLD_MIN", 30))
ALERT_ALTITUDE_THRESHOLD_M = float(os.getenv("ALERT_ALTITUDE_THRESHOLD_M", 1000))

def feet_to_meters(feet):
    """Convert altitude from feet to meters."""
    return feet * 0.3048

def send_email_alert(subject, message):
    """Send an email alert using Postmark."""
    try:
        email = PMMail(
            api_key=POSTMARK_API_TOKEN,
            subject=subject,
            sender=ALERT_EMAIL_FROM,
            to=ALERT_EMAIL_TO,
            text_body=message,
        )
        result = email.send()
        if result:
            print(f"Email alert sent successfully!")
        else:
            print(f"Failed to send email alert.")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

def should_send_alert(flight, lat, lon):
    """Check if the flight meets the alert thresholds."""
    altitude_ft = flight["position"].get("altitude", float("inf"))
    altitude_m = feet_to_meters(altitude_ft)
    distance_km = calculate_distance(flight, lat, lon)
    time_until_closest_min = time_until_closest(flight, lat, lon)

    return (
        altitude_m <= ALERT_ALTITUDE_THRESHOLD_M and
        distance_km <= ALERT_DISTANCE_THRESHOLD_KM and
        time_until_closest_min <= ALERT_TIME_THRESHOLD_MIN
    )

def get_flights_in_radius(lat, lon, radius_km=RADIUS_KM):
    """Fetch all flights within a given radius."""
    url = f"{API_ENDPOINT}/flights-in-radius?lat={lat}&lon={lon}&radius={radius_km}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    print(f"Fetching flights from: {url}")
    response = requests.get(url, headers=headers)
    print(f"Response status: {response.status_code}")
    return response.json()

def is_target_aircraft(flight):
    """Check if the flight matches the target aircraft code."""
    return flight["aircraft"].get("code") == TARGET_AIRCRAFT_CODE

def is_low_altitude(flight):
    """Check if the flight is below the low-altitude threshold."""
    altitude_ft = flight["position"].get("altitude", float("inf"))
    altitude_m = feet_to_meters(altitude_ft)
    return altitude_m < LOW_ALTITUDE_THRESHOLD_M

def calculate_distance(flight, lat, lon):
    """
    Calculate the 3D distance from the given coordinates to the flight.
    Includes altitude in meters.
    """
    pos = flight["position"]
    lat0, lon0 = pos["latitude"], pos["longitude"]
    alt_m = feet_to_meters(pos.get("altitude", 0))

    dx_km = (lat0 - lat) * 111
    dy_km = (lon0 - lon) * 111
    horizontal_distance_km = math.sqrt(dx_km**2 + dy_km**2)
    horizontal_distance_m = horizontal_distance_km * 1000
    distance_3d_m = math.sqrt(horizontal_distance_m**2 + alt_m**2)

    return distance_3d_m / 1000

def deg2rad(deg):
    return deg * math.pi / 180

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Rough distance in km for short distances using flat Earth approximation."""
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111

def time_until_closest(flight, lat, lon):
    """
    Compute time until closest point of approach (CPA) to (lat, lon).
    Uses current heading and ground_speed.
    Returns minutes until CPA. If already past CPA or speed=0, returns float('inf').
    Thanks ChatGPT.
    """
    pos = flight["position"]
    lat0, lon0 = pos["latitude"], pos["longitude"]
    speed_kmh = pos.get("ground_speed", 0)
    heading_deg = pos.get("heading", 0)

    if speed_kmh == 0:
        return float("inf")

    heading_rad = deg2rad(heading_deg)

    vx = math.sin(heading_rad) * speed_kmh
    vy = math.cos(heading_rad) * speed_kmh

    dx = (lat0 - lat) * 111
    dy = (lon0 - lon) * 111

    dot = dx * vx + dy * vy
    speed_sq = vx**2 + vy**2
    t_cpa = -dot / speed_sq if speed_sq != 0 else float("inf")

    if t_cpa < 0:
        return float("inf") # closest approach was in the past

    return t_cpa * 60

def monitor_flights(lat, lon, radius_km=RADIUS_KM, poll_interval=30):
    """Monitor flights and alert for target aircraft, highlighting low-altitude ones."""
    print(f"Monitoring for {TARGET_AIRCRAFT_CODE}s within {radius_km}km of ({lat}, {lon})...")
    while True:
        flights_data = get_flights_in_radius(lat, lon, radius_km)
        print(f"Found {len(flights_data.get('flights', []))} flights in radius.")
        if flights_data.get("found"):
            target_aircrafts_found = []
            for flight in flights_data["flights"]:
                if is_target_aircraft(flight):
                    target_aircrafts_found.append(flight)

            if target_aircrafts_found:
                print(f"\n--- {len(target_aircrafts_found)} {TARGET_AIRCRAFT_CODE}(s) detected ---")
                for flight in target_aircrafts_found:
                    flight_id = next(
                        (v for v in [flight.get("number"), flight.get("callsign"), flight.get("icao_24bit")] if v and v != "N/A"),
                        "N/A"
                    )
                    altitude_ft = flight["position"].get("altitude", "unknown")
                    altitude_m = feet_to_meters(altitude_ft) if altitude_ft != "unknown" else "unknown"
                    distance_km = calculate_distance(flight, lat, lon)
                    minutes_until_closest = time_until_closest(flight, lat, lon)

                    if is_low_altitude(flight):
                        alert_message = (
                            f"🚨 LOW ALTITUDE ALERT: {TARGET_AIRCRAFT_CODE} {flight_id} "
                            f"at {altitude_m:.0f}m, {distance_km:.1f}km away, "
                            f"{minutes_until_closest:.1f} minutes until closest approach."
                        )
                        print(alert_message)
                    else:
                        print(
                            f"ℹ️ {TARGET_AIRCRAFT_CODE} detected: {flight_id} "
                            f"at {altitude_m:.0f}m, {distance_km:.1f}km away, "
                            f"{minutes_until_closest:.1f} minutes until closest approach."
                        )

                    if should_send_alert(flight, lat, lon):
                        send_email_alert(f"Aircraft {TARGET_AIRCRAFT_CODE} Alert", alert_message)
                    else:
                        print("Alert thresholds not met. Skipping email.")

                print("---")
            else:
                print(f"No {TARGET_AIRCRAFT_CODE}s detected in this poll.")
        time.sleep(poll_interval)

if __name__ == "__main__":
    monitor_flights(LATITUDE, LONGITUDE, RADIUS_KM)
