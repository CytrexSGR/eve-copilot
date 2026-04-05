// Hunting Command Center Types

export interface HotZone {
  system_id: number;
  system_name: string;
  region_name: string;
  kills: number;
  deaths: number;
  total_activity: number;
}

export interface StrikeWindow {
  activity_by_hour: Array<{
    hour: number;
    activity: number;
    their_deaths: number;
    their_kills: number;
  }>;
  peak_hours: {
    start: string;
    end: string;
    pct: number;
  };
  weak_hours: {
    start: string;
    end: string;
    pct: number;
  };
  last_24h: {
    kills: number;
    capital_deployments: number;
  };
  recommendation: string;
}

export interface PriorityTarget {
  character_id: number;
  character_name: string;
  whale_score: number;
  whale_category: 'whale' | 'shark' | 'fish';
  isk_per_death: number;
  total_isk_lost: number;
  deaths: number;
  kills: number;
  efficiency: number;
  typical_ships: string[];
  last_active: string;
}

export interface FleetRole {
  ship: string;
  count: number;
  reason: string;
  type_id: number;
}

export interface CounterDoctrine {
  their_meta: Array<{
    ship: string;
    type_id: number;
    ship_class: string;
    pct: number;
    count: number;
  }>;
  damage_profile: {
    kinetic: number;
    thermal: number;
    em: number;
    explosive: number;
  };
  primary_damage_type: string;
  tank_recommendation: string;
  recommended_fleet: {
    dps: FleetRole;
    logi: FleetRole;
    support: FleetRole;
    tackle: FleetRole;
  };
  reasoning: string;
}

export interface HuntingData {
  hotZones: HotZone[];
  strikeWindow: StrikeWindow;
  priorityTargets: PriorityTarget[];
  counterDoctrine: CounterDoctrine;
}
