import { createApiClient } from './client';
import type {
  FleetOperation, FleetOperationSummary, FleetStatus,
  FleetParticipation, FleetRegisterRequest, FleetSnapshotMember,
  ScheduledOperation,
} from '../../types/fleet';

// For fleet_comp (doctrines, counter, etc.) — routes at /api/fleet/...
const fleetCompApi = createApiClient('/api/fleet');

// For fleet_ops (register, active, history, status, etc.) — routes at /api/military/fleet/...
const militaryFleetApi = createApiClient('/api/military/fleet');

// For ops calendar — routes at /api/military/ops/...
const militaryOpsApi = createApiClient('/api/military/ops');

export const fleetApi = {
  register: async (req: FleetRegisterRequest): Promise<FleetOperation> => {
    const { data } = await militaryFleetApi.post('/register', req);
    return data;
  },

  getActive: async (): Promise<FleetOperationSummary[]> => {
    const { data } = await militaryFleetApi.get('/active');
    return Array.isArray(data) ? data : [];
  },

  getHistory: async (params?: { limit?: number; offset?: number }): Promise<FleetOperationSummary[]> => {
    const { data } = await militaryFleetApi.get('/history', { params });
    return Array.isArray(data) ? data : [];
  },

  getStatus: async (opId: number): Promise<FleetStatus> => {
    const { data } = await militaryFleetApi.get(`/${opId}/status`);
    return data;
  },

  getParticipation: async (opId: number): Promise<FleetParticipation> => {
    const { data } = await militaryFleetApi.get(`/${opId}/participation`);
    return data;
  },

  snapshot: async (opId: number, members: FleetSnapshotMember[]): Promise<{ operationId: number; membersRecorded: number }> => {
    const { data } = await militaryFleetApi.post(`/${opId}/snapshot`, { members });
    return data;
  },

  close: async (opId: number, notes?: string): Promise<{ message: string; id: number; endTime: string }> => {
    const { data } = await militaryFleetApi.post(`/${opId}/close`, { notes });
    return data;
  },
};

export const opsCalendarApi = {
  list: async (daysAhead = 7): Promise<ScheduledOperation[]> => {
    const { data } = await militaryOpsApi.get('/', { params: { days_ahead: daysAhead } });
    return Array.isArray(data) ? data : (data.operations ?? []);
  },

  get: async (opId: number): Promise<ScheduledOperation> => {
    const { data } = await militaryOpsApi.get(`/${opId}`);
    return data;
  },

  create: async (payload: Partial<ScheduledOperation>): Promise<ScheduledOperation> => {
    const { data } = await militaryOpsApi.post('/', payload);
    return data;
  },

  update: async (opId: number, payload: Partial<ScheduledOperation>): Promise<ScheduledOperation> => {
    const { data } = await militaryOpsApi.put(`/${opId}`, payload);
    return data;
  },

  cancel: async (opId: number): Promise<void> => {
    await militaryOpsApi.delete(`/${opId}`);
  },

  start: async (opId: number): Promise<{ fleet_operation_id: number }> => {
    const { data } = await militaryOpsApi.post(`/${opId}/start`);
    return data;
  },
};

// Re-export fleetCompApi for potential doctrine/counter usage
export { fleetCompApi };

export const syncApi = {
  start: (opId: number, esiFleetId: number, fcCharId: number) =>
    militaryFleetApi.post(`/${opId}/sync/start`, {
      esi_fleet_id: esiFleetId, fc_character_id: fcCharId
    }),
  stop: (opId: number) =>
    militaryFleetApi.post(`/${opId}/sync/stop`),
  status: (opId: number) =>
    militaryFleetApi.get(`/${opId}/sync/status`),
};

// For pilot activity — routes at /api/military/pilot/...
const militaryApi = createApiClient("/api/military");

export const pilotApi = {
  getActivity: async (characterId: number) => {
    const { data } = await militaryApi.get(`/pilot/${characterId}/activity`);
    return data;
  },
};

export const notificationApi = {
  listConfigs: async () => {
    const { data } = await militaryApi.get('/notifications');
    return data;
  },
  createConfig: async (config: { webhook_url: string; event_types: string[]; ping_role?: string }) => {
    const { data } = await militaryApi.post('/notifications', config);
    return data;
  },
  deleteConfig: async (configId: number) => {
    const { data } = await militaryApi.delete(`/notifications/${configId}`);
    return data;
  },
};
