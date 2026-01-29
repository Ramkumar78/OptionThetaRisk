# Project Roadmap

## Frontend (React/TypeScript)

### 1. Advanced Visualization
- **Interactive Charts**: Integrate TradingView Lightweight Charts or Highcharts for real-time, zoomable candlestick charts with indicators (MA, RSI, Bollinger Bands).
- **Portfolio Dashboard**: Visual breakdown of portfolio allocation (Sector, Asset Class) using pie charts and treemaps.
- **Risk Heatmaps**: Visual representation of risk exposure across positions.

### 2. Real-Time Capabilities
- **WebSocket Integration**: Move from polling to WebSockets for live price updates and scanner alerts.
- **Toast Notifications**: Real-time alerts for trade signals or execution events.

### 3. User Experience (UX)
- **Strategy Builder UI**: Drag-and-drop interface to compose strategies from signals (e.g., "RSI < 30" + "Price > SMA200").
- **Mobile Responsiveness**: Optimised layout for mobile trading.
- **Dark/Light Mode**: Full theme support.

## Backend (Flask/Python)

### 1. Architecture & Scalability
- **Async Task Queue**: Implement Celery with Redis to handle long-running screening/backtesting jobs in the background.
- **Database Integration**: Migrate from CSV/SQLite to PostgreSQL for robust data storage (Tickers, Users, Trades).
- **Microservices**: Split the Screener, Backtester, and Execution engines into separate services if scaling is needed.

### 2. Features
- **User Authentication**: Implement JWT-based auth for multi-user support.
- **AI/ML Integration**:
    - Sentiment Analysis on news headlines.
    - Reinforcement Learning for parameter optimization.
- **Advanced Backtesting**:
    - Slippage and Commission models.
    - Monte Carlo simulations for robustness testing.
