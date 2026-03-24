import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Load environment variables (your App Password)
load_dotenv()

router = APIRouter()

# Define the expected JSON payload from the frontend
class AlertPayload(BaseModel):
    recipients: List[str]
    severity: str  # e.g., "CRITICAL", "WARNING", "INFO"
    location: str
    message: str
    instructions: str

def send_smtp_email(payload: AlertPayload):
    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        raise ValueError("Server configuration error: Missing SMTP credentials.")

    # Format the email to look official and urgent
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 2px solid #dc2626; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #dc2626; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0; tracking: 2px;">OMNIGUARD EMERGENCY ALERT</h1>
                <p style="margin: 5px 0 0 0; font-weight: bold;">SEVERITY: {payload.severity.upper()}</p>
            </div>
            <div style="padding: 20px; background-color: #f9fafb;">
                <h2 style="color: #1f2937;">Location: {payload.location}</h2>
                <p style="color: #4b5563; font-size: 16px; line-height: 1.5;">{payload.message}</p>
                <div style="background-color: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; margin-top: 20px;">
                    <h3 style="margin-top: 0; color: #991b1b;">Immediate Instructions:</h3>
                    <p style="margin-bottom: 0; color: #7f1d1d;">{payload.instructions}</p>
                </div>
                <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 25px 0;" />
                <p style="font-size: 12px; color: #6b7280; text-align: center;">
                    This is an automated message from the OmniGuard Disaster Intelligence Engine.<br>
                    Dispatched securely via verified channels.
                </p>
            </div>
        </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{payload.severity.upper()}] OmniGuard Alert: {payload.location}"
    msg["From"] = f"OmniGuard Fusion Hub <{sender_email}>"
    msg["To"] = ", ".join(payload.recipients)
    
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Connect to Google's SMTP server
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, payload.recipients, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {e}")
        raise e

@router.post("/dispatch")
async def dispatch_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    """
    Triggers an emergency email blast. 
    Uses BackgroundTasks so the API responds instantly, preventing latency.
    """
    try:
        # We pass the email function to a background task so the frontend doesn't hang
        background_tasks.add_task(send_smtp_email, payload)
        return {"status": "success", "message": f"Alert queued for {len(payload.recipients)} recipients."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))