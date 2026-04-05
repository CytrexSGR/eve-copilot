// unified-frontend/src/types/reactions.ts

export interface ReactionInput {
  input_type_id: number
  input_name: string
  quantity: number
}

export interface ReactionFormula {
  reaction_type_id: number
  reaction_name: string
  product_type_id: number
  product_name: string
  product_quantity: number
  reaction_time: number
  reaction_category?: string
  inputs: ReactionInput[]
}

export interface ReactionProfitability {
  reaction_type_id: number
  reaction_name: string
  product_name: string
  input_cost: number
  output_value: number
  profit_per_run: number
  profit_per_hour: number
  roi_percent: number
  reaction_time: number
  runs_per_hour: number
}

export interface ProfitableReaction extends ReactionProfitability {
  rank: number
}

export type ReactionType = 'simple' | 'complex' | 'composite' | 'biochemical' | 'all'
