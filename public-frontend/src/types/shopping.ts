export interface ShoppingList {
  id: number;
  name: string;
  character_id?: number;
  created_at: string;
  updated_at: string;
  item_count: number;
  total_value?: number;
}

export interface ShoppingItem {
  id: number;
  list_id: number;
  type_id: number;
  type_name: string;
  quantity: number;
  unit_price?: number;
  total_price?: number;
  purchased: boolean;
}

export interface CargoSummary {
  total_volume_m3: number;
  item_count: number;
  weight_kg: number;
  estimated_time_hours: number;
  transport_ships: TransportShip[];
}

export interface TransportShip {
  ship_name: string;
  cargo_capacity: number;
  security_level: string;
  cost_estimate: number;
  travel_time: number;
}

export interface FreightRoute {
  id: number;
  name: string;
  start_system_id: number;
  start_system_name?: string;
  end_system_id: number;
  end_system_name?: string;
  route_type: string;
  base_price: number;
  rate_per_m3: number;
  collateral_pct: number;
  max_volume: number;
  max_collateral: number;
  is_active: boolean;
  notes?: string;
}

export interface FreightCalculation {
  price: number;
  base_price: number;
  volume_charge: number;
  collateral_charge: number;
}

export interface RegionalComparison {
  regions: Array<{
    region_id: number;
    region_name: string;
    total_cost: number;
    items: Array<{
      type_id: number;
      type_name: string;
      quantity: number;
      price: number;
      available: boolean;
    }>;
  }>;
}
