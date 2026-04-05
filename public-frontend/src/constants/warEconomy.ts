// Trade hub regions for intelligence panel
export const TRADE_HUBS = [
  { id: 10000002, name: 'The Forge (Jita)' },
  { id: 10000043, name: 'Domain (Amarr)' },
  { id: 10000030, name: 'Heimatar (Rens)' },
  { id: 10000032, name: 'Sinq Laison (Dodixie)' },
  { id: 10000042, name: 'Metropolis (Hek)' }
] as const;

// Isotope to Capital Ship mapping
export const ISOTOPE_INFO: Record<number, { race: string; color: string; capitals: string }> = {
  16274: { race: 'Minmatar', color: '#c44536', capitals: 'Naglfar \u2022 Hel \u2022 Ragnarok' },
  17887: { race: 'Gallente', color: '#4a9c2d', capitals: 'Moros \u2022 Nyx \u2022 Erebus' },
  17888: { race: 'Caldari', color: '#4a90d9', capitals: 'Phoenix \u2022 Wyvern \u2022 Leviathan' },
  17889: { race: 'Amarr', color: '#d4af37', capitals: 'Revelation \u2022 Aeon \u2022 Avatar' }
};

// Anomaly threshold for visual gauge (% above baseline that triggers concern)
export const ANOMALY_THRESHOLDS = { warning: 10, danger: 25 };

// Activity thresholds based on kills/hour
// QUIET: < 80/hr (slow day), MODERATE: 80-150/hr (normal), ACTIVE: 150-250/hr (busy), HOT: 250+/hr (major conflict)
export const ACTIVITY_THRESHOLDS = {
  quiet: 80,
  moderate: 150,
  active: 250,
  maxScale: 300
} as const;

export const ACTIVITY_COLORS = {
  hot: '#ff4444',
  active: '#ff8800',
  moderate: '#ffcc00',
  quiet: '#00ff88'
} as const;

export const TAB_CONFIG = [
  { id: 'combat' as const, label: 'Combat', icon: '\u2694\uFE0F', color: '#ff4444' },
  { id: 'trading' as const, label: 'Trading', icon: '\uD83D\uDCB0', color: '#00ff88' },
  { id: 'routes' as const, label: 'Routes', icon: '\uD83D\uDEE3\uFE0F', color: '#00d4ff' },
  { id: 'signals' as const, label: 'Signals', icon: '\uD83D\uDCC8', color: '#ffcc00' },
  { id: 'intel' as const, label: 'Intel', icon: '\uD83E\uDD16', color: '#a855f7' },
] as const;

export type TabId = typeof TAB_CONFIG[number]['id'];
