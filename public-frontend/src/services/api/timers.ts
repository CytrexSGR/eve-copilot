import { createApiClient } from './client';
import type {
  TimerUpcomingResponse, StructureTimer, TimerCreateRequest, TimerStats,
} from '../../types/timers';

const api = createApiClient('/api/timers');

export const timerApi = {
  getUpcoming: async (params?: {
    hours?: number;
    category?: string;
    region_id?: number;
    alliance_id?: number;
  }): Promise<TimerUpcomingResponse> => {
    const { data } = await api.get('/upcoming', { params });
    return data;
  },

  get: async (timerId: number): Promise<StructureTimer> => {
    const { data } = await api.get(`/${timerId}`);
    return data;
  },

  create: async (req: TimerCreateRequest): Promise<{ id: number; message: string; systemName: string; regionName: string }> => {
    const { data } = await api.post('/', req);
    return data;
  },

  update: async (timerId: number, updates: {
    timerEnd?: string;
    result?: string;
    isActive?: boolean;
    notes?: string;
  }): Promise<{ message: string; id: number }> => {
    const { data } = await api.patch(`/${timerId}`, updates);
    return data;
  },

  remove: async (timerId: number): Promise<{ message: string; id: number }> => {
    const { data } = await api.delete(`/${timerId}`);
    return data;
  },

  getBySystem: async (systemId: number): Promise<{ systemId: number; timers: StructureTimer[] }> => {
    const { data } = await api.get(`/system/${systemId}`);
    return data;
  },

  getStats: async (): Promise<TimerStats> => {
    const { data } = await api.get('/stats/summary');
    return data;
  },

  transition: async (timerId: number, newState: string): Promise<{ timerId: number; state: string }> => {
    const { data } = await api.post(`/${timerId}/transition`, null, { params: { new_state: newState } });
    return data;
  },

  expireOld: async (): Promise<{ expiredCount: number; timerIds: number[] }> => {
    const { data } = await api.post('/expire-old');
    return data;
  },
};
