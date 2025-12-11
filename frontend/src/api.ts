import axios from 'axios';

const api = axios.create({
  baseURL: '/', // Relative URL since we serve from the same origin
});

export const runMarketScreener = async (ivRank: number, rsiThreshold: number, timeFrame: string, tastyCreds?: any) => {
  // If creds provided, send as JSON. If not, we can keep using FormData or switch to JSON.
  // The backend now accepts both, but JSON is preferred for nested data.
  // Let's use JSON for everything if possible, but to stay compatible with minimal changes:
  if (tastyCreds) {
      const payload = {
          iv_rank: ivRank,
          rsi_threshold: rsiThreshold,
          time_frame: timeFrame,
          tasty_creds: tastyCreds
      };
      const response = await api.post('/screen', payload, {
          headers: { 'Content-Type': 'application/json' }
      });
      return response.data;
  } else {
      const formData = new FormData();
      formData.append('iv_rank', ivRank.toString());
      formData.append('rsi_threshold', rsiThreshold.toString());
      formData.append('time_frame', timeFrame);
      const response = await api.post('/screen', formData);
      return response.data;
  }
};

export const runTurtleScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/turtle', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};

export const runMmsScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/mms', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};

export const runDarvasScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/darvas', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};

export const runBullPutScreener = async (region: string) => {
  const response = await api.get('/screen/bull_put', {
    params: { region }
  });
  return response.data;
};

export const importTradesToJournal = async (trades: any[]) => {
  const response = await api.post('/journal/import', trades);
  return response.data;
};

export const runEmaScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/ema', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};
