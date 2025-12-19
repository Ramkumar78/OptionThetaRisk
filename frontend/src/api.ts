import axios from 'axios';

const api = axios.create({
  baseURL: '/', // Relative URL since we serve from the same origin
});

export const runMarketScreener = async (ivRank: number, rsiThreshold: number, timeFrame: string, region: string) => {
  const formData = new FormData();
  formData.append('iv_rank', ivRank.toString());
  formData.append('rsi_threshold', rsiThreshold.toString());
  formData.append('time_frame', timeFrame);
  formData.append('region', region);
  const response = await api.post('/screen', formData);
  return response.data;
};

export const runTurtleScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/turtle', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};

export const runQuantumScreener = async (region: string) => {
  const response = await api.get('/screen/quantum', {
    params: { region }
  });
  return response.data;
};

export const runHybridScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/hybrid', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};

export const runFourierScreener = async (region: string, timeFrame: string) => {
  const response = await api.get('/screen/fourier', {
    params: { region, time_frame: timeFrame }
  });
  return response.data;
};

export const runIsaTrendScreener = async (region: string) => {
  const response = await api.get('/screen/isa', {
    params: { region }
  });
  return response.data;
};

export const checkIsaStock = async (ticker: string, entryPrice?: string) => {
  const params: any = { ticker };
  if (entryPrice) {
    params.entry_price = entryPrice;
  }
  const response = await api.get('/screen/isa/check', {
    params
  });
  return response.data;
};

export const checkUnifiedStock = async (ticker: string, strategy: string, timeFrame: string, entryPrice?: string, entryDate?: string) => {
  const params: any = { ticker, strategy, time_frame: timeFrame };
  if (entryPrice) {
    params.entry_price = entryPrice;
  }
  if (entryDate) {
    params.entry_date = entryDate;
  }
  const response = await api.get('/screen/check', {
    params
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
