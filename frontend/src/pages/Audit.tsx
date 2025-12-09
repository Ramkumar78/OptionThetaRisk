import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const Audit: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'csv' | 'manual'>('csv');
  const [loading, setLoading] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);

  // Manual Entry State
  const [manualRows, setManualRows] = useState<any[]>([
    { id: 1, date: '', symbol: '', action: 'BTO', qty: 1, price: 0, expiry: '', strike: '', opt: 'Call', fees: 0 }
  ]);

  // Common Settings
  const [accountSizeStart, setAccountSizeStart] = useState('');
  const [netLiquidityNow, setNetLiquidityNow] = useState('');
  const [buyingPowerAvailableNow, setBuyingPowerAvailableNow] = useState('');
  const [style, setStyle] = useState('income');
  const [feePerTrade, setFeePerTrade] = useState('0.65');
  const [dateMode] = useState('all');
  const [startDate] = useState('');
  const [endDate] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setCsvFile(e.target.files[0]);
    }
  };

  const handleManualChange = (id: number, field: string, value: any) => {
    setManualRows(rows => rows.map(r => r.id === id ? { ...r, [field]: value } : r));
  };

  const addRow = () => {
    const newId = Math.max(...manualRows.map(r => r.id), 0) + 1;
    setManualRows([...manualRows, { id: newId, date: '', symbol: '', action: 'BTO', qty: 1, price: 0, expiry: '', strike: '', opt: 'Call', fees: 0 }]);
  };

  const removeRow = (id: number) => {
    setManualRows(manualRows.filter(r => r.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData();
    formData.append('account_size_start', accountSizeStart);
    formData.append('net_liquidity_now', netLiquidityNow);
    formData.append('buying_power_available_now', buyingPowerAvailableNow);
    formData.append('style', style);
    formData.append('date_mode', dateMode);
    if (dateMode === 'range') {
        formData.append('start_date', startDate);
        formData.append('end_date', endDate);
    }

    if (activeTab === 'csv') {
       if (csvFile) formData.append('csv', csvFile);
       formData.append('csv_fee_per_trade', feePerTrade);
    } else {
       formData.append('manual_trades', JSON.stringify(manualRows));
       formData.append('fee_per_trade', feePerTrade); // Global fallback if per-row fees aren't fully used logic-side
    }

    try {
      const response = await axios.post('/analyze', formData);
      // Pass the result to the Results page via state
      navigate('/results', { state: { results: response.data } });
    } catch (error) {
      console.error('Analysis failed', error);
      alert('Analysis failed. Please check your input.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center space-y-2">
         <h1 id="audit-title" className="text-3xl font-bold text-gray-900 dark:text-white">Audit Your Portfolio</h1>
         <p className="text-gray-500 dark:text-gray-400">Upload your trade logs or enter them manually to uncover risks and opportunities.</p>
         <p className="text-sm text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
           The Audit tool is the core risk management engine. Upload your trade logs (CSV) from supported brokers like Tastytrade or Interactive Brokers, or enter trades manually. The system will analyze your portfolio for 'Greeks' exposure, PnL attribution, and strategy efficiency, generating a comprehensive risk report.
         </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
         <div className="flex border-b border-gray-200 dark:border-gray-800">
             <button
               id="tab-csv"
               onClick={() => setActiveTab('csv')}
               className={`flex-1 py-4 text-sm font-medium text-center transition-colors ${activeTab === 'csv' ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400 border-b-2 border-primary-500' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}`}
             >
               <i className="bi bi-file-earmark-spreadsheet mr-2"></i> CSV Upload
             </button>
             <button
               id="tab-manual"
               onClick={() => setActiveTab('manual')}
               className={`flex-1 py-4 text-sm font-medium text-center transition-colors ${activeTab === 'manual' ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400 border-b-2 border-primary-500' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}`}
             >
               <i className="bi bi-keyboard mr-2"></i> Manual Entry
             </button>
         </div>

         <form onSubmit={handleSubmit} className="p-6 md:p-8 space-y-8">
             {/* Common Financial Settings */}
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                   <label htmlFor="account-start" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start Balance</label>
                   <div className="mt-1 relative rounded-md shadow-sm">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="text-gray-500 sm:text-sm">$</span>
                      </div>
                      <input type="number" id="account-start" value={accountSizeStart} onChange={e => setAccountSizeStart(e.target.value)} className="focus:ring-primary-500 focus:border-primary-500 block w-full pl-7 sm:text-sm border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700 dark:text-white" placeholder="Optional" />
                   </div>
                </div>
                <div>
                   <label htmlFor="net-liq" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Net Liq (Now)</label>
                   <div className="mt-1 relative rounded-md shadow-sm">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="text-gray-500 sm:text-sm">$</span>
                      </div>
                      <input type="number" id="net-liq" value={netLiquidityNow} onChange={e => setNetLiquidityNow(e.target.value)} className="focus:ring-primary-500 focus:border-primary-500 block w-full pl-7 sm:text-sm border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700 dark:text-white" placeholder="Required for Drawdown" />
                   </div>
                </div>
                <div>
                   <label htmlFor="buying-power" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Buying Power</label>
                   <div className="mt-1 relative rounded-md shadow-sm">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="text-gray-500 sm:text-sm">$</span>
                      </div>
                      <input type="number" id="buying-power" value={buyingPowerAvailableNow} onChange={e => setBuyingPowerAvailableNow(e.target.value)} className="focus:ring-primary-500 focus:border-primary-500 block w-full pl-7 sm:text-sm border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700 dark:text-white" placeholder="Required for Usage %" />
                   </div>
                </div>
             </div>

             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                   <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Trading Style</label>
                   <select id="style-select" value={style} onChange={e => setStyle(e.target.value)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md dark:bg-gray-800 dark:border-gray-700 dark:text-white">
                      <option value="income">Income (Selling Premium)</option>
                      <option value="speculation">Speculation (Buying Premium)</option>
                   </select>
                </div>
                 <div>
                   <label htmlFor="fee-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Est. Fee per Trade</label>
                   <div className="mt-1 relative rounded-md shadow-sm">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="text-gray-500 sm:text-sm">$</span>
                      </div>
                      <input type="number" id="fee-input" value={feePerTrade} onChange={e => setFeePerTrade(e.target.value)} className="focus:ring-primary-500 focus:border-primary-500 block w-full pl-7 sm:text-sm border-gray-300 rounded-md dark:bg-gray-800 dark:border-gray-700 dark:text-white" step="0.01" />
                   </div>
                </div>
             </div>

             {activeTab === 'csv' ? (
               <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-8 text-center bg-gray-50 dark:bg-gray-800/50">
                   <div className="space-y-4">
                      <i className="bi bi-cloud-arrow-up text-4xl text-gray-400"></i>
                      <div>
                          <label htmlFor="csv-upload" className="cursor-pointer text-primary-600 hover:text-primary-500 font-medium">
                            Upload a CSV file
                          </label>
                          <input id="csv-upload" name="csv" type="file" accept=".csv" className="sr-only" onChange={handleFileChange} />
                          <p className="text-xs text-gray-500 mt-1">Tastytrade or IBKR exports supported</p>
                      </div>
                      {csvFile && <p className="text-sm font-semibold text-gray-900 dark:text-white">{csvFile.name}</p>}
                   </div>
               </div>
             ) : (
               <div className="space-y-4 overflow-x-auto">
                   <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                         <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Expiry</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th className="px-3 py-2"></th>
                         </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                         {manualRows.map((row) => (
                           <tr key={row.id}>
                              <td className="px-2 py-2"><input type="date" value={row.date} onChange={e => handleManualChange(row.id, 'date', e.target.value)} className="text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600" /></td>
                              <td className="px-2 py-2"><input type="text" value={row.symbol} onChange={e => handleManualChange(row.id, 'symbol', e.target.value.toUpperCase())} className="w-20 text-xs border-gray-300 rounded uppercase dark:bg-gray-800 dark:border-gray-600" /></td>
                              <td className="px-2 py-2">
                                <select value={row.action} onChange={e => handleManualChange(row.id, 'action', e.target.value)} className="text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600">
                                   <option>BTO</option><option>STO</option><option>BTC</option><option>STC</option>
                                </select>
                              </td>
                              <td className="px-2 py-2"><input type="number" value={row.qty} onChange={e => handleManualChange(row.id, 'qty', parseInt(e.target.value))} className="w-16 text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600" /></td>
                              <td className="px-2 py-2"><input type="number" value={row.price} onChange={e => handleManualChange(row.id, 'price', parseFloat(e.target.value))} className="w-20 text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600" step="0.01" /></td>
                              <td className="px-2 py-2"><input type="date" value={row.expiry} onChange={e => handleManualChange(row.id, 'expiry', e.target.value)} className="text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600" /></td>
                              <td className="px-2 py-2"><input type="number" value={row.strike} onChange={e => handleManualChange(row.id, 'strike', e.target.value)} className="w-20 text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600" /></td>
                              <td className="px-2 py-2">
                                <select value={row.opt} onChange={e => handleManualChange(row.id, 'opt', e.target.value)} className="text-xs border-gray-300 rounded dark:bg-gray-800 dark:border-gray-600">
                                   <option>Call</option><option>Put</option><option>Stock</option>
                                </select>
                              </td>
                              <td className="px-2 py-2">
                                 <button type="button" onClick={() => removeRow(row.id)} className="text-red-500 hover:text-red-700">x</button>
                              </td>
                           </tr>
                         ))}
                      </tbody>
                   </table>
                   <button type="button" onClick={addRow} className="mt-2 text-sm text-primary-600 hover:text-primary-500">+ Add Row</button>
               </div>
             )}

             <div className="pt-6 border-t border-gray-200 dark:border-gray-800 flex justify-end">
                <button
                  id="submit-audit-btn"
                  type="submit"
                  disabled={loading}
                  className="inline-flex justify-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-xl text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 transition-all"
                >
                  {loading ? 'Analyzing...' : 'Run Audit'}
                </button>
             </div>
         </form>
      </div>
    </div>
  );
};

export default Audit;
