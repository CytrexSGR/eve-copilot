// Power Bloc Detail API Client
import type {
  PBHuntingResponse, PBDetailsResponse, PBOffensiveResponse,
  PBDefensiveResponse, PBCapitalsResponse, PBWormholeResponse,
  PBCapsuleersResponse
} from '../../types/powerbloc';

const API_BASE = '/api';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
  return res.json();
}

export const powerblocApi = {
  getHunting: (id: number, days = 30) =>
    fetchJson<PBHuntingResponse>(`${API_BASE}/powerbloc/${id}/hunting?days=${days}`),
  getDetails: (id: number, days = 7) =>
    fetchJson<PBDetailsResponse>(`${API_BASE}/powerbloc/${id}/details?days=${days}`),
  getOffensive: (id: number, days = 7) =>
    fetchJson<PBOffensiveResponse>(`${API_BASE}/powerbloc/${id}/offensive?days=${days}`),
  getDefensive: (id: number, days = 7) =>
    fetchJson<PBDefensiveResponse>(`${API_BASE}/powerbloc/${id}/defensive?days=${days}`),
  getCapitals: (id: number, days = 7) =>
    fetchJson<PBCapitalsResponse>(`${API_BASE}/powerbloc/${id}/capitals?days=${days}`),
  getWormhole: (id: number, days = 30) =>
    fetchJson<PBWormholeResponse>(`${API_BASE}/powerbloc/${id}/wormhole?days=${days}`),
  getCapsuleers: (id: number, days = 7) =>
    fetchJson<PBCapsuleersResponse>(`${API_BASE}/powerbloc/${id}/capsuleers?days=${days}`),
  getAlliancesRanking: (id: number, days = 30) =>
    fetchJson<any[]>(`${API_BASE}/powerbloc/${id}/alliances-ranking?days=${days}`),
  getAlliancesTrends: (id: number, days = 30) =>
    fetchJson<any[]>(`${API_BASE}/powerbloc/${id}/alliances-trends?days=${days}`),
  getAlliancesShips: (id: number, days = 30) =>
    fetchJson<any[]>(`${API_BASE}/powerbloc/${id}/alliances-ships?days=${days}`),
  getAlliancesRegions: (id: number, days = 30) =>
    fetchJson<any[]>(`${API_BASE}/powerbloc/${id}/alliances-regions?days=${days}`),
  getVictimTankProfile: (id: number, days = 7) =>
    fetchJson<VictimTankProfile>(`${API_BASE}/powerbloc/${id}/victim-tank-profile?days=${days}`),
};

// Victim Tank Profile Types
export interface VictimTankProfile {
  coalition_name: string;
  period_days: number;
  killmails_analyzed: number;
  tank_distribution: {
    shield: number;
    armor: number;
    hull: number;
  };
  resist_weaknesses: Array<{
    damage_type: string;
    avg_resist: number;
    weakness_level: 'EXPLOIT' | 'SOFT' | 'NORMAL';
  }>;
  fleet_effectiveness: {
    avg_victim_ehp: number;
    estimated_fleet_dps: number;
    avg_time_to_kill_seconds: number;
    overkill_ratio: number;
  };
  top_ship_classes: Array<{
    ship_class: string;
    count: number;
    shield_pct: number;
    armor_pct: number;
  }>;
}
