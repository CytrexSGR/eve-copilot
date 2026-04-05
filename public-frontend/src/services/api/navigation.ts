import { api } from './client';
import type {
  JumpShip, JumpRange, JumpRoute, FatigueResult, CynoAltPlan,
} from '../../types/navigation';

// API client imported from ./client

export const jumpApi = {
  getShips: async (): Promise<{ ships: JumpShip[] }> => {
    const { data } = await api.get('/jump/ships');
    return data;
  },

  getRange: async (shipName: string, jdcLevel = 5, jfLevel = 5): Promise<JumpRange> => {
    const { data } = await api.get(`/jump/range/${encodeURIComponent(shipName)}`, {
      params: { jdc_level: jdcLevel, jf_level: jfLevel },
    });
    return data;
  },

  calculateRoute: async (params: {
    origin_id: number;
    destination_id: number;
    ship_name?: string;
    jdc_level?: number;
    jf_level?: number;
    avoid_jammed?: boolean;
  }): Promise<JumpRoute> => {
    const { data } = await api.get('/jump/route', { params });
    return data;
  },

  calculateFatigue: async (distanceLy: number, currentFatigue = 0): Promise<FatigueResult> => {
    const { data } = await api.get('/jump/fatigue', {
      params: { distance_ly: distanceLy, current_fatigue: currentFatigue },
    });
    return data;
  },

  planCynoAlts: async (params: {
    origin_id: number;
    destination_id: number;
    ship_name?: string;
    jdc_level?: number;
    jf_level?: number;
    prefer_stations?: boolean;
  }): Promise<CynoAltPlan> => {
    const { data } = await api.get('/jump/cyno-alts', { params });
    return data;
  },

  getSystemDistance: async (originId: number, destId: number) => {
    const { data } = await api.get('/jump/distance', {
      params: { origin_id: originId, destination_id: destId },
    });
    return data;
  },
};
