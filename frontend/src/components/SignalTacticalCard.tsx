import { Plane, Activity } from 'lucide-react';

export default function SignalTacticalCard({ signal, onDrawRoute }: any) {
  
  const handleGenerateMission = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/admin/drone-route/${signal.id}`);
      const data = await response.json();
      
      if (data.route && data.route.length > 0) {
        onDrawRoute(data.route);
      } else {
        alert("Insufficient data to plot drone route.");
      }
    } catch (err) {
      console.error("Drone route calculation failed", err);
    }
  };

  return (
    <div className="bg-[#0a0a0a] border border-[#00ffd0]/20 rounded-xl p-4 mt-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[#00ffd0] font-mono text-sm flex items-center gap-2">
          <Activity size={16} /> LOGISTICS & DISPATCH
        </h3>
        <span className="text-[10px] bg-red-500/20 text-red-400 px-2 py-1 rounded">
          {signal.logistics?.burn_rate_warning || "Calculating Burn Rate..."}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white/5 p-3 rounded-lg border border-white/10">
          <p className="text-gray-400 text-[10px] uppercase">Requisition Needed</p>
          <ul className="text-white text-xs list-disc ml-4 mt-1">
            {signal.logistics?.equipment?.map((e: string) => <li key={e}>{e}</li>) || "Standard Kit"}
          </ul>
        </div>
        <div className="bg-white/5 p-3 rounded-lg border border-white/10">
          <p className="text-gray-400 text-[10px] uppercase">Personnel</p>
          <p className="text-[#00ffd0] text-sm font-bold mt-1">
            {signal.logistics?.personnel || "NDRF Level 1"}
          </p>
        </div>
      </div>

      <button 
        onClick={handleGenerateMission}
        className="w-full bg-[#00ffd0] hover:bg-[#00ffd0]/80 text-black font-bold py-3 rounded-lg flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(0,255,208,0.3)]"
      >
        <Plane size={18} />
        INITIATE AUTONOMOUS DRONE SWEEP
      </button>
    </div>
  );
}