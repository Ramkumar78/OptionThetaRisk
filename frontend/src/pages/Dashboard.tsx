import React, { useEffect, useState } from 'react';
import axios from 'axios';
import DashboardPro from '../components/DashboardPro';

const Dashboard: React.FC = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await axios.get('/dashboard');
        if (response.data && !response.data.error) {
          setPortfolioData(response.data);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPortfolio();
  }, []);

  return <DashboardPro portfolioData={portfolioData} loading={loading} />;
};

export default Dashboard;
