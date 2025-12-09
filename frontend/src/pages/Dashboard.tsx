import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Results from './Results';

const Dashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await axios.get('/dashboard');
        if (response.data && !response.data.error) {
          setData(response.data);
        } else if (response.data.error === 'No portfolio found') {
           // Redirect to home if no data
           navigate('/');
        } else {
           setError(response.data.error || 'Failed to load dashboard');
        }
      } catch (err: any) {
        // If 401/404 or other error, redirect or show error
        if (err.response && err.response.status === 401) {
             navigate('/');
        } else {
             setError(err.message || 'Failed to connect to server');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, [navigate]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-gray-700 dark:text-gray-300">Error</h2>
        <p className="text-red-500">{error}</p>
        <button onClick={() => navigate('/')} className="mt-4 text-primary-600 hover:underline">Return Home</button>
      </div>
    );
  }

  // Reuse Results component but inject data via props (we need to modify Results to accept props OR state)
  // Since Results currently reads from useLocation(), we should wrap it or modify it.
  // Ideally, Results should be a dumb component that accepts `data` prop.
  // For now, let's modify Results.tsx to accept an optional prop `data` which overrides location.state.

  // Actually, passing data via state in a redirect is one way, but we want to render it here.
  // The cleanest way is to refactor Results to separate logic from data fetching/location.
  // However, given the constraints, passing data as a prop to Results is easiest if we modify Results.tsx.

  return <Results directData={data} />;
};

export default Dashboard;
