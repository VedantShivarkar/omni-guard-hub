import os
import requests
import json
import re
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def fetch_live_weather(lat: str, lon: str) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    clean_lat = str(lat).replace("Lat:", "").strip()
    clean_lon = str(lon).replace("Lng:", "").strip()
    
    if not api_key or clean_lat.lower() in ['none', 'unknown', ''] or clean_lon.lower() in ['none', 'unknown', '']:
        return {"status": "unverified", "description": "no_data", "city": "Unknown"}
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={clean_lat}&lon={clean_lon}&appid={api_key}"
        res = requests.get(url, timeout=3).json()
        return {
            "status": "verified",
            "city": res.get("name", "Unknown"),
            "condition": res.get("weather", [{}])[0].get("main", "").lower(),
            "description": res.get("weather", [{}])[0].get("description", "").lower(),
            "wind_speed": res.get("wind", {}).get("speed", 0)
        }
    except Exception:
        return {"status": "unverified", "description": "api_timeout", "city": "Unknown"}

def fetch_social_media_intel(city: str) -> str:
    if city == "Unknown": return "No social media data available."
    headers = {'User-agent': 'OmniGuard-B2G-Bot 1.0'}
    url = f"https://www.reddit.com/search.json?q={city} (flood OR earthquake OR storm OR disaster)&sort=new&limit=3"
    try:
        res = requests.get(url, headers=headers, timeout=3).json()
        posts = [child['data']['title'] for child in res['data']['children']]
        if not posts: return f"No recent emergency posts found on social media for {city}."
        return "Recent Social Media Chatter: " + " | ".join(posts)
    except Exception:
        return "Social media API timeout."

def transcribe_audio_with_groq(media_url: str) -> str:
    if not GROQ_API_KEY: return "Audio transcription failed: No Groq API Key."
    temp_audio_path = "temp_incoming_audio.ogg"
    print("[🎤] Sending Audio to Groq Whisper...")
    try:
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        if twilio_sid and twilio_token:
            response = requests.get(media_url, auth=(twilio_sid, twilio_token))
        else:
            response = requests.get(media_url)
            
        if response.status_code != 200:
            raise Exception(f"Twilio blocked the audio download. HTTP Status: {response.status_code}")

        with open(temp_audio_path, "wb") as f:
            f.write(response.content)

        url = "https://api.groq.com/openai/v1/audio/translations"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        with open(temp_audio_path, "rb") as audio_file:
            files = {"file": ("audio.ogg", audio_file, "audio/ogg")}
            data = {"model": "whisper-large-v3"}
            res = requests.post(url, headers=headers, files=files, data=data)
            
        res_data = res.json()
        if 'error' in res_data: raise Exception(res_data['error']['message'])
        return res_data['text'].strip()
    except Exception as e:
        print(f"Groq Audio Error: {e}")
        return "Audio intelligence degraded. Manual verification required."
    finally:
        if os.path.exists(temp_audio_path): os.remove(temp_audio_path)

def analyze_distress_signal(text: str, lat: str = 'None', lon: str = 'None', media_url: str = None) -> dict:
    actual_text = transcribe_audio_with_groq(media_url) if media_url else text
    if not actual_text: actual_text = "No intelligence provided."

    weather_data = fetch_live_weather(lat, lon)
    social_data = fetch_social_media_intel(weather_data['city'])

    print("[🧠] Analyzing Data using Groq Llama-3.3-70B...")
    
    system_prompt = f"""
You are OmniGuard, a strict forensic AI Logistics Officer for the NDRF.
Analyze this Distress Signal against the Live Weather and Social Data.

Distress Signal: "{actual_text}"
City/Region Context: {weather_data['city']}
Live Weather API: {weather_data}
Social Media API: {social_data}

CRITICAL RULE 1: FORENSIC WEATHER VERIFICATION
If the user claims a flood, heavy rain, or storm, BUT the Live Weather API shows 'clear', 'haze', 'clouds', or low wind, THIS IS A FALSE ALARM.

CRITICAL RULE 2: NON-NDRF INCIDENTS & LIFE-THREATENING ESCALATION
If the event is NOT a natural disaster (e.g., gunfire, robbery, power cut, medical emergency):
1. Set "is_natural_disaster" to false.
2. Identify the correct local department (e.g., Police 100, Electricity 1912, Ambulance 108) and put it in "local_authority_contact".
3. ESCALATION CHECK: Is this an immediate threat to life (e.g., active shooter, bleeding out, severe violence)?
   - If YES: Set "severity" to "CRITICAL", "urgency_score" to 9 or 10, and a high "truth_verification_score" based on context. Add "LIFE_THREATENING" to extracted_flags.
   - If NO (e.g., normal power outage, simple theft): Set "severity" to "INFO", "urgency_score" to 0-3, and "truth_verification_score" to "0%".

LOGISTICS OFFICER INSTRUCTION:
Generate operational deployment guidance based on severity, weather, terrain, and estimated_people.

Output ONLY valid JSON:
{{
    "is_natural_disaster": <boolean>,
    "event_type": "<e.g., Flood, Active Shooter, Power Outage>",
    "severity": "CRITICAL", "WARNING", or "INFO",
    "urgency_score": <int 0-10>,
    "truth_verification_score": "<percentage string, e.g. '0%' or '95%'>",
    "extracted_flags": ["<string>"],
    "estimated_people": <int>,
    "osint_context": "<Strict proof of weather match or mismatch>",
    "transcribed_text": "{actual_text}",
    "local_authority_contact": "<Provide correct emergency number/department if non-NDRF, else 'N/A'>",
    "logistics": {{
        "equipment": ["<list of deployment equipment>"],
        "personnel": "<team composition>",
        "burn_rate_warning": "<time critical survival window>"
    }}
}}
"""
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = { "Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json" }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": system_prompt}],
            "response_format": {"type": "json_object"} 
        }
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()
        if 'error' in res_data: raise Exception(res_data['error']['message'])
        
        result = json.loads(res_data['choices'][0]['message']['content'])
        
        # Hard override for safety
        if not result.get("is_natural_disaster", True) and result.get("severity") != "CRITICAL":
            if "FALSE CLAIM" in result.get("osint_context", ""):
                result["truth_verification_score"] = "0%"
                result["severity"] = "INFO"
            
        return result
        
    except Exception as e:
        print(f"Groq Analysis Error: {e}")
        return {
            "is_natural_disaster": True, "event_type": "Unknown",
            "severity": "INFO", "urgency_score": 0, "truth_verification_score": "0%",
            "extracted_flags": ["error"], "estimated_people": 0, 
            "osint_context": "API Error. Manual verification required.", "transcribed_text": actual_text,
            "local_authority_contact": "N/A",
            "logistics": {"equipment": ["Standard Requisition"], "personnel": "Standby", "burn_rate_warning": "N/A"}
        }

def fetch_global_news(query: str) -> str:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key or query == "Unknown": return "News OSINT offline."
    try:
        url = f"https://newsapi.org/v2/everything?q={query} AND (landslide OR tornado OR flood OR earthquake OR cyclone)&language=en&sortBy=publishedAt&pageSize=15&apiKey={api_key}"
        res = requests.get(url, timeout=4).json()
        if res.get("status") == "ok" and res.get("articles"):
            headlines = [f"[{a['source']['name']}] {a['title']}: {a['description']}" for a in res['articles']]
            return " | ".join(headlines)
        return f"No major critical news alerts found for {query}."
    except Exception as e:
        return "News API timeout."

def macro_osint_scan(region_name: str, lat: str, lon: str) -> dict:
    weather_data = fetch_live_weather(lat, lon)
    news_data = fetch_global_news(region_name)

    system_prompt = f"""
    You are OmniGuard Command, a strategic FEMA/NDRF disaster intelligence AI.
    Evaluate the live threat level for: "{region_name}".

    Live Global News API: {news_data}

    CRITICAL INSTRUCTION FOR COMPREHENSIVE REPORTING:
    Provide a detailed, multi-incident report for the entire region based on News data AND your internal knowledge of current events.
    
    CASUALTY & GEOLOCATION RULE:
    1. You MUST synthesize realistic integer casualty estimates if exact figures are missing. 
    2. You MUST provide approximate 'approx_lat' and 'approx_lng' coordinates for WHERE this incident is happening so we can plot it on a GIS map.

    Output ONLY valid JSON matching this exact structure:
    {{
        "threat_level": "DEFCON 1", "DEFCON 3", or "CLEAR",
        "primary_hazard": "Multiple Cascading Disasters",
        "confidence_score": "98%",
        "executive_summary": "A harsh 2-sentence summary of the multiple crises.",
        "active_incidents": [
            {{
                "location": "<Exact area>",
                "type": "<e.g., Landslide>",
                "approx_lat": <float coordinate>,
                "approx_lng": <float coordinate>,
                "dead": <integer>,
                "injured": <integer>,
                "trapped_or_missing": <integer>,
                "action_taken": "<1-sentence summary of local response>",
                "suggested_ndrf_action": "<1-sentence strategic deployment recommendation>"
            }}
        ]
    }}
    """
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = { "Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json" }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": system_prompt}],
            "response_format": {"type": "json_object"} 
        }
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()
        if 'error' in res_data: raise Exception(res_data['error']['message'])
        return json.loads(res_data['choices'][0]['message']['content'])
        
    except Exception as e:
        return {
            "threat_level": "UNKNOWN", "primary_hazard": "System Degradation", "confidence_score": "0%",
            "executive_summary": "OSINT APIs failed to return data.", "active_incidents": []
        }