import { createApiClient } from './client';
import type {
  RedListEntity, RedListCreateRequest, RedListCheckResult,
  VettingReport, VettingCheckRequest,
  ActivitySummary, FleetSession, InactiveMember,
  HrApplication, ApplicationReview,
} from '../../types/hr';

const api = createApiClient('/api/hr');

export const redListApi = {
  getEntries: async (params?: {
    category?: string;
    active_only?: boolean;
  }): Promise<RedListEntity[]> => {
    const { data } = await api.get('/redlist', { params });
    return Array.isArray(data) ? data : [];
  },

  addEntry: async (entry: RedListCreateRequest): Promise<RedListEntity> => {
    const { data } = await api.post('/redlist', entry);
    return data;
  },

  removeEntry: async (entryId: number): Promise<void> => {
    await api.delete(`/redlist/${entryId}`);
  },

  checkEntity: async (entityId: number): Promise<RedListCheckResult> => {
    const { data } = await api.get(`/redlist/check/${entityId}`);
    return data;
  },
};

export const vettingApi = {
  runCheck: async (request: VettingCheckRequest): Promise<VettingReport> => {
    const { data } = await api.post('/vetting/check', request);
    return data;
  },

  getReport: async (characterId: number): Promise<VettingReport | null> => {
    try {
      const { data } = await api.get(`/vetting/report/${characterId}`);
      return data;
    } catch {
      return null;
    }
  },

  getHistory: async (characterId: number): Promise<VettingReport[]> => {
    const { data } = await api.get(`/vetting/history/${characterId}`);
    return Array.isArray(data) ? data : [];
  },
};

export const activityApi = {
  getSummary: async (characterId: number): Promise<ActivitySummary> => {
    const { data } = await api.get(`/activity/summary/${characterId}`);
    return data;
  },

  getFleetSessions: async (params?: {
    character_id?: number;
    limit?: number;
  }): Promise<FleetSession[]> => {
    const { data } = await api.get('/activity/fleet-sessions', { params });
    return Array.isArray(data) ? data : [];
  },

  getInactive: async (days?: number): Promise<InactiveMember[]> => {
    const { data } = await api.get('/activity/inactive', { params: { days } });
    return Array.isArray(data) ? data : [];
  },
};

export const applicationApi = {
  getApplications: async (params?: {
    status?: string;
    corporation_id?: number;
    limit?: number;
  }): Promise<{ applications: HrApplication[]; count: number }> => {
    const { data } = await api.get('/applications/', { params });
    return data;
  },

  getApplication: async (applicationId: number): Promise<HrApplication> => {
    const { data } = await api.get(`/applications/${applicationId}`);
    return data;
  },

  reviewApplication: async (applicationId: number, review: ApplicationReview): Promise<{ application_id: number; status: string }> => {
    const { data } = await api.put(`/applications/${applicationId}/review`, review);
    return data;
  },

  vetApplication: async (applicationId: number): Promise<{ application_id: number; vetting_report: VettingReport }> => {
    const { data } = await api.post(`/applications/${applicationId}/vet`);
    return data;
  },
};
