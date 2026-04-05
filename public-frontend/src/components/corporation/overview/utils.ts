/**
 * Overview Tab Utilities
 *
 * Helper functions for formatting and data manipulation.
 */

/**
 * Format ISK value to human-readable string (e.g., "13.6T", "500M")
 */
export function formatISK(value: number): string {
  if (value >= 1e12) {
    return `${(value / 1e12).toFixed(1)}T`;
  }
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(1)}B`;
  }
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(1)}M`;
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(1)}K`;
  }
  return value.toFixed(0);
}

/**
 * Format percentage to string with 1 decimal place
 */
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

/**
 * Get color for efficiency value
 */
export function getEfficiencyColor(efficiency: number): string {
  if (efficiency >= 70) return '#3fb950'; // green
  if (efficiency >= 50) return '#ffcc00'; // yellow
  return '#f85149'; // red
}

/**
 * Get color for K/D ratio
 */
export function getKDColor(kd: number): string {
  if (kd >= 2.0) return '#3fb950'; // green
  if (kd >= 1.0) return '#ffcc00'; // yellow
  return '#f85149'; // red
}

/**
 * Get color for threat level
 */
export function getThreatColor(level: 'low' | 'medium' | 'high'): string {
  switch (level) {
    case 'high':
      return '#f85149'; // red
    case 'medium':
      return '#ffcc00'; // yellow
    case 'low':
      return '#3fb950'; // green
  }
}
