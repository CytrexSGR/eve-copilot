// Subscription System Types

export interface Customer {
  character_id: number
  character_name: string
  corporation_id: number | null
  alliance_id: number | null
  created_at: string
  last_login: string | null
}

export interface Product {
  id: number
  slug: string
  name: string
  description: string | null
  price_isk: number
  duration_days: number
  is_active: boolean
  features: string[]
  created_at: string
}

export interface ProductCreate {
  slug: string
  name: string
  description?: string
  price_isk: number
  duration_days?: number
  is_active?: boolean
  features?: string[]
}

export interface ProductUpdate {
  slug?: string
  name?: string
  description?: string
  price_isk?: number
  duration_days?: number
  is_active?: boolean
  features?: string[]
}

export interface Subscription {
  id: number
  character_id: number
  product_id: number
  starts_at: string
  expires_at: string
  payment_id: number | null
  created_at: string
  character_name?: string
  product_name?: string
}

export interface Payment {
  id: number
  journal_ref_id: number
  from_character_id: number
  from_character_name: string | null
  amount: number
  reason: string | null
  received_at: string
  status: 'pending' | 'matched' | 'processed' | 'failed'
  matched_customer_id: number | null
  payment_code: string | null
  processed_at: string | null
  notes: string | null
  created_at: string
}

export interface PaymentMatch {
  customer_id: number
  product_id: number
}

export interface SubscriptionStats {
  total_customers: number
  active_subscriptions: number
  pending_payments: number
  total_revenue_isk: number
  revenue_30d_isk: number
  active_products: number
}

export interface SystemConfig {
  subscription_enabled: string
  login_enabled: string
  wallet_poll_enabled: string
  billing_character_id: string
}

export interface ConfigUpdate {
  value: string
}
