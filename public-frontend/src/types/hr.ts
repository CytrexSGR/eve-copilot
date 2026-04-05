// Red List types

export interface RedListEntity {
  id: number;
  entity_id: number;
  entity_name: string;
  category: 'character' | 'corporation' | 'alliance';
  severity: number;
  reason: string;
  added_by: string;
  added_at: string;
  active: boolean;
}

export interface RedListCreateRequest {
  entity_id: number;
  entity_name: string;
  category: 'character' | 'corporation' | 'alliance';
  severity: number;
  reason: string;
  added_by: string;
}

export interface RedListCheckResult {
  on_list: boolean;
  severity?: number;
  reason?: string;
}

// Vetting types

export interface VettingFlags {
  red_list_hit: boolean;
  wallet_suspicious: boolean;
  skill_injection_detected: boolean;
  corp_hopping: boolean;
  short_tenure: boolean;
}

export interface VettingReport {
  id: number;
  character_id: number;
  character_name: string;
  risk_score: number;
  flags: VettingFlags;
  red_list_hits: Array<{
    entity_id: number;
    severity: number;
    reason: string;
  }>;
  wallet_flags: Array<{
    type: string;
    amount: number;
    direction: string;
  }>;
  skill_flags: Array<{
    type: string;
    details: string;
  }>;
  checked_at: string;
}

export interface VettingCheckRequest {
  character_id: number;
  check_contacts?: boolean;
  check_wallet?: boolean;
  check_skills?: boolean;
}

// Activity Tracking types

export interface ActivitySummary {
  character_id: number;
  character_name: string;
  fleet_count_30d: number;
  kill_count_30d: number;
  last_kill_at: string | null;
  last_fleet_at: string | null;
  last_login_at: string | null;
  total_sp: number;
  risk_score: number;
}

export interface FleetSession {
  id: number;
  fleet_id: number;
  fleet_name: string;
  character_id: number;
  character_name: string;
  ship_type_id: number;
  ship_name: string;
  start_time: string;
  end_time: string;
  solar_system_id: number;
}

export interface InactiveMember {
  character_id: number;
  character_name: string;
  last_login_at: string | null;
  days_inactive: number;
  fleet_count_30d: number;
  kill_count_30d: number;
}

// Application types

export interface HrApplication {
  id: number;
  character_id: number;
  character_name: string;
  corporation_id: number;
  status: 'pending' | 'reviewing' | 'approved' | 'rejected' | 'withdrawn';
  motivation: string;
  recruiter_id: number | null;
  recruiter_notes: string | null;
  submitted_at: string;
  reviewed_at: string | null;
  decided_at: string | null;
  vetting_report_id: number | null;
  risk_score: number | null;
  vetting_flags: VettingFlags | null;
}

export interface ApplicationReview {
  recruiter_id: number;
  recruiter_notes?: string;
  status: 'reviewing' | 'approved' | 'rejected' | 'withdrawn';
}

// Risk score color helpers

export function getRiskColor(score: number): string {
  if (score >= 70) return '#f85149';
  if (score >= 40) return '#d29922';
  return '#3fb950';
}

export function getRiskLabel(score: number): string {
  if (score >= 70) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

export function getSeverityColor(severity: number): string {
  if (severity >= 4) return '#f85149';
  if (severity >= 3) return '#ff8800';
  if (severity >= 2) return '#d29922';
  return '#8b949e';
}

export const STATUS_COLORS: Record<string, string> = {
  pending: '#d29922',
  reviewing: '#00d4ff',
  approved: '#3fb950',
  rejected: '#f85149',
  withdrawn: '#8b949e',
};
