"use client";

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

// CRITICAL: Prevent SSR crash for Leaflet
const LiveMap = dynamic(() => import('@/components/LiveMap'), { ssr: false, loading: () => <div className="h-[400px] bg-gray-900 animate-pulse rounded-xl border-2 border-gray-800 flex items-center justify-center text-gray-500">Initializing GIS Satellites...</div> });

export default function AdminDashboard() {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSignals = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/twilio/signals');
      const json = await res.json();
      if (json.data) setSignals(json.data);
    } catch (error) {
      console.error("Failed to fetch signals", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
  }, []);

  // MANUAL GMAIL TRIGGER (Hits your FastAPI backend)
  const handleDispatch = async (signal: any) => {
    const isConfirmed = confirm(`Dispatch rescue and send email alert for ${signal.hashed_id}?`);
    if (!isConfirmed) return;

    try {
      await fetch('http://localhost:8000/api/v1/alerts/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: ["shivarkarvedant@gmail.com"], // Sending to you for the demo
          severity: signal.severity,
          location: signal.location_str,
          message: `UNIT DEPLOYED for: "${signal.raw_message}"`,
          instructions: `OSINT Data: ${signal.osint_context}. Proceed with caution.`
        })
      });
      alert('✅ Rescue unit dispatched and email sent.');
    } catch (err) {
      alert('❌ Failed to dispatch email.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-sans">
      
      {/* GLOBAL OSINT BANNER */}
      <div className="w-full bg-blue-900/40 border-l-4 border-blue-500 p-4 mb-6 rounded flex items-center justify-between">
        <div>
          <h4 className="text-blue-400 font-bold text-sm">GLOBAL OSINT ASSESSMENT: NAGPUR SECTOR</h4>
          <p className="text-xs text-gray-300 mt-1">Weather API confirms severe thunderstorms. High risk of localized flooding in low-lying areas. Verification pipeline active.</p>
        </div>
        <div className="text-right">
          <span className="text-xs bg-blue-800 text-blue-200 px-2 py-1 rounded">API: LIVE</span>
        </div>
      </div>

      <header className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-black text-white">OmniGuard Command</h1>
        </div>
        <button onClick={fetchSignals} className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded text-sm font-bold transition-colors">Force Sync Data</button>
      </header>

      {/* SPLIT VIEW: MAP & TABLE */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* LEFT: GIS MAP */}
        <div className="flex flex-col gap-4">
          <h2 className="text-xl font-bold text-gray-300">Live GIS Tracking</h2>
          <LiveMap signals={signals} isPublicView={false} />
        </div>

        {/* RIGHT: DATA TABLE */}
        <div className="flex flex-col gap-4">
          <h2 className="text-xl font-bold text-gray-300">Triage Pipeline</h2>
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-y-auto max-h-[400px] shadow-2xl">
            {loading ? (
               <div className="p-10 text-center text-gray-500">Loading Data...</div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-gray-950 border-b border-gray-800">
                  <tr className="text-gray-400 text-xs uppercase tracking-widest">
                    <th className="p-4">Intelligence</th>
                    <th className="p-4">Action</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {signals.map((signal) => (
                    <tr key={signal.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                      <td className="p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${signal.severity === 'CRITICAL' ? 'bg-red-900/50 text-red-400 border border-red-800' : 'bg-orange-900/50 text-orange-400 border border-orange-800'}`}>
                            {signal.severity}
                          </span>
                          <span className="text-green-400 font-mono text-xs">Truth: {signal.truth_verification_score}</span>
                        </div>
                        <p className="text-gray-300 font-medium truncate max-w-xs">"{signal.raw_message}"</p>
                        <p className="text-[10px] text-gray-500 mt-1 uppercase">{signal.osint_context}</p>
                      </td>
                      <td className="p-4 align-middle">
                        <button 
                          onClick={() => handleDispatch(signal)}
                          className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-2 rounded text-xs font-bold w-full"
                        >
                          Send Rescue Unit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}