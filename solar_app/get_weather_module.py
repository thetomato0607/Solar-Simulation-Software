import requests

# Replace this with your real OpenWeatherMap API key
OPENWEATHER_API_KEY = "5a5e2d188de250bb48180caf4d086ec0"

# --- Get Current Weather and Estimated Irradiance ---
def get_weather(lat, lon):
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}&exclude=minutely,daily,alerts"
        f"&units=metric&appid={OPENWEATHER_API_KEY}"
    )

    try:
        response = requests.get(url)
        data = response.json()

        if "current" not in data or "hourly" not in data:
            return {"error": "No 'current' or 'hourly' data returned."}

        current = data["current"]
        hourly = data["hourly"][:48]  # Get next 48 hours

        forecast = []
        for h in hourly:
            timestamp = h["dt"]
            uvi = h.get("uvi", 0)
            irr = round(uvi * 0.12, 2)  # Estimate kWh/m²
            forecast.append((timestamp, irr))

        return {
            "clouds": current.get("clouds", "N/A"),
            "description": current["weather"][0]["description"].capitalize(),
            "uvi": current.get("uvi", None),
            "irradiance_kwh_per_m2": round(current.get("uvi", 0) * 0.12, 2),
            "forecast": forecast,
            "tip": "☀️ Great conditions!" if current.get("uvi", 0) > 6 else "🌥 Consider tilt optimization."
        }

    except Exception as e:
        return {"error": str(e)}


# --- Convert City Name to Latitude/Longitude ---
import requests

OPENWEATHER_API_KEY = "5a5e2d188de250bb48180caf4d086ec0"  # 🔐 Put your real key here

def get_coordinates(city_name):
    """Returns (lat, lon) from a city string using OpenWeatherMap Geo API."""
    
    # Clean user input — convert "UK" to "GB"
    city_name = city_name.replace(", UK", ",GB").replace(",UK", ",GB")

    # Append GB if country code not given
    if ',' not in city_name:
        city_name += ",GB"

    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OPENWEATHER_API_KEY}"

    try:
        print("[DEBUG] Requesting:", url)
        response = requests.get(url)
        print("[DEBUG] Response status:", response.status_code)
        print("[DEBUG] Raw response text:", response.text)

        data = response.json()

        if not data:
            print(f"[DEBUG] No results returned for '{city_name}'")
            return None, None

        lat = data[0]["lat"]
        lon = data[0]["lon"]
        return lat, lon

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        return None, None
