import React, { useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Brush
} from 'recharts';
import RiskMapChart from './RiskMapChart';

interface DashboardProProps {
  portfolioData: any;
  loading: boolean;
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatPercent = (value: number) => {
  return `${(value * 100).toFixed(1)}%`;
};

const DashboardPro: React.FC<DashboardProProps> = ({ portfolioData, loading }) => {
  const metrics = useMemo(() => {
    if (!portfolioData) return null;

    const strategies = portfolioData.strategy_groups || [];
    let grossWin = 0;
    let grossLoss = 0;

    strategies.forEach((s: any) => {
      // Use gross_pnl if available, otherwise fallback to pnl (net) + fees?
      // strategies have 'gross_pnl'.
      const pnl = s.gross_pnl !== undefined ? s.gross_pnl : s.pnl;
      if (pnl > 0) grossWin += pnl;
      else grossLoss += Math.abs(pnl);
    });

    const profitFactor = grossLoss === 0 ? (grossWin > 0 ? 999 : 0) : grossWin / grossLoss;

    // Max Drawdown from backend is usually correct, but let's use it directly
    const maxDrawdown = portfolioData.strategy_metrics?.max_drawdown || 0;
    const winRate = portfolioData.strategy_metrics?.win_rate || 0;
    const totalPnl = portfolioData.strategy_metrics?.total_pnl || 0;
    const netLiq = portfolioData.net_liquidity_now || 0;

    return {
      netPnl: totalPnl,
      winRate,
      profitFactor,
      maxDrawdown,
      netLiq
    };
  }, [portfolioData]);

  const chartData = useMemo(() => {
    if (!portfolioData?.portfolio_curve) return [];
    const initial = portfolioData.account_size_start || 0;
    return portfolioData.portfolio_curve.map((p: any) => ({
      date: p.x,
      value: initial + p.y,
      originalPnl: p.y
    }));
  }, [portfolioData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] bg-slate-950 text-slate-400">
        <div className="animate-pulse">Loading Market Data...</div>
      </div>
    );
  }

  if (!portfolioData || !metrics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-slate-950 text-slate-400 p-8 border border-slate-800 rounded-lg">
        <div className="text-xl mb-2">No Data Available</div>
        <p className="text-sm">Upload trades or connect a broker to see your dashboard.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 md:p-6 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Market Dashboard
          </h1>
          <p className="text-xs font-mono text-slate-500 mt-1 uppercase tracking-wider">
            Live Feed &bull; {new Date().toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-4 bg-slate-900 p-2 rounded-lg border border-slate-800">
             <div className="px-4 border-r border-slate-800">
                 <div className="text-[10px] uppercase text-slate-500 font-bold">Net Liq</div>
                 <div className="text-lg font-mono font-bold text-white">{formatCurrency(metrics.netLiq)}</div>
             </div>
             <div className="px-4">
                 <div className="text-[10px] uppercase text-slate-500 font-bold">Buying Power</div>
                 <div className="text-lg font-mono font-bold text-slate-300">
                     {portfolioData.buying_power_utilized_percent
                        ? `${(100 - portfolioData.buying_power_utilized_percent).toFixed(1)}%`
                        : 'N/A'}
                 </div>
             </div>
        </div>
      </div>

      {/* Metric Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
            title="Net PnL"
            value={formatCurrency(metrics.netPnl)}
            trend={metrics.netPnl >= 0 ? 'up' : 'down'}
            subtext="All Time"
        />
        <MetricCard
            title="Win Rate"
            value={formatPercent(metrics.winRate)}
            trend={metrics.winRate >= 0.5 ? 'up' : 'down'}
            subtext={`${portfolioData.strategy_metrics?.num_trades || 0} Trades`}
        />
        <MetricCard
            title="Profit Factor"
            value={metrics.profitFactor.toFixed(2)}
            trend={metrics.profitFactor >= 1.5 ? 'up' : (metrics.profitFactor >= 1 ? 'neutral' : 'down')}
            subtext="Gross Win / Loss"
        />
        <MetricCard
            title="Max Drawdown"
            value={formatCurrency(metrics.maxDrawdown)}
            trend="down"
            subtext="Peak to Trough"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Equity Curve - Spans 2 cols */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm flex flex-col h-[450px]">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/></svg>
                Equity Curve
            </h3>
            <div className="text-xs font-mono text-slate-500">
                Start: {formatCurrency(portfolioData.account_size_start || 0)}
            </div>
          </div>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis
                    dataKey="date"
                    stroke="#475569"
                    fontSize={11}
                    tickFormatter={(str) => {
                        const d = new Date(str);
                        return `${d.getMonth()+1}/${d.getDate()}`;
                    }}
                    tickMargin={10}
                />
                <YAxis
                    stroke="#475569"
                    fontSize={11}
                    tickFormatter={(val) => `$${val >= 1000 ? (val/1000).toFixed(1) + 'k' : val}`}
                    width={50}
                />
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#64748b', strokeWidth: 1, strokeDasharray: '4 4' }} />
                <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorValue)"
                    activeDot={{ r: 6, strokeWidth: 0 }}
                />
                <Brush
                    dataKey="date"
                    height={30}
                    stroke="#3b82f6"
                    fill="#0f172a"
                    tickFormatter={() => ''}
                    travellerWidth={10}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk / Info Panel */}
        <div className="flex flex-col gap-6 h-[450px]">
             {/* Risk Map Container */}
             <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm flex-1 flex flex-col min-h-0">
                 <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Risk Map
                 </h3>
                 <div className="flex-1 min-h-0 relative">
                      <div className="absolute inset-0">
                          <RiskMapChart data={portfolioData.risk_map} />
                      </div>
                 </div>
             </div>

             {/* Recent Verdict / Status */}
             <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm h-1/3 flex flex-col justify-center">
                  <div className="text-xs font-bold text-slate-500 uppercase mb-2">System Verdict</div>
                  <div className={`text-lg font-bold ${
                      portfolioData.verdict_color === 'red' ? 'text-red-400' :
                      portfolioData.verdict_color === 'yellow' ? 'text-amber-400' :
                      'text-emerald-400'
                  }`}>
                      {portfolioData.verdict || 'Analysis Pending'}
                  </div>
                  <div className="text-xs text-slate-400 mt-1 line-clamp-2">
                      {portfolioData.verdict_details || 'No critical alerts.'}
                  </div>
             </div>
        </div>
      </div>

      {/* Footer / Disclaimer */}
      <div className="text-center text-[10px] text-slate-600 font-mono mt-8">
          GENERATED BY OPTION AUDITOR &bull; DATA DELAYED BY 15 MIN &bull; NOT FINANCIAL ADVICE
      </div>
    </div>
  );
};

// --- Subcomponents ---

const MetricCard: React.FC<{
    title: string;
    value: string | number;
    trend: 'up' | 'down' | 'neutral';
    subtext?: string;
    isNegativeGood?: boolean;
}> = ({ title, value, trend, subtext, isNegativeGood }) => {

    let colorClass = 'text-slate-100';
    if (trend === 'up') colorClass = isNegativeGood ? 'text-red-400' : 'text-emerald-400';
    if (trend === 'down') colorClass = isNegativeGood ? 'text-emerald-400' : 'text-red-400';
    if (trend === 'neutral') colorClass = 'text-amber-400';

    // Special case for Max Drawdown (trend='down' but value is positive, usually bad, so red)
    // If isNegativeGood is true (unlikely for drawdown amount?), wait.
    // Drawdown amount is positive in data (e.g. 5000). It's "Bad".
    // So trend='down' (bad) -> red.
    // isNegativeGood defaults false.
    // My logic above: trend='down' -> red. Correct.

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm hover:border-slate-700 transition-colors">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">{title}</div>
            <div className={`text-2xl font-mono font-bold ${colorClass}`}>
                {value}
            </div>
            {subtext && <div className="text-[10px] text-slate-600 mt-1 font-mono">{subtext}</div>}
        </div>
    );
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-700 p-3 rounded shadow-xl text-xs">
        <div className="text-slate-400 mb-1 font-mono">{new Date(label).toLocaleDateString()}</div>
        <div className="font-bold text-white text-base">
            {formatCurrency(data.value)}
        </div>
        <div className={`font-mono ${data.originalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            Daily: {data.originalPnl >= 0 ? '+' : ''}{formatCurrency(data.originalPnl)}
        </div>
      </div>
    );
  }
  return null;
};

export default DashboardPro;
