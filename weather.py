import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

def get_weather(lat=40.56, lon=-111.93):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&temperature_unit=fahrenheit"
        "&windspeed_unit=mph"
    )
    
    
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(connect=0, read=0, redirect=0)))
    try:
        data = session.get(url, timeout=(5, None)).json()["current_weather"]
    except:
        data = {}
    
    if data:
        to_send = {
            "temperature": data["temperature"],
            "wind_speed": data["windspeed"],
            "wind_dir": data["winddirection"],
            "condition": WEATHER_CODES.get(data["weathercode"], "Unknown"),
            }
    else:
        to_send = {
            "temperature": None,
            "wind_speed": None,
            "wind_dir": None,
            "condition": None,
            }
    return to_send