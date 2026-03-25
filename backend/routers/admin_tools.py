from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client

router = APIRouter()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

class EvacPayload(BaseModel):
    lat: float
    lng: float
    radius: float
    message: str

@router.post("/broadcast-evac")
async def broadcast_evacuation(payload: EvacPayload):
    # Simulated SMS/WhatsApp Blast to all numbers in the radius
    print(f"🚨 BROADCASTING TO {payload.lat}, {payload.lng}: {payload.message}")
    return {"status": "Broadcast Initiated", "targets_reached": 142}

@router.get("/drone-route/{signal_id}")
async def get_drone_route(signal_id: str):
    """Generates an autonomous flight path from HQ -> target -> nearby critical signals"""
    try:
        # Get Target Signal
        sig_res = supabase.table("distress_signals").select("*").eq("id", signal_id).execute()
        if not sig_res.data:
            raise HTTPException(404, "Signal not found")
        target_signal = sig_res.data[0]

        # Get nearby critical signals
        nearby_res = supabase.table("distress_signals").select("*").eq("severity", "CRITICAL").neq("id", signal_id).limit(5).execute()
        nearby_signals = nearby_res.data or []

        def parse_coords(s):
            try:
                # Strip out 'Lat:' and 'Lng:' if they are present in the string
                parts = s.replace("Lat:", "").replace("Lng:", "").split(',')
                return [float(parts[0].strip()), float(parts[1].strip())]
            except: 
                return None

        # ---------------------------------------------------------
        # THE FIX: HARDCODED HQ BASE COORDINATES AS STARTING POINT
        # ---------------------------------------------------------
        HQ_COORDS = [21.152464, 79.071456]
        route = [HQ_COORDS] 
        
        # Add target victim as Waypoint 1
        t_coords = parse_coords(target_signal['location_str'])
        if t_coords: 
            route.append(t_coords)

        # Add nearby victims as subsequent Waypoints
        for sig in nearby_signals:
            c = parse_coords(sig['location_str'])
            if c: 
                route.append(c)

        return {"status": "success", "route": route}
        
    except Exception as e:
        raise HTTPException(500, str(e))