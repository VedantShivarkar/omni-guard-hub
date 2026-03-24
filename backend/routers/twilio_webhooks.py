from fastapi import APIRouter, Request, BackgroundTasks
from services.nlp_scoring import analyze_distress_signal
from routers.email_alerts import send_smtp_email, AlertPayload
from supabase import create_client, Client
import urllib.parse
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import uuid

load_dotenv()

router = APIRouter()

# Initialize Supabase connection
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


@router.post("/incoming-whatsapp")
async def handle_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    parsed_data = urllib.parse.parse_qs(body.decode("utf-8"))

    # --- NEW: audio interception ---
    num_media = int(parsed_data.get('NumMedia', ['0'])[0])
    media_url = parsed_data.get('MediaUrl0', [None])[0]
    media_type = parsed_data.get('MediaContentType0', [''])[0]

    # Standard text fallback
    incoming_msg = parsed_data.get('Body', [''])[0]

    # Simulated transcription if audio received
    if num_media > 0 and 'audio' in media_type:
        print(f"[AUDIO RECEIVED] Twilio URL: {media_url}")
        incoming_msg = "[VOICE NOTE TRANSCRIBED]: The water is rising to the second floor, 4 people trapped, please hurry!"

    sender_number = parsed_data.get('From', [''])[0]
    latitude = parsed_data.get('Latitude', ['None'])[0]
    longitude = parsed_data.get('Longitude', ['None'])[0]

    # pass lat/lon into NLP
    ai_analysis = analyze_distress_signal(incoming_msg, latitude, longitude)

    hashed_id = f"Victim-***{sender_number[-4:]}" if len(sender_number) >= 4 else "Victim-Unknown"
    location_str = f"{latitude}, {longitude}" if latitude != 'None' else "Location Not Provided"

    # --- Push to Supabase ---
    try:
        db_payload = {
            "hashed_id": hashed_id,
            "raw_message": incoming_msg,
            "severity": ai_analysis['severity'],
            "urgency_score": ai_analysis['urgency_score'],
            "truth_verification_score": ai_analysis['truth_verification_score'],
            "extracted_flags": ai_analysis['extracted_flags'],
            "estimated_people": ai_analysis['estimated_people'],
            "location_str": location_str,
            "status": "PENDING_RESCUE"
        }
        supabase.table("distress_signals").insert(db_payload).execute()
        print(f"[DB] Signal {hashed_id} logged to Supabase.")
    except Exception as e:
        print(f"[DB ERROR] {e}")

    # Email dispatcher
    if ai_analysis['severity'] == "CRITICAL":
        alert_payload = AlertPayload(
            recipients=["shivarkarvedant@gmail.com"],
            severity="CRITICAL",
            location=location_str,
            message=f"Intercepted: '{incoming_msg}'. AI detected {ai_analysis['estimated_people']} people at risk.",
            instructions="Deploy nearest rescue unit immediately."
        )
        background_tasks.add_task(send_smtp_email, alert_payload)

    return {"status": "received", "ai_processed": True}


@router.get("/signals")
async def get_all_signals():
    try:
        response = supabase.table("distress_signals").select("*").order("created_at", desc=True).execute()
        return {"data": response.data}
    except Exception as e:
        return {"error": str(e)}


class WebSignalPayload(BaseModel):
    message: str
    latitude: str
    longitude: str
    contact: str = "Anonymous-Web"


@router.post("/incoming-web")
async def handle_web_submission(payload: WebSignalPayload, background_tasks: BackgroundTasks):
    ai_analysis = analyze_distress_signal(payload.message, payload.latitude, payload.longitude)

    hashed_id = f"Web-***{str(uuid.uuid4())[:4]}"
    location_str = f"Lat: {payload.latitude}, Lng: {payload.longitude}"

    try:
        db_payload = {
            "hashed_id": hashed_id,
            "raw_message": payload.message,
            "severity": ai_analysis['severity'],
            "urgency_score": ai_analysis['urgency_score'],
            "truth_verification_score": ai_analysis['truth_verification_score'],
            "extracted_flags": ai_analysis['extracted_flags'],
            "estimated_people": ai_analysis['estimated_people'],
            "location_str": location_str,
            "status": "PENDING_RESCUE"
        }
        supabase.table("distress_signals").insert(db_payload).execute()
        print(f"[DB] Web Signal {hashed_id} logged to Supabase.")
    except Exception as e:
        print(f"[DB ERROR] {e}")

    if ai_analysis['severity'] == "CRITICAL":
        alert_payload = AlertPayload(
            recipients=["shivarkarvedant@gmail.com"],
            severity="CRITICAL",
            location=location_str,
            message=f"Intercepted Web Report: '{payload.message}'. AI detected {ai_analysis['estimated_people']} people at risk.",
            instructions="Deploy nearest rescue unit immediately."
        )
        background_tasks.add_task(send_smtp_email, alert_payload)

    return {"status": "success"}