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

export function formatTimestamp(value: string | null | undefined) {
  if (!value) return "Update time unavailable";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Update time unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
    timeZone: "Asia/Kolkata", timeZoneName: "short",
  }).format(date);
}
