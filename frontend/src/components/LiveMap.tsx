"use client";

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// 1. Red icon for User SOS Webhooks
const tacticalIcon = L.divIcon({
  className: 'custom-div-icon',
  html: `<div style="background-color:#ff3e3e; width:12px; height:12px; border-radius:50%; border:2px solid white; box-shadow: 0 0 10px #ff3e3e;"></div>`,
  iconSize: [12, 12],
  iconAnchor: [6, 6]
});

// 2. Orange icon for Macro OSINT Disasters
const osintIcon = L.divIcon({
  className: 'custom-div-icon',
  html: `<div style="background-color:#f97316; width:16px; height:16px; border-radius:50%; border:2px solid white; box-shadow: 0 0 15px #f97316;"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8]
});

// 3. NEW: High-Tech Drone Icon
const droneIcon = L.divIcon({
  className: 'drone-icon',
  html: `<div style="background-color:#050505; color:#00ffd0; width:28px; height:28px; border-radius:50%; border:2px solid #00ffd0; display:flex; align-items:center; justify-content:center; box-shadow: 0 0 20px #00ffd0; font-size:16px; z-index: 9999;">🛸</div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14]
});

function MapClickInterceptor({ onMapClick }: { onMapClick?: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) { if (onMapClick) onMapClick(e.latlng.lat, e.latlng.lng); }
  });
  return null;
}

export default function LiveMap({ signals, onMapClick, macroScan, activeRoute }: any) {
  // State to hold the current live position of the drone
  const [dronePos, setDronePos] = useState<[number, number] | null>(null);

  // --- AUTONOMOUS FLIGHT ANIMATION ENGINE ---
  useEffect(() => {
    // If there is no route or it's too short, ground the drone.
    if (!activeRoute || activeRoute.length < 2) {
      setDronePos(null);
      return;
    }

    let currentSegment = 0;
    let progress = 0;
    const speed = 0.0001; // Adjust this to make the drone fly faster or slower
    let animationFrameId: number;

    const animateDrone = () => {
      // Stop animation when we reach the final waypoint
      if (currentSegment >= activeRoute.length - 1) {
        return; 
      }

      const start = activeRoute[currentSegment];
      const end = activeRoute[currentSegment + 1];

      // Linear Interpolation (Lerp) Math
      const lat = start[0] + (end[0] - start[0]) * progress;
      const lng = start[1] + (end[1] - start[1]) * progress;
      
      setDronePos([lat, lng]);
      progress += speed;

      // When we reach the end of the current segment, target the next one
      if (progress >= 1) {
        progress = 0;
        currentSegment++;
      }

      // Loop the animation at 60fps
      animationFrameId = requestAnimationFrame(animateDrone);
    };

    // Launch the drone!
    animateDrone();

    // Cleanup function to stop memory leaks if the component unmounts
    return () => cancelAnimationFrame(animationFrameId);
  }, [activeRoute]);

  const parseLocation = (locStr: string): [number, number] | null => {
    if (!locStr || typeof locStr !== 'string' || locStr.includes("Not Provided")) return null;
    const cleanStr = locStr.replace(/Lat:/g, '').replace(/Lng:/g, '');
    const matches = cleanStr.match(/([-+]?[\d.]+)/g);
    if (matches && matches.length >= 2) {
      return [parseFloat(matches[0]), parseFloat(matches[1])];
    }
    return null;
  };

  return (
    <div className="h-[500px] w-full border border-[#00ffd0]/40 rounded-xl overflow-hidden shadow-[0_0_20px_rgba(0,255,208,0.15)] relative z-0">
      <MapContainer center={[21.1458, 79.0882]} zoom={4} scrollWheelZoom={true} className="h-full w-full bg-[#050505]">
        <MapClickInterceptor onMapClick={onMapClick} />
        <TileLayer 
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='© OMNI-GUARD INTEL'
        />

        {/* --- 1. RENDER THE STATIC FLIGHT PATH --- */}
        {activeRoute && activeRoute.length > 0 && (
          <Polyline 
            positions={activeRoute} 
            pathOptions={{ 
              color: '#00ffd0', 
              weight: 3, 
              dashArray: '10, 15', 
              lineCap: 'square',
              lineJoin: 'round',
              opacity: 0.5
            }} 
          />
        )}

        {/* --- 2. RENDER THE ANIMATED DRONE --- */}
        {dronePos && (
          <Marker position={dronePos} icon={droneIcon} zIndexOffset={1000}>
            <Popup className="tactical-popup">
              <div className="bg-[#050505] text-[#00ffd0] p-2 border border-[#00ffd0]/50 font-mono text-[10px]">
                <p className="font-bold border-b border-[#00ffd0]/20 mb-1 pb-1">🛸 OMNIGUARD RECON-1</p>
                <p className="italic">Status: En Route to Waypoint</p>
                <p>Telemetry: {dronePos[0].toFixed(4)}, {dronePos[1].toFixed(4)}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* --- 3. RENDER OSINT MACRO DISASTERS --- */}
        {macroScan && macroScan.incidents && macroScan.incidents.map((incident: any, idx: number) => {
          if (!incident.approx_lat || !incident.approx_lng) return null;
          return (
            <Marker key={`macro-${idx}`} position={[incident.approx_lat, incident.approx_lng]} icon={osintIcon}>
              <Popup className="tactical-popup">
                <div className="bg-[#050505] text-[#f97316] p-2 border border-[#f97316]/50 font-mono text-[10px] w-48">
                  <p className="font-bold border-b border-[#f97316]/20 mb-1 pb-1">⚠️ OSINT: {incident.type}</p>
                  <p className="text-white font-bold">{incident.location}</p>
                  <p className="mt-1">Dead: {incident.dead} | Inj: {incident.injured}</p>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* --- 4. RENDER INDIVIDUAL SOS SIGNALS --- */}
        {signals.map((signal: any) => {
          const coords = parseLocation(signal.location_str);
          if (!coords) return null; 
          
          return (
            <Marker key={signal.id} position={coords} icon={tacticalIcon}>
              <Popup className="tactical-popup">
                <div className="bg-[#050505] text-[#00ffd0] p-2 border border-[#00ffd0]/50 font-mono text-[10px]">
                  <p className="font-bold border-b border-[#00ffd0]/20 mb-1 pb-1">SIGNAL_ID: {(signal.hashed_id || "Unknown").substring(0,8)}</p>
                  <p className="italic">"{signal.raw_message || "No data"}"</p>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}