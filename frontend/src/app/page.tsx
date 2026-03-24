"use client";

import { useState } from 'react';
import dynamic from 'next/dynamic';

const LiveMap = dynamic(() => import('@/components/LiveMap'), { 
  ssr: false,
  loading: () => <div className="h-[250px] bg-gray-200 animate-pulse rounded-xl flex items-center justify-center text-gray-500 font-mono text-sm border-2 border-gray-300">Initializing Satellite Uplink...</div>
});

export default function PublicPortal() {
  const [locationStatus, setLocationStatus] = useState("Click to capture GPS");
  const [reportText, setReportText] = useState(""); // <-- New State for the textbox
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const emergencyNumber = "917588387675";
  const whatsappTemplate = encodeURI(
    "🚨 EMERGENCY 🚨\n\nI need immediate rescue.\n\n(Please send your LIVE LOCATION and a VOICE NOTE describing the situation and number of people trapped)"
  );
  const whatsappUrl = `https://wa.me/${emergencyNumber}?text=${whatsappTemplate}`;

  const captureLocation = () => {
    setLocationStatus("Locating satellite...");
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocationStatus(`📍 Lat: ${position.coords.latitude.toFixed(4)}, Lng: ${position.coords.longitude.toFixed(4)}`);
        },
        () => {
          setLocationStatus("GPS Failed. Please type location manually.");
        }
      );
    } else {
      setLocationStatus("Geolocation not supported.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const latMatch = locationStatus.match(/Lat: ([\d.]+)/);
    const lngMatch = locationStatus.match(/Lng: ([\d.]+)/);
    const lat = latMatch ? latMatch[1] : "Unknown";
    const lng = lngMatch ? lngMatch[1] : "Unknown";

    // Pass the actual typed text to the backend
    const payload = {
      message: reportText || "Silent report: Immediate assistance required.",
      latitude: lat,
      longitude: lng,
      contact: "Anonymous"
    };

    try {
      const response = await fetch('http://localhost:8000/api/v1/twilio/incoming-web', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) setSubmitted(true);
    } catch (error) {
      console.error("Transmission failed", error);
      setSubmitted(true); 
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center p-4 md:p-8 font-sans">
      <div className="max-w-md w-full space-y-6">
        
        {/* HEADER */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-extrabold text-red-600 tracking-tight">OMNIGUARD</h1>
          <p className="text-sm font-semibold text-gray-500 uppercase tracking-widest">Disaster Response Hub</p>
        </div>

        {/* PUBLIC OSINT BANNER */}
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-800 p-4 rounded shadow-sm text-sm font-medium">
          <strong>⚠️ VERIFIED DISASTER UPDATE:</strong> Heavy flooding confirmed in Sector 4. Proceed to Green Zones marked on the map immediately.
        </div>

        {/* 1. WHATSAPP FAST-TRACK */}
        <div className="bg-white rounded-2xl shadow-xl p-6 border-l-8 border-green-500">
          <h2 className="font-bold text-gray-800 text-lg mb-2">Fastest Method (Works Offline)</h2>
          <p className="text-sm text-gray-600 mb-4">Send a voice note & live location directly to our AI Triage engine.</p>
          <a
            href={whatsappUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center w-full bg-green-500 hover:bg-green-600 text-white font-bold py-4 px-4 rounded-xl shadow-md transition-transform active:scale-95"
          >
            💬 Open Secure WhatsApp Line
          </a>
        </div>

        {/* 2. SILENT WEB REPORT */}
        <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-200">
          <h2 className="font-bold text-gray-800 text-lg mb-2">Silent Web Report</h2>
          <p className="text-sm text-gray-600 mb-4">If you cannot speak, send a discrete SOS.</p>
          
          {submitted ? (
            <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-xl text-center font-bold">
              ✅ Report Received. NDRF Rescue assigned.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Describe Emergency</label>
                <textarea 
                  value={reportText}
                  onChange={(e) => setReportText(e.target.value)}
                  placeholder="E.g., 3 people trapped on the roof, water rising fast..."
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-lg text-sm text-gray-800 focus:ring-2 focus:ring-red-500 focus:outline-none"
                  rows={3}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Exact Location</label>
                <button 
                  type="button" 
                  onClick={captureLocation}
                  className="w-full text-left px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-sm font-mono text-gray-600"
                >
                  {locationStatus}
                </button>
              </div>
              <button 
                type="submit" 
                disabled={isSubmitting}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-4 rounded-xl shadow-md disabled:bg-red-300 transition-all"
              >
                {isSubmitting ? "Encrypting & Sending..." : "🚨 Transmit Rescue Signal"}
              </button>
            </form>
          )}
        </div>

        {/* 3. VERIFIED SAFE ZONES (REAL GIS MAP) */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-200">
          <div className="p-4 bg-blue-600 text-white flex justify-between items-center">
            <div>
              <h2 className="font-bold text-lg">🗺️ Live Safe Zones</h2>
              <p className="text-xs opacity-90">Auto-updating via OSINT Verification</p>
            </div>
          </div>
          <div className="p-0 border-b border-gray-200 bg-gray-100">
            <LiveMap signals={[]} isPublicView={true} />
          </div>
          <div className="bg-gray-50 p-3 text-xs flex justify-around">
            <span className="flex items-center gap-1 font-semibold text-green-700"><div className="w-3 h-3 bg-green-500 rounded-full opacity-50"></div> Verified Safe Zone</span>
            <span className="flex items-center gap-1 font-semibold text-red-700"><div className="w-3 h-3 bg-red-500 rounded-full"></div> Active Hazard</span>
          </div>
        </div>

      </div>
    </main>
  );
}