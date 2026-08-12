import logging
import urllib.request
import urllib.parse
import json
from flask import current_app

logger = logging.getLogger(__name__)

class WeatherService:
    @staticmethod
    def _assess_agri_risk(temp_c, humidity, precip_mm, condition_text):
        """Assess agricultural disease risk based on meteorological parameters."""
        condition_lower = condition_text.lower()
        is_wet = precip_mm > 0.5 or any(w in condition_lower for w in ['rain', 'drizzle', 'shower', 'thunderstorm'])
        
        if humidity >= 80 and (15 <= temp_c <= 30):
            return {
                "level": "High",
                "badge_class": "bg-danger",
                "text_class": "text-danger",
                "summary": "उच्च जोखिम (High Risk)",
                "recommendation": "उच्च आर्द्रता और अनुकूल तापमान के कारण फफूंद (Fungus/Blight) का खतरा अधिक है।"
            }
        elif is_wet or humidity >= 65:
            return {
                "level": "Moderate",
                "badge_class": "bg-warning text-dark",
                "text_class": "text-warning",
                "summary": "मध्यम जोखिम (Moderate Risk)",
                "recommendation": "नमी अधिक है, फसल पत्तियों का नियमित निरीक्षण करें।"
            }
        else:
            return {
                "level": "Low",
                "badge_class": "bg-success",
                "text_class": "text-success",
                "summary": "कम जोखिम (Low Risk)",
                "recommendation": "मौसम फसल स्वास्थ्य के लिए अनुकूल है।"
            }

    @classmethod
    def get_weather(cls, location=None, lat=None, lon=None):
        """
        Fetch current weather from WeatherAPI.com or fallback to demo data.
        location can be a city name, or lat/lon coordinates.
        """
        api_key = current_app.config.get('WEATHER_API_KEY')
        
        # Build location query parameter
        if lat is not None and lon is not None:
            query = f"{lat},{lon}"
        elif location:
            query = location
        else:
            query = "auto:ip"

        if not api_key:
            return cls._get_demo_weather()

        try:
            encoded_query = urllib.parse.quote(query)
            url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={encoded_query}"
            req = urllib.request.Request(url, headers={'User-Agent': 'AgriVisionAI/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            current = data.get('current', {})
            loc = data.get('location', {})
            
            temp_c = current.get('temp_c', 28.0)
            humidity = current.get('humidity', 60)
            precip_mm = current.get('precip_mm', 0.0)
            condition_info = current.get('condition', {})
            condition_text = condition_info.get('text', 'Clear')
            icon = condition_info.get('icon', '')
            if icon.startswith('//'):
                icon = 'https:' + icon
                
            risk = cls._assess_agri_risk(temp_c, humidity, precip_mm, condition_text)
            
            return {
                "success": True,
                "city": loc.get('name', 'Local Area'),
                "region": loc.get('region', ''),
                "country": loc.get('country', ''),
                "temp_c": round(temp_c, 1),
                "temp_f": round(current.get('temp_f', 82.4), 1),
                "feelslike_c": round(current.get('feelslike_c', temp_c), 1),
                "humidity": humidity,
                "wind_kph": current.get('wind_kph', 10.0),
                "precip_mm": precip_mm,
                "condition": condition_text,
                "icon": icon,
                "risk": risk
            }
        except Exception as e:
            logger.warning("Weather API request failed (%s), returning demo weather.", e)
            return cls._get_demo_weather()

    @staticmethod
    def _get_demo_weather():
        """Fallback demo weather response."""
        return {
            "success": True,
            "demo": True,
            "city": "New Delhi",
            "region": "Delhi",
            "country": "India",
            "temp_c": 28.5,
            "temp_f": 83.3,
            "feelslike_c": 29.0,
            "humidity": 65,
            "wind_kph": 12.0,
            "precip_mm": 0.0,
            "condition": "Partly Cloudy",
            "icon": "https://cdn.weatherapi.com/weather/64x64/day/116.png",
            "risk": {
                "level": "Moderate",
                "badge_class": "bg-warning text-dark",
                "text_class": "text-warning",
                "summary": "मध्यम जोखिम (Moderate Risk)",
                "recommendation": "नमी अधिक है, फसल पत्तियों का नियमित निरीक्षण करें।"
            }
        }
