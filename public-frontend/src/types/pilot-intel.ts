import type { CharacterSummary } from './character';
import type { PortfolioSnapshot, AggregatedOrdersResponse } from './market';

export interface PilotProfile {
  characters: CharacterSummary[];
  portfolioSummary: { snapshots: PortfolioSnapshot[]; combined_liquid: number } | null;
  orders: AggregatedOrdersResponse | null;
  lastUpdated: Date | null;
}

/** Derived data computed from PilotProfile */
export interface PilotDerived {
  totalWallet: number;
  totalAssetValue: number;
  totalSellOrderValue: number;
  totalBuyEscrow: number;
  totalNetWorth: number;
  activeIndustryJobs: number;
  completingSoonJobs: Array<{ characterName: string; jobName: string; endsAt: Date }>;
  outbidCount: number;
  skillMap: Map<number, number>;  // skillId -> level (merged from all chars)
  primaryCharacter: CharacterSummary | null;
}

export interface PilotIntelState {
  profile: PilotProfile;
  derived: PilotDerived;
  isLoading: boolean;
  refresh: () => Promise<void>;
}
