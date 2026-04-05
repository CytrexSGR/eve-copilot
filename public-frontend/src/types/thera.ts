// Thera Router Types

export interface TheraConnection {
  id: string;
  wh_type: string;
  max_ship_size: 'medium' | 'large' | 'xlarge' | 'capital';
  remaining_hours: number;
  expires_at: string;
  out_system_id: number;
  out_system_name: string;
  out_signature: string;
  in_system_id: number;
  in_system_name: string;
  in_system_class: string;
  in_region_id: number;
  in_region_name: string;
  in_signature?: string;
  completed: boolean;
}

export interface TheraSystemInfo {
  system_id: number;
  system_name: string;
  region_id?: number;
  region_name?: string;
  security_class?: string;
  security_status?: number;
}

export interface TheraRouteSegment {
  entry_connection: TheraConnection;
  exit_connection: TheraConnection;
  entry_jumps: number;
  exit_jumps: number;
  total_jumps: number;
}

export interface TheraRouteSavings {
  jumps_saved: number;
  percentage: number;
  estimated_time_saved_minutes?: number;
}

export interface TheraRoute {
  origin: TheraSystemInfo;
  destination: TheraSystemInfo;
  direct_jumps: number;
  thera_route: TheraRouteSegment | null;
  savings: TheraRouteSavings;
  recommended: 'direct' | 'thera';
}

export interface TheraConnectionList {
  count: number;
  hub: string;
  last_updated: string;
  connections: TheraConnection[];
}

export interface TheraStatus {
  status: string;
  thera_connections: number;
  turnur_connections: number;
  cache_age_seconds?: number;
  last_fetch?: string;
  eve_scout_reachable: boolean;
}

export type ShipSize = 'medium' | 'large' | 'xlarge' | 'capital';
export type HubType = 'thera' | 'turnur' | 'all';
