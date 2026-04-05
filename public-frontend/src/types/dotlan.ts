/**
 * DOTLAN API Types - Sovereignty campaigns and related data
 */

export interface SovCampaign {
  campaign_id: number;
  solar_system_id: number;
  solar_system_name: string | null;
  region_id: number | null;
  region_name: string | null;
  structure_type: 'IHUB' | 'TCU' | 'STATION';
  defender_name: string | null;
  defender_id: number | null;
  score: number | null;  // 0.0-1.0 (null = reinforced)
  status: string;
  first_seen: string;
  last_updated: string;
}

// Grouped by region for display
export interface RegionCampaignGroup {
  region_name: string;
  region_id: number;
  campaigns: SovCampaign[];
  defender_name: string;  // Primary defender (most systems)
  system_count: number;
}
