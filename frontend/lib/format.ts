const marketLocale = process.env.NEXT_PUBLIC_MARKET_LOCALE ?? "en-IN";

export function formatCurrency(value: number, currency: string) {
  return new Intl.NumberFormat(marketLocale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number, maximumFractionDigits = 1) {
  return new Intl.NumberFormat(marketLocale, {
    maximumFractionDigits,
  }).format(value);
}

export function formatDuration(hours: number) {
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);
  return `${wholeHours}h ${minutes}m`;
}
