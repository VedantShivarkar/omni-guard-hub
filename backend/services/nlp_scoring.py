import re
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_live_weather(lat: str, lon: str) -> dict:
    """Real OSINT: Fetch live weather data to cross-reference disaster claims."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or lat == 'None' or lon == 'None':
        return {"status": "unverified", "description": "no_data"}
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
        response = requests.get(url, timeout=3).json()
        return {
            "status": "verified",
            "condition": response.get("weather", [{}])[0].get("main", "").lower(),
            "description": response.get("weather", [{}])[0].get("description", "").lower(),
            "wind_speed": response.get("wind", {}).get("speed", 0)
        }
    except Exception:
        return {"status": "unverified", "description": "api_timeout"}

def analyze_distress_signal(text: str, lat: str = 'None', lon: str = 'None') -> dict:
    """
    Robust AI Triage & OSINT Verification.
    Cross-references user text with live meteorological data.
    """
    text_lower = text.lower()
    
    # 1. Base NLP Triage
    critical_keywords = ['trapped', 'drowning', 'unconscious', 'bleeding', 'urgent', 'help', 'collapse']
    flood_keywords = ['water', 'flood', 'rising', 'submerged']
    
    urgency_score = 0
    detected_flags = []
    
    for word in critical_keywords + flood_keywords:
        if word in text_lower:
            urgency_score += 2
            detected_flags.append(word)
            
    # Extract numbers for trapped people
    numbers = re.findall(r'\b\d+\b', text)
    people_count = int(numbers[0]) if numbers else 1
    if people_count > 2: urgency_score += 2
    
    severity = "CRITICAL" if urgency_score >= 4 else "WARNING" if urgency_score >= 2 else "INFO"

    # 2. OSINT Truth Verification
    truth_score = 50 # Base score
    osint_context = "No external verification possible."
    
    weather_data = fetch_live_weather(lat, lon)
    
    if weather_data["status"] == "verified":
        # Check if they claim flooding, and the weather API confirms heavy rain/storms
        claims_flood = any(word in text_lower for word in flood_keywords)
        actual_rain = "rain" in weather_data["condition"] or "storm" in weather_data["condition"]
        
        if claims_flood and actual_rain:
            truth_score += 45  # Highly verified claim
            osint_context = f"Verified: Meteorological data confirms {weather_data['description']} at coordinates."
        elif claims_flood and not actual_rain:
            truth_score -= 20  # Possible misinformation/panic
            osint_context = f"Discrepancy: User reports flooding, but OSINT shows {weather_data['condition']}."
        else:
            truth_score += 25  # General verification
            osint_context = f"Weather context: {weather_data['description']}."
    
    # Cap between 0 and 99
    truth_score = max(0, min(99, truth_score))

    return {
        "severity": severity,
        "urgency_score": urgency_score,
        "truth_verification_score": f"{truth_score}%",
        "extracted_flags": list(set(detected_flags)),
        "estimated_people": people_count,
        "osint_context": osint_context
    }