from fastapi import APIRouter, Request, BackgroundTasks, Response
from services.nlp_scoring import analyze_distress_signal
from routers.email_alerts import send_smtp_email, AlertPayload
from supabase import create_client, Client
from twilio.twiml.messaging_response import MessagingResponse
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

    num_media = int(parsed_data.get('NumMedia', ['0'])[0])
    media_url = parsed_data.get('MediaUrl0', [None])[0]
    media_type = parsed_data.get('MediaContentType0', [''])[0]
    incoming_msg = parsed_data.get('Body', [''])[0].strip()
    
    sender_number = parsed_data.get('From', [''])[0]
    latitude = parsed_data.get('Latitude', ['None'])[0]
    longitude = parsed_data.get('Longitude', ['None'])[0]

    has_location = latitude != 'None'
    has_audio = num_media > 0 and 'audio' in media_type
    has_text = len(incoming_msg) > 0

    reply_text = ""
    run_full_pipeline = False

    # CONVERSATIONAL LOGIC
    if (has_audio or has_text) and not has_location:
        reply_text = "⚠️ Audio Received & Transcribed. We MUST have your exact coordinates. Please tap the '+' icon and send your 'Live Location' immediately."
        run_full_pipeline = True

    elif has_location and not (has_audio or has_text):
        reply_text = "📍 Coordinates Locked. NDRF Rapid Response Team has been dispatched to your exact location. ETA 12 mins. Stay high and remain visible."
        run_full_pipeline = True
        incoming_msg = "Location ping received. Waiting for audio intelligence."
        media_url = None

    elif has_location and (has_audio or has_text):
        reply_text = "🚨 SOS Verified. Coordinates and Audio Intelligence locked. NDRF units are en route."
        run_full_pipeline = True
    else:
        reply_text = "OmniGuard System: Please send a voice note detailing your emergency AND share your live location."

    # --- STATEFUL PIPELINE EXECUTION ---
    if run_full_pipeline:
        ai_analysis = analyze_distress_signal(incoming_msg, latitude, longitude, media_url)

        hashed_id = f"Victim-***{sender_number[-4:]}" if len(sender_number) >= 4 else "Victim-Unknown"
        new_location_str = f"{latitude}, {longitude}" if has_location else "Location Pending"
        new_message_str = f"🎙️ {ai_analysis['transcribed_text']}" if has_audio else incoming_msg

        try:
            # 1. Check if this victim already has an active rescue signal
            existing = supabase.table("distress_signals").select("*").eq("hashed_id", hashed_id).eq("status", "PENDING_RESCUE").order("created_at", desc=True).limit(1).execute()

            if existing.data:
                # 2. MERGE LOGIC: Update the existing row instead of creating a second one
                record = existing.data[0]
                final_loc = new_location_str if has_location else record['location_str']
                
                # Keep the original voice text if this webhook is just a location ping
                final_msg = record['raw_message'] if (has_location and not has_audio and not has_text) else new_message_str

                supabase.table("distress_signals").update({
                    "raw_message": final_msg,
                    "location_str": final_loc,
                    "severity": ai_analysis['severity'],
                    "urgency_score": ai_analysis['urgency_score'],
                    "truth_verification_score": ai_analysis['truth_verification_score'],
                    "extracted_flags": ai_analysis['extracted_flags'],
                    "estimated_people": ai_analysis['estimated_people']
                }).eq("id", record['id']).execute()
                print(f"[✅ DB] Successfully merged audio and location for {hashed_id}")

                # Trigger Email only if it just hit CRITICAL + Location received
                if ai_analysis['severity'] == "CRITICAL" and has_location and record['location_str'] == "Location Pending":
                    alert_payload = AlertPayload(
                        recipients=["shivarkarvedant@gmail.com"],
                        severity="CRITICAL",
                        location=final_loc,
                        message=f"Merged Alert: '{final_msg}'",
                        instructions="Deploy NDRF immediately."
                    )
                    background_tasks.add_task(send_smtp_email, alert_payload)

            else:
                # 3. No active record exists, INSERT a new one
                db_payload = {
                    "hashed_id": hashed_id,
                    "raw_message": new_message_str,
                    "severity": ai_analysis['severity'],
                    "urgency_score": ai_analysis['urgency_score'],
                    "truth_verification_score": ai_analysis['truth_verification_score'],
                    "extracted_flags": ai_analysis['extracted_flags'],
                    "estimated_people": ai_analysis['estimated_people'],
                    "location_str": new_location_str,
                    "status": "PENDING_RESCUE"
                }
                supabase.table("distress_signals").insert(db_payload).execute()
                print(f"[✅ DB] Inserted new signal for {hashed_id}")

                if ai_analysis['severity'] == "CRITICAL" and has_location:
                    alert_payload = AlertPayload(
                        recipients=["shivarkarvedant@gmail.com"],
                        severity="CRITICAL",
                        location=new_location_str,
                        message=f"Intercepted Alert: '{new_message_str}'",
                        instructions="Deploy NDRF immediately."
                    )
                    background_tasks.add_task(send_smtp_email, alert_payload)

        except Exception as e:
            print(f"[❌ DB ERROR] {e}")

    # Reply to WhatsApp
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")

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
    except Exception as e:
        print(f"[DB ERROR] {e}")

    if ai_analysis['severity'] == "CRITICAL":
        alert_payload = AlertPayload(
            recipients=["shivarkarvedant@gmail.com"],
            severity="CRITICAL",
            location=location_str,
            message=f"Intercepted Web Report: '{payload.message}'.",
            instructions="Deploy nearest rescue unit immediately."
        )
        background_tasks.add_task(send_smtp_email, alert_payload)

    return {"status": "success"}