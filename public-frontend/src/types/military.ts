// D-Scan types

export interface DScanShipType {
  typeId: number;
  typeName: string;
  count: number;
}

export interface DScanShipClass {
  shipClass: string;
  count: number;
  types: DScanShipType[];
}

export interface DScanStructure {
  typeName: string;
  name: string;
  distanceKm: number;
}

export interface DScanResult {
  totalItems: number;
  totalShips: number;
  shipClasses: DScanShipClass[];
  structures: DScanStructure[];
  deployables: DScanStructure[];
  capsules: number;
  threatLevel: 'none' | 'low' | 'medium' | 'high' | 'critical';
  threatSummary: string;
  unknownLines: number;
}

export interface DScanDelta {
  typeId: number;
  typeName: string;
  shipClass: string;
  delta: number;
}

export interface DScanComparison {
  newShips: DScanDelta[];
  goneShips: DScanDelta[];
  newCount: number;
  goneCount: number;
  deltaByClass: Record<string, number>;
}

// Local Scan types

export interface LocalPilot {
  characterName: string;
  characterId: number;
  corporationId: number;
  corporationName: string;
  allianceId: number | null;
  allianceName: string | null;
  isRedListed: boolean;
  redListSeverity: number | null;
  redListReason: string | null;
  recentKills: number;
  recentLosses: number;
  lastShipType: string | null;
  threatLevel: 'critical' | 'high' | 'medium' | 'low' | 'unknown';
}

export interface GroupBreakdown {
  allianceId?: number;
  allianceName?: string;
  corporationId?: number;
  corporationName?: string;
  count: number;
}

export interface LocalScanResult {
  totalPilots: number;
  identified: number;
  unidentified: number;
  redListed: number;
  hostiles: number;
  threatBreakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    unknown: number;
  };
  pilots: LocalPilot[];
  allianceBreakdown: GroupBreakdown[];
  corporationBreakdown: GroupBreakdown[];
}

// Notification types

export interface EsiNotification {
  notificationId: number;
  characterId: number;
  senderId: number;
  senderType: string;
  type: string;
  timestamp: string;
  isRead: boolean;
  processed: boolean;
  processedAt: string | null;
}

export interface NotificationType {
  type: string;
  count: number;
  latest: string;
}

// Threat level colors
export const THREAT_COLORS: Record<string, string> = {
  critical: '#ff4444',
  high: '#f85149',
  medium: '#d29922',
  low: '#3fb950',
  none: '#8b949e',
  unknown: '#8b949e',
};

// Ship class colors for D-Scan
export const SHIP_CLASS_COLORS: Record<string, string> = {
  Capital: '#ff4444',
  Battleship: '#f85149',
  Battlecruiser: '#ff8800',
  Cruiser: '#d29922',
  Destroyer: '#ffcc00',
  Frigate: '#3fb950',
  Industrial: '#58a6ff',
  Structure: '#a855f7',
  Deployable: '#8b949e',
  Capsule: '#6e7681',
  Other: '#484f58',
};
