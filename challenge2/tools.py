"""Weather and Geocoding tools for the Google ADK 2.0 ecosystem."""

from typing import Dict, Any, Optional
import requests
import googlemaps


def convert_place_to_coordinates(address: str) -> Dict[str, Any]:
    """Convert a textual place name into coordinates using ADC authentication.

    Args:
        address: The name of the city or region (e.g., "Minneapolis, MN").
    """
    try:
        # Initializing without arguments automatically leverages the local gcloud ADC identity
        gmaps = googlemaps.Client()
        geocode_result = gmaps.geocode(address)
        
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return {
                "lat": location["lat"],
                "lng": location["lng"],
                "formatted_address": geocode_result[0]["formatted_address"]
            }
    except Exception as e:
        # Catch and handle network or resolution anomalies safely
        pass
        
    return {}


def retrieve_weather_by_coordinates(latitude: float, longitude: float) -> Optional[str]:
    """Retrieve the current real-time forecast directly from the National Weather Service.

    Args:
        latitude: The precise latitude coordinate.
        longitude: The precise longitude coordinate.

    Returns:
        A text string summarizing the current weather forecast periods,
        or None if data extraction fails.
    """
    headers = {"User-Agent": "(WeatherScoutAgent, gvasend@gmail.com)"}
    points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
    
    try:
        points_res = requests.get(points_url, headers=headers, timeout=10)
        points_res.raise_for_status()
        points_data = points_res.json()
        
        forecast_url = points_data["properties"]["forecast"]
        
        forecast_res = requests.get(forecast_url, headers=headers, timeout=10)
        forecast_res.raise_for_status()
        forecast_data = forecast_res.json()
        
        periods = forecast_data["properties"]["periods"]
        summary_runs = []
        for period in periods[:3]:
            summary_runs.append(f"{period['name']}: {period['detailedForecast']}")
            
        return "\n".join(summary_runs)
    except Exception:
        return None