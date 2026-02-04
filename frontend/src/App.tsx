import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Screener from './pages/Screener';
import Journal from './pages/Journal';
import Audit from './pages/Audit';
import Results from './pages/Results';
import Dashboard from './pages/Dashboard';
import PortfolioRisk from './pages/PortfolioRisk';
import MonteCarlo from './pages/MonteCarlo';
import Backtester from './pages/Backtester';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="screener" element={<Screener />} />
          <Route path="backtest" element={<Backtester />} />
          <Route path="journal" element={<Journal />} />
          <Route path="audit" element={<Audit />} />
          <Route path="results" element={<Results />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="portfolio-risk" element={<PortfolioRisk />} />
          <Route path="monte-carlo" element={<MonteCarlo />} />
          <Route path="*" element={<div className="text-center p-10">404 Not Found</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
