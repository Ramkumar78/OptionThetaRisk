export const METRIC_EXPLANATIONS = {
  regime: "The current broad market trend (Bull or Bear) based on technical indicators like SMA 200.",
  discipline_score: "A score evaluating your trading behavior against best practices (e.g., avoiding revenge trading, managing risk).",
  net_liq: "Net Liquidation Value. The total cash value of your account if all positions were closed immediately.",
  ytd: "Year-to-Date Return. The percentage change in your account value since the beginning of the year.",
  equity_curve: "A chart showing the growth (or decline) of your account balance over time.",
  drawdown: "The peak-to-trough decline during a specific recorded period of an investment.",
  beta_weighted_delta: "Measures your portfolio's sensitivity to market movements (S&P 500). A value of 50 means your portfolio moves like 50 shares of SPY.",
  morning_briefing: "A daily summary of market conditions and portfolio health.",
  risk_map: "A visualization of your open positions based on Days to Expiration (DTE) and Profit/Loss (PnL).",
  monte_carlo: "Simulate future equity curves using statistical methods to estimate potential outcomes.",
  dte: "Days until the option contract expires.",
  pnl_pct: "Estimated Profit/Loss percentage for the position.",
  theta: "Time Decay: How much value your option contract loses every single day as it approaches expiration.",
  delta: "Directional Risk: How much the option's price will move for every $1 move in the underlying stock.",
  gamma: "Acceleration: How fast your Delta changes. High Gamma means your risk changes rapidly.",
  vega: "Volatility Sensitivity: How much the option's price changes for a 1% change in Implied Volatility.",
  rs: "Relative Strength: A measure of a stock's momentum compared to the overall market (e.g., S&P 500)."
};
