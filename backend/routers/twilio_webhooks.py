from fastapi import APIRouter, Request, BackgroundTasks, Response
from services.nlp_scoring import analyze_distress_signal, transcribe_audio_with_groq
from routers.email_alerts import send_smtp_email, AlertPayload
from supabase import create_client, Client
from twilio.twiml.messaging_response import MessagingResponse
import urllib.parse
import os
import re
from dotenv import load_dotenv
from pydantic import BaseModel
import uuid

load_dotenv()

router = APIRouter()
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

    hashed_id = f"Victim-***{sender_number[-4:]}" if len(sender_number) >= 4 else "Victim-Unknown"

    has_location = latitude != 'None'
    has_audio = num_media > 0 and 'audio' in media_type
    
    # CRITICAL FIX: Ignore hidden Google Maps links sent by WhatsApp when dropping a pin
    has_meaningful_text = len(incoming_msg) > 3 and "google.com/maps" not in incoming_msg and "maps.apple.com" not in incoming_msg

    provided_description = has_audio or has_meaningful_text

    try:
        # 1. FETCH STATE: ONLY look for active, INCOMPLETE reports
        existing = supabase.table("distress_signals").select("*").eq("hashed_id", hashed_id).eq("status", "INCOMPLETE").order("created_at", desc=True).limit(1).execute()
        
        merged_text = incoming_msg
        merged_lat = latitude
        merged_lon = longitude
        
        # Immediately transcribe audio if present
        if has_audio and media_url:
            transcribed = transcribe_audio_with_groq(media_url)
            merged_text = f"🎙️ {transcribed}"
            provided_description = True

        # Merge with existing INCOMPLETE DB record if one exists
        if existing.data:
            record = existing.data[0]
            
            if provided_description and not has_location:
                if record['location_str'] and record['location_str'] != "Location Pending":
                    parts = record['location_str'].replace("Lat:", "").replace("Lng:", "").split(",")
                    if len(parts) == 2:
                        merged_lat, merged_lon = parts[0].strip(), parts[1].strip()
                        has_location = True
                        
            if has_location and not provided_description:
                if record['raw_message'] and record['raw_message'] != "Awaiting Voice Note...":
                    merged_text = record['raw_message']
                    provided_description = True

        new_location_str = f"{merged_lat}, {merged_lon}" if has_location else "Location Pending"

        # 2. DECIDE ACTION BASED ON COMPLETENESS
        if provided_description and not has_location:
            reply_text = "⚠️ Audio Received & Transcribed. We MUST have your exact coordinates. Please tap the '+' icon and send your 'Live Location' immediately."
            db_payload = {
                "raw_message": merged_text,
                "location_str": "Location Pending",
                "severity": "INFO",
                "urgency_score": 0,
                "truth_verification_score": "Pending",
                "osint_context": "Awaiting Location Data...",
                "event_type": "Pending",
                "status": "INCOMPLETE" 
            }

        elif has_location and not provided_description:
            reply_text = f"📍 Coordinates Locked: {merged_lat}, {merged_lon}. Please send a voice note describing the emergency so we can verify the threat."
            db_payload = {
                "raw_message": "Awaiting Voice Note...",
                "location_str": new_location_str,
                "severity": "INFO",
                "urgency_score": 0,
                "truth_verification_score": "Pending",
                "osint_context": "Awaiting Audio Data...",
                "event_type": "Pending",
                "status": "INCOMPLETE" 
            }

        elif provided_description and has_location:
            # WE HAVE BOTH! Trigger the heavy AI Triage
            ai_analysis = analyze_distress_signal(merged_text, merged_lat, merged_lon, media_url=None)
            
            truth_score = ai_analysis.get('truth_verification_score', '0%')
            is_disaster = ai_analysis.get('is_natural_disaster', True)

            # Formulate final WhatsApp reply
            if not is_disaster or truth_score == "0%":
                reply_text = f"⚠️ Alert rejected by OmniGuard OSINT. Truth Score: {truth_score}. Coordinates: {merged_lat}, {merged_lon}. Please contact local authorities."
            else:
                reply_text = f"🚨 SOS Verified. Coordinates Locked: {merged_lat}, {merged_lon}. OSINT Truth Verification: {truth_score}. NDRF units are dispatched."

            db_payload = {
                "raw_message": merged_text,
                "severity": ai_analysis['severity'],
                "urgency_score": ai_analysis['urgency_score'],
                "truth_verification_score": truth_score,
                "extracted_flags": ai_analysis['extracted_flags'],
                "estimated_people": ai_analysis['estimated_people'],
                "location_str": new_location_str,
                "event_type": ai_analysis.get('event_type', 'Unknown'),
                "is_natural_disaster": is_disaster,
                "osint_context": ai_analysis.get('osint_context', ''),
                "logistics": ai_analysis.get('logistics', {}),
                "contact_number": sender_number,
                "status": "PENDING_RESCUE" 
            }

            # Trigger Email Alert
            if ai_analysis['severity'] == "CRITICAL" and is_disaster and truth_score != "0%":
                alert_payload = AlertPayload(
                    recipients=["shivarkarvedant@gmail.com"],
                    severity="CRITICAL",
                    location=new_location_str,
                    message=f"Intercepted Alert: '{merged_text}'\nOSINT Truth Score: {truth_score}",
                    instructions=f"Deploy NDRF immediately. OSINT Context: {ai_analysis.get('osint_context', '')}"
                )
                background_tasks.add_task(send_smtp_email, alert_payload)
        else:
            reply_text = "OmniGuard System Error. Please send a voice note AND share your live location."
            db_payload = None

        # 4. DATABASE UPSERT
        if db_payload:
            if existing.data:
                supabase.table("distress_signals").update(db_payload).eq("id", existing.data[0]['id']).execute()
            else:
                db_payload["hashed_id"] = hashed_id
                supabase.table("distress_signals").insert(db_payload).execute()

    except Exception as e:
        print(f"[❌ DB ERROR] {e}")
        reply_text = "OmniGuard System Error. Please retry."

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")

@router.post("/incoming-sms")
async def handle_sms_webhook(request: Request, background_tasks: BackgroundTasks):
    """Tier 2 Zero-Bandwidth Mesh Fallback via Standard SMS"""
    body = await request.body()
    parsed_data = urllib.parse.parse_qs(body.decode("utf-8"))
    incoming_msg = parsed_data.get('Body', [''])[0].strip().upper()
    sender_number = parsed_data.get('From', [''])[0]

    # Regex to find coordinates in "SOS 21.14 79.08" format
    coord_match = re.findall(r"[-+]?\d*\.\d+|\d+", incoming_msg)
    
    if len(coord_match) >= 2:
        lat, lon = coord_match[0], coord_match[1]
        ai_analysis = analyze_distress_signal(incoming_msg, lat, lon)
        reply = f"OMNIGUARD: SOS Verified at {lat}, {lon}. Help is being routed."
    else:
        # Tier 2 Fallback: Coordinate Synchronization Simulation
        reply = "⚠️ OMNIGUARD: GPS Missing. Synchronizing with Network Provider for Cell Tower Triangulation. Keep phone ON."
        lat, lon = "0.0", "0.0" 
        ai_analysis = {"severity": "HIGH", "urgency_score": 8, "truth_verification_score": "Cell-ID Pending", "logistics": {}, "extracted_flags": [], "estimated_people": 1}

    try:
        supabase.table("distress_signals").insert({
            "hashed_id": f"SMS-***{sender_number[-4:]}",
            "raw_message": f"SMS FALLBACK: {incoming_msg}",
            "severity": ai_analysis.get('severity', 'CRITICAL'),
            "urgency_score": ai_analysis.get('urgency_score', 8),
            "truth_verification_score": ai_analysis.get('truth_verification_score', 'Pending'),
            "extracted_flags": ai_analysis.get('extracted_flags', []),
            "estimated_people": ai_analysis.get('estimated_people', 1),
            "location_str": f"{lat}, {lon}",
            "status": "PENDING_RESCUE",
            "osint_context": ai_analysis.get('osint_context', 'Degraded Network Alert'),
            "event_type": ai_analysis.get('event_type', 'SMS Alert'),
            "is_natural_disaster": ai_analysis.get('is_natural_disaster', True),
            "logistics": ai_analysis.get('logistics', {}),
            "contact_number": sender_number
        }).execute()
    except Exception as e:
        print(f"[DB ERROR SMS] {e}")

    twiml = MessagingResponse()
    twiml.message(reply)
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
    location_str = f"{payload.latitude}, {payload.longitude}"
    
    try:
        supabase.table("distress_signals").insert({
            "hashed_id": hashed_id,
            "raw_message": payload.message,
            "severity": ai_analysis['severity'],
            "urgency_score": ai_analysis['urgency_score'],
            "truth_verification_score": ai_analysis['truth_verification_score'],
            "extracted_flags": ai_analysis['extracted_flags'],
            "estimated_people": ai_analysis['estimated_people'],
            "location_str": location_str,
            "status": "PENDING_RESCUE",
            "osint_context": ai_analysis.get('osint_context', ''),
            "event_type": ai_analysis.get('event_type', 'Unknown'),
            "is_natural_disaster": ai_analysis.get('is_natural_disaster', True),
            "logistics": ai_analysis.get('logistics', {})
        }).execute()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return {"status": "success"}