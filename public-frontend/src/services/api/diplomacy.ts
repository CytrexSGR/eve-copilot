import { createApiClient } from './client';

const api = createApiClient('/api/auth/public/org/diplomacy');

export interface StandingEntry {
  contact_id: number;
  contact_name: string | null;
  contact_type: string;
  standing: number;
  is_blocked: boolean;
  is_watched: boolean;
  labels?: any[];
}

export interface ContactsSummary {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  watched: number;
  blocked: number;
  contacts: StandingEntry[];
}

export interface StandingsSummary {
  total: number;
  entries: StandingEntry[];
}

export interface AlumniMember {
  character_id: number;
  character_name: string;
  left_at: string | null;
  destination_corp_id: number | null;
  destination_corp_name: string | null;
  note: string;
  noted_by_name: string | null;
  created_at: string | null;
}

export const diplomacyApi = {
  getStandings: async (params?: { contact_type?: string; limit?: number; offset?: number }): Promise<StandingsSummary> => {
    const { data } = await api.get('/standings', { params });
    return data;
  },

  getContacts: async (params?: {
    contact_type?: string;
    min_standing?: number;
    max_standing?: number;
    watched_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<ContactsSummary> => {
    const { data } = await api.get('/contacts', { params });
    return data;
  },

  getAlumni: async (params?: { limit?: number; offset?: number }): Promise<{ alumni: AlumniMember[]; total: number }> => {
    const { data } = await api.get('/alumni', { params });
    return data;
  },

  upsertAlumniNote: async (noteData: { character_id: number; character_name: string; note: string }): Promise<{ success: boolean; id: number }> => {
    const { data } = await api.post('/alumni/note', noteData);
    return data;
  },
};
