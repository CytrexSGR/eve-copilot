/**
 * Corporation Detail API Client
 *
 * Provides typed API methods for corporation intelligence endpoints.
 */

import type {
  CorporationBasicInfo,
  HuntingOverview,
  TopPilot,
  Doctrine,
  HotZone,
  TimezoneActivity,
  OffensiveStats,
  DefensiveStats,
  PilotRanking,
  PilotIntel,
  CapitalIntel,
  Geography,
  ActivityTimeline,
  TimelineResponse,
  OffensiveOverview,
  DefensiveOverview,
  CapitalSummary,
  PilotSummary,
  GeographySummary,
  ActivitySummary,
  HuntingSummary,
  ParticipationTrendsResponse,
  BurnoutIndexResponse,
  AttritionTrackerResponse,
  GeographyExtended,
} from '../types/corporation';

const API_BASE = '/api/intelligence/fast/corporation';

/**
 * Corporation Detail API Client
 */
export const corpApi = {
  /**
   * Get basic corporation info (for header)
   */
  getBasicInfo: async (corpId: number, days = 30): Promise<CorporationBasicInfo> => {
    const res = await fetch(`${API_BASE}/${corpId}/basic-info?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch corporation basic info');
    return res.json();
  },

  /**
   * Get hunting overview (Hunting tab)
   */
  getHuntingOverview: async (corpId: number, days = 30): Promise<HuntingOverview> => {
    const res = await fetch(`${API_BASE}/${corpId}/hunting-overview?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch hunting overview');
    return res.json();
  },

  /**
   * Get top high-value target pilots (Hunting tab)
   */
  getTopPilots: async (corpId: number, days = 30): Promise<TopPilot[]> => {
    const res = await fetch(`${API_BASE}/${corpId}/top-pilots?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch top pilots');
    return res.json();
  },

  /**
   * Get doctrine analysis (Hunting tab)
   */
  getDoctrines: async (corpId: number, days = 30): Promise<Doctrine[]> => {
    const res = await fetch(`${API_BASE}/${corpId}/doctrines?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch doctrines');
    return res.json();
  },

  /**
   * Get hot zones / top systems (Hunting tab)
   */
  getHotZones: async (corpId: number, days = 30): Promise<HotZone[]> => {
    const res = await fetch(`${API_BASE}/${corpId}/hot-zones?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch hot zones');
    return res.json();
  },

  /**
   * Get 24-hour timezone activity heatmap (Hunting/Activity tab)
   */
  getTimezoneActivity: async (corpId: number, days = 30): Promise<TimezoneActivity[]> => {
    const res = await fetch(`${API_BASE}/${corpId}/timezone-activity?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch timezone activity');
    return res.json();
  },

  /**
   * Get offensive kill statistics (Offensive tab)
   */
  getOffensiveStats: async (corpId: number, days = 30): Promise<OffensiveStats> => {
    const res = await fetch(`${API_BASE}/${corpId}/offensive-stats?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch offensive stats');
    return res.json();
  },

  /**
   * Get defensive loss statistics (Defensive tab)
   */
  getDefensiveStats: async (corpId: number, days = 30): Promise<DefensiveStats> => {
    const res = await fetch(`${API_BASE}/${corpId}/defensive-stats?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch defensive stats');
    return res.json();
  },

  /**
   * Get pilot ranking (Pilots tab)
   */
  getPilotRanking: async (corpId: number, days = 30): Promise<PilotRanking[]> => {
    const res = await fetch(`${API_BASE}/${corpId}/pilot-ranking?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch pilot ranking');
    return res.json();
  },

  /**
   * Get comprehensive pilot intelligence (Pilots tab - enhanced)
   */
  getPilotIntel: async (corpId: number, days = 30): Promise<PilotIntel> => {
    const res = await fetch(`${API_BASE}/${corpId}/pilot-intel?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch pilot intel');
    return res.json();
  },

  /**
   * Get capital fleet intelligence (Capitals tab)
   */
  getCapitalIntel: async (corpId: number, days = 30): Promise<CapitalIntel> => {
    const res = await fetch(`${API_BASE}/${corpId}/capital-intel?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch capital intel');
    return res.json();
  },

  /**
   * Get geographic operations map (Geography tab)
   */
  getGeography: async (corpId: number, days = 30): Promise<Geography> => {
    const res = await fetch(`${API_BASE}/${corpId}/geography?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch geography');
    return res.json();
  },

  /**
   * Get extended geography with DOTLAN integration
   *
   * Returns existing zKillboard data plus:
   * - live_activity: Real-time system activity from DOTLAN
   * - sov_defense: Active sovereignty campaigns + ADM levels
   * - territorial_changes: Recent sovereignty changes
   * - alliance_power: Alliance statistics and trends
   */
  getGeographyExtended: async (corpId: number, days = 30): Promise<GeographyExtended> => {
    const res = await fetch(`${API_BASE}/${corpId}/geography/extended?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch extended geography');
    return res.json();
  },

  /**
   * Get activity timeline with trends (Hunting tab + Overview)
   */
  getActivityTimeline: async (corpId: number, days = 30): Promise<ActivityTimeline> => {
    const res = await fetch(`${API_BASE}/${corpId}/activity-timeline?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch activity timeline');
    return res.json();
  },

  /**
   * Get lightweight kill/death timeline (Overview tab - optimized for timeline cards)
   */
  getTimeline: async (corpId: number, days = 30): Promise<TimelineResponse> => {
    const res = await fetch(`${API_BASE}/${corpId}/timeline?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch timeline');
    return res.json();
  },

  // ============================================================================
  // Overview Tab - Summary Extracts
  // ============================================================================

  /**
   * Get offensive intelligence summary (Overview tab)
   */
  getOffensiveSummary: async (corpId: number, days = 30): Promise<OffensiveOverview> => {
    const res = await fetch(`${API_BASE}/${corpId}/offensive-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch offensive summary');
    return res.json();
  },

  /**
   * Get defensive intelligence summary (Overview tab)
   */
  getDefensiveSummary: async (corpId: number, days = 30): Promise<DefensiveOverview> => {
    const res = await fetch(`${API_BASE}/${corpId}/defensive-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch defensive summary');
    return res.json();
  },

  /**
   * Get capital warfare intelligence summary (Overview tab)
   */
  getCapitalSummary: async (corpId: number, days = 30): Promise<CapitalSummary> => {
    const res = await fetch(`${API_BASE}/${corpId}/capital-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch capital summary');
    return res.json();
  },

  /**
   * Get pilot intelligence summary (Overview tab)
   */
  getPilotSummary: async (corpId: number, days = 30): Promise<PilotSummary> => {
    const res = await fetch(`${API_BASE}/${corpId}/pilot-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch pilot summary');
    return res.json();
  },

  /**
   * Get geographic intelligence summary (Overview tab)
   */
  getGeographySummary: async (corpId: number, days = 30): Promise<GeographySummary> => {
    const res = await fetch(`${API_BASE}/${corpId}/geography-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch geography summary');
    return res.json();
  },

  /**
   * Get activity intelligence summary (Overview tab)
   */
  getActivitySummary: async (corpId: number, days = 30): Promise<ActivitySummary> => {
    const res = await fetch(`${API_BASE}/${corpId}/activity-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch activity summary');
    return res.json();
  },

  /**
   * Get hunting intelligence summary (Overview tab)
   */
  getHuntingSummary: async (corpId: number, days = 30): Promise<HuntingSummary> => {
    const res = await fetch(`${API_BASE}/${corpId}/hunting-summary?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch hunting summary');
    return res.json();
  },

  /**
   * Get wormhole intelligence (Wormhole tab)
   */
  getWormholeIntel: async (corpId: number, days = 30): Promise<any> => {
    const res = await fetch(`/api/intelligence/corporation/${corpId}/wormhole?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch wormhole intelligence');
    return res.json();
  },

  // ============================================================================
  // Overview Tab - Additional Insights (from Alliance)
  // ============================================================================

  /**
   * Get participation trends (Overview tab)
   */
  getParticipationTrends: async (corpId: number, days = 14): Promise<ParticipationTrendsResponse> => {
    const res = await fetch(`${API_BASE}/${corpId}/participation-trends?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch participation trends');
    return res.json();
  },

  /**
   * Get burnout index (Overview tab)
   */
  getBurnoutIndex: async (corpId: number, days = 14): Promise<BurnoutIndexResponse> => {
    const res = await fetch(`${API_BASE}/${corpId}/burnout-index?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch burnout index');
    return res.json();
  },

  /**
   * Get attrition tracker (Overview tab)
   */
  getAttritionTracker: async (corpId: number, days = 30): Promise<AttritionTrackerResponse> => {
    const res = await fetch(`${API_BASE}/${corpId}/attrition-tracker?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch attrition tracker');
    return res.json();
  },
};
