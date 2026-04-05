import type { Battle } from '@/app/api/battles/route';
import type { SovCampaign } from '@/app/api/dotlan-campaigns/route';

export type ColorMode = 'region' | 'security' | 'faction' | 'alliance' | 'npc_kills' | 'ship_kills' | 'jumps' | 'adm' | 'entity_activity' | 'hunting';

export interface LiveKill {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  ship_type_id: number;
  ship_name: string | null;
  ship_value: number;
  victim_corporation_id?: number;
  victim_corp_name?: string;
  battle_id?: number | null;
}

export interface LiveKillsResponse {
  kills: LiveKill[];
  count: number;
  minutes: number;
}

export interface HoveredSystem {
  systemId: number;
  name: string;
  security: number;
  x: number;
  y: number;
  regionName?: string;
  factionName?: string;
  allianceName?: string;
  activityValue?: number;
  activityMetric?: string;
  admLevel?: number;
  huntingScore?: number;
  huntingDeaths?: number;
  huntingAvgIsk?: number;
  huntingCapitals?: boolean;
}

export interface HoveredBattle {
  battle: Battle;
  x: number;
  y: number;
}

export interface HoveredKill {
  kill: LiveKill;
  systemName: string;
  regionName: string;
  x: number;
  y: number;
}

export interface HoveredCampaign {
  campaign: SovCampaign;
  x: number;
  y: number;
}

export interface CameraState {
  x: number;
  y: number;
  zoom: number;
}


export interface EntityActivitySystem {
  activity: number;
  isHome: boolean;
  kills: number;
  deaths: number;
}

export interface EntityActivityData {
  systems: Record<number, EntityActivitySystem>;
  regions: Array<{ region_id: number; region_name: string; activity: number }>;
  maxActivity: number;
  allianceId?: number | null;
}

export interface HuntingHeatmapData {
  systems: Record<number, { score: number; deaths: number; avg_isk: number; has_capitals: boolean }>;
  max_score: number;
}

export interface CapitalActivityData {
  systems: Record<number, { sightings: number; capital_classes: string[]; last_seen: string }>;
  max_sightings: number;
}

export interface LogiPresenceData {
  systems: Record<number, { logi_pilots: number; fleet_size: number; logi_ratio: number }>;
  max_ratio: number;
}

export interface TheraConnection {
  id: string;
  wh_type: string;
  max_ship_size: 'small' | 'medium' | 'large' | 'xlarge' | 'capital';
  remaining_hours: number;
  expires_at: string;
  out_system_id: number;
  out_system_name: string;
  in_system_id: number;
  in_system_name: string;
  in_system_class: string;
  in_region_id: number;
  in_region_name: string;
}

export interface HoveredTheraConnection {
  connection: TheraConnection;
  x: number;
  y: number;
}

export type { Battle, SovCampaign };
