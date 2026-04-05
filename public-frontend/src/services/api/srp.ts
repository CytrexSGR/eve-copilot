import { createApiClient } from './client';
import type {
  Doctrine, DoctrineCreate, DoctrineImportEft, DoctrineImportFitting,
  SrpRequest, SrpSubmitRequest, SrpReviewRequest, SrpConfig,
  DoctrineCloneRequest, DoctrineChangelogEntry, DoctrineAutoPrice,
  FleetReadiness, SkillPlanExport,
} from '../../types/srp';

const api = createApiClient('/api/finance');

export const doctrineApi = {
  list: async (corpId: number, activeOnly = true): Promise<{ doctrines: Doctrine[]; total: number }> => {
    const { data } = await api.get(`/doctrines/${corpId}`, { params: { active_only: activeOnly } });
    return data;
  },

  get: async (doctrineId: number): Promise<Doctrine> => {
    const { data } = await api.get(`/doctrine/${doctrineId}`);
    return data;
  },

  create: async (doctrine: DoctrineCreate): Promise<Doctrine> => {
    const { data } = await api.post('/doctrine', doctrine);
    return data;
  },

  importEft: async (req: DoctrineImportEft): Promise<Doctrine> => {
    const { data } = await api.post('/doctrine/import/eft', req);
    return data;
  },

  importDna: async (corpId: number, dnaString: string, name: string, basePayout?: number): Promise<Doctrine> => {
    const { data } = await api.post('/doctrine/import/dna', {
      corporation_id: corpId,
      dna_string: dnaString,
      name,
      base_payout: basePayout,
    });
    return data;
  },

  importFromFitting: async (data: DoctrineImportFitting): Promise<Doctrine> => {
    const { data: result } = await api.post('/doctrine/import/fitting', data);
    return result;
  },

  update: async (doctrineId: number, updates: Partial<Doctrine>): Promise<Doctrine> => {
    const { data } = await api.put(`/doctrine/${doctrineId}`, updates);
    return data;
  },

  archive: async (doctrineId: number): Promise<void> => {
    await api.delete(`/doctrine/${doctrineId}`);
  },

  clone: async (doctrineId: number, newName: string, category?: string): Promise<Doctrine> => {
    const body: DoctrineCloneRequest = { new_name: newName, category };
    const { data } = await api.post(`/doctrine/${doctrineId}/clone`, body);
    return data;
  },

  getPrice: async (doctrineId: number): Promise<DoctrineAutoPrice> => {
    const { data } = await api.get(`/doctrine/${doctrineId}/price`);
    return data;
  },

  getChangelog: async (doctrineId: number, limit = 50, offset = 0): Promise<DoctrineChangelogEntry[]> => {
    const { data } = await api.get(`/doctrine/${doctrineId}/changelog`, {
      params: { limit, offset },
    });
    return data;
  },

  getCorpChangelog: async (corpId: number, limit = 50, offset = 0): Promise<DoctrineChangelogEntry[]> => {
    const { data } = await api.get(`/doctrines/${corpId}/changelog`, {
      params: { limit, offset },
    });
    return data;
  },
};

export const srpApi = {
  getRequests: async (corpId: number, params?: {
    status?: string;
    character_id?: number;
    limit?: number;
    offset?: number;
  }): Promise<SrpRequest[]> => {
    const { data } = await api.get(`/srp/requests/${corpId}`, { params });
    return Array.isArray(data) ? data : data.requests || [];
  },

  getRequest: async (requestId: number): Promise<SrpRequest> => {
    const { data } = await api.get(`/srp/request/${requestId}`);
    return data;
  },

  submit: async (req: SrpSubmitRequest): Promise<SrpRequest> => {
    const { data } = await api.post('/srp/submit', req);
    return data;
  },

  review: async (requestId: number, review: SrpReviewRequest): Promise<SrpRequest> => {
    const { data } = await api.put(`/srp/request/${requestId}/review`, review);
    return data;
  },

  batchPaid: async (requestIds: number[]): Promise<{ updated: number }> => {
    const { data } = await api.post('/srp/batch-paid', { request_ids: requestIds });
    return data;
  },

  getPayoutList: async (corpId: number, status = 'approved'): Promise<string> => {
    const { data } = await api.get(`/srp/payout-list/${corpId}`, {
      params: { status },
      responseType: 'text' as const,
    });
    return data;
  },

  getConfig: async (corpId: number): Promise<SrpConfig> => {
    const { data } = await api.get(`/srp/config/${corpId}`);
    return data;
  },

  updateConfig: async (corpId: number, config: Partial<SrpConfig>): Promise<SrpConfig> => {
    const { data } = await api.put(`/srp/config/${corpId}`, config);
    return data;
  },

  syncPrices: async (corpId: number): Promise<{ synced: number; total_types: number }> => {
    const { data } = await api.post('/srp/sync-prices', null, { params: { corporation_id: corpId } });
    return data;
  },
};

const doctrineStatsAxios = createApiClient('/api/doctrines');

export const doctrineStatsApi = {
  getStats: (doctrineId: number, characterId?: number) =>
    doctrineStatsAxios.get(`/${doctrineId}/stats`, {
      params: characterId ? { character_id: characterId } : undefined,
    }).then(r => r.data),

  getReadiness: (doctrineId: number, characterId: number) =>
    doctrineStatsAxios.get(`/${doctrineId}/readiness/${characterId}`).then(r => r.data),

  getBom: (doctrineId: number, quantity: number = 1) =>
    doctrineStatsAxios.get(`/${doctrineId}/bom`, {
      params: { quantity },
    }).then(r => r.data),

  checkCompliance: (doctrineId: number, killmailItems: Array<{type_id: number; flag: number}>) =>
    doctrineStatsAxios.post('/compliance', {
      doctrine_id: doctrineId,
      killmail_items: killmailItems,
    }).then(r => r.data),

  getFleetReadiness: async (doctrineId: number, corpId: number): Promise<FleetReadiness> => {
    const { data } = await doctrineStatsAxios.get(`/${doctrineId}/fleet-readiness/${corpId}`);
    return data;
  },

  getSkillPlan: async (doctrineId: number, characterId: number, format: 'evemon' | 'text' = 'text'): Promise<SkillPlanExport> => {
    const { data } = await doctrineStatsAxios.get(`/${doctrineId}/skill-plan/${characterId}`, {
      params: { format },
    });
    return data;
  },
};
