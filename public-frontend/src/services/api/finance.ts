import { createApiClient } from './client';
import type {
  WalletJournalEntry, WalletBalance, WalletDivision,
  IncomeBreakdown, ExpenseSummary, PnlReport,
  MiningLedgerEntry, MiningTaxSummary, MiningConfig,
  TaxInvoice,
  BuybackAppraisal, BuybackRequest, BuybackConfig,
} from '../../types/finance';

const api = createApiClient('/api/finance');

export const walletApi = {
  getJournal: async (corpId: number, params?: {
    division_id?: number;
    ref_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<WalletJournalEntry[]> => {
    const { data } = await api.get(`/wallet/journal/${corpId}`, { params });
    return Array.isArray(data) ? data : data.entries || [];
  },

  getBalance: async (corpId: number, divisionId = 1): Promise<WalletBalance> => {
    const { data } = await api.get(`/wallet/balance/${corpId}`, {
      params: { division_id: divisionId },
    });
    return data;
  },

  getDivisions: async (corpId: number): Promise<WalletDivision[]> => {
    const { data } = await api.get(`/wallet/divisions/${corpId}`);
    return Array.isArray(data) ? data : data.divisions || [];
  },
};

export const reportsApi = {
  getIncome: async (corpId: number, days = 30, divisionId = 1): Promise<IncomeBreakdown[]> => {
    const { data } = await api.get(`/reports/income/${corpId}`, {
      params: { days, division_id: divisionId },
    });
    return Array.isArray(data) ? data : data.breakdown || [];
  },

  getExpenses: async (corpId: number, days = 30): Promise<ExpenseSummary[]> => {
    const { data } = await api.get(`/reports/expenses/${corpId}`, { params: { days } });
    return Array.isArray(data) ? data : data.breakdown || [];
  },

  getPnl: async (corpId: number, periodStart: string, periodEnd: string): Promise<PnlReport> => {
    const { data } = await api.get(`/reports/pnl/${corpId}`, {
      params: { period_start: periodStart, period_end: periodEnd },
    });
    return data;
  },
};

export const miningApi = {
  getLedger: async (corpId: number, params?: {
    character_id?: number;
    days?: number;
    limit?: number;
    offset?: number;
  }): Promise<MiningLedgerEntry[]> => {
    const { data } = await api.get(`/mining/ledger/${corpId}`, { params });
    return Array.isArray(data) ? data : data.entries || [];
  },

  getTaxSummary: async (corpId: number, days = 30): Promise<MiningTaxSummary[]> => {
    const { data } = await api.get(`/mining/tax-summary/${corpId}`, { params: { days } });
    return Array.isArray(data) ? data : data.summary || [];
  },

  getConfig: async (corpId: number): Promise<MiningConfig> => {
    const { data } = await api.get(`/mining/config/${corpId}`);
    return data;
  },

  updateConfig: async (corpId: number, config: Partial<MiningConfig>): Promise<MiningConfig> => {
    const { data } = await api.put(`/mining/config/${corpId}`, null, { params: config });
    return data;
  },
};

export const invoiceApi = {
  getInvoices: async (params?: {
    corporation_id?: number;
    character_id?: number;
    status?: string;
    limit?: number;
  }): Promise<TaxInvoice[]> => {
    const { data } = await api.get('/invoices', { params });
    return Array.isArray(data) ? data : data.invoices || [];
  },

  generate: async (corpId: number, periodStart: string, periodEnd: string, taxRate: number) => {
    const { data } = await api.post('/invoices/generate', {
      corporation_id: corpId, period_start: periodStart, period_end: periodEnd, tax_rate: taxRate,
    });
    return data;
  },

  matchPayments: async (corpId: number) => {
    const { data } = await api.post(`/invoices/match-payments/${corpId}`);
    return data;
  },
};

export const buybackApi = {
  appraise: async (rawText: string, configId?: number): Promise<BuybackAppraisal> => {
    const { data } = await api.post('/buyback/appraise', {
      raw_text: rawText, config_id: configId,
    });
    return data;
  },

  submit: async (rawText: string, configId: number, characterId: number, characterName: string, corporationId: number): Promise<BuybackRequest> => {
    const { data } = await api.post('/buyback/submit', {
      raw_text: rawText, config_id: configId,
      character_id: characterId, character_name: characterName, corporation_id: corporationId,
    });
    return data;
  },

  getRequests: async (params?: {
    corporation_id?: number;
    character_id?: number;
    status?: string;
    limit?: number;
  }): Promise<{ requests: BuybackRequest[]; count: number }> => {
    const { data } = await api.get('/buyback/requests', { params });
    return data;
  },

  getConfigs: async (corporationId?: number, activeOnly = true): Promise<{ configs: BuybackConfig[]; count: number }> => {
    const { data } = await api.get('/buyback/configs', {
      params: { corporation_id: corporationId, active_only: activeOnly },
    });
    return data;
  },
};
