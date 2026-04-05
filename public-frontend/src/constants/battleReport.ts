export type TabId = 'battlefield' | 'alliances' | 'intelligence';

export const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'battlefield', label: 'Battlefield', icon: '⚔️' },
  { id: 'alliances', label: 'Alliances', icon: '🛡️' },
  { id: 'intelligence', label: 'Intel', icon: '🤖' },
];

export const TAB_COLORS: Record<TabId, string> = {
  battlefield: '#ff4444',
  alliances: '#a855f7',
  intelligence: '#00d4ff',
};

export const SHIP_CLASS_CATEGORIES: Record<string, { color: string; types: string[] }> = {
  'Capitals': { color: '#ff4444', types: ['titan', 'supercarrier', 'carrier', 'dreadnought', 'fax', 'capital'] },
  'Battleships': { color: '#ff8800', types: ['battleship'] },
  'Cruisers': { color: '#ffcc00', types: ['cruiser', 'heavy_assault', 'recon', 'strategic_cruiser'] },
  'Frigates': { color: '#00ff88', types: ['frigate', 'interceptor', 'assault_frigate', 'covert_ops'] },
  'Industrial': { color: '#00d4ff', types: ['industrial', 'freighter', 'mining'] },
  'Other': { color: '#a855f7', types: [] }
};

export const RACE_COLORS: Record<string, string> = {
  Minmatar: '#c44536',
  Gallente: '#4a9c2d',
  Caldari: '#4a90d9',
  Amarr: '#d4af37'
};

export const SHIP_CLASS_COLORS: Record<string, string> = {
  Dreadnought: '#00d4ff',
  Supercarrier: '#ff8800',
  Titan: '#ff4444'
};
