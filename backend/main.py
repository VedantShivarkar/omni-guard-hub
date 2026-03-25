from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import email_alerts, twilio_webhooks, admin_tools
from services.nlp_scoring import macro_osint_scan
from pydantic import BaseModel

app = FastAPI(
    title="OmniGuard Fusion Hub API",
    description="Headless Disaster Intelligence & Triage Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(email_alerts.router, prefix="/api/v1/alerts", tags=["Notifications"])
app.include_router(twilio_webhooks.router, prefix="/api/v1/twilio", tags=["Comms"])
app.include_router(admin_tools.router, prefix="/api/v1/admin", tags=["Tactical"])

class ScanRequest(BaseModel):
    region_name: str
    lat: str
    lon: str

@app.post("/api/v1/osint/global-scan", tags=["OSINT"])
async def trigger_global_scan(payload: ScanRequest):
    analysis = macro_osint_scan(payload.region_name, payload.lat, payload.lon)
    return {"status": "success", "region": payload.region_name, "intelligence": analysis}

@app.get("/")
async def health_check():
    return {"status": "OmniGuard Core is Online"}