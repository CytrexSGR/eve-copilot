// Wallet types

export interface WalletJournalEntry {
  transaction_id: number;
  corporation_id: number;
  division_id: number;
  date: string;
  ref_type: string;
  ref_type_label: string;
  first_party_id: number;
  second_party_id: number;
  amount: number;
  balance: number;
  reason: string;
}

export interface WalletBalance {
  corporation_id: number;
  division_id: number;
  balance: number;
  as_of: string;
}

export interface WalletDivision {
  corporation_id: number;
  division_id: number;
  name: string;
}

// Report types

export interface IncomeBreakdown {
  category: string;
  ref_types: string[];
  total_amount: number;
  transaction_count: number;
}

export interface ExpenseSummary {
  division_id: number;
  division_name: string;
  total_amount: number;
  transaction_count: number;
}

export interface PnlReport {
  corporation_id: number;
  period_start: string;
  period_end: string;
  total_income: number;
  total_expenses: number;
  net_profit: number;
  income_breakdown: IncomeBreakdown[];
  expense_breakdown: ExpenseSummary[];
}

// Mining Tax types

export interface MiningLedgerEntry {
  observer_id: number;
  character_id: number;
  character_name: string;
  type_id: number;
  type_name: string;
  last_updated: string;
  quantity: number;
  delta_quantity: number;
  isk_value: number;
  tax_amount: number;
}

export interface MiningTaxSummary {
  character_id: number;
  character_name: string;
  total_mined_quantity: number;
  total_isk_value: number;
  total_tax: number;
  ore_breakdown: Array<{
    ore: string;
    quantity: number;
    isk_value: number;
  }>;
}

export interface MiningConfig {
  corporation_id: number;
  tax_rate: number;
  reprocessing_yield: number;
  pricing_mode: string;
  updated_at?: string;
}

// Invoice types

export interface TaxInvoice {
  id: number;
  character_id: number;
  period_start: string;
  period_end: string;
  total_mined_value: number;
  tax_rate: number;
  amount_due: number;
  amount_paid: number;
  remaining_balance: number;
  status: 'pending' | 'partial' | 'paid' | 'overdue';
  created_at: string;
}

// Buyback types

export interface BuybackItem {
  type_id: number;
  type_name: string;
  quantity: number;
  jita_sell: number;
  jita_buy: number;
  jita_sell_total: number;
  jita_buy_total: number;
  total_volume: number;
  buyback_price: number;
  buyback_total: number;
}

export interface BuybackAppraisal {
  items: BuybackItem[];
  summary: {
    item_count: number;
    total_jita_sell: number;
    total_jita_buy: number;
    total_volume: number;
  };
  buyback: {
    total_payout: number;
    discount_applied: number;
  };
  config: {
    name: string;
    base_discount: number;
    ore_modifier: number;
  };
}

export interface BuybackRequest {
  id: number;
  character_id: number;
  corporation_id: number;
  status: string;
  total_payout: number;
  submitted_at: string;
}

export interface BuybackConfig {
  id: number;
  corporation_id: number;
  name: string;
  base_discount: number;
  ore_modifier: number;
  notes?: string;
}

// ISK formatting helper
export function formatIsk(value: number): string {
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B ISK`;
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M ISK`;
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(0)}K ISK`;
  return `${value.toLocaleString()} ISK`;
}
