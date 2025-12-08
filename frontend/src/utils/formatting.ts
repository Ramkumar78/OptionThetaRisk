export const formatCurrency = (value: number | undefined | null, symbol: string): string => {
  if (value === undefined || value === null) return '-';

  let displayValue = value;

  // Convert Pence (GBX) to Pounds (GBP)
  if (symbol === '£') {
      displayValue = value / 100;
  }

  // Basic formatting with commas
  const formattedValue = displayValue.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  return `${symbol}${formattedValue}`;
};

export const getCurrencySymbol = (ticker: string): string => {
  if (!ticker) return '$';

  if (ticker.endsWith('.L')) return '£';
  if (ticker.endsWith('.NS')) return '₹';

  // Euro check - simplistic list based on common Yahoo Finance suffixes
  const euroSuffixes = ['.PA', '.DE', '.AS', '.MC', '.MA', '.MI', '.BR', '.VI'];
  if (euroSuffixes.some(s => ticker.endsWith(s))) return '€';

  return '$';
};
