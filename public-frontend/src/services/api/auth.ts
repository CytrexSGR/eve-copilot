import axios from 'axios';
import type {
  AuthConfig,
  UserProfile,
  AccountInfo,
  TierPricing,
  TierInfo,
  SubscriptionDetail,
  SubscribeResponse,
  PaymentRecord,
  CorpInfo,
  ModuleInfo,
  ModulePricing,
  TokenHealth,
  AccountSummary,
  OrgMember,
  OrgOverview,
  OrgPermissionsResponse,
  AuditLogResponse,
} from '../../types/auth';

const api = axios.create({
  baseURL: '/api',
  timeout: 15_000,
  withCredentials: true,
});

export const authApi = {
  getConfig: () => api.get<AuthConfig>('/auth/public/config').then(r => r.data),
  getLoginUrl: (redirectUrl?: string) =>
    api.get<{ auth_url: string }>('/auth/public/login', {
      params: redirectUrl ? { redirect_url: redirectUrl } : undefined,
    }).then(r => r.data),
  getProfile: () => api.get<UserProfile>('/auth/public/me').then(r => r.data),
  logout: () => api.post('/auth/public/logout').then(r => r.data),
  getAccount: () => api.get<AccountInfo>('/auth/public/account').then(r => r.data),
  addCharacter: () =>
    api.post<{ auth_url: string }>('/auth/public/account/add-character').then(r => r.data),
};

export const tierApi = {
  getPricing: () => api.get<TierPricing[]>('/tier/pricing').then(r => r.data),
  getMyTier: () => api.get<TierInfo>('/tier/my-tier').then(r => r.data),
  getMySubscription: () =>
    api.get<SubscriptionDetail>('/tier/my-subscription').then(r => r.data),
  subscribe: (tier: string, corporationId?: number, allianceId?: number) =>
    api.post<SubscribeResponse>('/tier/subscribe', null, {
      params: { tier, corporation_id: corporationId, alliance_id: allianceId },
    }).then(r => r.data),
  getPaymentStatus: (code: string) =>
    api.get<PaymentRecord>(`/tier/payment-status/${code}`).then(r => r.data),
  getCorpInfo: () => api.get<CorpInfo>('/tier/corp-info').then(r => r.data),
};

export const moduleApi = {
  getActiveModules: () => api.get<ModuleInfo>('/tier/modules/active').then(r => r.data),
  activateTrial: (moduleName: string) => api.post(`/tier/modules/trial/${moduleName}`).then(r => r.data),
  getModulePricing: () => api.get<{ pricing: ModulePricing[] }>('/tier/modules/pricing').then(r => r.data),
};

export const characterMgmtApi = {
  getTokenHealth: (characterId: number) =>
    api.get<TokenHealth>(`/auth/public/characters/${characterId}/token-health`).then(r => r.data),
  setPrimary: (characterId: number) =>
    api.put(`/auth/public/account/primary/${characterId}`).then(r => r.data),
  removeCharacter: (characterId: number) =>
    api.delete(`/auth/public/account/characters/${characterId}`).then(r => r.data),
};

export const characterSummaryApi = {
  getAccountSummary: () =>
    api.get<AccountSummary>(`/characters/summary/account`).then(r => r.data),
};

export const orgApi = {
  getOverview: () =>
    api.get<OrgOverview>('/auth/public/org/overview').then(r => r.data),
  getMembers: () =>
    api.get<OrgMember[]>('/auth/public/org/members').then(r => r.data),
  changeRole: (characterId: number, role: string) =>
    api.put(`/auth/public/org/members/${characterId}/role`, { role }).then(r => r.data),
  removeMember: (characterId: number) =>
    api.delete(`/auth/public/org/members/${characterId}`).then(r => r.data),
  getPermissions: () =>
    api.get<OrgPermissionsResponse>('/auth/public/org/permissions').then(r => r.data),
  updatePermissions: (updates: Array<{role: string; permission: string; granted: boolean}>) =>
    api.put('/auth/public/org/permissions', { updates }).then(r => r.data),
  getAuditLog: (params?: { limit?: number; offset?: number; action?: string; actor_id?: number; date_from?: string; date_to?: string }) =>
    api.get<AuditLogResponse>('/auth/public/org/audit', { params }).then(r => r.data),
  exportAuditCsv: () =>
    api.get('/auth/public/org/audit/export', { responseType: 'blob' }).then(r => r.data),
};
