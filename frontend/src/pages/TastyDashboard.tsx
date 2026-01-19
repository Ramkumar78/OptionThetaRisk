import React, { useState, useEffect } from 'react';
import { connectTastytrade, fetchAccountMetrics } from '../api';

const TastyDashboard = () => {
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState("Disconnected");
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    try {
        await connectTastytrade();
        setStatus("🟢 CONNECTED");
        const metrics = await fetchAccountMetrics();
        setData(metrics.data);
        setError(null);
    } catch (e: any) {
        setStatus("🔴 ERROR");
        setError(e.response?.data?.message || e.message || "Failed to connect");
    }
  };

  useEffect(() => {
    // Optional: Auto connect check? Or just let user click.
    // We'll let user click for now.
  }, []);

  return (
    <div className="p-8 bg-slate-900 text-white min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">THALAIVA COMMAND</h1>
        <button onClick={handleConnect} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-bold">
          {status}
        </button>
      </div>

      {error && (
        <div className="bg-red-900 border border-red-500 text-red-200 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
            <div className="mt-2 text-xs opacity-75">
                Check server logs for more details. If SDK is missing, ensure 'tastytrade' is installed.
            </div>
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-800 p-6 rounded border-b-4 border-blue-500">
            <p className="text-gray-400 uppercase text-xs">Net Liquidation</p>
            <p className="text-4xl font-mono">${data.net_liq}</p>
          </div>
          <div className={`p-6 rounded border-b-4 ${data.bp_usage > 35 ? 'border-red-500' : 'border-green-500'} bg-slate-800`}>
            <p className="text-gray-400 uppercase text-xs">BP Usage (%)</p>
            <p className="text-4xl font-mono">{data.bp_usage}%</p>
            <p className="text-xs mt-2 uppercase font-bold">
                {data.bp_usage > 30 ? '🛑 NO NEW TRADES' : '🟢 CLEAR TO TRADE'}
            </p>
          </div>
          <div className="bg-slate-800 p-6 rounded border-b-4 border-yellow-500">
            <p className="text-gray-400 uppercase text-xs">Buying Power</p>
            <p className="text-4xl font-mono">${data.buying_power}</p>
          </div>
        </div>
      )}

      {/* Position Audit */}
      {data && (
      <div className="bg-slate-800 rounded p-4 overflow-x-auto">
        <h2 className="text-xl font-bold mb-4">Live Positions Audit</h2>
        <table className="w-full text-left font-mono text-sm">
          <thead className="text-gray-500 bg-slate-900">
            <tr>
                <th className="p-3">Symbol</th>
                <th className="p-3">Qty</th>
                <th className="p-3">Mark</th>
                <th className="p-3">Exp</th>
                <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.positions.map((p: any) => (
              <tr key={p.symbol} className="border-t border-slate-700 hover:bg-slate-700">
                <td className="p-3 font-bold text-blue-300">{p.symbol}</td>
                <td className="p-3">{p.qty}</td>
                <td className="p-3">${p.mark}</td>
                <td className="p-3">{p.exp}</td>
                <td className="p-3"><span className="text-green-400 font-bold">IN PLAY</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
};

export default TastyDashboard;
