import { api } from './client';
import type {
  DScanResult, DScanComparison, LocalScanResult,
  EsiNotification, NotificationType,
} from '../../types/military';

// API client imported from ./client

export const dscanApi = {
  parse: async (rawText: string): Promise<DScanResult> => {
    const { data } = await api.post('/military/dscan/parse', { rawText });
    return data;
  },

  compare: async (scanA: string, scanB: string): Promise<DScanComparison> => {
    const { data } = await api.post('/military/dscan/compare', { scanA, scanB });
    return data;
  },
};

export const localScanApi = {
  analyze: async (rawText: string, days = 7, systemId?: number): Promise<LocalScanResult> => {
    const { data } = await api.post('/military/local/analyze', {
      rawText,
      systemId: systemId || undefined,
    }, {
      params: { days },
    });
    return data;
  },
};

export const notificationApi = {
  getRecent: async (params?: {
    character_id?: number;
    notification_type?: string;
    unprocessed_only?: boolean;
    limit?: number;
  }): Promise<{ notifications: EsiNotification[]; count: number }> => {
    const { data } = await api.get('/notifications/recent', { params });
    return data;
  },

  getTypes: async (): Promise<{ types: NotificationType[] }> => {
    const { data } = await api.get('/notifications/types');
    return data;
  },

  markProcessed: async (notificationId: number): Promise<void> => {
    await api.post(`/notifications/mark-processed/${notificationId}`);
  },
};
