// src/types/warfare-intel.ts
// Types for Live Warfare Intelligence Tab

import type { ActiveBattle } from './battle';
import type { FastEnemy } from './intelligence';

// Alliance selector item
export interface AllianceOption {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  kills: number;
  coalition_id: number | null;
}

// Coalition with nested alliances for selector
export interface CoalitionGroup {
  coalition_id: number;
  leader_name: string;
  alliances: AllianceOption[];
}

// Live Activity section - alliance-filtered battles
export interface AllianceBattle extends ActiveBattle {
  enemy_coalition: string | null;
  has_capitals: boolean;
}

// Top Enemy with efficiency comparison
export interface TopEnemy extends FastEnemy {
  ticker: string;
  losses_to_them: number;
  isk_lost_to_them: number;
  efficiency_vs_them: number; // our kills / their kills against us
}

// Doctrine usage stats
export interface DoctrineUsage {
  doctrine_name: string;
  losses: number;
  percentage: number;
}

// Matchup result
export interface DoctrineMatchup {
  our_doctrine: string;
  enemy_doctrine: string;
  enemy_alliance: string;
  enemy_ticker: string;
  wins: number;
  losses: number;
  winrate: number;
}

// Activity Pattern with timezone breakdown
export interface ActivityPattern {
  kills_by_hour: number[];
  deaths_by_hour: number[];
  peak_start: number;
  peak_end: number;
  timezone_breakdown: {
    eutz: number; // percentage
    ustz: number;
    autz: number;
  };
}

// Full warfare intel response
export interface WarfareIntelData {
  alliance_id: number;
  alliance_name: string;
  period_minutes: number;
  live_battles: AllianceBattle[];
  recent_kills: RecentKill[];
  top_enemies: TopEnemy[];
  doctrine_usage: DoctrineUsage[];
  doctrine_matchups: DoctrineMatchup[];
  activity_pattern: ActivityPattern;
}

// Kill ticker item
export interface RecentKill {
  killmail_id: number;
  ship_name: string;
  value: number;
  time: string;
}
