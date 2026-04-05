export interface AllianceCapitalIntel {
  alliance_id: number;
  days: number;
  summary: {
    total_engagements: number;
    unique_corps: number;
    regions_active: number;
    ship_types: number;
  };
  race_distribution: Record<string, number>;
  ships: Array<{
    ship_name: string;
    race: string;
    ship_class: string;
    engagements: number;
    corps_using: number;
  }>;
  top_corps: Array<{
    corporation_id: number;
    corporation_name: string;
    engagements: number;
    ship_types: number;
    ships_used: string[];
  }>;
  regions: Array<{
    region: string;
    ops: number;
    last_seen: string;
  }>;
  daily_activity: Array<{
    day: string;
    engagements: number;
  }>;
}
