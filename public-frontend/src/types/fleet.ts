// Fleet Operations types (war-intel-service uses camelCase)

export interface FleetOperation {
  id: number;
  fleetName: string;
  fcCharacterId: number | null;
  fcName: string | null;
  doctrineId: number | null;
  startTime: string;
  endTime: string | null;
  isActive: boolean;
  notes: string | null;
  createdAt: string;
}

export interface FleetOperationSummary {
  id: number;
  fleetName: string;
  fcName: string | null;
  doctrineId: number | null;
  startTime: string;
  endTime: string | null;
  isActive: boolean;
  notes: string | null;
  memberCount: number;
  snapshotCount: number;
  totalParticipants?: number;
  totalSnapshots?: number;
  durationMinutes?: number;
}

export interface FleetMember {
  characterId: number;
  characterName: string | null;
  shipTypeId: number | null;
  shipName: string | null;
  shipTypeName: string | null;
  solarSystemId: number | null;
  firstSeen: string;
  lastSeen: string;
  snapshotCount: number;
  participationPct?: number;
}

export interface FleetStatus {
  fleet: FleetOperation;
  snapshotCount: number;
  memberCount: number;
  members: FleetMember[];
}

export interface FleetParticipation {
  fleet: FleetOperation;
  totalSnapshots: number;
  totalParticipants: number;
  participants: FleetMember[];
}

export interface FleetRegisterRequest {
  fleetName: string;
  fcCharacterId?: number;
  fcName?: string;
  doctrineId?: number;
  notes?: string;
}

export interface FleetSnapshotMember {
  characterId: number;
  characterName?: string;
  shipTypeId?: number;
  shipName?: string;
  solarSystemId?: number;
}

// Helpers

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

// Ops Calendar types (military-service uses snake_case)

export type OpImportance = 'normal' | 'important' | 'cta';
export type OpType = 'stratop' | 'roam' | 'mining' | 'defense' | 'other';

export interface ScheduledOperation {
  id: number;
  title: string;
  description?: string;
  fc_character_id: number;
  fc_name: string;
  doctrine_id?: number;
  doctrine_name?: string;
  formup_system?: string;
  formup_time: string;
  op_type: string;
  importance: string;
  max_pilots?: number;
  is_cancelled: boolean;
  fleet_operation_id?: number;
  created_at: string;
  corporation_id: number;
}
