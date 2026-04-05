// Structure Timer types (war-intel-service uses camelCase)

export interface StructureTimer {
  id: number;
  structureId: number | null;
  structureName: string;
  category: string;
  systemId: number;
  systemName: string;
  regionName: string;
  ownerAllianceId?: number | null;
  ownerAllianceName: string | null;
  timerType: string;
  timerStart?: string | null;
  timerEnd: string;
  hoursUntil: number;
  urgency: 'critical' | 'urgent' | 'upcoming' | 'planned';
  state?: string;
  cynoJammed: boolean;
  isActive: boolean;
  result: string | null;
  source: string;
  reportedBy?: string | null;
  notes: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface TimerSummary {
  critical: number;
  urgent: number;
  upcoming: number;
  planned: number;
  total: number;
}

export interface TimerUpcomingResponse {
  summary: TimerSummary;
  timers: StructureTimer[];
}

export interface TimerCreateRequest {
  structureName: string;
  category: string;
  systemId: number;
  timerType: string;
  timerEnd: string;
  structureId?: number;
  ownerAllianceId?: number;
  ownerAllianceName?: string;
  reportedBy?: string;
  notes?: string;
}

export interface TimerStats {
  activeTimers: {
    byCategory: Record<string, number>;
    byUrgency: Record<string, number>;
    total: number;
  };
  recentResults: Record<string, number>;
}

// Helpers

export const URGENCY_COLORS: Record<string, string> = {
  critical: '#f85149',
  urgent: '#ff8800',
  upcoming: '#d29922',
  planned: '#8b949e',
};

export const CATEGORY_LABELS: Record<string, string> = {
  tcurfc: 'Citadel/EC/Refinery',
  ihub: 'IHUB',
  poco: 'POCO',
  pos: 'POS',
  ansiblex: 'Ansiblex',
  cyno_beacon: 'Cyno Beacon',
  cyno_jammer: 'Cyno Jammer',
};

export const TIMER_TYPE_LABELS: Record<string, string> = {
  armor: 'Armor',
  hull: 'Hull',
  anchoring: 'Anchoring',
  unanchoring: 'Unanchoring',
  online: 'Online',
};

export const RESULT_COLORS: Record<string, string> = {
  defended: '#3fb950',
  destroyed: '#f85149',
  repaired: '#00d4ff',
  captured: '#d29922',
};

export function formatTimeUntil(hours: number): string {
  if (hours < 0) return 'Expired';
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  const d = Math.floor(hours / 24);
  const h = Math.round(hours % 24);
  return `${d}d ${h}h`;
}
