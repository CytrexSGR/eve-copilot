// Corp Contracts types (war-intel-service uses camelCase)

export interface CorpContract {
  contractId: number;
  type: string;
  status: string;
  title: string | null;
  issuerId: number;
  acceptorId: number | null;
  price: number | null;
  reward: number | null;
  collateral: number | null;
  volume: number | null;
  dateIssued: string;
  dateExpired: string;
  dateAccepted: string | null;
  daysToComplete: number;
}

export interface ContractSummary {
  outstanding: number;
  inProgress: number;
  total: number;
}

export interface ContractActiveResponse {
  corporationId: number;
  summary: ContractSummary;
  contracts: CorpContract[];
}

export interface ContractTypeStatus {
  type: string;
  status: string;
  count: number;
  totalValue: number;
}

export interface ContractCompletionRate {
  type: string;
  total: number;
  completed: number;
  failed: number;
  completionRate: number;
}

export interface ContractStatsResponse {
  corporationId: number;
  periodDays: number;
  byTypeStatus: ContractTypeStatus[];
  completionRates: ContractCompletionRate[];
}

export interface CourierEfficiency {
  averageIskPerM3: number;
  averageCompletionHours: number;
  totalRewardPaid: number;
  totalVolumeMoved: number;
}

export interface CourierAnalysisResponse {
  corporationId: number;
  periodDays: number;
  summary: { total: number; outstanding: number; inProgress: number; completed: number; completionRate: number };
  efficiency: CourierEfficiency;
  topHaulers: { characterId: number; count: number; volume: number; reward: number }[];
}

export interface ContractChange {
  contractId: number;
  oldStatus: string;
  newStatus: string;
  changedAt: string;
  type: string;
  price: number | null;
  reward: number | null;
}

// Discord Relay types

export interface DiscordRelay {
  id: number;
  name: string;
  webhookUrl: string;
  filterRegions: number[];
  filterAlliances: number[];
  notifyTypes: string[];
  pingRoleId: string | null;
  isActive: boolean;
  minIskThreshold: number;
  createdAt: string;
  updatedAt: string;
}

export interface DiscordRelayCreate {
  name: string;
  webhookUrl: string;
  filterRegions?: number[];
  filterAlliances?: number[];
  notifyTypes?: string[];
  pingRoleId?: string;
  minIskThreshold?: number;
}

export interface DiscordRelayUpdate {
  name?: string;
  webhookUrl?: string;
  filterRegions?: number[];
  filterAlliances?: number[];
  notifyTypes?: string[];
  pingRoleId?: string;
  isActive?: boolean;
  minIskThreshold?: number;
}

// Helpers

export const CONTRACT_STATUS_COLORS: Record<string, string> = {
  outstanding: '#d29922',
  in_progress: '#00d4ff',
  finished: '#3fb950',
  finished_issuer: '#3fb950',
  finished_contractor: '#3fb950',
  cancelled: '#8b949e',
  rejected: '#f85149',
  failed: '#f85149',
  deleted: '#8b949e',
  reversed: '#ff8800',
};

export const NOTIFY_TYPE_LABELS: Record<string, string> = {
  timer_created: 'Timer Created',
  timer_expiring: 'Timer Expiring',
  battle_started: 'Battle Started',
  structure_attack: 'Structure Attack',
  high_value_kill: 'High-Value Kill',
};

export function formatIsk(amount: number): string {
  if (amount >= 1e12) return `${(amount / 1e12).toFixed(1)}T`;
  if (amount >= 1e9) return `${(amount / 1e9).toFixed(1)}B`;
  if (amount >= 1e6) return `${(amount / 1e6).toFixed(1)}M`;
  if (amount >= 1e3) return `${(amount / 1e3).toFixed(0)}K`;
  return amount.toFixed(0);
}
