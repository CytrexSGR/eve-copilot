/**
 * Application-wide constants for the public frontend
 */

// Refresh intervals
export const AUTO_REFRESH_SECONDS = 60;
export const TICKER_REFRESH_MS = 30_000;

// Display limits
export const MAX_TICKER_ALERTS = 30;
export const MAX_POWER_ENTRIES = 5;
export const MAX_CONFLICTS_DISPLAY = 4;
export const MAX_ROUTES_DISPLAY = 6;

// Map defaults
export const DEFAULT_ACTIVITY_MINUTES = 60;
export const ACTIVITY_OPTIONS = [
  { value: 10, label: '10m' },
  { value: 60, label: '1h' },
] as const;

// Status levels with colors
export const STATUS_LEVELS = {
  gank: { label: 'Gank', color: '#ff4444' },
  brawl: { label: 'Brawl', color: '#ff8800' },
  battle: { label: 'Battle', color: '#ffcc00' },
  hellcamp: { label: 'Hellcamp', color: '#00d4ff' },
} as const;

export type StatusLevel = keyof typeof STATUS_LEVELS;

// Color modes for map
export const COLOR_MODES = {
  region: { label: 'Reg' },
  security: { label: 'Sec' },
  faction: { label: 'FW' },
  alliance: { label: 'Sov' },
} as const;

export type ColorMode = keyof typeof COLOR_MODES;

// Danger level thresholds
export const DANGER_THRESHOLDS = {
  CRITICAL: 7,
  HIGH: 4,
  MODERATE: 2,
} as const;

// Danger level colors
export const DANGER_COLORS = {
  SAFE: '#00ff88',
  MODERATE: '#ffcc00',
  HIGH: '#ff8800',
  CRITICAL: '#ff4444',
} as const;

// UI Colors
export const COLORS = {
  positive: '#00ff88',
  negative: '#ff4444',
  warning: '#ff8800',
  accent: '#00d4ff',
  accentBlue: '#00d4ff',
  textSecondary: 'rgba(255,255,255,0.5)',
  textTertiary: 'rgba(255,255,255,0.4)',
  borderSubtle: 'rgba(255,255,255,0.1)',
} as const;

// API timeouts
export const API_TIMEOUT_MS = 60_000;

// ISK formatting
export const ISK_BILLION = 1_000_000_000;
export const ISK_MILLION = 1_000_000;
