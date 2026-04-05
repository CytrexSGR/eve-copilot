export const WORMHOLE_TAB_CONFIG = [
  { id: 'hunters' as const, label: 'Hunters', icon: '🎯', color: '#ff4444' },
  { id: 'market' as const, label: 'Market', icon: '📈', color: '#00ff88' },
  { id: 'residents' as const, label: 'Residents', icon: '👥', color: '#00d4ff' },
  { id: 'thera-router' as const, label: 'Thera', icon: '🗺️', color: '#ffcc00' },
] as const;

export const WORMHOLE_CLASS_COLORS: Record<number, string> = {
  1: '#4488ff',  // C1 - Blue (Low)
  2: '#4488ff',  // C2 - Blue (Low)
  3: '#00ff88',  // C3 - Green (Mid)
  4: '#00ff88',  // C4 - Green (Mid)
  5: '#ff8800',  // C5 - Orange (High)
  6: '#ff2222',  // C6 - Red (Apex)
  // Special classes
  13: '#ffcc00', // C13 - Shattered (Yellow)
  14: '#00ff88', // Thera (Green)
  15: '#ff4444', // Sentinel (Drifter - Red)
  16: '#ff4444', // Barbican (Drifter - Red)
  17: '#ff4444', // Vidette (Drifter - Red)
  18: '#ff4444', // Conflux (Drifter - Red)
};

export const ACTIVITY_LEVEL_COLORS: Record<string, string> = {
  LOW: '#888888',
  MODERATE: '#ffcc00',
  HIGH: '#ff4444',
};

export const THREAT_SEVERITY_COLORS: Record<string, string> = {
  critical: '#ff2222',
  warning: '#ff8800',
  info: '#ffcc00',
};

export const DIFFICULTY_COLORS: Record<string, string> = {
  EASY: '#00ff88',
  MEDIUM: '#ffcc00',
  HARD: '#ff4444',
};

export const WORMHOLE_TICKER_TAGS = {
  KILL: { icon: '💀', label: 'KILL', color: '#ff4444' },
  EVICTION: { icon: '🔥', label: 'EVICTION', color: '#ff8800' },
  RESIDENT: { icon: '👁', label: 'RESIDENT', color: '#00d4ff' },
  SPIKE: { icon: '⚡', label: 'SPIKE', color: '#ffcc00' },
};
