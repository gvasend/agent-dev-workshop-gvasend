import googlemaps
import requests
from typing import Dict, Any

def convert_place_to_coordinates(address: str) -> Dict[str, Any]:
    """Convert a textual place name into coordinates using ADC authentication.

    Args:
        address: The name of the city or region (e.g., "Minneapolis, MN").
    """
    try:
        gmaps = googlemaps.Client()
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return {
                "lat": location["lat"],
                "lng": location["lng"],
                "formatted_address": geocode_result[0]["formatted_address"]
            }
    except Exception:
        pass
    return {}

def retrieve_weather_by_coordinates(lat: float, lng: float) -> str:
    """Retrieve raw real-time meteorological forecasts from the National Weather Service grid.

    Args:
        lat: Latitude coordinate.
        lng: Longitude coordinate.
    """
    try:
        headers = {"User-Agent": "WeatherAgentWorkshop/1.0"}
        points_url = f"https://api.weather.gov/points/{lat},{lng}"
        res = requests.get(points_url, headers=headers, timeout=10)
        if res.status_code == 200:
            forecast_url = res.json()["properties"]["forecast"]
            forecast_res = requests.get(forecast_url, headers=headers, timeout=10)
            if forecast_res.status_code == 200:
                return str(forecast_res.json()["properties"]["periods"][0])
    except Exception as e:
        return f"Weather service mapping error: {str(e)}"
    return "Weather telemetry unavailable."