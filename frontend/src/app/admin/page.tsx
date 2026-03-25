"use client";

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { Target, Crosshair, Radio, Globe, AlertTriangle } from 'lucide-react';
import SignalTacticalCard from '@/components/SignalTacticalCard';

const LiveMap = dynamic(() => import('@/components/LiveMap'), { 
  ssr: false, 
  loading: () => <div className="h-[500px] bg-black/50 flex items-center justify-center border border-[#00ffd0]/20 text-[#00ffd0] animate-pulse">INITIATING GIS UPLINK...</div> 
});

export default function AdminDashboard() {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [macroData, setMacroData] = useState<any>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanRegion, setScanRegion] = useState("INDIA"); 
  const [scanLat, setScanLat] = useState("21.14");
  const [scanLng, setScanLng] = useState("79.08");
  const [lastScannedLocation, setLastScannedLocation] = useState<{lat: number, lng: number} | null>(null);

  // NEW: Drone Route State
  const [activeRoute, setActiveRoute] = useState<[number, number][] | null>(null);

  const fetchSignals = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/twilio/signals');
      const json = await res.json();
      if (json.data) setSignals(json.data);
    } catch (error) {
      console.error("UPLINK_FAILURE", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
  }, []);

  const handleMapClick = async (lat: number, lng: number) => {
    setScanLat(lat.toFixed(4));
    setScanLng(lng.toFixed(4));
    setScanRegion("TRIANGULATING...");
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`);
      const data = await res.json();
      const area = data.address?.country || data.address?.state || `SEC_${lat.toFixed(1)}_${lng.toFixed(1)}`;
      setScanRegion(area.toUpperCase());
    } catch (error) {
      setScanRegion(`SEC_${lat.toFixed(2)}`);
    }
  };

  const runMacroScan = async () => {
    setIsScanning(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/osint/global-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region_name: scanRegion, lat: scanLat, lon: scanLng })
      });
      const json = await res.json();
      setMacroData(json);
      setLastScannedLocation({ lat: parseFloat(scanLat), lng: parseFloat(scanLng) });
    } finally {
      setIsScanning(false);
    }
  };

  const triggerEvacuationBlast = async () => {
    if (!macroData) { alert("Run OSINT Sweep First to lock target region."); return; }
    const confirm = window.confirm("🚨 WARNING: Mass evacuation blast will be sent to all users in this sector. Proceed?");
    if(!confirm) return;

    await fetch('http://localhost:8000/api/v1/admin/broadcast-evac', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: lastScannedLocation?.lat || 21.14, 
        lng: lastScannedLocation?.lng || 79.08, 
        radius: 50,
        message: "OMNIGUARD ALERT: Flash flood imminent. Evacuate to higher ground immediately."
      })
    });
    alert("✅ Evacuation Blast Transmitted securely.");
  };

  const handleDispatch = async (signal: any) => {
    const isConfirmed = confirm(`Dispatch rescue and send email alert for ${signal.hashed_id}?`);
    if (!isConfirmed) return;
    try {
      await fetch('http://localhost:8000/api/v1/alerts/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: ["shivarkarvedant@gmail.com"],
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
    <div className="min-h-screen bg-[#050505] text-[#00ffd0] p-6 font-mono selection:bg-[#00ffd0] selection:text-black pb-20">
      
      {/* GOD'S EYE RADAR WITH LIVE METRICS */}
      <motion.div 
        initial={{ y: -50, opacity: 0 }} 
        animate={{ y: 0, opacity: 1 }}
        className={`glass-panel p-4 mb-6 border-l-4 ${macroData?.intelligence?.threat_level === 'DEFCON 1' ? 'border-red-500 bg-red-950/10' : 'border-[#00ffd0]'}`}
      >
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <Globe className={`w-5 h-5 ${isScanning ? 'animate-spin' : ''}`} />
              <h2 className="text-sm font-black tracking-widest uppercase">
                {macroData ? `OSINT ASSESSMENT: ${macroData.region}` : "GLOBAL THREAT SCANNER STATUS: STANDBY"}
              </h2>
              {macroData && <span className="px-2 py-0.5 bg-red-600 text-black font-bold text-[10px] animate-pulse">LIVE FEED</span>}
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed max-w-5xl">
              {macroData ? macroData.intelligence?.executive_summary : "Click the tactical map to initialize regional intelligence gathering."}
            </p>
          </div>
          
          <div className="flex items-center gap-2 bg-black/40 p-2 border border-[#00ffd0]/20 rounded">
            <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 ml-1">TARGET_AREA</span>
              <input value={scanRegion} onChange={(e) => setScanRegion(e.target.value)} className="bg-transparent text-xs px-2 py-1 outline-none w-32 font-bold uppercase" />
            </div>
            <div className="flex flex-col gap-2">
              <button 
                onClick={runMacroScan} 
                disabled={isScanning || !scanLat}
                className="bg-[#00ffd0] hover:bg-[#00ffd0]/80 disabled:bg-gray-800 text-black px-4 py-2 text-xs font-black uppercase tracking-tighter flex items-center justify-center gap-2 transition-all"
              >
                <Target className="w-4 h-4" /> {isScanning ? "SCANNING..." : "EXECUTE SWEEP"}
              </button>
              <button 
                onClick={triggerEvacuationBlast}
                className="border border-red-500 text-red-500 hover:bg-red-500 hover:text-white px-4 py-2 rounded text-[10px] font-bold transition-all w-full tracking-widest"
              >
                📢 EVACUATION BLAST
              </button>
            </div>
          </div>
        </div>

        {/* ACTIVE LIVE INCIDENTS CARDS */}
        {macroData?.intelligence?.active_incidents && macroData.intelligence.active_incidents.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4 pt-4 border-t border-[#00ffd0]/20 max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
            {macroData.intelligence.active_incidents.map((incident: any, idx: number) => (
              <div key={idx} className="bg-black/80 border border-red-500/30 p-4 rounded flex flex-col gap-3 shadow-[0_0_15px_rgba(239,68,68,0.1)]">
                
                {/* Header & Casualties */}
                <div className="flex justify-between items-start border-b border-gray-800 pb-2">
                  <div className="flex-1">
                    <h4 className="text-sm font-bold text-red-400 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4"/> {incident.type || 'Unknown Hazard'}
                    </h4>
                    <span className="text-[10px] text-gray-400 mt-1 block tracking-wider uppercase">{incident.location || 'Unknown Sector'}</span>
                  </div>
                  <div className="flex gap-2">
                    <div className="bg-red-950/40 px-3 py-1 rounded border border-red-900/50 text-center">
                      <p className="text-[8px] text-gray-500 uppercase font-bold tracking-widest">Dead</p>
                      <p className="text-sm font-black text-red-500">{incident.dead || 0}</p>
                    </div>
                    <div className="bg-orange-950/40 px-3 py-1 rounded border border-orange-900/50 text-center">
                      <p className="text-[8px] text-gray-500 uppercase font-bold tracking-widest">Inj/Trap</p>
                      <p className="text-sm font-black text-orange-400">{(incident.injured || 0) + (incident.trapped_or_missing || 0)}</p>
                    </div>
                  </div>
                </div>
                
                {/* Logistics & Action Intelligence */}
                <div className="space-y-2 mt-1">
                  <div className="bg-blue-950/20 p-2.5 rounded border border-blue-900/30">
                    <p className="text-[9px] text-blue-400 font-bold uppercase tracking-widest mb-1 flex items-center gap-1">
                      <Radio className="w-3 h-3" /> Local Action Taken
                    </p>
                    <p className="text-[10px] text-gray-300 leading-relaxed font-sans">{incident.action_taken || 'Awaiting local reports.'}</p>
                  </div>
                  <div className="bg-emerald-950/20 p-2.5 rounded border border-emerald-900/30">
                    <p className="text-[9px] text-emerald-400 font-bold uppercase tracking-widest mb-1 flex items-center gap-1">
                      <Target className="w-3 h-3" /> Recommended NDRF Deployment
                    </p>
                    <p className="text-[10px] text-gray-300 leading-relaxed font-sans">{incident.suggested_ndrf_action || 'Standby for logistics calculation.'}</p>
                  </div>
                </div>

              </div>
            ))}
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: TACTICAL MAP */}
        <div className="lg:col-span-7">
          <div className="flex justify-between items-end mb-3">
            <h3 className="text-xs font-bold tracking-[0.3em] flex items-center gap-2">
              <Crosshair className="w-4 h-4" /> BATTLESPACE_VISUALIZATION
            </h3>
            <span className="text-[10px] text-gray-500">GIS_VER: 4.2.0-STABLE</span>
          </div>
          <div className="relative border border-[#00ffd0]/30 shadow-[0_0_30px_rgba(0,255,208,0.1)]">
            <LiveMap 
              signals={signals} 
              onMapClick={handleMapClick}
              activeRoute={activeRoute}
              macroScan={macroData && lastScannedLocation ? {
                lat: lastScannedLocation.lat,
                lng: lastScannedLocation.lng,
                threatLevel: macroData.intelligence?.threat_level || 'UNKNOWN',
                incidents: macroData.intelligence?.active_incidents || [] 
              } : null}
            />
          </div>
        </div>

        {/* RIGHT: INTEL FEED */}
        <div className="lg:col-span-5 flex flex-col">
          <div className="flex justify-between items-end mb-3">
            <h3 className="text-xs font-bold tracking-[0.3em] flex items-center gap-2">
              <Radio className="w-4 h-4" /> SIGNAL_TRIAGE_PIPELINE
            </h3>
            <button onClick={fetchSignals} className="text-[10px] text-gray-500 hover:text-[#00ffd0] underline">SYNC_NOW</button>
          </div>
          <div className="glass-panel flex-1 max-h-[600px] overflow-y-auto custom-scrollbar border border-[#00ffd0]/20 shadow-2xl">
            {signals.map((signal, idx) => (
              <motion.div 
                key={signal.id}
                initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-4 border-b border-[#00ffd0]/10 hover:bg-[#00ffd0]/5 transition-all group relative ${signal.is_natural_disaster === false ? 'opacity-60' : ''}`}
              >
                {/* Main Visible Row */}
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[9px] font-black px-2 py-0.5 border ${signal.severity === 'CRITICAL' ? 'bg-red-950 text-red-500 border-red-500 shadow-[0_0_10px_rgba(239,68,68,0.2)]' : signal.severity === 'WARNING' ? 'bg-orange-950 text-orange-400 border-orange-500' : 'bg-blue-950 text-blue-400 border-blue-400'}`}>
                    {signal.event_type ? String(signal.event_type).toUpperCase() : (signal.severity || 'UNKNOWN')}
                  </span>
                  <div className="flex flex-col items-end">
                    <span className="text-[9px] text-gray-500 font-mono">CONFIDENCE: {signal.truth_verification_score || '0%'}</span>
                    {signal.is_natural_disaster === false && (
                       <span className="text-[8px] text-orange-500 font-bold tracking-widest mt-1">NON-NDRF INCIDENT</span>
                    )}
                  </div>
                </div>
                
                <p className="text-xs text-white mb-2 leading-tight">"{signal.raw_message || "No transmission data."}"</p>
                
                <div className="flex justify-between items-center">
                  <p className="text-[9px] text-gray-500 uppercase tracking-widest">{(signal.osint_context || "Awaiting OSINT verification.").substring(0, 60)}...</p>
                  <button onClick={() => handleDispatch(signal)} className="text-[10px] font-bold text-[#00ffd0] border border-[#00ffd0]/30 px-2 py-1 hover:bg-[#00ffd0] hover:text-black transition-all">
                    DISPATCH
                  </button>
                </div>

                {/* HIDDEN FORENSIC DATA & DRONE UI (Reveals on Hover) */}
                <div className="hidden group-hover:block mt-3 p-3 bg-black/60 rounded border border-[#00ffd0]/20 text-[10px] text-gray-300 transition-all shadow-inner">
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <p><strong className="text-[#00ffd0]">Coordinates:</strong> {signal.location_str || "Unknown"}</p>
                    <p><strong className="text-[#00ffd0]">Est. Trapped:</strong> {signal.estimated_people || 0} Person(s)</p>
                    <p><strong className="text-[#00ffd0]">Event Type:</strong> {signal.event_type || 'Unknown'}</p>
                    <p><strong className="text-[#00ffd0]">Urgency Score:</strong> {signal.urgency_score || 0}/10</p>
                    <p className="col-span-2 text-[9px]"><strong className="text-[#00ffd0]">Extracted Flags:</strong> {signal.extracted_flags?.join(', ') || 'None'}</p>
                    <p className="col-span-2 text-[9px] border-t border-gray-800 pt-1 mt-1"><strong className="text-[#00ffd0]">Full OSINT Log:</strong> {signal.osint_context || "No context logged."}</p>
                  </div>
                  
                  {/* TACTICAL DRONE COMPONENT */}
                  <SignalTacticalCard 
                    signal={signal} 
                    onDrawRoute={setActiveRoute}
                  />

                </div>
              </motion.div>
            ))}
            {signals.length === 0 && !loading && (
              <div className="p-8 text-center text-gray-600 font-mono text-xs">NO ACTIVE LOCAL SIGNALS DETECTED</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}