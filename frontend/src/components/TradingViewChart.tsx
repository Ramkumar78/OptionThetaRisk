import React from 'react';
import { AdvancedRealTimeChart } from 'react-ts-tradingview-widgets';

interface TradingViewChartProps {
  symbol: string;
  theme?: "light" | "dark";
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({ symbol, theme = "light" }) => {
  return (
    <div className="w-full h-[600px]">
      <AdvancedRealTimeChart
        symbol={symbol}
        theme={theme}
        autosize
        interval="D"
        timezone="Etc/UTC"
        style="1"
        locale="en"
        toolbar_bg="#f1f3f6"
        enable_publishing={false}
        hide_side_toolbar={false}
        allow_symbol_change={true}
        container_id={`tradingview_widget_${symbol}`}
      />
    </div>
  );
};

export default TradingViewChart;
