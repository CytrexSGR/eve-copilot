/**
 * Get the base URL for ectmap iframe embedding.
 * In dev mode (ports 5173/5175), points to the Next.js ectmap on port 3001.
 * In production, uses relative /ectmap (nginx proxies to port 3001).
 */
export function getEctmapBaseUrl(): string {
  const port = window.location.port;
  if (port === '5173' || port === '5175') {
    return `http://${window.location.hostname}:3001/ectmap`;
  }
  return '/ectmap';
}

/**
 * Format ISK value with appropriate suffix (T/B/M/K)
 * Canonical implementation - use this everywhere
 */
export function formatISK(value: number | string | undefined | null): string {
  if (value == null) return '0 ISK';
  const num = typeof value === 'string' ? Number(value) : value;
  if (isNaN(num)) return '0 ISK';
  if (num >= 1_000_000_000_000) {
    return `${(num / 1_000_000_000_000).toFixed(2)}T ISK`;
  }
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(2)}B ISK`;
  }
  if (num >= 1_000_000) {
    const m = num / 1_000_000;
    return `${m.toFixed(m < 10 ? 2 : 1)}M ISK`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(0)}K ISK`;
  }
  return `${num.toFixed(0)} ISK`;
}

/**
 * Format ISK without suffix (for compact display)
 */
export function formatISKCompact(value: number | string | undefined | null): string {
  if (value == null) return '0';
  const num = typeof value === 'string' ? Number(value) : value;
  if (isNaN(num)) return '0';
  if (num >= 1_000_000_000_000) {
    return `${(num / 1_000_000_000_000).toFixed(2)}T`;
  }
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(2)}B`;
  }
  if (num >= 1_000_000) {
    const m = num / 1_000_000;
    return `${m.toFixed(m < 10 ? 2 : 1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toLocaleString();
}

/**
 * Format hours ago to human readable string
 */
export function formatHoursAgo(hours: number): string {
  if (hours < 1) return 'now';
  if (hours < 24) return `${Math.floor(hours)}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Format number with K/M/B suffix
 */
export function formatNumber(value: number | string | undefined | null): string {
  if (value == null) return '0';
  const num = typeof value === 'string' ? Number(value) : value;
  if (isNaN(num)) return '0';
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1)}B`;
  } else if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  } else if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toLocaleString();
}

/**
 * Format timestamp to readable format (EVE Time / UTC)
 */
export function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
      timeZoneName: 'short'
    });
  } catch {
    return isoString;
  }
}
