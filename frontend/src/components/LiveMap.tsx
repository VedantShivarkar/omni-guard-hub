"use client";

import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix Next.js Leaflet icon bug
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

// Custom Red Icon for CRITICAL signals
const criticalIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

export default function LiveMap({ signals, isPublicView = false }: { signals: any[], isPublicView?: boolean }) {
  // Defaulting to Nagpur coordinates for your demo
  const centerPosition: [number, number] = [21.1458, 79.0882]; 

  // Hardcoded verified safe zones for the demo
  const safeZones = [
    { id: 1, lat: 21.1500, lng: 79.0900, radius: 400, name: "Govt Hospital Relief Camp" },
    { id: 2, lat: 21.1350, lng: 79.0800, radius: 600, name: "High-Ground School Shelter" }
  ];

  // Helper to parse the DB location string safely
  const parseLocation = (locStr: string): [number, number] | null => {
    if (!locStr || locStr.includes("Not Provided")) return null;
    const matches = locStr.match(/([\d.-]+)/g);
    if (matches && matches.length >= 2) {
      return [parseFloat(matches[0]), parseFloat(matches[1])];
    }
    return null;
  };

  return (
    <div className="h-[400px] w-full rounded-xl overflow-hidden border-2 border-gray-700 z-0">
      <MapContainer 
        center={centerPosition} 
        zoom={13} 
        scrollWheelZoom={false} /* <-- THIS IS THE RAM FIX */
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />

        {/* Render Green Safe Zones */}
        {safeZones.map(zone => (
          <Circle 
            key={zone.id} 
            center={[zone.lat, zone.lng]} 
            radius={zone.radius} 
            pathOptions={{ color: 'green', fillColor: 'green', fillOpacity: 0.4 }}
          >
            <Popup><strong>✅ {zone.name}</strong><br/>Verified Safe Zone</Popup>
          </Circle>
        ))}

        {/* Render Distress Signals (If Admin, show all details. If Public, obfuscate for privacy) */}
        {signals.map((signal) => {
          const coords = parseLocation(signal.location_str);
          if (!coords) return null;

          return (
            <Marker 
              key={signal.id} 
              position={coords} 
              icon={signal.severity === 'CRITICAL' ? criticalIcon : defaultIcon}
            >
              <Popup>
                <div className="text-gray-900 font-sans">
                  <h3 className="font-bold text-red-600 mb-1">{signal.severity} ALERT</h3>
                  {!isPublicView ? (
                    <>
                      <p className="text-xs mb-1"><strong>ID:</strong> {signal.hashed_id}</p>
                      <p className="text-xs italic mb-2">"{signal.raw_message}"</p>
                      <div className="bg-gray-100 p-2 rounded text-xs border border-gray-300">
                        <span className="font-bold text-blue-600">OSINT Truth Score: {signal.truth_verification_score}</span>
                        <p className="mt-1 text-gray-600">{signal.osint_context || "Weather API data pending."}</p>
                      </div>
                    </>
                  ) : (
                    <p className="text-xs text-gray-600">Active Rescue Operation Area. AVOID.</p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}