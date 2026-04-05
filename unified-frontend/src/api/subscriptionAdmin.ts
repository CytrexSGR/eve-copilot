import axios from 'axios'
import type {
  Customer,
  Product,
  ProductCreate,
  ProductUpdate,
  Subscription,
  Payment,
  PaymentMatch,
  SubscriptionStats,
  SystemConfig,
  ConfigUpdate,
} from '@/types/subscription'

// Auth service runs on port 8010
const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8010'

const authClient = axios.create({
  baseURL: AUTH_API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export const subscriptionAdminApi = {
  // Stats
  getStats: async (): Promise<SubscriptionStats> => {
    const response = await authClient.get<SubscriptionStats>('/api/admin/stats')
    return response.data
  },

  // Customers
  getCustomers: async (limit = 100, offset = 0): Promise<Customer[]> => {
    const response = await authClient.get<Customer[]>('/api/admin/customers', {
      params: { limit, offset }
    })
    return response.data
  },

  // Products
  getProducts: async (): Promise<Product[]> => {
    const response = await authClient.get<Product[]>('/api/admin/products')
    return response.data
  },

  createProduct: async (data: ProductCreate): Promise<Product> => {
    const response = await authClient.post<Product>('/api/admin/products', data)
    return response.data
  },

  updateProduct: async (id: number, data: ProductUpdate): Promise<Product> => {
    const response = await authClient.put<Product>(`/api/admin/products/${id}`, data)
    return response.data
  },

  deleteProduct: async (id: number): Promise<void> => {
    await authClient.delete(`/api/admin/products/${id}`)
  },

  // Subscriptions
  getSubscriptions: async (activeOnly = true, limit = 100): Promise<Subscription[]> => {
    const response = await authClient.get<Subscription[]>('/api/admin/subscriptions', {
      params: { active_only: activeOnly, limit }
    })
    return response.data
  },

  createSubscription: async (characterId: number, productId: number): Promise<Subscription> => {
    const response = await authClient.post<Subscription>('/api/admin/subscriptions', null, {
      params: { character_id: characterId, product_id: productId }
    })
    return response.data
  },

  // Payments
  getPayments: async (status?: string, limit = 100): Promise<Payment[]> => {
    const response = await authClient.get<Payment[]>('/api/admin/payments', {
      params: { status, limit }
    })
    return response.data
  },

  matchPayment: async (paymentId: number, data: PaymentMatch): Promise<{ payment: Payment; subscription: Subscription }> => {
    const response = await authClient.post(`/api/admin/payments/${paymentId}/match`, data)
    return response.data
  },

  // Config
  getConfig: async (): Promise<SystemConfig> => {
    const response = await authClient.get<SystemConfig>('/api/admin/config')
    return response.data
  },

  updateConfig: async (key: string, data: ConfigUpdate): Promise<{ key: string; value: string }> => {
    const response = await authClient.put(`/api/admin/config/${key}`, data)
    return response.data
  },
}
