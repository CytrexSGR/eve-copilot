import { apiClient } from './client'

export interface ItemSearchResult {
  typeID: number
  typeName: string
  groupID: number
  volume: number
  basePrice: string | null
}

export interface ItemSearchResponse {
  query: string
  results: ItemSearchResult[]
}

export interface ProductionMaterial {
  type_id: number
  name: string
  base_quantity: number
  adjusted_quantity: number
  unit_price: number
  total_cost: number
}

export interface ProductionCostResponse {
  item: {
    type_id: number
    name: string
    output_quantity: number
  }
  blueprint: {
    type_id: number
    name: string
  }
  settings: {
    me_level: number
    te_level: number
    region_id: number
    price_source: string
  }
  materials: ProductionMaterial[]
  summary: {
    total_material_cost: number
    cost_per_unit: number
    base_build_time_seconds: number
    adjusted_build_time_seconds: number
    build_time_formatted: string
  }
  profit_analysis?: {
    current_sell_price: number
    total_sell_value: number
    profit: number
    profit_margin_percent: number
    profitable: boolean
  }
}

export interface ProductionChainNode {
  name: string
  quantity: number
  is_raw: boolean
  children: Record<string, ProductionChainNode>
}

export interface ProductionChainResponse {
  item_type_id: number
  item_name: string
  tree: Record<string, ProductionChainNode>
  has_dependencies: boolean
}

export const productionApi = {
  /**
   * Search items by name
   */
  searchItems: async (query: string, limit: number = 20): Promise<ItemSearchResponse> => {
    const response = await apiClient.get<ItemSearchResponse>('/items/search', {
      params: { q: query, limit },
    })
    return response.data
  },

  /**
   * Get production cost for an item
   */
  getProductionCost: async (
    typeId: number,
    meLevel: number = 0,
    regionId: number = 10000002
  ): Promise<ProductionCostResponse> => {
    const response = await apiClient.get<ProductionCostResponse>(`/production/cost/${typeId}`, {
      params: { me: meLevel, region_id: regionId },
    })
    return response.data
  },

  /**
   * Get production chain (material tree)
   */
  getProductionChain: async (typeId: number): Promise<ProductionChainResponse> => {
    const response = await apiClient.get<ProductionChainResponse>(`/production/chains/${typeId}`)
    return response.data
  },
}
