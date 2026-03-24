from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import email_alerts
# We will uncomment the twilio router in the next step
# from routers import twilio_webhooks

app = FastAPI(
    title="OmniGuard Fusion Hub API",
    description="Headless Disaster Intelligence & Triage Engine",
    version="1.0.0"
)

# Configure CORS so your Next.js frontend can communicate securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routing modules
app.include_router(email_alerts.router, prefix="/api/v1/alerts", tags=["Notifications"])
# app.include_router(twilio_webhooks.router, prefix="/api/v1/twilio", tags=["Comms"])

@app.get("/")
async def health_check():
    return {"status": "OmniGuard Core is Online", "edge_compute": "Active"}