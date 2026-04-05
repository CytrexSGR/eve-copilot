/**
 * EVE Online Security Status Utilities
 * Provides color coding, formatting, and zone classification for system security status
 */

// Re-export formatting functions from canonical source
export { formatISK, formatISKCompact, formatNumber, formatTime } from './format';

/**
 * Get EVE Online standard security status color
 * Uses official EVE color scheme matching in-game display
 */
export function getSecurityColor(sec: number): string {
  if (sec >= 1.0) return '#2FEFEF';  // Bright cyan (1.0)
  if (sec >= 0.9) return '#48F0C0';
  if (sec >= 0.8) return '#00EF47';
  if (sec >= 0.7) return '#00F000';
  if (sec >= 0.6) return '#8FEF2F';
  if (sec >= 0.5) return '#EFEF00';  // Yellow (0.5 - HighSec boundary)
  if (sec >= 0.4) return '#D77700';
  if (sec >= 0.3) return '#F06000';
  if (sec >= 0.2) return '#F04800';
  if (sec >= 0.1) return '#D73000';
  return '#F00000';  // Red (0.0 and below - NullSec)
}

/**
 * Get security zone label
 */
export function getSecurityZone(sec: number): string {
  if (sec >= 0.5) return 'HighSec';
  if (sec >= 0.1) return 'LowSec';
  return 'NullSec';
}

/**
 * Format security status for display
 */
export function formatSecurity(sec: number): string {
  return sec.toFixed(1);
}
