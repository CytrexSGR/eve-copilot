/**
 * DOTLAN Integration Types for Geography Tab
 *
 * Types for the extended geography data from DOTLAN scrapers,
 * including live system activity, sovereignty campaigns, territorial changes,
 * and alliance power metrics.
 */

// ============================================================================
// Section 1: Live Activity Monitor
// ============================================================================

export interface DotlanSystemActivity {
  solar_system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  npc_kills: number;
  ship_kills: number;
  pod_kills: number;
  jumps: number;
  heat_index: number; // 0-1 normalized
  last_activity: string | null; // ISO timestamp
}

export interface LiveActivityData {
  systems: DotlanSystemActivity[];
  refresh_rate_seconds: number;
  last_scraped: string | null;
}

// ============================================================================
// Section 2: Sovereignty Defense Status
// ============================================================================

export type VulnerabilityLevel = 'critical' | 'vulnerable' | 'defended' | 'unknown';

export interface SovCampaign {
  campaign_id: number;
  solar_system_id: number;
  system_name: string | null;
  region_name: string | null;
  structure_type: string; // 'IHUB', 'TCU', etc.
  defender_name: string | null;
  score: number | null; // 0-100 percentage
  status: string;
  last_updated: string | null;
  adm_level: number | null;
  vulnerability: VulnerabilityLevel;
}

export interface SovDefenseData {
  campaigns: SovCampaign[];
  total_active: number;
  critical_count: number;
  refresh_rate_seconds: number;
}

// ============================================================================
// Section 3: Territorial Changes Timeline
// ============================================================================

export type ChangeDirection = 'gained' | 'lost' | 'neutral';

export interface SovChange {
  id: number;
  solar_system_id: number;
  system_name: string | null;
  region_name: string | null;
  change_type: string;
  old_alliance_name: string | null;
  new_alliance_name: string | null;
  changed_at: string | null;
  change_direction: ChangeDirection;
}

export interface TerritorialChangesData {
  changes: SovChange[];
  net_gained: number;
  net_lost: number;
  period_days: number;
}

// ============================================================================
// Section 4: Alliance Power Index
// ============================================================================

export interface AlliancePower {
  alliance_name: string;
  alliance_id: number | null;
  systems_count: number;
  member_count: number;
  corp_count: number;
  rank_by_systems: number | null;
  systems_delta: number;
  member_delta: number;
}

export interface AlliancePowerData {
  alliances: AlliancePower[];
  total_systems: number;
  total_members: number;
}

// ============================================================================
// Combined Extended Geography Response
// ============================================================================

import type { GeographyRegion, GeographySystem, HomeSystem } from './corporation';

export interface GeographyExtended {
  // Existing zKill data
  regions: GeographyRegion[];
  top_systems: GeographySystem[];
  home_systems: HomeSystem[];

  // New DOTLAN data
  live_activity: LiveActivityData;
  sov_defense: SovDefenseData;
  territorial_changes: TerritorialChangesData;
  alliance_power: AlliancePowerData;
}

// ============================================================================
// Utility Types
// ============================================================================

/** Heat level categories for UI styling */
export type HeatLevel = 'critical' | 'high' | 'medium' | 'low' | 'safe';

/** Get heat level from normalized heat index */
export function getHeatLevel(heatIndex: number): HeatLevel {
  if (heatIndex > 0.8) return 'critical';
  if (heatIndex > 0.6) return 'high';
  if (heatIndex > 0.4) return 'medium';
  if (heatIndex > 0.2) return 'low';
  return 'safe';
}

/** Get color for heat level */
export function getHeatColor(heatIndex: number): string {
  if (heatIndex > 0.8) return 'var(--danger, #f85149)';
  if (heatIndex > 0.6) return '#ff6b35';
  if (heatIndex > 0.4) return 'var(--warning, #d29922)';
  if (heatIndex > 0.2) return 'var(--accent-blue, #58a6ff)';
  return 'var(--success, #3fb950)';
}

/** Get vulnerability color */
export function getVulnerabilityColor(level: VulnerabilityLevel): string {
  switch (level) {
    case 'critical':
      return 'var(--danger, #f85149)';
    case 'vulnerable':
      return 'var(--warning, #d29922)';
    case 'defended':
      return 'var(--success, #3fb950)';
    default:
      return 'var(--text-tertiary, #8b949e)';
  }
}

/** Get change direction color */
export function getChangeColor(direction: ChangeDirection): string {
  switch (direction) {
    case 'gained':
      return 'var(--success, #3fb950)';
    case 'lost':
      return 'var(--danger, #f85149)';
    default:
      return 'var(--text-tertiary, #8b949e)';
  }
}
